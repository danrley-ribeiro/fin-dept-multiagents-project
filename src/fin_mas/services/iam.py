"""SVC-IAM — identidade e acesso de pessoas (ADR-009, NORM-12, NORM-13), DSM3.

Antes, qualquer processo local que lesse o token da sessão agia como o aprovador `APR`. Agora
quem usa a plataforma é uma **pessoa com conta**: entra com senha, recebe uma sessão, só faz o
que os papéis dela permitem, e cada comando e cada decisão ficam ligados a ela.

Regras (cada uma com id; toda negação vai para a trilha de acesso com a regra):

- IAM-01  o primeiro administrador só é criado enquanto não existe nenhuma conta (bootstrap);
- IAM-02  senha com no mínimo 12 caracteres, diferente do usuário e fora da lista de senhas
          óbvias; senha redefinida por um administrador precisa ser trocada na primeira entrada;
- IAM-03  cinco senhas erradas seguidas bloqueiam a conta por 15 minutos; usuário inexistente
          custa o mesmo tempo de verificação e recebe a mesma resposta;
- IAM-04  a sessão vale 8 horas, cai após 15 minutos sem uso e pode ser revogada; conta
          bloqueada ou desativada derruba as sessões dela;
- IAM-05  negado por padrão: só passa o que algum papel da conta concede (`models/permissions.yaml`);
- IAM-06  a mesma conta não acumula papéis incompatíveis (administrador de acesso e aprovador),
          e o último administrador ativo não pode ser removido, bloqueado nem rebaixado;
- IAM-07  cadastro com integridade comprometida não deixa ninguém entrar (falha fechada).

Senhas: `hashlib.scrypt` com sal por conta; o cadastro guarda só o resultado. Sessões: o
cadastro guarda só o SHA-256 do token. Os dois arquivos são selados (`services/selado.py`) e
podem ser alterados pela TUI enquanto o servidor roda: a revogação vale na requisição seguinte.

**Atestado de decisão** (POL-09): uma decisão no Approval Gate leva
`{pessoa, sessao, nonce, token}`, em que `token` é um HMAC, com uma chave que só existe neste
processo, sobre o ticket, o hash do veto, a decisão, o corpo da decisão, a pessoa, a sessão e
o nonce. O SVC-POL só aceita a decisão se o atestado conferir, a sessão estiver viva, o nonce
for inédito e a pessoa tiver o papel de aprovador. Sem isso, uma mensagem `approve` bem
formada, vinda da caixa `APR`, não basta.

`Acesso.simulado()` cria contas em memória, sem senha e com relógio lógico, para os cenários
em lote: o atestado e as regras POL valem do mesmo jeito, de forma determinística.

DSM4 (ADR-012): segundo fator (IAM-08), empresas (IAM-09), cofre (IAM-10) e delegações (POL-11)
ficam em `services/acesso_avancado.py`, uma extensão desta classe.
"""
import base64
import contextlib
import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from fin_mas.core import permissoes
from fin_mas.services.acesso_avancado import AcessoAvancado
from fin_mas.services.selado import ArquivoComprometido, ArquivoSelado, TravaOcupada
from fin_mas.services.trilha import TrilhaAcesso

VERSAO = 1
MIN_SENHA = 12
MAX_FALHAS = 5
BLOQUEIO_S = 15 * 60
TTL_SESSAO_S = 8 * 60 * 60
INATIVIDADE_S = 15 * 60
PERSISTIR_VISTA_S = 60  # a marca de último uso vai ao disco no máximo uma vez por minuto
SENHAS_PROIBIDAS = {"123456789012", "senha1234567", "password1234", "administrador", "qwertyuiop12", "aaaaaaaaaaaa",
                    "trocar-senha!", "controladoria"}
ESTADOS = ("ativa", "bloqueada", "desativada")
PAPEL_ADM = "ROLE-ADM"


class AcessoNegado(PermissionError):
    """Negação com a regra aplicada; a mensagem pode ir para a interface (nunca traz segredo)."""

    def __init__(self, regra: str, motivo: str):
        super().__init__(f"{regra}: {motivo}")
        self.regra, self.motivo = regra, motivo


class SegundoFatorPendente(AcessoNegado):
    """Senha certa, falta o código (IAM-08): `desafio` é o token da pré-sessão, que só serve para
    `confirmar_entrada`. Quem não trata o caso continua negando a entrada (falha fechada)."""

    def __init__(self, desafio: str, expira_em: float):
        super().__init__("IAM-08", "segundo fator pendente: informe o código do aplicativo autenticador ou um "
                                   "código de recuperação")
        self.desafio, self.expira_em = desafio, expira_em


@dataclass(frozen=True)
class Sessao:
    id: str
    usuario: str
    nome: str
    papeis: tuple
    permissoes: frozenset
    pessoa_erp: str | None
    cargo: str | None
    csrf: str
    expira_em: float
    trocar_senha: bool = False
    pendente_2fa: bool = False  # a política do cadastro exige o segundo fator e a conta ainda não o ativou (IAM-08)
    empresa: str | None = None  # empresa ativa da sessão (IAM-09)
    empresas: tuple = ()  # escopo da conta

    def pode(self, permissao: str) -> bool:
        return permissao in self.permissoes

    def publico(self) -> dict:
        """O que a interface recebe sobre a própria sessão (sem o token)."""
        return {"usuario": self.usuario, "nome": self.nome, "papeis": list(self.papeis),
                "permissoes": sorted(self.permissoes), "pessoa_erp": self.pessoa_erp, "cargo": self.cargo,
                "expira_em": self.expira_em, "trocar_senha": self.trocar_senha, "pendente_2fa": self.pendente_2fa,
                "empresa": self.empresa, "empresas": list(self.empresas)}


def _hash_senha(senha: str, custo: int, sal: bytes | None = None) -> str:
    sal = sal or secrets.token_bytes(16)
    dk = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=2 ** custo, r=8, p=1, maxmem=2 ** 27, dklen=32)
    return f"scrypt${custo}$8$1${base64.b64encode(sal).decode()}${base64.b64encode(dk).decode()}"


def _confere_senha(senha: str, guardado: str) -> bool:
    try:
        _, custo, _, _, sal, _ = guardado.split("$")
        return hmac.compare_digest(guardado, _hash_senha(senha, int(custo), base64.b64decode(sal)))
    except (ValueError, TypeError):
        return False


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _publica(conta: dict) -> dict:
    """A conta como a interface a vê: sem o hash da senha e sem os hashes dos códigos de recuperação."""
    publica = {k: v for k, v in conta.items() if k not in ("senha", "segundo_fator")}
    sf = conta.get("segundo_fator") or {}
    publica["segundo_fator"] = {"ativo": bool(sf.get("ativo")), "desde": sf.get("desde"),
                                "codigos_restantes": len(sf.get("recuperacao", []))}
    return publica


class Acesso(AcessoAvancado):
    ID = "SVC-IAM"

    def __init__(self, pasta=None, *, relogio=time.time, custo_scrypt: int = 15):
        self.pasta = Path(pasta) if pasta else None
        self.relogio = relogio
        self.custo = custo_scrypt
        self.simulado = self.pasta is None
        self._contas = ArquivoSelado(self.pasta / "contas.json" if self.pasta else None, "acesso-contas", VERSAO,
                                     {"contas": {}})
        self._sessoes = ArquivoSelado(self.pasta / "sessoes.json" if self.pasta else None, "acesso-sessoes", VERSAO,
                                      {"sessoes": {}})
        self.trilha = TrilhaAcesso(self.pasta / "trilha.jsonl" if self.pasta else None)
        self._chave_atestado = secrets.token_bytes(32)  # só deste processo: atestado não sobrevive a reinício
        self._nonces: set = set()
        self._seq_nonce = 0
        self._vista: dict[str, float] = {}  # sessão -> último uso ainda não persistido
        self._falso = _hash_senha("senha-que-ninguem-usa", self.custo)  # custo igual para usuário inexistente

    # ---- cadastro: leitura com falha fechada ---------------------------------------------
    def _ler_contas(self) -> dict:
        try:
            return self._contas.ver()["contas"]
        except ArquivoComprometido as erro:
            self._auditar("cadastro_comprometido", None, "negado", regra="IAM-07", motivo=str(erro))
            raise AcessoNegado("IAM-07", f"cadastro de contas comprometido: {erro}") from None

    def _ler_sessoes(self) -> dict:
        try:
            return self._sessoes.ver()["sessoes"]
        except ArquivoComprometido as erro:
            self._auditar("cadastro_comprometido", None, "negado", regra="IAM-07", motivo=str(erro))
            raise AcessoNegado("IAM-07", f"cadastro de sessões comprometido: {erro}") from None

    @contextlib.contextmanager
    def _tx(self, arquivo):
        """Transação num arquivo selado; integridade quebrada ou trava presa viram negação IAM-07 (falha fechada)."""
        try:
            with arquivo.transacao() as dados:
                yield dados
        except ArquivoComprometido as erro:
            self._auditar("cadastro_comprometido", None, "negado", regra="IAM-07", motivo=str(erro))
            raise AcessoNegado("IAM-07", f"cadastro comprometido: {erro}") from None
        except TravaOcupada as erro:
            raise AcessoNegado("IAM-07", f"cadastro em uso por outro processo, tente de novo: {erro}") from None

    def vazio(self) -> bool:
        return not self._ler_contas()

    def contas(self) -> list[dict]:
        """Contas sem o hash da senha nem os hashes dos códigos de recuperação (para a TUI e a CLI)."""
        return [_publica(c) for c in self._ler_contas().values()]

    def conta(self, usuario: str) -> dict | None:
        c = self._ler_contas().get(usuario)
        return None if c is None else _publica(c)

    def registrar(self, evento: str, ator: str | None, resultado: str = "ok", **campos) -> None:
        """Registro na trilha de acesso feito por outro serviço (ex.: decisões aceitas e negadas pelo SVC-POL)."""
        self._auditar(evento, ator, resultado, **campos)

    def _auditar(self, evento, ator, resultado="ok", **campos) -> None:
        try:
            self.trilha.registrar(self.relogio(), evento, ator=ator, resultado=resultado, **campos)
        except Exception:  # a trilha nunca derruba a operação que ela registra; a verificação acusa a falta
            pass

    # ---- contas ----------------------------------------------------------------------------
    def _validar_senha(self, usuario: str, senha: str) -> None:
        if not isinstance(senha, str) or len(senha) < MIN_SENHA:
            raise AcessoNegado("IAM-02", f"a senha precisa de pelo menos {MIN_SENHA} caracteres")
        if usuario.lower() in senha.lower() or senha.lower() in SENHAS_PROIBIDAS or len(set(senha)) < 5:
            raise AcessoNegado("IAM-02", "senha óbvia demais: não use o nome de usuário nem sequências repetidas")

    def _validar_papeis(self, papeis) -> tuple:
        papeis = tuple(dict.fromkeys(papeis))
        desconhecidos = [p for p in papeis if p not in permissoes.papeis_humanos()]
        if desconhecidos:
            raise AcessoNegado("IAM-05", f"papéis desconhecidos: {desconhecidos}")
        par = permissoes.incompatibilidade(papeis)
        if par:
            raise AcessoNegado("IAM-06", f"a mesma conta não acumula {' e '.join(sorted(par))}")
        return papeis

    @staticmethod
    def _validar_usuario(usuario) -> str:
        if not isinstance(usuario, str) or not (3 <= len(usuario) <= 32) or not usuario.replace("_", "").replace(".", "").isalnum() \
                or usuario != usuario.lower():
            raise AcessoNegado("IAM-02", "usuário: de 3 a 32 letras minúsculas, números, ponto ou sublinhado")
        return usuario

    def iniciar(self, usuario: str, nome: str, senha: str) -> dict:
        """IAM-01: cria o primeiro administrador; só funciona com o cadastro vazio."""
        self._validar_usuario(usuario)
        self._validar_senha(usuario, senha)
        with self._tx(self._contas) as dados:
            if dados["contas"]:
                self._auditar("bootstrap", usuario, "negado", regra="IAM-01")
                raise AcessoNegado("IAM-01", "já existe conta cadastrada: o primeiro administrador só é criado uma vez")
            dados["contas"][usuario] = self._nova(usuario, nome, [PAPEL_ADM], senha, None, None, trocar=False)
        self._auditar("bootstrap", usuario, alvo=usuario, papeis=[PAPEL_ADM], regra="IAM-01")
        return self.conta(usuario)

    def _nova(self, usuario, nome, papeis, senha, pessoa_erp, cargo, trocar) -> dict:
        return {"usuario": usuario, "nome": nome, "papeis": list(papeis), "pessoa_erp": pessoa_erp, "cargo": cargo,
                "estado": "ativa", "senha": _hash_senha(senha, self.custo) if senha else None, "trocar_senha": trocar,
                "falhas": 0, "bloqueada_ate": None, "criada_em": round(self.relogio(), 3)}

    def criar_conta(self, ator: Sessao, usuario: str, nome: str, senha: str, papeis, *, pessoa_erp=None,
                    cargo=None, trocar_senha=True) -> dict:
        self.exigir(ator, "PERM-IAM-USUARIOS")
        self._validar_usuario(usuario)
        self._validar_senha(usuario, senha)
        papeis = self._validar_papeis(papeis)
        if cargo is not None and cargo not in permissoes.cargos():
            raise AcessoNegado("IAM-05", f"cargo desconhecido: {cargo} (use {', '.join(permissoes.cargos())})")
        with self._tx(self._contas) as dados:
            if usuario in dados["contas"]:
                raise AcessoNegado("IAM-02", f"o usuário {usuario} já existe")
            dados["contas"][usuario] = self._nova(usuario, nome, papeis, senha, pessoa_erp, cargo, trocar_senha)
        self._auditar("conta_criada", ator.usuario, alvo=usuario, papeis=list(papeis), cargo=cargo, pessoa_erp=pessoa_erp)
        return self.conta(usuario)

    def _alterar(self, ator: Sessao, usuario: str, permissao: str, evento: str, mudar, **campos) -> dict:
        self.exigir(ator, permissao)
        with self._tx(self._contas) as dados:
            conta = dados["contas"].get(usuario)
            if conta is None:
                raise AcessoNegado("IAM-05", f"conta inexistente: {usuario}")
            antes = dict(conta)
            mudar(conta)
            administradores = [c for c in dados["contas"].values() if PAPEL_ADM in c["papeis"] and c["estado"] == "ativa"]
            era_adm = PAPEL_ADM in antes["papeis"] and antes["estado"] == "ativa"
            if era_adm and not administradores:
                self._auditar(evento, ator.usuario, "negado", alvo=usuario, regra="IAM-06")
                raise AcessoNegado("IAM-06", "é o último administrador ativo: a alteração deixaria o sistema sem administração")
        if conta["estado"] != "ativa":
            self._revogar_de(usuario, ator.usuario, f"conta {conta['estado']}")
        self._auditar(evento, ator.usuario, alvo=usuario, **campos)
        return self.conta(usuario)

    def atribuir_papeis(self, ator: Sessao, usuario: str, papeis) -> dict:
        papeis = self._validar_papeis(papeis)
        return self._alterar(ator, usuario, "PERM-IAM-PAPEIS", "papeis_alterados",
                             lambda c: c.update(papeis=list(papeis)), papeis=list(papeis))

    def definir_vinculo(self, ator: Sessao, usuario: str, *, pessoa_erp=None, cargo=None) -> dict:
        """Liga a conta à pessoa do ERP e ao cargo: é o que a segregação de funções e a POL-02 conferem."""
        if cargo is not None and cargo not in permissoes.cargos():
            raise AcessoNegado("IAM-05", f"cargo desconhecido: {cargo}")
        return self._alterar(ator, usuario, "PERM-IAM-PAPEIS", "vinculo_alterado",
                             lambda c: c.update(pessoa_erp=pessoa_erp, cargo=cargo), pessoa_erp=pessoa_erp, cargo=cargo)

    def bloquear(self, ator: Sessao, usuario: str) -> dict:
        return self._alterar(ator, usuario, "PERM-IAM-USUARIOS", "conta_bloqueada",
                             lambda c: c.update(estado="bloqueada", bloqueada_ate=None))

    def desbloquear(self, ator: Sessao, usuario: str) -> dict:
        return self._alterar(ator, usuario, "PERM-IAM-USUARIOS", "conta_desbloqueada",
                             lambda c: c.update(estado="ativa", bloqueada_ate=None, falhas=0))

    def desativar(self, ator: Sessao, usuario: str) -> dict:
        return self._alterar(ator, usuario, "PERM-IAM-USUARIOS", "conta_desativada", lambda c: c.update(estado="desativada"))

    def redefinir_senha(self, ator: Sessao, usuario: str, nova: str) -> dict:
        """Senha temporária definida pelo administrador: a pessoa troca na primeira entrada (IAM-02)."""
        self._validar_senha(usuario, nova)
        conta = self._alterar(ator, usuario, "PERM-IAM-USUARIOS", "senha_redefinida",
                              lambda c: c.update(senha=_hash_senha(nova, self.custo), trocar_senha=True, falhas=0,
                                                 bloqueada_ate=None))
        self._revogar_de(usuario, ator.usuario, "senha redefinida")
        return conta

    def trocar_senha(self, sessao: Sessao, atual: str, nova: str) -> None:
        self._validar_senha(sessao.usuario, nova)
        with self._tx(self._contas) as dados:
            conta = dados["contas"][sessao.usuario]
            if not conta["senha"] or not _confere_senha(atual, conta["senha"]):
                self._auditar("senha_trocada", sessao.usuario, "negado", regra="IAM-02")
                raise AcessoNegado("IAM-02", "senha atual não confere")
            if atual == nova:
                raise AcessoNegado("IAM-02", "a senha nova precisa ser diferente da atual")
            conta.update(senha=_hash_senha(nova, self.custo), trocar_senha=False)
        self._auditar("senha_trocada", sessao.usuario)

    # ---- entrada e sessões ---------------------------------------------------------------
    def autenticar(self, usuario: str, senha: str, origem: str = "") -> tuple[Sessao, str]:
        """Devolve a sessão e o token (entregue uma única vez; o cadastro guarda só o hash dele)."""
        agora = self.relogio()
        negacao = None  # (regra, mensagem ao usuário, motivo na trilha): a transação grava as falhas antes de negar
        with self._transacao_contas() as dados:
            conta = dados["contas"].get(usuario) if isinstance(usuario, str) else None
            if conta is None or not conta.get("senha"):
                _confere_senha(senha if isinstance(senha, str) else "", self._falso)  # mesmo custo, mesma resposta
                negacao = ("IAM-03", "usuário ou senha inválidos", "usuário inexistente")
            elif conta["estado"] == "desativada":
                negacao = ("IAM-04", "usuário ou senha inválidos", "conta desativada")
            elif conta["estado"] == "bloqueada" and conta["bloqueada_ate"] is None:
                negacao = ("IAM-03", "conta bloqueada: procure o administrador de acesso",
                           "conta bloqueada pelo administrador")
            elif conta["bloqueada_ate"] is not None and agora < conta["bloqueada_ate"]:
                negacao = ("IAM-03", f"conta bloqueada por tentativas: tente de novo em "
                                     f"{int((conta['bloqueada_ate'] - agora) // 60) + 1} min", "conta em bloqueio temporário")
            elif not isinstance(senha, str) or not _confere_senha(senha, conta["senha"]):
                conta["falhas"] += 1
                if conta["falhas"] >= MAX_FALHAS:
                    conta.update(estado="bloqueada", bloqueada_ate=agora + BLOQUEIO_S, falhas=0)
                    negacao = ("IAM-03", f"conta bloqueada por {MAX_FALHAS} senhas erradas: tente de novo em "
                                         f"{BLOQUEIO_S // 60} min", "senha errada (conta bloqueada por 15 min)")
                else:
                    negacao = ("IAM-03", "usuário ou senha inválidos", "senha errada")
            else:
                conta.update(falhas=0, bloqueada_ate=None, estado="ativa")
                copia = dict(conta)
        if negacao:
            regra, mensagem, motivo = negacao
            self._auditar("entrada", str(usuario)[:64], "negado", regra=regra, motivo=motivo, origem=origem)
            raise AcessoNegado(regra, mensagem)
        if (copia.get("segundo_fator") or {}).get("ativo"):  # IAM-08: a senha só abre a pré-sessão do código
            desafio, expira = self._abrir_pre_sessao(usuario, agora, origem)
            self._auditar("entrada", usuario, "pendente", regra="IAM-08", motivo="segundo fator pendente", origem=origem)
            raise SegundoFatorPendente(desafio, expira)
        return self._abrir_sessao(usuario, copia, agora, origem)

    def _abrir_sessao(self, usuario: str, conta: dict, agora: float, origem: str) -> tuple["Sessao", str]:
        token = secrets.token_urlsafe(32)
        sid = "S-" + self._id_sessao()
        escopo = conta.get("empresas") or []
        registro = {"id": sid, "usuario": usuario, "hash": _sha(token), "csrf": secrets.token_urlsafe(18),
                    "criada_em": round(agora, 3), "vista_em": round(agora, 3), "expira_em": round(agora + TTL_SESSAO_S, 3),
                    "origem": str(origem)[:80], "revogada": None}
        if len(escopo) == 1:  # uma empresa só no escopo: ela já é a ativa (IAM-09)
            registro["empresa"] = escopo[0]
        with self._tx(self._sessoes) as dados:
            for antigo in [k for k, s in dados["sessoes"].items() if s["expira_em"] < agora - 24 * 3600]:
                del dados["sessoes"][antigo]  # limpeza: expiradas há mais de um dia
            dados["sessoes"][sid] = registro
        self._auditar("entrada", usuario, sessao=sid, origem=origem)
        return self._sessao(registro, conta), token

    def _transacao_contas(self):
        try:
            self._contas.ler()
        except ArquivoComprometido as erro:
            self._auditar("cadastro_comprometido", None, "negado", regra="IAM-07", motivo=str(erro))
            raise AcessoNegado("IAM-07", f"cadastro de contas comprometido: {erro}") from None
        return self._tx(self._contas)

    def _sessao(self, registro: dict, conta: dict) -> Sessao:
        return Sessao(registro["id"], conta["usuario"], conta["nome"], tuple(conta["papeis"]),
                      permissoes.permissoes_de(conta["papeis"]), conta.get("pessoa_erp"), conta.get("cargo"),
                      registro["csrf"], registro["expira_em"], bool(conta.get("trocar_senha")),
                      self.exige_2fa(conta), registro.get("empresa"), tuple(conta.get("empresas") or ()))

    def sessao(self, token: str | None) -> Sessao | None:
        """Sessão viva do token, ou None (IAM-04). Relê os cadastros: revogação e bloqueio valem na hora."""
        if not isinstance(token, str) or not token:
            return None
        alvo = _sha(token)
        registro = next((s for s in self._ler_sessoes().values() if hmac.compare_digest(s["hash"], alvo)), None)
        return self._viva(registro)

    def sessao_por_id(self, sid: str) -> Sessao | None:
        return self._viva(self._ler_sessoes().get(sid))

    def _viva(self, registro) -> Sessao | None:
        if registro is None or registro["revogada"] or registro.get("pre2fa"):  # pré-sessão só confirma o código
            return None
        agora = self.relogio()
        vista = max(registro["vista_em"], self._vista.get(registro["id"], 0))
        if agora >= registro["expira_em"] or (not self.simulado and agora - vista > INATIVIDADE_S):
            return None
        conta = self._ler_contas().get(registro["usuario"])
        if conta is None or conta["estado"] != "ativa":
            return None
        self._vista[registro["id"]] = agora
        if agora - registro["vista_em"] > PERSISTIR_VISTA_S and not self.simulado:
            with self._tx(self._sessoes) as dados:
                if registro["id"] in dados["sessoes"]:
                    dados["sessoes"][registro["id"]]["vista_em"] = round(agora, 3)
        return self._sessao(registro, conta)

    def exigir(self, sessao: Sessao | None, permissao: str) -> None:
        """IAM-05: negado por padrão."""
        if sessao is None:
            raise AcessoNegado("IAM-04", "sessão ausente, expirada ou revogada")
        atual = self.sessao_por_id(sessao.id)  # relê o cadastro: sessão revogada ou conta bloqueada não age mais,
        if atual is None:                      # mesmo que alguém ainda guarde o objeto em memória
            self._auditar("permissao", sessao.usuario, "negado", regra="IAM-04", permissao=permissao,
                          motivo="sessão encerrada")
            raise AcessoNegado("IAM-04", "sessão expirada ou revogada")
        sessao = atual                         # e valem os papéis de agora, não os de quando entrou
        if sessao.pendente_2fa:
            self._auditar("permissao", sessao.usuario, "negado", regra="IAM-08", permissao=permissao,
                          motivo="segundo fator exigido pela política do cadastro")
            raise AcessoNegado("IAM-08", "a política do cadastro exige o segundo fator para a sua conta: ative-o "
                                         "antes de continuar")
        self._conferir_empresa(sessao, permissao)
        if not sessao.pode(permissao):
            self._auditar("permissao", sessao.usuario, "negado", regra="IAM-05", permissao=permissao)
            titulo = permissoes.catalogo().get(permissao, {}).get("titulo", permissao)
            raise AcessoNegado("IAM-05", f"{sessao.usuario} não tem a permissão {permissao} ({titulo})")

    def sessoes(self, ator: Sessao | None = None) -> list[dict]:
        if ator is not None:
            self.exigir(ator, "PERM-IAM-SESSOES")
        agora = self.relogio()
        return [{"id": s["id"], "usuario": s["usuario"], "criada_em": s["criada_em"], "vista_em": s["vista_em"],
                 "expira_em": s["expira_em"], "origem": s["origem"], "revogada": s["revogada"],
                 "pre2fa": bool(s.get("pre2fa")), "empresa": s.get("empresa"),
                 "viva": not s["revogada"] and agora < s["expira_em"] and agora - s["vista_em"] <= INATIVIDADE_S}
                for s in self._ler_sessoes().values()]

    def sair(self, sessao: Sessao) -> None:
        self._revogar([sessao.id], "saída do usuário")
        self._auditar("saida", sessao.usuario, sessao=sessao.id)

    def revogar(self, ator: Sessao, sid: str) -> None:
        self.exigir(ator, "PERM-IAM-SESSOES")
        if sid not in self._ler_sessoes():
            raise AcessoNegado("IAM-04", f"sessão inexistente: {sid}")
        self._revogar([sid], f"revogada por {ator.usuario}")
        self._auditar("sessao_revogada", ator.usuario, sessao=sid)

    def revogar_usuario(self, ator: Sessao, usuario: str) -> list[str]:
        """Revoga todas as sessões vivas de um usuário de uma vez (menos a do próprio ator); devolve os ids."""
        self.exigir(ator, "PERM-IAM-SESSOES")
        ids = [s["id"] for s in self._ler_sessoes().values()
               if s["usuario"] == usuario and not s["revogada"] and s["id"] != ator.id]
        if ids:
            self._revogar(ids, f"revogada por {ator.usuario}")
            self._auditar("sessoes_revogadas", ator.usuario, alvo=usuario, sessoes=ids, motivo="revogação pelo administrador")
        return ids

    def _revogar_de(self, usuario: str, ator: str, motivo: str) -> None:
        ids = [s["id"] for s in self._ler_sessoes().values() if s["usuario"] == usuario and not s["revogada"]]
        if ids:
            self._revogar(ids, motivo)
            self._auditar("sessoes_revogadas", ator, alvo=usuario, sessoes=ids, motivo=motivo)

    def _revogar(self, ids, motivo: str) -> None:
        with self._tx(self._sessoes) as dados:
            for sid in ids:
                if sid in dados["sessoes"] and not dados["sessoes"][sid]["revogada"]:
                    dados["sessoes"][sid]["revogada"] = motivo

    # ---- atestado de decisão (POL-09) ----------------------------------------------------
    def _token_atestado(self, pessoa, sessao, nonce, ticket, veto, decisao, corpo) -> str:
        base = "|".join(str(x) for x in (ticket, veto, decisao, corpo, pessoa, sessao, nonce))
        return hmac.new(self._chave_atestado, base.encode("utf-8"), hashlib.sha256).hexdigest()

    def atestar(self, sessao: Sessao, *, ticket: str, veto: str, decisao: str, corpo: str) -> dict:
        """Prova de que esta sessão, nesta execução, decidiu isto sobre este veto."""
        self.exigir(sessao, "PERM-APR-DECIDIR")
        self._seq_nonce += 1
        nonce = f"n-{self._seq_nonce:04d}" if self.simulado else secrets.token_hex(8)
        return {"pessoa": sessao.usuario, "sessao": sessao.id, "nonce": nonce,
                "token": self._token_atestado(sessao.usuario, sessao.id, nonce, ticket, veto, decisao, corpo)}

    def verificar_atestado(self, atestado, *, ticket: str, veto: str, decisao: str, corpo: str) -> Sessao:
        """Sessão de quem decidiu, ou `AcessoNegado` com a regra POL-09."""
        if not isinstance(atestado, dict) or not all(isinstance(atestado.get(k), str) for k in ("pessoa", "sessao", "nonce", "token")):
            raise AcessoNegado("POL-09", "decisão sem atestado de sessão de uma pessoa autenticada")
        esperado = self._token_atestado(atestado["pessoa"], atestado["sessao"], atestado["nonce"], ticket, veto, decisao, corpo)
        if not hmac.compare_digest(esperado, atestado["token"]):
            raise AcessoNegado("POL-09", "atestado não confere com o ticket, o veto, a decisão ou a pessoa")
        if (atestado["sessao"], atestado["nonce"]) in self._nonces:
            raise AcessoNegado("POL-09", "atestado já usado (replay)")
        sessao = self.sessao_por_id(atestado["sessao"])
        if sessao is None or sessao.usuario != atestado["pessoa"]:
            raise AcessoNegado("POL-09", "a sessão do atestado está expirada, revogada ou é de outra pessoa")
        if not sessao.pode("PERM-APR-DECIDIR"):
            raise AcessoNegado("POL-09", f"{sessao.usuario} não tem o papel de aprovador")
        if sessao.pendente_2fa:
            raise AcessoNegado("POL-09", f"{sessao.usuario} ainda não ativou o segundo fator exigido pela política")
        self._nonces.add((atestado["sessao"], atestado["nonce"]))
        return sessao

    # ---- acesso simulado e contas de demonstração ------------------------------------------
    @classmethod
    def simulado_com(cls, contas: dict, relogio) -> "Acesso":
        """Contas em memória, sem senha, cada uma já com sessão (`SIM-<usuario>`): cenários em lote.

        `contas`: usuario -> {nome?, papeis, pessoa_erp?, cargo?}. `relogio` é o tempo lógico do barramento.
        """
        a = cls(None, relogio=relogio, custo_scrypt=10)
        with a._contas.transacao() as dados:
            for usuario, c in contas.items():
                papeis = a._validar_papeis(c["papeis"])
                dados["contas"][usuario] = a._nova(usuario, c.get("nome", usuario), papeis, None, c.get("pessoa_erp"),
                                                   c.get("cargo"), trocar=False)
        with a._sessoes.transacao() as dados:
            for usuario in contas:
                sid = f"SIM-{usuario}"
                dados["sessoes"][sid] = {"id": sid, "usuario": usuario, "hash": _sha(sid), "csrf": "", "criada_em": 0,
                                         "vista_em": 0, "expira_em": float("inf"), "origem": "simulação", "revogada": None}
        return a

    def sessao_simulada(self, usuario: str) -> Sessao | None:
        registro = self._ler_sessoes().get(f"SIM-{usuario}")
        if registro is None or registro["revogada"]:
            return None
        conta = self._ler_contas().get(usuario)
        return None if conta is None or conta["estado"] != "ativa" else self._sessao(registro, conta)

    def revogar_simulada(self, usuario: str) -> None:
        self._revogar([f"SIM-{usuario}"], "revogada no cenário")


# Contas de demonstração (`acesso demo`, `serve --demo`): uma por papel, mais as pessoas do ERP da
# empresa fictícia. As senhas são públicas, documentadas e só servem para avaliar o sistema.
SENHA_DEMO = "Demonstracao-SMA-2026"
CONTAS_DEMO = (
    # usuario, nome, papeis, pessoa_erp, cargo
    ("admin", "Administração de Acesso", ("ROLE-ADM",), None, None),
    ("operador", "Operação da Plataforma", ("ROLE-OPE",), None, None),
    ("auditor", "Auditoria Interna", ("ROLE-AUD",), None, None),
    ("controller", "Controller", ("ROLE-APR", "ROLE-SOL"), None, "controller"),
    ("elisa", "Elisa Prado", ("ROLE-SOL", "ROLE-APR"), "elisa", "diretor"),
    ("carla", "Carla Mendes", ("ROLE-APR",), "carla", "gerente"),
    ("diego", "Diego Rocha", ("ROLE-APR",), "diego", "gerente"),
    ("ana", "Ana Lima", ("ROLE-SOL", "ROLE-APR"), "ana", "analista"),
    ("bruno", "Bruno Souza", ("ROLE-SOL",), "bruno", "analista"),
    ("avaliador", "Avaliação (operação, pedidos, aprovação e auditoria)",
     ("ROLE-OPE", "ROLE-SOL", "ROLE-APR", "ROLE-AUD"), None, "controller"),
)


def criar_demo(pasta, custo_scrypt: int = 15) -> Acesso:
    """Cria as contas de demonstração numa pasta vazia; se já houver cadastro, só o abre."""
    a = Acesso(pasta, custo_scrypt=custo_scrypt)
    if not a.vazio():
        return a
    a.iniciar("admin", "Administração de Acesso", SENHA_DEMO)
    adm, _ = a.autenticar("admin", SENHA_DEMO, "demo")
    for usuario, nome, papeis, pessoa, cargo in CONTAS_DEMO[1:]:
        a.criar_conta(adm, usuario, nome, SENHA_DEMO, papeis, pessoa_erp=pessoa, cargo=cargo, trocar_senha=False)
    a.sair(adm)
    return a

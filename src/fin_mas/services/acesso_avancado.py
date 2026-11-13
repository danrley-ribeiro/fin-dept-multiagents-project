"""SVC-IAM, acesso avançado (DSM4, ADR-012): segundo fator, política do cadastro, delegações,
empresas e segredos do cofre. É uma extensão (mixin) da classe `Acesso` de `services/iam.py`.

Regras novas (toda negação vai para a trilha de acesso com a regra):

- IAM-08  segundo fator (TOTP, RFC 6238): com ele ativo, a senha certa só abre uma **pré-sessão**
          de 5 minutos que não serve para nada além de confirmar o código; o código vale uma vez
          (anti-replay pelo passo), dentro de ±30 s; cada código de recuperação vale uma vez; cinco
          códigos errados derrubam a pré-sessão. Quando a política do cadastro exige o segundo
          fator para um papel da conta (`exigir_2fa_para`), a conta sem ele só consegue ativá-lo;
- IAM-09  empresa (multiempresa): com empresas cadastradas, a sessão escolhe uma empresa ativa
          dentro do escopo da conta, e toda permissão que não é da administração do cadastro
          exige essa empresa ativa e no escopo;
- IAM-10  cofre: segredos só entram e saem sob `PERM-MOD-SEGREDOS`, com nome permitido, e o valor
          nunca é devolvido à interface (só "existe");
- POL-11  delegação (criada aqui, conferida pelo SVC-POL na decisão): um aprovador delega a outra
          conta aprovadora, com prazo, teto de valor e escopo (uma competência ou uma solicitação);
          quem recebeu não delega de novo (sem subdelegação); expira sozinha e é revogável.
"""
import itertools
import math

from fin_mas.core import permissoes
from fin_mas.services import totp
from fin_mas.services.cofre import Cofre, SegredoInvalido

PRE2FA_S = 5 * 60
MAX_FALHAS_2FA = 5
POLITICA_PADRAO = {"exigir_2fa_para": [], "escalonamento_percentual": None}
PAPEIS_2FA = ("ROLE-ADM", "ROLE-APR")
# permissões da administração do cadastro: valem fora de qualquer empresa (o cadastro é um só)
PERMISSOES_GLOBAIS = {"PERM-IAM-USUARIOS", "PERM-IAM-PAPEIS", "PERM-IAM-SESSOES", "PERM-IAM-POLITICA",
                      "PERM-IAM-EMPRESAS", "PERM-MOD-SEGREDOS"}
PREFIXOS_INTERFACE = ("llm:", "conector:")  # segredos que a interface pode definir e remover (TOTP é interno)


def _negado(regra, motivo):
    from fin_mas.services.iam import AcessoNegado
    return AcessoNegado(regra, motivo)


class AcessoAvancado:
    """Métodos do acesso avançado; dependem de `_tx`, `_contas`, `_sessoes`, `_auditar`, `exigir` de `Acesso`."""

    def _id_sessao(self) -> str:
        """Id de sessão: aleatório; no acesso simulado, sequencial (o trace do cenário se repete byte a byte)."""
        import secrets
        if not self.simulado:
            return secrets.token_hex(6)
        self._seq_sessao = getattr(self, "_seq_sessao", 0) + 1
        return f"{self._seq_sessao:012d}"

    # ---- política do cadastro ------------------------------------------------------------
    def politica(self) -> dict:
        return {**POLITICA_PADRAO, **(self._contas.ver().get("politica") or {})}

    def definir_politica(self, ator, **campos) -> dict:
        self.exigir(ator, "PERM-IAM-POLITICA")
        novos = {}
        if "exigir_2fa_para" in campos:
            papeis = list(dict.fromkeys(campos["exigir_2fa_para"] or []))
            fora = [p for p in papeis if p not in PAPEIS_2FA]
            if fora:
                raise _negado("IAM-08", f"o segundo fator obrigatório vale para {', '.join(PAPEIS_2FA)}; não para {fora}")
            novos["exigir_2fa_para"] = papeis
        if "escalonamento_percentual" in campos:
            pct = campos["escalonamento_percentual"]
            if pct is not None and (not isinstance(pct, int) or isinstance(pct, bool) or not 10 <= pct <= 90):
                raise _negado("POL-14", "escalonamento: percentual inteiro do prazo entre 10 e 90 (ou nenhum)")
            novos["escalonamento_percentual"] = pct
        desconhecidos = set(campos) - set(POLITICA_PADRAO)
        if desconhecidos:
            raise _negado("IAM-05", f"campos desconhecidos na política do cadastro: {sorted(desconhecidos)}")
        with self._tx(self._contas) as dados:
            dados["politica"] = {**POLITICA_PADRAO, **(dados.get("politica") or {}), **novos}
            politica = dict(dados["politica"])
        self._auditar("politica_alterada", ator.usuario, **novos)
        return politica

    def exige_2fa(self, conta: dict) -> bool:
        exigidos = set(self.politica()["exigir_2fa_para"])
        return bool(exigidos & set(conta.get("papeis", []))) and not (conta.get("segundo_fator") or {}).get("ativo")

    # ---- cofre ----------------------------------------------------------------------------
    @property
    def cofre(self) -> Cofre:
        if getattr(self, "_cofre", None) is None:
            self._cofre = Cofre.do_cadastro(self.pasta, relogio=self.relogio)
        return self._cofre

    def definir_segredo(self, ator, nome: str, valor: str) -> dict:
        self.exigir(ator, "PERM-MOD-SEGREDOS")
        if not isinstance(nome, str) or not nome.startswith(PREFIXOS_INTERFACE):
            self._auditar("segredo_definido", ator.usuario, "negado", regra="IAM-10", nome=str(nome)[:64])
            raise _negado("IAM-10", f"pela interface só se definem segredos {' ou '.join(PREFIXOS_INTERFACE)}…")
        try:
            self.cofre.guardar(nome, valor, ator.usuario)
        except SegredoInvalido as erro:
            raise _negado("IAM-10", str(erro)) from None
        self._auditar("segredo_definido", ator.usuario, nome=nome, regra="IAM-10")
        return {"nome": nome, "existe": True}

    def remover_segredo(self, ator, nome: str) -> dict:
        self.exigir(ator, "PERM-MOD-SEGREDOS")
        if not isinstance(nome, str) or not nome.startswith(PREFIXOS_INTERFACE):
            raise _negado("IAM-10", f"pela interface só se removem segredos {' ou '.join(PREFIXOS_INTERFACE)}…")
        removido = self.cofre.remover(nome, ator.usuario)
        self._auditar("segredo_removido", ator.usuario, nome=nome, removido=removido, regra="IAM-10")
        return {"nome": nome, "existe": False, "removido": removido}

    def segredos(self, ator) -> list[dict]:
        """Nomes dos segredos da interface (nunca o valor)."""
        self.exigir(ator, "PERM-MOD-SEGREDOS")
        return [s for s in self.cofre.nomes() if s["nome"].startswith(PREFIXOS_INTERFACE)]

    # ---- segundo fator (IAM-08) -------------------------------------------------------------
    def iniciar_2fa(self, sessao) -> dict:
        """Gera o segredo (pendente até a confirmação) e o devolve **uma vez**, com a URI otpauth://."""
        sessao = self._exigir_viva(sessao)
        conta = self._ler_contas()[sessao.usuario]
        if (conta.get("segundo_fator") or {}).get("ativo"):
            raise _negado("IAM-08", "o segundo fator já está ativo: desative antes de cadastrar outro aparelho")
        segredo = totp.novo_segredo()
        self.cofre.guardar(f"totp-pendente:{sessao.usuario}", segredo, sessao.usuario)
        self._auditar("2fa_iniciado", sessao.usuario, regra="IAM-08")
        return {"segredo": segredo, "uri": totp.uri(segredo, sessao.usuario)}

    def confirmar_2fa(self, sessao, codigo: str) -> list[str]:
        """Confere o primeiro código e ativa; devolve os códigos de recuperação (mostrados uma única vez)."""
        sessao = self._exigir_viva(sessao)
        segredo = self.cofre.ler(f"totp-pendente:{sessao.usuario}")
        if segredo is None:
            raise _negado("IAM-08", "nenhum cadastro de segundo fator em andamento: comece pela ativação")
        aceito = totp.verificar(segredo, codigo, self.relogio())
        if aceito is None:
            self._auditar("2fa_ativado", sessao.usuario, "negado", regra="IAM-08", motivo="código inválido")
            raise _negado("IAM-08", "código não confere: confira o relógio do aparelho e digite o código atual")
        codigos = totp.codigos_recuperacao()
        self.cofre.guardar(f"totp:{sessao.usuario}", segredo, sessao.usuario)
        self.cofre.remover(f"totp-pendente:{sessao.usuario}", sessao.usuario)
        with self._tx(self._contas) as dados:
            dados["contas"][sessao.usuario]["segundo_fator"] = {
                "ativo": True, "desde": round(self.relogio(), 3), "ultimo_passo": aceito,
                "recuperacao": [totp.hash_recuperacao(c) for c in codigos]}
        self._auditar("2fa_ativado", sessao.usuario, regra="IAM-08")
        return codigos

    def desativar_2fa(self, sessao, codigo: str) -> None:
        """A própria pessoa desativa, confirmando com um código válido (TOTP ou recuperação)."""
        sessao = self._exigir_viva(sessao)
        with self._tx(self._contas) as dados:
            conta = dados["contas"][sessao.usuario]
            if not (conta.get("segundo_fator") or {}).get("ativo"):
                raise _negado("IAM-08", "o segundo fator não está ativo")
            motivo = self._conferir_codigo(conta, codigo)
            if motivo is None:
                conta["segundo_fator"] = {"ativo": False}
        if motivo is not None:
            self._auditar("2fa_desativado", sessao.usuario, "negado", regra="IAM-08", motivo=motivo)
            raise _negado("IAM-08", f"desativação recusada: {motivo}")
        self.cofre.remover(f"totp:{sessao.usuario}", sessao.usuario)
        self._auditar("2fa_desativado", sessao.usuario, regra="IAM-08")

    def redefinir_2fa(self, ator, usuario: str) -> dict:
        """Aparelho perdido e sem códigos: o administrador desliga o segundo fator; as sessões da conta caem."""
        conta = self._alterar(ator, usuario, "PERM-IAM-USUARIOS", "2fa_redefinido",
                              lambda c: c.update(segundo_fator={"ativo": False}), regra="IAM-08")
        self.cofre.remover(f"totp:{usuario}", ator.usuario)
        self._revogar_de(usuario, ator.usuario, "segundo fator redefinido")
        return conta

    def _conferir_codigo(self, conta: dict, codigo) -> str | None:
        """Motivo da recusa, ou None. Altera `conta` (último passo, código de recuperação usado): chamar em transação."""
        sf = conta.get("segundo_fator") or {}
        if not isinstance(codigo, str) or not codigo.strip():
            return "código ausente"
        texto = codigo.strip().lower()
        if "-" in texto:  # código de recuperação: uso único
            alvo = totp.hash_recuperacao(texto)
            if alvo in sf.get("recuperacao", []):
                sf["recuperacao"] = [h for h in sf["recuperacao"] if h != alvo]
                return None
            return "código de recuperação inválido ou já usado"
        segredo = self.cofre.ler(f"totp:{conta['usuario']}")
        if segredo is None:
            return "segredo do segundo fator ausente no cofre (procure o administrador)"
        anterior = sf.get("ultimo_passo", -1)
        aceito = totp.verificar(segredo, texto, self.relogio(), ultimo_passo=anterior)
        if aceito is None:
            usado = totp.verificar(segredo, texto, self.relogio())
            return "código já usado (replay)" if usado is not None and usado <= anterior else \
                "código fora da janela de tempo ou inválido"
        sf["ultimo_passo"] = aceito
        return None

    def _abrir_pre_sessao(self, usuario: str, agora: float, origem: str) -> tuple[str, float]:
        import secrets
        from fin_mas.services.iam import _sha
        token = secrets.token_urlsafe(32)
        sid = "P-" + self._id_sessao()
        expira = round(agora + PRE2FA_S, 3)
        with self._tx(self._sessoes) as dados:
            dados["sessoes"][sid] = {"id": sid, "usuario": usuario, "hash": _sha(token), "csrf": "",
                                     "criada_em": round(agora, 3), "vista_em": round(agora, 3), "expira_em": expira,
                                     "origem": str(origem)[:80], "revogada": None, "pre2fa": True, "falhas": 0}
        return token, expira

    def confirmar_entrada(self, desafio: str, codigo: str, origem: str = ""):
        """Segunda etapa da entrada: código certo na pré-sessão viva abre a sessão de verdade (IAM-08)."""
        import hmac
        from fin_mas.services.iam import _sha
        agora = self.relogio()
        alvo = _sha(desafio) if isinstance(desafio, str) and desafio else None
        registro = next((s for s in self._ler_sessoes().values() if alvo and s.get("pre2fa")
                         and hmac.compare_digest(s["hash"], alvo)), None)
        if registro is None or registro["revogada"] or agora >= registro["expira_em"]:
            self._auditar("segundo_fator", None, "negado", regra="IAM-08", motivo="pré-sessão ausente ou expirada",
                          origem=origem)
            raise _negado("IAM-08", "pré-sessão ausente ou expirada: entre de novo com usuário e senha")
        usuario = registro["usuario"]
        with self._tx(self._contas) as dados:
            conta = dados["contas"].get(usuario)
            motivo = "conta inativa" if conta is None or conta["estado"] != "ativa" else self._conferir_codigo(conta, codigo)
            copia = dict(conta) if conta is not None else None
        if motivo is not None:
            with self._tx(self._sessoes) as dados:
                pre = dados["sessoes"].get(registro["id"])
                if pre is not None:
                    pre["falhas"] = pre.get("falhas", 0) + 1
                    if pre["falhas"] >= MAX_FALHAS_2FA:
                        pre["revogada"] = f"{MAX_FALHAS_2FA} códigos errados"
            self._auditar("segundo_fator", usuario, "negado", regra="IAM-08", motivo=motivo, origem=origem)
            raise _negado("IAM-08", motivo)
        self._revogar([registro["id"]], "segundo fator confirmado")
        self._auditar("segundo_fator", usuario, regra="IAM-08", origem=origem)
        return self._abrir_sessao(usuario, copia, agora, origem)

    def _exigir_viva(self, sessao):
        atual = self.sessao_por_id(sessao.id) if sessao is not None else None
        if atual is None:
            raise _negado("IAM-04", "sessão ausente, expirada ou revogada")
        return atual

    # ---- empresas (IAM-09) -------------------------------------------------------------------
    def empresas(self) -> dict:
        return dict(self._contas.ver().get("empresas") or {})

    def multiempresa(self) -> bool:
        return bool(self._contas.ver().get("empresas"))

    def criar_empresa(self, ator, empresa: str, nome: str, porte: str = "media") -> dict:
        from fin_mas.env.portes import PORTES
        self.exigir(ator, "PERM-IAM-EMPRESAS")
        self._validar_usuario(empresa)  # mesmo formato: vira o nome da pasta dados/<empresa>/
        if porte not in PORTES:
            raise _negado("IAM-09", f"porte desconhecido: {porte} (use {', '.join(PORTES)})")
        with self._tx(self._contas) as dados:
            empresas = dados.setdefault("empresas", {})
            if empresa in empresas:
                raise _negado("IAM-09", f"a empresa {empresa} já existe")
            empresas[empresa] = {"id": empresa, "nome": str(nome)[:120] or empresa, "porte": porte,
                                 "criada_em": round(self.relogio(), 3)}
            if not ator.empresas and len(empresas) == 1:  # a primeira empresa entra no escopo de quem a criou
                dados["contas"][ator.usuario]["empresas"] = [empresa]
            criada = dict(empresas[empresa])
        self._auditar("empresa_criada", ator.usuario, empresa=empresa, porte=porte, regra="IAM-09")
        return criada

    def definir_escopo(self, ator, usuario: str, empresas) -> dict:
        empresas = list(dict.fromkeys(empresas))
        conhecidas = self.empresas()
        fora = [e for e in empresas if e not in conhecidas]
        if fora:
            raise _negado("IAM-09", f"empresas inexistentes: {fora}")
        return self._alterar(ator, usuario, "PERM-IAM-EMPRESAS", "escopo_alterado",
                             lambda c: c.update(empresas=empresas), empresas=empresas, regra="IAM-09")

    def escolher_empresa(self, sessao, empresa: str):
        """Troca a empresa ativa da sessão; só dentro do escopo da conta (IAM-09)."""
        sessao = self._exigir_viva(sessao)
        if empresa not in sessao.empresas:
            self._auditar("empresa_escolhida", sessao.usuario, "negado", regra="IAM-09", empresa=str(empresa)[:40])
            raise _negado("IAM-09", f"{sessao.usuario} não tem acesso à empresa {empresa}")
        with self._tx(self._sessoes) as dados:
            dados["sessoes"][sessao.id]["empresa"] = empresa
        self._auditar("empresa_escolhida", sessao.usuario, empresa=empresa, sessao=sessao.id, regra="IAM-09")
        return self.sessao_por_id(sessao.id)

    def simular_empresas(self, escopos: dict, nomes: dict | None = None) -> None:
        """Só no acesso simulado (cenários em lote): empresas, escopo de cada conta e a empresa ativa de cada
        sessão `SIM-<usuario>` (a primeira do escopo)."""
        if not self.simulado:
            raise _negado("IAM-09", "empresas simuladas só existem no acesso simulado")
        with self._tx(self._contas) as dados:
            for empresa in sorted({e for lista in escopos.values() for e in lista}):
                dados.setdefault("empresas", {})[empresa] = {"id": empresa, "nome": (nomes or {}).get(empresa, empresa),
                                                             "porte": "media", "criada_em": 0}
            for usuario, lista in escopos.items():
                dados["contas"][usuario]["empresas"] = list(lista)
        with self._tx(self._sessoes) as dados:
            for usuario, lista in escopos.items():
                if f"SIM-{usuario}" in dados["sessoes"] and lista:
                    dados["sessoes"][f"SIM-{usuario}"]["empresa"] = lista[0]

    def _conferir_empresa(self, sessao, permissao: str) -> None:
        if permissao in PERMISSOES_GLOBAIS or not self.multiempresa():
            return
        if sessao.empresa is None or sessao.empresa not in sessao.empresas:
            self._auditar("permissao", sessao.usuario, "negado", regra="IAM-09", permissao=permissao,
                          empresa=sessao.empresa)
            raise _negado("IAM-09", "escolha uma empresa do seu escopo antes de continuar" if sessao.empresa is None
                          else f"{sessao.usuario} não tem mais acesso à empresa {sessao.empresa}")

    # ---- delegações (POL-11) -------------------------------------------------------------------
    def delegar(self, ator, para: str, *, ate: float, teto: int, competencia: str | None = None,
                solicitacao: str | None = None, via: str | None = None) -> dict:
        self.exigir(ator, "PERM-APR-DELEGAR")
        ator = self._exigir_viva(ator)

        def negar(motivo):
            self._auditar("delegacao_criada", ator.usuario, "negado", regra="POL-11", motivo=motivo, alvo=str(para)[:32])
            return _negado("POL-11", motivo)
        if via is not None:
            raise negar("sem subdelegação: quem recebeu uma delegação não a repassa")
        contas = self._ler_contas()
        alvo = contas.get(para)
        if para == ator.usuario:
            raise negar("ninguém delega a si mesmo")
        if alvo is None or alvo["estado"] != "ativa" or "PERM-APR-DECIDIR" not in permissoes.permissoes_de(alvo["papeis"]):
            raise negar(f"{para} não é uma conta aprovadora ativa (só aprovadores recebem delegação)")
        if (competencia is None) == (solicitacao is None):
            raise negar("escopo: informe uma competência (AAAA-MM) ou uma solicitação (SOL-…), só uma")
        if competencia is not None and not (isinstance(competencia, str) and len(competencia) == 7 and competencia[4] == "-"):
            raise negar("competência no formato AAAA-MM")
        if not isinstance(teto, int) or isinstance(teto, bool) or teto <= 0:
            raise negar("teto: valor em centavos maior que zero")
        agora = self.relogio()
        if not isinstance(ate, (int, float)) or not math.isfinite(ate) or ate <= agora:
            raise negar("prazo: a delegação precisa terminar no futuro")
        if self.multiempresa() and ator.empresa not in (alvo.get("empresas") or []):
            raise negar(f"{para} não tem acesso à empresa {ator.empresa} (IAM-09)")
        escopo = {"competencia": competencia} if competencia else {"solicitacao": solicitacao}
        with self._tx(self._contas) as dados:
            delegacoes = dados.setdefault("delegacoes", {})
            numero = next(n for n in itertools.count(len(delegacoes) + 1) if f"DLG-{n:03d}" not in delegacoes)
            did = f"DLG-{numero:03d}"
            delegacoes[did] = {"id": did, "de": ator.usuario, "para": para, "ate": ate, "teto": teto, "escopo": escopo,
                               "empresa": ator.empresa, "criada_em": round(agora, 3), "revogada": None}
            criada = dict(delegacoes[did])
        self._auditar("delegacao_criada", ator.usuario, delegacao=did, alvo=para, ate=ate, teto=teto, regra="POL-11",
                      **escopo)
        return criada

    def revogar_delegacao(self, ator, did: str) -> dict:
        ator = self._exigir_viva(ator)
        d = (self._contas.ver().get("delegacoes") or {}).get(did)
        if d is None:
            raise _negado("POL-11", f"delegação inexistente: {did}")
        if d["de"] != ator.usuario:
            self.exigir(ator, "PERM-IAM-USUARIOS")  # só quem delegou, ou a administração de contas
        else:
            self.exigir(ator, "PERM-APR-DELEGAR")
        with self._tx(self._contas) as dados:
            dados["delegacoes"][did]["revogada"] = f"revogada por {ator.usuario}"
            d = dict(dados["delegacoes"][did])
        self._auditar("delegacao_revogada", ator.usuario, delegacao=did, regra="POL-11")
        return d

    def delegacoes(self, usuario: str | None = None) -> list[dict]:
        agora = self.relogio()
        saida = []
        for d in (self._contas.ver().get("delegacoes") or {}).values():
            if usuario is None or usuario in (d["de"], d["para"]):
                situacao = "revogada" if d["revogada"] else "expirada" if agora >= d["ate"] else "viva"
                saida.append({**d, "situacao": situacao})
        return saida

    def delegacao_para_decisao(self, did, pessoa: str, ticket: dict) -> dict:
        """Delegação válida para esta pessoa decidir este ticket: devolve a conta de quem delegou, ou nega (POL-11)."""
        d = (self._contas.ver().get("delegacoes") or {}).get(did) if isinstance(did, str) else None
        if d is None:
            raise _negado("POL-11", f"delegação inexistente ou forjada: {did!r}")
        if d["para"] != pessoa:
            raise _negado("POL-11", f"a delegação {did} é de {d['de']} para {d['para']}, não para {pessoa} "
                                    f"(sem subdelegação)")
        if d["revogada"]:
            raise _negado("POL-11", f"a delegação {did} foi revogada")
        if self.relogio() >= d["ate"]:
            raise _negado("POL-11", f"a delegação {did} expirou em t={d['ate']}")
        escopo = d["escopo"]
        if ("competencia" in escopo and escopo["competencia"] != ticket["competencia"]) or \
                ("solicitacao" in escopo and escopo["solicitacao"] != ticket["solicitacao"]):
            raise _negado("POL-11", f"a delegação {did} vale para {escopo}, não para este ticket")
        conta = self._ler_contas().get(d["de"])
        if conta is None or conta["estado"] != "ativa" or "PERM-APR-DECIDIR" not in permissoes.permissoes_de(conta["papeis"]):
            raise _negado("POL-11", f"quem delegou ({d['de']}) não é mais um aprovador ativo")
        return {"delegacao": d, "conta": {k: v for k, v in conta.items() if k != "senha"}}

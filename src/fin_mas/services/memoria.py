"""SVC-MEM — memória de longo prazo aprovada, com proveniência, retenção e privacidade (DSM3).

Regras (REQ-F07, NORM-06, NORM-08):

- **só saída aprovada vira memória**: toda gravação cita um ticket PROT-APR que o SVC-POL
  confirma como decidido por um humano, e o ticket precisa corresponder ao que se grava:
  `waiver` exige ticket de waiver aprovado, `correcao` um ticket de correção executado e
  `bloqueio` um ticket rejeitado; a competência é a do ticket e o lançamento está entre os
  achados (ou as correções executadas) daquele veto. Fora disso, a gravação é recusada;
- **identidade**: grava e consulta só quem tem uma visão emitida pelo serviço (`visao`), com
  um token de acesso; chamar o serviço declarando o nome de um agente não basta;
- **proveniência**: aprovação, solicitação, conversa de conformidade, decisão, quem decidiu
  (pseudônimo com chave) e fonte; quem consulta recebe o id `MEM-…`;
- **controle de acesso**: cada tipo de memória tem escritores e leitores;
- **privacidade**: o valor passa por redaction (fail-closed); pessoas viram pseudônimos
  estáveis (`pessoa#…`, HMAC com a chave da memória, que não se reverte por dicionário) e nenhum texto livre com nomes é guardado;
- **retenção**: entradas mais antigas que `retencao` competências expiram na consulta;
- **persistência íntegra**: com `caminho`, a memória é um arquivo JSON gravado de forma atômica.
  Cada entrada leva uma assinatura HMAC-SHA256 e o arquivo inteiro um **selo** HMAC sobre
  (contador de versão, entradas). A chave e o último contador ficam **fora da pasta de dados**
  (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`; a chave pode vir de `FIN_MAS_CHAVE_MEMORIA`);
- **falha fechada**: arquivo ausente quando já houve gravação, corrompido, com selo que não
  confere, com contador menor que o último gravado (volta a uma versão antiga), em outra versão
  do formato (`VERSAO`; ex.: v3, com pseudônimos sem chave), com entrada
  removida, inventada ou malformada deixa a memória **comprometida**: nada é gravado, a
  consulta informa o estado e o AG-CIN trata todo achado crítico como reincidente, de modo que
  a política não abre waiver até a memória ser restaurada.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

from fin_mas.core.schema import FORMATOS
from fin_mas.services.redacao import FalhaRedacao, redigir

VERSAO = 4  # v4: pseudônimo com HMAC (chave da memória) em vez de SHA-256 sem chave
RETENCAO_COMPETENCIAS = 12
ACESSO = {  # tipo -> (quem grava, quem lê)
    "waiver": ({"AG-CIN"}, {"AG-CIN"}),
    "correcao": ({"AG-CIN"}, {"AG-CIN"}),
    "bloqueio": ({"AG-CIN"}, {"AG-CIN"}),
}
EXIGE = {  # tipo -> (decisão do ticket, estados aceitos)
    "waiver": ("waiver", {"aprovado", "executado"}),
    "correcao": ("corrigir", {"executado"}),
    "bloqueio": ("bloquear", {"rejeitado"}),
}
COMPETENCIA = FORMATOS["aaaa-mm"][0]  # mesma regra do barramento e do dashboard (core/schema.py)
CAMPOS = {"id": str, "tipo": str, "chave": str, "valor": dict, "competencia": str, "agente": str,
          "proveniencia": dict, "assinatura": str}


class MemoriaRecusada(PermissionError):
    pass


PSEUDONIMO = re.compile(r"pessoa#[0-9a-f]{10}")


def _sem_pseudonimo(valor):
    """Tira o pseudônimo dos registros do trace: ele depende da chave local da memória (mudaria o
    hash do trace entre máquinas) e não acrescenta nada ao auditor, que já vê os usuários do ERP
    como evidência de alçada e SoD. A entrada da memória (`MEM-…`) continua identificada."""
    if isinstance(valor, str):
        return PSEUDONIMO.sub("pessoa#…", valor)
    if isinstance(valor, dict):
        return {k: _sem_pseudonimo(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_sem_pseudonimo(v) for v in valor]
    return valor




def _meses(competencia: str) -> int:
    return int(competencia[:4]) * 12 + int(competencia[5:7])


def _canonico(entrada: dict) -> bytes:
    return json.dumps({k: v for k, v in entrada.items() if k != "assinatura"}, sort_keys=True,
                      ensure_ascii=False).encode("utf-8")


class Memoria:
    ID = "SVC-MEM"

    def __init__(self, audit, clock, politica=None, caminho=None, retencao: int = RETENCAO_COMPETENCIAS):
        self.audit = audit
        self.clock = clock
        self.politica = politica
        self.caminho = Path(caminho) if caminho else None
        self.retencao = retencao
        self.entradas: list[dict] = []
        self._acessos: dict[str, str] = {}  # agente -> token da visão emitida
        self.comprometida: str | None = None  # motivo, quando a integridade do arquivo não pôde ser garantida
        self.contador = 0
        self._chave = self._carregar_chave()
        if self.caminho:
            self._carregar()

    @property
    def integra(self) -> bool:
        return self.comprometida is None

    def pseudonimo(self, valor: str) -> str:
        """Pseudônimo estável de uma pessoa: HMAC com a chave da memória (fora da pasta de dados).

        Sem a chave não dá para refazer a tabela nome -> pseudônimo, mesmo com poucos usuários
        no ERP; com a mesma chave o pseudônimo se repete entre execuções (reincidência).
        """
        return "pessoa#" + hmac.new(self._chave, f"pseudonimo:{valor}".encode("utf-8"),
                                    hashlib.sha256).hexdigest()[:10]

    # ---- identidade -------------------------------------------------------------------
    def visao(self, agente: str) -> "VisaoMemoria":
        """Emite a visão do agente (uma por agente): só ela grava e consulta em nome dele."""
        if agente in self._acessos:
            raise MemoriaRecusada(f"visão de {agente} já emitida")
        self._acessos[agente] = secrets.token_hex(16)
        return VisaoMemoria(self, agente, self._acessos[agente])

    def _autentico(self, agente, token) -> bool:
        esperado = self._acessos.get(agente)
        return esperado is not None and isinstance(token, str) and hmac.compare_digest(esperado, token)

    # ---- escrita ------------------------------------------------------------------
    def gravar(self, agente: str, tipo: str, chave: str, valor: dict, *, competencia: str, aprovacao: str,
               fonte: str, cid: str | None = None, token: str | None = None) -> dict:
        try:
            if not self._autentico(agente, token):
                raise MemoriaRecusada(f"{agente}: identidade não autenticada (use a visão emitida pelo SVC-MEM)")
            if self.comprometida:
                raise MemoriaRecusada(f"memória comprometida ({self.comprometida}): restaure o arquivo antes de gravar")
            if tipo not in ACESSO or agente not in ACESSO[tipo][0]:
                raise MemoriaRecusada(f"{agente} não grava memória do tipo {tipo}")
            ticket = self.politica.tickets.get(aprovacao) if self.politica else None
            decisao, estados = EXIGE[tipo]
            if ticket is None or ticket["estado"] not in estados or ticket["decisao"] != decisao:
                raise MemoriaRecusada(f"NORM-08: {aprovacao!r} não é uma decisão humana de {decisao} registrada")
            if competencia != ticket["competencia"]:
                raise MemoriaRecusada(f"NORM-08: competência {competencia} difere da do ticket ({ticket['competencia']})")
            validos = ({x["lancamento"] for x in ticket.get("executadas", [])} if tipo == "correcao"
                       else {a["lancamento"] for a in ticket.get("achados", [])})
            if not isinstance(valor, dict) or valor.get("lancamento") not in validos:
                raise MemoriaRecusada(f"NORM-08: lançamento {valor.get('lancamento') if isinstance(valor, dict) else None}"
                                      f" não pertence à decisão {aprovacao}")
            try:
                valor = redigir(valor)
            except FalhaRedacao as erro:
                raise MemoriaRecusada(f"NORM-06: sanitização falhou ({erro})") from erro
        except MemoriaRecusada as erro:
            self._registrar(cid, "recusada", agente=agente, tipo=tipo, chave=chave, motivo=str(erro))
            raise
        repetida = next((e for e in self.entradas if (e["tipo"], e["chave"], e["competencia"],
                                                      e["proveniencia"]["aprovacao"]) ==
                         (tipo, chave, competencia, aprovacao)), None)
        if repetida:
            return repetida
        proximo = max((int(e["id"][4:]) for e in self.entradas if e["id"][4:].isdigit()), default=0) + 1
        entrada = {
            "id": f"MEM-{proximo:04d}", "tipo": tipo, "chave": chave, "valor": valor,
            "competencia": competencia, "agente": agente,
            "proveniencia": {"aprovacao": aprovacao, "solicitacao": ticket["solicitacao"], "cmp": ticket["cmp"],
                             "decisao": ticket["decisao"],
                             "decidido_por": self.pseudonimo(ticket["aprovado_por"]["pessoa"]) if ticket.get("aprovado_por")
                             else None, "fonte": fonte},
        }
        entrada["assinatura"] = self._assinar(entrada)
        self.entradas.append(entrada)
        self._persistir()
        self._registrar(cid, "gravada", agente=agente, memoria=entrada["id"], tipo=tipo, chave=chave,
                        competencia=competencia, aprovacao=aprovacao)
        return entrada

    # ---- leitura --------------------------------------------------------------------
    def consultar(self, agente: str, tipo: str, chave: str | None = None, *, competencia_atual: str,
                  cid: str | None = None, token: str | None = None) -> list[dict]:
        """Entradas do tipo (e chave) de competências anteriores, dentro da retenção."""
        if not self._autentico(agente, token) or tipo not in ACESSO or agente not in ACESSO[tipo][1]:
            self._registrar(cid, "negada", agente=agente, tipo=tipo, chave=chave)
            return []
        if self.comprometida:
            self._registrar(cid, "indisponivel", agente=agente, tipo=tipo, motivo=self.comprometida)
            return []
        self.expirar(competencia_atual, cid)
        achadas = [e for e in self.entradas if e["tipo"] == tipo and (chave is None or e["chave"] == chave)
                   and _meses(e["competencia"]) < _meses(competencia_atual)]
        if achadas:
            self._registrar(cid, "consultada", agente=agente, tipo=tipo, chave=chave,
                            memorias=[e["id"] for e in achadas])
        return achadas

    def expirar(self, competencia_atual: str, cid: str | None = None) -> None:
        limite = _meses(competencia_atual) - self.retencao
        vencidas = [e for e in self.entradas if _meses(e["competencia"]) < limite]
        if vencidas:
            self.entradas = [e for e in self.entradas if e not in vencidas]
            self._persistir()
            self._registrar(cid, "expirada", agente=self.ID, memorias=[e["id"] for e in vencidas],
                            retencao=self.retencao)

    # ---- persistência e integridade ---------------------------------------------------------
    def _arquivo_estado(self, sufixo: str) -> Path:
        base = Path(os.environ.get("FIN_MAS_DIR_CHAVES") or Path.home() / ".fin_mas" / "chaves")
        nome = hashlib.sha256(str(self.caminho.resolve()).encode("utf-8")).hexdigest()[:16]
        return base / f"memoria-{nome}.{sufixo}"

    def _carregar_chave(self) -> bytes:
        if os.environ.get("FIN_MAS_CHAVE_MEMORIA"):
            return os.environ["FIN_MAS_CHAVE_MEMORIA"].encode("utf-8")
        if not self.caminho:
            return secrets.token_bytes(32)  # memória só em processo: chave efêmera
        arquivo = self._arquivo_estado("chave")  # fora da pasta de dados
        if arquivo.exists():
            return arquivo.read_bytes()
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        chave = secrets.token_bytes(32)
        arquivo.write_bytes(chave)
        try:
            os.chmod(arquivo, 0o600)
        except OSError:
            pass
        return chave

    def _assinar(self, entrada: dict) -> str:
        return hmac.new(self._chave, _canonico(entrada), hashlib.sha256).hexdigest()

    def _selar(self, contador: int, entradas: list) -> str:
        corpo = json.dumps({"contador": contador, "entradas": entradas}, sort_keys=True, ensure_ascii=False)
        return hmac.new(self._chave, corpo.encode("utf-8"), hashlib.sha256).hexdigest()

    def _ultimo_contador(self) -> int:
        try:
            return int(self._arquivo_estado("contador").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0

    def _comprometer(self, motivo: str) -> None:
        if self.comprometida is None:
            self.comprometida = motivo
            self._registrar(None, "comprometida", agente=self.ID, motivo=motivo,
                            arquivo=self.caminho.name if self.caminho else None)

    def _carregar(self) -> None:
        esperado = self._ultimo_contador()
        if not self.caminho.exists():
            if esperado > 0:
                self._comprometer(f"arquivo ausente, mas a versão {esperado} já foi gravada")
            return
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            if not isinstance(dados, dict) or not isinstance(dados.get("entradas"), list):
                raise ValueError("estrutura inesperada")
        except (ValueError, OSError) as erro:
            self._registrar(None, "descartada", agente=self.ID, motivo=f"arquivo ilegível: {erro}")
            self._comprometer(f"arquivo ilegível: {erro}")
            return
        if dados.get("versao") != VERSAO:
            # outro formato (ex.: v3, pseudônimo sem chave): as chaves de reincidência não casam com as
            # consultas desta versão e a POL-06 deixaria de valer. Não há migração (os nomes não ficam
            # guardados), então a memória fica comprometida (falha fechada). Apagar só o arquivo não basta:
            # o contador fora da pasta de dados acusaria arquivo ausente; o caminho é começar outro arquivo.
            self._comprometer(f"arquivo na versão {dados.get('versao')!r} do formato, esta é a {VERSAO}: "
                              "chaves de reincidência de outra versão não são reconhecidas; "
                              "comece uma memória nova (outro arquivo em --memoria)")
            return
        contador, brutas = dados.get("contador"), dados["entradas"]
        if not isinstance(contador, int) or not hmac.compare_digest(str(dados.get("selo")),
                                                                    self._selar(contador, brutas)):
            self._comprometer("selo do arquivo não confere (entrada removida, inserida ou arquivo alterado)")
        elif contador < esperado:
            self._comprometer(f"versão {contador} é anterior à última gravada ({esperado}): arquivo antigo restaurado")
        self.contador = contador if isinstance(contador, int) else 0
        for e in brutas:
            motivo = self._invalida(e)
            if motivo:
                self._registrar(None, "descartada", agente=self.ID,
                                memoria=e.get("id") if isinstance(e, dict) else None, motivo=motivo)
                self._comprometer(f"entrada inválida: {motivo}")
            else:
                self.entradas.append(e)
        self._registrar(None, "carregada", agente=self.ID, entradas=len(self.entradas), arquivo=self.caminho.name,
                        integra=self.integra)

    def _invalida(self, e) -> str | None:
        if not isinstance(e, dict):
            return "entrada não é objeto"
        for campo, tipo in CAMPOS.items():
            if not isinstance(e.get(campo), tipo):
                return f"campo {campo} ausente ou de tipo errado"
        if e["tipo"] not in ACESSO or not COMPETENCIA.fullmatch(e["competencia"]):
            return "tipo ou competência inválidos"
        if not isinstance(e["proveniencia"].get("aprovacao"), str):
            return "proveniência sem aprovação"
        if not hmac.compare_digest(e["assinatura"], self._assinar(e)):
            return "assinatura não confere (entrada alterada fora do SVC-MEM)"
        return None

    def _persistir(self) -> None:
        if not self.caminho:
            return
        self.contador += 1
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(self.caminho.suffix + ".tmp")
        temporario.write_text(json.dumps({"versao": VERSAO, "contador": self.contador, "entradas": self.entradas,
                                          "selo": self._selar(self.contador, self.entradas)},
                                         ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(temporario, self.caminho)
        estado = self._arquivo_estado("contador")
        estado.parent.mkdir(parents=True, exist_ok=True)
        estado.write_text(str(self.contador), encoding="utf-8")

    def _registrar(self, cid, evento, **campos) -> None:
        self.audit.record(self.clock(), "memoria", conversation_id=cid, evento=evento, **_sem_pseudonimo(campos))


class VisaoMemoria:
    """O que o agente enxerga do SVC-MEM: grava e consulta com a própria identidade e o token da visão."""

    def __init__(self, servico: Memoria, agente: str, token: str):
        self._servico = servico
        self._agente = agente
        self.__token = token

    def gravar(self, tipo, chave, valor, **kw) -> dict:
        return self._servico.gravar(self._agente, tipo, chave, valor, token=self.__token, **kw)

    def consultar(self, tipo, chave=None, **kw) -> list[dict]:
        return self._servico.consultar(self._agente, tipo, chave, token=self.__token, **kw)

    def pseudonimo(self, valor: str) -> str:
        return self._servico.pseudonimo(valor)

    @property
    def integra(self) -> bool:
        return self._servico.integra

    @property
    def motivo_comprometida(self) -> str | None:
        return self._servico.comprometida

    def resumo(self) -> dict:
        return {"entradas": len(self._servico.entradas), "persistente": self._servico.caminho is not None,
                "integra": self._servico.integra}

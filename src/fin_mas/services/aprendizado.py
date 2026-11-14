"""Registro de aprendizado das regras locais de hipótese (DSM4, ADR-010, NORM-20).

Cada regra do motor local (`cognicao/regras.py`) tem uma confiança inicial, escolhida por quem
escreveu a regra. Este registro guarda, por agente e por regra, quantas hipóteses que ela propôs
foram **confirmadas** ou **refutadas** por evidência determinística, e devolve a confiança da
regra para as competências seguintes:

    confiança = (inicial x k + confirmadas) / (k + confirmadas + refutadas)        k = peso do prior

Com k = 2, uma regra de confiança inicial 0,80 cai para 0,53 depois de uma refutação e para 0,40
depois de duas; sobe para 0,87 depois de uma confirmação. É uma contagem, não um modelo: dá para
refazer a conta à mão a partir do que está gravado.

Por que não fica no SVC-MEM. A memória de longo prazo só aceita decisão aprovada por um humano
(NORM-08): toda gravação cita um ticket do Approval Gate, e é isso que permite ao AG-CIN negar um
segundo waiver com base nela. Estatística de regra não é decisão de ninguém; para caber lá seria
preciso abrir uma exceção à NORM-08, e a memória deixaria de ser "só o que um humano aprovou".
Por isso o aprendizado tem um arquivo próprio, com o mesmo formato selado dos cadastros de acesso
(`services/selado.py`: selo HMAC, contador contra rollback, gravação atômica, trava entre
processos), e não se mistura com a memória.

Regras do registro:

- **só evidência verificada conta**: a observação exige o desfecho `confirmada` ou `refutada` e a
  fonte da evidência, que não pode ser um proponente (`local:` ou `llm:`). Hipótese arquivada não
  entra na conta, porque não se sabe se a regra acertou;
- **só regra local aprende**: origem `llm:` não é contada (o modelo muda fora do nosso controle);
- **só o passado informa**: a confiança usada numa competência vem das observações de competências
  anteriores a ela, de modo que a ordem dos eventos dentro do mês não muda o resultado;
- **uma observação por hipótese**: a chave (agente, regra, competência, tipo, alvo) é única; rodar
  de novo a mesma competência com o arquivo persistente não conta duas vezes;
- **falha fechada**: arquivo comprometido desliga o aprendizado (as regras voltam à confiança
  inicial) e nada é gravado; o motivo vai para o trace;
- **determinismo**: sem `caminho` o registro vive só na execução, e o trace é função da seed.

Confiança aprendida não é crença e não classifica nada: ela só entra no contexto dos planos
epistêmicos que custam mensagem (regra que errou muito não justifica uma consulta nova).
"""
import re
from fin_mas.services.selado import ArquivoComprometido, ArquivoSelado

VERSAO = 1
PESO_DO_PRIOR = 2
CONFIANCA_NEUTRA = 0.5  # regra que não declara confiança inicial


FONTE_DETERMINISTICA = re.compile(r"^(AG-[A-Z]{3}\b|SVC-[A-Z]{3}\b|mcp://|cálculo sobre )")


class ObservacaoRecusada(ValueError):
    """A observação não tem a proveniência exigida para contar no aprendizado."""


def _meses(competencia: str) -> int:
    return int(competencia[:4]) * 12 + int(competencia[5:7])


def confianca(inicial: float | None, confirmadas: int, refutadas: int, peso: int = PESO_DO_PRIOR) -> float:
    base = CONFIANCA_NEUTRA if inicial is None else inicial
    return round((base * peso + confirmadas) / (peso + confirmadas + refutadas), 2)


class Aprendizado:
    ID = "SVC-APD"

    def __init__(self, audit, clock, caminho=None, peso_do_prior: int = PESO_DO_PRIOR):
        self.audit = audit
        self.clock = clock
        self.peso = peso_do_prior
        self.comprometido: str | None = None
        self.arquivo = ArquivoSelado(caminho, "aprendizado", VERSAO, {"observacoes": []})
        self.persistente = self.arquivo.caminho is not None
        if self.persistente:
            observacoes = self._ler()
            self._registrar(None, "carregado", agente=self.ID, observacoes=len(observacoes),
                            arquivo=self.arquivo.caminho.name, integro=self.comprometido is None)

    # ---- leitura -----------------------------------------------------------------
    def _ler(self) -> list[dict]:
        if self.comprometido:
            return []
        try:
            return list(self.arquivo.ver()["observacoes"])
        except (ArquivoComprometido, KeyError, TypeError) as erro:
            self.comprometido = str(erro) or type(erro).__name__
            self._registrar(None, "comprometido", agente=self.ID, motivo=self.comprometido)
            return []

    def situacao(self, agente: str, regra: str, inicial: float | None, competencia: str) -> dict:
        """Contagem da regra nas competências anteriores a `competencia` e a confiança que dela resulta."""
        anteriores = [o for o in self._ler() if (o["agente"], o["regra"]) == (agente, regra)
                      and _meses(o["competencia"]) < _meses(competencia)]
        confirmadas = sum(1 for o in anteriores if o["desfecho"] == "confirmada")
        refutadas = len(anteriores) - confirmadas
        return {"regra": regra, "confirmadas": confirmadas, "refutadas": refutadas,
                "observacoes": len(anteriores), "confianca": confianca(inicial, confirmadas, refutadas, self.peso)}

    def resumo(self) -> list[dict]:
        """Totais por agente e regra (todas as competências), para relatório e dashboard."""
        totais: dict[tuple, dict] = {}
        for o in self._ler():
            t = totais.setdefault((o["agente"], o["regra"]), {"agente": o["agente"], "regra": o["regra"],
                                                              "confirmadas": 0, "refutadas": 0})
            t["confirmadas" if o["desfecho"] == "confirmada" else "refutadas"] += 1
        return [totais[k] for k in sorted(totais)]

    # ---- escrita -----------------------------------------------------------------
    def observar(self, agente: str, hipotese, desfecho: str, fonte: str | None) -> list[dict]:
        """Soma o desfecho da hipótese às regras locais que a propuseram. Devolve o que foi gravado."""
        try:
            if desfecho not in ("confirmada", "refutada"):
                raise ObservacaoRecusada(f"desfecho '{desfecho}' não é evidência (só confirmada ou refutada contam)")
            texto = str(fonte or "").strip()
            # lista de permissões: outro agente, serviço da plataforma, tool MCP ou cálculo sobre eles; nada que
            # cite um proponente (regra local ou LLM), em qualquer posição (correção simulada da DSM4, m2)
            if (not FONTE_DETERMINISTICA.match(texto) or "llm:" in texto.lower() or "local:" in texto.lower()):
                raise ObservacaoRecusada(f"evidência sem fonte determinística ({fonte!r})")
        except ObservacaoRecusada as erro:
            self._registrar(hipotese.cid, "recusada", agente=agente, hipotese=hipotese.id, motivo=f"NORM-20: {erro}")
            return []
        if self.comprometido:
            self._registrar(hipotese.cid, "indisponivel", agente=agente, hipotese=hipotese.id, motivo=self.comprometido)
            return []
        regras = [o for o in hipotese.origens if o.startswith("local:")]
        novas = []
        try:
            with self.arquivo.transacao() as dados:
                for regra in regras:
                    chave = (agente, regra, hipotese.competencia, hipotese.tipo, hipotese.alvo)
                    if any((o["agente"], o["regra"], o["competencia"], o["tipo"], o["alvo"]) == chave
                           for o in dados["observacoes"]):
                        continue  # a mesma hipótese já foi contada (ex.: competência reprocessada)
                    obs = {"agente": agente, "regra": regra, "competencia": hipotese.competencia,
                           "tipo": hipotese.tipo, "alvo": hipotese.alvo, "desfecho": desfecho, "fonte": str(fonte),
                           "hipotese": hipotese.id}
                    dados["observacoes"].append(obs)
                    novas.append(obs)
        except ArquivoComprometido as erro:
            self.comprometido = str(erro)
            self._registrar(hipotese.cid, "comprometido", agente=self.ID, motivo=self.comprometido)
            return []
        todas = self._ler()
        for obs in novas:
            mesmas = [o for o in todas if (o["agente"], o["regra"]) == (agente, obs["regra"])]
            confirmadas = sum(1 for o in mesmas if o["desfecho"] == "confirmada")
            self._registrar(hipotese.cid, "observada", agente=agente, regra=obs["regra"], hipotese=hipotese.id,
                            tipo=hipotese.tipo, alvo=hipotese.alvo, competencia=hipotese.competencia,
                            desfecho=desfecho, fonte=str(fonte), confirmadas=confirmadas,
                            refutadas=len(mesmas) - confirmadas, norma="NORM-20")
        return novas

    def _registrar(self, cid, evento, **campos) -> None:
        self.audit.record(self.clock(), "aprendizado", conversation_id=cid, evento=evento, **campos)

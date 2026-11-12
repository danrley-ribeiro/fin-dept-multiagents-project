"""Hipóteses dos agentes cognitivos: proposta, validação e ciclo de vida (ADR-008, NORM-11).

Uma **proposta** vem de um proponente: regras locais (`cognicao/regras.py`, offline) ou um
LLM opcional (`services/modelos.py`). Proposta não é crença. Ela só vira **hipótese** depois
de passar pela validação determinística deste módulo, e uma hipótese só muda o que o agente
acredita quando uma **evidência** de fonte determinística a confirma (outro agente, uma
tool, um cálculo sobre o histórico). O caminho é sempre:

    proposta -> validação -> hipótese -> ação epistêmica -> evidência -> crença

Validação (cada regra recusa a proposta inteira; o motivo vai para o trace):

1. o tipo está na lista fechada do agente e o alvo existe na tarefa;
2. toda evidência citada é uma crença que o agente realmente tem;
3. o texto não traz números: valores entram por marcadores (`{chave}`) que o agente resolve
   a partir das próprias crenças, de modo que o proponente não consegue inventar um valor
   nem trocar a grandeza de um valor verdadeiro;
4. o texto não propõe ação (aprovar, estornar, lançar…): quem age é a política, não a hipótese;
5. todo marcador aponta para uma evidência citada ou para o alvo.

Estados: proposta -> em_verificacao -> confirmada | refutada | arquivada.
"""
import json
import re
from dataclasses import dataclass, field

ESTADOS = ("proposta", "em_verificacao", "confirmada", "refutada", "arquivada")
FINAIS = {"confirmada", "refutada", "arquivada"}
MARCADOR = re.compile(r"\{([^{}]*)\}")
DIGITO = re.compile(r"\d")
ACAO = re.compile(r"\b(aprov[ae]r?|aprove|estorn[ae]r?|estorne|execut[ae]r?|execute|lan[cç]ar|lance|liberar?|libere|"
                  r"classifi(car|que)|reclassifi(car|que)|bloque(ar|ie)|pag(ar|ue))\b", re.IGNORECASE)
MAX_TEXTO = 600
CAMPOS_PROPOSTA = {"tipo", "alvo", "justificativa", "evidencias", "confianca"}


class PropostaInvalida(ValueError):
    """A resposta do proponente não tem a forma exigida (JSON estrito)."""


@dataclass(frozen=True)
class Proposta:
    tipo: str
    alvo: str
    justificativa: str = ""
    evidencias: tuple = ()
    confianca: float | None = None
    origem: str = ""  # "local:<regra>" ou "llm:<provedor>/<modelo>@<versão do prompt>"; quem define é a plataforma


@dataclass
class Hipotese:
    id: str
    tipo: str
    alvo: str
    competencia: str
    origens: list
    justificativa: str
    evidencias: tuple
    confianca: float | None
    cid: str | None
    estado: str = "proposta"
    verificacao: str | None = None  # fonte da evidência que confirmou ou refutou

    def resumo(self) -> dict:
        return {"id": self.id, "tipo": self.tipo, "alvo": self.alvo, "competencia": self.competencia,
                "origens": list(self.origens), "estado": self.estado, "confianca": self.confianca,
                "justificativa": self.justificativa, "evidencias": list(self.evidencias),
                "verificacao": self.verificacao}


@dataclass(frozen=True)
class EsquemaHipoteses:
    """Lista fechada do que um agente aceita como hipótese numa tarefa."""

    tipos: dict  # tipo -> descrição
    alvos: tuple
    evidencias: tuple  # chaves de crença que podem ser citadas
    max_propostas: int = 4
    valores: dict = field(default_factory=dict)  # chave de crença -> texto já formatado (resolve marcadores)

    def como_json_schema(self) -> dict:
        """Esquema JSON da resposta, para provedores que restringem a saída."""
        return {
            "type": "object", "additionalProperties": False, "required": ["propostas"],
            "properties": {"propostas": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["tipo", "alvo", "justificativa", "evidencias", "confianca"],
                "properties": {
                    "tipo": {"type": "string", "enum": sorted(self.tipos)},
                    "alvo": {"type": "string", "enum": list(self.alvos)},
                    "justificativa": {"type": "string"},
                    "evidencias": {"type": "array", "items": {"type": "string"}},
                    "confianca": {"type": "number"},
                }}}},
        }


def ler_propostas(texto: str, origem: str) -> list[Proposta]:
    """JSON estrito `{"propostas": [...]}`; qualquer desvio de forma levanta `PropostaInvalida`."""
    try:
        dados = json.loads(texto)
    except (TypeError, ValueError) as erro:
        raise PropostaInvalida(f"resposta não é JSON: {erro}") from None
    if not isinstance(dados, dict) or set(dados) != {"propostas"} or not isinstance(dados["propostas"], list):
        raise PropostaInvalida('a resposta precisa ser {"propostas": [...]}, sem outros campos')
    saida = []
    for item in dados["propostas"]:
        if not isinstance(item, dict) or not set(item) <= CAMPOS_PROPOSTA or not {"tipo", "alvo"} <= set(item):
            raise PropostaInvalida(f"proposta com campos fora de {sorted(CAMPOS_PROPOSTA)}")
        evidencias = item.get("evidencias") or []
        confianca = item.get("confianca")
        if (not isinstance(item["tipo"], str) or not isinstance(item["alvo"], str)
                or not isinstance(item.get("justificativa", ""), str) or not isinstance(evidencias, list)
                or not all(isinstance(e, str) for e in evidencias)
                or not (confianca is None or (isinstance(confianca, (int, float)) and not isinstance(confianca, bool)))):
            raise PropostaInvalida("proposta com tipos de campo inválidos")
        saida.append(Proposta(item["tipo"], item["alvo"], item.get("justificativa", ""), tuple(evidencias),
                              None if confianca is None else float(confianca), origem))
    return saida


def validar_proposta(p: Proposta, esquema: EsquemaHipoteses) -> str | None:
    """Motivo da recusa, ou None quando a proposta pode virar hipótese."""
    if p.tipo not in esquema.tipos:
        return f"tipo '{p.tipo}' fora da lista fechada {sorted(esquema.tipos)}"
    if p.alvo not in esquema.alvos:
        return f"alvo '{p.alvo}' não faz parte da tarefa"
    if not p.evidencias:
        return "nenhuma evidência citada"
    estranhas = [e for e in p.evidencias if e not in esquema.evidencias]
    if estranhas:
        return f"evidência que o agente não tem: {estranhas}"
    if p.confianca is not None and not 0 <= p.confianca <= 1:
        return f"confiança {p.confianca} fora de 0..1"
    if len(p.justificativa) > MAX_TEXTO:
        return f"justificativa com mais de {MAX_TEXTO} caracteres"
    marcadores = MARCADOR.findall(p.justificativa)
    fora = [m for m in marcadores if m != "alvo" and m not in p.evidencias]
    if fora:
        return f"marcador sem evidência correspondente: {fora}"
    livre = MARCADOR.sub("", p.justificativa)
    if "{" in livre or "}" in livre:
        return "chaves desbalanceadas na justificativa"
    if DIGITO.search(livre):
        return "o texto traz número; valores só entram por marcador de evidência"
    acao = ACAO.search(livre)
    if acao:
        return f"o texto propõe uma ação ({acao.group(0)})"
    return None


def resolver(texto: str, alvo: str, valores: dict) -> str:
    """Troca `{alvo}` e `{chave}` pelo valor que o agente tem; marcador desconhecido fica como está."""
    return MARCADOR.sub(lambda m: alvo if m.group(1) == "alvo" else str(valores.get(m.group(1), m.group(0))), texto)

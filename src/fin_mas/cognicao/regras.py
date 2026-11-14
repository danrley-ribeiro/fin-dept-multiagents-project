"""Proponente local de hipóteses: regras e heurísticas offline (ADR-008).

É o que deixa os agentes BDI mais ricos sem rede e sem chave: a partir das percepções da
tarefa (texto livre da planilha, histórico mensal) as regras propõem **hipóteses**, que
passam pela mesma validação e pela mesma verificação das propostas de um LLM
(`core/inferencia.py`). Uma regra nunca grava crença nem escolhe plano.

Cada regra recebe o contexto de uma conta e devolve uma `Proposta` ou `None`. O texto usa
marcadores (`{chave}`), nunca números. O contexto de uma conta é:

    {"conta", "chaves": {"orcado", "realizado", "observacao"?, "historico"?},
     "observacao"?: str, "historico"?: [{"mes_no_trimestre", "orcado", "realizado"}, ...],
     "mes_no_trimestre": int, "limiar_percentual": int}
"""
import re
import unicodedata

from fin_mas.core.inferencia import Proposta

REPETICAO = re.compile(r"duplicid|duplicad|em dobro|duas vezes|lancad[oa] novamente|lancamento repetido")
RECORRENCIA = re.compile(r"todo (inicio|comeco|fim|final) de (trimestre|ano|semestre)|sazonal|sazonalidade|"
                         r"todos os anos|todo trimestre")


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _obs_repeticao(x) -> Proposta | None:
    """Quem preencheu a planilha avisou de um lançamento repetido: o desvio pode ser de controle."""
    obs = x.get("observacao")
    if not obs or not REPETICAO.search(sem_acento(obs)):
        return None
    k = x["chaves"]
    return Proposta("causa_controle", x["conta"],
                    f"A observação {{{k['observacao']}}} fala em lançamento repetido em {{alvo}}; o realizado "
                    f"{{{k['realizado']}}} pode estar inflado por um problema de controle, não de orçamento.",
                    (k["observacao"], k["realizado"]), 0.8)


def _obs_recorrencia(x) -> Proposta | None:
    """O texto livre descreve um gasto que se repete na mesma época: o desvio pode ser só de calendário."""
    obs = x.get("observacao")
    if not obs or not RECORRENCIA.search(sem_acento(obs)):
        return None
    k = x["chaves"]
    return Proposta("efeito_temporal", x["conta"],
                    f"A observação {{{k['observacao']}}} descreve um gasto que se repete na mesma época em {{alvo}}.",
                    (k["observacao"],), 0.6)


def _pico_no_historico(x) -> Proposta | None:
    """No último trimestre do histórico, o mesmo mês do trimestre também ficou acima do orçado."""
    serie = x.get("historico") or []
    mesmo_mes = [m for m in serie if m["mes_no_trimestre"] == x["mes_no_trimestre"]]
    if not mesmo_mes:
        return None
    ultimo = mesmo_mes[-1]
    if (ultimo["realizado"] - ultimo["orcado"]) * 100 < ultimo["orcado"] * x["limiar_percentual"]:
        return None
    k = x["chaves"]
    return Proposta("efeito_temporal", x["conta"],
                    f"O histórico {{{k['historico']}}} mostra {{alvo}} acima do orçado neste mesmo mês do "
                    f"trimestre anterior; o desvio de agora pode ser um efeito de calendário.",
                    (k["historico"], k["realizado"]), 0.7)


def _memoria_reincidencia(x) -> Proposta | None:
    """DSM4: a memória aprovada registra, em competência anterior, correção de lançamento irregular na conta."""
    k = x["chaves"]
    if not x.get("reincidencia") or "reincidencia" not in k:
        return None
    return Proposta("causa_controle", x["conta"],
                    f"A memória de decisões humanas {{{k['reincidencia']}}} registra correção de lançamento irregular em "
                    f"{{alvo}} em competência anterior; o realizado {{{k['realizado']}}} pode repetir o mesmo "
                    f"problema de controle.", (k["reincidencia"], k["realizado"]), 0.7)


REGRAS = (("R-OBS-REPETICAO", _obs_repeticao), ("R-OBS-RECORRENCIA", _obs_recorrencia),
          ("R-HIST-PICO", _pico_no_historico), ("R-MEM-REINCIDENCIA", _memoria_reincidencia))


# ---- regras do AG-RES (DSM4, ADR-010): causa da variação de um indicador --------------------
# Contexto de um indicador:
#   {"conta": nome do indicador, "chaves": {"indicador", "historico", "receita", "custos_variaveis", "custos_fixos"},
#    "linhas": {linha: {"atual", "media", "adverso_percentual"}}, "limiar_linha": int}
# `adverso_percentual` é quanto a linha piorou contra a média do histórico (alta de custo ou queda de receita).
def _linha_adversa(linha, tipo, frase):
    def regra(x) -> Proposta | None:
        dados = (x.get("linhas") or {}).get(linha)
        if not dados or dados["adverso_percentual"] < x["limiar_linha"]:
            return None
        k = x["chaves"]
        return Proposta(tipo, x["conta"], frase.format(linha=f"{{{k[linha]}}}", historico=f"{{{k['historico']}}}"),
                        (k[linha], k["historico"], k["indicador"]), 0.7)
    return regra


REGRAS_RES = (
    ("R-RES-CUSTO-FIXO", _linha_adversa("custos_fixos", "causa_custo_fixo",
                                        "Os custos fixos {linha} estão acima da média do histórico {historico}; a "
                                        "queda de {{alvo}} pode vir de um centro de custo.")),
    ("R-RES-CUSTO-VARIAVEL", _linha_adversa("custos_variaveis", "causa_custo_variavel",
                                            "Os custos variáveis {linha} estão acima da média do histórico "
                                            "{historico}; a queda de {{alvo}} pode vir do custo dos produtos.")),
    ("R-RES-RECEITA", _linha_adversa("receita", "causa_receita",
                                     "A receita {linha} está abaixo da média do histórico {historico}; a queda de "
                                     "{{alvo}} pode vir do volume ou do preço.")),
)


class ProponenteLocal:
    """Aplica as regras, em ordem fixa, a cada conta do contexto (determinístico)."""

    ID = "local"

    def __init__(self, regras=REGRAS):
        self.regras = tuple(regras)

    def propor(self, agente, cid, tarefa, contexto, esquema) -> list[Proposta]:
        propostas = []
        for conta in contexto.get("contas", []):
            for regra_id, regra in self.regras:
                p = regra(conta)
                if p is not None:
                    propostas.append(Proposta(p.tipo, p.alvo, p.justificativa, p.evidencias, p.confianca,
                                              f"local:{regra_id}"))
        return propostas

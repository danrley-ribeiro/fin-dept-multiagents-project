"""Linha de base da DSM1: workflow sequencial único, sem agentes (CP4).

É o "workflow determinístico" do project charter (docs/dsm1/project_charter.md): uma
função executa as etapas em ordem fixa, lendo só as fontes que a etapa precisa:

    custos -> orçamento (planilha) -> DRE -> verificação de regras -> relatório

Não há veto (achados críticos viram anexo e a publicação segue), não há consulta
entre unidades (o desvio não é atribuído a lançamentos irregulares), não há
reconciliação entre planilha e ERP e não há recurso disputado. As fórmulas são as
mesmas dos agentes; muda só a coordenação. A latência lógica supõe o mesmo custo por
etapa do bus (1 tick de entrega + 2 de processamento), sem paralelismo.
"""
from dataclasses import dataclass, field

from fin_mas.env.dataset import Dataset

TICKS_POR_ETAPA = 3
ETAPAS = {"fechar_mes": ["custos", "orcamento", "resultados", "conformidade", "relatorio"],
          "avaliar_orcamento": ["orcamento", "relatorio"]}


@dataclass
class ResultadoBaseline:
    intencao: str
    status: str
    sinalizadas: list
    dre: dict | None
    achados: list
    criticas_publicadas: int
    etapas: int
    ticks: int
    mensagens: int = 0
    decisoes: list = field(default_factory=list)


def executar(ds: Dataset, intencao: str = "fechar_mes") -> ResultadoBaseline:
    decisoes = []
    sinalizadas = []
    limiar = ds.perfil["limiar_desvio"]
    for linha in ds.orcamento:  # só a planilha: é a fonte que a etapa de orçamento conhece
        desvio = linha["realizado_acumulado"] - linha["orcado_acumulado"]
        if (abs(desvio) * 100 >= linha["orcado_acumulado"] * limiar["percentual"]
                and abs(desvio) >= limiar["absoluto"]):
            sinalizadas.append(linha["conta"])
            decisoes.append(("orcamento", "desvio acima do limiar", linha["conta"]))
    dre, achados = None, []
    if intencao == "fechar_mes":
        receita = sum(p["preco"] * p["qtd"] for p in ds.produtos)
        cv = sum(p["custo_variavel_unit"] * p["qtd"] for p in ds.produtos)
        fixo = sum(c["valor"] for c in ds.custos_fixos)
        dre = {"receita": receita, "custos_variaveis": cv, "margem_contribuicao": receita - cv,
               "custos_fixos": fixo, "ebitda": receita - cv - fixo}
        achados = _verificar(ds)
        decisoes.append(("conformidade", "achados anexados; sem poder de veto", len(achados)))
    criticas = sum(1 for a in achados if a["severidade"] == "critica")
    status = "publicado_com_ressalva" if achados else "publicado"
    etapas = len(ETAPAS[intencao])
    return ResultadoBaseline(intencao, status, sorted(sinalizadas), dre, achados, criticas, etapas,
                             ticks=etapas * TICKS_POR_ETAPA, decisoes=decisoes)


def _verificar(ds: Dataset) -> list:
    achados, vistos = [], set()
    for lanc in ds.lancamentos:
        regras = []
        teto = ds.perfil["limites_alcada"][ds.perfil["pessoas"][lanc["aprovador"]]]
        if teto is not None and lanc["valor"] > teto:
            regras.append("alcada")
        if lanc["criador"] == lanc["aprovador"]:
            regras.append("sod")
        chave = (lanc["fornecedor"], lanc["documento"], lanc["valor"])
        if chave in vistos:
            regras.append("duplicidade")
        vistos.add(chave)
        if lanc["competencia"] != ds.competencia:
            regras.append("competencia")
        achados += [{"regra": r, "lancamento": lanc["id"], "severidade": ds.perfil["severidade"][r]} for r in regras]
    return sorted(achados, key=lambda a: (a["regra"], a["lancamento"]))

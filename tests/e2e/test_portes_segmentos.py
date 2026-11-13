"""Portes novos (MEI, Média empresa II) e eixo segmento (comércio, serviços, indústria): DSM4.

Cenários nomeados de ponta a ponta sobre o barramento: o gabarito vem do que o Dataset plantou
(`ds.gold`), as regras vêm de models/portes.yaml e a forma da empresa de models/segmentos.yaml.
"""
import pytest

from fin_mas.env.dataset import Dataset
from fin_mas.env.portes import PORTES, classe_legal, perfil, porte_por_receita
from fin_mas.env.scenarios import CENARIOS, Scenario, run_scenario
from fin_mas.env.segmentos import SEGMENTO_PADRAO, SEGMENTOS, segmento

pytestmark = pytest.mark.e2e


def _veto(e):
    return next((r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto"), None)


def _achados(e):
    return {(a["regra"], a["lancamento"], a["severidade"]) for a in _veto(e)["content"]["achados"]}


def _gabarito(ds):
    return {(n["regra"], n["lancamento"], n["severidade"]) for n in ds.gold["nao_conformidades"]}


def test_legal_bands_follow_lc123_and_bndes():
    reais = 100  # centavos
    assert PORTES == ("mei", "micro", "pequena", "media", "media_ii", "grande")
    assert porte_por_receita(81_000 * reais, mei=True) == "mei"
    assert porte_por_receita(81_000 * reais) == "micro"  # MEI é opção (SIMEI), não só faixa de receita
    assert porte_por_receita(81_001 * reais, mei=True) == "micro"
    assert porte_por_receita(360_000 * reais) == "micro" and porte_por_receita(360_001 * reais) == "pequena"
    assert porte_por_receita(90_000_000 * reais) == "media"  # Média Empresa I do BNDES
    assert porte_por_receita(90_000_001 * reais) == "media_ii" and classe_legal("media_ii") == "media"
    assert porte_por_receita(300_000_000 * reais) == "media_ii" and porte_por_receita(300_000_001 * reais) == "grande"
    # os quatro portes de antes não mudaram de valor
    assert (perfil("micro")["receita_bruta_anual_max"], perfil("media")["receita_bruta_anual_max"]) == (36000000, 30000000000)


def test_mei_runs_alone_without_erp_and_with_compensating_control():
    e = run_scenario("fechamento_mei")
    ds, p = e.system.dataset, perfil("mei")
    assert list(p["pessoas"]) == ["elisa"] and p["aprovadores"] == ["titular"] and not p["tem_erp"]
    for seed in (1, 2, 3, 42):
        assert porte_por_receita(Dataset(seed=seed, porte="mei").gold["dre"]["receita"] * 12, mei=True) == "mei"
    # sem ERP: a tool do ERP é indisponível e o realizado vem da planilha
    assert [(r["agente"], r["tool"]) for r in e.audit.records if r["kind"] == "mcp_denied"] == [
        ("AG-ORC", "erp.realizado_por_conta")]
    # o veto lista todo o gabarito; só a duplicidade é crítica e o estorno dela destrava
    veto = _veto(e)
    assert {(a["regra"], a["severidade"]) for a in veto["content"]["achados"] if a["severidade"] == "critica"} == {
        ("duplicidade", "critica")}
    assert _achados(e) == _gabarito(ds)
    assert [c["acao"] for c in ds.correcoes] == ["estornar"]
    r = e.resposta
    assert r.performative == "inform" and r.content["status"] == "publicado_com_ressalva"
    sod = [x for x in r.content["ressalvas"] if x.startswith("sod em")]
    assert len(sod) == 1 and "controle compensatório" in sod[0] and "segregação é impossível" in sod[0]
    assert any(x.startswith("competencia em") for x in r.content["ressalvas"])
    # alçada não existe para quem está sozinho: o plantio é recusado em vez de gerar um gabarito falso
    with pytest.raises(ValueError, match="alcada impossível"):
        Dataset(seed=1, porte="mei", plantar=("alcada",))


def test_media_ii_applies_the_upper_band_rules():
    e = run_scenario("fechamento_media_ii")
    ds, p = e.system.dataset, perfil("media_ii")
    assert porte_por_receita(ds.gold["dre"]["receita"] * 12) == "media_ii"
    assert e.system.agentes["AG-ORC"].conhecimento["limiar_absoluto"] == p["limiar_desvio"]["absoluto"] == 2000000
    assert e.system.agentes["AG-CIN"].DESEJOS_PERMANENTES == p["pesos_cin"]
    assert _achados(e) == _gabarito(ds) and "alcada" in {a[0] for a in _achados(e)}
    assert [c["acao"] for c in ds.correcoes] == ["reaprovar"]
    assert e.resposta.performative == "inform" and e.resposta.content["status"] == "publicado"
    assert len(ds.gold["desvios"]) == 2


ESPERADO_SEGMENTO = {
    "fechamento_comercio": ("comercio", {"UN-LOJ": 80, "UN-ECO": 20}, "rateio-comercio-v1", "estornar"),
    "fechamento_servicos": ("servicos", {"UN-CON": 65, "UN-OPE": 35}, "rateio-servicos-v1", "reaprovar"),
    "fechamento_industria": ("industria", {"UN-L1": 70, "UN-L2": 30}, "rateio-industria-v1", "estornar"),
}


@pytest.mark.parametrize("nome", sorted(ESPERADO_SEGMENTO))
def test_segment_changes_accounts_costs_and_allocation_driver(nome):
    seg, pct, versao, acao = ESPERADO_SEGMENTO[nome]
    e = run_scenario(nome)
    ds, s = e.system.dataset, segmento(seg)
    assert CENARIOS[nome].segmento == seg and ds.segmento == seg and ds.rateio == pct
    # plano de contas e unidades do segmento chegam aos agentes (orçamento, lançamentos, produtos)
    assert [o["conta"] for o in ds.orcamento] == s["contas"] + [s["conta_chamariz"]]
    assert {lanc["conta"] for lanc in ds.lancamentos} <= set(s["contas"])
    assert {p["un"] for p in ds.produtos} == set(s["unidades"]) and [c["centro"] for c in ds.custos_fixos] == list(s["centros_custo"])
    # AG-CUS rateia os custos fixos pelo direcionador do segmento: o resultado por UN confere com o gabarito
    cus = e.system.agentes["AG-CUS"]
    assert cus.conhecimento["rateio"] == pct and cus.conhecimento["versao_rateio"] == versao
    custos = cus.estado["custos"][ds.competencia]
    assert custos["resultado_un"] == ds.gold["resultado_un"] and custos["proveniencia"]["versao_rateio"] == versao
    assert e.resposta.content["resultado"]["dre"] == ds.gold["dre"]
    meta = next(r for r in e.audit.records if r["kind"] == "meta")
    assert meta["segmento"]["segmento"] == seg and meta["segmento"]["versao_rateio"] == versao
    # o veto lista todas as inconformidades do gabarito e a correção sugerida destrava a publicação
    assert _achados(e) == _gabarito(ds)
    assert [c["acao"] for c in ds.correcoes] == [acao] and e.resposta.performative == "inform"
    assert porte_por_receita(ds.gold["dre"]["receita"] * 12) == "media"


def test_segment_cost_structure_is_consistent():
    comercio = Dataset(seed=7, segmento="comercio").gold["estrutura_custos"]
    e = comercio["estoque"]
    assert e["inicial"] + e["compras"] - e["final"] == e["cmv"] == comercio["custo_variavel_total"]
    servicos = Dataset(seed=7, segmento="servicos")
    est = servicos.gold["estrutura_custos"]
    assert sum(est["composicao"].values()) == est["custo_variavel_total"] and est["horas_mod"] > 0
    industria = Dataset(seed=7, segmento="industria")
    prod = industria.gold["estrutura_custos"]["custo_producao"]
    assert prod["total"] == prod["variavel"] + prod["cif_fixos"] and sum(prod["rateio_cif_fixos"].values()) == prod["cif_fixos"]
    assert set(industria.gold["estrutura_custos"]["composicao"]) == {"materia_prima", "mao_de_obra_direta", "cif_variaveis"}


def test_default_segment_keeps_the_dsm3_data_and_trace():
    assert SEGMENTOS[0] == SEGMENTO_PADRAO
    for seed in (1, 42, 1337):
        a, b = Dataset(seed=seed, plantar=("alcada", "desvio_irregular")), Dataset(seed=seed, segmento=SEGMENTO_PADRAO,
                                                                                   plantar=("alcada", "desvio_irregular"))
        assert (a.produtos, a.lancamentos, a.orcamento, a.gold) == (b.produtos, b.lancamentos, b.orcamento, b.gold)
        assert "estrutura_custos" not in a.gold and a.rateio == {"UN-A": 60, "UN-B": 40}
    padrao = run_scenario("fechar_mes")
    explicito = run_scenario(Scenario("fechar_mes", CENARIOS["fechar_mes"].descricao, "fechar_mes",
                                      segmento=SEGMENTO_PADRAO))
    assert padrao.hash == explicito.hash
    assert "segmento" not in next(r for r in padrao.audit.records if r["kind"] == "meta")

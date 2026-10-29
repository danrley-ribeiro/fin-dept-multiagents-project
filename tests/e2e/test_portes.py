"""Regras base e BDI por porte de empresa (micro, pequena, média, grande): TEST-36 e TEST-37.

As regras vêm de models/portes.yaml (LC 123/2006, BNDES, Lei 11.638/2007, ITG 1000, NBC TG 1000,
NBC TA 320, COSO 2013) e são percebidas pelos agentes pela tool MCP `normas.perfil`.
"""
import pytest

from fin_mas import baseline
from fin_mas.env.dataset import Dataset
from fin_mas.env.portes import PORTES, perfil, porte_por_receita
from fin_mas.env.scenarios import Scenario, run_scenario

pytestmark = pytest.mark.e2e


def _cin(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind and r.get("agente") == "AG-CIN"]


@pytest.mark.parametrize("porte", PORTES)
def test_rules_and_bdi_follow_company_size(porte):
    e = run_scenario(Scenario(f"alcada_{porte}", "alçada violada", "fechar_mes", porte=porte, plantar=("alcada",),
                              decisao_aprovador="corrigir"))
    ds, p = e.system.dataset, perfil(porte)
    # a receita anual simulada cai na faixa legal do porte
    assert porte_por_receita(ds.gold["dre"]["receita"] * 12) == porte
    # os agentes percebem o porte pela base normativa e ajustam conhecimento e pesos dos desejos
    for agente in ("AG-ORC", "AG-CIN"):
        assert any(r["kind"] == "belief" and r["agente"] == agente and r["chave"] == "porte" and r["depois"] == porte
                   for r in e.audit.records)
    cin = e.system.agentes["AG-CIN"]
    assert cin.DESEJOS_PERMANENTES == p["pesos_cin"]
    assert e.system.agentes["AG-ORC"].conhecimento["limiar_absoluto"] == p["limiar_desvio"]["absoluto"]
    # a utilidade dos planos de parecer reflete o peso do prazo do porte
    delib = _cin(e, "deliberation")[0]
    util = {o["plano"]: o["utilidade"] for o in delib["opcoes"]}
    assert util["P-APROVAR"] == 10 * (p["pesos_cin"]["conformidade"] + p["pesos_cin"]["prazo"])
    assert util["P-VETAR"] == 10 * p["pesos_cin"]["conformidade"]
    # todas as inconformidades do gabarito (plantadas e as naturais do porte) são detectadas, com a severidade do porte
    veto = next(r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto")
    achados = {(a["regra"], a["lancamento"], a["severidade"]) for a in veto["content"]["achados"]}
    assert achados == {(n["regra"], n["lancamento"], n["severidade"]) for n in ds.gold["nao_conformidades"]}
    # a correção sugerida destrava o fechamento em todos os portes
    assert e.resposta.performative == "inform" and e.system.dataset.correcoes


def test_micro_company_has_no_erp_and_compensating_control():
    e = run_scenario("fechamento_micro")
    # sem ERP: a tool do ERP é indisponível, o realizado vem da planilha e a proveniência aponta para Excel
    indisponivel = [r for r in e.audit.records if r["kind"] == "mcp_denied"]
    assert [(r["agente"], r["tool"], r["motivo"]) for r in indisponivel] == [
        ("AG-ORC", "erp.realizado_por_conta", "empresa sem ERP")]
    fontes = {r["chave"].split("[")[0]: r["fonte"] for r in e.audit.records
              if r["kind"] == "belief" and r["agente"] == "AG-ORC" and r["chave"].startswith("realizado[")}
    assert fontes == {"realizado": "planilha (empresa sem ERP)"}
    assert all(r["fonte"].startswith("mcp://excel/") for r in e.audit.records
               if r["kind"] == "mcp_call" and r["tool"] == "erp.lancamentos")
    # SoD inevitável (só a sócia aprova) não é crítica: vira ressalva consolidada com o controle compensatório
    r = e.resposta
    sod = [x for x in r.content["ressalvas"] if x.startswith("sod em")]
    assert len(sod) == 1 and "controle compensatório" in sod[0]
    # a alçada do assistente é crítica; a sócia pode reaprovar (controle compensatório)
    assert any("reaprovado por elisa" in n for n in r.content["notas"])


def test_large_company_treats_cutoff_as_critical():
    e = run_scenario("fechamento_grande")
    veto = next(r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto")
    assert [(a["regra"], a["severidade"]) for a in veto["content"]["achados"]] == [("competencia", "critica")]
    assert veto["content"]["correcoes_sugeridas"][0]["acao"] == "reclassificar"
    assert e.resposta.content["status"] == "publicado"  # reclassificado e reavaliado pelo AG-CIN
    # a mesma competência errada na média empresa é só ressalva, sem veto
    media = run_scenario(Scenario("corte_media", "competência", "fechar_mes", porte="media", plantar=("competencia",)))
    assert media.resposta.content["status"] == "publicado_com_ressalva"
    assert not [r for r in media.audit.records if r["kind"] == "send" and r["performative"] == "veto"]


@pytest.mark.parametrize("porte", PORTES)
def test_size_profile_is_legal_across_seeds_and_baseline_uses_same_rules(porte):
    for seed in range(1, 11):
        ds = Dataset(seed=seed, porte=porte, plantar=("desvio_orcamentario",))
        assert porte_por_receita(ds.gold["dre"]["receita"] * 12) == porte
        assert baseline.executar(ds, "avaliar_orcamento").sinalizadas == ds.gold["desvios"]

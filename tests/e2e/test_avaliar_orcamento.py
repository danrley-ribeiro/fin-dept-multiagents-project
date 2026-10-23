"""E2 — "avaliar orçamento" de ponta a ponta (complementa o TEST-05 do agente isolado)."""
import pytest

from fin_mas.env.scenarios import run_scenario

pytestmark = pytest.mark.e2e


def test_avaliacao_sinaliza_so_os_desvios_plantados():
    e = run_scenario("avaliar_orcamento")
    r = e.resposta
    assert r.performative == "inform"
    assert r.content["resultado"]["sinalizadas"] == e.system.dataset.gold["desvios"]
    assert "Desvios acima do limiar: " + ", ".join(e.system.dataset.gold["desvios"]) in r.content["relatorio"]
    assert list(r.content["dag"]) == ["orcamento", "relatorio"]


def test_avaliacao_nao_reserva_o_periodo_e_nao_consulta_custos():
    e = run_scenario("avaliar_orcamento")
    assert not [r for r in e.audit.records if r["kind"] == "lock"]
    assert not [r for r in e.audit.records if r["kind"] == "mcp_call" and r["agente"] in ("AG-CUS", "AG-CIN")]


def test_avaliacao_sem_desvios_informa_que_nao_ha():
    from fin_mas.env.scenarios import Scenario
    e = run_scenario(Scenario("sem_desvio", "sem plantio", "avaliar_orcamento"))
    assert "Nenhum desvio acima do limiar." in e.resposta.content["relatorio"]

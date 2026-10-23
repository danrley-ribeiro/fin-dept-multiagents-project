import pytest

from fin_mas.core.bus import Bus
from fin_mas.env.dataset import (
    LIMIAR_ABSOLUTO, LIMIAR_PERCENTUAL, Dataset, brl, mes_no_trimestre, ratear,
)
from fin_mas.mcp.gateway import MCPGateway, ToolDenied


def test_mesmo_seed_gera_os_mesmos_dados():
    a, b = Dataset(seed=42, plantar=("sod",)), Dataset(seed=42, plantar=("sod",))
    assert (a.produtos, a.orcamento, a.lancamentos, a.gold) == (b.produtos, b.orcamento, b.lancamentos, b.gold)


def test_seeds_diferentes_geram_dados_diferentes():
    assert Dataset(seed=1).produtos != Dataset(seed=2).produtos


def test_sem_plantio_nao_ha_inconformidade_nem_desvio():
    for seed in range(20):
        ds = Dataset(seed=seed)
        assert ds.gold["nao_conformidades"] == []
        assert ds.gold["desvios"] == []


def test_gold_dre_fecha_com_as_margens():
    ds = Dataset(seed=7)
    dre = ds.gold["dre"]
    assert dre["margem_contribuicao"] == sum(m["margem"] for m in ds.gold["margens_produto"].values())
    assert dre["ebitda"] == dre["margem_contribuicao"] - dre["custos_fixos"]
    assert sum(u["resultado"] for u in ds.gold["resultado_un"].values()) == dre["ebitda"]


def test_plantios_aparecem_no_gabarito():
    ds = Dataset(seed=3, plantar=("alcada", "sod", "duplicidade", "competencia", "desvio_orcamentario"))
    regras = {nc["regra"]: nc["severidade"] for nc in ds.gold["nao_conformidades"]}
    assert regras == {"alcada": "critica", "sod": "critica", "duplicidade": "critica", "competencia": "nao_critica"}
    assert len(ds.gold["desvios"]) == 2


def test_chamariz_fica_abaixo_do_limiar_absoluto():
    ds = Dataset(seed=3)
    chamariz = next(c for c in ds.orcamento if c["conta"].startswith("C-3005"))
    desvio = chamariz["realizado_acumulado"] - chamariz["orcado_acumulado"]
    assert desvio * 100 >= chamariz["orcado_acumulado"] * LIMIAR_PERCENTUAL
    assert desvio < LIMIAR_ABSOLUTO


def test_plantio_desconhecido_e_rejeitado():
    with pytest.raises(ValueError):
        Dataset(seed=1, plantar=("inexistente",))


def test_ratear_fecha_a_soma():
    partes = ratear(100_01, {"UN-A": 60, "UN-B": 40})
    assert sum(partes.values()) == 100_01


def test_brl_e_mes_no_trimestre():
    assert brl(1234567) == "R$ 12.345,67"
    assert brl(-5) == "-R$ 0,05"
    assert [mes_no_trimestre(f"2026-{m:02d}") for m in (7, 8, 9, 10)] == [1, 2, 3, 1]


def gateway(**kw):
    bus = Bus()
    return MCPGateway(Dataset(seed=1, **kw), bus.audit, bus), bus


def test_chamada_devolve_dados_com_proveniencia_e_audita():
    gw, bus = gateway()
    r = gw.call("AG-CUS", "erp.balancete", "DEL-001")
    assert r["proveniencia"]["fonte"] == "mcp://erp/balancete"
    assert r["proveniencia"]["seed"] == 1
    assert [x["kind"] for x in bus.audit.records] == ["mcp_call"]


def test_tool_fora_da_allowlist_e_negada_e_auditada():
    gw, bus = gateway()
    with pytest.raises(ToolDenied):
        gw.call("AG-CUS", "erp.lancamentos", "DEL-001")
    assert bus.audit.records[-1]["kind"] == "mcp_denied"


def test_agente_sem_allowlist_nao_acessa_nada():
    gw, _ = gateway()
    with pytest.raises(ToolDenied):
        gw.call("AG-REL", "erp.balancete", "DEL-001")

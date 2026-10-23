"""Custos e Orçamento respondendo a PROT-DEL e PROT-QRY (TEST-04 e TEST-05).

O solicitante é um cliente de teste; o Orquestrador entra no marco seguinte.
"""
import pytest

from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.core.bus import Bus
from fin_mas.env.dataset import Dataset
from fin_mas.mcp.gateway import MCPGateway
from helpers import Cliente

pytestmark = pytest.mark.e2e


def montar(seed=42, plantar=()):
    bus = Bus()
    ds = Dataset(seed=seed, plantar=tuple(plantar))
    gw = MCPGateway(ds, bus.audit, bus)
    return bus, ds, Cliente("CLI", bus), AgenteCustos(bus, gw), AgenteOrcamento(bus, gw)


def delegar(bus, cliente, receptor, tarefa, cid="DEL-001"):
    cliente.send(receptor, "request", "PROT-DEL", cid, {"tarefa": tarefa}, reply_by=bus.now + 20)
    bus.run()
    return cliente.por_performativo("inform", cid)[0].content


@pytest.mark.parametrize("seed", [1, 42, 2026])
def test_contribution_margin_matches_gold(seed):
    bus, ds, cli, cus, _ = montar(seed)
    r = delegar(bus, cli, "AG-CUS", "apurar_custos")
    assert r["margens_produto"] == ds.gold["margens_produto"]
    assert r["resultado_un"] == ds.gold["resultado_un"]
    # proveniência: fonte MCP, consulta e versão do rateio
    assert r["proveniencia"]["fonte"] == "mcp://erp/balancete"
    assert r["proveniencia"]["versao_rateio"] == "rateio-v1"
    assert r["proveniencia"]["consulta"]["competencia"] == ds.competencia


def test_custos_responde_agree_antes_do_inform():
    bus, _, cli, *_ = montar()
    delegar(bus, cli, "AG-CUS", "apurar_custos")
    assert [m.performative for m in cli.recebidas] == ["agree", "inform"]
    assert bus.conversations["DEL-001"].state == "CONCLUIDA"


def test_tarefa_desconhecida_vira_failure_explicito():
    bus, _, cli, *_ = montar()
    cli.send("AG-CUS", "request", "PROT-DEL", "DEL-001", {"tarefa": "voar"}, reply_by=bus.now + 20)
    bus.run()
    assert cli.por_performativo("failure")[0].content["motivo"].startswith("tarefa desconhecida")
    assert bus.conversations["DEL-001"].state == "FALHOU"


def test_budget_variance_flags_threshold():
    bus, ds, cli, _, orc = montar(seed=5, plantar=["desvio_orcamentario"])
    r = delegar(bus, cli, "AG-ORC", "orcado_x_realizado")
    assert r["sinalizadas"] == ds.gold["desvios"]
    assert len(r["sinalizadas"]) == 2
    # o chamariz passa no percentual mas não no valor absoluto: não é sinalizado
    chamariz = next(c for c in r["desvios"] if c["conta"].startswith("C-3005"))
    assert chamariz["desvio"] > 0 and not chamariz["sinalizado"]


def test_sem_desvio_plantado_nada_e_sinalizado():
    bus, ds, cli, _, orc = montar(seed=5)
    assert delegar(bus, cli, "AG-ORC", "orcado_x_realizado")["sinalizadas"] == []


def test_forecast_run_rate_e_reproduzivel():
    def rodar():
        bus, _, cli, *_ = montar(seed=9)
        return delegar(bus, cli, "AG-ORC", "orcado_x_realizado")

    a, b = rodar(), rodar()
    assert a["totais"]["forecast_trimestre"] == b["totais"]["forecast_trimestre"]
    # competência 2026-09 é o 3º mês do trimestre: forecast == realizado acumulado
    assert a["totais"]["forecast_trimestre"] == a["totais"]["realizado_acumulado"]


def test_query_ref_entre_pares_responde_do_estado():
    bus, ds, cli, cus, orc = montar()
    cli.send("AG-CUS", "query-ref", "PROT-QRY", "QRY-001", {"assunto": "custos_por_UN"}, reply_by=bus.now + 10)
    cli.send("AG-ORC", "query-ref", "PROT-QRY", "QRY-002", {"assunto": "desvios"}, reply_by=bus.now + 10)
    bus.run()
    assert cli.por_performativo("inform", "QRY-001")[0].content["resultado_un"] == ds.gold["resultado_un"]
    assert "desvios" in cli.por_performativo("inform", "QRY-002")[0].content
    assert bus.conversations["QRY-001"].state == "RESPONDIDA"


def test_query_ref_de_assunto_desconhecido_e_recusado():
    bus, _, cli, *_ = montar()
    cli.send("AG-CUS", "query-ref", "PROT-QRY", "QRY-001", {"assunto": "folha"}, reply_by=bus.now + 10)
    bus.run()
    assert bus.conversations["QRY-001"].state == "RECUSADA"

"""Resultados (query-ref), Controles Internos (veto) e Relatórios (template) em isolamento.

TEST-06, TEST-07 (lado do agente), TEST-09 e TEST-10; o fluxo completo vem com o Orquestrador.
"""
import pytest

from fin_mas.agents.cin import AgenteControlesInternos
from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.agents.rel import AgenteRelatorios
from fin_mas.agents.res import AgenteResultados
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import Dataset
from fin_mas.mcp.gateway import MCPGateway
from helpers import Cliente

pytestmark = pytest.mark.e2e


def montar(seed=42, plantar=(), faults=None):
    bus = Bus(faults=faults)
    ds = Dataset(seed=seed, plantar=tuple(plantar))
    gw = MCPGateway(ds, bus.audit, bus)
    agentes = [AgenteCustos(bus, gw), AgenteOrcamento(bus, gw), AgenteResultados(bus, gw),
               AgenteControlesInternos(bus, gw), AgenteRelatorios(bus, gw)]
    return bus, ds, Cliente("CLI", bus), agentes


def consolidar(bus, cli, cid="DEL-001"):
    cli.send("AG-RES", "request", "PROT-DEL", cid, {"tarefa": "consolidar_resultado"}, reply_by=bus.now + 40)
    bus.run()


def test_results_query_ref_to_costs():
    bus, ds, cli, _ = montar()
    consolidar(bus, cli)
    final = cli.por_performativo("inform", "DEL-001")[0].content
    assert final["dre"] == ds.gold["dre"]
    # ordem causal: as duas query-ref e seus inform precedem o inform final de AG-RES
    trilha = [(r["conversation_id"], r["performative"]) for r in bus.audit.records
              if r["kind"] == "send" or r["kind"] == "open"]
    posicao = {par: i for i, par in enumerate(trilha)}
    final_pos = posicao[("DEL-001", "inform")]
    for qid in ("QRY-001", "QRY-002"):
        assert posicao[(qid, "query-ref")] < posicao[(qid, "inform")] < final_pos
    assert {"AG-CUS", "AG-ORC"} == {r["receiver"] for r in bus.audit.records
                                    if r["kind"] == "open" and r["performative"] == "query-ref"}
    assert bus.conversations["QRY-001"].state == "RESPONDIDA"


def test_resultados_nao_acessa_orcamento_diretamente():
    bus, _, cli, _ = montar()
    consolidar(bus, cli)
    chamadas = {(r["agente"], r["tool"]) for r in bus.audit.records if r["kind"] == "mcp_call"}
    assert ("AG-ORC", "planilhas.orcamento") in chamadas
    assert ("AG-RES", "planilhas.orcamento") not in chamadas


def test_query_ref_expirada_vira_failure_ao_solicitante():
    bus, _, cli, _ = montar(faults=[Fault("AG-CUS", "query-ref", times=1)])
    consolidar(bus, cli)
    falha = cli.por_performativo("failure", "DEL-001")[0]
    assert "insumo indisponível (custos)" in falha.content["motivo"]
    assert bus.conversations["DEL-001"].state == "FALHOU"
    assert bus.conversations["QRY-001"].state == "EXPIRADA"


def test_query_ref_rejects_unsolicited_inform():
    from fin_mas.core.fsm import ProtocolViolation
    from fin_mas.core.message import Message
    bus, _, cli, _ = montar()
    with pytest.raises(ProtocolViolation, match="conversation_id desconhecido"):
        bus.send(Message("AG-CUS", "AG-RES", "inform", "QRY-777", "PROT-QRY", {"x": 1}))


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_planted_nonconformities_detected(seed):
    plantios = ["alcada", "sod", "duplicidade", "competencia"]
    bus, ds, cli, _ = montar(seed=seed, plantar=plantios)
    cli.send("AG-CIN", "request", "PROT-CMP", "CMP-001", {"tarefa": "compliance_check"})
    bus.run()
    veto = cli.por_performativo("veto")[0]
    achados = [{"regra": a["regra"], "lancamento": a["lancamento"], "severidade": a["severidade"]}
               for a in veto.content["achados"]]
    assert achados == ds.gold["nao_conformidades"]  # recall e precisão de 100%
    assert bus.conversations["CMP-001"].state == "VETADO"


def test_so_competencia_fora_do_periodo_libera_com_ressalva():
    bus, _, cli, _ = montar(plantar=["competencia"])
    cli.send("AG-CIN", "request", "PROT-CMP", "CMP-001", {"tarefa": "compliance_check"})
    bus.run()
    assert [m.performative for m in cli.recebidas] == ["nao_conforme_nao_critico"]
    assert bus.conversations["CMP-001"].state == "LIBERADO_COM_RESSALVA"


def test_pacote_conforme_e_liberado():
    bus, _, cli, _ = montar()
    cli.send("AG-CIN", "request", "PROT-CMP", "CMP-001", {"tarefa": "compliance_check"})
    bus.run()
    assert [m.performative for m in cli.recebidas] == ["conforme"]
    assert bus.conversations["CMP-001"].state == "LIBERADO"


def test_report_template_without_llm():
    bus, ds, cli, _ = montar()
    consolidar(bus, cli)
    r = cli.por_performativo("inform", "DEL-001")[0].content
    cli.send("AG-REL", "request", "PROT-DEL", "DEL-002", {
        "tarefa": "relatorio_executivo", "entidade": ds.entidade, "competencia": ds.competencia,
        "dre": r["dre"], "kpis": r["kpis"], "resultado_un": r["resultado_un"],
        "parecer": "conforme", "ressalvas": ["lançamento L-013 em competência anterior"],
    }, reply_by=bus.now + 20)
    bus.run()
    rel = cli.por_performativo("inform", "DEL-002")[0].content
    assert rel["modo"] == "template" and rel["versao_template"] == "tpl-exec-v1"
    assert "EBITDA" in rel["texto"] and "Ressalva: lançamento L-013" in rel["texto"]
    from fin_mas.env.dataset import brl
    assert brl(ds.gold["dre"]["ebitda"]) in rel["texto"]  # número vem do núcleo, igual ao gabarito


def test_relatorio_de_tarefa_desconhecida_falha_explicitamente():
    bus, _, cli, _ = montar()
    cli.send("AG-REL", "request", "PROT-DEL", "DEL-001", {"tarefa": "poesia"}, reply_by=bus.now + 20)
    bus.run()
    assert bus.conversations["DEL-001"].state == "FALHOU"

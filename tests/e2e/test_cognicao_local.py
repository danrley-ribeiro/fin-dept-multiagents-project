"""Cognição local do AG-ORC (ADR-008): proposta -> hipótese -> ação epistêmica -> evidência -> crença.

Tudo verificado em cenários completos, pelo trace e pela resposta final. Os cenários
revisados da DSM3 ficam no nível `basico`: o último bloco confere que nada mudou neles.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fin_mas import metricas
from fin_mas.agents.cin import AgenteControlesInternos
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.cognicao.regras import ProponenteLocal
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import Dataset
from fin_mas.env.scenarios import CENARIOS, run_scenario
from fin_mas.mcp.gateway import MCPGateway
from helpers import Cliente

pytestmark = pytest.mark.e2e
RAIZ = Path(__file__).resolve().parents[2]
COGNITIVOS = sorted(n for n, sc in CENARIOS.items() if sc.cognicao != "basico")
BASICOS = sorted(n for n, sc in CENARIOS.items() if sc.cognicao == "basico")
TOOLS_DA_COGNICAO = {"planilhas.observacoes", "erp.historico"}


def _eventos(e, kind, agente="AG-ORC"):
    return [r for r in e.audit.records if r["kind"] == kind and r.get("agente") == agente]


def _hipoteses(e):
    return [(r["evento"], r.get("tipo"), r.get("alvo")) for r in _eventos(e, "hipotese")]


def _consultas_ao_cin(e):
    return [c for c in e.system.bus.conversations.values()
            if c.protocol.id == "PROT-QRY" and c.counterpart == "AG-CIN"]


def test_local_hypothesis_triggers_verification_and_reclassifies():
    basico, local = run_scenario("orc_sem_cin"), run_scenario("orc_hipotese_local")
    ds = local.system.dataset
    conta = ds.gold["desvios_atribuidos"][0]
    # nível básico: a consulta se perde e o desvio é sinalizado como orçamentário (falso desvio)
    assert basico.resposta.content["resultado"]["sinalizadas"] == [conta]
    assert not _eventos(basico, "hipotese")
    # nível local: a observação da planilha vira hipótese, que leva a uma segunda consulta ao AG-CIN
    assert _hipoteses(local) == [("aceita", "causa_controle", conta), ("em_verificacao", "causa_controle", conta),
                                 ("confirmada", "causa_controle", conta)]
    aceita = _eventos(local, "hipotese")[0]
    assert aceita["origem"] == "local:R-OBS-REPETICAO" and aceita["regra"] == "NORM-11"
    assert [c.state for c in _consultas_ao_cin(local)] == ["EXPIRADA", "RESPONDIDA"]
    assert len(_consultas_ao_cin(local)) == len(_consultas_ao_cin(basico)) + 1  # custo: uma conversa a mais
    delib = next(r for r in _eventos(local, "deliberation") if r["desejo"].startswith("verificar_hipotese"))
    assert delib["escolhido"] == "P-VERIFICAR-COM-CIN"
    # a classificação muda pela crença que o AG-CIN sustentou, e passa a bater com o gabarito
    r = local.resposta.content
    assert r["resultado"]["sinalizadas"] == ds.gold["desvios"] == []
    assert r["resultado"]["atribuidas_a_controle"] == ds.gold["desvios_atribuidos"]
    assert not any("AG-CIN indisponível" in x for x in r["ressalvas"])
    assert r["hipoteses"][0]["estado"] == "confirmada" and r["hipoteses"][0]["verificacao"] == "AG-CIN (QRY-002)"
    assert "Insight: " + conta in r["relatorio"]
    confirmada = _eventos(local, "hipotese")[-1]
    assert confirmada["fonte"] == "AG-CIN (QRY-002)"
    # MET-18: uma hipótese, confirmada, com uma consulta a mais e nenhuma crença vinda do proponente
    m = metricas.medir_cognicao(local)
    assert (m["hipoteses"], m["confirmadas"], m["consultas_de_verificacao"], m["crencas_com_fonte_de_proponente"]) == (1, 1, 1, 0)
    assert metricas.medir_cognicao(basico)["propostas"] == 0


@pytest.mark.parametrize("nome", COGNITIVOS)
def test_hypothesis_never_writes_a_belief(nome):
    """Proposta não é crença: nenhuma crença tem um proponente como fonte, em nenhum cenário."""
    e = run_scenario(nome)
    if nome != "llm_provedor_fora":  # único cenário cognitivo sem nenhuma proposta (provedor fora do ar)
        assert _eventos(e, "hipotese"), "o cenário deveria registrar ao menos uma proposta"
    fontes = {r["fonte"] for a in ("AG-ORC", "AG-CIN") for r in _eventos(e, "belief", a)}
    assert not [f for f in fontes if f.startswith(("local:", "llm:"))]
    # o que muda a avaliação tem fonte determinística: o AG-CIN, uma tool MCP ou um plano de domínio
    for r in _eventos(e, "belief"):
        if r["chave"].startswith(("contestado[", "classificacao[", "padrao_calendario[")):
            assert r["fonte"].startswith(("AG-CIN", "plano P-", "cálculo sobre mcp://"))


def test_false_alarm_hypothesis_is_refuted_without_extra_messages():
    local = run_scenario("hipotese_refutada")
    basico = run_scenario("hipotese_refutada", cognicao="basico")
    assert [h[0] for h in _hipoteses(local)] == ["aceita", "refutada"]
    delib = next(r for r in _eventos(local, "deliberation") if r["desejo"].startswith("verificar_hipotese"))
    assert delib["escolhido"] == "P-CONFERIR-EVIDENCIA"  # usa a resposta que o AG-CIN já deu
    assert len(_consultas_ao_cin(local)) == len(_consultas_ao_cin(basico))
    assert local.resposta.content["resultado"] == basico.resposta.content["resultado"]
    assert local.resposta.content["resultado"]["sinalizadas"] == local.system.dataset.gold["desvios"]


def test_hypothesis_without_evidence_is_archived_and_changes_nothing():
    local = run_scenario("hipotese_arquivada")
    basico = run_scenario("hipotese_arquivada", cognicao="basico")
    assert [h[0] for h in _hipoteses(local)] == ["aceita", "em_verificacao", "arquivada"]
    # três consultas perdidas: a normal, a de verificação e a feita depois de negociar mais prazo
    assert [c.state for c in _consultas_ao_cin(local)] == ["EXPIRADA", "EXPIRADA", "EXPIRADA"]
    for campo in ("resultado", "ressalvas", "status"):
        assert local.resposta.content[campo] == basico.resposta.content[campo]
    assert any("AG-CIN indisponível" in x for x in local.resposta.content["ressalvas"])


def test_calendar_pattern_is_confirmed_by_history_not_by_the_rule():
    e = run_scenario("historico_calendario")
    conta = e.system.dataset.gold["sazonais"][0]
    eventos = _eventos(e, "hipotese")
    assert [(r["evento"], r["tipo"]) for r in eventos] == [("aceita", "efeito_temporal"),
                                                           ("corroborada", "efeito_temporal"),
                                                           ("confirmada", "efeito_temporal")]
    assert {eventos[0]["origem"], eventos[1]["origem"]} == {"local:R-OBS-RECORRENCIA", "local:R-HIST-PICO"}
    padrao = next(r for r in _eventos(e, "belief") if r["chave"].startswith("padrao_calendario["))
    assert padrao["fonte"] == "cálculo sobre mcp://erp/historico" and padrao["depois"]["confirmado"]
    assert padrao["depois"]["trimestres"] == padrao["depois"]["repetiu"] == padrao["depois"]["fechou_no_orcado"] == 2
    # o desvio continua sinalizado (a hipótese não reclassifica); o que entra é a ressalva de calendário
    r = e.resposta.content
    assert r["resultado"]["sinalizadas"] == [conta] == e.system.dataset.gold["desvios"]
    assert any("efeito de calendário" in x for x in r["ressalvas"])


def test_calendar_hypothesis_is_refuted_when_history_does_not_repeat():
    """Mesma observação de recorrência, mas o histórico não mostra o padrão: refutada."""
    sc = CENARIOS["historico_calendario"]
    e = run_scenario(sc)
    orc = e.system.agentes["AG-ORC"]
    from fin_mas.agents.orc import padrao_de_calendario
    serie = orc.crencas.get(next(k for k in orc.crencas.snapshot() if k.startswith("historico[")))
    plano = [dict(m, realizado=m["orcado"]) for m in serie]  # histórico sem pico
    assert padrao_de_calendario(serie, 1, 10)["confirmado"]
    assert not padrao_de_calendario(plano, 1, 10)["confirmado"]
    assert not padrao_de_calendario(serie[:3], 1, 10)["confirmado"]  # um trimestre só não basta


def test_full_closing_with_local_cognition_reaches_approved_correction():
    e = run_scenario("fechamento_hipotese_local")
    assert [h[0] for h in _hipoteses(e)] == ["aceita", "em_verificacao", "confirmada"]
    r = e.resposta
    assert r.performative == "inform" and "Insight: " in r.content["relatorio"]
    assert [c["acao"] for c in e.system.dataset.correcoes] == ["estornar"]


class ClienteQueNegocia(Cliente):
    """Solicitante de teste que responde às propostas de prazo como o Orquestrador responderia."""

    def __init__(self, agent_id, bus, aceita):
        super().__init__(agent_id, bus)
        self.aceita = aceita

    def on_message(self, msg):
        super().on_message(msg)
        if msg.performative == "propose":
            if self.aceita:
                novo = self.bus.prazos[msg.conversation_id] + msg.content["prazo_extra"]
                self.send(msg.sender, "accept-proposal", "PROT-DEL", msg.conversation_id, {"prazo": novo}, reply_by=novo)
            else:
                self.send(msg.sender, "reject-proposal", "PROT-DEL", msg.conversation_id, {"motivo": "sem folga"})


def _orcamento_isolado(prazo, aceita=False):
    bus = Bus(faults=[Fault(receiver="AG-CIN", performative="query-ref", times=1)])
    ds = Dataset(seed=42, plantar=("desvio_irregular",))
    gw = MCPGateway(ds, bus.audit, bus)
    cliente, orc = ClienteQueNegocia("CLI", bus, aceita), AgenteOrcamento(bus, gw)
    AgenteControlesInternos(bus, gw)
    orc.proponentes.append(ProponenteLocal())
    cliente.send("AG-ORC", "request", "PROT-DEL", "DEL-001",
                 {"tarefa": "orcado_x_realizado", "entidade": "SMA", "competencia": "2026-09"},
                 reply_by=bus.now + prazo)
    bus.run()
    return bus, cliente, orc


def test_epistemic_action_respects_requester_deadline():
    """Prazo curto: a nova consulta não cabe. O agente pede prazo; recusado, arquiva e responde no prazo original."""
    bus, cliente, orc = _orcamento_isolado(prazo=20)
    delib = next(r for r in bus.audit.records if r["kind"] == "deliberation"
                 and r["desejo"].startswith("verificar_hipotese"))
    motivos = {o["plano"]: o["motivo"] for o in delib["opcoes"]}
    assert delib["escolhido"] == "P-NEGOCIAR-PRAZO"
    assert motivos["P-VERIFICAR-COM-CIN"].startswith("não cabe no prazo do solicitante")
    assert next(iter(orc.hipoteses.values())).estado == "arquivada"
    (entrega,) = cliente.por_performativo("inform", "DEL-001")
    assert bus.conversations["DEL-001"].state == "CONCLUIDA"
    assert next(r["t"] for r in bus.audit.records if r["kind"] == "send" and r["performative"] == "inform"
                and r["conversation_id"] == "DEL-001") < 20
    assert any("AG-CIN indisponível" in x for x in entrega.content["ressalvas"])
    assert len([c for c in bus.conversations.values() if c.protocol.id == "PROT-QRY"]) == 1  # nenhuma consulta fora do prazo
    # com prazo folgado, a mesma situação leva direto à verificação, sem negociar
    bus2, _, orc2 = _orcamento_isolado(prazo=60)
    assert next(iter(orc2.hipoteses.values())).estado == "confirmada"
    assert not [r for r in bus2.audit.records if r.get("performative") == "propose"]
    # prazo curto e solicitante que aceita: a consulta acontece dentro do prazo estendido
    bus3, cliente3, orc3 = _orcamento_isolado(prazo=20, aceita=True)
    assert next(iter(orc3.hipoteses.values())).estado == "confirmada"
    assert bus3.conversations["DEL-001"].state == "CONCLUIDA" and cliente3.por_performativo("inform", "DEL-001")


@pytest.mark.parametrize("nome", BASICOS)
def test_basic_cognition_has_no_hypotheses_and_no_extra_perception(nome):
    """Os cenários revisados não ganham registro novo: sem hipóteses e sem as tools da cognição."""
    e = run_scenario(nome)
    assert not [r for r in e.audit.records if r["kind"] == "hipotese"]
    assert not [r for r in e.audit.records if r["kind"] == "mcp_call" and r["tool"] in TOOLS_DA_COGNICAO]
    meta = next(r for r in e.audit.records if r["kind"] == "meta")
    assert "cognicao" not in meta
    resposta = e.resposta.content
    assert "hipoteses" not in resposta and "insights" not in resposta


def test_cli_runs_a_reviewed_scenario_at_local_level():
    """Terminal: `--cognicao local` liga a cognição num cenário que por padrão roda no nível básico."""
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
    saida = subprocess.run([sys.executable, "-m", "fin_mas", "run", "--scenario", "orc_sem_cin", "--cognicao", "local"],
                           capture_output=True, text=True, env=env, check=True, cwd=RAIZ).stdout
    assert "HIPOTESE AG-ORC: AG-ORC-H001 causa_controle(C-3002 Marketing) confirmada" in saida
    assert "Insight: C-3002 Marketing" in saida and "Desvios atribuídos a lançamentos irregulares" in saida

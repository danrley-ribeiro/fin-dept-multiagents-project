"""E6 — TEST-26: um reenvio e, na segunda falha, failure explícito."""
import pytest

from fin_mas.env.scenarios import Scenario, run_scenario

pytestmark = pytest.mark.e2e


def conversas_com(e, agente):
    return [c for c in e.system.bus.conversations.values() if c.counterpart == agente]


def test_specialist_failure_retry_then_abort():
    e = run_scenario("falha_especialista")
    r = e.resposta
    assert r.performative == "failure"
    assert r.content["subtarefa"] == "custos" and r.content["motivo"] == "timeout"
    assert r.content["publicado"] is False
    # um reenvio: duas conversas com AG-CUS, ambas expiradas
    assert [c.state for c in conversas_com(e, "AG-CUS")] == ["EXPIRADA", "EXPIRADA"]
    # nada além de AG-ORC foi delegado depois; nada publicado
    assert not conversas_com(e, "AG-RES") and not conversas_com(e, "AG-REL") and not conversas_com(e, "AG-CIN")
    assert e.system.bus.conversations[e.sid].state == "FALHOU"
    assert e.system.locks.dono("SMA", "2026-09") is None  # reserva liberada
    regras = [r["regra"] for r in e.audit.records if r["kind"] == "decision" and r["agente"] == "AG-ORQ"]
    assert "um reenvio por subtarefa expirada ou falha" in regras
    assert "segunda falha (ou recusa) aborta a solicitação" in regras


def test_uma_falha_e_reenviada_e_a_solicitacao_conclui():
    e = run_scenario(Scenario("uma_falha", "AG-CUS perde um request", "fechar_mes",
                              faults=({"receiver": "AG-CUS", "performative": "request", "times": 1},)))
    assert e.resposta.performative == "inform"
    custos = e.resposta.content["dag"]["custos"]
    assert custos["tentativas"] == 2
    assert [e.system.bus.conversations[c].state for c in custos["conversas"]] == ["EXPIRADA", "CONCLUIDA"]
    assert e.system.locks.dono("SMA", "2026-09") is None


def test_controles_internos_silencioso_tambem_reenvia_uma_vez_e_aborta():
    e = run_scenario(Scenario("cin_mudo", "AG-CIN não responde", "fechar_mes",
                              faults=({"receiver": "AG-CIN", "performative": "request", "times": 2},)))
    assert e.resposta.performative == "failure" and e.resposta.content["subtarefa"] == "conformidade"
    assert len(conversas_com(e, "AG-CIN")) == 2
    assert not conversas_com(e, "AG-REL")  # sem parecer, nada é publicado


def test_resposta_de_tentativa_anterior_e_ignorada():
    # a resposta da 1ª tentativa chega depois do reenvio: o resultado vem só da última conversa
    e = run_scenario(Scenario("uma_falha", "AG-ORC perde um request", "fechar_mes",
                              faults=({"receiver": "AG-ORC", "performative": "request", "times": 1},)))
    assert e.resposta.performative == "inform"
    assert e.resposta.content["dag"]["orcamento"]["tentativas"] == 2


@pytest.mark.parametrize("agente, protocolo, performativo, conteudo", [
    ("AG-RES", "PROT-DEL", "inform", {}),
    ("AG-CIN", "PROT-CMP", "veto", {"achados": [1, 2], "opcoes": [], "correcoes_sugeridas": []}),
])
def test_malformed_nested_payload_from_a_specialist_becomes_an_explicit_failure(agente, protocolo, performativo,
                                                                                conteudo):
    """Correção simulada da v0.5.0 (M3): conteúdo aninhado inválido deixava o solicitante sem resposta e o
    período reservado. O Orquestrador aborta com `failure` e libera a reserva."""
    from fin_mas.env.scenarios import build_system

    s = build_system(plantar=("alcada",) if agente == "AG-CIN" else ())
    original = s.agentes[agente].on_message

    def defeituoso(msg):  # o especialista responde com um payload que passa no esquema de primeiro nível
        if msg.protocol == protocolo and msg.performative == "request":
            if protocolo == "PROT-DEL":
                s.agentes[agente].send(msg.sender, "agree", protocolo, msg.conversation_id, {})
            s.agentes[agente].send(msg.sender, performativo, protocolo, msg.conversation_id, conteudo)
        else:
            original(msg)

    s.agentes[agente].on_message = defeituoso
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r is not None and r.performative == "failure" and r.content["publicado"] is False
    assert "resposta malformada" in r.content["motivo"]
    assert s.locks.dono(s.dataset.entidade, s.dataset.competencia) is None  # período liberado


@pytest.mark.parametrize("nome, montagem, falha, esperado", [
    ("resposta final de uma delegação", {}, {"receiver": "AG-ORQ", "performative": "inform", "times": 1,
                                             "protocol": "PROT-DEL"}, "publicado"),
    ("resposta final perdida três vezes", {}, {"receiver": "AG-ORQ", "performative": "inform", "times": 3,
                                               "protocol": "PROT-DEL"}, "failure"),
    ("parecer do AG-CIN", {}, {"receiver": "AG-ORQ", "performative": "conforme", "times": 1}, "publicado"),
    ("veto do AG-CIN", {"plantar": ("alcada",), "decisao_aprovador": "corrigir"},
     {"receiver": "AG-ORQ", "performative": "veto", "times": 1}, "publicado"),
    ("correção enviada ao AG-CIN", {"plantar": ("alcada",), "decisao_aprovador": "corrigir"},
     {"receiver": "AG-CIN", "performative": "correcao", "times": 1}, "publicado"),
])
def test_message_lost_after_the_opening_never_leaves_the_requester_without_an_answer(nome, montagem, falha, esperado):
    """Achado do experimento da DSM4: a FSM avança no envio; se a resposta final de um especialista (ou uma
    mensagem do meio do PROT-CMP) se perdia na entrega, o Orquestrador esperava para sempre e o solicitante
    ficava sem resposta. O barramento avisa o iniciador, que reenvia uma vez ou falha de forma explícita."""
    from fin_mas import invariantes
    from fin_mas.env.scenarios import build_system

    s = build_system(faults=(falha,), **montagem)
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r is not None, nome
    if esperado == "failure":
        assert r.performative == "failure" and r.content["publicado"] is False
    else:
        assert r.performative == "inform" and r.content["status"].startswith("publicado")
    assert [x for x in s.bus.audit.records if x["kind"] == "drop"]
    assert [x for x in s.bus.audit.records if x["kind"] == "timeout" and x["de"] == x["para"]]  # aviso sem transição
    assert invariantes.verificar(s.bus.audit.records) == []
    assert s.locks.dono("SMA", "2026-09") is None

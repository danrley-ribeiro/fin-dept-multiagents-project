import pytest

from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message


class Eco(Agent):
    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.recebidas = []

    def on_message(self, msg):
        self.recebidas.append((self.bus.now, msg.performative))


def sistema(**kw):
    bus = Bus(**kw)
    return bus, Eco("A", bus), Eco("B", bus)


def msg(perf, cid="DEL-001", origem="A", destino="B", proto="PROT-DEL", **kw):
    return Message(origem, destino, perf, cid, proto, **kw)


def test_entrega_em_ordem_pelo_relogio_logico():
    bus, a, b = sistema()
    bus.send(msg("request"))
    bus.run()
    bus.send(msg("agree", origem="B", destino="A"))
    bus.run()
    assert b.recebidas == [(1, "request")]
    assert a.recebidas == [(2, "agree")]
    assert bus.conversations["DEL-001"].state == "EM_EXECUCAO"


def test_inform_antes_de_agree_levanta_violacao():
    bus, *_ = sistema()
    bus.send(msg("request"))
    with pytest.raises(ProtocolViolation, match="resultado antes de agree"):
        bus.send(msg("inform", origem="B", destino="A"))


def test_inform_com_conversation_id_desconhecido_e_rejeitado():
    bus, *_ = sistema()
    with pytest.raises(ProtocolViolation, match="conversation_id desconhecido"):
        bus.send(msg("inform", cid="QRY-099", proto="PROT-QRY", origem="B", destino="A"))


def test_terceiro_nao_participa_da_conversa():
    bus, *_ = sistema()
    Eco("C", bus)
    bus.send(msg("request"))
    with pytest.raises(ProtocolViolation, match="não participa"):
        bus.send(msg("agree", origem="C", destino="A"))


def test_reply_by_expira_a_conversa_e_avisa_o_iniciador():
    bus, a, b = sistema()
    bus.send(msg("request", reply_by=5))
    bus.run()
    assert bus.conversations["DEL-001"].state == "EXPIRADA"
    assert a.recebidas == [(5, "timeout")]


def test_resposta_apos_reply_by_e_descartada():
    bus, a, b = sistema()
    bus.send(msg("request", reply_by=3))
    bus.run()
    bus.send(msg("agree", origem="B", destino="A"))
    bus.run()
    assert [p for _, p in a.recebidas] == ["timeout"]
    assert any(r["kind"] == "discard" for r in bus.audit.records)


def test_conversa_concluida_nao_expira():
    bus, a, b = sistema()
    bus.send(msg("request", reply_by=10))
    bus.send(msg("agree", origem="B", destino="A"))
    bus.send(msg("inform", origem="B", destino="A"))
    bus.run()
    assert bus.conversations["DEL-001"].state == "CONCLUIDA"
    assert "timeout" not in [p for _, p in a.recebidas]


def test_falha_injetada_descarta_na_entrega_e_a_conversa_expira():
    bus, a, b = sistema(faults=[Fault("B", "request", times=1)])
    bus.send(msg("request", reply_by=4))
    bus.run()
    assert b.recebidas == []
    assert a.recebidas == [(4, "timeout")]
    assert any(r["kind"] == "drop" for r in bus.audit.records)


def test_advance_aplica_transicao_local():
    bus, *_ = sistema()
    bus.send(msg("request", cid="CMP-001", proto="PROT-CMP"))
    bus.send(msg("veto", cid="CMP-001", proto="PROT-CMP", origem="B", destino="A"))
    assert bus.advance("CMP-001", "prazo_esgotado", "A") == "BLOQUEADO"


def test_mensagem_de_interface_nao_passa_pela_fsm():
    bus, a, b = sistema()
    bus.send(Message("A", "B", "notify", "UI-001", None, {"x": 1}))
    bus.run()
    assert b.recebidas == [(1, "notify")]


def test_protocolo_sem_timeout_avisa_o_iniciador_se_a_contraparte_nao_respondeu():
    bus, a, b = sistema(faults=[Fault("B", "request", times=1)])
    bus.send(msg("request", cid="CMP-001", proto="PROT-CMP", reply_by=6))
    bus.run()
    assert a.recebidas == [(6, "timeout")]
    assert bus.conversations["CMP-001"].state == "EM_ANALISE"  # FSM intacta


def test_protocolo_sem_timeout_nao_avisa_depois_que_a_contraparte_respondeu():
    bus, a, b = sistema()
    bus.send(msg("request", cid="CMP-001", proto="PROT-CMP", reply_by=6))
    bus.send(msg("veto", cid="CMP-001", proto="PROT-CMP", origem="B", destino="A"))
    bus.run()
    assert [p for _, p in a.recebidas] == ["veto"]

import pytest

from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault, MensagemRejeitada
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message


class Eco(Agent):
    def __init__(self, agent_id, bus, papel):
        super().__init__(agent_id, bus, papel)
        self.recebidas = []

    def on_message(self, msg):
        self.recebidas.append((self.bus.now, msg.performative))


def sistema(**kw):
    bus = Bus(**kw)
    return bus, Eco("A", bus, "ROLE-ORQ"), Eco("B", bus, "ROLE-CIN")


DEL = {"tarefa": "t", "entidade": "SMA", "competencia": "2026-09"}


def enviar(agente, perf, destino, cid="DEL-001", proto="PROT-DEL", content=None, **kw):
    if content is None:
        content = dict(DEL) if perf == "request" else ({"achados": [], "opcoes": [], "correcoes_sugeridas": []}
                                                       if perf == "veto" else {})
    agente.send(destino, perf, proto, cid, content, **kw)


def test_entrega_em_ordem_pelo_relogio_logico():
    bus, a, b = sistema()
    enviar(a, "request", "B")
    bus.run()
    enviar(b, "agree", "A")
    bus.run()
    assert b.recebidas == [(1, "request")]
    assert a.recebidas == [(2, "agree")]
    assert bus.conversations["DEL-001"].state == "EM_EXECUCAO"


def test_inform_antes_de_agree_levanta_violacao():
    bus, a, b = sistema()
    enviar(a, "request", "B")
    with pytest.raises(ProtocolViolation, match="resultado antes de agree"):
        enviar(b, "inform", "A")


def test_inform_com_conversation_id_desconhecido_e_rejeitado():
    bus, a, b = sistema()
    Eco("R", bus, "ROLE-RES")
    with pytest.raises(ProtocolViolation, match="conversation_id desconhecido"):
        enviar(b, "inform", "R", cid="QRY-099", proto="PROT-QRY", content={"proveniencia": {}})


def test_terceiro_nao_participa_da_conversa():
    bus, a, b = sistema()
    c = Eco("C", bus, "ROLE-CUS")
    enviar(a, "request", "B")
    with pytest.raises(ProtocolViolation, match="não participa"):
        enviar(c, "agree", "A")


def test_reply_by_expira_a_conversa_e_avisa_o_iniciador():
    bus, a, b = sistema()
    enviar(a, "request", "B", reply_by=5)
    bus.run()
    assert bus.conversations["DEL-001"].state == "EXPIRADA"
    assert a.recebidas == [(5, "timeout")]


def test_resposta_apos_reply_by_e_descartada():
    bus, a, b = sistema()
    enviar(a, "request", "B", reply_by=3)
    bus.run()
    enviar(b, "agree", "A")
    bus.run()
    assert [p for _, p in a.recebidas] == ["timeout"]
    assert any(r["kind"] == "discard" for r in bus.audit.records)


def test_conversa_concluida_nao_expira():
    bus, a, b = sistema()
    enviar(a, "request", "B", reply_by=10)
    enviar(b, "agree", "A")
    enviar(b, "inform", "A")
    bus.run()
    assert bus.conversations["DEL-001"].state == "CONCLUIDA"
    assert "timeout" not in [p for _, p in a.recebidas]


def test_falha_injetada_descarta_na_entrega_e_a_conversa_expira():
    bus, a, b = sistema(faults=[Fault("B", "request", times=1)])
    enviar(a, "request", "B", reply_by=4)
    bus.run()
    assert b.recebidas == []
    assert a.recebidas == [(4, "timeout")]
    assert any(r["kind"] == "drop" for r in bus.audit.records)


def test_advance_aplica_transicao_local():
    bus, a, b = sistema()
    enviar(a, "request", "B", cid="CMP-001", proto="PROT-CMP")
    enviar(b, "nao_conforme_nao_critico", "A", cid="CMP-001", proto="PROT-CMP", content={"achados": []})
    assert a.avancar("CMP-001", "publicar") == "LIBERADO"


def test_mensagem_sem_protocolo_e_rejeitada():
    """DSM3: o canal livre (protocol=None) deixou de existir; avisos e decisões têm protocolo."""
    bus, a, b = sistema()
    with pytest.raises(MensagemRejeitada, match="sem protocolo"):
        enviar(a, "notify", "B", cid="UI-001", proto=None, content={"x": 1})
    bus.run()
    assert b.recebidas == []


def test_protocolo_sem_timeout_avisa_o_iniciador_se_a_contraparte_nao_respondeu():
    bus, a, b = sistema(faults=[Fault("B", "request", times=1)])
    enviar(a, "request", "B", cid="CMP-001", proto="PROT-CMP", reply_by=6)
    bus.run()
    assert a.recebidas == [(6, "timeout")]
    assert bus.conversations["CMP-001"].state == "EM_ANALISE"  # FSM intacta


def test_protocolo_sem_timeout_nao_avisa_depois_que_a_contraparte_respondeu():
    bus, a, b = sistema()
    enviar(a, "request", "B", cid="CMP-001", proto="PROT-CMP", reply_by=6)
    enviar(b, "veto", "A", cid="CMP-001", proto="PROT-CMP")
    bus.run()
    assert [p for _, p in a.recebidas] == ["veto"]


def test_mensagem_crua_sem_credencial_e_rejeitada():
    bus, a, b = sistema()
    with pytest.raises(MensagemRejeitada, match="não autenticado"):
        bus.send(Message("A", "B", "request", "DEL-001", "PROT-DEL", dict(DEL)))
    assert "DEL-001" not in bus.conversations

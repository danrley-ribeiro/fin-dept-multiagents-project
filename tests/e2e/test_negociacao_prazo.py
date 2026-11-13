"""Negociação de prazo no PROT-DEL (DSM3): o especialista propõe, o Orquestrador aceita ou recusa.

Em vez de estourar o tempo e falhar, o agente que precisa de mais prazo para buscar uma evidência
pede uma extensão justificada. Quem coordena decide com regras próprias: só prazo é negociável,
uma extensão por subtarefa, dentro de um teto, e nenhuma num fechamento com período reservado.
"""
import pytest

from fin_mas.agents.orq import MAX_EXTENSAO, PRAZO_SUBTAREFA
from fin_mas.core.bus import MensagemRejeitada
from fin_mas.env.scenarios import CENARIOS, montar, run_scenario

pytestmark = pytest.mark.e2e


def reg(e, kind=None, **campos):
    return [r for r in e.audit.records if (kind is None or r["kind"] == kind)
            and all(r.get(k) == v for k, v in campos.items())]


def test_specialist_negotiates_deadline_and_orchestrator_accepts():
    basico = run_scenario("negociacao_prazo", cognicao="basico")
    e = run_scenario("negociacao_prazo")
    ds = e.system.dataset
    (proposta,) = reg(e, "send", performative="propose")
    assert (proposta["sender"], proposta["receiver"], proposta["de"], proposta["para"]) == \
        ("AG-ORC", "AG-ORQ", "EM_EXECUCAO", "NEGOCIANDO")
    assert proposta["content"]["tipo"] == "mais_prazo" and "hipótese AG-ORC-H001" in proposta["content"]["motivo"]
    (aceite,) = reg(e, "send", performative="accept-proposal")
    assert aceite["sender"] == "AG-ORQ" and aceite["para"] == "EM_EXECUCAO"
    original = next(r for r in reg(e, "open", protocol="PROT-DEL") if r["receiver"] == "AG-ORC")["t"] + PRAZO_SUBTAREFA
    assert aceite["content"]["prazo"] == original + proposta["content"]["prazo_extra"]
    decisao = next(r for r in reg(e, "decision", agente="AG-ORQ") if "negociação de prazo" in r["regra"])
    assert decisao["resultado"] == {"novo_prazo": aceite["content"]["prazo"]}
    # com o prazo estendido, a terceira consulta é respondida e a hipótese é confirmada
    consultas = [c.state for c in e.system.bus.conversations.values() if c.protocol.id == "PROT-QRY"]
    assert consultas == ["EXPIRADA", "EXPIRADA", "RESPONDIDA"]
    assert [r["evento"] for r in reg(e, "hipotese")] == ["aceita", "em_verificacao", "confirmada"]
    r = e.resposta.content
    assert r["resultado"]["sinalizadas"] == ds.gold["desvios"] == []
    assert r["resultado"]["atribuidas_a_controle"] == ds.gold["desvios_atribuidos"]
    # sem a negociação (nível básico) o mesmo cenário termina com um falso desvio
    assert basico.resposta.content["resultado"]["sinalizadas"] == ds.gold["desvios_atribuidos"]
    assert not reg(basico, "send", performative="propose")


def test_orchestrator_refuses_extension_when_the_period_is_reserved():
    e = run_scenario("negociacao_recusada")
    (recusa,) = reg(e, "send", performative="reject-proposal")
    assert "período reservado" in recusa["content"]["motivo"] and recusa["para"] == "EM_EXECUCAO"
    assert not reg(e, "send", performative="accept-proposal")
    assert [r["evento"] for r in reg(e, "hipotese")] == ["aceita", "em_verificacao", "arquivada"]
    cid = recusa["conversation_id"]
    entrega = next(r for r in reg(e, "send", performative="inform", conversation_id=cid))
    aberta = next(r for r in reg(e, "open", conversation_id=cid))
    assert entrega["t"] < aberta["t"] + PRAZO_SUBTAREFA  # sem extensão, entrega dentro do prazo original
    assert not reg(e, "timeout", conversation_id=cid)
    # o fechamento segue: o AG-CIN veta a NF duplicada e o estorno aprovado destrava a publicação
    assert e.resposta.performative == "inform" and [c["acao"] for c in e.system.dataset.correcoes] == ["estornar"]


def test_extended_deadline_replaces_the_original_timer():
    """Trabalho que passa do prazo original, dentro do prazo estendido, não é expirado pelo temporizador antigo."""
    e = run_scenario("hipotese_arquivada")
    aberta = next(r for r in reg(e, "open", protocol="PROT-DEL") if r["receiver"] == "AG-ORC")
    cid, original = aberta["conversation_id"], aberta["t"] + PRAZO_SUBTAREFA
    entrega = next(r for r in reg(e, "send", performative="inform", conversation_id=cid))
    assert entrega["t"] > original and e.system.bus.conversations[cid].state == "CONCLUIDA"
    assert not reg(e, "timeout", conversation_id=cid) and not reg(e, "discard", conversation_id=cid)
    assert e.resposta.performative == "inform"


def _ate(sistema, condicao, limite=5000):
    for _ in range(limite):
        if condicao():
            return
        if not sistema.bus.step():
            break
    raise AssertionError("a condição esperada não aconteceu")


@pytest.mark.parametrize("conteudo, trecho", [
    ({"tipo": "mais_prazo", "prazo_extra": MAX_EXTENSAO + 1, "motivo": "quero bem mais tempo"}, "fora do teto"),
    ({"tipo": "mais_prazo", "prazo_extra": 0, "motivo": "extensão nula"}, "fora do teto"),
    ({"tipo": "parcial", "prazo_extra": 5, "motivo": "entrego só uma parte"}, "só o prazo é negociável"),
])
def test_orchestrator_rules_for_proposals(conteudo, trecho):
    sistema, _ = montar(CENARIOS["avaliar_orcamento"])
    bus, orc = sistema.bus, sistema.agentes["AG-ORC"]
    _ate(sistema, lambda: "DEL-001" in bus.conversations and bus.conversations["DEL-001"].state == "EM_EXECUCAO")
    orc.send("AG-ORQ", "propose", "PROT-DEL", "DEL-001", conteudo)
    _ate(sistema, lambda: any(r["kind"] == "send" and r["performative"] == "reject-proposal" for r in bus.audit.records))
    recusa = next(r for r in bus.audit.records if r["kind"] == "send" and r["performative"] == "reject-proposal")
    assert trecho in recusa["content"]["motivo"]
    bus.run()
    assert sistema.usuario.recebidas[-1].performative == "inform"  # a negociação recusada não derruba o pedido


def test_only_one_extension_per_subtask():
    sistema, _ = montar(CENARIOS["negociacao_prazo"])
    bus, orc = sistema.bus, sistema.agentes["AG-ORC"]
    _ate(sistema, lambda: any(r["kind"] == "deliver" and r["performative"] == "accept-proposal" for r in bus.audit.records))
    orc.send("AG-ORQ", "propose", "PROT-DEL", "DEL-001", {"tipo": "mais_prazo", "prazo_extra": 5, "motivo": "de novo"})
    _ate(sistema, lambda: any(r["kind"] == "send" and r["performative"] == "reject-proposal" for r in bus.audit.records))
    recusa = next(r for r in bus.audit.records if r["kind"] == "send" and r["performative"] == "reject-proposal")
    assert "já teve uma extensão" in recusa["content"]["motivo"]


def test_protocol_rejects_negotiation_out_of_order_or_by_the_wrong_role():
    sistema, _ = montar(CENARIOS["avaliar_orcamento"])
    bus, orc, orq = sistema.bus, sistema.agentes["AG-ORC"], sistema.orq
    proposta = {"tipo": "mais_prazo", "prazo_extra": 5, "motivo": "teste"}
    _ate(sistema, lambda: "DEL-001" in bus.conversations)
    with pytest.raises(MensagemRejeitada, match="proposta de prazo antes de agree"):
        orc.send("AG-ORQ", "propose", "PROT-DEL", "DEL-001", proposta)
    _ate(sistema, lambda: bus.conversations["DEL-001"].state == "EM_EXECUCAO")
    with pytest.raises(MensagemRejeitada):  # quem aceita é só o Orquestrador
        orc.send("AG-ORQ", "accept-proposal", "PROT-DEL", "DEL-001", {"prazo": 99})
    with pytest.raises(MensagemRejeitada):  # o Orquestrador não propõe prazo a si mesmo pelo especialista
        orq.send("AG-ORC", "propose", "PROT-DEL", "DEL-001", proposta)
    with pytest.raises(MensagemRejeitada, match="prazo_extra"):  # esquema: campo obrigatório ausente
        orc.send("AG-ORQ", "propose", "PROT-DEL", "DEL-001", {"tipo": "mais_prazo", "motivo": "sem o campo"})
    orc.send("AG-ORQ", "propose", "PROT-DEL", "DEL-001", proposta)
    with pytest.raises(MensagemRejeitada, match="resultado com proposta de prazo ainda sem resposta"):
        orc.send("AG-ORQ", "inform", "PROT-DEL", "DEL-001", {})
    rejeitadas = [r for r in bus.audit.records if r["kind"] == "rejected"]
    assert len(rejeitadas) == 5 and {r["etapa"] for r in rejeitadas} >= {"fsm", "papel", "esquema"}

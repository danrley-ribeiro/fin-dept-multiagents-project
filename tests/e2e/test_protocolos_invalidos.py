"""E4 — mensagens fora da FSM são rejeitadas (TEST-03 e TEST-07)."""
import pytest

from fin_mas.core.fsm import ProtocolViolation
from fin_mas.env.scenarios import build_system

pytestmark = pytest.mark.e2e


def test_delegation_rejects_inform_before_agree():
    s = build_system()
    s.orq.send("AG-CUS", "request", "PROT-DEL", "DEL-900",
               {"tarefa": "apurar_custos", "entidade": "SMA", "competencia": "2026-09"})
    with pytest.raises(ProtocolViolation, match="resultado antes de agree"):
        s.agentes["AG-CUS"].send("AG-ORQ", "inform", "PROT-DEL", "DEL-900", {"x": 1})
    assert s.bus.conversations["DEL-900"].state == "AGUARDANDO"
    # a mensagem rejeitada não foi agendada nem entregue
    s.bus.run()
    assert not [r for r in s.bus.audit.records if r["kind"] == "deliver" and r["content"] == {"x": 1}]


def test_query_ref_rejects_unsolicited_inform():
    s = build_system()
    with pytest.raises(ProtocolViolation, match="conversation_id desconhecido"):
        s.agentes["AG-CUS"].send("AG-RES", "inform", "PROT-QRY", "QRY-777", {"x": 1, "proveniencia": {}})
    assert "QRY-777" not in s.bus.conversations


def test_segundo_resultado_para_a_mesma_solicitacao_e_rejeitado():
    s = build_system()
    sid = s.usuario.solicitar("avaliar_orcamento")
    s.bus.run()
    assert s.bus.conversations[sid].state == "CONCLUIDA"
    with pytest.raises(ProtocolViolation, match="segundo resultado"):
        s.orq.send("SOL", "inform", "PROT-SOL", sid, {"x": 1, "intencao": "avaliar_orcamento", "status": "publicado",
                                                      "relatorio": "-", "ressalvas": [], "resultado": {}})

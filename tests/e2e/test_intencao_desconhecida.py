"""E3 — TEST-02: intenção fora do catálogo termina em RECUSADA com not-understood."""
import pytest

from fin_mas.env.scenarios import build_system

pytestmark = pytest.mark.e2e


def test_unknown_intent_not_understood():
    s = build_system()
    sid = s.usuario.solicitar("demitir_todos")
    s.bus.run()
    resposta = s.usuario.resposta(sid)
    assert resposta.performative == "not-understood"
    assert s.bus.conversations[sid].state == "RECUSADA"
    # nada foi delegado nem reservado
    assert [c for c in s.bus.conversations if not c.startswith("SOL")] == []
    assert not [r for r in s.bus.audit.records if r["kind"] == "lock"]
    decisao = next(r for r in s.bus.audit.records if r["kind"] == "decision")
    assert decisao["regra"] == "intenção fora do catálogo"

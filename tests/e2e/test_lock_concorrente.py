"""E7 — TEST-14: duas reservas sobrepostas do mesmo período; TTL libera."""
import pytest

from fin_mas.core.bus import Bus
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.services.locks import LockService

pytestmark = pytest.mark.e2e


@pytest.fixture
def lck():
    bus = Bus()
    return LockService(bus.audit, lambda: bus.now, ttl=10), bus


def test_period_lock_conflict_rejected(lck):
    locks, bus = lck
    primeira = locks.reserve("EMP-01", "2026-09", "SOL-001")
    segunda = locks.reserve("EMP-01", "2026-09", "SOL-002")
    assert primeira["performative"] == "reserve-accept"
    assert segunda["performative"] == "reserve-failure"
    assert segunda["dono_atual"] == "SOL-001"
    # a reserva original continua valendo
    assert locks.dono("EMP-01", "2026-09") == "SOL-001"


def test_ttl_libera_a_reserva(lck):
    locks, bus = lck
    locks.reserve("EMP-01", "2026-09", "SOL-001")
    bus.now = 9
    assert locks.reserve("EMP-01", "2026-09", "SOL-002")["performative"] == "reserve-failure"
    bus.now = 10
    assert locks.reserve("EMP-01", "2026-09", "SOL-002")["performative"] == "reserve-accept"
    assert locks.dono("EMP-01", "2026-09") == "SOL-002"
    assert any(r.get("evento") == "ttl_expirado" for r in bus.audit.records)


def test_competencias_ou_entidades_diferentes_nao_conflitam(lck):
    locks, _ = lck
    assert locks.reserve("EMP-01", "2026-09", "SOL-001")["performative"] == "reserve-accept"
    assert locks.reserve("EMP-01", "2026-10", "SOL-002")["performative"] == "reserve-accept"
    assert locks.reserve("EMP-02", "2026-09", "SOL-003")["performative"] == "reserve-accept"


def test_release_libera_para_outro_dono(lck):
    locks, _ = lck
    locks.reserve("EMP-01", "2026-09", "SOL-001")
    locks.release("EMP-01", "2026-09", "SOL-001")
    assert locks.reserve("EMP-01", "2026-09", "SOL-002")["performative"] == "reserve-accept"


def test_liberar_reserva_inexistente_e_violacao(lck):
    locks, _ = lck
    with pytest.raises(ProtocolViolation, match="liberar reserva inexistente"):
        locks.release("EMP-01", "2026-09", "SOL-001")


def test_so_o_dono_libera(lck):
    locks, _ = lck
    locks.reserve("EMP-01", "2026-09", "SOL-001")
    with pytest.raises(ProtocolViolation, match="não é o dono"):
        locks.release("EMP-01", "2026-09", "SOL-002")
    assert locks.dono("EMP-01", "2026-09") == "SOL-001"

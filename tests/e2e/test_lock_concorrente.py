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
    primeira = locks.reserve("SMA", "2026-09", "SOL-001")
    segunda = locks.reserve("SMA", "2026-09", "SOL-002")
    assert primeira["performative"] == "reserve-accept"
    assert segunda["performative"] == "reserve-failure"
    assert segunda["dono_atual"] == "SOL-001"
    # a reserva original continua valendo
    assert locks.dono("SMA", "2026-09") == "SOL-001"


def test_ttl_libera_a_reserva(lck):
    locks, bus = lck
    locks.reserve("SMA", "2026-09", "SOL-001")
    bus.now = 9
    assert locks.reserve("SMA", "2026-09", "SOL-002")["performative"] == "reserve-failure"
    bus.now = 10
    assert locks.reserve("SMA", "2026-09", "SOL-002")["performative"] == "reserve-accept"
    assert locks.dono("SMA", "2026-09") == "SOL-002"
    assert any(r.get("evento") == "ttl_expirado" for r in bus.audit.records)


def test_competencias_ou_entidades_diferentes_nao_conflitam(lck):
    locks, _ = lck
    assert locks.reserve("SMA", "2026-09", "SOL-001")["performative"] == "reserve-accept"
    assert locks.reserve("SMA", "2026-10", "SOL-002")["performative"] == "reserve-accept"
    assert locks.reserve("EMP-02", "2026-09", "SOL-003")["performative"] == "reserve-accept"


def test_release_libera_para_outro_dono(lck):
    locks, _ = lck
    locks.reserve("SMA", "2026-09", "SOL-001")
    locks.release("SMA", "2026-09", "SOL-001")
    assert locks.reserve("SMA", "2026-09", "SOL-002")["performative"] == "reserve-accept"


def test_liberar_reserva_inexistente_e_violacao(lck):
    locks, _ = lck
    with pytest.raises(ProtocolViolation, match="liberar reserva inexistente"):
        locks.release("SMA", "2026-09", "SOL-001")


def test_so_o_dono_libera(lck):
    locks, _ = lck
    locks.reserve("SMA", "2026-09", "SOL-001")
    with pytest.raises(ProtocolViolation, match="não é o dono"):
        locks.release("SMA", "2026-09", "SOL-002")
    assert locks.dono("SMA", "2026-09") == "SOL-001"


def test_dois_fechamentos_concorrentes_do_mesmo_periodo_pelo_orquestrador():
    from fin_mas.env.scenarios import build_system
    s = build_system()
    primeiro = s.usuario.solicitar("fechar_mes")
    segundo = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    assert s.usuario.resposta(primeiro).performative == "inform"
    recusa = s.usuario.resposta(segundo)
    assert recusa.performative == "refuse"
    assert recusa.content["dono_atual"] == primeiro
    assert s.bus.conversations[segundo].state == "RECUSADA"
    # depois que o primeiro termina, o período volta a ficar disponível
    terceiro = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    assert s.usuario.resposta(terceiro).performative == "inform"


def test_period_reservation_cannot_be_released_or_taken_by_naming_its_owner():
    """Correção simulada da v0.5.0 (M6): bastava dizer o nome do dono para liberar a reserva de um fechamento
    em andamento e tomá-la. No sistema montado, a transição exige a credencial do Orquestrador."""
    from fin_mas.core.fsm import ProtocolViolation
    from fin_mas.env.scenarios import build_system

    s = build_system(plantar=("alcada",), interativo=True)
    sid = s.usuario.solicitar("fechar_mes")
    while s.bus.proximo_tempo() is not None and s.locks.dono("SMA", "2026-09") != sid:
        s.bus.step()
    for chamada in (lambda: s.locks.release("SMA", "2026-09", sid),
                    lambda: s.locks.reserve("SMA", "2026-09", "INTRUSO"),
                    lambda: s.locks.renovar("SMA", "2026-09", sid, 10**6),
                    lambda: s.locks.release("SMA", "2026-09", sid, agente="AG-ORQ", credencial="chute"),
                    lambda: s.locks.release("SMA", "2026-09", sid, agente="AG-REL", credencial=None)):
        with pytest.raises(ProtocolViolation, match="sem credencial válida do Orquestrador"):
            chamada()
    assert s.locks.dono("SMA", "2026-09") == sid
    recusas = [r for r in s.bus.audit.records if r["kind"] == "rejected" and r.get("protocol") == "PROT-LCK"]
    assert len(recusas) == 5

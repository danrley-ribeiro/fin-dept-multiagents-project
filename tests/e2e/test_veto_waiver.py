"""E5 — veto de AG-CIN, waiver humano e bloqueio (TEST-08); TEST-09 de ponta a ponta."""
import pytest

from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message
from fin_mas.env.scenarios import Scenario, build_system, run_scenario

pytestmark = pytest.mark.e2e


def test_critical_nonconformity_vetoes_close():
    e = run_scenario("veto_bloqueio")
    r = e.resposta
    assert r.performative == "failure"
    assert r.content["publicado"] is False and r.content["subtarefa"] == "conformidade"
    assert r.content["achados"][0]["regra"] == "alcada"
    # o relatório nunca foi pedido: nada publicado
    assert not [c for c in e.system.bus.conversations.values() if c.counterpart == "AG-REL"]
    assert e.system.bus.conversations["CMP-001"].state == "BLOQUEADO"
    assert e.system.bus.conversations[e.sid].state == "FALHOU"
    assert e.system.locks.dono("EMP-01", "2026-09") is None  # reserva liberada no bloqueio


def test_publicar_em_vetado_e_rejeitado_e_a_reserva_continua():
    s = build_system(plantar=("alcada",))
    s.aprovador.on_message = lambda m: None  # ninguém decide: a conversa fica em VETADO
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    assert s.bus.conversations["CMP-001"].state == "VETADO"
    with pytest.raises(ProtocolViolation, match="publicar"):
        s.bus.send(Message("AG-ORQ", "AG-CIN", "publicar", "CMP-001", "PROT-CMP"))
    assert s.locks.dono("EMP-01", "2026-09") == sid  # reserva segue ativa durante o veto
    assert s.usuario.resposta(sid) is None


def test_waiver_humano_libera_com_ressalva():
    e = run_scenario("veto_waiver")
    r = e.resposta
    assert r.performative == "inform" and r.content["status"] == "publicado_com_ressalva"
    assert any("waiver de alcada" in x for x in r.content["ressalvas"])
    assert "Ressalva: waiver de alcada" in r.content["relatorio"]
    assert e.system.bus.conversations["CMP-001"].state == "LIBERADO"
    assert [h[1] for h in e.system.bus.conversations["CMP-001"].history] == [
        "request", "veto", "waiver_humano", "publicar"]
    assert len(e.system.aprovador.avisos) == 1
    assert e.system.locks.dono("EMP-01", "2026-09") is None


def test_nao_conformidade_nao_critica_libera_com_ressalva_sem_humano():
    e = run_scenario(Scenario("so_competencia", "competência fora do período", "fechar_mes",
                              plantar=("competencia",)))
    assert e.resposta.content["status"] == "publicado_com_ressalva"
    assert e.system.aprovador.avisos == []
    assert [h[1] for h in e.system.bus.conversations["CMP-001"].history] == [
        "request", "nao_conforme_nao_critico", "publicar"]


@pytest.mark.parametrize("seed", [3, 42])
def test_veto_lista_todas_as_criticas_plantadas(seed):
    e = run_scenario(Scenario("todas", "todas as regras", "fechar_mes", seed=seed,
                              plantar=("alcada", "sod", "duplicidade", "competencia"),
                              decisao_aprovador="nenhuma"))
    achados = e.resposta.content["achados"]
    criticas = {(a["regra"], a["lancamento"]) for a in achados if a["severidade"] == "critica"}
    esperadas = {(n["regra"], n["lancamento"]) for n in e.system.dataset.gold["nao_conformidades"]
                 if n["severidade"] == "critica"}
    assert criticas == esperadas and len(criticas) == 3

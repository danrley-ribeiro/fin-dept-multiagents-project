"""DSM4 — revisão do commit 1e03ee5 (POL-06 decidida na mesma trava da memória).

1. Oferta e decisão do waiver usam a mesma janela: reexecutar a reincidência com a mesma memória dá o mesmo
   resultado da primeira execução, sem waiver oferecido e depois recusado, sem ticket sem resposta.
2. No modo em lote, o waiver recusado por um ticket concorrente vira bloqueio explícito (não espera o prazo).
3. Falha na gravação do waiver não deixa entrada fantasma na memória em processo.
4. A trava entre processos é liberada em exceção e não é reentrante em silêncio (espera e recusa).
"""
import pytest

from fin_mas.core.bus import MensagemRejeitada
from fin_mas.env.scenarios import CENARIOS, montar, run_scenario
from fin_mas.services import selado
from helpers import rodar_ate_humano

pytestmark = pytest.mark.e2e
JUSTIFICATIVA = "aceito o risco: lançamento será corrigido no próximo ciclo"


def _resumo(execucao):
    respostas = {sid: execucao.system.usuario.resposta(sid) for sid in execucao.sids}
    return {sid: (r.performative, r.content.get("status")) for sid, r in respostas.items()}


# ---- 1. mesma janela na oferta e na decisão ------------------------------------------------------
def test_rerunning_the_recurrence_with_the_same_memory_gives_the_same_result(tmp_path):
    arquivo = tmp_path / "memoria.json"
    primeira = run_scenario("reincidencia_waiver", memoria=arquivo)
    segunda = run_scenario("reincidencia_waiver", memoria=arquivo)  # a documentação manda rodar assim
    assert _resumo(segunda) == _resumo(primeira)
    for execucao in (primeira, segunda):
        registros = execucao.audit.records
        assert not [r for r in registros if r["kind"] == "erro_agente"]
        assert not [r for r in registros if r["kind"] == "timeout" and r.get("protocol") == "PROT-APR"]
    import json
    entradas = json.loads(arquivo.read_text(encoding="utf-8"))["entradas"]
    waivers = [e for e in entradas if e["tipo"] == "waiver"]
    assert len({(e["chave"], e["competencia"]) for e in waivers}) == len(waivers)  # sem waiver duplicado


def test_waiver_is_not_offered_when_a_later_month_was_already_waived(tmp_path):
    """Setembro liberado primeiro; numa execução seguinte, com a mesma memória, agosto já é emitido sem o waiver
    (antes: oferecido na emissão, que só olhava meses anteriores, e recusado na decisão)."""
    arquivo = tmp_path / "memoria.json"
    s, (agosto, setembro) = montar(CENARIOS["reincidencia_waiver"], interativo=True, memoria=arquivo)
    while s.bus.proximo_tempo() is not None and len(s.aprovador.pendentes) < 2:
        s.bus.step()
    assert s.aprovador.decidir(setembro, "waiver", JUSTIFICATIVA) is True
    assert s.aprovador.decidir(agosto, "corrigir") is True
    s.bus.run()
    s2, (agosto2, _) = montar(CENARIOS["reincidencia_waiver"], interativo=True, memoria=arquivo)
    while s2.bus.proximo_tempo() is not None and agosto2 not in s2.aprovador.pendentes:
        s2.bus.step()
    ticket = next(t for t in s2.politica.tickets.values() if t["solicitacao"] == agosto2)
    assert "waiver" not in ticket["opcoes"]
    assert [n["regra"] for n in ticket["negadas"]] == ["POL-06"]  # negado já na emissão, não na decisão
    assert any("reincidente: waiver posterior" in a["evidencia"] for a in ticket["achados"])


# ---- 2. lote com ticket concorrente --------------------------------------------------------------
def test_batch_approver_blocks_instead_of_waiting_when_the_concurrent_waiver_is_refused():
    s, (agosto, setembro) = montar(CENARIOS["reincidencia_waiver"], interativo=True)
    while s.bus.proximo_tempo() is not None and len(s.aprovador.pendentes) < 2:
        s.bus.step()
    propostas = dict(s.aprovador.pendentes)
    s.aprovador.pendentes.clear()
    s.aprovador.interativo, s.aprovador.decisoes = False, ["waiver"]  # roteiro em lote: waiver nos dois
    s.aprovador.on_message(propostas[agosto])
    s.aprovador.on_message(propostas[setembro])  # recusado (POL-06): cai para bloquear
    s.bus.run()
    assert s.usuario.resposta(agosto).content["status"] == "publicado_com_ressalva"
    r = s.usuario.resposta(setembro)
    assert r.performative == "failure" and r.content["publicado"] is False
    assert not [x for x in s.bus.audit.records if x["kind"] == "erro_agente"]
    ticket = next(t for t in s.politica.tickets.values() if t["solicitacao"] == setembro)
    assert ticket["estado"] == "rejeitado" and ticket["negadas"][-1]["regra"] == "POL-06"


# ---- 3. falha na gravação não deixa fantasma -----------------------------------------------------
def test_failed_waiver_write_leaves_no_phantom_entry():
    s, (agosto, _) = montar(CENARIOS["reincidencia_waiver"], interativo=True)
    rodar_ate_humano(s.bus)
    mem = s.memoria
    original = mem._inserir

    def quebra(*args, **kwargs):
        original(*args, **kwargs)  # insere e falha em seguida, como um disco cheio no meio da gravação
        raise OSError("disco cheio")
    mem._inserir = quebra
    with pytest.raises(MensagemRejeitada, match="histórico de decisões indisponível"):
        s.aprovador.decidir(agosto, "waiver", JUSTIFICATIVA)
    assert not [e for e in mem.entradas if e["tipo"] == "waiver"]
    mem._inserir = original
    assert s.aprovador.decidir(agosto, "waiver", JUSTIFICATIVA) is True  # e a decisão legítima continua possível


# ---- 4. trava entre processos ---------------------------------------------------------------------
def test_lock_is_released_on_exception_and_is_not_silently_reentrant(tmp_path, monkeypatch):
    alvo = tmp_path / "dados.json"
    with pytest.raises(RuntimeError):
        with selado.trava(alvo):
            raise RuntimeError("falha no meio da transação")
    with selado.trava(alvo):  # liberada: pega de novo na hora
        monkeypatch.setattr(selado, "ESPERA_TRAVA", 0.2)
        with pytest.raises(selado.TravaOcupada):
            with selado.trava(alvo):  # a mesma trava de novo, aninhada: espera e recusa, não entra
                pass

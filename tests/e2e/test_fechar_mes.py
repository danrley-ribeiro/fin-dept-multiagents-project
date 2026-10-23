"""E1 — "fechar o mês" no caminho feliz (TEST-01) com o resultado igual ao gabarito."""
import pytest

from fin_mas.env.scenarios import run_scenario
from helpers import seq

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def e():
    return run_scenario("fechar_mes")


def test_intent_decomposition_dag(e):
    r = e.resposta
    assert r.performative == "inform" and r.content["status"] == "publicado"
    dag = r.content["dag"]
    assert {n: d["agente"] for n, d in dag.items()} == {
        "custos": "AG-CUS", "orcamento": "AG-ORC", "resultados": "AG-RES",
        "conformidade": "AG-CIN", "relatorio": "AG-REL"}
    # cada subtarefa percorre a sua conversa: request -> agree -> inform (CIN: request -> parecer)
    for no, d in dag.items():
        assert len(d["conversas"]) == 1
        perfs = [x["performative"] for x in e.audit.by_conversation(d["conversas"][0])
                 if x["kind"] in ("open", "send")]
        assert perfs == (["request", "conforme"] if no == "conformidade" else ["request", "agree", "inform"])
    cid = {n: d["conversas"][0] for n, d in dag.items()}
    a = e.audit
    # CUS e ORC em paralelo: ambos abertos antes de qualquer um concluir
    assert max(seq(a, cid["custos"], "request"), seq(a, cid["orcamento"], "request")) < \
        min(seq(a, cid["custos"], "inform"), seq(a, cid["orcamento"], "inform"))
    # RES só depois dos dois; CIN só depois de RES; REL só depois do parecer
    assert seq(a, cid["resultados"], "request") > max(seq(a, cid["custos"], "inform"),
                                                      seq(a, cid["orcamento"], "inform"))
    assert seq(a, cid["conformidade"], "request") > seq(a, cid["resultados"], "inform")
    assert seq(a, cid["relatorio"], "request") > seq(a, cid["conformidade"], "conforme")
    # a resposta final fecha a conversa do solicitante
    assert e.system.bus.conversations[e.sid].state == "CONCLUIDA"
    assert seq(a, e.sid, "inform") > seq(a, cid["relatorio"], "inform")


def test_resultado_final_igual_ao_gabarito(e):
    assert e.resposta.content["resultado"]["dre"] == e.system.dataset.gold["dre"]


def test_relatorio_traz_numeros_do_gabarito(e):
    from fin_mas.env.dataset import brl
    texto = e.resposta.content["relatorio"]
    assert brl(e.system.dataset.gold["dre"]["ebitda"]) in texto
    assert e.resposta.content["ressalvas"] == []


def test_reserva_e_liberada_ao_final(e):
    assert e.system.locks.dono("EMP-01", "2026-09") is None
    eventos = [r["evento"] for r in e.audit.records if r["kind"] == "lock"]
    assert eventos == ["reserve", "release"]


def test_toda_decisao_registra_a_regra(e):
    decisoes = [r for r in e.audit.records if r["kind"] == "decision"]
    assert {d["agente"] for d in decisoes} >= {"AG-ORQ", "AG-CUS", "AG-RES", "AG-CIN", "AG-REL"}
    assert all(d["regra"] for d in decisoes)

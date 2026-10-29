"""AG-ORC cognitivo (BDI): consulta direta ao AG-CIN, reconsideração, replanejamento e divergência.

TEST-27, TEST-28 e TEST-29. Tudo verificado pelo trace de cenários completos.
"""
import pytest

from fin_mas import baseline
from fin_mas.env.scenarios import run_scenario

pytestmark = pytest.mark.e2e


def _eventos(e, agente, kind):
    return [r for r in e.audit.records if r["kind"] == kind and r.get("agente") == agente]


def test_budget_agent_queries_controls_and_reconsiders():
    e = run_scenario("desvio_irregular")
    ds = e.system.dataset
    # a consulta ao AG-CIN é decisão do AG-ORC: conversa PROT-QRY iniciada por ele, sem o Orquestrador
    consultas = [c for c in e.system.bus.conversations.values()
                 if c.protocol.id == "PROT-QRY" and c.counterpart == "AG-CIN"]
    assert len(consultas) == 1 and consultas[0].initiator == "AG-ORC" and consultas[0].state == "RESPONDIDA"
    # a deliberação escolheu consultar (maior utilidade) com o fallback ainda aplicável
    delib = next(r for r in _eventos(e, "AG-ORC", "deliberation") if r["desejo"].startswith("explicar_desvio"))
    assert delib["escolhido"] == "P-CONSULTAR-CIN"
    assert {o["plano"]: o["aplicavel"] for o in delib["opcoes"]} == {"P-CONSULTAR-CIN": True, "P-SEM-EXPLICACAO": True}
    # a resposta revisa a crença e torna a intenção de sinalizar sem sentido: reconsiderada e abandonada
    contestado = next(r for r in _eventos(e, "AG-ORC", "belief") if r["chave"].startswith("contestado["))
    assert contestado["fonte"].startswith("AG-CIN") and contestado["depois"] > 0
    abandono = next(r for r in _eventos(e, "AG-ORC", "intention")
                    if r["plano"] == "P-SINALIZAR" and r["evento"] == "abandonada")
    assert "reconsiderada" in abandono["motivo"] and "abaixo do limiar" in abandono["motivo"]
    assert any(r["plano"] == "P-ENCAMINHAR-CONTROLE" and r["evento"] == "concluida"
               for r in _eventos(e, "AG-ORC", "intention"))
    # classificação igual ao gabarito; o workflow centralizado sinaliza o desvio como orçamentário
    orc = next(r for r in e.audit.records if r["kind"] == "send" and r["sender"] == "AG-ORC"
               and r["performative"] == "inform" and r["protocol"] == "PROT-DEL")["content"]
    assert orc["sinalizadas"] == ds.gold["desvios"] and orc["atribuidas_a_controle"] == ds.gold["desvios_atribuidos"]
    original = type(ds)(seed=ds.seed, competencia=ds.competencia, plantar=ds.plantar)
    assert baseline.executar(original, "fechar_mes").sinalizadas == ds.gold["desvios_atribuidos"]
    # a correção (estorno da NF duplicada) sugerida pelo AG-CIN destrava o fechamento
    assert e.resposta.performative == "inform"
    assert [c["acao"] for c in ds.correcoes] == ["estornar"]


def test_budget_plan_failure_replans_on_timeout():
    e = run_scenario("orc_sem_cin")
    assert [r["conversation_id"] for r in e.audit.records if r["kind"] == "drop"] == ["QRY-001"]
    eventos = [(r["plano"], r["evento"]) for r in _eventos(e, "AG-ORC", "intention")
               if r["plano"] in ("P-CONSULTAR-CIN", "P-SEM-EXPLICACAO")]
    assert eventos[:4] == [("P-CONSULTAR-CIN", "adotada"), ("P-CONSULTAR-CIN", "suspensa"),
                           ("P-CONSULTAR-CIN", "retomada"), ("P-CONSULTAR-CIN", "falhou")]
    assert ("P-CONSULTAR-CIN", "reconsiderada") in eventos and ("P-SEM-EXPLICACAO", "concluida") in eventos
    replanejamento = [r for r in _eventos(e, "AG-ORC", "deliberation") if r["desejo"].startswith("explicar")][-1]
    assert replanejamento["escolhido"] == "P-SEM-EXPLICACAO"
    assert {o["plano"]: o["motivo"] for o in replanejamento["opcoes"]}["P-CONSULTAR-CIN"] == "já tentado sem sucesso"
    # sem atribuição o desvio segue como orçamentário, com ressalva explícita; ainda há resposta final
    r = e.resposta
    assert r.performative == "inform"
    assert any("AG-CIN indisponível" in x for x in r.content["ressalvas"])


def test_source_divergence_revises_belief():
    e = run_scenario("divergencia_fonte")
    ds = e.system.dataset
    conta = ds.gold["divergencias"][0]
    adotado = next(r for r in _eventos(e, "AG-ORC", "belief") if r["chave"].startswith(f"realizado[{conta}]"))
    assert adotado["depois"] == ds.realizado_erp[conta] and adotado["fonte"] == "mcp://erp/realizado_por_conta"
    delib = next(r for r in _eventos(e, "AG-ORC", "deliberation") if r["desejo"].startswith("fonte_confiavel"))
    assert delib["escolhido"] == "P-ADOTAR-ERP"
    assert not {o["plano"]: o["aplicavel"] for o in delib["opcoes"]}["P-MANTER-PLANILHA"]
    r = e.resposta
    assert r.content["resultado"]["sinalizadas"] == ds.gold["desvios"]  # pela planilha haveria um falso desvio
    assert any(x.startswith(f"divergência em {conta}") for x in r.content["ressalvas"])
    assert f"Ressalva: divergência em {conta}" in r.content["relatorio"]

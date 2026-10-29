"""AG-CIN cognitivo: seleção entre vetos, correção humana, reconsideração e waiver (TEST-30 e TEST-31)."""
import pytest

from fin_mas.env.scenarios import run_scenario

pytestmark = pytest.mark.e2e


def _cin(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind and r.get("agente") == "AG-CIN"]


def test_veto_correction_reconsidered_by_controls():
    e = run_scenario("veto_correcao")
    cmp_ = e.system.bus.conversations["CMP-001"]
    assert [h[1] for h in cmp_.history] == ["request", "veto", "correcao", "conforme"]
    assert cmp_.state == "LIBERADO"
    primeira, segunda = _cin(e, "deliberation")
    # com crítica corrigível os dois vetos se aplicam; vence o que também atende ao prazo
    util = {o["plano"]: (o["aplicavel"], o["utilidade"]) for o in primeira["opcoes"]}
    assert primeira["escolhido"] == "P-VETAR-COM-CORRECAO"
    assert util["P-VETAR"][0] and util["P-VETAR-COM-CORRECAO"][1] > util["P-VETAR"][1]
    veto = next(r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto")
    assert veto["content"]["correcoes_sugeridas"] == [{"lancamento": "L-013", "regras": ["alcada"],
                                                       "acao": "reaprovar"}]
    # a correção é percebida de novo via MCP; a intenção de vetar é reconsiderada e trocada por aprovar
    eventos = [(r["plano"], r["evento"]) for r in _cin(e, "intention")]
    assert eventos.index(("P-VETAR-COM-CORRECAO", "reconsiderada")) < eventos.index(("P-APROVAR", "adotada"))
    assert segunda["escolhido"] == "P-APROVAR"
    assert any(r["chave"] == "lanc[L-013]@2026-09" and r["depois"]["violacoes"] == [] for r in _cin(e, "belief"))
    r = e.resposta
    assert r.performative == "inform" and r.content["status"] == "publicado"
    assert r.content["notas"] and "L-013 reaprovado por carla" in r.content["notas"][0]
    assert e.system.locks.dono("SMA", "2026-09") is None


def test_partial_correction_keeps_veto_then_blocks():
    e = run_scenario("correcao_parcial")
    cmp_ = e.system.bus.conversations["CMP-001"]
    assert [h[1] for h in cmp_.history] == ["request", "veto", "correcao", "veto", "prazo_esgotado"]
    assert cmp_.state == "BLOQUEADO"
    segunda = _cin(e, "deliberation")[1]
    motivos = {o["plano"]: o["motivo"] for o in segunda["opcoes"]}
    assert segunda["escolhido"] == "P-VETAR"  # mantém o compromisso de vetar, sem novo ciclo de correção
    assert motivos["P-VETAR-COM-CORRECAO"].startswith("ciclo de correção já usado")
    assert any(r["plano"] == "P-VETAR" and r["evento"] == "concluida" and "bloqueada" in r["motivo"]
               for r in _cin(e, "intention"))
    # o aprovador só pôde bloquear ou dar waiver no segundo aviso
    assert e.system.aprovador.avisos[1].content["opcoes"] == ["waiver", "bloquear"]
    r = e.resposta
    assert r.performative == "failure" and r.content["publicado"] is False


def test_waiver_ends_controls_intention_but_keeps_belief():
    e = run_scenario("veto_waiver")
    abandono = next(r for r in _cin(e, "intention") if r["evento"] == "abandonada")
    assert "waiver humano" in abandono["motivo"]
    assert any(r["chave"] == "waiver[CMP-001]" for r in _cin(e, "belief"))
    assert e.system.agentes["AG-CIN"].crencas.get("lanc[L-013]@2026-09")["violacoes"] == ["alcada"]

"""Decisão no Approval Gate vinculada à pessoa autenticada (SVC-IAM, ADR-009): POL-09, POL-02, POL-03, POL-13.

Cenários completos com as contas de demonstração em memória e relógio lógico. O que se
confere é o trace, o ticket da política, a trilha de acesso e a resposta final.
"""
import json

import pytest

from fin_mas import metricas
from fin_mas.env.scenarios import CENARIOS, run_scenario

pytestmark = pytest.mark.e2e
COM_ACESSO = sorted(n for n, sc in CENARIOS.items() if sc.acesso)


def reg(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind]


def rejeicoes(e):
    return [r["motivo"] for r in reg(e, "rejected")]


def ticket(e):
    (t,) = e.system.politica.tickets.values()
    return t


def test_involved_approver_is_refused_and_another_person_decides():
    e = run_scenario("decisao_por_pessoa")
    assert rejeicoes(e) == ["POL-03: carla participou de um lançamento vetado e não pode decidir sobre ele"]
    t = ticket(e)
    assert "carla" in t["envolvidos"] and t["solicitado_por"] == "elisa"
    assert t["aprovado_por"] == {"agente": "APR", "pessoa": "diego", "titulo": "gerente", "sessao": "SIM-diego"}
    assert e.resposta.performative == "inform" and e.resposta.content["status"].startswith("publicado")
    # a decisão aceita leva o atestado, e o token nunca aparece no trace
    aprovacao = next(r for r in reg(e, "send") + reg(e, "open") if r.get("performative") == "approve")
    assert aprovacao["content"]["atestado"]["pessoa"] == "diego"
    assert aprovacao["content"]["atestado"]["token"] == "[SEGREDO REDIGIDO]"
    # trilha de acesso: a tentativa negada e a decisão aceita, cada uma com a pessoa
    trilha = e.system.acesso.trilha.ler()
    assert [(r["ator"], r["resultado"], r.get("regra")) for r in trilha if r["evento"] == "decisao"] == \
        [("carla", "negado", "POL-03"), ("diego", "ok", None)]


def test_requester_cannot_approve_their_own_request():
    e = run_scenario("solicitante_nao_aprova")
    assert rejeicoes(e) == ["POL-13: elisa fez a solicitação SOL-001 e não pode decidir sobre ela"]
    assert ticket(e)["aprovado_por"]["pessoa"] == "controller"
    assert e.resposta.content["status"].startswith("publicado")


def test_position_limits_which_decisions_a_person_can_take():
    e = run_scenario("waiver_exige_cargo")
    assert rejeicoes(e) == ["POL-02: ana (analista) não pode decidir 'waiver'"]
    t = ticket(e)
    assert (t["decisao"], t["aprovado_por"]["pessoa"], t["aprovado_por"]["titulo"]) == ("waiver", "diego", "gerente")
    assert e.resposta.content["status"] == "publicado_com_ressalva"


def test_single_person_company_uses_the_registered_compensating_control():
    e = run_scenario("micro_controle_compensatorio")
    assert not rejeicoes(e)
    decidido = next(r for r in reg(e, "politica") if r["evento"] == "decidido")
    assert decidido["aprovado_por"]["pessoa"] == "controller" == ticket(e)["solicitado_por"]
    assert "revisão mensal dos lançamentos pelo sócio" in decidido["controle_compensatorio"]
    # no porte médio, sem controle compensatório, a mesma situação é recusada (cenário solicitante_nao_aprova)
    assert e.resposta.performative == "inform"


def test_access_attacks_are_all_rejected_and_nothing_is_published():
    e = run_scenario("ataque_acesso")
    (ataques,) = reg(e, "ataques")
    resultados = ataques["resultados"]
    assert len(resultados) == 15 and not [r for r in resultados if r["aceito"]]
    regras = {r["ataque"]: r["motivo"].split(":")[0] for r in resultados}
    assert regras["decisão pela caixa APR sem atestado de pessoa (a lacuna da primeira versão)"] == "POL-09"
    assert regras["atestado de sessão revogada"] == "POL-09"
    assert regras["mesmo atestado enviado duas vezes (replay)"] == "POL-09"
    assert regras["pessoa sem papel de aprovador pede um atestado (operador)"] == "IAM-05"
    assert regras["cargo sem alçada para a decisão (analista concede waiver)"] == "POL-02"
    assert regras["aprovador que participou do lançamento vetado decide sobre ele (ana corrige)"] == "POL-03"
    assert regras["quem fez a solicitação decide sobre ela (elisa)"] == "POL-13"
    assert regras["operador atribui a si o papel de aprovador"] == "IAM-05"
    assert regras["administrador de acesso acumula o papel de aprovador"] == "IAM-06"
    assert regras["administrador remove o último administrador (ele mesmo)"] == "IAM-06"
    assert {r.split(":")[0] for r in regras.values()} == {"POL-02", "POL-03", "POL-09", "POL-13", "IAM-05", "IAM-06"}
    m = metricas.medir_acesso(e)  # MET-17
    assert (m["ataques_tentados"], m["ataques_aceitos"], m["decisoes_aceitas"]) == (15, 0, 0)
    assert m["decisoes_negadas_por_regra"] == {"POL-02": 2, "POL-03": 1, "POL-09": 8, "POL-13": 1}
    t = ticket(e)
    assert t["estado"] == "expirado" and t["aprovado_por"] is None and not e.system.dataset.correcoes
    assert e.resposta.performative == "failure" and e.resposta.content["publicado"] is False
    # nenhum token de atestado vaza para o trace, nem nos ataques
    trace = json.dumps(e.audit.records, ensure_ascii=False, default=str)
    assert '"token": "[SEGREDO REDIGIDO]"' in trace
    assert not any(len(a["content"]["atestado"].get("token", "")) == 64 for a in reg(e, "rejected")
                   if isinstance((a.get("content") or {}).get("atestado"), dict))


@pytest.mark.parametrize("nome", COM_ACESSO)
def test_person_bound_scenarios_are_reproducible_and_every_decision_names_a_person(nome):
    a, b = run_scenario(nome), run_scenario(nome)
    assert a.hash == b.hash and a.resposta.content == b.resposta.content
    assert next(r for r in reg(a, "meta"))["acesso"]["modo"] == "simulado"
    for t in a.system.politica.tickets.values():
        if t["aprovado_por"] is not None:
            assert t["aprovado_por"]["pessoa"] != "APR" and t["aprovado_por"]["sessao"].startswith("SIM-")


def test_without_iam_the_reviewed_scenarios_keep_the_identity_based_rules():
    """Lote da primeira versão da DSM3: sem contas, sem atestado, mesmas regras POL-01 a POL-08."""
    e = run_scenario("veto_correcao")
    assert e.system.acesso is None
    aprovacao = next(r for r in reg(e, "send") + reg(e, "open") if r.get("performative") == "approve")
    assert "atestado" not in aprovacao["content"] and "acesso" not in reg(e, "meta")[0]
    assert ticket(e)["aprovado_por"] == {"agente": "APR", "pessoa": "controller", "titulo": "Controller"}

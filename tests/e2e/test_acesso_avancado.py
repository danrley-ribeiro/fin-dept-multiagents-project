"""Acesso avançado no Approval Gate (DSM4, ADR-012): POL-10, POL-11, POL-12, POL-14, IAM-08 e IAM-09.

Cenários completos sobre o barramento, com as contas de demonstração em memória e relógio
lógico. Confere-se o trace, o ticket da política, a trilha de acesso, os invariantes e a
resposta final. O isolamento entre empresas roda o mesmo par de meses com a memória de cada
empresa na pasta dela.
"""
import copy
import json

import pytest

from fin_mas import invariantes, metricas
from fin_mas.env.scenarios import CENARIOS, Scenario, run_scenario

pytestmark = pytest.mark.e2e
NOVOS = ("aprovador_sem_alcada", "delegacao_valida", "delegacao_expirada", "dupla_aprovacao",
         "dupla_mesma_pessoa_recusada", "escalonamento", "ataque_acesso_avancado")


def reg(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind]


def rejeicoes(e):
    return [r["motivo"] for r in reg(e, "rejected")]


def ticket(e):
    (t,) = e.system.politica.tickets.values()
    return t


@pytest.mark.parametrize("nome", NOVOS)
def test_new_scenarios_hold_every_invariant_and_repeat(nome):
    a, b = run_scenario(nome), run_scenario(nome)
    assert invariantes.verificar(a.audit.records) == []
    assert a.hash == b.hash and CENARIOS[nome].esperado


def test_person_without_authority_in_the_size_cannot_release(nome="aprovador_sem_alcada"):
    e = run_scenario(nome)
    assert rejeicoes(e) == ["POL-10: carla (gerente, sem alçada no porte) não libera R$ 3.000,00 em exposição"]
    t = ticket(e)
    assert t["exposicao"] == 300000 and t["aprovado_por"]["pessoa"] == "controller"
    veto = next(r for r in reg(e, "send") + reg(e, "open") if r.get("performative") == "veto")
    assert veto["content"]["exposicao"] == 300000  # o AG-CIN informa a exposição com o SVC-IAM ligado
    decidido = next(r for r in reg(e, "politica") if r["evento"] == "decidido")
    assert decidido["alcada"] is None and "POL-10..12" in decidido["regra"]  # controller: maior alçada (sócio)
    assert e.resposta.content["status"].startswith("publicado")


def test_without_iam_the_veto_carries_no_exposure():
    e = run_scenario("veto_correcao")
    veto = next(r for r in reg(e, "send") + reg(e, "open") if r.get("performative") == "veto")
    assert "exposicao" not in veto["content"] and "exposicao" not in ticket(e)


def test_delegated_decision_records_who_delegated():
    e = run_scenario("delegacao_valida")
    assert not rejeicoes(e)
    t = ticket(e)
    assert t["aprovado_por"] == {"agente": "APR", "pessoa": "ana", "titulo": "gerente", "sessao": "SIM-ana",
                                 "por_delegacao_de": "diego", "delegacao": "DLG-001"}
    assert t["decisao"] == "waiver" and e.resposta.content["status"] == "publicado_com_ressalva"
    trilha = e.system.acesso.trilha.ler()
    assert any(r["evento"] == "delegacao_criada" and r["delegacao"] == "DLG-001" for r in trilha)


def test_expired_delegation_is_refused_and_the_delegator_decides():
    e = run_scenario("delegacao_expirada")
    assert rejeicoes(e) == ["POL-11: a delegação DLG-001 expirou em t=5"]
    assert ticket(e)["aprovado_por"]["pessoa"] == "diego" and "por_delegacao_de" not in ticket(e)["aprovado_por"]


def test_four_eyes_endorse_then_approve_by_another_person():
    e = run_scenario("dupla_aprovacao")
    assert not rejeicoes(e)
    t = ticket(e)
    assert (t["exposicao"], t["dupla"]) == (3000000, True)
    assert t["aprovado_por"]["pessoa"] == "diego" and t["aprovado_por"]["aval"] == {"pessoa": "carla",
                                                                                   "sessao": "SIM-carla"}
    aval = next(r for r in reg(e, "send") if r.get("performative") == "endorse")
    assert (aval["de"], aval["para"]) == ("PENDENTE", "PENDENTE") and aval["content"]["atestado"]["pessoa"] == "carla"
    assert [r["endossos"] for r in reg(e, "politica") if r["evento"] == "endossado"] == [1]
    assert e.resposta.content["status"].startswith("publicado")


def test_same_person_cannot_endorse_and_approve():
    e = run_scenario("dupla_mesma_pessoa_recusada")
    assert len(rejeicoes(e)) == 1 and rejeicoes(e)[0].startswith("POL-12: carla já deu o aval")
    assert ticket(e)["aprovado_por"]["pessoa"] == "diego"


def test_approval_without_endorsement_is_refused_above_the_limit():
    sc = Scenario("sem_aval", "aprovação direta acima do limite", "fechar_mes", porte="grande", plantar=("alcada",),
                  acesso=True, solicitante="elisa", decisao_aprovador="nenhuma")
    from fin_mas.env.scenarios import montar
    sistema, _ = montar(sc)
    while not sistema.aprovador.avisos:  # até o aprovador receber a proposta (o ticket segue pendente)
        assert sistema.bus.step()
    (tid,) = sistema.politica.tickets
    proposta = next(r for r in sistema.bus.audit.records if r["kind"] == "open" and r.get("protocol") == "PROT-APR")
    from fin_mas.services.politica import digest_decisao
    conteudo = {"aprovacao": tid, "solicitacao": proposta["content"]["solicitacao"], "veto": proposta["content"]["veto"],
                "decisao": "corrigir", "justificativa": "corrige o lançamento acima da alçada",
                "correcoes": proposta["content"]["correcoes_sugeridas"]}
    acesso = sistema.acesso
    conteudo["atestado"] = acesso.atestar(acesso.sessao_simulada("diego"), ticket=tid, veto=conteudo["veto"],
                                          decisao="corrigir", corpo=digest_decisao(conteudo))
    with pytest.raises(Exception, match="POL-12: acima de R\\$ 25.000,00 a liberação exige duas pessoas"):
        sistema.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, conteudo)
    # num ticket sem dupla aprovação, o aval não existe
    e = run_scenario("waiver_exige_cargo")
    assert ticket(e)["dupla"] is False


def test_ticket_escalates_after_half_the_deadline():
    e = run_scenario("escalonamento")
    (recusa,) = rejeicoes(e)
    assert recusa.startswith("POL-14: o ticket APR-001 está no nível gerente: elisa (diretor)")
    (escalado,) = [r for r in reg(e, "politica") if r["evento"] == "escalado"]
    emitido = next(r for r in reg(e, "politica") if r["evento"] == "emitido")
    assert (escalado["de"], escalado["para"]) == ("gerente", "diretor")
    assert escalado["t"] == emitido["escalona_em"] == emitido["t"] + 10  # 50% do prazo de 20 ticks
    t = ticket(e)
    assert t["aprovado_por"]["pessoa"] == "elisa" and t["decidido_em"] >= escalado["t"]
    assert any(r["evento"] == "ticket_escalado" for r in e.system.acesso.trilha.ler())


def test_advanced_access_attacks_are_all_rejected():
    e = run_scenario("ataque_acesso_avancado")
    (ataques,) = reg(e, "ataques")
    resultados = ataques["resultados"]
    assert len(resultados) == 12 and not [r for r in resultados if r["aceito"]]
    regras = {r["ataque"]: r["motivo"].split(":")[0] for r in resultados}
    assert {r for r in regras.values()} == {"IAM-04", "IAM-08", "IAM-09", "POL-10", "POL-11", "POL-12"}
    assert regras["código TOTP já usado na ativação, repetido na entrada (replay)"] == "IAM-08"
    assert regras["código de recuperação usado duas vezes"] == "IAM-08"
    assert regras["pré-sessão (senha certa, sem o código) usada numa rota comum"] == "IAM-04"
    assert regras["quem recebeu a delegação tenta repassá-la (subdelegação)"] == "POL-11"
    assert regras["a mesma pessoa dá o aval e aprova (quatro olhos com dois)"] == "POL-12"
    assert regras["analista libera R$ 30 mil com alçada de R$ 20 mil"] == "POL-10"
    assert regras["aprovador de outra empresa decide sobre o ticket desta"] == "IAM-09"
    m = metricas.medir_acesso(e)
    assert (m["ataques_tentados"], m["ataques_aceitos"], m["decisoes_aceitas"]) == (12, 0, 0)
    t = ticket(e)
    assert t["estado"] == "expirado" and t["aprovado_por"] is None and not e.system.dataset.correcoes
    assert e.resposta.performative == "failure" and e.resposta.content["publicado"] is False
    trace = json.dumps(e.audit.records, ensure_ascii=False, default=str)
    assert "Ataque-Simulado-2026" not in trace  # a senha da conta de verdade não vaza


def test_invariants_catch_a_single_person_release_and_one_above_authority():
    e = run_scenario("dupla_aprovacao")
    registros = copy.deepcopy(e.audit.records)
    decidido = next(r for r in registros if r["kind"] == "politica" and r.get("evento") == "decidido")
    decidido["aprovado_por"]["aval"]["pessoa"] = decidido["aprovado_por"]["pessoa"]
    decidido["alcada"] = 100
    violacoes = invariantes.verificar(registros)
    assert any(v.startswith("INV-09") for v in violacoes) and any(v.startswith("INV-10") for v in violacoes)


AGOSTO = Scenario("agosto", "waiver em agosto", "fechar_mes", decisao_aprovador="waiver",
                  agenda=(("2026-08", ("alcada",)),), pedidos=(("fechar_mes", "2026-08", 1),))
SETEMBRO = Scenario("setembro", "mesma alçada em setembro", "fechar_mes", decisao_aprovador="waiver",
                    agenda=(("2026-09", ("alcada",)),), pedidos=(("fechar_mes", "2026-09", 1),))


def test_one_company_memory_is_never_remembered_in_another(tmp_path):
    """IAM-09: dados/<empresa>/memoria.json por empresa: o waiver de alfa não vira reincidência em beta, e a cópia
    da memória de alfa colocada na pasta de beta não é lida (fica comprometida, falha fechada)."""
    import shutil
    alfa, beta = tmp_path / "dados" / "alfa" / "memoria.json", tmp_path / "dados" / "beta" / "memoria.json"
    run_scenario(AGOSTO, memoria=alfa)
    em_alfa = run_scenario(SETEMBRO, memoria=alfa)
    assert ticket(em_alfa)["negadas"][0]["regra"] == "POL-06"  # alfa lembra do próprio waiver
    em_beta = run_scenario(SETEMBRO, memoria=beta)
    assert ticket(em_beta)["negadas"] == [] and em_beta.resposta.content["status"] == "publicado_com_ressalva"
    assert not [r for r in reg(em_beta, "memoria") if r["evento"] == "consultada"]
    beta.unlink()
    shutil.copy(alfa, beta)  # alguém copia a memória de alfa para beta
    copiada = run_scenario(SETEMBRO, memoria=beta)
    assert not copiada.system.memoria.integra and "outra pasta" in copiada.system.memoria.comprometida

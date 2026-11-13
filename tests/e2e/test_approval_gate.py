"""DSM3 — Approval Gate (PROT-APR) e política de aprovação do SVC-POL.

Decisão humana vinculada à solicitação, ao veto (hash), à identidade do aprovador e a um
prazo; uso único; efeito externo (correção no ERP) só com aprovação válida.
"""
import pytest

from fin_mas.core.bus import MensagemRejeitada
from fin_mas.env.scenarios import build_system, run_scenario
from fin_mas.mcp.gateway import ToolDenied
from fin_mas.services.politica import AprovacaoNecessaria
from helpers import rodar_ate_humano

pytestmark = pytest.mark.e2e


def pendente(plantar=("alcada",), **kw):
    s = build_system(plantar=plantar, interativo=True, **kw)
    sid = s.usuario.solicitar("fechar_mes")
    rodar_ate_humano(s.bus)
    proposta = s.aprovador.pendentes[sid]
    return s, sid, proposta


JUSTIFICATIVA = "aceito o risco: lançamento será corrigido no próximo ciclo"


def decisao(sid, proposta, **extra):
    return {"aprovacao": proposta.conversation_id, "solicitacao": sid, "veto": proposta.content["veto"],
            "justificativa": JUSTIFICATIVA, **extra}


def test_external_action_requires_approval():
    """TEST-12: a correção no ERP fica retida enquanto o ticket está PENDENTE."""
    s, sid, proposta = pendente()
    tid, alvo = proposta.conversation_id, proposta.content["correcoes_sugeridas"][0]
    antes = [dict(x) for x in s.dataset.lancamentos]
    with pytest.raises(AprovacaoNecessaria, match="pendente"):  # o próprio Orquestrador, autenticado
        s.orq.ferramenta("erp.corrigir", tid, aprovacao=tid, lancamento=alvo["lancamento"], acao=alvo["acao"])
    with pytest.raises(AprovacaoNecessaria, match="sem aprovação"):
        s.orq.ferramenta("erp.corrigir", tid, lancamento=alvo["lancamento"], acao=alvo["acao"])
    with pytest.raises(ToolDenied, match="não autenticada"):  # terceiro em nome do Orquestrador
        s.gateway.call("AG-ORQ", "erp.corrigir", tid, aprovacao=tid, lancamento=alvo["lancamento"], acao=alvo["acao"])
    with pytest.raises(MensagemRejeitada, match="execução sem aprovação humana"):
        s.orq.avancar(tid, "execute")
    assert s.dataset.lancamentos == antes and s.dataset.correcoes == []
    assert s.bus.conversations[tid].state == "PENDENTE"
    s.aprovador.decidir(sid, "corrigir")  # com a aprovação, o efeito executa e o AG-CIN reavalia
    s.bus.run()
    assert s.bus.conversations[tid].state == "EXECUTADA"
    assert [c["lancamento"] for c in s.dataset.correcoes] == [alvo["lancamento"]]
    assert s.usuario.resposta(sid).content["status"] == "publicado"


def test_denied_action_never_executes():
    """TEST-13: fora da allowlist ou sem opção de liberação (DENY), nada chega à fonte de dados."""
    s, sid, proposta = pendente()
    alvo = proposta.content["correcoes_sugeridas"][0]
    with pytest.raises(ToolDenied):
        s.gateway.call("AG-REL", "erp.corrigir", "X", aprovacao=proposta.conversation_id,
                       lancamento=alvo["lancamento"], acao=alvo["acao"])
    assert s.dataset.correcoes == []
    # política sem nenhuma liberação possível: ticket NEGADO, bloqueio imediato, approve impossível
    s2 = build_system(plantar=("alcada",), aprovadores={"APR": {"pessoa": "controller", "titulo": "Controller",
                                                               "decisoes": ["waiver", "corrigir", "bloquear"]}})
    original = s2.orq.politica.emitir  # força o caso: o veto chega sem nenhuma opção de liberação

    def sem_liberacao(**kw):
        kw["veto"] = {**kw["veto"], "opcoes": ["bloquear"]}
        return original(**kw)

    s2.orq.politica.emitir = sem_liberacao
    sid2 = s2.usuario.solicitar("fechar_mes")
    s2.bus.run()
    assert s2.bus.conversations["APR-001"].state == "NEGADA"
    assert s2.usuario.resposta(sid2).content["decisao"] == "negada"
    assert s2.dataset.correcoes == [] and s2.aprovador.avisos  # o aprovador só toma ciência
    with pytest.raises(MensagemRejeitada, match="ação DENY não admite aprovação|não admite"):
        s2.aprovador.send("AG-ORQ", "approve", "PROT-APR", "APR-001",
                          decisao(sid2, s2.aprovador.avisos[0], decisao="waiver"))


def test_approval_bound_to_request_veto_and_ticket():
    s, sid, proposta = pendente()
    tid = proposta.conversation_id
    with pytest.raises(MensagemRejeitada, match="hash do veto não confere"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**decisao(sid, proposta, decisao="waiver"),
                                                                "veto": "f" * 64})
    with pytest.raises(MensagemRejeitada, match="é da solicitação"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, decisao("SOL-999", proposta, decisao="waiver"))
    with pytest.raises(MensagemRejeitada, match="não corresponde ao ticket"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**decisao(sid, proposta, decisao="waiver"),
                                                                "aprovacao": "APR-777"})
    with pytest.raises(MensagemRejeitada, match="campo obrigatório ausente: veto"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid,
                         {"aprovacao": tid, "solicitacao": sid, "decisao": "waiver", "justificativa": "aceito o risco"})
    assert s.bus.conversations[tid].state == "PENDENTE"


def test_duplicate_approval_is_rejected():
    s, sid, proposta = pendente()
    tid, d = proposta.conversation_id, decisao(sid, proposta, decisao="waiver")
    s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, d)
    with pytest.raises(MensagemRejeitada, match="já está aprovado|aprovação duplicada"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, d)
    with pytest.raises(MensagemRejeitada):
        s.aprovador.send("AG-ORQ", "reject", "PROT-APR", tid, decisao(sid, proposta))
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r.content["status"] == "publicado_com_ressalva"
    assert sum(1 for x in r.content["ressalvas"] if x.startswith("waiver de alcada")) == 1


def test_late_approval_after_deadline_is_discarded():
    s, sid, proposta = pendente(prazo_aprovacao=15)
    s.bus.run()  # ninguém decide: o prazo do ticket esgota
    assert s.bus.conversations[proposta.conversation_id].state == "EXPIRADA"
    s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA)  # decisão atrasada
    s.bus.run()
    assert any(r["kind"] == "discard" and r["conversation_id"] == proposta.conversation_id
               for r in s.bus.audit.records)
    r = s.usuario.resposta(sid)
    assert r.performative == "failure" and r.content["decisao"] == "expirada" and r.content["publicado"] is False
    assert s.politica.tickets[proposta.conversation_id]["estado"] == "expirado"


def test_approval_reuse_across_veto_cycles_is_rejected():
    """Correção parcial: o ticket do 1º ciclo (APR-001) não vale para o 2º veto (APR-002)."""
    s = build_system(plantar=("alcada", "sod"), decisao_aprovador=("corrigir_parcial",), interativo=False)
    s.aprovador.decisoes = ["corrigir_parcial", "nenhuma"]
    sid = s.usuario.solicitar("fechar_mes")
    rodar_ate_humano(s.bus)
    assert s.politica.tickets["APR-001"]["consumido"] is True
    assert s.bus.conversations["APR-002"].state == "PENDENTE"
    with pytest.raises(MensagemRejeitada, match="já foi usada|já está executado"):
        s.orq.send("AG-CIN", "correcao", "PROT-CMP", "CMP-001",
                   {"aprovacao": "APR-001", "correcoes": s.politica.tickets["APR-001"]["executadas"]})
    with pytest.raises(MensagemRejeitada, match="já foi usada|com decisão corrigir"):
        s.orq.send("AG-CIN", "waiver_humano", "PROT-CMP", "CMP-001",
                   {"aprovacao": "APR-001", "justificativa": "reaproveitar a aprovação anterior"})
    velho = s.aprovador.avisos[0]
    with pytest.raises(MensagemRejeitada):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", "APR-001", decisao(sid, velho, decisao="waiver"))
    s.bus.run()
    assert s.usuario.resposta(sid).performative == "failure"


def test_approver_role_limits_decisions():
    """POL-02: um analista pode pedir correção ou bloquear, mas não conceder waiver."""
    analista = {"APR": {"pessoa": "analista.revisor", "titulo": "Analista", "decisoes": ["corrigir", "bloquear"]}}
    s, sid, proposta = pendente(aprovadores=analista)
    with pytest.raises(MensagemRejeitada, match="POL-02.*não pode decidir 'waiver'"):
        s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA)
    assert sid in s.aprovador.pendentes  # a recusa não consome a pendência (revisão do PR, item 1)
    s.aprovador.decidir(sid, "corrigir")
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"] == "publicado"


def test_approver_involved_in_vetoed_entry_cannot_decide():
    """POL-03: quem aprovou o lançamento vetado não decide sobre ele (SoD da aprovação)."""
    s0, _, p0 = pendente()
    envolvido = s0.politica.tickets[p0.conversation_id]["envolvidos"][0]
    s, sid, proposta = pendente(aprovadores={"APR": {"pessoa": envolvido, "titulo": "Gerente",
                                                     "decisoes": ["waiver", "corrigir", "bloquear"]}})
    with pytest.raises(MensagemRejeitada, match="POL-03"):
        s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA)
    assert s.bus.conversations[proposta.conversation_id].state == "PENDENTE"


def test_waiver_requires_justification_and_correction_must_be_suggested():
    s, sid, proposta = pendente()
    tid = proposta.conversation_id
    with pytest.raises(MensagemRejeitada, match="POL-04"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**decisao(sid, proposta, decisao="waiver"),
                                                                "justificativa": "ok"})
    with pytest.raises(MensagemRejeitada, match="POL-05"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid,
                         decisao(sid, proposta, decisao="corrigir",
                                 correcoes=[{"lancamento": "L-001", "acao": "estornar"}]))
    with pytest.raises(MensagemRejeitada, match="POL-05"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, decisao(sid, proposta, decisao="corrigir"))
    assert s.dataset.correcoes == []


def test_reject_blocks_publication_and_is_audited():
    s, sid, proposta = pendente()
    s.aprovador.decidir(sid, "bloquear", "lançamento sem documentação de suporte")
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r.performative == "failure" and r.content["decisao"] == "bloquear"
    assert s.bus.conversations[proposta.conversation_id].state == "REJEITADA"
    t = s.politica.tickets[proposta.conversation_id]
    assert t["aprovado_por"]["agente"] == "APR" and t["justificativa"] == "lançamento sem documentação de suporte"
    assert any(x["kind"] == "politica" and x["evento"] == "decidido" for x in s.bus.audit.records)


def test_recurring_violation_after_waiver_denies_new_waiver():
    """POL-06 + SVC-MEM: o waiver de agosto não se repete em setembro para o mesmo padrão."""
    e = run_scenario("reincidencia_waiver")
    t1, t2 = e.system.politica.tickets["APR-001"], e.system.politica.tickets["APR-002"]
    assert "waiver" in t1["opcoes"] and "waiver" not in t2["opcoes"]
    assert t2["negadas"][0]["regra"] == "POL-06" and "MEM-0001" in t2["negadas"][0]["motivo"]
    agosto, setembro = (e.respostas[s] for s in e.sids)
    assert agosto.content["status"] == "publicado_com_ressalva"
    assert setembro.content["status"] == "publicado" and setembro.content["notas"]
    veto = next(r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto"
                and r["conversation_id"] == t2["cmp"])
    assert veto["content"]["achados"][0]["reincidencia"]["memoria"] == "MEM-0001"


def test_lost_approval_never_leaves_request_without_answer():
    """Revisão da DSM3 (G2): approve perdido em trânsito expira o ticket e o solicitante recebe failure."""
    from fin_mas.core.bus import Fault

    s = build_system(plantar=("alcada",), decisao_aprovador="waiver",
                     faults=[Fault(receiver="AG-ORQ", performative="approve", times=1)])
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r.performative == "failure" and r.content["decisao"] == "expirada" and r.content["publicado"] is False
    assert s.bus.conversations["APR-001"].state == "EXPIRADA"
    assert s.politica.tickets["APR-001"]["estado"] == "expirado"
    assert s.locks.dono("SMA", "2026-09") is None  # reserva liberada
    assert all(c.is_final for c in s.bus.conversations.values())


def test_non_serializable_content_is_rejected_before_any_side_effect():
    """Revisão da DSM3 (G2): conteúdo que não vira JSON é rejeitado antes de a política ou a FSM mudarem."""
    s, sid, proposta = pendente()
    tid = proposta.conversation_id
    with pytest.raises(MensagemRejeitada, match="não serializável"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**decisao(sid, proposta, decisao="waiver"), 1: "x"})
    assert s.bus.conversations[tid].state == "PENDENTE" and s.politica.tickets[tid]["estado"] == "pendente"
    s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA)  # a decisão legítima continua possível
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"] == "publicado_com_ressalva"
    assert s.bus.conversations[tid].state == "EXECUTADA"  # waiver também fecha o ticket


def test_period_lock_is_renewed_while_waiting_for_approver():
    """Revisão da DSM3 (G3): a espera pelo aprovador não deixa outro fechamento do mesmo mês entrar."""
    s = build_system(plantar=("alcada",), interativo=True)
    primeiro = s.usuario.solicitar("fechar_mes")
    segundo = s.usuario.solicitar("fechar_mes", atraso=250)  # depois do TTL original (200)
    while s.bus.proximo_tempo() is not None and s.bus.proximo_tempo() < 400:
        s.bus.step()
    assert s.usuario.resposta(segundo).performative == "refuse"
    assert any(r["kind"] == "lock" and r["evento"] == "renovar" for r in s.bus.audit.records)
    s.aprovador.decidir(primeiro, "waiver", "risco aceito pelo controller nesta competência")
    s.bus.run()
    assert s.usuario.resposta(primeiro).content["status"] == "publicado_com_ressalva"


def test_waiver_justification_must_have_content():
    s, sid, proposta = pendente()
    for texto in ("aaaaaaaaaa", "ok ok ok ok ok"):
        with pytest.raises(MensagemRejeitada, match="POL-04"):
            s.aprovador.send("AG-ORQ", "approve", "PROT-APR", proposta.conversation_id,
                             {**decisao(sid, proposta, decisao="waiver"), "justificativa": texto})


def test_decision_that_cannot_be_delivered_in_time_is_rejected():
    """Recorreção (N4): decisão no último tick é recusada explicitamente, e não aceita e depois expirada."""
    s, sid, proposta = pendente(prazo_aprovacao=15)
    tid, expira = proposta.conversation_id, s.politica.tickets[proposta.conversation_id]["expira_em"]
    while s.bus.proximo_tempo() is not None and s.bus.proximo_tempo() < expira:
        s.bus.step()
    s.bus.now = expira - 1  # o humano decide no último tick antes do prazo
    with pytest.raises(MensagemRejeitada, match="não seria entregue no prazo"):
        s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA)
    assert s.politica.tickets[tid]["estado"] == "pendente" and s.politica.tickets[tid]["aprovado_por"] is None
    s.bus.run()
    assert s.usuario.resposta(sid).content["decisao"] == "expirada"


def test_deadline_check_uses_the_real_delivery_time_of_the_decision():
    """Residual da 3ª rodada: a checagem do prazo supunha entrega em um tick. Uma decisão enviada com
    antecedência, mas por um canal lento (entrega depois do prazo), é recusada; pelo canal normal, vale."""
    s, sid, proposta = pendente(prazo_aprovacao=15)
    tid, expira = proposta.conversation_id, s.politica.tickets[proposta.conversation_id]["expira_em"]
    falta = expira - s.bus.now
    assert falta > 3
    with pytest.raises(MensagemRejeitada, match="não seria entregue no prazo"):
        s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid,
                         {**decisao(sid, proposta, decisao="waiver"), "justificativa": JUSTIFICATIVA}, delay=falta)
    assert s.politica.tickets[tid]["estado"] == "pendente" and s.politica.tickets[tid]["aprovado_por"] is None
    s.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid,
                     {**decisao(sid, proposta, decisao="waiver"), "justificativa": JUSTIFICATIVA}, delay=falta - 1)
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"] == "publicado_com_ressalva"

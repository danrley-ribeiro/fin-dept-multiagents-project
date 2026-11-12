"""DSM3 — autenticidade e integridade das interações (feedback da DSM2).

Cada teste reproduz um ataque relatado pelo professor ou um da mesma família e verifica
que o barramento o rejeita, registra a rejeição e não muda o estado de nenhuma conversa.
"""
import pytest

from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, MensagemRejeitada
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message
from fin_mas.env.scenarios import build_system, run_scenario
from helpers import rodar_ate_humano

pytestmark = pytest.mark.e2e


def vetado():
    """Fechamento com alçada violada, aprovador em silêncio: o veto fica pendente no PROT-APR."""
    s = build_system(plantar=("alcada",), decisao_aprovador="nenhuma")
    sid = s.usuario.solicitar("fechar_mes")
    rodar_ate_humano(s.bus)
    assert s.bus.conversations["CMP-001"].state == "VETADO"
    assert s.bus.conversations["APR-001"].state == "PENDENTE"
    return s, sid


def rejeicoes(s, etapa=None):
    return [r for r in s.bus.audit.records if r["kind"] == "rejected" and (etapa is None or r["etapa"] == etapa)]


def test_forged_human_decision_from_unknown_sender_is_rejected():
    """O ataque do feedback: decisao_humana de remetente inexistente liberava o fechamento vetado."""
    s, sid = vetado()
    with pytest.raises(MensagemRejeitada, match="remetente desconhecido"):
        s.bus.send(Message("FANTASMA", "AG-ORQ", "decisao_humana", "CMP-001", None,
                           {"solicitacao": sid, "decisao": "waiver", "justificativa": "liberar já"}))
    s.bus.run()
    r = s.usuario.resposta(sid)
    assert r.performative == "failure" and r.content["publicado"] is False
    assert s.bus.conversations["CMP-001"].state == "BLOQUEADO"
    assert not [c for c in s.bus.conversations.values() if c.counterpart == "AG-REL"]  # nada foi publicado
    assert rejeicoes(s, "autenticacao")


def test_spoofed_approver_identity_without_credential_is_rejected():
    s, sid = vetado()
    proposta = s.aprovador.avisos[0].content
    decisao = {"aprovacao": "APR-001", "solicitacao": sid, "veto": proposta["veto"], "decisao": "waiver",
               "justificativa": "aceito o risco do lançamento"}
    with pytest.raises(MensagemRejeitada, match="não autenticado"):
        s.bus.send(Message("APR", "AG-ORQ", "approve", "APR-001", "PROT-APR", decisao))
    intruso = Agent("INTRUSO", s.bus, "ROLE-APR")  # registrado, mas usa a credencial dele para se passar por APR
    with pytest.raises(MensagemRejeitada, match="não autenticado"):
        s.bus.send(Message("APR", "AG-ORQ", "approve", "APR-001", "PROT-APR", decisao),
                   credencial=intruso._Agent__credencial)
    with pytest.raises(MensagemRejeitada, match="não participa"):
        intruso.send("AG-ORQ", "approve", "PROT-APR", "APR-001", decisao)
    assert s.bus.conversations["APR-001"].state == "PENDENTE"
    assert s.politica.tickets["APR-001"]["estado"] == "pendente"


def test_registered_agent_without_role_cannot_approve():
    s, sid = vetado()
    proposta = s.aprovador.avisos[0].content
    decisao = {"aprovacao": "APR-001", "solicitacao": sid, "veto": proposta["veto"], "decisao": "waiver",
               "justificativa": "aceito o risco do lançamento"}
    with pytest.raises(MensagemRejeitada, match="ROLE-REL .* não pode emitir 'approve'"):
        s.agentes["AG-REL"].send("AG-ORQ", "approve", "PROT-APR", "APR-001", decisao)
    with pytest.raises(MensagemRejeitada, match="ROLE-ORQ .* não pode emitir 'approve'"):
        s.orq.send("APR", "approve", "PROT-APR", "APR-001", decisao)
    assert s.bus.conversations["APR-001"].state == "PENDENTE"


def test_local_transition_by_unauthorized_identity_is_rejected():
    """O ataque do feedback: transição local atribuída a identificador não autorizado mudava a FSM."""
    s, sid = vetado()
    with pytest.raises(MensagemRejeitada, match="identidade desconhecida"):
        s.bus.advance("CMP-001", "publicar", "HACKER")
    with pytest.raises(MensagemRejeitada, match="sem credencial"):
        s.bus.advance("CMP-001", "publicar", "AG-ORQ")  # identidade real, sem a credencial
    with pytest.raises(MensagemRejeitada, match="ROLE-CIN .* não pode aplicar 'publicar'"):
        s.agentes["AG-CIN"].avancar("CMP-001", "publicar")
    with pytest.raises(MensagemRejeitada, match="ROLE-ORQ .* não pode aplicar 'require_approval'"):
        s.orq.avancar("APR-001", "require_approval")  # só o SVC-POL classifica
    with pytest.raises(MensagemRejeitada, match="não é um evento local"):
        s.orq.avancar("CMP-001", "waiver_humano")  # waiver não é atalho local
    with pytest.raises(ProtocolViolation, match="publicar resultado vetado"):
        s.orq.avancar("CMP-001", "publicar")  # o participante autorizado também respeita a FSM
    assert s.bus.conversations["CMP-001"].state == "VETADO"
    assert len(rejeicoes(s)) == 6


def test_reply_to_non_participant_receiver_is_rejected():
    """O ataque do feedback: resposta destinada a quem não participa da conversa era aceita."""
    s = build_system()
    s.orq.send("AG-CUS", "request", "PROT-DEL", "DEL-900",
               {"tarefa": "apurar_custos", "entidade": "SMA", "competencia": "2026-09"})
    with pytest.raises(MensagemRejeitada, match="AG-RES não é a contraparte de AG-CUS em DEL-900"):
        s.agentes["AG-CUS"].send("AG-RES", "agree", "PROT-DEL", "DEL-900")
    with pytest.raises(MensagemRejeitada, match="destinatário desconhecido"):
        s.agentes["AG-CUS"].send("NINGUEM", "agree", "PROT-DEL", "DEL-900")
    assert s.bus.conversations["DEL-900"].state == "AGUARDANDO"
    assert rejeicoes(s, "destinatario")


def test_malformed_request_does_not_crash_simulation():
    """O caso do feedback: pedido sem campos obrigatórios gerava KeyError e parava a execução."""
    s = build_system()
    with pytest.raises(MensagemRejeitada, match="campo obrigatório ausente: entidade"):
        s.usuario.send("AG-ORQ", "request", "PROT-SOL", "SOL-900", {"intencao": "fechar_mes"})
    with pytest.raises(MensagemRejeitada, match="deveria ser str"):
        s.usuario.send("AG-ORQ", "request", "PROT-SOL", "SOL-901",
                       {"intencao": "fechar_mes", "entidade": 7, "competencia": "2026-09"})
    with pytest.raises(MensagemRejeitada, match="reply_by"):
        s.usuario.send("AG-ORQ", "request", "PROT-SOL", "SOL-902",
                       {"intencao": "fechar_mes", "entidade": "SMA", "competencia": "2026-09"}, reply_by=0)
    with pytest.raises(MensagemRejeitada, match="ontologia"):
        s.bus.send(Message("SOL", "AG-ORQ", "request", "SOL-903", "PROT-SOL",
                           {"intencao": "fechar_mes", "entidade": "SMA", "competencia": "2026-09"}, ontology="x"),
                   credencial=s.usuario._Agent__credencial)
    sid = s.usuario.solicitar("avaliar_orcamento")  # a simulação segue normalmente
    s.bus.run()
    assert s.usuario.resposta(sid).performative == "inform"
    assert not {"SOL-900", "SOL-901", "SOL-902", "SOL-903"} & set(s.bus.conversations)
    assert len(rejeicoes(s, "esquema")) == 4


def test_agent_exception_is_isolated_and_answered():
    """Um agente com defeito não derruba a simulação: o erro é auditado e a conversa recebe resposta."""
    s = build_system()

    def defeito(msg):
        raise KeyError("campo_que_nao_existe")

    s.agentes["AG-REL"].on_message = defeito
    sid = s.usuario.solicitar("avaliar_orcamento")
    s.bus.run()
    erros = [r for r in s.bus.audit.records if r["kind"] == "erro_agente"]
    assert erros and erros[0]["agente"] == "AG-REL" and "KeyError" in erros[0]["erro"]
    r = s.usuario.resposta(sid)
    assert r.performative == "failure" and r.content["subtarefa"] == "relatorio"


def test_content_tampering_after_send_is_detected():
    s = build_system()
    conteudo = {"tarefa": "apurar_custos", "entidade": "SMA", "competencia": "2026-09"}
    s.orq.send("AG-CUS", "request", "PROT-DEL", "DEL-900", conteudo)
    conteudo["tarefa"] = "outra"  # o remetente não altera o que já foi enviado (cópia no envio)
    _, _, _, (msg, _) = s.bus._queue[0]
    assert msg.content["tarefa"] == "apurar_custos"
    msg.content["entidade"] = "OUTRA"  # adulteração do conteúdo enfileirado
    s.bus.run()
    perdidas = [r for r in s.bus.audit.records if r["kind"] == "drop" and r["motivo"].startswith("integridade")]
    assert perdidas and perdidas[0]["conversation_id"] == "DEL-900"
    assert not [r for r in s.bus.audit.records if r["kind"] == "deliver" and r["conversation_id"] == "DEL-900"]
    assert not s.agentes["AG-CUS"].estado["custos"]  # a mensagem adulterada não foi tratada


def test_identity_impersonation_on_register_is_rejected():
    s = build_system()
    with pytest.raises(ProtocolViolation, match="já registrada"):
        Agent("APR", s.bus, "ROLE-APR")
    with pytest.raises(ProtocolViolation, match="não consta no diretório"):
        Agent("AG-REL", Bus(), "ROLE-APR")  # id conhecido com papel de outro
    with pytest.raises(ProtocolViolation, match="papel desconhecido"):
        Agent("X", s.bus, "ROLE-ADMIN")


def test_adversarial_scenario_rejects_every_attack():
    """Cenário `ataque_decisao_forjada`: todos os ataques são rejeitados e nada é publicado."""
    e = run_scenario("ataque_decisao_forjada")
    resultado = next(r for r in e.audit.records if r["kind"] == "ataques")
    assert len(resultado["resultados"]) == 14  # a sequência inteira rodou
    assert not [x for x in resultado["resultados"] if x["aceito"]]
    assert not [r for r in e.audit.records if r["kind"] == "erro_agente"]
    assert sum(1 for r in e.audit.records if r["kind"] == "rejected") == 12
    assert sum(1 for r in e.audit.records if r["kind"] == "mcp_denied") == 2  # sem aprovação; identidade falsa
    assert e.resposta.performative == "failure" and e.resposta.content["publicado"] is False
    assert e.system.bus.conversations["CMP-001"].state == "BLOQUEADO"
    assert e.system.bus.conversations["APR-001"].state == "EXPIRADA"
    linhas = e.audit.trilha(e.sid)
    assert any("REJEITADA [autenticacao] FANTASMA" in linha for linha in linhas)
    assert any("ATAQUES" in linha and "rejeitados" in linha for linha in linhas)


@pytest.mark.parametrize("cenario", ["fechar_mes", "veto_waiver", "veto_correcao", "correcao_parcial",
                                     "expediente_sma", "reincidencia_waiver", "fechamento_micro"])
def test_nominal_scenarios_have_no_rejection_or_agent_error(cenario):
    """Os agentes legítimos cumprem esquemas, papéis e FSM: nenhuma rejeição nem erro nos cenários nominais."""
    e = run_scenario(cenario)
    assert not [r for r in e.audit.records if r["kind"] in ("rejected", "erro_agente")]


def test_invalid_period_or_unknown_entity_is_refused():
    """Revisão da DSM3: competência fora do formato é barrada na entrada; entidade desconhecida recebe refuse."""
    s = build_system()
    for competencia in ("xx", "2026-99", "2026-00", "26-09", "2026-9", "0001-01", "9999-12"):
        with pytest.raises(MensagemRejeitada, match="AAAA-MM"):
            s.usuario.send("AG-ORQ", "request", "PROT-SOL", f"SOL-{competencia}",
                           {"intencao": "fechar_mes", "entidade": "SMA", "competencia": competencia})
    outra = s.usuario.solicitar("avaliar_orcamento", entidade="OUTRA")
    valida = s.usuario.solicitar("avaliar_orcamento")
    s.bus.run()
    recusa = s.usuario.resposta(outra)
    assert recusa.performative == "refuse" and "entidade desconhecida" in recusa.content["motivo"]
    assert s.usuario.resposta(valida).performative == "inform"
    assert not [r for r in s.bus.audit.records if r["kind"] == "erro_agente"]
    assert not [c for c in s.bus.conversations.values() if c.protocol.id == "PROT-DEL"
                and c.conversation_id in s.bus.audit.familia(outra)]  # nada foi delegado

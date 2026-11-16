"""DSM3 — achados da 5ª rodada de correção simulada (v0.5.0 no Windows), um teste por achado.

1. promover o cargo de uma conta não pode apagar o vínculo com a pessoa do ERP (senão a POL-03 some);
2. um participante que ocupa um `conversation_id` que o sistema vai gerar não deixa o pedido sem resposta,
   e qualquer erro interno do Orquestrador vira falha explícita para quem pediu;
3. reiniciar pelo dashboard nunca cria pedidos em nome de outra pessoa (nem bloqueia quem reiniciou de decidir);
4. o atraso de entrega do barramento é validado (texto, None, zero e negativo são rejeitados e auditados).
"""
import pytest

from fin_mas.core.bus import MensagemRejeitada
from fin_mas.env.scenarios import build_system
from fin_mas.services.iam import SENHA_DEMO, AcessoNegado, criar_demo
from test_dashboard_acesso import _ate_humano, entrar, servico  # noqa: F401  (fixture e login HTTP reais)

pytestmark = pytest.mark.integracao
PEDIDO = {"intencao": "fechar_mes", "entidade": "SMA", "competencia": "2026-08"}


# ---- 1. vínculo com a pessoa do ERP -----------------------------------------------------------------
def test_promoting_an_account_keeps_its_erp_person_and_removal_must_be_explicit(tmp_path):
    acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
    adm, _ = acesso.autenticar("admin", SENHA_DEMO, origem="cli")
    antes = acesso.conta("carla")
    assert antes["pessoa_erp"] == "carla"
    assert acesso.definir_vinculo(adm, "carla", cargo="diretor")["pessoa_erp"] == "carla"  # promoção não apaga a SoD
    depois = acesso.definir_vinculo(adm, "carla", pessoa_erp="bruno")
    assert (depois["pessoa_erp"], depois["cargo"]) == ("bruno", "diretor")  # e trocar a pessoa não apaga o cargo
    removido = acesso.definir_vinculo(adm, "carla", pessoa_erp=None)  # só remove quando pedido
    assert (removido["pessoa_erp"], removido["cargo"]) == (None, "diretor")
    with pytest.raises(AcessoNegado, match="IAM-05"):
        acesso.definir_vinculo(adm, "carla")  # nada a alterar
    for vazio in ("", "   ", 7):  # recorreção (achado B): texto vazio não remove o vínculo às escondidas
        with pytest.raises(AcessoNegado, match="IAM-05"):
            acesso.definir_vinculo(adm, "diego", pessoa_erp=vazio)
    assert acesso.conta("diego")["pessoa_erp"] == "diego"


# ---- 2. id de conversa ocupado e erro interno do Orquestrador --------------------------------------
@pytest.mark.parametrize("ocupado, plantar, decisao", [("APR-001", ("alcada",), "corrigir"), ("CMP-001", (), "nenhuma"),
                                                       ("DEL-001", (), "nenhuma")])
def test_squatted_conversation_id_does_not_leave_the_request_unanswered(ocupado, plantar, decisao):
    s = build_system(plantar=plantar, decisao_aprovador=decisao)
    s.usuario.send("AG-ORQ", "request", "PROT-SOL", ocupado, PEDIDO)  # abre, com outro protocolo, um id do sistema
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    resposta = s.usuario.resposta(sid)
    assert resposta is not None and resposta.performative == "inform" and resposta.content["status"].startswith("publicado")
    assert not [r for r in s.bus.audit.records if r["kind"] == "erro_agente"]
    assert s.locks.dono("SMA", "2026-09") is None


@pytest.mark.parametrize("erro", [RuntimeError("defeito"), MensagemRejeitada("envio recusado", "conversa")])
def test_orchestrator_internal_error_becomes_an_explicit_failure(erro):
    s = build_system(plantar=("alcada",), decisao_aprovador="corrigir")

    def quebrado(*_a, **_k):
        raise erro
    s.orq._veto = quebrado
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    resposta = s.usuario.resposta(sid)
    assert resposta.performative == "failure" and resposta.content["publicado"] is False
    assert "erro interno" in resposta.content["motivo"]
    assert s.locks.dono("SMA", "2026-09") is None  # o período não fica preso


# ---- 3. reinício pelo dashboard -------------------------------------------------------------------
def _ultimo_pedido(sim):
    return [r for r in sim.registros if r["kind"] == "open" and r["protocol"] == "PROT-SOL"][-1]["content"]


def test_restart_never_creates_requests_in_someone_elses_name(servico):  # noqa: F811
    sim, _, porta = servico("solicitante_nao_aprova")
    assert _ultimo_pedido(sim).get("solicitado_por") == "elisa"  # ao subir o servidor, vale o roteiro do cenário
    operador, avaliador = entrar(porta, "operador"), entrar(porta, "avaliador")
    reinicio = {"tipo": "reiniciar", "cenario": "solicitante_nao_aprova"}
    assert operador.post("/api/comando", reinicio)[0] == 202  # operar a simulação continua permitido
    sim.processar_comandos()
    assert _ultimo_pedido(sim).get("solicitado_por") is None  # operador não pode solicitar: pedido sem pessoa
    assert [r["ator"] for r in sim.registros if r["kind"] == "operador"] == ["operador"]  # e o trace diz quem reiniciou
    assert avaliador.post("/api/comando", {"tipo": "reiniciar", "cenario": "veto_waiver"})[0] == 202
    sim.processar_comandos()
    assert _ultimo_pedido(sim).get("solicitado_por") is None  # nem no nome de quem reiniciou
    _ate_humano(sim)
    decisao = {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "waiver", "justificativa": "risco aceito pela diretoria"}
    assert avaliador.post("/api/comando", decisao)[0] == 202
    sim.processar_comandos()
    assert not [r for r in sim.registros if r["kind"] == "rejected"]  # quem reiniciou continua podendo decidir (POL-13)
    assert not sim.sistema.aprovador.pendentes


# ---- 4. atraso de entrega ---------------------------------------------------------------------------
@pytest.mark.parametrize("atraso", ["1", None, 0, -5, 1.5, True])
def test_invalid_delivery_delay_is_rejected_and_audited(atraso):
    s = build_system()
    with pytest.raises(MensagemRejeitada, match="atraso de entrega inválido"):
        s.usuario.send("AG-ORQ", "request", "PROT-SOL", "SOL-900", dict(PEDIDO), delay=atraso)
    assert "SOL-900" not in s.bus.conversations
    assert [r["etapa"] for r in s.bus.audit.records if r["kind"] == "rejected"] == ["envelope"]

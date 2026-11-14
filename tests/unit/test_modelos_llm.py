"""DSM3 — LLM opcional do AG-REL pelo Registro de Modelos (ADR-002, NORM-05, NORM-07), sempre offline."""
import pytest

from fin_mas.env.scenarios import build_system, run_scenario
from fin_mas.services.audit import AuditLog
from fin_mas.services.modelos import ConfiguracaoInvalida, RegistroModelos

pytestmark = pytest.mark.e2e


def registros(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind]


def test_llm_numeric_mismatch_falls_back():
    """TEST-15: número alterado pelo LLM descarta o texto; o relatório sai só com o template."""
    base = run_scenario("fechar_mes")
    e = run_scenario("fechar_mes", llm="mock-alucina")
    assert e.resposta.content["relatorio"] == base.resposta.content["relatorio"]
    assert "NORM-05" in registros(e, "llm_fallback")[0]["motivo"]
    acao = run_scenario("fechar_mes", llm="mock-acao")  # proposta de ação também é descartada
    assert "propõe uma ação" in registros(acao, "llm_fallback")[0]["motivo"]
    assert acao.resposta.content["relatorio"] == base.resposta.content["relatorio"]
    ok = run_scenario("fechar_mes", llm="mock-narrador")
    relatorio = ok.resposta.content["relatorio"]  # desde a v0.5.0 a síntese do modelo vem ao fim, rotulada
    assert "não verificada" in relatorio and relatorio.index("\nSíntese: ") > relatorio.index("Receita:")
    assert base.resposta.content["relatorio"] in ok.resposta.content["relatorio"]  # a flag só acrescenta texto


def test_prompt_log_only_when_llm_enabled():
    """TEST-17: registro de prompt existe se e só se a flag está ligada."""
    assert not registros(run_scenario("fechar_mes"), "llm_prompt")
    ligado = registros(run_scenario("fechar_mes", llm="mock-narrador"), "llm_prompt")
    assert len(ligado) == 1 and ligado[0]["agente"] == "AG-REL" and ligado[0]["versao_prompt"]


def test_cost_log_per_call_and_task():
    """TEST-18: custo por chamada soma o total da tarefa; zero com a flag desligada."""
    assert not registros(run_scenario("fechar_mes"), "llm_custo")
    e = run_scenario("expediente_sma", llm="mock-narrador")
    custos = registros(e, "llm_custo")
    assert len(custos) == len(registros(e, "llm_prompt")) > 1
    total = sum(c["tokens_entrada"] + c["tokens_saida"] for c in custos)
    assert custos[-1]["acumulado_tokens"] == total == e.system.modelos.config("AG-REL")["usado"]


def test_model_swap_without_redeploy():
    """TEST-20: a troca de modelo vale na próxima tarefa, com os mesmos agentes."""
    s = build_system(llm="mock-alucina")
    s.usuario.solicitar("avaliar_orcamento")
    s.bus.run()
    s.modelos.configurar("AG-REL", modelo="mock-narrador")  # em runtime, sem recriar agentes
    sid = s.usuario.solicitar("avaliar_orcamento")
    s.bus.run()
    modelos = [r["modelo"] for r in s.bus.audit.records if r["kind"] == "llm_prompt"]
    assert modelos == ["mock-alucina", "mock-narrador"]
    assert "\nSíntese: " in s.usuario.resposta(sid).content["relatorio"]


def test_llm_not_allowed_roles_rejected():
    """TEST-21: habilitar LLM em AG-ORQ, AG-CUS ou AG-CIN é rejeitado na validação."""
    reg = RegistroModelos(AuditLog(), lambda: 0)
    for agente in ("AG-ORQ", "AG-CUS", "AG-CIN"):
        with pytest.raises(ConfiguracaoInvalida, match="NORM-07"):
            reg.configurar(agente, llm=True)
    with pytest.raises(ConfiguracaoInvalida, match="modelo desconhecido"):
        reg.configurar("AG-REL", modelo="gpt-qualquer")
    assert reg.gerar("AG-CIN", "X", "t", "Receita: 1") is None


def test_token_limit_exceeded_fallback():
    """TEST-22: cota esgotada bloqueia a chamada antes do envio e o relatório usa o template."""
    s = build_system(llm="mock-narrador")
    s.modelos.configurar("AG-REL", cota_tokens=100)
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    assert not [r for r in s.bus.audit.records if r["kind"] == "llm_prompt"]
    assert "cota esgotada" in next(r for r in s.bus.audit.records if r["kind"] == "llm_fallback")["motivo"]
    assert not s.usuario.resposta(sid).content["relatorio"].startswith("Síntese:")


def test_real_provider_unavailable_falls_back_offline():
    """Provedor real sem SDK ou sem rede: falha registrada e template (a suíte nunca acessa a rede)."""
    e = run_scenario("fechar_mes", llm="claude-opus-5-5")
    assert "provedor indisponível" in registros(e, "llm_fallback")[0]["motivo"]
    assert e.resposta.content["status"] == "publicado"


def test_versions_recorded_in_logs():
    """TEST-25: o trace registra versões de pacote, normas, template, rateio, prompt e configuração."""
    e = run_scenario("veto_waiver", llm="mock-narrador")
    meta = registros(e, "meta")[0]
    assert set(meta["versoes"]) >= {"pacote", "normas", "template", "rateio", "prompt"}
    assert meta["llm"]["modelo"] == "mock-narrador" and meta["prazo_aprovacao"] and meta["identidades"]["APR"]
    veto = next(r for r in e.audit.records if r["kind"] == "send" and r["performative"] == "veto")
    assert veto["content"]["versao_normas"] == meta["versoes"]["normas"]
    assert registros(e, "llm_prompt")[0]["versao_prompt"] == meta["versoes"]["prompt"]
    assert e.resposta.content["dag"]  # proveniência do plano executado

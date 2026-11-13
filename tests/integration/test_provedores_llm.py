"""Provedores de LLM pelo caminho real de rede (HTTP em loopback) e pela linha de comando.

Um servidor falso (`tests/fakes/servidor_llm.py`) responde nos formatos da OpenAI, do Gemini
e do Claude. Cada teste roda um cenário completo com o AG-ORC apontado para ele e confere o
que saiu pela rede, o que ficou no trace e o resultado final. Nenhuma chamada sai da máquina.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fakes.servidor_llm import ServidorLLM
from fin_mas.env.scenarios import run_scenario

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
CHAVE = "sk-teste-" + "a1b2c3d4e5f6" * 2


@pytest.fixture
def servidor(monkeypatch):
    criados = []

    def criar(confiavel=True, **kw):
        criados.append(ServidorLLM(**kw))
        if confiavel:  # quem instala fixa as URLs que podem receber a chave do servidor
            url = criados[-1].url
            monkeypatch.setenv("FIN_MAS_LLM_URLS_CONFIAVEIS", ",".join(
                [u for u in os.environ.get("FIN_MAS_LLM_URLS_CONFIAVEIS", "").split(",") if u]
                + [url, url + "/v1", url + "/v1beta"]))
        return criados[-1]
    yield criar
    for s in criados:
        s.fechar()


def reg(e, kind):
    return [r for r in e.audit.records if r["kind"] == kind]


def rodar(provedor, base_url, modelo="modelo-de-teste", **extras):
    return run_scenario("orc_hipotese_llm", llm={"AG-ORC": {"provedor": provedor, "modelo": modelo, "base_url": base_url,
                                                             "usos": ("hipoteses",), **extras}})


def test_openai_compatible_local_server_feeds_a_verified_hypothesis(servidor, monkeypatch):
    monkeypatch.delenv("FIN_MAS_LLM_API_KEY", raising=False)
    s = servidor(modelo_servido="modelo-de-teste-q4")
    e = rodar("openai-compat", s.url + "/v1")
    (pedido,) = s.pedidos
    assert pedido["caminho"] == "/v1/chat/completions" and "authorization" not in pedido["cabecalhos"]
    corpo = pedido["corpo"]
    assert corpo["model"] == "modelo-de-teste" and corpo["max_tokens"] == 2000
    assert corpo["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]
    # servidor em loopback não é provedor externo: sem consentimento e sem pseudônimos
    assert "F-77" in corpo["messages"][1]["content"]
    aceita = next(r for r in reg(e, "hipotese") if r["evento"] == "aceita")
    assert aceita["origem"] == "llm:openai-compat/modelo-de-teste-q4@prompt-hipoteses-v1"
    custo = reg(e, "llm_custo")[0]
    assert (custo["tokens_entrada"], custo["tokens_saida"]) == (321, 45)
    assert custo["modelo_servido"] == "modelo-de-teste-q4"
    assert custo["custo_usd"] is None and "não configurado" in custo["custo_motivo"]
    assert e.resposta.content["hipoteses"][0]["estado"] == "confirmada"
    assert e.resposta.content["resultado"]["sinalizadas"] == []


def test_openai_provider_sends_key_in_header_and_never_in_the_trace(servidor, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", CHAVE)
    s = servidor()
    e = rodar("openai", s.url + "/v1", pseudonimizar=True, preco_entrada=1.0, preco_saida=2.0)
    (pedido,) = s.pedidos
    assert pedido["cabecalhos"]["authorization"] == f"Bearer {CHAVE}"
    assert pedido["corpo"]["max_completion_tokens"] == 4000 and "max_tokens" not in pedido["corpo"]
    usuario = pedido["corpo"]["messages"][1]["content"]
    assert "FORNECEDOR-A" in usuario and "F-77" not in usuario
    assert CHAVE not in json.dumps(e.audit.records, ensure_ascii=False, default=str)
    assert reg(e, "llm_custo")[0]["custo_usd"] == round((321 * 1.0 + 45 * 2.0) / 1_000_000, 6)
    assert "F-77" in e.resposta.content["insights"][0]


def test_gemini_provider_request_and_usage(servidor, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    s = servidor()
    e = rodar("gemini", s.url + "/v1beta", modelo="gemini-de-teste")
    (pedido,) = s.pedidos
    assert pedido["caminho"] == "/v1beta/models/gemini-de-teste:generateContent"
    assert pedido["cabecalhos"]["x-goog-api-key"] == CHAVE
    corpo = pedido["corpo"]
    assert corpo["generationConfig"] == {"maxOutputTokens": 4000, "responseMimeType": "application/json"}
    assert corpo["contents"][0]["role"] == "user" and corpo["systemInstruction"]["parts"][0]["text"]
    custo = reg(e, "llm_custo")[0]
    assert (custo["tokens_entrada"], custo["tokens_saida"]) == (300, 52)  # saída inclui os tokens de raciocínio
    assert [r["evento"] for r in reg(e, "hipotese")] == ["aceita", "em_verificacao", "confirmada"]
    assert CHAVE not in json.dumps(e.audit.records, ensure_ascii=False, default=str)


def test_anthropic_sdk_request_shape_and_served_model(servidor, monkeypatch):
    pytest.importorskip("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", CHAVE)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    s = servidor(modelo_servido="claude-opus-4-8")
    e = rodar("anthropic", s.url, modelo="claude-opus-5-5")
    (pedido,) = s.pedidos
    assert pedido["caminho"].startswith("/v1/messages")
    cabecalhos = pedido["cabecalhos"]  # o SDK escolhe o cabeçalho da credencial conforme a versão da API
    assert CHAVE in (cabecalhos.get("x-api-key"), cabecalhos.get("authorization", "").removeprefix("Bearer "))
    assert "server-side-fallback-2026-07-01" in pedido["cabecalhos"]["anthropic-beta"]
    corpo = pedido["corpo"]
    assert corpo["model"] == "claude-opus-5-5" and corpo["max_tokens"] == 16000 and corpo["fallbacks"] == "default"
    assert corpo["output_config"]["effort"] == "low"
    formato = corpo["output_config"]["format"]
    assert formato["type"] == "json_schema" and formato["schema"]["additionalProperties"] is False
    assert "thinking" not in corpo and "temperature" not in corpo
    custo = reg(e, "llm_custo")[0]
    assert custo["modelo_servido"] == "claude-opus-4-8"  # o fallback do servidor respondeu
    assert custo["custo_usd"] == round((410 * 5.00 + 52 * 25.00) / 1_000_000, 6)  # preço do modelo que serviu
    assert e.resposta.content["hipoteses"][0]["estado"] == "confirmada"
    assert CHAVE not in json.dumps(e.audit.records, ensure_ascii=False, default=str)


@pytest.mark.parametrize("modo, trecho", [
    ("429", "HTTP 429"), ("500", "HTTP 500"), ("nao_json", "não é JSON"), ("fora_do_formato", "fora do formato"),
    ("cortada", "cortada no limite de tokens"), ("recusa", "recusou o pedido"),
])
def test_provider_failures_fall_back_to_the_deterministic_path(servidor, modo, trecho):
    referencia = run_scenario("orc_hipotese_llm", cognicao="local")
    s = servidor(modo=modo)
    e = rodar("openai-compat", s.url + "/v1")
    (fallback,) = reg(e, "llm_fallback")
    assert fallback["motivo"].startswith("provedor indisponível") and trecho in fallback["motivo"]
    assert "sk-vazou" not in fallback["motivo"]  # o corpo de erro do provedor passa pela redação
    assert not reg(e, "hipotese") and not reg(e, "llm_custo")
    assert e.resposta.content["resultado"] == referencia.resposta.content["resultado"]


def test_slow_provider_times_out_without_stopping_the_run(servidor):
    from fin_mas.env.scenarios import CENARIOS, montar
    s = servidor(modo="lento", atraso=1.5)
    sistema, sids = montar(CENARIOS["orc_hipotese_llm"], llm={"AG-ORC": {
        "provedor": "openai-compat", "modelo": "m", "base_url": s.url + "/v1", "usos": ("hipoteses",)}})
    sistema.modelos.tempo_limite = 0.2
    sistema.bus.run()
    fallback = next(r for r in sistema.bus.audit.records if r["kind"] == "llm_fallback")
    assert "sem resposta do provedor" in fallback["motivo"]
    assert sistema.usuario.resposta(sids[0]).performative == "inform"


def test_missing_key_is_reported_without_any_request(servidor, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = servidor()
    e = rodar("openai", s.url + "/v1")
    assert "chave ausente: defina a variável de ambiente OPENAI_API_KEY" in reg(e, "llm_fallback")[0]["motivo"]
    assert not s.pedidos


def _cli(*args, **env):
    return subprocess.run([sys.executable, "-m", "fin_mas", *args], capture_output=True, text=True, cwd=RAIZ,
                          env={**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1", **env})


def test_cli_runs_llm_cognition_against_a_local_server(servidor):
    s = servidor()
    r = _cli("run", "--scenario", "orc_hipotese_llm", "--llm", "openai-compat:modelo-local", "--llm-agentes", "AG-ORC",
             "--llm-usos", "hipoteses", "--llm-base-url", s.url + "/v1")
    assert r.returncode == 0, r.stderr
    assert "LLM AG-ORC chama openai-compat/modelo-local (hipoteses; prompt-hipoteses-v1)" in r.stdout
    assert "HIPOTESE AG-ORC: AG-ORC-H001 causa_controle(C-3002 Marketing) confirmada" in r.stdout
    assert len(s.pedidos) == 1


def test_cli_rejects_llm_on_forbidden_agent_and_unknown_provider():
    r = _cli("run", "--scenario", "fechar_mes", "--llm", "mock:mock-analista", "--llm-agentes", "AG-CIN")
    assert r.returncode == 2 and "NORM-07" in r.stderr
    r = _cli("run", "--scenario", "fechar_mes", "--llm", "inexistente:modelo", "--llm-agentes", "AG-ORC")
    assert r.returncode == 2 and "provedor desconhecido" in r.stderr
    r = _cli("run", "--scenario", "fechar_mes", "--llm", "mock-narrador")  # forma antiga: só a síntese do AG-REL
    assert r.returncode == 0 and "Síntese:" in r.stdout


def test_cli_benchmark_table_with_mock_and_with_a_local_server(servidor):
    """Bancada (`llm avaliar`): mesmos casos, mesma régua, para qualquer provedor."""
    r = _cli("llm", "avaliar")
    assert r.returncode == 0, r.stderr
    assert "bancada de hipóteses: mock/mock-analista" in r.stdout
    assert "acertos: 6 de 6 | resultado igual ao gabarito: 6 de 6 | propostas aceitas: 4 de 4" in r.stdout
    ruim = json.loads(_cli("llm", "avaliar", "--modelo", "mock-analista-ruim", "--json").stdout)
    assert ruim["resumo"]["aceitas"] == 0 and ruim["resumo"]["rejeitadas"] == 30  # tudo barrado pela validação
    assert ruim["resumo"]["acertos"] < 6
    s = servidor()
    http = json.loads(_cli("llm", "avaliar", "--provedor", "openai-compat", "--modelo", "local", "--base-url",
                           s.url + "/v1", "--json").stdout)
    assert http["resumo"]["acertos"] == 6 and len(s.pedidos) == 6
    assert all(x["custo_usd"] is None for x in http["casos"])  # preço de modelo de terceiro é configuração
    fora = _cli("llm", "avaliar", "--provedor", "openai", "--modelo", "qualquer")  # externo, sem consentimento
    assert "NORM-06: sem consentimento" in fora.stdout and "chamadas com fallback: 6" in fora.stdout


def test_cli_lists_providers_without_revealing_keys():
    r = _cli("llm", "provedores", OPENAI_API_KEY=CHAVE)
    assert r.returncode == 0 and CHAVE not in r.stdout
    assert "OPENAI_API_KEY: definida" in r.stdout and "mock" in r.stdout and "(exige --base-url)" in r.stdout


@pytest.mark.parametrize("provedor, variavel, sufixo", [
    ("openai", "OPENAI_API_KEY", "/v1"), ("gemini", "GEMINI_API_KEY", "/v1beta"), ("anthropic", "ANTHROPIC_API_KEY", ""),
    ("openai-compat", "FIN_MAS_LLM_API_KEY", "/v1"),
])
def test_server_api_key_is_never_sent_to_a_url_chosen_in_the_configuration(servidor, monkeypatch, provedor,
                                                                          variavel, sufixo):
    """Correção simulada da v0.5.0 (M1): quem configura o modelo apontava `base_url` para um endereço seu e
    recebia a chave de API do servidor. Fora da URL do provedor e da lista da instalação, a chave não sai."""
    monkeypatch.setenv(variavel, CHAVE)
    s = servidor(confiavel=False)
    e = rodar(provedor, s.url + sufixo)
    assert CHAVE not in json.dumps([dict(p["cabecalhos"]) for p in s.pedidos])
    assert e.resposta.performative == "inform"  # a execução conclui pelo caminho sem LLM (ou sem a chave)
    if provedor != "openai-compat":
        assert not s.pedidos and "chave do servidor não é enviada" in reg(e, "llm_fallback")[0]["motivo"]

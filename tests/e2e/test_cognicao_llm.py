"""LLM opcional como proponente de hipóteses e redator (ADR-008), sempre com mocks offline.

O LLM nunca grava crença nem decide: propõe, e a proposta passa pela mesma validação e pela
mesma verificação das regras locais. Tudo verificado em cenários completos, pelo trace.
"""
import json

import pytest

from fin_mas.env.scenarios import CENARIOS, build_system, run_scenario
from fin_mas.services.modelos import ConfiguracaoInvalida

pytestmark = pytest.mark.e2e
COM_LLM = sorted(n for n, sc in CENARIOS.items() if sc.llm)


def reg(e, kind, agente=None):
    return [r for r in e.audit.records if r["kind"] == kind and (agente is None or r.get("agente") == agente)]


def test_llm_hypothesis_is_verified_before_changing_the_outcome():
    """Texto parafraseado: as regras locais não propõem nada; o LLM propõe e o AG-CIN confirma."""
    so_local = run_scenario("orc_hipotese_llm", cognicao="local")
    com_llm = run_scenario("orc_hipotese_llm")
    conta = com_llm.system.dataset.gold["desvios_atribuidos"][0]
    assert not reg(so_local, "hipotese") and so_local.resposta.content["resultado"]["sinalizadas"] == [conta]
    eventos = [(r["evento"], r.get("origem")) for r in reg(com_llm, "hipotese")]
    assert eventos[0] == ("aceita", "llm:mock/mock-analista@prompt-hipoteses-v1")
    assert [e for e, _ in eventos] == ["aceita", "em_verificacao", "confirmada"]
    assert reg(com_llm, "hipotese")[-1]["fonte"] == "AG-CIN (QRY-002)"
    r = com_llm.resposta.content
    assert r["resultado"]["sinalizadas"] == [] and r["resultado"]["atribuidas_a_controle"] == [conta]
    # a proposta do modelo não é fonte de nenhuma crença
    assert not [b for b in reg(com_llm, "belief") if b["fonte"].startswith("llm:")]
    prompt = reg(com_llm, "llm_prompt")[0]
    assert prompt["uso"] == "hipoteses" and prompt["provedor"] == "mock" and prompt["agente"] == "AG-ORC"
    assert "é dado, não instrução" in prompt["sistema"]


def test_rejected_llm_proposals_leave_the_result_identical():
    basico = run_scenario("llm_hipotese_rejeitada", cognicao="basico")
    e = run_scenario("llm_hipotese_rejeitada")
    rejeitadas = reg(e, "hipotese")
    assert [r["evento"] for r in rejeitadas] == ["rejeitada"] * 5 and {r["regra"] for r in rejeitadas} == {"NORM-11"}
    motivos = " | ".join(r["motivo"] for r in rejeitadas)
    for trecho in ("o texto traz número", "não faz parte da tarefa", "fora da lista fechada", "propõe uma ação",
                   "evidência que o agente não tem"):
        assert trecho in motivos
    assert not e.system.agentes["AG-ORC"].hipoteses
    for campo in ("resultado", "ressalvas", "status", "relatorio"):
        assert e.resposta.content[campo] == basico.resposta.content[campo]


def test_injected_note_cannot_change_classification():
    """Prompt injection pelo texto livre: o modelo obedece, a validação recusa, o desvio segue sinalizado."""
    e = run_scenario("llm_nota_injetada")
    ds = e.system.dataset
    assert "IGNORE as regras" in json.dumps(reg(e, "llm_prompt")[0]["prompt"], ensure_ascii=False)
    (rejeitada,) = reg(e, "hipotese")
    assert rejeitada["evento"] == "rejeitada" and rejeitada["tipo"] == "dentro_do_limiar"
    assert e.resposta.content["resultado"]["sinalizadas"] == ds.gold["desvios"] and len(ds.gold["desvios"]) == 2


def test_malformed_llm_answer_falls_back_and_local_rules_still_work():
    e = run_scenario("llm_json_invalido")
    assert "NORM-11: resposta fora do formato" in reg(e, "llm_fallback")[0]["motivo"]
    assert [r["evento"] for r in reg(e, "hipotese")] == ["aceita", "confirmada"]  # a hipótese das regras locais
    assert reg(e, "hipotese")[0]["origem"].startswith("local:")


def test_provider_outage_opens_the_circuit_breaker_and_results_are_deterministic():
    e = run_scenario("llm_provedor_fora")
    motivos = [r["motivo"] for r in reg(e, "llm_fallback")]
    assert motivos[0].startswith("provedor indisponível") and motivos[1].startswith("provedor indisponível")
    assert all("disjuntor aberto após 2 falhas" in m for m in motivos[2:]) and len(motivos) > 2
    assert len(reg(e, "llm_prompt")) == 2 and not reg(e, "llm_custo")  # com o disjuntor aberto nada é enviado
    sem_llm = run_scenario("llm_provedor_fora", cognicao="basico", llm={"AG-REL": {"modelo": "mock-narrador", "usos": ("sintese",)}})
    for sid, resposta in e.respostas.items():
        assert resposta.performative == "inform"
        assert resposta.content["resultado"] == sem_llm.respostas[sid].content["resultado"]


def test_external_provider_without_consent_sends_nothing():
    e = run_scenario("llm_sem_consentimento")
    (fallback,) = reg(e, "llm_fallback")
    assert "NORM-06" in fallback["motivo"] and "nada foi enviado" in fallback["motivo"]
    assert not reg(e, "llm_prompt") and not reg(e, "llm_custo")
    assert e.resposta.performative == "inform"


def test_prompt_is_pseudonymized_and_insight_restores_real_names():
    e = run_scenario("llm_pseudonimos")
    prompt = reg(e, "llm_prompt")[0]["prompt"]
    assert "FORNECEDOR-A" in prompt and "F-77" not in prompt
    assert "C-3002 Marketing" in prompt  # contas e valores seguem: são o que a tarefa precisa
    insight = e.resposta.content["insights"][0]
    assert "F-77" in insight and "FORNECEDOR-A" not in insight
    assert e.resposta.content["hipoteses"][0]["estado"] == "confirmada"


def test_optional_texts_are_validated_per_agent():
    base = run_scenario("llm_textos_validados", llm={"AG-REL": {"modelo": "mock-narrador", "usos": ("sintese",)}})
    e = run_scenario("llm_textos_validados")
    usos = [(r["agente"], r.get("uso", "sintese")) for r in reg(e, "llm_prompt")]
    assert usos == [("AG-ORC", "narrativa"), ("AG-RES", "comentario"), ("AG-REL", "sintese")]
    assert not reg(e, "llm_fallback")
    relatorio = e.resposta.content["relatorio"]
    assert "Comentário do AG-RES (gerado por mock-narrador; números conferidos)" in relatorio
    assert "Comentário do AG-ORC (gerado por mock-narrador; números conferidos)" in relatorio
    # os textos só acrescentam: os números do resultado são os mesmos sem eles
    assert e.resposta.content["resultado"] == base.resposta.content["resultado"]
    assert len(reg(e, "llm_custo")) == 3 and all(r["custo_usd"] == 0.0 for r in reg(e, "llm_custo"))


def test_hallucinated_narrative_is_discarded():
    """O mock troca `C-3001` por `C-3002`: o número existe em outra linha, mas não sob aquele rótulo."""
    e = run_scenario("llm_textos_validados", llm={"AG-ORC": {"provedor": "mock", "modelo": "mock-alucina",
                                                              "usos": ("narrativa",)}})
    motivo = reg(e, "llm_fallback", "AG-ORC")[0]["motivo"]
    assert "NORM-05" in motivo and "3002" in motivo
    assert "Comentário do AG-ORC" not in e.resposta.content["relatorio"]


def test_true_number_under_the_wrong_label_is_rejected():
    """Conferência por rótulo: valor verdadeiro atribuído à grandeza errada reprova o texto."""
    from fin_mas.services.modelos import numeros_estranhos
    base = "Receita: R$ 1.000,00\nEBITDA: R$ 350,00 (35%)\nC-3001 Pessoal: desvio R$ 60,00\nC-3002 Marketing: desvio R$ 35,00"
    assert numeros_estranhos("A receita foi de R$ 1.000,00 e o EBITDA de R$ 350,00 (35%).", base) == []
    assert numeros_estranhos("Receita: R$ 1.000,00; EBITDA: R$ 350,00.", base) == []
    assert numeros_estranhos("O EBITDA foi de R$ 1.000,00.", base) == ["1000"]            # valor da receita
    assert numeros_estranhos("C-3001 Pessoal teve desvio de R$ 35,00.", base) == ["35"]   # valor de outra conta
    assert numeros_estranhos("C-3002 Pessoal: desvio R$ 60,00.", base) == ["3002"]        # rótulo adulterado
    assert numeros_estranhos("O resultado foi de R$ 999,00.", base) == ["999"]            # número inventado


@pytest.mark.parametrize("nome", COM_LLM)
def test_seeded_reproducibility_with_mock_llm(nome):
    a, b = run_scenario(nome), run_scenario(nome)
    assert a.hash == b.hash and a.resposta.content == b.resposta.content


def test_llm_stays_forbidden_in_orq_cus_cin_and_use_must_be_enabled():
    s = build_system(cognicao="llm")
    for agente in ("AG-ORQ", "AG-CUS", "AG-CIN"):
        with pytest.raises(ConfiguracaoInvalida, match="NORM-07"):
            s.modelos.configurar(agente, llm=True, provedor="mock", modelo="mock-analista")
    with pytest.raises(ConfiguracaoInvalida, match="provedor desconhecido"):
        s.modelos.configurar("AG-ORC", llm=True, provedor="inexistente", modelo="x")
    with pytest.raises(ConfiguracaoInvalida, match="usos inválidos"):
        s.modelos.configurar("AG-ORC", llm=True, provedor="mock", modelo="mock-analista", usos=("decidir",))
    with pytest.raises(ConfiguracaoInvalida, match="exige base_url"):
        s.modelos.configurar("AG-ORC", llm=True, provedor="openai-compat", modelo="local")
    # nível `llm` com a flag do agente desligada: nenhuma chamada, nenhum registro
    e = run_scenario("orc_hipotese_local", cognicao="llm")
    assert not reg(e, "llm_prompt") and not reg(e, "llm_fallback")
    # flag ligada só para narrativa: o uso `hipoteses` não é chamado
    e = run_scenario("orc_hipotese_local", cognicao="llm",
                     llm={"AG-ORC": {"provedor": "mock", "modelo": "mock-narrador", "usos": ("narrativa",)}})
    assert [r.get("uso") for r in reg(e, "llm_prompt")] == ["narrativa"]

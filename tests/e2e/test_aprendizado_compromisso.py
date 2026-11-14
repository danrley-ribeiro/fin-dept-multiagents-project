"""Aprendizado local auditável e estratégias de compromisso (DSM4, ADR-010), em cenários completos.

Aprendizado: cada regra local soma confirmações e refutações de evidência verificada, e a confiança
dela nas competências seguintes vem dessa contagem. Compromisso: cego, obstinado e aberto sobre a
mesma situação, com `aberto` igual ao comportamento de antes.
"""
import pytest

from fin_mas import metricas
from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.services.aprendizado import confianca

pytestmark = pytest.mark.e2e
REGRA = "local:R-OBS-REPETICAO"


def reg(e, kind, agente=None):
    return [r for r in e.audit.records if r["kind"] == kind and (agente is None or r.get("agente") == agente)]


def consultas_ao_cin(e):
    return [c for c in e.system.bus.conversations.values() if c.protocol.id == "PROT-QRY" and c.counterpart == "AG-CIN"]


def verificacao(e, competencia):
    return next(r for r in reg(e, "deliberation", "AG-ORC") if r["desejo"].startswith(f"verificar_hipotese:{competencia}"))


# ---- aprendizado ---------------------------------------------------------------------------------
def test_rule_confidence_follows_refutations_and_changes_what_the_agent_does():
    e = run_scenario("aprendizado_regra")
    observadas = [r for r in reg(e, "aprendizado") if r["evento"] == "observada"]
    # duas refutações, cada uma com a hipótese, a competência e a fonte da evidência (o AG-CIN)
    assert [(r["regra"], r["desfecho"], r["competencia"], r["refutadas"]) for r in observadas] == [
        (REGRA, "refutada", "2026-07", 1), (REGRA, "refutada", "2026-08", 2)]
    assert all(r["fonte"].startswith("AG-CIN (QRY-") and r["norma"] == "NORM-20" for r in observadas)
    # a confiança da proposta em cada mês vem só das competências anteriores: 0,80 -> 0,53 -> 0,40
    aceitas = [r for r in reg(e, "hipotese", "AG-ORC") if r["evento"] == "aceita"]
    assert [r["confianca"] for r in aceitas] == [0.8, 0.53, 0.4]
    assert [confianca(0.8, 0, n) for n in (0, 1, 2)] == [0.8, 0.53, 0.4]  # a conta que qualquer um refaz
    assert "aprendizado" not in aceitas[0] and aceitas[2]["confianca_inicial"] == 0.8
    assert aceitas[2]["aprendizado"] == {"regra": REGRA, "confirmadas": 0, "refutadas": 2, "observacoes": 2, "confianca": 0.4}
    # setembro: AG-CIN sem responder. Regra que errou duas vezes não justifica outra consulta: arquiva
    d = verificacao(e, "2026-09")
    opcoes = {o["plano"]: o for o in d["opcoes"]}
    assert d["escolhido"] == "P-ARQUIVAR-HIPOTESE"
    assert opcoes["P-VERIFICAR-COM-CIN"]["motivo"].startswith("confiança 0.40 da hipótese abaixo de 0.5")
    assert [r["evento"] for r in reg(e, "hipotese", "AG-ORC")][-2:] == ["aceita", "arquivada"]
    # sem aprendizado, a mesma situação custa uma consulta a mais; a classificação é a mesma nos dois casos
    sem = run_scenario("aprendizado_regra", aprendizado=False)
    assert verificacao(sem, "2026-09")["escolhido"] == "P-VERIFICAR-COM-CIN"
    assert len(consultas_ao_cin(sem)) == len(consultas_ao_cin(e)) + 1
    assert not reg(sem, "aprendizado") and [r["confianca"] for r in reg(sem, "hipotese", "AG-ORC") if r["evento"] == "aceita"] == [0.8] * 3
    for sid in e.sids:
        assert e.respostas[sid].content["resultado"] == sem.respostas[sid].content["resultado"]
        assert e.respostas[sid].content["resultado"]["sinalizadas"] == e.system.ambiente.dataset(
            e.respostas[sid].content["competencia"]).gold["desvios"]
    # nível básico: sem hipóteses, sem aprendizado, mesma classificação
    basico = run_scenario("aprendizado_regra", cognicao="basico")
    assert not reg(basico, "aprendizado") and not reg(basico, "hipotese")
    assert [r.content["resultado"]["sinalizadas"] for r in basico.respostas.values()] == [
        r.content["resultado"]["sinalizadas"] for r in e.respostas.values()]


def test_rule_confidence_rises_with_confirmations():
    sc = Scenario("aprendizado_confirma", "a regra acerta dois meses seguidos", "avaliar_orcamento", cognicao="local",
                  agenda=tuple((c, ("desvio_irregular",)) for c in ("2026-07", "2026-08", "2026-09")),
                  pedidos=(("avaliar_orcamento", "2026-07", 1), ("avaliar_orcamento", "2026-08", 50),
                           ("avaliar_orcamento", "2026-09", 100)))
    e = run_scenario(sc)
    aceitas = [r["confianca"] for r in reg(e, "hipotese", "AG-ORC") if r["evento"] == "aceita"]
    assert aceitas == [0.8, 0.87, 0.9] == [confianca(0.8, n, 0) for n in (0, 1, 2)]
    assert [r["confirmadas"] for r in reg(e, "aprendizado") if r["evento"] == "observada"] == [1, 2, 3]
    assert e.system.aprendizado.resumo() == [{"agente": "AG-ORC", "regra": REGRA, "confirmadas": 3, "refutadas": 0}]


def test_only_verified_evidence_counts_for_learning():
    """Hipótese arquivada não soma nada; proposta de LLM não aprende; nenhuma crença nasce do aprendizado."""
    arquivada = run_scenario("hipotese_arquivada")
    assert [r["evento"] for r in reg(arquivada, "hipotese", "AG-ORC")][-1] == "arquivada"
    assert not [r for r in reg(arquivada, "aprendizado") if r["evento"] == "observada"]
    assert arquivada.system.aprendizado.resumo() == []
    llm = run_scenario("orc_hipotese_llm")  # confirmada, mas a origem é o modelo: não entra na contagem
    assert [r["evento"] for r in reg(llm, "hipotese", "AG-ORC")][-1] == "confirmada"
    assert not [r for r in reg(llm, "aprendizado") if r["evento"] == "observada"]
    # o registro recusa observação sem evidência determinística (NORM-20)
    registro = arquivada.system.aprendizado
    h = next(iter(arquivada.system.agentes["AG-ORC"].hipoteses.values()))
    assert registro.observar("AG-ORC", h, "arquivada", None) == []
    assert registro.observar("AG-ORC", h, "confirmada", "llm:mock/mock-analista") == []
    assert registro.observar("AG-ORC", h, "confirmada", None) == []
    recusas = [r for r in reg(arquivada, "aprendizado") if r["evento"] == "recusada"]
    assert len(recusas) == 3 and all(r["motivo"].startswith("NORM-20") for r in recusas)
    assert registro.resumo() == []
    for e in (run_scenario("aprendizado_regra"), arquivada, llm):
        assert not [r for r in reg(e, "belief") if "aprendizado" in str(r["fonte"]).lower()]


def test_results_agent_rules_learn_too():
    e = run_scenario("res_explica_variacao")
    (obs,) = [r for r in reg(e, "aprendizado") if r["evento"] == "observada"]
    assert (obs["agente"], obs["regra"], obs["desfecho"]) == ("AG-RES", "local:R-RES-CUSTO-FIXO", "confirmada")
    assert obs["fonte"] == "cálculo sobre AG-CUS (QRY-003) e mcp://erp/historico_resultado"


# ---- compromisso ----------------------------------------------------------------------------------
def intencoes(e, plano):
    return [r["evento"] for r in reg(e, "intention", "AG-ORC") if r["plano"] == plano]


def test_three_commitment_strategies_differ_on_the_same_situation():
    aberto, obstinado, cego = (run_scenario(f"compromisso_{x}") for x in ("aberto", "obstinado", "cego"))
    conta = aberto.system.dataset.gold["desvios_atribuidos"][0]
    for e, estrategia in ((obstinado, "obstinado"), (cego, "cego")):
        meta = next(r for r in e.audit.records if r["kind"] == "meta")
        assert meta["compromisso"] == {"AG-ORC": estrategia} and e.system.agentes["AG-ORC"].compromisso == estrategia
    assert "compromisso" not in next(r for r in aberto.audit.records if r["kind"] == "meta")
    # 1) o meio falha (consulta perdida): aberto e obstinado replanejam; o cego insiste no mesmo plano
    for e in (aberto, obstinado):
        assert intencoes(e, "P-CONSULTAR-CIN") == ["adotada", "suspensa", "retomada", "falhou", "reconsiderada"]
        assert "concluida" in intencoes(e, "P-SEM-EXPLICACAO")
    assert intencoes(cego, "P-CONSULTAR-CIN") == ["adotada", "suspensa", "retomada", "insistida", "suspensa", "retomada",
                                                  "concluida"]
    assert not intencoes(cego, "P-SEM-EXPLICACAO") and not intencoes(cego, "P-VERIFICAR-COM-CIN")
    # 2) o motivo cai (o AG-CIN contesta o lançamento): só o aberto abandona o alerta
    assert intencoes(aberto, "P-SINALIZAR")[-1] == "abandonada"
    for e in (obstinado, cego):
        eventos = intencoes(e, "P-SINALIZAR")
        assert "mantida" in eventos and eventos[-1] == "concluida" and "abandonada" not in eventos
        mantida = next(r for r in reg(e, "intention", "AG-ORC") if r["evento"] == "mantida")
        assert "o motivo caiu" in mantida["motivo"] and "abaixo do limiar" in mantida["motivo"]
    # resultado contra o gabarito: aberto acerta; os outros dois sinalizam um falso desvio
    assert aberto.resposta.content["resultado"]["sinalizadas"] == aberto.system.dataset.gold["desvios"] == []
    assert aberto.resposta.content["resultado"]["atribuidas_a_controle"] == [conta]
    for e in (obstinado, cego):
        assert e.resposta.content["resultado"]["sinalizadas"] == [conta]
        assert metricas.medir(e)["falsos_desvios"] == 1
    assert metricas.medir(aberto)["falsos_desvios"] == 0
    # os três traces são diferentes entre si e cada um é reprodutível
    assert len({aberto.hash, obstinado.hash, cego.hash}) == 3
    assert cego.hash == run_scenario("compromisso_cego").hash


def test_open_commitment_is_the_default_and_reproduces_previous_behaviour():
    """`aberto` explícito não muda nada: mesmo trace, byte a byte, com e sem o parâmetro."""
    for nome in ("orc_hipotese_local", "desvio_irregular", "veto_correcao"):
        assert run_scenario(nome, compromisso="aberto").hash == run_scenario(nome).hash
        assert run_scenario(nome, compromisso={"AG-ORC": "aberto", "AG-CIN": "aberto"}).hash == run_scenario(nome).hash
    sem_parametro = run_scenario("orc_hipotese_local")
    aberto = run_scenario("compromisso_aberto")
    assert aberto.resposta.content["resultado"] == sem_parametro.resposta.content["resultado"]
    assert [r["evento"] for r in reg(aberto, "intention", "AG-ORC")] == [r["evento"] for r in reg(sem_parametro, "intention", "AG-ORC")]
    # nível básico do mesmo cenário: sem hipótese, a consulta perdida vira falso desvio (o que a cognição evita)
    basico = run_scenario("compromisso_aberto", cognicao="basico")
    assert basico.resposta.content["resultado"]["sinalizadas"] == basico.system.dataset.gold["desvios_atribuidos"]


def test_blind_commitment_stops_insisting_at_the_cap_and_costs_the_deadline():
    """Falha permanente: o cego repete a consulta duas vezes, estoura o prazo da subtarefa e só então replaneja."""
    sc = Scenario("cego_sem_cin", "AG-CIN nunca responde", "avaliar_orcamento", plantar=("desvio_irregular",),
                  cognicao="local", compromisso=(("AG-ORC", "cego"),),
                  faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 9},))
    cego = run_scenario(sc)
    eventos = intencoes(cego, "P-CONSULTAR-CIN")
    assert eventos.count("insistida") == 2 and eventos[-2:] == ["falhou", "reconsiderada"]
    assert "concluida" in intencoes(cego, "P-SEM-EXPLICACAO")
    # o custo do compromisso cego: três consultas de 10 ticks estouram o prazo das duas tentativas do
    # Orquestrador, que aborta com falha explícita (INV-07: há resposta, mas nada é publicado)
    assert cego.resposta.performative == "failure"
    assert (cego.resposta.content["subtarefa"], cego.resposta.content["motivo"]) == ("orcamento", "timeout")
    assert len([c for c in consultas_ao_cin(cego) if c.state == "EXPIRADA"]) >= 3
    # com compromisso aberto a mesma falha permanente termina em avaliação entregue, com ressalva
    aberto = run_scenario(sc, compromisso={"AG-ORC": "aberto"})
    assert aberto.resposta.performative == "inform"
    assert any("AG-CIN indisponível" in x for x in aberto.resposta.content["ressalvas"])


def test_commitment_applies_to_the_new_bdi_specialists():
    """AG-CUS cego relê o mesmo direcionador inconsistente duas vezes antes de trocar de critério."""
    cego = run_scenario("cus_rateio_alternativo", compromisso={"AG-CUS": "cego"})
    eventos = [r["evento"] for r in reg(cego, "intention", "AG-CUS") if r["plano"] == "P-RATEIO-PADRAO"]
    assert eventos == ["adotada", "insistida", "insistida", "falhou", "reconsiderada"]
    leituras = [r for r in cego.audit.records if r["kind"] == "mcp_call" and r["tool"] == "erp.direcionadores"]
    assert len(leituras) == 3
    aberto = run_scenario("cus_rateio_alternativo")
    assert cego.resposta.content["resultado"] == aberto.resposta.content["resultado"]


def test_learning_only_counts_evidence_from_a_deterministic_source():
    """Correção simulada da DSM4 (m2): qualquer texto valia como fonte ("eu acho", " llm:mock" com espaço à frente)."""
    from types import SimpleNamespace

    from fin_mas.services.aprendizado import Aprendizado
    from fin_mas.services.audit import AuditLog

    registro = Aprendizado(AuditLog(), lambda: 0)
    h = SimpleNamespace(id="AG-ORC-H001", cid="DEL-001", tipo="causa_controle", alvo="C-3002", competencia="2026-09",
                        origens=["local:R-OBS-REPETICAO"], confianca=0.8)
    for fonte in ("eu acho", " llm:mock/x", "local:R-OBS-REPETICAO", "", None, "AG-CIN e llm:mock"):
        assert registro.observar("AG-ORC", h, "confirmada", fonte) == [], fonte
    assert registro.observar("AG-ORC", h, "confirmada", "AG-CIN (QRY-002)")

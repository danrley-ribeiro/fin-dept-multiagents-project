"""Variantes BDI de AG-RES, AG-CUS e AG-REL (DSM4, ADR-010), em cenários completos e pelo trace.

Cada teste confere a deliberação (opções aplicáveis e não aplicáveis, plano escolhido), a falha de
plano e o replanejamento quando existem, a fonte das crenças, o resultado contra o gabarito e o
mesmo cenário no nível `basico`, em que os três agentes continuam sendo as classes reativas.
"""
import pytest

from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.cus_bdi import AgenteCustosBDI
from fin_mas.agents.rel import AgenteRelatorios
from fin_mas.agents.rel_bdi import AgenteRelatoriosBDI
from fin_mas.agents.res import AgenteResultados
from fin_mas.agents.res_bdi import AgenteResultadosBDI
from fin_mas.env.scenarios import CENARIOS, Scenario, build_system, run_scenario

pytestmark = pytest.mark.e2e
NOVOS = ("res_explica_variacao", "res_insumo_faltante", "cus_rateio_alternativo", "rel_relatorio_de_excecao",
         "aprendizado_regra", "compromisso_cego", "compromisso_obstinado", "compromisso_aberto",
         "memoria_reincidencia_orc", "normas_sem_evidencia", "normas_fundamentam_achado")
BDI_NOVOS = ("AG-RES", "AG-CUS", "AG-REL")
KINDS_BDI = ("belief", "desire", "deliberation", "intention", "hipotese")


def reg(e, kind, agente):
    return [r for r in e.audit.records if r["kind"] == kind and r.get("agente") == agente]


def deliberacoes(e, agente, desejo):
    return [r for r in reg(e, "deliberation", agente) if r["desejo"].startswith(desejo)]


def opcoes(r) -> dict:
    return {o["plano"]: o for o in r["opcoes"]}


def planos(e, agente, prefixo="P-"):
    return [(r["plano"], r["evento"]) for r in reg(e, "intention", agente) if r["plano"].startswith(prefixo)]


def entrega(e, agente, performativo="inform"):
    """Conteúdo da última resposta do especialista ao Orquestrador (PROT-DEL)."""
    return [r["content"] for r in e.audit.records if r["kind"] == "send" and r["sender"] == agente
            and r["protocol"] == "PROT-DEL" and r["performative"] == performativo][-1]


# ---- todos os cenários novos: catálogo, deliberação real e crença com fonte determinística -----------
@pytest.mark.parametrize("nome", NOVOS)
def test_new_scenarios_deliberate_and_keep_beliefs_with_deterministic_sources(nome):
    sc = CENARIOS[nome]
    assert sc.cognicao in ("local", "llm") and sc.esperado
    e = run_scenario(nome)
    assert all(r is not None for r in e.respostas.values())
    assert isinstance(e.system.agentes["AG-RES"], AgenteResultadosBDI)
    # em toda execução cognitiva há deliberação em que um plano é aplicável e outro não, com o motivo de cada um
    mistas = [r for r in e.audit.records if r["kind"] == "deliberation"
              and any(o["aplicavel"] for o in r["opcoes"]) and any(not o["aplicavel"] for o in r["opcoes"])]
    assert mistas and all(o["motivo"] for r in mistas for o in r["opcoes"])
    assert all(r["escolhido"] in opcoes(r) and opcoes(r)[r["escolhido"]]["aplicavel"] for r in mistas)
    # nenhuma crença, de nenhum agente, tem regra local ou LLM como fonte (INV-05); toda crença tem fonte
    crencas = [r for r in e.audit.records if r["kind"] == "belief"]
    assert crencas and all(r["fonte"] and not r["fonte"].startswith(("local:", "llm:")) for r in crencas)
    for r in crencas:
        if r["agente"] in BDI_NOVOS:
            assert r["fonte"].startswith(("mcp://", "cálculo sobre ", "plano P-", "AG-", "SVC-A2A (timeout", "SVC-MEM ",
                                          "pedido do AG-ORQ"))


@pytest.mark.parametrize("nome", NOVOS)
def test_basic_level_runs_the_same_scenario_with_the_reactive_specialists(nome):
    """O braço `basico` do experimento: classes reativas, sem nenhum registro BDI de RES, CUS e REL."""
    e = run_scenario(nome, cognicao="basico")
    ag = e.system.agentes
    assert (type(ag["AG-RES"]), type(ag["AG-CUS"]), type(ag["AG-REL"])) == (AgenteResultados, AgenteCustos, AgenteRelatorios)
    assert not [r for r in e.audit.records if r["kind"] in KINDS_BDI and r.get("agente") in BDI_NOVOS]
    assert not [r for r in e.audit.records if r["kind"] in ("aprendizado",)]
    assert all(r is not None for r in e.respostas.values())


def test_build_system_picks_the_variant_by_cognition_level():
    for nivel, classes in (("basico", (AgenteResultados, AgenteCustos, AgenteRelatorios)),
                           ("local", (AgenteResultadosBDI, AgenteCustosBDI, AgenteRelatoriosBDI)),
                           ("llm", (AgenteResultadosBDI, AgenteCustosBDI, AgenteRelatoriosBDI))):
        ag = build_system(cognicao=nivel).agentes
        assert (type(ag["AG-RES"]), type(ag["AG-CUS"]), type(ag["AG-REL"])) == classes
    with pytest.raises(ValueError, match="compromisso"):
        build_system(cognicao="local", compromisso="teimoso")


# ---- AG-RES ------------------------------------------------------------------------------------
def test_results_agent_explains_a_relevant_variation_with_verified_evidence():
    e = run_scenario("res_explica_variacao")
    gold = e.system.dataset.gold["variacao"]
    # a variação relevante é uma crença calculada, não um palpite
    variacao = next(r for r in reg(e, "belief", "AG-RES") if r["chave"].startswith("variacao["))
    assert variacao["depois"]["relevante"] and variacao["depois"]["delta_pp"] <= -3
    assert variacao["fonte"] == "cálculo sobre AG-CUS (QRY-001) e mcp://erp/historico_resultado"
    # regra local propõe; a hipótese é validada (NORM-11) e vira o desejo de explicar
    eventos = [(r["evento"], r.get("tipo")) for r in reg(e, "hipotese", "AG-RES")]
    assert eventos == [("aceita", "causa_custo_fixo"), ("em_verificacao", "causa_custo_fixo"),
                       ("confirmada", "causa_custo_fixo")]
    assert reg(e, "hipotese", "AG-RES")[0]["origem"] == "local:R-RES-CUSTO-FIXO"
    (d,) = deliberacoes(e, "AG-RES", "explicar_variacao")
    assert d["escolhido"] == "P-DETALHAR-COM-CUSTOS"
    assert {p: o["aplicavel"] for p, o in opcoes(d).items()} == {"P-DETALHAR-COM-CUSTOS": True,
                                                                 "P-CONFERIR-NO-HISTORICO": True,
                                                                 "P-ARQUIVAR-HIPOTESE": True}
    assert opcoes(d)["P-DETALHAR-COM-CUSTOS"]["utilidade"] > opcoes(d)["P-CONFERIR-NO-HISTORICO"]["utilidade"]
    # a consulta de detalhe é decisão do AG-RES, direto ao AG-CUS (PROT-QRY), e é dela que vem a explicação
    detalhe = [c for c in e.system.bus.conversations.values() if c.protocol.id == "PROT-QRY" and c.initiator == "AG-RES"]
    assert [(c.counterpart, c.state) for c in detalhe] == [("AG-CUS", "RESPONDIDA"), ("AG-ORC", "RESPONDIDA"),
                                                           ("AG-CUS", "RESPONDIDA")]
    explicacao = next(r for r in reg(e, "belief", "AG-RES") if r["chave"].startswith("explicacao["))
    assert explicacao["fonte"] == "cálculo sobre AG-CUS (QRY-003) e mcp://erp/historico_resultado"
    assert (explicacao["depois"]["linha"], explicacao["depois"]["centro"]) == (gold["linha"], gold["centro"])
    assert abs(explicacao["depois"]["aumento_do_centro"] - gold["aumento"]) * 100 < gold["aumento"] * 2  # histórico oscila 1%
    assert reg(e, "hipotese", "AG-RES")[-1]["fonte"] == explicacao["fonte"]
    # resultado igual ao gabarito, com a explicação no relatório, em frase do agente
    r = e.resposta.content
    assert r["resultado"]["dre"] == e.system.dataset.gold["dre"]
    assert entrega(e, "AG-RES")["explicacoes"][0]["centro"] == "CC-OPS"
    assert "Insight: ebitda_pct: hipótese AG-RES-H001" in r["relatorio"] and "maior aumento em CC-OPS" in r["relatorio"]
    # nível básico: mesma DRE, nenhuma explicação
    basico = run_scenario("res_explica_variacao", cognicao="basico")
    assert basico.resposta.content["resultado"]["dre"] == r["resultado"]["dre"]
    assert "Insight" not in basico.resposta.content["relatorio"] and "explicacoes" not in entrega(basico, "AG-RES")


def test_variation_hypothesis_falls_back_to_history_when_the_cost_agent_goes_offline():
    """Plano que depende de outro agente falha (AG-CUS desligado com a consulta de detalhe a caminho) e o AG-RES replaneja."""
    sistema = build_system(plantar=("variacao_custo_fixo",), cognicao="local")
    sid = sistema.usuario.solicitar("fechar_mes")
    audit = sistema.bus.audit
    while not any(r["kind"] == "hipotese" and r.get("agente") == "AG-RES" and r["evento"] == "em_verificacao"
                  for r in audit.records):
        assert sistema.bus.step()
    sistema.bus.set_online("AG-CUS", False)  # o operador desliga o AG-CUS (mesmo comando do dashboard)
    sistema.bus.run()
    eventos = [(r["plano"], r["evento"]) for r in audit.records if r["kind"] == "intention" and r.get("agente") == "AG-RES"
               and r["plano"] in ("P-DETALHAR-COM-CUSTOS", "P-CONFERIR-NO-HISTORICO")]
    assert ("P-DETALHAR-COM-CUSTOS", "falhou") in eventos and ("P-CONFERIR-NO-HISTORICO", "concluida") in eventos
    replanejada = [r for r in audit.records if r["kind"] == "deliberation" and r.get("agente") == "AG-RES"
                   and r["desejo"].startswith("explicar_variacao")][-1]
    assert replanejada["escolhido"] == "P-CONFERIR-NO-HISTORICO"
    assert opcoes(replanejada)["P-DETALHAR-COM-CUSTOS"]["motivo"] == "já tentado sem sucesso"
    explicacao = next(r for r in audit.records if r["kind"] == "belief" and r["chave"].startswith("explicacao["))
    assert explicacao["depois"]["linha"] == "custos_fixos" and "centro" not in explicacao["depois"]  # menos preciso
    assert explicacao["fonte"] == "cálculo sobre cálculo sobre AG-CUS (QRY-001) e mcp://erp/historico_resultado"
    assert sistema.usuario.resposta(sid).performative == "inform"


def test_results_agent_replans_when_a_specialist_is_silent_and_decides_by_size_and_criticality():
    e = run_scenario("res_insumo_faltante")
    # falha de plano e replanejamento observáveis: consulta, consulta de novo, dá por indisponível
    assert [p for p in planos(e, "AG-RES") if p[1] in ("falhou", "concluida") and "orcamento" not in p[0]
            and p[0] in ("P-CONSULTAR-ESPECIALISTA", "P-CONSULTAR-DE-NOVO", "P-DAR-POR-INDISPONIVEL")] == [
        ("P-CONSULTAR-ESPECIALISTA", "concluida"),  # custos chegaram
        ("P-CONSULTAR-ESPECIALISTA", "falhou"), ("P-CONSULTAR-DE-NOVO", "falhou"), ("P-DAR-POR-INDISPONIVEL", "concluida")]
    ds = deliberacoes(e, "AG-RES", "obter_insumo:orcamento")
    assert [d["escolhido"] for d in ds] == ["P-CONSULTAR-ESPECIALISTA", "P-CONSULTAR-DE-NOVO", "P-DAR-POR-INDISPONIVEL"]
    assert opcoes(ds[0])["P-CONSULTAR-DE-NOVO"]["motivo"] == "nenhuma consulta expirou sem resposta"
    assert opcoes(ds[1])["P-CONSULTAR-ESPECIALISTA"]["motivo"] == "já tentado sem sucesso"
    assert opcoes(ds[1])["P-CONSULTAR-DE-NOVO"]["motivo"] == "a consulta expirou e outra cabe no prazo"
    assert not opcoes(ds[2])["P-CONSULTAR-DE-NOVO"]["aplicavel"] and opcoes(ds[2])["P-DAR-POR-INDISPONIVEL"]["aplicavel"]
    # a crença sobre o insumo é revisada pelo timeout do barramento, não por suposição
    crencas = [(r["depois"]["estado"], r["fonte"]) for r in reg(e, "belief", "AG-RES") if r["chave"].startswith("insumo[orcamento]")]
    assert crencas == [("aguardando", "plano P-CONSULTAR-ESPECIALISTA"), ("sem_resposta", "SVC-A2A (timeout de QRY-002)"),
                       ("aguardando", "plano P-CONSULTAR-DE-NOVO"), ("sem_resposta", "SVC-A2A (timeout de QRY-003)"),
                       ("indisponivel", "plano P-DAR-POR-INDISPONIVEL")]
    # média empresa: o orçamento não é crítico para a DRE e a tempestividade pesa mais -> consolida com ressalva
    (d,) = deliberacoes(e, "AG-RES", "consolidar")
    assert d["escolhido"] == "P-CONSOLIDAR-COM-RESSALVA"
    assert not opcoes(d)["P-CONSOLIDAR-COMPLETO"]["aplicavel"] and opcoes(d)["P-FALHAR-EXPLICITAMENTE"]["aplicavel"]
    r = e.resposta.content
    assert r["status"] == "publicado_com_ressalva" and r["resultado"]["dre"] == e.system.dataset.gold["dre"]
    assert r["resultado"]["kpis"]["desvio_orcamentario"] is None
    assert any("KPI de desvio orçamentário indisponível" in x for x in r["ressalvas"])
    assert r["dag"]["resultados"]["tentativas"] == 1  # o Orquestrador não precisou reenviar
    # nível básico: o AG-RES reativo devolve failure na primeira consulta perdida; o Orquestrador reenvia a
    # subtarefa inteira, a segunda consulta também se perde e o fechamento é abortado, sem publicar nada
    basico = run_scenario("res_insumo_faltante", cognicao="basico")
    assert basico.resposta.performative == "failure" and basico.resposta.content["publicado"] is False
    assert basico.resposta.content["subtarefa"] == "resultados"
    assert entrega(basico, "AG-RES", "failure")["motivo"].startswith("insumo indisponível (orcamento)")
    assert len([r for r in basico.audit.records if r["kind"] == "link" and r.get("subtarefa") == "resultados"]) == 2
    # grande empresa (auditada): a completude pesa mais -> falha explícita em vez de indicador incompleto
    grande = run_scenario("res_insumo_faltante", porte="grande")
    d = deliberacoes(grande, "AG-RES", "consolidar")[0]
    assert d["escolhido"] == "P-FALHAR-EXPLICITAMENTE" and opcoes(d)["P-CONSOLIDAR-COM-RESSALVA"]["aplicavel"]
    assert opcoes(d)["P-FALHAR-EXPLICITAMENTE"]["utilidade"] > opcoes(d)["P-CONSOLIDAR-COM-RESSALVA"]["utilidade"]
    assert entrega(grande, "AG-RES", "failure")["motivo"] == "insumo indisponível (orcamento): AG-ORC não respondeu a 2 consulta(s)"
    assert grande.resposta.content["dag"]["resultados"]["tentativas"] == 2 and grande.resposta.content["status"] == "publicado"


def test_missing_critical_input_never_becomes_a_partial_result():
    """Sem custos não há DRE: em qualquer porte só resta a falha explícita (criticidade do insumo)."""
    sc = Scenario("res_sem_custos", "AG-CUS não responde ao AG-RES", "fechar_mes", cognicao="local",
                  faults=({"receiver": "AG-CUS", "performative": "query-ref", "times": 9},))
    for porte in ("media", "micro"):
        e = run_scenario(sc, porte=porte)
        d = deliberacoes(e, "AG-RES", "consolidar")[0]
        assert d["escolhido"] == "P-FALHAR-EXPLICITAMENTE"
        assert opcoes(d)["P-CONSOLIDAR-COM-RESSALVA"]["motivo"] == "custos é insumo crítico: sem ele não há DRE"
        assert e.resposta.performative == "failure" and e.resposta.content["publicado"] is False


# ---- AG-CUS ------------------------------------------------------------------------------------
def test_cost_agent_picks_an_allocation_criterion_when_the_driver_is_unusable():
    e = run_scenario("cus_rateio_alternativo")
    ds = e.system.dataset
    assert ds.gold["rateio"]["direcionador"] == "inconsistente"
    d1, d2 = deliberacoes(e, "AG-CUS", "definir_rateio")
    # primeira deliberação: o padrão vence, com alternativas aplicáveis e uma não aplicável
    assert d1["escolhido"] == "P-RATEIO-PADRAO"
    assert {p: o["aplicavel"] for p, o in opcoes(d1).items()} == {
        "P-RATEIO-PADRAO": True, "P-RATEIO-ULTIMO-VALIDO": False, "P-RATEIO-PROPORCIONAL-RECEITA": True,
        "P-RATEIO-IGUALITARIO": True}
    # o plano falha ao perceber o dado: a crença é revisada com a fonte e o agente replaneja
    direcionador = next(r for r in reg(e, "belief", "AG-CUS") if r["chave"].startswith("direcionador@"))
    assert direcionador["fonte"] == "mcp://erp/direcionadores" and direcionador["depois"]["estado"] == "inconsistente"
    assert planos(e, "AG-CUS", "P-RATEIO") == [
        ("P-RATEIO-PADRAO", "adotada"), ("P-RATEIO-PADRAO", "falhou"), ("P-RATEIO-PADRAO", "reconsiderada"),
        ("P-RATEIO-PROPORCIONAL-RECEITA", "adotada"), ("P-RATEIO-PROPORCIONAL-RECEITA", "concluida")]
    assert d2["escolhido"] == "P-RATEIO-PROPORCIONAL-RECEITA"
    assert opcoes(d2)["P-RATEIO-PADRAO"]["motivo"] == "já tentado sem sucesso"
    assert "a versão anterior deixou de valer" in opcoes(d2)["P-RATEIO-ULTIMO-VALIDO"]["motivo"]
    assert opcoes(d2)["P-RATEIO-PROPORCIONAL-RECEITA"]["utilidade"] > opcoes(d2)["P-RATEIO-IGUALITARIO"]["utilidade"]
    # critério e motivo registrados; conta igual ao gabarito do critério escolhido; DRE não muda
    custos = entrega(e, "AG-CUS")
    assert custos["proveniencia"]["criterio_rateio"] == "proporcional_receita"
    assert "somam 110" in custos["proveniencia"]["motivo_criterio"]
    assert custos["resultado_un"] == ds.gold["rateio"]["por_criterio"]["proporcional_receita"]
    assert custos["margens_produto"] == ds.gold["margens_produto"]
    assert sum(u["custo_fixo_rateado"] for u in custos["resultado_un"].values()) == ds.gold["dre"]["custos_fixos"]
    decisao = next(r for r in reg(e, "decision", "AG-CUS") if r["regra"].startswith("critério de rateio"))
    assert decisao["resultado"] == "proporcional_receita" and decisao["entradas"]["porte"] == "media"
    r = e.resposta.content
    assert r["resultado"]["dre"] == ds.gold["dre"] and r["status"] == "publicado_com_ressalva"
    assert any(x.startswith("rateio dos custos fixos pelo critério proporcional à receita") for x in r["ressalvas"])
    # nível básico: o agente reativo aplica o rateio fixo sem olhar o direcionador e sem avisar ninguém
    basico = run_scenario("cus_rateio_alternativo", cognicao="basico")
    assert entrega(basico, "AG-CUS")["resultado_un"] == ds.gold["rateio"]["por_criterio"]["padrao"]
    assert basico.resposta.content["status"] == "publicado" and basico.resposta.content["ressalvas"] == []
    assert not [x for x in basico.audit.records if x["kind"] == "mcp_call" and x["tool"] == "erp.direcionadores"]


def test_cost_criterion_depends_on_company_size_and_on_what_is_wrong_with_the_driver():
    # microempresa pesa simplicidade: com a mesma tabela inconsistente, divide em partes iguais
    micro = run_scenario("cus_rateio_alternativo", porte="micro")
    d = deliberacoes(micro, "AG-CUS", "definir_rateio")[-1]
    assert d["escolhido"] == "P-RATEIO-IGUALITARIO" and opcoes(d)["P-RATEIO-PROPORCIONAL-RECEITA"]["aplicavel"]
    assert entrega(micro, "AG-CUS")["resultado_un"] == micro.system.dataset.gold["rateio"]["por_criterio"]["igualitario"]
    # tabela não publicada (em vez de alterada): vale a última aprovada, em qualquer porte
    ausente = Scenario("cus_direcionador_ausente", "tabela do período não publicada", "fechar_mes",
                       plantar=("direcionador_ausente",), cognicao="local")
    e = run_scenario(ausente)
    d = deliberacoes(e, "AG-CUS", "definir_rateio")[-1]
    assert d["escolhido"] == "P-RATEIO-ULTIMO-VALIDO"
    assert entrega(e, "AG-CUS")["proveniencia"]["criterio_rateio"] == "ultimo_valido"
    assert entrega(e, "AG-CUS")["resultado_un"] == e.system.dataset.gold["resultado_un"]
    assert any("última tabela aprovada" in x for x in e.resposta.content["ressalvas"])
    # sem problema no direcionador: critério padrão, nenhum replanejamento, mesmos números do agente reativo
    normal = run_scenario("fechar_mes", cognicao="local")
    assert planos(normal, "AG-CUS", "P-RATEIO") == [("P-RATEIO-PADRAO", "adotada"), ("P-RATEIO-PADRAO", "concluida")]
    assert entrega(normal, "AG-CUS")["resultado_un"] == entrega(run_scenario("fechar_mes"), "AG-CUS")["resultado_un"]
    assert normal.resposta.content["ressalvas"] == []


# ---- AG-REL ------------------------------------------------------------------------------------
def test_report_agent_chooses_structure_by_findings_and_audience():
    e = run_scenario("rel_relatorio_de_excecao")
    (d,) = deliberacoes(e, "AG-REL", "comunicar")
    assert d["escolhido"] == "P-RELATORIO-DE-EXCECAO"
    assert {p: o["aplicavel"] for p, o in opcoes(d).items()} == {"P-RELATORIO-DE-EXCECAO": True, "P-SUMARIO-EXECUTIVO": False,
                                                                 "P-RELATORIO-COMPLETO": True}
    achados = next(r for r in reg(e, "belief", "AG-REL") if r["chave"].startswith("achados@"))
    assert achados["fonte"].startswith("pedido do AG-ORQ") and achados["depois"]["correcoes"] == 1
    assert next(r for r in reg(e, "belief", "AG-REL") if r["chave"] == "publico")["fonte"] == "mcp://normas/cognicao"
    linhas = e.resposta.content["relatorio"].splitlines()
    assert linhas[1].startswith("Relatório executivo de exceção") and linhas[2] == "Destinatário: diretoria"
    # a exceção vem antes dos indicadores, com a base normativa citada
    nota = next(i for i, x in enumerate(linhas) if x.startswith("Nota: correção aprovada"))
    assert nota < linhas.index("Indicadores do período:") < next(i for i, x in enumerate(linhas) if x.startswith("Receita:"))
    assert any(x.startswith("Base normativa (aprovação por alçada):") and "COSO-ALCADA" in x and "corpus-v1" in x for x in linhas)
    assert entrega(e, "AG-REL")["estrutura"] == "excecao" and entrega(e, "AG-REL")["modo"] == "template"
    # nível básico: mesmo conteúdo no template de sempre, com a correção no fim
    basico = run_scenario("rel_relatorio_de_excecao", cognicao="basico").resposta.content["relatorio"].splitlines()
    assert basico[1].startswith("Relatório executivo —") and basico[-1].startswith("Nota: correção aprovada")
    for linha in basico:  # nada do template se perde no relatório de exceção
        assert linha in linhas or linha == basico[1]
    # tudo conforme: sumário para a diretoria; relatório completo para conselho e auditoria (grande empresa)
    conforme = run_scenario("fechar_mes", cognicao="local")
    (d,) = deliberacoes(conforme, "AG-REL", "comunicar")
    assert d["escolhido"] == "P-SUMARIO-EXECUTIVO" and not opcoes(d)["P-RELATORIO-DE-EXCECAO"]["aplicavel"]
    sumario = conforme.resposta.content["relatorio"].splitlines()
    assert sumario[1].startswith("Sumário executivo") and sumario[-1].startswith("Sem exceções")
    assert not [x for x in sumario if x.startswith(("Margem", "Custos fixos", "Resultado UN"))]
    grande = run_scenario("fechar_mes", cognicao="local", porte="grande")
    (d,) = deliberacoes(grande, "AG-REL", "comunicar")
    assert d["escolhido"] == "P-RELATORIO-COMPLETO" and opcoes(d)["P-SUMARIO-EXECUTIVO"]["aplicavel"]
    assert grande.resposta.content["relatorio"] == run_scenario("fechar_mes", porte="grande").resposta.content["relatorio"]


def test_exception_report_orders_caveats_and_keeps_only_verified_insights():
    """Waiver e hipótese arquivada no mesmo fechamento: destaque das ressalvas e seleção de insights."""
    sc = Scenario("excecao_com_insights", "SoD com waiver e consultas ao AG-CIN perdidas", "fechar_mes", cognicao="local",
                  plantar=("sod", "desvio_irregular", "divergencia_fonte"), decisao_aprovador="waiver",
                  faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 3},))
    e = run_scenario(sc)
    assert deliberacoes(e, "AG-REL", "comunicar")[0]["escolhido"] == "P-RELATORIO-DE-EXCECAO"
    linhas = e.resposta.content["relatorio"].splitlines()
    ressalvas = [x for x in linhas if x.startswith("Ressalva: ")]
    assert ressalvas[0].startswith("Ressalva: waiver de ")  # o que o humano liberou vem primeiro
    assert [x for x in ressalvas if "divergência em" in x] and ressalvas.index(next(x for x in ressalvas if "divergência em" in x)) > 0
    # hipótese arquivada (sem evidência) não é reproduzida no relatório de exceção: só a contagem
    assert next(iter(e.system.agentes["AG-ORC"].hipoteses.values())).estado == "arquivada"
    assert not [x for x in linhas if x.startswith("Insight: ")]
    assert "1 hipótese(s) sem evidência não reproduzida(s) neste relatório de exceção." in linhas
    assert any(x.startswith("Base normativa (segregação de funções):") and "COSO-SEGREGACAO" in x for x in linhas)
    # para conselho e auditoria (completude) o mesmo relatório traz todos os insights e o texto do trecho
    grande = run_scenario(sc, porte="grande")
    if deliberacoes(grande, "AG-REL", "comunicar")[0]["escolhido"] == "P-RELATORIO-DE-EXCECAO":
        texto = grande.resposta.content["relatorio"]
        assert "sem evidência não reproduzida" not in texto


def test_model_text_goes_to_the_end_of_the_report_labelled_and_never_inside_template_sentences():
    """LLM opcional (mocks) com as variantes BDI: o texto do modelo é rotulado e fica depois do template."""
    llm = {"AG-RES": {"provedor": "mock", "modelo": "mock-narrador", "usos": ("comentario",)},
           "AG-REL": {"provedor": "mock", "modelo": "mock-narrador", "usos": ("sintese",)}}
    e = run_scenario("rel_relatorio_de_excecao", cognicao="llm", llm=llm)
    texto = e.resposta.content["relatorio"]
    corpo, _, rodape = texto.partition("\n\n")
    assert "Texto de modelo" not in corpo and corpo == run_scenario("rel_relatorio_de_excecao").resposta.content["relatorio"]
    rotulos = [x for x in rodape.splitlines() if x.startswith("Texto de modelo (")]
    assert len(rotulos) == 2 and all("só os números foram conferidos" in x for x in rotulos)
    assert entrega(e, "AG-REL")["modo"] == "template+llm"
    assert not [r for r in e.audit.records if r["kind"] == "belief" and r["fonte"].startswith("llm:")]
    with pytest.raises(Exception, match="NORM-07"):  # AG-CUS segue sem LLM
        run_scenario("cus_rateio_alternativo", cognicao="llm", llm={"AG-CUS": {"provedor": "mock", "modelo": "mock-narrador"}})

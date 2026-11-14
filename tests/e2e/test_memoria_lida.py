"""Memória aprovada lida por AG-ORC, AG-RES e AG-REL (DSM4, ADR-010), com controle de acesso por tipo.

A memória continua só com decisões humanas (NORM-08) e só o AG-CIN grava. O que mudou é quem lê:
correção aprovada é legível pelos três; waiver e bloqueio seguem só com o AG-CIN.
"""
import pytest

from fin_mas.env.scenarios import Scenario, build_system, run_scenario
from fin_mas.services.memoria import ACESSO

pytestmark = pytest.mark.e2e


def reg(e, kind, agente=None):
    return [r for r in e.audit.records if r["kind"] == kind and (agente is None or r.get("agente") == agente)]


def test_budget_agent_reads_approved_memory_and_avoids_a_false_deviation():
    e = run_scenario("memoria_reincidencia_orc")
    agosto, setembro = e.respostas.values()
    conta = e.system.ambiente.dataset("2026-09").gold["desvios_atribuidos"][0]
    # agosto: o estorno aprovado vira memória, com a conta (o valor não vai para o trace)
    gravada = next(r for r in reg(e, "memoria") if r["evento"] == "gravada")
    assert (gravada["tipo"], gravada["competencia"], gravada["agente"]) == ("correcao", "2026-08", "AG-CIN")
    (entrada,) = e.system.memoria.entradas
    assert entrada["valor"]["conta"] == conta and entrada["valor"]["regras"] == ["duplicidade"]
    assert entrada["proveniencia"]["aprovacao"] == "APR-001" and entrada["proveniencia"]["decisao"] == "corrigir"
    # setembro: a planilha não fala em duplicidade (regra da observação calada) e a consulta ao AG-CIN se perde
    consulta = next(r for r in reg(e, "memoria") if r["evento"] == "consultada" and r["agente"] == "AG-ORC")
    assert consulta["tipo"] == "correcao" and consulta["memorias"] == [entrada["id"]]
    crenca = next(r for r in reg(e, "belief", "AG-ORC") if r["chave"].startswith("reincidencia["))
    assert crenca["fonte"] == f"SVC-MEM {entrada['id']}" and crenca["depois"]["competencia"] == "2026-08"
    hipoteses = [r for r in reg(e, "hipotese", "AG-ORC") if r["conversation_id"] == crenca["conversation_id"]]
    assert [(r["evento"], r.get("origem")) for r in hipoteses][0] == ("aceita", "local:R-MEM-REINCIDENCIA")
    assert crenca["chave"] in hipoteses[0]["evidencias"]
    assert [r["evento"] for r in hipoteses] == ["aceita", "em_verificacao", "confirmada"]
    assert hipoteses[-1]["fonte"].startswith("AG-CIN (QRY-")  # quem confirma é o AG-CIN, não a memória
    assert not [r for r in reg(e, "belief", "AG-ORC") if r["chave"].startswith("classificacao[") and "SVC-MEM" in r["fonte"]]
    r = setembro.content["resultado"]
    assert r["sinalizadas"] == [] and r["atribuidas_a_controle"] == [conta]
    assert f"Insight: {conta}: hipótese" in setembro.content["relatorio"] and entrada["id"] in setembro.content["relatorio"]
    assert agosto.performative == "inform"
    # nível básico: ninguém lê a memória em setembro e o desvio é sinalizado como orçamentário (falso desvio)
    basico = run_scenario("memoria_reincidencia_orc", cognicao="basico")
    assert not [x for x in reg(basico, "memoria") if x.get("agente") == "AG-ORC"]
    assert list(basico.respostas.values())[1].content["resultado"]["sinalizadas"] == [conta]
    # nível local sem a memória (correção de outro tipo de problema não conta): mesmo falso desvio
    so_alcada = Scenario("memoria_outra_regra", "correção de alçada em agosto", "fechar_mes", cognicao="local",
                         decisao_aprovador="corrigir",
                         agenda=(("2026-08", ("alcada",)), ("2026-09", ("desvio_irregular", "observacao_parafraseada"))),
                         pedidos=(("fechar_mes", "2026-08", 1), ("avaliar_orcamento", "2026-09", 100)),
                         faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1, "competencia": "2026-09"},))
    outro = run_scenario(so_alcada)
    assert not [x for x in reg(outro, "belief", "AG-ORC") if x["chave"].startswith("reincidencia[")]
    assert list(outro.respostas.values())[1].content["resultado"]["sinalizadas"] == [conta]


def test_memory_corroboration_raises_the_confidence_of_an_existing_hypothesis():
    """Observação da planilha e memória apontam a mesma causa: a hipótese é corroborada e a confiança sobe."""
    sc = Scenario("memoria_corrobora", "duas origens para a mesma hipótese", "fechar_mes", cognicao="local",
                  decisao_aprovador="corrigir",
                  agenda=(("2026-08", ("desvio_irregular",)), ("2026-09", ("desvio_irregular",))),
                  pedidos=(("fechar_mes", "2026-08", 1), ("avaliar_orcamento", "2026-09", 100)))
    e = run_scenario(sc)
    setembro = [r for r in reg(e, "hipotese", "AG-ORC") if r["conversation_id"] != reg(e, "hipotese", "AG-ORC")[0]["conversation_id"]]
    aceita, corroborada = setembro[0], setembro[1]
    assert (aceita["evento"], aceita["origem"]) == ("aceita", "local:R-OBS-REPETICAO")
    assert (corroborada["evento"], corroborada["origem"]) == ("corroborada", "local:R-MEM-REINCIDENCIA")
    assert corroborada["confianca"] > aceita["confianca"] > 0.8  # 0,87 aprendida em agosto; mais alta com a memória
    assert setembro[-1]["evento"] == "confirmada"


def test_memory_read_access_is_by_type_and_denials_are_audited():
    assert ACESSO["correcao"][1] == {"AG-CIN", "AG-ORC", "AG-RES", "AG-REL"}
    assert ACESSO["waiver"][1] == ACESSO["bloqueio"][1] == {"AG-CIN"} and all(g == {"AG-CIN"} for g, _ in ACESSO.values())
    # agosto: waiver; setembro: correção. O AG-ORC enxerga a correção e não o waiver
    e = run_scenario("reincidencia_waiver", cognicao="local")
    orc, rel, cin = (e.system.agentes[a].memoria for a in ("AG-ORC", "AG-REL", "AG-CIN"))
    tipos = sorted(m["tipo"] for m in e.system.memoria.entradas)
    assert tipos == ["correcao", "waiver"]
    antes = len(reg(e, "memoria"))
    assert orc.consultar("waiver", competencia_atual="2026-10") == []
    assert rel.consultar("waiver", competencia_atual="2026-10") == []
    assert [m["tipo"] for m in cin.consultar("waiver", competencia_atual="2026-10")] == ["waiver"]
    assert [m["tipo"] for m in orc.consultar("correcao", competencia_atual="2026-10")] == ["correcao"]
    novos = reg(e, "memoria")[antes:]
    assert [(r["evento"], r["agente"], r["tipo"]) for r in novos] == [
        ("negada", "AG-ORC", "waiver"), ("negada", "AG-REL", "waiver"), ("consultada", "AG-CIN", "waiver"),
        ("consultada", "AG-ORC", "correcao")]
    # ninguém além do AG-CIN grava; o AG-CUS nem recebe visão (não lê nada); no nível básico só o AG-CIN tem visão
    with pytest.raises(PermissionError, match="não grava"):
        orc.gravar("correcao", "x", {"lancamento": "L-001"}, competencia="2026-10", aprovacao="APR-001", fonte="-")
    assert e.system.agentes["AG-CUS"].memoria is None
    basico = build_system()
    assert [a for a, ag in basico.agentes.items() if ag.memoria is not None] == ["AG-CIN"]


def test_report_and_results_agents_cite_previous_approved_corrections():
    # AG-REL: relatório de exceção de setembro mostra a correção aprovada em agosto, com o id da memória
    dois_meses = Scenario("historico_no_relatorio", "alçada corrigida em dois meses", "fechar_mes", cognicao="local",
                          decisao_aprovador="corrigir", agenda=(("2026-08", ("alcada",)), ("2026-09", ("alcada",))),
                          pedidos=(("fechar_mes", "2026-08", 1), ("fechar_mes", "2026-09", 100)))
    e = run_scenario(dois_meses)
    agosto, setembro = (r.content["relatorio"] for r in e.respostas.values())
    assert "Histórico:" not in agosto
    assert "Histórico: 1 correção(ões) aprovada(s) em competências anteriores: reaprovar em 2026-08 (MEM-0001)" in setembro
    crenca = next(r for r in reg(e, "belief", "AG-REL") if r["chave"].startswith("historico_decisoes@"))
    assert crenca["fonte"] == "SVC-MEM MEM-0001"
    # AG-RES: ao explicar a variação de setembro, avisa que a base de comparação tem mês corrigido
    variacao = Scenario("variacao_apos_correcao", "correção em agosto e variação em setembro", "fechar_mes",
                        cognicao="local", decisao_aprovador="corrigir",
                        agenda=(("2026-08", ("alcada",)), ("2026-09", ("variacao_custo_fixo",))),
                        pedidos=(("fechar_mes", "2026-08", 1), ("fechar_mes", "2026-09", 100)))
    e = run_scenario(variacao)
    crenca = next(r for r in reg(e, "belief", "AG-RES") if r["chave"].startswith("correcoes_anteriores@"))
    assert crenca["fonte"] == "SVC-MEM MEM-0001" and crenca["depois"] == [{"memoria": "MEM-0001", "competencia": "2026-08"}]
    setembro = list(e.respostas.values())[1].content["relatorio"]
    assert "a base de comparação inclui correção aprovada em competência anterior (MEM-0001 em 2026-08)" in setembro

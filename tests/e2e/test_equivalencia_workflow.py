"""Equivalência funcional entre o SMA básico e o workflow centralizado da DSM4 (`baseline_eq.py`).

É este teste que sustenta a palavra "equivalente" no experimento: sem falhas, o controlador único
e os agentes têm de chegar ao mesmo status, à mesma DRE, às mesmas contas sinalizadas e atribuídas
a controle, às mesmas correções no ERP e às mesmas decisões no Approval Gate. Onde a equivalência
acaba (falha de comunicação, workflow mínimo) também fica registrado aqui.
"""
import pytest

from fin_mas import baseline, baseline_eq, metricas
from fin_mas.caos import ModeloFalhas
from fin_mas.env.dataset import Dataset
from fin_mas.estudo import PORTES  # os quatro portes do pré-registro; MEI e Média II ficam fora do experimento
from fin_mas.env.scenarios import CENARIOS, Scenario, run_scenario

pytestmark = pytest.mark.e2e

# cenários da comparação da DSM3 que não injetam falha de comunicação (com falha os braços divergem por desenho)
COMPARAVEIS = ("fechar_mes", "avaliar_orcamento", "veto_waiver", "veto_bloqueio", "veto_correcao", "correcao_parcial",
               "divergencia_fonte", "desvio_irregular", "fechamento_micro", "fechamento_pequena", "fechamento_grande")


def _decisoes(registros) -> list:
    return [(r["conversation_id"], r["decisao"], [(c["lancamento"], c["acao"]) for c in r["correcoes"]])
            for r in registros if r["kind"] == "politica" and r["evento"] == "decidido"]


def resultado_do_sma(e) -> dict:
    r, reg = e.resposta, e.audit.records
    orc = next(x["content"] for x in reversed(reg) if x["kind"] == "send" and x.get("sender") == "AG-ORC"
               and x["performative"] == "inform" and x.get("protocol") == "PROT-DEL")
    parecer = next((x["content"]["achados"] for x in reg if x["kind"] == "send" and x.get("protocol") == "PROT-CMP"
                    and x.get("sender") == "AG-CIN"), [])
    publicado = r.performative == "inform"
    return {"status": metricas.status_mas(r),
            "dre": r.content["resultado"].get("dre") if publicado else None,
            "kpis": r.content["resultado"].get("kpis") if publicado else None,
            "sinalizadas": orc["sinalizadas"], "atribuidas": orc["atribuidas_a_controle"], "totais": orc["totais"],
            "achados": [(a["regra"], a["lancamento"], a["severidade"]) for a in parecer],
            "correcoes": [(c["lancamento"], c["acao"]) for c in e.system.dataset.correcoes],
            "ressalvas": len(r.content["ressalvas"]) if publicado else None,
            "notas": len(r.content["notas"]) if publicado else None,
            "aprovacoes": _decisoes(reg),
            "expiradas": sum(1 for x in reg if x["kind"] == "timeout" and x.get("protocol") == "PROT-APR")}


def resultado_do_workflow(w) -> dict:
    reg = w.audit.records
    return {"status": w.status, "dre": w.dre if w.publicado else None, "kpis": w.kpis if w.publicado else None,
            "sinalizadas": w.sinalizadas, "atribuidas": w.atribuidas, "totais": w.totais,
            "achados": [(a["regra"], a["lancamento"], a["severidade"]) for a in w.achados],
            "correcoes": [(c["lancamento"], c["acao"]) for c in w.correcoes],
            "ressalvas": len(w.ressalvas) if w.publicado else None, "notas": len(w.notas) if w.publicado else None,
            "aprovacoes": _decisoes(reg),
            "expiradas": sum(1 for x in reg if x["kind"] == "timeout" and x.get("protocol") == "PROT-APR")}


@pytest.mark.parametrize("nome", COMPARAVEIS)
def test_equivalent_workflow_matches_the_mas_on_the_comparable_scenarios(nome):
    sc = CENARIOS[nome]
    for seed in range(1, 6):
        sma = resultado_do_sma(run_scenario(nome, seed=seed))
        w = baseline_eq.executar(seed, sc.plantar, sc.intencao, sc.porte, decisao_aprovador=sc.decisao_aprovador)
        assert resultado_do_workflow(w) == sma, f"{nome}, seed {seed}"


@pytest.mark.parametrize("porte", PORTES)
def test_equivalent_workflow_matches_the_mas_on_drawn_workloads(porte):
    """Cargas sorteadas como no experimento (plantios e perfil do aprovador), fora das seeds 1 a 30."""
    vistos = set()
    for seed in range(201, 213):
        for intencao in ("fechar_mes", "avaliar_orcamento"):
            modelo = ModeloFalhas(seed)
            sc = Scenario("estudo", "carga sorteada", intencao, plantar=modelo.plantios(), porte=porte)
            sma = resultado_do_sma(run_scenario(sc, seed=seed, caos=modelo))
            w = baseline_eq.executar(seed, modelo.plantios(), intencao, porte, caos=ModeloFalhas(seed))
            assert resultado_do_workflow(w) == sma, f"{porte}, {intencao}, seed {seed}, {modelo.plantios()}"
            vistos.add(sma["status"])
            assert not any(x["kind"] in ("drop", "erro_agente") for x in w.audit.records)
    assert {"publicado", "publicado_com_ressalva"} <= vistos  # a carga exercita mais de um desfecho


def test_equivalent_workflow_has_one_controller_and_only_approval_messages():
    w = baseline_eq.executar(7, ("alcada", "desvio_irregular"), "fechar_mes", decisao_aprovador="corrigir")
    reg = w.audit.records
    mensagens = [r for r in reg if r["kind"] in ("open", "send")]
    assert {r["protocol"] for r in mensagens} == {"PROT-APR"} and len(mensagens) == 2  # proposta e decisão
    assert {r["agente"] for r in reg if r["kind"] == "decision"} == {baseline_eq.CONTROLADOR}
    assert w.status == "publicado_com_ressalva" and len(w.correcoes) == 2 and w.atribuidas == ["C-3002 Marketing"]
    assert w.etapas == ["custos", "orcamento", "resultados", "conformidade", "reavaliacao", "relatorio"]
    # a correção só acontece com a aprovação confirmada pela política, uma vez por correção
    efeitos = [r for r in reg if r["kind"] == "politica" and r["evento"] == "efeito_executado"]
    assert len(efeitos) == 2 and all(r["conversation_id"] == "APR-001" for r in efeitos)


def test_equivalence_stops_where_messages_can_be_lost_and_the_minimal_workflow_never_was_equivalent():
    # com perda de mensagens, o SMA falha explicitamente e o workflow, que não troca mensagens entre componentes, publica
    sc = CENARIOS["falha_especialista"]
    assert metricas.status_mas(run_scenario("falha_especialista").resposta) == "falhou"
    assert baseline_eq.executar(sc.seed, sc.plantar, sc.intencao, sc.porte).status == "publicado"
    # o workflow mínimo da DSM3 publica a crítica que os outros dois braços vetam
    veto = CENARIOS["veto_bloqueio"]
    minimo = baseline.executar(Dataset(seed=1, plantar=veto.plantar), "fechar_mes")
    assert minimo.status == "publicado_com_ressalva" and minimo.criticas_publicadas == 1
    assert baseline_eq.executar(1, veto.plantar, "fechar_mes").status == "bloqueado"
    assert metricas.status_mas(run_scenario("veto_bloqueio", seed=1).resposta) == "bloqueado"

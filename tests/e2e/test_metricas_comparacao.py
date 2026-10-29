"""Métricas corrigidas e comparação SMA x workflow centralizado sob as mesmas seeds (TEST-32 e TEST-33)."""
import pytest

from fin_mas import experimentos, metricas
from fin_mas.env.scenarios import run_scenario

pytestmark = pytest.mark.e2e


def test_completion_metric_excludes_failures():
    respostas = [run_scenario("fechar_mes").resposta, run_scenario("veto_bloqueio").resposta,
                 run_scenario("falha_especialista").resposta]
    t = metricas.taxas(respostas)
    assert t["MET-01"] == pytest.approx(1 / 3)  # failure não conta como concluída
    assert t["MET-13"] == 1.0  # mas toda solicitação teve resposta explícita
    assert metricas.medir(run_scenario("veto_bloqueio"))["status"] == "bloqueado"


@pytest.fixture(scope="module")
def comparacao():
    cenarios = ["veto_bloqueio", "veto_correcao", "desvio_irregular", "divergencia_fonte", "falha_especialista"]
    linhas = experimentos.executar(seeds=range(1, 4), cenarios=cenarios)
    return linhas, experimentos.resumir(linhas)


def test_mas_vs_centralized_baseline(comparacao):
    linhas, resumo = comparacao
    sma = [r for r in linhas if r["estrategia"] == "SMA"]
    # H1: com o veto, nenhuma crítica plantada chega publicada sem correção ou waiver
    assert all(r["criticas_publicadas_sem_tratamento"] == 0 for r in sma)
    assert resumo["veto_bloqueio"]["workflow"]["criticas_publicadas_sem_tratamento"] >= 1
    # decisões distribuídas acertam o que a linha de base erra
    assert resumo["desvio_irregular"]["SMA"]["desvios_corretos"] == 1.0
    assert resumo["desvio_irregular"]["workflow"]["desvios_corretos"] == 0.0
    assert resumo["divergencia_fonte"]["workflow"]["falsos_desvios"] == 1.0
    assert resumo["veto_correcao"]["SMA"]["criticas_corrigidas"] == 1.0
    assert resumo["veto_correcao"]["SMA"]["status"] == "publicado"
    # custo: mensagens e reconsiderações que o workflow não tem
    assert all(resumo[n]["SMA"]["mensagens_a2a"] > resumo[n]["workflow"]["mensagens_a2a"] == 0 for n in resumo
               if not n.startswith("_"))
    # caso em que a sofisticação não compensa: com a perda de mensagens o SMA falha e o workflow publica
    assert resumo["falha_especialista"]["SMA"]["status"] == "falhou"
    assert resumo["falha_especialista"]["workflow"]["status"] == "publicado"
    assert resumo["_global"]["MET-13_resposta_explicita"] == 1.0
    assert 0.5 < resumo["_global"]["MET-14_distribuicao_decisoria"] < 1.0


def test_comparison_artifacts_written(comparacao, tmp_path):
    linhas, resumo = comparacao
    experimentos.gravar(linhas, resumo, tmp_path)
    csv = (tmp_path / "comparacao.csv").read_text(encoding="utf-8").splitlines()
    assert csv[0].startswith("cenario,seed,estrategia") and len(csv) == len(linhas) + 1
    assert "<svg" in (tmp_path / "comparacao.svg").read_text(encoding="utf-8")
    assert "| `desvio_irregular` | workflow |" in (tmp_path / "comparacao.md").read_text(encoding="utf-8")


def test_sma_office_day_answers_every_request():
    e = run_scenario("expediente_sma")
    respostas = e.respostas
    assert len(respostas) == 6 and metricas.taxas(list(respostas.values()))["MET-13"] == 1.0
    # fechamentos de competências diferentes não disputam reserva; o mesmo mês concorrente é recusado
    recusas = [sid for sid, r in respostas.items() if r.performative == "refuse"]
    assert recusas == ["SOL-004"] and respostas["SOL-004"].content["dono_atual"] == "SOL-003"
    competencias = {r.content["competencia"] for r in respostas.values() if r.performative == "inform"}
    assert competencias == {"2026-07", "2026-08", "2026-09"}
    assert all(e.system.locks.dono("SMA", c) is None for c in competencias)
    assert all(m["relatorio"].startswith("SMA S.A.")
               for m in (r.content for r in respostas.values() if r.performative == "inform"))

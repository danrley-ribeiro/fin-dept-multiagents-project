"""Bloco E do experimento (revisão da DSM4, feedback da DSM3): concorrência, frequência de irregularidades, volume e
porte.

Confere o aparato, não os números: reprodutibilidade, sorteios aninhados, e as propriedades que a análise usa.
"""
import pytest

from fin_mas import estudo_e

pytestmark = pytest.mark.integracao
MES = estudo_e.COMPETENCIAS[0]


def test_block_e_is_reproducible():
    """Duas execuções do plano dão as mesmas linhas (o tempo de parede fica em outro arquivo)."""
    plano = list(estudo_e.celulas(1))[:4]  # um pedaço do plano com a seed 1 basta para conferir

    def medir():
        rodadas = [(estudo_e._sma if b == "sma_basico" else estudo_e._workflow)(seed, pedidos, volume, porte, decide)
                   for _, _, _, seed, pedidos, volume, porte, decide in plano for b in estudo_e.BRACOS]
        return [{k: v for k, v in r.items() if k != "segundos"} for r in rodadas]
    assert medir() == medir()


def test_frequency_draws_are_nested():
    for seed in range(1, 31):
        baixa, media, alta = (set(estudo_e.plantios(seed, p)) for p in estudo_e.FREQUENCIAS.values())
        assert baixa <= media <= alta


def test_approver_draw_covers_the_three_decisions():
    assert {estudo_e.decisao(s) for s in range(1, 31)} == set(estudo_e.DECISOES)


@pytest.mark.parametrize("n", [2, 4])
def test_same_period_requests_publish_once_in_both_arms(n):
    """O SMA reserva o período (PROT-LCK); o workflow recusa mês já atendido na fila (o equivalente num controlador
    único). Antes, o workflow publicava o mesmo mês n vezes: a comparação media mecanismo ausente."""
    pedidos = [(MES, ("alcada",))] * n
    sma, wf = estudo_e._sma(1, pedidos), estudo_e._workflow(1, pedidos)
    for braco in (sma, wf):
        assert (braco["publicados"], braco["recusados"], braco["publicacoes_indevidas"]) == (1, n - 1, 0)
    assert sma["criticas_corrigidas"] == wf["criticas_corrigidas"] == 1  # a mesma correção conta uma vez


def test_recurrence_limits_waivers_in_both_arms():
    """Quatro meses com a mesma violação de alçada e o aprovador pedindo waiver: a POL-06 deixa passar um waiver por
    padrão nos dois braços (o workflow usa a mesma memória, SVC-MEM)."""
    pedidos = [(c, ("alcada",)) for c in estudo_e.COMPETENCIAS[:4]]
    sma = estudo_e._sma(1, pedidos, decisao_aprovador="waiver")
    wf = estudo_e._workflow(1, pedidos, decisao_aprovador="waiver")
    assert sma["waivers"] == wf["waivers"] == 1
    assert sma["publicados"] == wf["publicados"] == 1
    assert sma["criticas_publicadas_sem_tratamento"] == wf["criticas_publicadas_sem_tratamento"] == 0


def test_distinct_periods_run_in_parallel_in_the_mas_and_in_sequence_in_the_queue():
    pedidos = [(c, ("alcada",)) for c in estudo_e.COMPETENCIAS[:4]]
    um = estudo_e._sma(1, pedidos[:1])
    sma, wf = estudo_e._sma(1, pedidos), estudo_e._workflow(1, pedidos)
    assert sma["publicados"] == wf["publicados"] == 4
    assert sma["makespan_ticks"] == um["makespan_ticks"]  # em paralelo: quatro meses no tempo de um
    assert wf["makespan_ticks"] > sma["makespan_ticks"]  # em fila: um depois do outro


def test_logical_time_does_not_depend_on_volume():
    """O relógio do barramento conta eventos, não lançamentos: o custo do volume aparece no tempo de parede."""
    medidas = [estudo_e._sma(1, [(MES, ("alcada",))], v) for v in estudo_e.VOLUMES]
    assert len({m["makespan_ticks"] for m in medidas}) == 1
    assert [m["lancamentos"] for m in medidas] == sorted(m["lancamentos"] for m in medidas)

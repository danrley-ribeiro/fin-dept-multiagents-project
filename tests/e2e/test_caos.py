"""Modelo de falhas por seed (`caos.py`) e parâmetros injetáveis (`parametros.py`) sobre o sistema inteiro.

O que se confere: por padrão nada muda; com o modelo ligado, a execução se repete byte a byte
para a mesma seed; cada fator tem o seu sorteio; as falhas chegam de fato ao barramento, ao
aprovador e ao Approval Gate; e os parâmetros trocam o comportamento que deveriam trocar.
"""
import pytest

from fin_mas import estudo, invariantes, metricas
from fin_mas.caos import ModeloFalhas
from fin_mas.core.bus import Bus
from fin_mas.core.message import Message
from fin_mas.env.scenarios import CENARIOS, Scenario, run_scenario
from fin_mas.parametros import PADRAO, Parametros

pytestmark = pytest.mark.e2e
SEEDS = range(301, 313)  # fora das seeds do experimento (1 a 30)


def rodar(seed, intencao="fechar_mes", porte="media", cognicao="basico", parametros=None, **falhas):
    modelo = ModeloFalhas(seed, **falhas)
    sc = Scenario("estudo", "teste do modelo de falhas", intencao, plantar=modelo.plantios(), porte=porte, cognicao=cognicao)
    return run_scenario(sc, seed=seed, parametros=parametros, caos=modelo)


def test_chaos_and_parameters_change_nothing_by_default():
    assert Bus().caos is None
    assert Parametros() == PADRAO and PADRAO.diferencas() == {}
    for nome in ("fechar_mes", "veto_correcao", "negociacao_prazo", "expediente_sma", "ataque_acesso"):
        a, b = run_scenario(nome), run_scenario(nome, parametros=Parametros())
        assert a.hash == b.hash, nome
        assert not any("caos" in r or "parametros" in r for r in a.audit.records if r["kind"] == "meta")


def test_same_seed_repeats_the_run_and_each_factor_has_its_own_draw():
    falhas = {"perda": 0.15, "jitter": 2, "indisponibilidades": 1, "aprovador": "lento", "ataque": True}
    a, b = rodar(305, **falhas), rodar(305, **falhas)
    assert a.hash == b.hash and a.audit.records[0]["caos"]["perda"] == 0.15  # a configuração fica no trace
    assert rodar(306, **falhas).hash != a.hash
    # ligar uma falha não muda a carga: plantios, perfil do aprovador e dados da empresa são os mesmos
    for seed in SEEDS:
        calmo, agitado = ModeloFalhas(seed), ModeloFalhas(seed, **falhas)
        assert calmo.plantios() == agitado.plantios() and calmo.perfil_aprovador() == agitado.perfil_aprovador()
    assert rodar(305).system.dataset.gold == a.system.dataset.gold
    assert len({ModeloFalhas(s).plantios() for s in SEEDS}) > 6  # a carga varia entre seeds
    # o que se perde com probabilidade baixa também se perde com probabilidade alta (números aleatórios comuns)
    pedido = Message("AG-ORQ", "AG-CUS", "request", "DEL-001", "PROT-DEL", {})
    destinos = []
    for seed in range(1000, 1200):
        baixa, alta = ModeloFalhas(seed, perda=0.05), ModeloFalhas(seed, perda=0.30)
        destinos.append(([baixa.perder(pedido) for _ in range(3)], [alta.perder(pedido) for _ in range(3)]))
    assert all(not b or a for baixas, altas in destinos for b, a in zip(baixas, altas))
    assert 10 < sum(sum(b) for b, _ in destinos) < 60 < sum(sum(a) for _, a in destinos) < 260  # ~30 e ~180 de 600
    # a conversa com as pessoas não se perde nem atrasa
    humano = Message("APR", "AG-ORQ", "approve", "APR-001", "PROT-APR", {})
    ruidoso = ModeloFalhas(1, perda=1.0, jitter=5)
    assert not ruidoso.perder(humano) and ruidoso.atraso(humano) == 0 and ruidoso.perder(pedido)


def test_random_loss_and_outages_reach_the_bus_and_every_silence_is_flagged():
    perdas = indisponiveis = sem_resposta = 0
    for seed in SEEDS:
        e = rodar(seed, perda=0.15, indisponibilidades=1)
        reg = e.audit.records
        perdas += sum(1 for r in reg if r["kind"] == "drop" and r["motivo"] == "perda aleatória (caos)")
        indisponiveis += sum(1 for r in reg if r["kind"] == "agente" and r["evento"] == "desligado")
        assert all(r["protocol"] in ("PROT-DEL", "PROT-CMP", "PROT-QRY") for r in reg if r["kind"] == "drop")
        assert not any(r["kind"] == "erro_agente" for r in reg)
        violados, _ = estudo.violacoes(reg)
        # desde a correção do aviso de mensagem perdida, ninguém fica sem resposta: nenhum invariante é violado
        assert not violados and e.resposta is not None
        sem_resposta += e.resposta is None
        medida = estudo.medir_sma(e)
        assert medida["criticas_publicadas_sem_tratamento"] == 0
        assert (medida["perdas"] > 0) == (medida["t_primeira_falha"] is not None) or medida["prazos_esgotados"] > 0
    assert perdas > 10 and indisponiveis == len(SEEDS)


def test_slow_or_absent_approver_lets_the_ticket_expire_and_nothing_is_published():
    desfechos, expiradas, atrasadas = set(), 0, 0
    for seed in SEEDS:
        pontual, lento = rodar(seed), rodar(seed, aprovador="lento")
        reg = lento.audit.records
        desfechos.add(metricas.status_mas(lento.resposta))
        expiradas += sum(1 for r in reg if r["kind"] == "timeout" and r["protocol"] == "PROT-APR")
        atrasadas += sum(1 for r in reg if r["kind"] == "ambiente" and "aprovador" in r["evento"])
        assert lento.resposta is not None and estudo.medir_sma(lento)["criticas_publicadas_sem_tratamento"] == 0
        if not any(r.get("protocol") == "PROT-APR" for r in pontual.audit.records):
            assert metricas.status_mas(lento.resposta) == metricas.status_mas(pontual.resposta)  # sem veto, nada muda
        assert invariantes.verificar(reg) == []
    assert expiradas > 0 and atrasadas > 0 and "bloqueado" in desfechos


def test_attacks_during_combined_failures_are_all_rejected():
    tentados = 0
    for seed in SEEDS:
        e = rodar(seed, perda=0.10, jitter=2, indisponibilidades=1, aprovador="lento", ataque=True)
        medida = estudo.medir_sma(e)
        tentados += medida["ataques_tentados"]
        assert medida["ataques_aceitos"] == 0 and medida["criticas_publicadas_sem_tratamento"] == 0
        assert not estudo.violacoes(e.audit.records)[0] and e.resposta is not None
    assert tentados >= 14  # pelo menos uma execução teve veto pendente e foi atacada


def test_injected_parameters_change_the_coordination_they_control():
    # reenvio: com uma só tentativa, a perda de uma mensagem derruba a solicitação que o padrão recupera
    assert run_scenario("depuracao").resposta.performative == "inform"
    assert run_scenario("depuracao", parametros=Parametros(max_tentativas=1)).resposta.performative == "failure"
    # veto com correção: sem ciclo de correção o aprovador não tem o que corrigir e o prazo esgota
    assert metricas.status_mas(run_scenario("veto_correcao").resposta) == "publicado"
    sem_correcao = run_scenario("veto_correcao", parametros=Parametros(max_correcoes=0))
    assert metricas.status_mas(sem_correcao.resposta) == "bloqueado" and sem_correcao.system.dataset.correcoes == []
    # negociação de prazo: com extensão zero o Orquestrador recusa e a hipótese é arquivada
    assert any(r.get("performative") == "accept-proposal" for r in run_scenario("negociacao_prazo").audit.records)
    sem_negociacao = run_scenario("negociacao_prazo", parametros=Parametros(max_extensao=0))
    assert any(r.get("performative") == "reject-proposal" for r in sem_negociacao.audit.records)
    # reserva de período: sem ela, dois pedidos do mesmo mês são executados e publicados
    dois = Scenario("dois_pedidos", "dois fechamentos do mesmo mês", "fechar_mes",
                    pedidos=(("fechar_mes", None, 1), ("fechar_mes", None, 3)))
    com, sem = run_scenario(dois), run_scenario(dois, parametros=Parametros(reserva_periodo=False))
    assert [r.performative for r in com.respostas.values()] == ["inform", "refuse"]
    assert [r.performative for r in sem.respostas.values()] == ["inform", "inform"]
    assert not any(r["kind"] == "lock" for r in sem.audit.records)
    # prazos e limiares chegam a quem os usa, e ficam no trace
    e = run_scenario("veto_bloqueio", parametros=Parametros(prazo_aprovacao=7, prazo_subtarefa=45, ttl_reserva=90))
    meta = e.audit.records[0]
    assert meta["prazo_aprovacao"] == 7 and meta["parametros"] == {"prazo_aprovacao": 7, "prazo_subtarefa": 45, "ttl_reserva": 90}
    assert e.system.orq.conhecimento["prazo_subtarefa"] == 45 and e.system.locks.ttl == 90
    frouxo = run_scenario("avaliar_orcamento", parametros=Parametros(limiar_percentual=40))
    assert frouxo.resposta.content["resultado"]["sinalizadas"] == []  # o gabarito continua com os dois desvios
    assert len(frouxo.system.dataset.gold["desvios"]) == 2
    assert CENARIOS["avaliar_orcamento"].plantar == ("desvio_orcamentario",)


def test_late_delivery_of_an_earlier_message_does_not_hide_a_lost_final_answer():
    """Correção simulada da DSM4 (C1): com atraso de entrega de 3 ticks ou mais, o `agree` atrasado chegava depois de
    o `inform` final se perder e apagava a marca da perda; o Orquestrador esperava para sempre. Toda execução responde."""
    for jitter in (3, 4, 6):
        for seed in SEEDS:
            e = rodar(seed, perda=0.10, jitter=jitter, indisponibilidades=1, aprovador="lento")
            assert e.resposta is not None, (jitter, seed)
            assert not estudo.violacoes(e.audit.records)[0], (jitter, seed)

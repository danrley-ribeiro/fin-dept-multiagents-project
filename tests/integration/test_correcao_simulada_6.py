"""DSM3 — achados da 6ª rodada de correção simulada, um teste por achado corrigido.

1. um pedido de competência distante (2099-12) não apaga a memória de waivers, e a POL-06 continua valendo;
4. ids de memória nunca são reaproveitados, nem depois de uma expiração;
7. decisão depois do prazo é avisada a quem decidiu, e a pendência vencida some da lista.
"""
import pytest

from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.services.audit import AuditLog
from fin_mas.services.memoria import Memoria
from test_dashboard_acesso import entrar, servico  # noqa: F401  (fixture e login HTTP reais)

pytestmark = pytest.mark.integracao
VALOR = {"regra": "alcada", "lancamento": "L-001"}


class PoliticaFalsa:  # mesma dublê de tests/unit/test_memoria_redacao.py
    def __init__(self, **tickets):
        self.tickets = tickets


def ticket(competencia):
    return {"estado": "aprovado", "solicitacao": "SOL-001", "cmp": "CMP-001", "decisao": "waiver",
            "competencia": competencia, "achados": [{"lancamento": "L-001"}], "executadas": [],
            "aprovado_por": {"pessoa": "controller"}}


def _mes(competencia, nome):
    return Scenario(nome, f"alçada violada em {competencia}, humano dá waiver", "fechar_mes", decisao_aprovador="waiver",
                    agenda=((competencia, ("alcada",)),), pedidos=(("fechar_mes", competencia, 1),))


# ---- 1. competência distante não apaga a memória -------------------------------------------------
def test_far_future_request_does_not_erase_the_waiver_memory(tmp_path):
    arquivo = tmp_path / "memoria.json"
    run_scenario(_mes("2026-08", "agosto"), memoria=arquivo)
    distante = run_scenario(_mes("2099-12", "distante"), memoria=arquivo)  # o ataque da 6ª rodada
    assert not [r for r in distante.audit.records if r["kind"] == "memoria" and r["evento"] == "expirada"]
    setembro = run_scenario(_mes("2026-09", "setembro"), memoria=arquivo)
    t = setembro.system.politica.tickets["APR-001"]
    assert "waiver" not in t["opcoes"] and t["negadas"][0]["regra"] == "POL-06"  # agosto continua lembrado
    assert setembro.resposta.performative == "failure"


def test_retention_is_a_query_filter_and_removal_is_explicit():
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**{"APR-001": ticket(competencia="2026-08")}))
    cin = mem.visao("AG-CIN")
    cin.gravar("waiver", "k", VALOR, competencia="2026-08", aprovacao="APR-001", fonte="-")
    assert cin.consultar("waiver", "k", competencia_atual="2099-12") == []  # fora da janela do pedido distante
    assert len(mem.entradas) == 1  # mas não apagada
    assert cin.consultar("waiver", "k", competencia_atual="2026-09")  # e vista pelo mês seguinte
    mem.expirar("2099-12")  # manutenção explícita
    assert mem.entradas == []


# ---- 4. ids de memória ----------------------------------------------------------------------------
def test_memory_ids_are_never_reused_after_expiry(tmp_path):
    tickets = {"APR-001": ticket(competencia="2026-01"), "APR-002": ticket(competencia="2027-06")}
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**tickets), caminho=tmp_path / "m.json", retencao=2)
    cin = mem.visao("AG-CIN")
    primeira = cin.gravar("waiver", "k", VALOR, competencia="2026-01", aprovacao="APR-001", fonte="-")
    mem.expirar("2027-06")
    assert mem.entradas == []
    segunda = cin.gravar("waiver", "k", VALOR, competencia="2027-06", aprovacao="APR-002", fonte="-")
    assert primeira["id"] == "MEM-0001" and segunda["id"] != primeira["id"]
    outra = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**tickets), caminho=tmp_path / "m.json", retencao=2)
    assert outra.integra and [e["id"] for e in outra.entradas] == [segunda["id"]]  # entre processos também


# ---- 7. decisão depois do prazo ------------------------------------------------------------------
def test_decision_after_the_deadline_is_reported_and_the_pending_item_disappears(servico):  # noqa: F811
    sim, _, porta = servico("decisao_por_pessoa")
    for _ in range(5000):  # até o veto, e depois até o prazo do ticket esgotar sem decisão
        if sim.sistema.aprovador.pendentes:
            break
        sim.sistema.bus.step()
    ticket_id = next(iter(sim.sistema.aprovador.pendentes.values())).conversation_id
    while not sim.sistema.bus.conversations[ticket_id].is_final:
        sim.sistema.bus.step()
    assert sim.snapshot()["pendentes_humanos"] == []  # vencida não aparece mais como pendência
    avisos = []
    sim._emitir = lambda ev: avisos.append(ev)
    diego = entrar(porta, "diego")
    decisao = {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "corrigir", "justificativa": "reaprovar com outro gerente"}
    assert diego.post("/api/comando", decisao)[0] == 202
    sim.processar_comandos()
    assert any("já foi encerrado (estado EXPIRADA)" in (ev.get("erro") or "") for ev in avisos)  # quem decidiu é avisado
    assert not sim.sistema.aprovador.pendentes
    recusa = [r for r in sim.registros if r["kind"] == "decisao_nao_enviada"]  # e o trace diz que não valeu
    assert len(recusa) == 1 and recusa[0]["ator"] == "diego" and recusa[0]["ticket"] == ticket_id
    assert "EXPIRADA" in recusa[0]["motivo"]

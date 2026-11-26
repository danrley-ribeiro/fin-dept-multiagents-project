"""Revisão da DSM4, correção simulada: a memória do dashboard sobrevive ao reinício do cenário.

No modo demonstração, a simulação principal nascia sem arquivo de memória: cada reinício montava um SVC-MEM novo e o
waiver de agosto da rodada anterior era esquecido; setembro recebia waiver de novo (o caminho do teste do professor
na DSM3). Agora a memória fica em arquivo e reiniciar não a apaga; apagar é o comando `limpar_memoria`, só do
administrador (PERM-MEM-LIMPAR), registrado no trace.
"""
import json

import pytest

from test_dashboard_acesso import _ate_humano, entrar, servico  # noqa: F401  (fixture e login HTTP reais)

pytestmark = pytest.mark.integracao
JUSTIFICATIVA = "risco aceito pela diretoria nesta competência"


def _competencia(sim, sid):
    return sim.sistema.aprovador.pendentes[sid].content.get("competencia")


def _pendente_de(sim, competencia, limite=20):
    """Avança até haver uma pendência humana da competência pedida e devolve (sid, ticket)."""
    for _ in range(limite):
        _ate_humano(sim)
        for sid, msg in sim.sistema.aprovador.pendentes.items():
            if msg.content.get("competencia") == competencia and not sim.sistema.bus.conversations[msg.conversation_id].is_final:
                return sid, msg.conversation_id
        sim.passo()
    raise AssertionError(f"nenhuma pendência de {competencia}")


def _decidir(sim, navegador, sid, decisao):
    assert navegador.post("/api/comando", {"tipo": "decidir", "solicitacao": sid, "decisao": decisao,
                                           "justificativa": JUSTIFICATIVA})[0] == 202
    sim.processar_comandos()


def test_restart_keeps_the_waiver_memory_and_only_the_administrator_clears_it(servico, tmp_path):  # noqa: F811
    arquivo = tmp_path / "memoria.json"
    sim, _, porta = servico("reincidencia_waiver", memoria=str(arquivo))
    operador, controller = entrar(porta, "operador"), entrar(porta, "controller")
    reinicio = {"tipo": "reiniciar", "cenario": "reincidencia_waiver"}

    # rodada 1: agosto recebe o waiver
    assert operador.post("/api/comando", reinicio)[0] == 202
    sim.processar_comandos()
    sid, _ = _pendente_de(sim, "2026-08")
    _decidir(sim, controller, sid, "waiver")
    assert sum(e["tipo"] == "waiver" for e in json.loads(arquivo.read_text(encoding="utf-8"))["entradas"]) == 1

    # rodada 2, depois de reiniciar: setembro não recebe waiver (antes, o reinício esquecia agosto)
    assert operador.post("/api/comando", reinicio)[0] == 202
    sim.processar_comandos()
    sid, ticket = _pendente_de(sim, "2026-09")
    assert "waiver" not in sim.sistema.politica.tickets[ticket]["opcoes"]
    _decidir(sim, controller, sid, "waiver")
    assert sid in sim.sistema.aprovador.pendentes  # a tentativa não foi enviada: a pendência continua
    assert sum(e["tipo"] == "waiver" for e in json.loads(arquivo.read_text(encoding="utf-8"))["entradas"]) == 1

    # limpar a memória é do administrador: quem opera (e o avaliador, que também aprova) não apaga o histórico
    for usuario in ("operador", "avaliador"):
        status, _ = entrar(porta, usuario).post("/api/comando", {"tipo": "limpar_memoria"})
        assert status == 403
    admin = entrar(porta, "admin")
    assert admin.post("/api/comando", {"tipo": "limpar_memoria"})[0] == 202
    sim.processar_comandos()
    assert json.loads(arquivo.read_text(encoding="utf-8"))["entradas"] == []
    limpeza = [r for r in sim.registros if r["kind"] == "memoria" and r.get("evento") == "limpa"]
    assert limpeza and limpeza[-1]["ator"] == "admin" and len(limpeza[-1]["memorias"]) == 1


def test_demo_server_gives_the_main_simulation_a_memory_file(tmp_path, monkeypatch):
    """`serve --demo` sem empresa cadastrada: a simulação principal grava a memória em <pasta de dados>/memoria.json
    (antes, `memoria=None`: só em processo, esquecida a cada reinício)."""
    from fin_mas import server
    from fin_mas.live import Simulacao

    class Capturado(Exception):
        pass

    def capturar(sim, **_kw):
        raise Capturado(sim)

    monkeypatch.setattr(server, "criar_servidor", capturar)
    monkeypatch.setattr(Simulacao, "iniciar", lambda self: None)
    pasta = tmp_path / "dados" / "empresa"
    with pytest.raises(Capturado) as capturado:
        server.servir("reincidencia_waiver", pasta_dados=str(pasta), pasta_acesso=str(tmp_path / "acesso"), demo=True)
    sim = capturado.value.args[0]
    assert sim.memoria == str(pasta / "memoria.json")
    assert sim.sistema.memoria.caminho == pasta / "memoria.json"

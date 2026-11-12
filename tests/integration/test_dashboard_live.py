"""Integração da execução ao vivo com o servidor do dashboard (TEST-34) e dos arquivos gerados (TEST-35).

Simulação, bus, agentes, servidor HTTP real em 127.0.0.1 e exportação juntos; a rede
externa segue bloqueada pelo conftest.
"""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from fin_mas.env.dataset import brl
from fin_mas.exportar import exportar_traces, gravar_relatorio
from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor, tratar
from helpers import aguardando_humano

pytestmark = pytest.mark.integracao


def _ate_esvaziar(sim, limite=5000):
    for _ in range(limite):
        if not sim.passo():
            return
    raise AssertionError("simulação não esvaziou a fila")


def _ate_humano(sim, limite=5000):
    """Avança até a fila esvaziar ou só faltar o prazo da aprovação humana (o dashboard espera)."""
    for _ in range(limite):
        sim.processar_comandos()
        if aguardando_humano(sim.sistema.bus) or not sim.passo():
            return
    raise AssertionError("simulação não chegou à espera humana")


def test_live_operator_controls_and_human_decision():
    sim = Simulacao("veto_waiver", interativo=True)
    _ate_humano(sim)
    estado = sim.snapshot()
    pendente = estado["pendentes_humanos"][0]
    assert pendente["solicitacao"] == "SOL-001" and pendente["opcoes"] == ["corrigir", "waiver", "bloquear"]
    assert estado["solicitacoes"]["SOL-001"] is None  # o fechamento espera o humano
    assert estado["agentes"]["AG-CIN"]["bdi"]["intencoes"][0]["estado"] == "suspensa"
    sim.comando({"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "corrigir"})
    _ate_esvaziar(sim)
    final = sim.snapshot()
    assert final["solicitacoes"]["SOL-001"]["content"]["status"] == "publicado"
    assert final["conversas"]["CMP-001"]["estado"] == "LIBERADO"
    json.dumps(final, default=str)  # o snapshot vai para o navegador


def test_offline_agent_causes_timeouts_and_explicit_failure():
    sim = Simulacao("desvio_irregular", interativo=True)
    sim.comando({"tipo": "agente", "agente": "AG-CIN", "online": False})
    _ate_esvaziar(sim)
    registros = sim.registros
    assert any(r["kind"] == "agente" and r["evento"] == "desligado" for r in registros)
    perdidas = {r["conversation_id"] for r in registros if r["kind"] == "drop"
                and r["motivo"] == "agente fora de operação"}
    assert "QRY-001" in perdidas and "CMP-001" in perdidas
    # o AG-ORC replaneja sozinho; o Orquestrador reenvia a verificação uma vez e falha explicitamente
    assert any(r["kind"] == "intention" and r["plano"] == "P-SEM-EXPLICACAO" and r["evento"] == "concluida"
               for r in registros)
    resposta = sim.snapshot()["solicitacoes"]["SOL-001"]
    assert resposta["performative"] == "failure" and resposta["content"]["subtarefa"] == "conformidade"


def test_server_routes_validate_commands():
    sim = Simulacao("fechar_mes", pausado=True)
    status, _, corpo = tratar(sim, "GET", "/api/cenarios")
    dados = json.loads(corpo)
    assert status == 200 and "expediente_sma" in [c["nome"] for c in dados["cenarios"]]
    assert dados["empresa"]["sigla"] == "SMA" and dados["agentes"]["AG-ORC"]["titulo"] == "Agente de Orçamento"
    assert tratar(sim, "POST", "/api/comando", b'{"tipo": "voar"}')[0] == 400
    assert tratar(sim, "POST", "/api/comando", b'{"tipo": "agente", "agente": "AG-ORQ", "online": false}')[0] == 400
    assert tratar(sim, "POST", "/api/comando", b'{"tipo": "velocidade", "ms_por_tick": 50}')[0] == 202
    sim.processar_comandos()
    assert sim.controle()["ms_por_tick"] == 50
    assert tratar(sim, "GET", "/api/inexistente")[0] == 404


def test_live_server_streams_trace_over_http():
    sim = Simulacao("fechar_mes", ms_por_tick=0)
    sim.iniciar()
    servidor = criar_servidor(sim, porta=0)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{porta}"
        token = json.load(urllib.request.urlopen(url + "/api/sessao", timeout=5))["token"]
        req = urllib.request.Request(url + "/api/comando", data=b'{"tipo": "pausar"}', method="POST",
                                     headers={"X-SMA-Token": token})
        assert urllib.request.urlopen(req, timeout=5).status == 202
        with urllib.request.urlopen(url + "/api/eventos", timeout=5) as stream:
            primeiro = json.loads(stream.readline().decode("utf-8")[len("data: "):])
            assert primeiro["tipo"] == "reset" and primeiro["cenario"] == "fechar_mes"
            stream.readline()
            segundo = json.loads(stream.readline().decode("utf-8")[len("data: "):])
            assert segundo["tipo"] == "registro" and segundo["registro"]["kind"] == "meta"
        for _ in range(100):  # comandos são aplicados de forma assíncrona pela thread da simulação
            estado = json.load(urllib.request.urlopen(url + "/api/estado", timeout=5))
            if estado["controle"]["pausado"]:
                break
            time.sleep(0.02)
        assert estado["controle"]["pausado"] is True and "AG-ORC" in estado["agentes"]
    finally:
        servidor.shutdown()
        servidor.server_close()
        sim.parar()


def test_export_and_branded_report_files(tmp_path):
    nomes = exportar_traces(tmp_path / "traces")
    indice = json.loads((tmp_path / "traces" / "index.json").read_text(encoding="utf-8"))
    assert {c["nome"] for c in indice["cenarios"]} == set(nomes) and "expediente_sma" in nomes
    trace = json.loads((tmp_path / "traces" / "desvio_irregular.json").read_text(encoding="utf-8"))
    kinds = {r["kind"] for r in trace["registros"]}
    assert {"meta", "belief", "desire", "deliberation", "intention", "decision"} <= kinds
    html_path, json_path = gravar_relatorio("fechar_mes", tmp_path / "saidas")
    html = html_path.read_text(encoding="utf-8")
    resultado = json.loads(json_path.read_text(encoding="utf-8"))
    assert 'aria-label="SMA"' in html and "SMA" in html
    ebitda = resultado["resposta"]["content"]["resultado"]["dre"]["ebitda"]
    assert brl(ebitda) in html and resultado["hash_trace"][:16] in html


def test_restart_replays_initial_records_to_live_clients():
    sim = Simulacao("fechar_mes", pausado=True)
    eventos = []
    sim.ouvintes.append(eventos.append)
    sim.comando({"tipo": "reiniciar", "cenario": "fechar_mes", "porte": "micro"})
    sim.processar_comandos()
    tipos = [e["tipo"] for e in eventos]
    assert tipos[0] == "reset"
    registros = [e["registro"] for e in eventos if e["tipo"] == "registro"]
    # quem já estava conectado recebe o meta (porte) e o pedido inicial do novo cenário
    assert registros[0]["kind"] == "meta" and registros[0]["porte"] == "micro"
    assert any(r["kind"] == "open" and r["protocol"] == "PROT-SOL" for r in registros)


def test_dashboard_mutations_require_session_token():
    """POST sem token, com token errado, de outro site (Origin) ou por outro nome (Host) é recusado (403)."""
    sim = Simulacao("veto_waiver", interativo=True, ms_por_tick=0, pausado=True)
    servidor = criar_servidor(sim, porta=0)
    url = f"http://127.0.0.1:{servidor.server_address[1]}"
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    def status(caminho, metodo="GET", corpo=None, **cabecalhos):
        req = urllib.request.Request(url + caminho, data=corpo, method=metodo, headers=cabecalhos)
        try:
            return urllib.request.urlopen(req, timeout=5).status
        except urllib.error.HTTPError as erro:
            return erro.code

    try:
        decisao = b'{"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "waiver"}'
        assert status("/api/comando", "POST", decisao) == 403
        assert status("/api/comando", "POST", decisao, **{"X-SMA-Token": "chute"}) == 403
        token = servidor.token
        assert status("/api/comando", "POST", decisao, **{"X-SMA-Token": token, "Origin": "https://evil.example"}) == 403
        assert status("/api/sessao", Host="evil.example:8765") == 403  # DNS rebinding
        assert status("/api/sessao", Origin="https://evil.example") == 403
        assert status("/api/dados/planilha", "POST", b"{}") == 403
        assert sim.comandos.empty()  # nada chegou à simulação
        assert status("/api/comando", "POST", b'{"tipo": "pausar"}', **{"X-SMA-Token": token}) == 202
        assert status("/api/sessao", Host="localhost:5173", Origin="http://localhost:5173") == 200  # Vite em dev
    finally:
        servidor.shutdown()
        servidor.server_close()


def test_malformed_dashboard_commands_do_not_kill_the_simulation():
    """Revisão da DSM3 (M3): comando com tipo errado é recusado (400) e a thread da simulação segue viva."""
    sim = Simulacao("veto_waiver", interativo=True, ms_por_tick=0)
    sim.iniciar()
    try:
        for cmd in ({"tipo": "passo", "n": "muitos"}, {"tipo": "velocidade", "ms_por_tick": "rapido"},
                    {"tipo": "solicitar", "intencao": "fechar_mes", "competencia": "agosto"},
                    {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "waiver", "justificativa": 12345},
                    {"tipo": "agente", "agente": "AG-CIN", "online": "nao"}):
            assert tratar(sim, "POST", "/api/comando", json.dumps(cmd).encode())[0] == 400
        sim._aplicar = lambda cmd: (_ for _ in ()).throw(RuntimeError("defeito"))  # mesmo um erro inesperado
        sim.comando({"tipo": "pausar"})
        time.sleep(0.3)
        assert sim._thread.is_alive()
    finally:
        sim.parar()


def test_dashboard_authenticates_before_reading_the_body():
    """Recorreção (N5): sem token, um corpo enorme declarado não é lido; token não-ASCII não gera exceção."""
    import socket as _socket

    sim = Simulacao("fechar_mes", interativo=True, ms_por_tick=0, pausado=True)
    servidor = criar_servidor(sim, porta=0)
    porta = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        for cabecalho in ("", "X-SMA-Token: ç\r\n"):
            with _socket.create_connection(("127.0.0.1", porta), timeout=3) as s:
                s.sendall(("POST /api/comando HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 10000000\r\n"
                           + cabecalho + "\r\n").encode("latin-1"))
                resposta = s.recv(200).decode("latin-1")  # sem enviar o corpo: precisa responder já
            assert resposta.startswith("HTTP/1.0 403") or resposta.startswith("HTTP/1.1 403"), resposta
        assert sim.comandos.empty()
    finally:
        servidor.shutdown()
        servidor.server_close()

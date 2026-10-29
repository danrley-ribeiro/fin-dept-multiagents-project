"""Servidor local do dashboard (biblioteca padrão, sem rede externa).

    GET  /api/cenarios   cenários, fichas dos agentes e da empresa
    GET  /api/estado     snapshot: controle, mente BDI de cada agente, conversas, pendências humanas
    GET  /api/eventos    Server-Sent Events: histórico do trace e cada registro novo, ao vivo
    POST /api/comando    {"tipo": "pausar" | "retomar" | "passo" | "velocidade" | "agente" | ...}

Também serve o build do dashboard (`web/dist`) quando ele existe.
"""
import json
import mimetypes
import queue
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from fin_mas.env.scenarios import CENARIOS
from fin_mas.exportar import agentes_info, empresa_info
from fin_mas.live import ComandoInvalido, Simulacao

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def _json(status, dados) -> tuple[int, dict, bytes]:
    corpo = json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, corpo


def tratar(sim: Simulacao, metodo: str, caminho: str, corpo: bytes = b"") -> tuple[int, dict, bytes]:
    """Roteamento sem socket (testado diretamente); /api/eventos é tratado à parte (streaming)."""
    rota = caminho.split("?", 1)[0]
    if metodo == "GET" and rota == "/api/cenarios":
        return _json(200, {"cenarios": [{"nome": n, "descricao": s.descricao} for n, s in CENARIOS.items()],
                           "agentes": agentes_info(), "empresa": empresa_info()})
    if metodo == "GET" and rota == "/api/estado":
        return _json(200, sim.snapshot())
    if metodo == "POST" and rota == "/api/comando":
        try:
            cmd = json.loads(corpo or b"{}")
            sim.comando(cmd)
        except (ValueError, ComandoInvalido) as erro:
            return _json(400, {"erro": str(erro)})
        return _json(202, {"ok": True, "comando": cmd})
    if metodo == "GET" and not rota.startswith("/api/"):
        return _estatico(rota)
    return _json(404, {"erro": f"rota desconhecida: {metodo} {rota}"})


def _estatico(rota) -> tuple[int, dict, bytes]:
    if not WEB_DIST.exists():
        return 404, {"Content-Type": "text/plain; charset=utf-8"}, (
            "Dashboard não construído: rode `npm install && npm run build` em web/ "
            "ou use `npm run dev` (porta 5173).").encode("utf-8")
    alvo = (WEB_DIST / rota.lstrip("/")).resolve()
    if WEB_DIST.resolve() not in alvo.parents and alvo != WEB_DIST.resolve() or not alvo.is_file():
        alvo = WEB_DIST / "index.html"  # SPA: qualquer rota cai no index
    tipo = mimetypes.guess_type(alvo.name)[0] or "application/octet-stream"
    return 200, {"Content-Type": tipo}, alvo.read_bytes()


def criar_servidor(sim: Simulacao, host="127.0.0.1", porta=8765) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencioso: o trace é o log
            pass

        def _responder(self, status, cabecalhos, corpo):
            self.send_response(status)
            for k, v in cabecalhos.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/api/eventos":
                self._eventos()
            else:
                self._responder(*tratar(sim, "GET", self.path))

        def do_POST(self):
            tamanho = int(self.headers.get("Content-Length", 0))
            self._responder(*tratar(sim, "POST", self.path, self.rfile.read(tamanho)))

        def _eventos(self):
            fila: queue.Queue = queue.Queue()
            with sim.lock:  # histórico e assinatura atômicos: nenhum registro perdido ou duplicado
                historico = [{"tipo": "reset", "geracao": sim.geracao, "cenario": sim.cenario.nome,
                              "seed": sim.seed}] + [{"tipo": "registro", "geracao": sim.geracao, "registro": r}
                                                    for r in sim.registros]
                historico.append({"tipo": "controle", "geracao": sim.geracao, "estado": sim.controle()})
                sim.ouvintes.append(fila.put)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                for evento in historico:
                    self._enviar(evento)
                while True:
                    try:
                        self._enviar(fila.get(timeout=10))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            finally:
                if fila.put in sim.ouvintes:
                    sim.ouvintes.remove(fila.put)

        def _enviar(self, evento):
            dados = json.dumps(evento, ensure_ascii=False, default=str)
            self.wfile.write(f"data: {dados}\n\n".encode("utf-8"))
            self.wfile.flush()

    servidor = ThreadingHTTPServer((host, porta), Handler)
    servidor.daemon_threads = True
    return servidor


def servir(cenario="expediente_sma", seed=None, porta=8765, ms_por_tick=350) -> None:
    sim = Simulacao(cenario, seed, interativo=True, ms_por_tick=ms_por_tick)
    sim.iniciar()
    servidor = criar_servidor(sim, porta=porta)
    print(f"dashboard da SMA: http://127.0.0.1:{porta}  (API em /api; Ctrl+C encerra)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sim.parar()
        servidor.server_close()

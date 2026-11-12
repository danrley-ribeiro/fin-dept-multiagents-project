"""Servidor local do dashboard (biblioteca padrão, sem rede externa).

    GET  /api/cenarios   cenários, fichas dos agentes e da empresa
    GET  /api/estado     snapshot: controle, mente BDI de cada agente, conversas, pendências humanas
    GET  /api/eventos    Server-Sent Events: histórico do trace e cada registro novo, ao vivo
    POST /api/comando    {"tipo": "pausar" | "retomar" | "passo" | "velocidade" | "agente" | ...}
    GET  /api/modelos            modelos Excel disponíveis (empresa sem ERP)
    GET  /api/modelos/<arquivo>  baixa o modelo (.xlsx gerado na hora)
    GET  /api/dados              planilha atual da pasta de dados e validação
    POST /api/dados/planilha     {"nome", "conteudo_base64"}: valida e grava a planilha preenchida

Também serve o build do dashboard (`web/dist`) quando ele existe.

Proteção (DSM3): o servidor escuta só em loopback e recusa (403) requisições cujo `Host`
ou `Origin` não seja `127.0.0.1`/`localhost` (DNS rebinding e páginas de outros sites).
Os POST (comandos, decisão humana e envio de planilha) exigem o cabeçalho `X-SMA-Token`
com o token da sessão, que o dashboard obtém em `GET /api/sessao`: outro site não lê essa
resposta (sem CORS) e, portanto, não consegue forjar comandos (CSRF).
"""
import base64
import json
import mimetypes
import hmac
import queue
import secrets
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from fin_mas.env.dataset import Dataset
from fin_mas.env.portes import PORTES, perfil
from fin_mas.env.scenarios import CENARIOS
from fin_mas.exportar import agentes_info, empresa_info
from fin_mas.fontes import planilha
from fin_mas.live import ComandoInvalido, Simulacao

MODELOS = {"modelo_controladoria_em_branco.xlsx": None, **{f"exemplo_{p}.xlsx": p for p in PORTES}}
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
LIMITE_UPLOAD = 5 * 1024 * 1024

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
LOOPBACK = {"127.0.0.1", "localhost"}
LEITURA_SEGUNDOS = 5  # tempo máximo para receber o corpo de um POST
DESCARTE_MAXIMO = 64 * 1024  # corpo de requisição recusada que ainda é lido e descartado
CABECALHO_TOKEN = "X-SMA-Token"


def _nome_host(valor: str | None) -> str | None:
    """Nome sem porta de um cabeçalho Host ("localhost:5173") ou Origin ("http://localhost:5173")."""
    if not valor:
        return None
    return urlsplit(valor if "//" in valor else "//" + valor).hostname


def _json(status, dados) -> tuple[int, dict, bytes]:
    corpo = json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, corpo


def tratar(sim: Simulacao, metodo: str, caminho: str, corpo: bytes = b"") -> tuple[int, dict, bytes]:
    """Roteamento sem socket (testado diretamente); /api/eventos é tratado à parte (streaming)."""
    rota = caminho.split("?", 1)[0]
    if metodo == "GET" and rota == "/api/cenarios":
        return _json(200, {"cenarios": [{"nome": n, "descricao": s.descricao} for n, s in CENARIOS.items()],
                           "agentes": agentes_info(), "empresa": empresa_info(),
                           "portes": [{"porte": p, "titulo": perfil(p)["titulo"], "tem_erp": perfil(p)["tem_erp"],
                                       "norma_contabil": perfil(p)["norma_contabil"]} for p in PORTES]})
    if metodo == "GET" and rota == "/api/modelos":
        return _json(200, {"modelos": [{"arquivo": a, "porte": p, "descricao": "modelo em branco" if p is None
                                        else f"exemplo preenchido ({perfil(p)['titulo']})"} for a, p in MODELOS.items()]})
    if metodo == "GET" and rota.startswith("/api/modelos/"):
        return _modelo(rota.rsplit("/", 1)[-1])
    if metodo == "GET" and rota == "/api/dados":
        return _json(200, _situacao_dados(sim.pasta_dados))
    if metodo == "POST" and rota == "/api/dados/planilha":
        return _receber_planilha(sim.pasta_dados, corpo)
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


def _modelo(arquivo) -> tuple[int, dict, bytes]:
    if arquivo not in MODELOS:
        return _json(404, {"erro": f"modelo desconhecido: {arquivo}"})
    porte = MODELOS[arquivo]
    with tempfile.TemporaryDirectory() as tmp:
        caminho = planilha.gerar_modelo(f"{tmp}/{arquivo}",
                                        exemplo=Dataset(seed=42, porte=porte, plantar=("competencia",)) if porte else None)
        conteudo = caminho.read_bytes()
    return 200, {"Content-Type": XLSX, "Content-Disposition": f'attachment; filename="{arquivo}"'}, conteudo


def _situacao_dados(pasta) -> dict:
    if pasta is None:
        return {"pasta": None, "planilha": None}
    try:
        ds = planilha.ler(pasta)
    except planilha.ModeloInvalido as e:
        return {"pasta": str(pasta), "planilha": None, "erros": e.erros}
    return {"pasta": str(pasta), "planilha": ds.arquivo.name, "erros": [], "porte": ds.porte,
            "competencia": ds.competencia, "razao_social": ds.razao_social, "tem_erp": ds.tem_erp,
            "lancamentos": len(ds.lancamentos)}


def _receber_planilha(pasta, corpo) -> tuple[int, dict, bytes]:
    """Valida a planilha enviada pelo dashboard antes de gravá-la como a planilha da pasta."""
    if pasta is None:
        return _json(400, {"erro": "servidor sem pasta de dados (--pasta-dados)"})
    try:
        pedido = json.loads(corpo or b"{}")
        conteudo = base64.b64decode(pedido["conteudo_base64"], validate=True)
        nome = Path(str(pedido.get("nome") or "planilha.xlsx")).name
    except (ValueError, KeyError) as erro:
        return _json(400, {"erro": f"pedido inválido: {erro}"})
    if not nome.lower().endswith(".xlsx") or len(conteudo) > LIMITE_UPLOAD:
        return _json(400, {"erro": "envie um .xlsx de até 5 MB"})
    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / nome
        alvo.write_bytes(conteudo)
        try:
            ds = planilha.ler(alvo)
        except planilha.ModeloInvalido as e:
            return _json(422, {"ok": False, "erros": e.erros})
        except Exception as erro:  # arquivo que nem abre como xlsx
            return _json(422, {"ok": False, "erros": [f"não foi possível ler a planilha: {erro}"]})
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.xlsx"):  # uma planilha por vez: a pasta é a fonte da competência
        antigo.unlink()
    (pasta / nome).write_bytes(conteudo)
    return _json(200, {"ok": True, "erros": [], "planilha": nome, "porte": ds.porte, "competencia": ds.competencia,
                       "razao_social": ds.razao_social, "lancamentos": len(ds.lancamentos)})


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


def criar_servidor(sim: Simulacao, host="127.0.0.1", porta=8765, token: str | None = None) -> ThreadingHTTPServer:
    token = token or secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencioso: o trace é o log
            pass

        def _origem_ok(self) -> bool:
            if _nome_host(self.headers.get("Host")) not in LOOPBACK:
                return False
            origem = self.headers.get("Origin")
            return origem is None or _nome_host(origem) in LOOPBACK

        def _proibido(self, motivo):
            self._responder(*_json(403, {"erro": motivo}))

        def _responder(self, status, cabecalhos, corpo):
            self.send_response(status)
            for k, v in cabecalhos.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            rota = self.path.split("?", 1)[0]
            if not self._origem_ok():
                self._proibido("origem não permitida: use http://127.0.0.1 ou http://localhost")
            elif rota == "/api/sessao":
                self._responder(*_json(200, {"token": token, "cabecalho": CABECALHO_TOKEN}))
            elif rota == "/api/eventos":
                self._eventos()
            else:
                self._responder(*tratar(sim, "GET", self.path))

        def _ler(self, tamanho: int) -> bytes | None:
            """Lê o corpo com tempo limite: quem declara um tamanho e não envia não prende a thread."""
            self.connection.settimeout(LEITURA_SEGUNDOS)
            try:
                corpo = self.rfile.read(tamanho)
                return corpo if len(corpo) == tamanho else None
            except OSError:
                return None
            finally:
                self.connection.settimeout(None)

        def do_POST(self):
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
            except ValueError:
                tamanho = -1
            recebido = self.headers.get(CABECALHO_TOKEN, "").encode("utf-8", "surrogateescape")
            autorizado = self._origem_ok() and hmac.compare_digest(recebido, token.encode("utf-8"))
            if not autorizado:  # autentica antes de ler: corpo grande sem token nunca é lido
                if 0 < tamanho <= DESCARTE_MAXIMO:
                    self._ler(tamanho)  # descarta o corpo pequeno: responder no meio do envio aborta a conexão
                self.close_connection = True
                motivo = ("origem não permitida: use http://127.0.0.1 ou http://localhost" if not self._origem_ok()
                          else f"token de sessão ausente ou inválido ({CABECALHO_TOKEN}; obtenha em /api/sessao)")
                self._proibido(motivo)
                return
            if tamanho < 0 or tamanho > LIMITE_UPLOAD * 2:
                self.close_connection = True
                self._responder(*_json(413, {"erro": "corpo ausente, inválido ou grande demais"}))
                return
            corpo = self._ler(tamanho)
            if corpo is None:
                self.close_connection = True
                self._responder(*_json(408, {"erro": "corpo incompleto ou enviado devagar demais"}))
                return
            self._responder(*tratar(sim, "POST", self.path, corpo))

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

    servidor = _Servidor((host, porta), Handler)
    servidor.daemon_threads = True
    servidor.token = token
    return servidor


class _Servidor(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        """Navegador que fecha a aba ou cancela um fetch não é erro do servidor: ignora em silêncio."""
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def servir(cenario="expediente_sma", seed=None, porta=8765, ms_por_tick=350, pasta_dados="dados/empresa") -> None:
    sim = Simulacao(cenario, seed, interativo=True, ms_por_tick=ms_por_tick, pasta_dados=pasta_dados)
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

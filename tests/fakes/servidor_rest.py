"""Servidor REST falso em loopback para os testes do conector: cada rota tem um defeito conhecido.

    /ok          200 {"data": [{"id": "A-1", "amount": 10.5}]}
    /negado      401 e ecoa o cabeçalho Authorization no corpo (um servidor mal-educado)
    /quebrado    500 e ecoa a chave recebida
    /lento       dorme mais que o tempo limite do conector
    /invalido    200 com JSON truncado
    /desvio      302 para um host externo (o conector não segue)
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


class ServidorFalso:
    def __init__(self, atraso=3.0):
        self.atraso = atraso
        self.recebidos: list[dict] = []
        fora = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _enviar(self, status, corpo: bytes, extra=None):
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):
                rota = urlsplit(self.path).path
                fora.recebidos.append({"rota": rota, "authorization": self.headers.get("Authorization"),
                                       "query": urlsplit(self.path).query})
                if rota == "/ok":
                    return self._enviar(200, b'{"data": [{"id": "A-1", "amount": 10.5}]}')
                if rota == "/negado":
                    return self._enviar(401, json.dumps({"erro": "token inválido",
                                                         "recebido": self.headers.get("Authorization")}).encode())
                if rota == "/quebrado":
                    return self._enviar(500, json.dumps({"erro": "falhou", "chave": self.headers.get("Authorization")})
                                        .encode())
                if rota == "/lento":
                    time.sleep(fora.atraso)
                    return self._enviar(200, b'{"data": []}')
                if rota == "/invalido":
                    return self._enviar(200, b'{"data": [ {"id": ')
                if rota == "/desvio":
                    return self._enviar(302, b"", {"Location": "http://erp.exemplo.com.br/roubar"})
                return self._enviar(404, b'{"erro": "nao existe"}')

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.servidor.daemon_threads = True
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.servidor.server_address[1]}"

    def parar(self):
        self.servidor.shutdown()
        self.servidor.server_close()

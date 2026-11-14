"""Servidor falso de LLM em loopback, para exercitar o caminho HTTP dos provedores sem rede externa.

Atende os três formatos usados pelo SVC-MOD:

    POST /v1/chat/completions              OpenAI e servidores compatíveis
    POST /v1beta/models/<m>:generateContent Gemini
    POST /v1/messages                      Claude (SDK oficial)

O texto devolvido vem dos mocks do próprio sistema (por padrão `mock-analista`), de modo que
a resposta é uma lista de propostas plausível para o contexto recebido. `modo` simula falhas.
"""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fin_mas.services import provedores as prov

MODOS = ("ok", "429", "500", "lento", "nao_json", "fora_do_formato", "cortada", "recusa")


class ServidorLLM:
    def __init__(self, modo="ok", mock="mock-analista", modelo_servido=None, atraso=1.5):
        self.modo, self.mock, self.modelo_servido, self.atraso = modo, mock, modelo_servido, atraso
        self.pedidos: list[dict] = []  # {"caminho", "cabecalhos", "corpo"}
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                dono.pedidos.append({"caminho": self.path, "cabecalhos": {k.lower(): v for k, v in self.headers.items()},
                                     "corpo": corpo})
                status, resposta = dono._responder(self.path, corpo)
                dados = resposta if isinstance(resposta, bytes) else json.dumps(resposta, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                try:
                    self.wfile.write(dados)
                except OSError:
                    pass  # o cliente desistiu (teste de tempo esgotado)

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._http.daemon_threads = True
        self.porta = self._http.server_address[1]
        self.url = f"http://127.0.0.1:{self.porta}"
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

    def fechar(self):
        self._http.shutdown()
        self._http.server_close()

    # ---- respostas ---------------------------------------------------------
    def _texto(self, sistema, prompt):
        return prov.MOCKS[self.mock](prov.PedidoLLM(sistema, prompt, 1000, texto_base=prompt.split("Relatório:\n")[-1]))

    def _responder(self, caminho, corpo):
        if self.modo == "429":
            return 429, {"error": {"message": "rate limit; Authorization: Bearer sk-vazou-no-erro-1234567890"}}
        if self.modo == "500":
            return 500, {"error": {"message": "erro interno"}}
        if self.modo == "lento":
            time.sleep(self.atraso)
        if self.modo == "nao_json":
            return 200, b"<html>gateway</html>"
        if self.modo == "fora_do_formato":
            return 200, {"ok": True}
        if "/chat/completions" in caminho:
            return 200, self._openai(corpo)
        if ":generateContent" in caminho:
            return 200, self._gemini(caminho, corpo)
        if "/messages" in caminho:
            return 200, self._anthropic(corpo)
        return 404, {"error": {"message": f"rota desconhecida: {caminho}"}}

    def _openai(self, corpo):
        sistema, prompt = corpo["messages"][0]["content"], corpo["messages"][1]["content"]
        mensagem = {"role": "assistant", "content": self._texto(sistema, prompt)}
        fim = {"cortada": "length", "recusa": "content_filter"}.get(self.modo, "stop")
        return {"id": "chatcmpl-falso", "object": "chat.completion", "model": self.modelo_servido or corpo["model"],
                "choices": [{"index": 0, "message": mensagem, "finish_reason": fim}],
                "usage": {"prompt_tokens": 321, "completion_tokens": 45, "total_tokens": 366}}

    def _gemini(self, caminho, corpo):
        sistema = corpo["systemInstruction"]["parts"][0]["text"]
        prompt = corpo["contents"][0]["parts"][0]["text"]
        fim = {"cortada": "MAX_TOKENS", "recusa": "SAFETY"}.get(self.modo, "STOP")
        modelo = caminho.split("/models/")[1].split(":")[0]
        return {"candidates": [{"content": {"role": "model", "parts": [{"text": self._texto(sistema, prompt)}]},
                                "finishReason": fim}],
                "usageMetadata": {"promptTokenCount": 300, "candidatesTokenCount": 40, "thoughtsTokenCount": 12,
                                  "totalTokenCount": 352},
                "modelVersion": self.modelo_servido or modelo}

    def _anthropic(self, corpo):
        prompt = corpo["messages"][0]["content"]
        fim = {"cortada": "max_tokens", "recusa": "refusal"}.get(self.modo, "end_turn")
        return {"id": "msg_falso", "type": "message", "role": "assistant", "model": self.modelo_servido or corpo["model"],
                "content": [{"type": "text", "text": self._texto(corpo.get("system", ""), prompt)}],
                "stop_reason": fim, "stop_sequence": None,
                "usage": {"input_tokens": 410, "output_tokens": 52}}

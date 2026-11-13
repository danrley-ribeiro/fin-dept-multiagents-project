"""Cliente MCP por stdio (JSON-RPC 2.0, linha a linha) e o conector sobre ele.

O cliente inicia o processo do servidor, faz `initialize`, lista as tools (`tools/list`) e chama
tools (`tools/call`). Exercitado contra o servidor MCP de Excel do próprio sistema
(`python -m fin_mas mcp-excel --pasta ...`), mas não depende dele: qualquer servidor MCP por
stdio serve. Só o dono da máquina (CLI ou código) escolhe o comando; pelo dashboard só se
cadastra o servidor de Excel embutido, sobre uma pasta da área de dados (ver `fontes/registro.py`).

Configuração do conector:

    {"comando": ["python", "-m", "fin_mas", "mcp-excel", "--pasta", "dados/planilhas"],
     "recursos": {"Lancamentos": {"tool": "ler_aba",
                                  "argumentos": {"arquivo": "fechamento.xlsx", "aba": "Lancamentos", "limite": 1000},
                                  "raiz": "linhas"}},
     "competencia": "2026-09"}

A resposta de uma tool é `content[0].text` com JSON; `raiz` aponta a lista de registros.
"""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

from fin_mas.conectores.base import (ConectorMapeado, ErroConector, FonteIndisponivel, RespostaInvalida,
                                     diagnostico, etapa)
from fin_mas.conectores.rest import raiz_de

PROTOCOLO = "2024-11-05"
TEMPO_LIMITE = 20.0


def comando_excel(pasta) -> list[str]:
    """Comando do servidor MCP de Excel embutido, com o mesmo Python deste processo."""
    return [sys.executable, "-m", "fin_mas", "mcp-excel", "--pasta", str(pasta)]


class ClienteMCP:
    def __init__(self, comando: list[str], tempo_limite: float = TEMPO_LIMITE, cwd=None):
        self.comando, self.tempo_limite, self.cwd = list(comando), tempo_limite, cwd
        self._proc = None
        self._seq = 0
        self._saida: queue.Queue = queue.Queue()

    def __enter__(self):
        self.abrir()
        return self

    def __exit__(self, *exc):
        self.fechar()

    def abrir(self) -> dict:
        env = dict(os.environ)
        pacote = str(Path(__file__).resolve().parents[2])  # src/: o servidor embutido acha o pacote
        env["PYTHONPATH"] = pacote + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env.setdefault("PYTHONUTF8", "1")
        try:
            self._proc = subprocess.Popen(self.comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=subprocess.DEVNULL, cwd=self.cwd, env=env, text=True,
                                          encoding="utf-8", bufsize=1)
        except OSError as e:
            raise FonteIndisponivel(f"não foi possível iniciar o servidor MCP: {type(e).__name__}") from None
        threading.Thread(target=self._ler, daemon=True).start()
        info = self.chamar("initialize", {"protocolVersion": PROTOCOLO, "capabilities": {},
                                          "clientInfo": {"name": "fin-mas-conector", "version": "1"}})
        self._enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return info

    def _ler(self):
        for linha in self._proc.stdout:
            self._saida.put(linha)
        self._saida.put(None)

    def _enviar(self, mensagem: dict) -> None:
        try:
            self._proc.stdin.write(json.dumps(mensagem, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            raise FonteIndisponivel("o servidor MCP encerrou a conexão") from None

    def chamar(self, metodo: str, params: dict | None = None):
        self._seq += 1
        rid = self._seq
        self._enviar({"jsonrpc": "2.0", "id": rid, "method": metodo, "params": params or {}})
        while True:
            try:
                linha = self._saida.get(timeout=self.tempo_limite)
            except queue.Empty:
                raise FonteIndisponivel(f"servidor MCP sem resposta a {metodo} ({self.tempo_limite:g} s)") from None
            if linha is None:
                raise FonteIndisponivel("o servidor MCP encerrou antes de responder")
            try:
                resposta = json.loads(linha)
            except ValueError:
                raise RespostaInvalida("o servidor MCP respondeu fora do JSON-RPC") from None
            if resposta.get("id") != rid:
                continue  # notificação ou resposta atrasada
            if "error" in resposta:
                raise RespostaInvalida(f"MCP {metodo}: {resposta['error'].get('message')}")
            return resposta.get("result")

    def tools(self) -> list[dict]:
        return (self.chamar("tools/list") or {}).get("tools", [])

    def tool(self, nome: str, argumentos: dict | None = None):
        r = self.chamar("tools/call", {"name": nome, "arguments": argumentos or {}}) or {}
        texto = "".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")
        if r.get("isError"):
            raise RespostaInvalida(f"tool {nome}: {texto[:300]}")
        try:
            return json.loads(texto)
        except ValueError:
            return texto

    def fechar(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=5)
        self._proc = None


class ConectorMCP(ConectorMapeado):
    tipo = "mcp"

    def __init__(self, id: str, config: dict, mapeamento: dict | None = None):
        super().__init__(id, mapeamento, porte=config.get("porte"))
        self.config = config
        if not isinstance(config.get("comando"), list) or not config["comando"]:
            raise ValueError("informe o comando do servidor MCP (lista de argumentos)")

    def competencia_padrao(self):
        return self.config.get("competencia")

    def capacidades(self) -> set:
        return {"leitura"}

    def cliente(self) -> ClienteMCP:
        return ClienteMCP(self.config["comando"], float(self.config.get("tempo_limite") or TEMPO_LIMITE))

    def descricao(self) -> dict:
        return {**super().descricao(), "recursos": sorted(self.config.get("recursos") or {})}

    def ler(self, competencia):
        with self.cliente() as c:
            self._aberto = c
            try:
                return super().ler(competencia)
            finally:
                self._aberto = None

    def ler_recurso(self, recurso: str, competencia) -> list[dict]:
        spec = (self.config.get("recursos") or {}).get(recurso)
        if spec is None:
            raise RespostaInvalida(f"recurso não configurado: {recurso}")
        args = {k: (v.replace("{competencia}", competencia or "") if isinstance(v, str) else v)
                for k, v in (spec.get("argumentos") or {}).items()}
        cliente = getattr(self, "_aberto", None)
        if cliente is None:
            with self.cliente() as c:
                return raiz_de(c.tool(spec["tool"], args), spec.get("raiz"))
        return raiz_de(cliente.tool(spec["tool"], args), spec.get("raiz"))

    def uri(self, recurso: str) -> str:
        spec = (self.config.get("recursos") or {}).get(recurso) or {}
        aba = (spec.get("argumentos") or {}).get("aba")
        return f"mcp://{self.id}/{spec.get('tool', recurso)}" + (f"#{aba}" if aba else "")

    def testar(self) -> dict:
        etapas = []
        try:
            with self.cliente() as c:
                etapas.append(etapa("iniciar servidor", True, "initialize respondido"))
                tools = c.tools()
                etapas.append(etapa("listar tools", True, ", ".join(t["name"] for t in tools)))
                for nome, spec in sorted((self.config.get("recursos") or {}).items()):
                    try:
                        n = len(raiz_de(c.tool(spec["tool"], spec.get("argumentos")), spec.get("raiz")))
                        etapas.append(etapa(f"recurso {nome}", True, f"{n} registro(s)"))
                    except ErroConector as e:
                        etapas.append(etapa(f"recurso {nome}", False, str(e)))
        except ErroConector as e:
            etapas.append(etapa("servidor MCP", False, str(e)))
        return diagnostico(etapas)

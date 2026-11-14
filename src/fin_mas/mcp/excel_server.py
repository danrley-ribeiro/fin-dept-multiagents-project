"""Servidor MCP de Excel (stdio, JSON-RPC 2.0) sobre a pasta de planilhas da empresa sem ERP.

    python -m fin_mas mcp-excel --pasta dados/empresa

Expõe a mesma leitura validada que os agentes usam (`fontes/planilha.py`), para qualquer
cliente MCP (por exemplo, um assistente que precise ler os modelos preenchidos). Só lê
arquivos dentro da pasta configurada; a única escrita é criar um modelo em branco novo,
nunca sobrescrever planilha existente.

Configuração de cliente (exemplo):
    {"mcpServers": {"sma-excel": {"command": "python", "args": ["-m", "fin_mas", "mcp-excel",
                                                                 "--pasta", "C:/dados/empresa"]}}}
"""
import json
import sys
from pathlib import Path

from fin_mas import __version__
from fin_mas.fontes import planilha
from fin_mas.env.portes import PORTES, perfil

PROTOCOLO = "2024-11-05"

FERRAMENTAS = [
    {"name": "listar_planilhas", "description": "Lista as planilhas .xlsx da pasta e se cada uma é um modelo válido.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "ler_aba", "description": "Lê as linhas de uma aba de uma planilha da pasta.",
     "inputSchema": {"type": "object", "required": ["arquivo", "aba"], "properties": {
         "arquivo": {"type": "string"}, "aba": {"type": "string", "enum": ["Empresa", *planilha.ABAS]},
         "limite": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100}}}},
    {"name": "validar_planilha", "description": "Valida o modelo (abas, colunas, tipos e referências) e lista os erros.",
     "inputSchema": {"type": "object", "required": ["arquivo"], "properties": {"arquivo": {"type": "string"}}}},
    {"name": "resumo_empresa",
     "description": "Empresa, porte e regras do porte (alçadas, materialidade, severidades) e totais do mês.",
     "inputSchema": {"type": "object", "required": ["arquivo"], "properties": {"arquivo": {"type": "string"}}}},
    {"name": "criar_modelo_em_branco", "description": "Cria um modelo em branco na pasta (não sobrescreve).",
     "inputSchema": {"type": "object", "required": ["arquivo"], "properties": {"arquivo": {"type": "string"}}}},
]


class ServidorExcel:
    def __init__(self, pasta):
        self.pasta = Path(pasta).resolve()
        self.pasta.mkdir(parents=True, exist_ok=True)

    def _arquivo(self, nome: str) -> Path:
        alvo = (self.pasta / nome).resolve()
        if self.pasta not in alvo.parents or alvo.suffix.lower() != ".xlsx":
            raise PermissionError(f"arquivo fora da pasta permitida ou não .xlsx: {nome}")
        return alvo

    # ---- ferramentas -------------------------------------------------------
    def listar_planilhas(self):
        itens = []
        for p in sorted(self.pasta.glob("*.xlsx")):
            if p.name.startswith("~$"):
                continue
            try:
                planilha.ler(p)
                valido, erros = True, []
            except planilha.ModeloInvalido as e:
                valido, erros = False, e.erros[:3]
            itens.append({"arquivo": p.name, "bytes": p.stat().st_size, "valido": valido, "erros": erros})
        return {"pasta": str(self.pasta), "planilhas": itens}

    def ler_aba(self, arquivo, aba, limite=100):
        abas = planilha.ler_abas(self._existente(arquivo))
        if aba not in abas:
            raise KeyError(f"aba inexistente: {aba} (há {', '.join(abas)})")
        linhas = abas[aba]
        return {"arquivo": arquivo, "aba": aba, "total": len(linhas), "linhas": _json(linhas[:limite]),
                "proveniencia": f"mcp://excel/{arquivo}#{aba}"}

    def validar_planilha(self, arquivo):
        try:
            ds = planilha.ler(self._existente(arquivo))
        except planilha.ModeloInvalido as e:
            return {"ok": False, "erros": e.erros}
        return {"ok": True, "erros": [], "porte": ds.porte, "competencia": ds.competencia,
                "lancamentos": len(ds.lancamentos)}

    def resumo_empresa(self, arquivo):
        ds = planilha.ler(self._existente(arquivo))
        p = perfil(ds.porte)
        receita = sum(x["preco"] * x["qtd"] for x in ds.produtos)
        return {"razao_social": ds.razao_social, "sigla": ds.entidade, "competencia": ds.competencia,
                "porte": ds.porte, "porte_titulo": p["titulo"], "norma_contabil": p["norma_contabil"],
                "tem_erp": ds.tem_erp, "limites_alcada_centavos": p["limites_alcada"],
                "limiar_desvio": p["limiar_desvio"], "severidade": p["severidade"],
                "receita_mes_centavos": receita, "lancamentos_ativos": len(ds.lancamentos),
                "versao_normas": p["versao"]}

    def criar_modelo_em_branco(self, arquivo):
        alvo = self._arquivo(arquivo)
        if alvo.exists():
            raise FileExistsError(f"{arquivo} já existe: o servidor não sobrescreve planilhas")
        planilha.gerar_modelo(alvo)
        return {"criado": arquivo, "portes": list(PORTES)}

    def _existente(self, arquivo) -> Path:
        alvo = self._arquivo(arquivo)
        if not alvo.exists():
            raise FileNotFoundError(f"{arquivo} não está na pasta")
        return alvo

    # ---- JSON-RPC -----------------------------------------------------------
    def tratar(self, req) -> dict | None:
        if not isinstance(req, dict):  # null, número, texto ou lote: requisição inválida, responde e segue
            return _erro(None, -32600, "requisição inválida: esperado um objeto JSON-RPC")
        metodo, rid = req.get("method"), req.get("id")
        if rid is None:  # notificação (ex.: notifications/initialized): sem resposta
            return None
        try:
            if metodo == "initialize":
                resultado = {"protocolVersion": PROTOCOLO, "capabilities": {"tools": {}},
                             "serverInfo": {"name": "sma-excel", "version": __version__}}
            elif metodo == "ping":
                resultado = {}
            elif metodo == "tools/list":
                resultado = {"tools": FERRAMENTAS}
            elif metodo == "tools/call":
                params = req.get("params") or {}
                if not isinstance(params, dict) or not isinstance(params.get("arguments") or {}, dict):
                    return _erro(rid, -32602, "params e arguments precisam ser objetos")
                nome, args = params.get("name"), params.get("arguments") or {}
                if nome not in {f["name"] for f in FERRAMENTAS}:
                    return _erro(rid, -32602, f"ferramenta desconhecida: {nome}")
                try:
                    dados = getattr(self, nome)(**args)
                    resultado = {"content": [{"type": "text", "text": json.dumps(dados, ensure_ascii=False)}],
                                 "isError": False}
                except (planilha.ModeloInvalido, PermissionError, FileNotFoundError, FileExistsError, KeyError,
                        TypeError, ValueError) as e:
                    resultado = {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
            else:
                return _erro(rid, -32601, f"método não suportado: {metodo}")
        except Exception as e:  # nunca derruba o servidor
            return _erro(rid, -32603, str(e))
        return {"jsonrpc": "2.0", "id": rid, "result": resultado}

    def servir(self, entrada=sys.stdin, saida=sys.stdout) -> None:
        for linha in entrada:
            if not linha.strip():
                continue
            try:
                req = json.loads(linha)
            except (ValueError, RecursionError):  # inclusive JSON aninhado demais: responde e segue
                resposta = _erro(None, -32700, "JSON inválido")
            else:
                try:
                    resposta = self.tratar(req)
                except Exception as e:  # nenhuma requisição derruba o servidor
                    resposta = _erro(None, -32603, f"{type(e).__name__}")
            if resposta is not None:
                saida.write(json.dumps(resposta, ensure_ascii=False) + "\n")
                saida.flush()


def _erro(rid, codigo, mensagem):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": codigo, "message": mensagem}}


def _json(linhas):
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in linha.items()} for linha in linhas]

"""Servidores MCP mock (somente leitura) sobre o dataset sintético (ADR-004).

Cada tool devolve {"dados", "proveniencia"}. Uma allowlist por agente nega,
fail-closed, qualquer tool que o papel não tenha (NORM-02). Toda chamada é auditada.
"""
from fin_mas.env.dataset import LIMITES_ALCADA, SEVERIDADE, USUARIOS, Dataset

ALLOWLIST = {
    "AG-CUS": {"erp.balancete"},
    "AG-ORC": {"planilhas.orcamento"},
    "AG-RES": {"erp.balancete"},
    "AG-CIN": {"erp.lancamentos", "normas.alcadas", "normas.regras"},
}


class ToolDenied(PermissionError):
    """Tool fora da allowlist do papel solicitante."""


class MCPGateway:
    def __init__(self, dataset: Dataset, audit, bus):
        self.ds = dataset
        self.audit = audit
        self.bus = bus

    def call(self, agente: str, tool: str, conversation_id: str, **args):
        if tool not in ALLOWLIST.get(agente, set()):
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool)
            raise ToolDenied(f"{agente} não pode chamar {tool}")
        consulta = {"entidade": self.ds.entidade, "competencia": self.ds.competencia, **args}
        dados = getattr(self, "_" + tool.replace(".", "_"))()
        proveniencia = {"fonte": f"mcp://{tool.replace('.', '/')}", "consulta": consulta, "seed": self.ds.seed}
        self.audit.record(
            self.bus.now, "mcp_call", conversation_id=conversation_id, agente=agente, tool=tool, consulta=consulta,
        )
        return {"dados": dados, "proveniencia": proveniencia}

    def _erp_balancete(self):
        return {
            "produtos": [dict(p) for p in self.ds.produtos],
            "custos_fixos": [dict(c) for c in self.ds.custos_fixos],
        }

    def _erp_lancamentos(self):
        return [dict(lanc) for lanc in self.ds.lancamentos]

    def _planilhas_orcamento(self):
        return {
            "meses_decorridos": self.ds.gold["meses_decorridos"],
            "contas": [dict(c) for c in self.ds.orcamento],
        }

    def _normas_alcadas(self):
        return {"limites": dict(LIMITES_ALCADA), "cargos": dict(USUARIOS)}

    def _normas_regras(self):
        return {"severidade": dict(SEVERIDADE), "versao": "normas-v1"}

"""Servidores MCP mock (somente leitura) sobre o dataset sintético (ADR-004).

Cada tool devolve {"dados", "proveniencia"}. Uma allowlist por agente nega,
fail-closed, qualquer tool que o papel não tenha (NORM-02). Toda chamada é auditada.
"""
from fin_mas.env.dataset import LIMITES_ALCADA, SEVERIDADE, USUARIOS, Ambiente, Dataset

ALLOWLIST = {
    "AG-CUS": {"erp.balancete"},
    "AG-ORC": {"planilhas.orcamento", "erp.realizado_por_conta"},
    "AG-RES": {"erp.balancete"},
    "AG-CIN": {"erp.lancamentos", "normas.alcadas", "normas.regras"},
}


class ToolDenied(PermissionError):
    """Tool fora da allowlist do papel solicitante."""


class MCPGateway:
    def __init__(self, ambiente: Ambiente | Dataset, audit, bus):
        self.ambiente = Ambiente.de_dataset(ambiente) if isinstance(ambiente, Dataset) else ambiente
        self.audit = audit
        self.bus = bus

    @property
    def ds(self) -> Dataset:
        return self.ambiente.dataset()

    def call(self, agente: str, tool: str, conversation_id: str, competencia: str | None = None, **args):
        if tool not in ALLOWLIST.get(agente, set()):
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool)
            raise ToolDenied(f"{agente} não pode chamar {tool}")
        ds = self.ambiente.dataset(competencia)
        consulta = {"entidade": ds.entidade, "competencia": ds.competencia, **args}
        dados = getattr(self, "_" + tool.replace(".", "_"))(ds)
        proveniencia = {"fonte": f"mcp://{tool.replace('.', '/')}", "consulta": consulta, "seed": ds.seed}
        self.audit.record(
            self.bus.now, "mcp_call", conversation_id=conversation_id, agente=agente, tool=tool, consulta=consulta,
        )
        return {"dados": dados, "proveniencia": proveniencia}

    def _erp_balancete(self, ds):
        return {
            "produtos": [dict(p) for p in ds.produtos],
            "custos_fixos": [dict(c) for c in ds.custos_fixos],
        }

    def _erp_lancamentos(self, ds):
        return [dict(lanc) for lanc in ds.lancamentos]

    def _planilhas_orcamento(self, ds):
        return {
            "meses_decorridos": ds.gold["meses_decorridos"],
            "contas": [dict(c) for c in ds.orcamento],
        }

    def _normas_alcadas(self, ds):
        return {"limites": dict(LIMITES_ALCADA), "cargos": dict(USUARIOS)}

    def _normas_regras(self, ds):
        return {"severidade": dict(SEVERIDADE), "versao": "normas-v1"}

    def _erp_realizado_por_conta(self, ds):
        return {"meses_decorridos": ds.gold["meses_decorridos"], "realizado": dict(ds.realizado_erp)}

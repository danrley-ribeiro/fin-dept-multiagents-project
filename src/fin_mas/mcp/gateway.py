"""Servidores MCP (somente leitura) sobre a fonte de dados da empresa (ADR-004).

A fonte é o dataset sintético (por porte) ou a planilha preenchida de uma empresa sem ERP
(`fontes/planilha.py`, a mesma lida pelo servidor MCP de Excel). Cada tool devolve
{"dados", "proveniencia"}; a allowlist por agente nega, fail-closed, o que o papel não tem
(NORM-02). Empresa sem ERP não tem `erp.realizado_por_conta`: a tool falha explicitamente e
o agente segue com a planilha. Toda chamada é auditada.
"""
from fin_mas.env.dataset import Ambiente, Dataset

ALLOWLIST = {
    "AG-CUS": {"erp.balancete"},
    "AG-ORC": {"planilhas.orcamento", "erp.realizado_por_conta", "normas.perfil"},
    "AG-RES": {"erp.balancete"},
    "AG-CIN": {"erp.lancamentos", "normas.alcadas", "normas.regras", "normas.perfil"},
}
ABA = {"erp.balancete": "Produtos+CustosFixos", "erp.lancamentos": "Lancamentos", "planilhas.orcamento": "Orcamento",
       "erp.realizado_por_conta": "Orcamento"}


class ToolDenied(PermissionError):
    """Tool fora da allowlist do papel solicitante."""


class ToolIndisponivel(LookupError):
    """A fonte da empresa não oferece esta tool (ex.: empresa sem ERP)."""


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
        if tool == "erp.realizado_por_conta" and not ds.perfil["tem_erp"]:
            self.audit.record(self.bus.now, "mcp_denied", conversation_id=conversation_id, agente=agente, tool=tool,
                              motivo="empresa sem ERP")
            raise ToolIndisponivel("empresa sem ERP: o realizado vem só da planilha")
        dados = getattr(self, "_" + tool.replace(".", "_"))(ds)
        proveniencia = {"fonte": self._fonte(ds, tool), "consulta": consulta, "seed": ds.seed}
        self.audit.record(self.bus.now, "mcp_call", conversation_id=conversation_id, agente=agente, tool=tool,
                          consulta=consulta, fonte=proveniencia["fonte"])
        return {"dados": dados, "proveniencia": proveniencia}

    @staticmethod
    def _fonte(ds, tool) -> str:
        if hasattr(ds, "proveniencia") and tool in ABA:  # planilha real de empresa sem ERP
            return ds.proveniencia(ABA[tool])
        if tool.startswith("erp.") and not ds.perfil["tem_erp"]:
            return f"mcp://excel/{ABA[tool]}"  # empresa sintética sem ERP: dados vêm de planilhas
        return f"mcp://{tool.replace('.', '/')}"

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
        p = ds.perfil
        return {"limites": dict(p["limites_alcada"]), "cargos": dict(p["pessoas"]),  # None = sem limite
                "aprovadores": list(p["aprovadores"])}

    def _normas_regras(self, ds):
        return {"severidade": dict(ds.perfil["severidade"]), "versao": ds.perfil["versao"],
                "controle_compensatorio": dict(ds.perfil["controle_compensatorio"])}

    def _normas_perfil(self, ds):
        p = ds.perfil
        return {k: p[k] for k in ("porte", "titulo", "norma_contabil", "tem_erp", "fonte_primaria", "limiar_desvio",
                                  "pesos_cin", "pesos_orc", "max_ciclos_correcao", "versao")}

    def _erp_realizado_por_conta(self, ds):
        return {"meses_decorridos": ds.gold["meses_decorridos"], "realizado": dict(ds.realizado_erp)}

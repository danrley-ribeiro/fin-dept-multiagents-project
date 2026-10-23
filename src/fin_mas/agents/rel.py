"""AG-REL — Agente de Relatórios: relatório executivo por template determinístico.

Nesta entrega só existe o modo template; o LLM opcional (ADR-002) fica para a DSM3.
Todo número do texto vem do conteúdo recebido, nunca é calculado aqui.
"""
from fin_mas.agents.base import Specialist
from fin_mas.env.dataset import brl

VERSAO_TEMPLATE = "tpl-exec-v1"


class AgenteRelatorios(Specialist):
    def __init__(self, bus, gateway):
        super().__init__("AG-REL", bus, gateway)
        self.conhecimento = {"templates": {"relatorio_executivo": VERSAO_TEMPLATE,
                                           "relatorio_orcamentario": VERSAO_TEMPLATE}}
        self.estado = {"rascunho": None}

    def executar(self, tarefa, content, conversation_id):
        if tarefa not in self.conhecimento["templates"]:
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        linhas = getattr(self, "_" + tarefa)(content)
        for ressalva in content.get("ressalvas", []):
            linhas.append(f"Ressalva: {ressalva}")
        texto = "\n".join(linhas)
        self.estado["rascunho"] = texto
        self.decide(conversation_id, "relatório por template determinístico",
                    {"tarefa": tarefa, "ressalvas": len(content.get("ressalvas", []))}, VERSAO_TEMPLATE)
        return {"texto": texto, "modo": "template", "versao_template": VERSAO_TEMPLATE}

    def _relatorio_executivo(self, c):
        dre, kpis = c["dre"], c["kpis"]
        linhas = [
            f"Relatório executivo — {c['entidade']} — {c['competencia']}",
            f"Receita: {brl(dre['receita'])}",
            f"Margem de contribuição: {brl(dre['margem_contribuicao'])} ({kpis['margem_contribuicao_pct']}%)",
            f"Custos fixos: {brl(dre['custos_fixos'])}",
            f"EBITDA: {brl(dre['ebitda'])} ({kpis['ebitda_pct']}%)",
        ]
        for un, r in sorted(c["resultado_un"].items()):
            linhas.append(f"Resultado {un}: {brl(r['resultado'])}")
        linhas.append(f"Parecer de conformidade: {c['parecer']}")
        return linhas

    def _relatorio_orcamentario(self, c):
        t = c["totais"]
        linhas = [
            f"Relatório orçamentário — {c['entidade']} — {c['competencia']}",
            f"Orçado acumulado: {brl(t['orcado_acumulado'])}",
            f"Realizado acumulado: {brl(t['realizado_acumulado'])}",
            f"Forecast do trimestre: {brl(t['forecast_trimestre'])}",
        ]
        if c["sinalizadas"]:
            linhas.append("Desvios acima do limiar: " + ", ".join(c["sinalizadas"]))
        else:
            linhas.append("Nenhum desvio acima do limiar.")
        return linhas

"""AG-REL — Agente de Relatórios: relatório executivo por template determinístico.

Todo número do texto vem do conteúdo recebido, nunca é calculado aqui. DSM3: com a flag
do SVC-MOD ligada, um LLM acrescenta uma síntese no topo; o texto é validado contra o
template (NORM-05) e, se reprovado, só o template é entregue (ADR-002).
"""
from fin_mas.agents.base import Specialist
from fin_mas.env.dataset import brl
from fin_mas.env.empresa import EMPRESA

VERSAO_TEMPLATE = "tpl-exec-v2"  # v2: cabeçalho da SMA, notas de correção e desvios atribuídos


class AgenteRelatorios(Specialist):
    PAPEL = "ROLE-REL"
    def __init__(self, bus, gateway):
        super().__init__("AG-REL", bus, gateway)
        self.conhecimento = {"templates": {"relatorio_executivo": VERSAO_TEMPLATE,
                                           "relatorio_orcamentario": VERSAO_TEMPLATE}}
        self.estado = {"rascunho": None}
        self.modelos = None  # SVC-MOD (services/modelos.py); None = só template

    def executar(self, tarefa, content, conversation_id):
        if tarefa not in self.conhecimento["templates"]:
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        linhas = getattr(self, "_" + tarefa)(content)
        for insight in content.get("insights", []):  # hipóteses verificadas dos especialistas (ADR-008)
            linhas.append(f"Insight: {insight}")
        for ressalva in content.get("ressalvas", []):
            linhas.append(f"Ressalva: {ressalva}")
        for nota in content.get("notas", []):
            linhas.append(f"Nota: {nota}")
        texto = "\n".join(linhas)
        sintese = self.modelos.gerar(self.id, conversation_id, tarefa, texto) if self.modelos else None
        modo = "template"
        if sintese:
            modelo = self.modelos.config(self.id)["modelo"]
            texto, modo = f"{sintese}\n(síntese gerada por {modelo}; números conferidos com o template)\n\n{texto}", \
                "template+llm"
        self.estado["rascunho"] = texto
        self.decide(conversation_id, "relatório por template determinístico" + (" com síntese validada" if sintese else ""),
                    {"tarefa": tarefa, "ressalvas": len(content.get("ressalvas", []))}, VERSAO_TEMPLATE)
        return {"texto": texto, "modo": modo, "versao_template": VERSAO_TEMPLATE}

    def _relatorio_executivo(self, c):
        dre, kpis = c["dre"], c["kpis"]
        linhas = [
            EMPRESA["razao_social"],
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
            EMPRESA["razao_social"],
            f"Relatório orçamentário — {c['entidade']} — {c['competencia']}",
            f"Orçado acumulado: {brl(t['orcado_acumulado'])}",
            f"Realizado acumulado: {brl(t['realizado_acumulado'])}",
            f"Forecast do trimestre: {brl(t['forecast_trimestre'])}",
        ]
        if c["sinalizadas"]:
            linhas.append("Desvios acima do limiar: " + ", ".join(c["sinalizadas"]))
        else:
            linhas.append("Nenhum desvio acima do limiar.")
        if c.get("atribuidas_a_controle"):
            linhas.append("Desvios atribuídos a lançamentos irregulares: " + ", ".join(c["atribuidas_a_controle"]))
        return linhas

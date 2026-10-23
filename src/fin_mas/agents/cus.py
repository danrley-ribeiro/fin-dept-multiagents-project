"""AG-CUS — Agente de Custos: margem de contribuição e rentabilidade por produto e UN."""
from fin_mas.agents.base import Specialist
from fin_mas.env.dataset import RATEIO, VERSAO_RATEIO, ratear


class AgenteCustos(Specialist):
    def __init__(self, bus, gateway):
        super().__init__("AG-CUS", bus, gateway)
        self.conhecimento = {"rateio": dict(RATEIO), "versao_rateio": VERSAO_RATEIO}
        self.estado = {"custos": None, "pendencias": []}

    def executar(self, tarefa, content, conversation_id):
        if tarefa != "apurar_custos":
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        return self._apurar(conversation_id)

    def consultar(self, assunto, content, conversation_id):
        if assunto != "custos_por_UN":
            raise KeyError(assunto)
        custos = self.estado["custos"] or self._apurar(conversation_id)
        return {"resultado_un": custos["resultado_un"], "totais": custos["totais"],
                "proveniencia": custos["proveniencia"]}

    def _apurar(self, conversation_id):
        resposta = self.gw.call(self.id, "erp.balancete", conversation_id)
        dados = resposta["dados"]
        if not dados["produtos"]:
            self.estado["pendencias"].append("balancete sem produtos")
            raise ValueError("dado de origem ausente: balancete sem produtos")
        margens = {}
        for p in dados["produtos"]:
            receita, cv = p["preco"] * p["qtd"], p["custo_variavel_unit"] * p["qtd"]
            margens[p["id"]] = {"receita": receita, "custo_variavel": cv, "margem": receita - cv}
        fixo_total = sum(c["valor"] for c in dados["custos_fixos"])
        fixo_un = ratear(fixo_total, self.conhecimento["rateio"])
        resultado_un = {}
        for un in self.conhecimento["rateio"]:
            margem = sum(margens[p["id"]]["margem"] for p in dados["produtos"] if p["un"] == un)
            resultado_un[un] = {"margem": margem, "custo_fixo_rateado": fixo_un[un],
                                "resultado": margem - fixo_un[un]}
        receita = sum(m["receita"] for m in margens.values())
        cv = sum(m["custo_variavel"] for m in margens.values())
        custos = {
            "margens_produto": margens, "resultado_un": resultado_un,
            "totais": {"receita": receita, "custos_variaveis": cv, "margem_contribuicao": receita - cv,
                       "custos_fixos": fixo_total},
            "proveniencia": {**resposta["proveniencia"], "versao_rateio": self.conhecimento["versao_rateio"]},
        }
        self.estado["custos"] = custos
        self.decide(conversation_id, "margem = receita - custo variável; rateio fixo por UN",
                    {"produtos": len(margens), "versao_rateio": self.conhecimento["versao_rateio"]},
                    custos["totais"])
        return custos

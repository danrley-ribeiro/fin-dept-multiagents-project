"""AG-ORC — Agente de Orçamento: orçado x realizado, desvios acima do limiar e forecast."""
from fin_mas.agents.base import Specialist
from fin_mas.env.dataset import LIMIAR_ABSOLUTO, LIMIAR_PERCENTUAL


class AgenteOrcamento(Specialist):
    def __init__(self, bus, gateway):
        super().__init__("AG-ORC", bus, gateway)
        self.conhecimento = {
            "limiar_percentual": LIMIAR_PERCENTUAL,
            "limiar_absoluto": LIMIAR_ABSOLUTO,
            "metodo_forecast": "run-rate: realizado acumulado x 3 / meses decorridos",
        }
        self.estado = {"avaliacao": None}

    def executar(self, tarefa, content, conversation_id):
        if tarefa != "orcado_x_realizado":
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        return self._avaliar(conversation_id)

    def consultar(self, assunto, content, conversation_id):
        if assunto != "desvios":
            raise KeyError(assunto)
        avaliacao = self.estado["avaliacao"] or self._avaliar(conversation_id)
        return {"desvios": avaliacao["desvios"], "totais": avaliacao["totais"],
                "proveniencia": avaliacao["proveniencia"]}

    def _avaliar(self, conversation_id):
        resposta = self.gw.call(self.id, "planilhas.orcamento", conversation_id)
        meses = resposta["dados"]["meses_decorridos"]
        pct, absoluto = self.conhecimento["limiar_percentual"], self.conhecimento["limiar_absoluto"]
        contas, sinalizadas = [], []
        for c in resposta["dados"]["contas"]:
            desvio = c["realizado_acumulado"] - c["orcado_acumulado"]
            acima = abs(desvio) * 100 >= c["orcado_acumulado"] * pct and abs(desvio) >= absoluto
            forecast = (c["realizado_acumulado"] * 3 + meses // 2) // meses
            contas.append({
                "conta": c["conta"], "orcado_acumulado": c["orcado_acumulado"],
                "realizado_acumulado": c["realizado_acumulado"], "desvio": desvio,
                "sinalizado": acima, "forecast_trimestre": forecast,
            })
            if acima:
                sinalizadas.append(c["conta"])
                self.decide(conversation_id, f"desvio >= {pct}% e >= {absoluto} centavos",
                            {"conta": c["conta"], "desvio": desvio}, "sinalizado")
        avaliacao = {
            "desvios": contas, "sinalizadas": sorted(sinalizadas),
            "totais": {"orcado_acumulado": sum(c["orcado_acumulado"] for c in contas),
                       "realizado_acumulado": sum(c["realizado_acumulado"] for c in contas),
                       "forecast_trimestre": sum(c["forecast_trimestre"] for c in contas)},
            "metodo_forecast": self.conhecimento["metodo_forecast"],
            "proveniencia": resposta["proveniencia"],
        }
        self.estado["avaliacao"] = avaliacao
        return avaliacao

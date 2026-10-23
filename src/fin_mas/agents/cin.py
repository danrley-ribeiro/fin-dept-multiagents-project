"""AG-CIN — Agente de Controles Internos: parecer e veto por regras simbólicas (BDI).

Crenças: conformidade de cada lançamento. Intenção: aprovar, apontar ou vetar.
O veto muda o espaço de opções do Orquestrador (PROT-CMP).
"""
from fin_mas.agents.base import Specialist
from fin_mas.core.message import Message


class AgenteControlesInternos(Specialist):
    def __init__(self, bus, gateway):
        super().__init__("AG-CIN", bus, gateway)
        self.conhecimento = {"regras": ["alcada", "sod", "duplicidade", "competencia"]}
        self.estado = {"crencas": {}, "intencao": None}

    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-CMP" and msg.performative == "request":
            self._verificar(msg)
        else:
            super().on_message(msg)

    def _verificar(self, msg: Message) -> None:
        cid = msg.conversation_id
        lancamentos = self.gw.call(self.id, "erp.lancamentos", cid)
        alcadas = self.gw.call(self.id, "normas.alcadas", cid)["dados"]
        regras = self.gw.call(self.id, "normas.regras", cid)["dados"]
        periodo = lancamentos["proveniencia"]["consulta"]["competencia"]
        achados = self._avaliar(lancamentos["dados"], alcadas, regras["severidade"], periodo)
        criticos = [a for a in achados if a["severidade"] == "critica"]
        if criticos:
            evento, intencao = "veto", "vetar"
        elif achados:
            evento, intencao = "nao_conforme_nao_critico", "apontar"
        else:
            evento, intencao = "conforme", "aprovar"
        self.estado["intencao"] = intencao
        self.decide(cid, f"parecer {evento}: críticas vetam a publicação",
                    {"lancamentos": len(lancamentos["dados"]), "normas": regras["versao"]},
                    {"achados": len(achados), "criticos": len(criticos)})
        self.send(msg.sender, evento, "PROT-CMP", cid,
                  {"achados": achados, "versao_normas": regras["versao"],
                   "proveniencia": lancamentos["proveniencia"]}, delay=2)

    def _avaliar(self, lancamentos, alcadas, severidade, periodo):
        achados, vistos = [], set()
        for lanc in lancamentos:
            violacoes = []
            limite = alcadas["limites"][alcadas["cargos"][lanc["aprovador"]]]
            if lanc["valor"] > limite:
                violacoes.append(("alcada", f"valor acima da alçada de {lanc['aprovador']}"))
            if lanc["criador"] == lanc["aprovador"]:
                violacoes.append(("sod", f"{lanc['criador']} criou e aprovou"))
            chave = (lanc["fornecedor"], lanc["documento"], lanc["valor"])
            if chave in vistos:
                violacoes.append(("duplicidade", "fornecedor, documento e valor já lançados"))
            vistos.add(chave)
            if lanc["competencia"] != periodo:
                violacoes.append(("competencia", f"competência {lanc['competencia']} fora de {periodo}"))
            self.estado["crencas"][lanc["id"]] = [r for r, _ in violacoes] or ["conforme"]
            for regra, evidencia in violacoes:
                achados.append({"regra": regra, "lancamento": lanc["id"],
                                "severidade": severidade[regra], "evidencia": evidencia})
        return sorted(achados, key=lambda a: (a["regra"], a["lancamento"]))

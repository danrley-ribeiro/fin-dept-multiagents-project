"""AG-RES — Agente de Resultados: DRE gerencial e KPIs a partir de Custos e Orçamento.

Depende de informação de outros agentes: obtém custos e desvios por query-ref
(PROT-QRY), sem reimplementar as regras de AG-CUS e AG-ORC (REQ-F04).
"""
from fin_mas.agents.base import Specialist
from fin_mas.core.message import Message

PRAZO_CONSULTA = 10  # ticks lógicos até a expiração de uma query-ref


class AgenteResultados(Specialist):
    def __init__(self, bus, gateway):
        super().__init__("AG-RES", bus, gateway)
        self.conhecimento = {"estrutura_dre": ["receita", "custos_variaveis", "margem_contribuicao",
                                               "custos_fixos", "ebitda"]}
        self.estado = {"consolidacoes": {}, "consulta_para_tarefa": {}}

    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-DEL" and msg.performative == "request":
            self._consolidar(msg)
        elif msg.protocol == "PROT-QRY" and msg.performative in ("inform", "refuse", "failure", "timeout"):
            self._resposta(msg)
        else:
            super().on_message(msg)

    def _consolidar(self, msg: Message) -> None:
        cid = msg.conversation_id
        self.send(msg.sender, "agree", "PROT-DEL", cid)
        if msg.content.get("tarefa") != "consolidar_resultado":
            self.send(msg.sender, "failure", "PROT-DEL", cid,
                      {"motivo": f"tarefa desconhecida: {msg.content.get('tarefa')}"})
            return
        balancete = self.gw.call(self.id, "erp.balancete", cid)
        receita = sum(p["preco"] * p["qtd"] for p in balancete["dados"]["produtos"])
        consolidacao = {"solicitante": msg.sender, "receita": receita, "respostas": {}, "consultas": {},
                        "falhou": False, "proveniencia": [balancete["proveniencia"]]}
        for destino, assunto, chave in (("AG-CUS", "custos_por_UN", "custos"), ("AG-ORC", "desvios", "orcamento")):
            qid = self.bus.new_conversation_id("QRY")
            consolidacao["consultas"][qid] = chave
            self.estado["consulta_para_tarefa"][qid] = cid
            self.bus.audit.record(self.bus.now, "link", conversation_id=cid, filha=qid,
                                  subtarefa=f"consulta {chave}", agente=self.id)
            self.send(destino, "query-ref", "PROT-QRY", qid, {"assunto": assunto},
                      reply_by=self.bus.now + PRAZO_CONSULTA)
        self.estado["consolidacoes"][cid] = consolidacao

    def _resposta(self, msg: Message) -> None:
        tarefa = self.estado["consulta_para_tarefa"].get(msg.conversation_id)
        consolidacao = self.estado["consolidacoes"].get(tarefa)
        if consolidacao is None or consolidacao["falhou"]:
            return
        if msg.performative != "inform":
            consolidacao["falhou"] = True
            motivo = msg.content.get("motivo") or f"consulta {msg.performative}"
            self.send(consolidacao["solicitante"], "failure", "PROT-DEL", tarefa,
                      {"motivo": f"insumo indisponível ({consolidacao['consultas'][msg.conversation_id]}): {motivo}"})
            return
        consolidacao["respostas"][consolidacao["consultas"][msg.conversation_id]] = msg.content
        consolidacao["proveniencia"].append(msg.content["proveniencia"])
        if len(consolidacao["respostas"]) == len(consolidacao["consultas"]):
            self._finalizar(tarefa, consolidacao)

    def _finalizar(self, tarefa: str, c: dict) -> None:
        custos = c["respostas"]["custos"]["totais"]
        orcamento = c["respostas"]["orcamento"]["totais"]
        if custos["receita"] != c["receita"]:
            c["falhou"] = True
            self.send(c["solicitante"], "failure", "PROT-DEL", tarefa,
                      {"motivo": "receita do ERP diverge da receita usada na apuração de custos"})
            return
        receita = c["receita"]
        margem = receita - custos["custos_variaveis"]
        dre = {"receita": receita, "custos_variaveis": custos["custos_variaveis"],
               "margem_contribuicao": margem, "custos_fixos": custos["custos_fixos"],
               "ebitda": margem - custos["custos_fixos"]}
        kpis = {"margem_contribuicao_pct": round(margem * 100 / receita, 2),
                "ebitda_pct": round(dre["ebitda"] * 100 / receita, 2),
                "desvio_orcamentario": orcamento["realizado_acumulado"] - orcamento["orcado_acumulado"]}
        self.decide(tarefa, "DRE = receita - variáveis - fixos; receita do ERP conferida com a de Custos",
                    {"consultas": sorted(c["consultas"])}, dre)
        self.estado["ultima_dre"] = dre
        self.send(c["solicitante"], "inform", "PROT-DEL", tarefa,
                  {"dre": dre, "kpis": kpis, "resultado_un": c["respostas"]["custos"]["resultado_un"],
                   "proveniencia": c["proveniencia"]})

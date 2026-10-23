"""AG-ORQ — Orquestrador: intenção -> DAG de subtarefas, prazos, reenvio e resposta final.

Única fronteira com o usuário (PROT-SOL). Delega por PROT-DEL e PROT-CMP, reserva
o período (PROT-LCK) e, na falha de um especialista, reenvia uma vez antes de
abortar com failure explícito (REQ-F01). Não usa LLM (ADR-002).
"""
from fin_mas.core.agent import Agent
from fin_mas.core.message import Message

PRAZO_SUBTAREFA = 30  # ticks lógicos de reply_by por delegação
MAX_TENTATIVAS = 2  # envio original + um reenvio


def _no(agente, tarefa, depende=(), protocolo="PROT-DEL"):
    return {"agente": agente, "tarefa": tarefa, "depende": list(depende), "protocolo": protocolo}


CATALOGO = {
    "fechar_mes": {
        "reservar_periodo": True,
        "nos": {
            "custos": _no("AG-CUS", "apurar_custos"),
            "orcamento": _no("AG-ORC", "orcado_x_realizado"),
            "resultados": _no("AG-RES", "consolidar_resultado", ["custos", "orcamento"]),
            "conformidade": _no("AG-CIN", "compliance_check", ["resultados"], "PROT-CMP"),
            "relatorio": _no("AG-REL", "relatorio_executivo", ["conformidade"]),
        },
    },
    "avaliar_orcamento": {
        "reservar_periodo": False,
        "nos": {
            "orcamento": _no("AG-ORC", "orcado_x_realizado"),
            "relatorio": _no("AG-REL", "relatorio_orcamentario", ["orcamento"]),
        },
    },
}


class Orquestrador(Agent):
    def __init__(self, bus, locks, aprovador="APR"):
        super().__init__("AG-ORQ", bus)
        self.locks = locks
        self.aprovador = aprovador
        self.conhecimento = {"catalogo": CATALOGO, "prazo_subtarefa": PRAZO_SUBTAREFA,
                             "max_tentativas": MAX_TENTATIVAS}
        self.estado = {"solicitacoes": {}, "conversa_para_solicitacao": {}}

    # ---- entrada ----------------------------------------------------------
    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-SOL" and msg.performative == "request":
            self._nova_solicitacao(msg)
        elif msg.protocol is None and msg.performative == "decisao_humana":
            self._decisao_humana(msg)
        elif msg.protocol in ("PROT-DEL", "PROT-CMP"):
            self._resposta_especialista(msg)

    def _nova_solicitacao(self, msg: Message) -> None:
        sid, c = msg.conversation_id, msg.content
        plano = CATALOGO.get(c.get("intencao"))
        if plano is None:
            self.decide(sid, "intenção fora do catálogo", {"intencao": c.get("intencao")}, "not-understood")
            self.send(msg.sender, "not-understood", "PROT-SOL", sid, {"motivo": "intenção fora do catálogo"})
            return
        sol = {"id": sid, "solicitante": msg.sender, "intencao": c["intencao"], "entidade": c["entidade"],
               "competencia": c["competencia"], "plano": plano, "status": "executando", "reserva": False,
               "nos": {n: {"status": "pendente", "tentativas": 0, "conversas": [], "resultado": None}
                       for n in plano["nos"]},
               "ressalvas": [], "parecer": "conforme"}
        if plano["reservar_periodo"]:
            r = self.locks.reserve(sol["entidade"], sol["competencia"], sid)
            if r["performative"] == "reserve-failure":
                self.decide(sid, "período já reservado por outro fechamento", {"dono_atual": r["dono_atual"]}, "refuse")
                self.send(msg.sender, "refuse", "PROT-SOL", sid,
                          {"motivo": "período em fechamento", "dono_atual": r["dono_atual"]})
                return
            sol["reserva"] = True
        self.estado["solicitacoes"][sid] = sol
        self.decide(sid, "intenção -> DAG do catálogo", {"intencao": sol["intencao"]},
                    {n: d["depende"] for n, d in plano["nos"].items()})
        self.send(msg.sender, "agree", "PROT-SOL", sid)
        self._avancar(sol)

    # ---- execução do DAG --------------------------------------------------
    def _avancar(self, sol: dict) -> None:
        if sol["status"] != "executando":
            return
        for nome, no in sol["plano"]["nos"].items():
            estado = sol["nos"][nome]
            if estado["status"] == "pendente" and all(sol["nos"][d]["status"] == "concluido" for d in no["depende"]):
                self._enviar(sol, nome)
        if all(n["status"] == "concluido" for n in sol["nos"].values()):
            self._concluir(sol)

    def _enviar(self, sol: dict, nome: str) -> None:
        no, estado = sol["plano"]["nos"][nome], sol["nos"][nome]
        prefixo = "CMP" if no["protocolo"] == "PROT-CMP" else "DEL"
        cid = self.bus.new_conversation_id(prefixo)
        estado["status"], estado["tentativas"] = "enviado", estado["tentativas"] + 1
        estado["conversas"].append(cid)
        self.estado["conversa_para_solicitacao"][cid] = (sol["id"], nome)
        conteudo = {"tarefa": no["tarefa"], "entidade": sol["entidade"], "competencia": sol["competencia"],
                    **self._insumos(sol, nome)}
        self.send(no["agente"], "request", no["protocolo"], cid, conteudo,
                  reply_by=self.bus.now + PRAZO_SUBTAREFA)

    def _insumos(self, sol: dict, nome: str) -> dict:
        r = {n: e["resultado"] for n, e in sol["nos"].items()}
        if nome == "relatorio" and sol["intencao"] == "fechar_mes":
            return {"dre": r["resultados"]["dre"], "kpis": r["resultados"]["kpis"],
                    "resultado_un": r["resultados"]["resultado_un"], "parecer": sol["parecer"],
                    "ressalvas": list(sol["ressalvas"])}
        if nome == "relatorio":
            return {"totais": r["orcamento"]["totais"], "sinalizadas": r["orcamento"]["sinalizadas"],
                    "ressalvas": []}
        return {}

    def _resposta_especialista(self, msg: Message) -> None:
        ref = self.estado["conversa_para_solicitacao"].get(msg.conversation_id)
        if ref is None:
            return
        sol, nome = self.estado["solicitacoes"][ref[0]], ref[1]
        if sol["status"] != "executando" or msg.conversation_id != sol["nos"][nome]["conversas"][-1]:
            return  # solicitação já encerrada ou resposta de uma tentativa anterior
        p = msg.performative
        if p == "agree":
            return
        if p == "inform" or p in ("conforme", "nao_conforme_nao_critico"):
            self._parecer_ou_resultado(sol, nome, msg)
        elif p == "veto":
            self._veto(sol, nome, msg)
        else:  # failure, refuse ou timeout
            motivo = msg.content.get("motivo") or p
            self._falha(sol, nome, p, motivo)

    def _parecer_ou_resultado(self, sol, nome, msg):
        if msg.performative == "nao_conforme_nao_critico":
            sol["parecer"] = "conforme com ressalvas"
            sol["ressalvas"] += [f"{a['regra']} em {a['lancamento']}: {a['evidencia']}" for a in msg.content["achados"]]
            self.bus.advance(msg.conversation_id, "publicar", self.id)
        self._concluir_no(sol, nome, msg.content)

    def _concluir_no(self, sol, nome, resultado):
        sol["nos"][nome].update(status="concluido", resultado=resultado)
        self._avancar(sol)

    # ---- veto e waiver ----------------------------------------------------
    def _veto(self, sol, nome, msg):
        sol["nos"][nome].update(status="vetado", resultado=msg.content)
        sol["veto"] = {"no": nome, "cid": msg.conversation_id, "achados": msg.content["achados"]}
        self.decide(sol["id"], "NORM-04: não conformidade crítica bloqueia a publicação",
                    {"achados": [a["lancamento"] for a in msg.content["achados"]]}, "VETADO")
        self.send(self.aprovador, "veto_notice", None, msg.conversation_id,
                  {"solicitacao": sol["id"], "achados": msg.content["achados"]})

    def _decisao_humana(self, msg: Message) -> None:
        sol = self.estado["solicitacoes"].get(msg.content["solicitacao"])
        if sol is None or sol["status"] != "executando" or "veto" not in sol:
            return
        veto, cid = sol.pop("veto"), msg.conversation_id
        if msg.content["decisao"] == "waiver":
            self.bus.advance(cid, "waiver_humano", self.id)
            self.bus.advance(cid, "publicar", self.id)
            criticos = [f"waiver de {a['regra']} em {a['lancamento']}: {msg.content['justificativa']}"
                        for a in veto["achados"] if a["severidade"] == "critica"]
            outros = [f"{a['regra']} em {a['lancamento']}: {a['evidencia']}"
                      for a in veto["achados"] if a["severidade"] != "critica"]
            sol["ressalvas"] += criticos + outros
            sol["parecer"] = "liberado por waiver humano"
            self.decide(sol["id"], "waiver humano com justificativa", {"justificativa": msg.content["justificativa"]},
                        "LIBERADO_COM_RESSALVA")
            self._concluir_no(sol, veto["no"], {"achados": veto["achados"], "waiver": True})
        else:
            self.bus.advance(cid, "prazo_esgotado", self.id)
            self._abortar(sol, veto["no"], "publicação bloqueada por veto (NORM-04)",
                          {"achados": veto["achados"]})

    # ---- falha, reenvio e abort -------------------------------------------
    def _falha(self, sol, nome, performativo, motivo):
        estado = sol["nos"][nome]
        if performativo != "refuse" and estado["tentativas"] < MAX_TENTATIVAS:
            self.decide(sol["id"], "um reenvio por subtarefa expirada ou falha",
                        {"subtarefa": nome, "motivo": motivo, "tentativa": estado["tentativas"]}, "reenviar")
            self._enviar(sol, nome)
        else:
            self.decide(sol["id"], "segunda falha (ou recusa) aborta a solicitação",
                        {"subtarefa": nome, "motivo": motivo}, "abortar")
            self._abortar(sol, nome, motivo)

    def _abortar(self, sol, nome, motivo, extra=None):
        sol["status"] = "falhou"
        self._liberar(sol)
        self.send(sol["solicitante"], "failure", "PROT-SOL", sol["id"],
                  {"subtarefa": nome, "motivo": motivo, "publicado": False, **(extra or {})})

    def _liberar(self, sol):
        if sol["reserva"]:
            self.locks.release(sol["entidade"], sol["competencia"], sol["id"])
            sol["reserva"] = False

    # ---- resposta final ---------------------------------------------------
    def _concluir(self, sol):
        sol["status"] = "concluida"
        r = {n: e["resultado"] for n, e in sol["nos"].items()}
        resposta = {"intencao": sol["intencao"], "entidade": sol["entidade"], "competencia": sol["competencia"],
                    "status": "publicado_com_ressalva" if sol["ressalvas"] else "publicado",
                    "relatorio": r["relatorio"]["texto"], "ressalvas": sol["ressalvas"],
                    "dag": {n: {"agente": sol["plano"]["nos"][n]["agente"], "tentativas": e["tentativas"],
                                "conversas": e["conversas"]} for n, e in sol["nos"].items()}}
        if sol["intencao"] == "fechar_mes":
            resposta["resultado"] = {"dre": r["resultados"]["dre"], "kpis": r["resultados"]["kpis"]}
        else:
            resposta["resultado"] = {"totais": r["orcamento"]["totais"], "sinalizadas": r["orcamento"]["sinalizadas"]}
        self._liberar(sol)
        self.decide(sol["id"], "todas as subtarefas concluídas", {"parecer": sol["parecer"]}, resposta["status"])
        self.send(sol["solicitante"], "inform", "PROT-SOL", sol["id"], resposta)

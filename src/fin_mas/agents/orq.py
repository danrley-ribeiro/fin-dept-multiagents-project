"""AG-ORQ — Orquestrador: intenção -> DAG de subtarefas, prazos, reenvio e resposta final.

Única fronteira com o usuário (PROT-SOL). Delega por PROT-DEL e PROT-CMP, reserva
o período (PROT-LCK) e, na falha de um especialista, reenvia uma vez antes de
abortar com failure explícito (REQ-F01). Não usa LLM (ADR-002).

O Orquestrador não decide conformidade nem desvio: encaminha o veto e as correções
sugeridas pelo AG-CIN ao aprovador humano e devolve ao AG-CIN a decisão (correção,
waiver ou bloqueio); quem reavalia é o AG-CIN.

DSM3 — Approval Gate. O veto vira um ticket do SVC-POL e uma conversa PROT-APR com o
aprovador designado (propose-action -> approve | reject | timeout). O Orquestrador só
age sobre uma decisão que a política validou no barramento; a correção no ERP é um
efeito externo executado pelo gateway MCP com o id da aprovação, e o AG-CIN recebe o
mesmo id, que a política aceita uma única vez.
"""
from fin_mas.core.agent import Agent
from fin_mas.core.message import Message
from fin_mas.services.politica import PoliticaAprovacao

PRAZO_SUBTAREFA = 30  # ticks lógicos de reply_by por delegação
MAX_TENTATIVAS = 2  # envio original + um reenvio
MAX_CORRECOES = 2  # teto de segurança; quem oferece (ou não) a correção é o AG-CIN, conforme o porte
MAX_EXTENSAO = 20  # ticks a mais que uma subtarefa pode negociar, uma única vez (PROT-DEL, propose)


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


def ressalvas(achados, agrupar_acima=3) -> list[str]:
    """Uma linha por achado; a mesma regra repetida em muitos lançamentos vira uma linha só."""
    por_regra: dict[str, list] = {}
    for a in achados:
        por_regra.setdefault(a["regra"], []).append(a)
    linhas = []
    for regra, grupo in por_regra.items():
        if len(grupo) > agrupar_acima:
            ids = ", ".join(a["lancamento"] for a in grupo)
            comum = grupo[0]["evidencia"].split("; ", 1)[-1] if "; " in grupo[0]["evidencia"] else grupo[0]["evidencia"]
            linhas.append(f"{regra} em {len(grupo)} lançamentos ({ids}): {comum}")
        else:
            linhas += [f"{a['regra']} em {a['lancamento']}: {a['evidencia']}" for a in grupo]
    return linhas


class Orquestrador(Agent):
    PAPEL = "ROLE-ORQ"
    def __init__(self, bus, locks, aprovador="APR", politica: PoliticaAprovacao | None = None, gateway=None,
                 parametros=None):
        super().__init__("AG-ORQ", bus)
        self.locks = locks
        self.aprovador = aprovador
        self.politica = politica if politica is not None else PoliticaAprovacao(bus)
        self.gw = gateway
        # DSM4: parâmetros de coordenação injetáveis (`fin_mas.parametros`); sem eles valem as constantes acima
        self.prazo_subtarefa = getattr(parametros, "prazo_subtarefa", PRAZO_SUBTAREFA)
        self.max_tentativas = getattr(parametros, "max_tentativas", MAX_TENTATIVAS)
        self.max_correcoes = getattr(parametros, "max_correcoes", MAX_CORRECOES)
        self.max_extensao = getattr(parametros, "max_extensao", MAX_EXTENSAO)
        self.reserva_periodo = getattr(parametros, "reserva_periodo", True)
        self.conhecimento = {"catalogo": CATALOGO, "prazo_subtarefa": self.prazo_subtarefa,
                             "max_tentativas": self.max_tentativas, "max_correcoes": self.max_correcoes,
                             "prazo_aprovacao": self.politica.prazo}
        self.estado = {"solicitacoes": {}, "conversa_para_solicitacao": {}, "aprovacao_para_solicitacao": {}}

    # ---- entrada ----------------------------------------------------------
    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-SOL" and msg.performative == "request":
            self._nova_solicitacao(msg)
        elif msg.protocol == "PROT-APR":
            self._resposta_aprovador(msg)
        elif msg.protocol in ("PROT-DEL", "PROT-CMP"):
            self._resposta_especialista(msg)

    def _nova_solicitacao(self, msg: Message) -> None:
        sid, c = msg.conversation_id, msg.content
        plano = CATALOGO.get(c.get("intencao"))
        if plano is None:
            self.decide(sid, "intenção fora do catálogo", {"intencao": c.get("intencao")}, "not-understood")
            self.send(msg.sender, "not-understood", "PROT-SOL", sid, {"motivo": "intenção fora do catálogo"})
            return
        motivo = self._fora_do_escopo(c["entidade"], c["competencia"])
        if motivo:
            self.decide(sid, "pedido fora do escopo da controladoria", {"entidade": c["entidade"],
                                                                       "competencia": c["competencia"]}, "refuse")
            self.send(msg.sender, "refuse", "PROT-SOL", sid, {"motivo": motivo})
            return
        sol = {"id": sid, "solicitante": msg.sender, "intencao": c["intencao"], "entidade": c["entidade"],
               "competencia": c["competencia"], "plano": plano, "status": "executando", "reserva": False,
               "nos": {n: {"status": "pendente", "tentativas": 0, "conversas": [], "resultado": None}
                       for n in plano["nos"]},
               "ressalvas": [], "notas": [], "correcoes": 0, "ciclos_veto": 0, "aprovacoes": [],
               "parecer": "conforme"}
        if isinstance(c.get("solicitado_por"), str):  # pessoa autenticada que pediu (interface com SVC-IAM)
            sol["solicitado_por"] = c["solicitado_por"]
        if plano["reservar_periodo"] and self.reserva_periodo:
            r = self.com_credencial(self.locks.reserve, sol["entidade"], sol["competencia"], sid)
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

    def _fora_do_escopo(self, entidade: str, competencia: str) -> str | None:
        """Entidade que não é a empresa atendida ou competência sem dados: recusa antes de delegar."""
        if self.gw is None:
            return None
        ambiente = self.gw.ambiente
        if entidade != ambiente.dataset().entidade:
            return f"entidade desconhecida: {entidade} (esta controladoria atende {ambiente.dataset().entidade})"
        if ambiente.pasta is not None and competencia != ambiente.principal:
            return f"sem dados da competência {competencia}: a planilha da empresa é de {ambiente.principal}"
        return None

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
        self.bus.audit.record(self.bus.now, "link", conversation_id=sol["id"], filha=cid,
                              subtarefa=nome, agente=self.id)
        conteudo = {"tarefa": no["tarefa"], "entidade": sol["entidade"], "competencia": sol["competencia"],
                    **self._insumos(sol, nome)}
        self.send(no["agente"], "request", no["protocolo"], cid, conteudo,
                  reply_by=self.bus.now + self.prazo_subtarefa)

    def _insumos(self, sol: dict, nome: str) -> dict:
        r = {n: e["resultado"] for n, e in sol["nos"].items()}
        # insights dos especialistas (só existem com cognição local ou LLM, ADR-008): o Orquestrador repassa
        extras = {"insights": list(r["orcamento"]["insights"])} if (r.get("orcamento") or {}).get("insights") else {}
        if (r.get("resultados") or {}).get("insights"):  # DSM4: o AG-RES cognitivo também explica (ADR-010)
            extras["insights"] = extras.get("insights", []) + list(r["resultados"]["insights"])
        for origem, campo in (("orcamento", "narrativa"), ("resultados", "comentario")):  # textos de LLM validados
            if (r.get(origem) or {}).get(campo):
                extras[campo] = dict(r[origem][campo])
        if nome == "relatorio" and sol["intencao"] == "fechar_mes":
            return {"dre": r["resultados"]["dre"], "kpis": r["resultados"]["kpis"],
                    "resultado_un": r["resultados"]["resultado_un"], "parecer": sol["parecer"],
                    "ressalvas": list(sol["ressalvas"]), "notas": list(sol["notas"]), **extras}
        if nome == "relatorio":
            return {"totais": r["orcamento"]["totais"], "sinalizadas": r["orcamento"]["sinalizadas"],
                    "atribuidas_a_controle": r["orcamento"].get("atribuidas_a_controle", []),
                    "ressalvas": list(sol["ressalvas"]), "notas": list(sol["notas"]), **extras}
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
        if p == "propose":
            self._negociar_prazo(sol, nome, msg)
            return
        if p == "inform" or p in ("conforme", "nao_conforme_nao_critico", "veto"):
            try:
                if p == "veto":
                    self._veto(sol, nome, msg)
                else:
                    self._parecer_ou_resultado(sol, nome, msg)
            except (KeyError, TypeError, ValueError, AttributeError, IndexError) as erro:
                # conteúdo aninhado fora do esperado (o esquema do protocolo só confere o primeiro nível): o
                # solicitante recebe falha explícita e o período é liberado, em vez de silêncio (correção M3)
                if sol["status"] not in ("executando", "aguardando_aprovacao", "aguardando"):
                    raise
                motivo = f"resposta malformada de {msg.sender} em {nome}: {type(erro).__name__}: {erro}"
                self.decide(sol["id"], "resposta de especialista que não pode ser interpretada aborta a solicitação",
                            {"subtarefa": nome, "motivo": motivo}, "abortar")
                self._abortar(sol, nome, motivo)
        else:  # failure, refuse ou timeout
            motivo = msg.content.get("motivo") or p
            self._falha(sol, nome, p, motivo)

    def _negociar_prazo(self, sol, nome, msg) -> None:
        """O especialista pede mais prazo em vez de estourar o tempo. Regras de quem coordena:

        só prazo é negociável (resultado parcial não); uma extensão por subtarefa, até `MAX_EXTENSAO`;
        e nenhuma extensão num fechamento com período reservado, porque a reserva tem prazo e outros
        pedidos esperam por ela.
        """
        no, c = sol["nos"][nome], msg.content
        motivo = None
        if c["tipo"] != "mais_prazo":
            motivo = "só o prazo é negociável: resultado parcial não é aceito"
        elif sol["reserva"]:
            motivo = "período reservado para o fechamento: a subtarefa precisa caber no prazo original"
        elif no.get("extensoes"):
            motivo = "esta subtarefa já teve uma extensão de prazo"
        elif not 0 < c["prazo_extra"] <= self.max_extensao:
            motivo = f"extensão de {c['prazo_extra']} ticks fora do teto de {self.max_extensao}"
        entradas = {"subtarefa": nome, "prazo_extra": c["prazo_extra"], "motivo_do_pedido": c["motivo"]}
        if motivo:
            self.decide(sol["id"], "negociação de prazo (PROT-DEL): proposta recusada", entradas, motivo)
            self.send(msg.sender, "reject-proposal", "PROT-DEL", msg.conversation_id, {"motivo": motivo})
            return
        no["extensoes"] = 1
        novo = self.bus.prazos[msg.conversation_id] + c["prazo_extra"]
        self.decide(sol["id"], "negociação de prazo (PROT-DEL): uma extensão por subtarefa, dentro do teto", entradas,
                    {"novo_prazo": novo})
        self.send(msg.sender, "accept-proposal", "PROT-DEL", msg.conversation_id, {"prazo": novo}, reply_by=novo)

    def _parecer_ou_resultado(self, sol, nome, msg):
        if msg.performative == "nao_conforme_nao_critico":
            sol["parecer"] = "conforme com ressalvas"
            sol["ressalvas"] += ressalvas(msg.content["achados"])
            self.avancar(msg.conversation_id, "publicar")
        self._concluir_no(sol, nome, msg.content)

    def _concluir_no(self, sol, nome, resultado):
        sol["nos"][nome].update(status="concluido", resultado=resultado)
        sol["ressalvas"] += resultado.get("ressalvas", []) if nome != "relatorio" else []
        self._avancar(sol)

    # ---- veto e Approval Gate (PROT-APR) -------------------------------------
    def _veto(self, sol, nome, msg):
        sol["nos"][nome].update(status="vetado", resultado=msg.content)
        opcoes = list(msg.content.get("opcoes", ["waiver", "bloquear"]))
        if sol["correcoes"] >= self.max_correcoes:
            opcoes = [o for o in opcoes if o != "corrigir"]
        sol["ciclos_veto"] += 1
        self.decide(sol["id"], "NORM-04: não conformidade crítica bloqueia a publicação",
                    {"achados": [a["lancamento"] for a in msg.content["achados"]]}, "VETADO")
        ticket = self.politica.emitir(solicitacao=sol["id"], competencia=sol["competencia"], cmp=msg.conversation_id,
                                      ciclo=sol["ciclos_veto"], veto={**msg.content, "opcoes": opcoes},
                                      aprovador=self.aprovador, solicitado_por=sol.get("solicitado_por"))
        tid = ticket["id"]
        sol["veto"] = {"no": nome, "cid": msg.conversation_id, "achados": msg.content["achados"], "aprovacao": tid}
        sol["aprovacoes"].append(tid)
        self.estado["aprovacao_para_solicitacao"][tid] = sol["id"]
        self.bus.audit.record(self.bus.now, "link", conversation_id=sol["id"], filha=tid,
                              subtarefa="aprovação humana", agente=self.id)
        if sol["reserva"] and not self.com_credencial(self.locks.renovar, sol["entidade"], sol["competencia"], sol["id"],
                                                     ticket["expira_em"] + 2 * self.prazo_subtarefa):
            sol.pop("veto")  # a reserva do período expirou antes do veto: não há como esperar o aprovador
            self.politica.expirar(tid)
            self.decide(sol["id"], "PROT-LCK: reserva do período perdida durante o fechamento", {}, "abortar")
            self._abortar(sol, nome, "reserva do período perdida (TTL)")
            return
        self.send(self.aprovador, "propose-action", "PROT-APR", tid, self.politica.conteudo_proposta(tid),
                  reply_by=ticket["expira_em"])
        if self.politica.classificar(tid) == "deny":
            self.decide(sol["id"], "POL-07: a política não deixou opção de liberação", {"negadas": ticket["negadas"]},
                        "NEGADO")
            self._bloquear(sol, sol.pop("veto"), "negada")

    def _resposta_aprovador(self, msg: Message) -> None:
        tid = msg.conversation_id
        sol = self.estado["solicitacoes"].get(self.estado["aprovacao_para_solicitacao"].get(tid))
        if sol is None or sol["status"] != "executando" or sol.get("veto", {}).get("aprovacao") != tid:
            return  # decisão de um ticket encerrado ou de outro ciclo de veto
        ticket = self.politica.ticket(tid)
        veto = sol.pop("veto")
        if msg.performative == "timeout":
            self.politica.expirar(tid)
            self.decide(sol["id"], "POL-08: prazo da aprovação esgotado sem decisão", {"aprovacao": tid}, "BLOQUEADO")
            self._bloquear(sol, veto, "expirada")
        elif msg.performative == "reject" and ticket["estado"] == "rejeitado":
            self.decide(sol["id"], "aprovador rejeitou a liberação",
                        {"aprovacao": tid, "aprovado_por": ticket["aprovado_por"]}, "BLOQUEADO")
            self._bloquear(sol, veto, "bloquear")
        elif msg.performative == "approve" and ticket["estado"] == "aprovado" and ticket["decisao"] == "corrigir":
            self._corrigir(sol, veto, ticket)
        elif msg.performative == "approve" and ticket["estado"] == "aprovado" and ticket["decisao"] == "waiver":
            self._waiver(sol, veto, ticket)
        else:  # ticket em estado inesperado (ex.: alterado fora do fluxo): bloqueia, nunca fica sem resposta
            self.politica.expirar(tid)
            self.decide(sol["id"], "ticket em estado inesperado: bloqueio por segurança (fail-closed)",
                        {"aprovacao": tid, "estado": ticket["estado"], "performativo": msg.performative},
                        "BLOQUEADO")
            self._bloquear(sol, veto, "inconsistente")

    def _corrigir(self, sol, veto, ticket):
        sol["correcoes"] += 1
        tid, executadas = ticket["id"], []
        for pedido in ticket["correcoes_aprovadas"]:
            try:
                r = self.ferramenta("erp.corrigir", tid, competencia=sol["competencia"], aprovacao=tid,
                                 lancamento=pedido["lancamento"], acao=pedido["acao"])["dados"]
                executadas.append(r)
            except Exception as erro:  # correção inviável: o AG-CIN reavalia e mantém o veto
                motivo = str(erro) or type(erro).__name__
                self.politica.registrar_falha(tid, pedido, motivo)
                self.decide(sol["id"], "correção aprovada não pôde ser executada", {**pedido, "erro": motivo},
                            "NAO_EXECUTADA")
        self.avancar(tid, "execute")
        quem = ticket["aprovado_por"]["titulo"]
        sol["notas"] += [f"correção aprovada por {quem} ({tid}): {c['detalhe']}" for c in executadas]
        self.decide(sol["id"], "correção aprovada no Approval Gate: AG-CIN reavalia o pacote",
                    {"aprovacao": tid, "correcoes": executadas}, "REAVALIAR")
        sol["nos"][veto["no"]]["status"] = "enviado"
        self.send("AG-CIN", "correcao", "PROT-CMP", veto["cid"], {"aprovacao": tid, "correcoes": executadas})

    def _waiver(self, sol, veto, ticket):
        tid, justificativa = ticket["id"], ticket["justificativa"]
        self.send("AG-CIN", "waiver_humano", "PROT-CMP", veto["cid"],
                  {"aprovacao": tid, "justificativa": justificativa, "aprovado_por": ticket["aprovado_por"]["pessoa"]})
        self.avancar(veto["cid"], "publicar")
        self.avancar(tid, "execute")  # a liberação (efeito do waiver) foi executada: o ticket fecha em EXECUTADA
        quem = ticket["aprovado_por"]["titulo"]
        criticos = [f"waiver de {a['regra']} em {a['lancamento']} por {quem} ({tid}): {justificativa}"
                    for a in veto["achados"] if a["severidade"] == "critica"]
        outros = ressalvas([a for a in veto["achados"] if a["severidade"] != "critica"])
        sol["ressalvas"] += criticos + outros
        sol["parecer"] = "liberado por waiver humano"
        self.decide(sol["id"], "waiver humano com justificativa (Approval Gate)",
                    {"aprovacao": tid, "justificativa": justificativa, "aprovado_por": ticket["aprovado_por"]},
                    "LIBERADO_COM_RESSALVA")
        self._concluir_no(sol, veto["no"], {"achados": veto["achados"], "waiver": True, "aprovacao": tid})

    def _bloquear(self, sol, veto, decisao):
        self.send("AG-CIN", "prazo_esgotado", "PROT-CMP", veto["cid"],
                  {"decisao": decisao, "aprovacao": veto["aprovacao"]})
        self._abortar(sol, veto["no"], "publicação bloqueada por veto (NORM-04)",
                      {"achados": veto["achados"], "aprovacao": veto["aprovacao"], "decisao": decisao})

    # ---- falha, reenvio e abort -------------------------------------------
    def _falha(self, sol, nome, performativo, motivo):
        estado = sol["nos"][nome]
        if performativo != "refuse" and estado["tentativas"] < self.max_tentativas:
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
            if self.locks.dono(sol["entidade"], sol["competencia"]) == sol["id"]:
                self.com_credencial(self.locks.release, sol["entidade"], sol["competencia"], sol["id"])
            else:  # a reserva já expirou por TTL (ex.: espera longa por decisão humana)
                self.decide(sol["id"], "reserva do período já expirada por TTL", {"competencia": sol["competencia"]},
                            "sem liberação")
            sol["reserva"] = False

    # ---- resposta final ---------------------------------------------------
    def _concluir(self, sol):
        if sol["reserva"] and self.locks.dono(sol["entidade"], sol["competencia"]) != sol["id"]:
            # PROT-LCK: sem a reserva, outro fechamento pode estar no mesmo mês; publicar violaria a exclusão mútua
            self.decide(sol["id"], "PROT-LCK: não publica sem a reserva do período", {"competencia": sol["competencia"]},
                        "abortar")
            self._abortar(sol, "relatorio", "reserva do período perdida (TTL): publicação cancelada")
            return
        sol["status"] = "concluida"
        r = {n: e["resultado"] for n, e in sol["nos"].items()}
        resposta = {"intencao": sol["intencao"], "entidade": sol["entidade"], "competencia": sol["competencia"],
                    "status": "publicado_com_ressalva" if sol["ressalvas"] else "publicado",
                    "relatorio": r["relatorio"]["texto"], "ressalvas": sol["ressalvas"], "notas": sol["notas"],
                    "dag": {n: {"agente": sol["plano"]["nos"][n]["agente"], "tentativas": e["tentativas"],
                                "conversas": e["conversas"]} for n, e in sol["nos"].items()}}
        if sol["intencao"] == "fechar_mes":
            resposta["resultado"] = {"dre": r["resultados"]["dre"], "kpis": r["resultados"]["kpis"]}
        else:
            resposta["resultado"] = {"totais": r["orcamento"]["totais"], "sinalizadas": r["orcamento"]["sinalizadas"],
                                     "atribuidas_a_controle": r["orcamento"].get("atribuidas_a_controle", [])}
        if (r.get("orcamento") or {}).get("hipoteses"):
            resposta["hipoteses"] = r["orcamento"]["hipoteses"]
            resposta["insights"] = r["orcamento"]["insights"]
        self._liberar(sol)
        self.decide(sol["id"], "todas as subtarefas concluídas", {"parecer": sol["parecer"]}, resposta["status"])
        self.send(sol["solicitante"], "inform", "PROT-SOL", sol["id"], resposta)

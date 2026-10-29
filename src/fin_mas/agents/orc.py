"""AG-ORC — Agente de Orçamento, cognitivo (BDI).

Crenças: orçado e realizado por conta em duas fontes (planilha e ERP), fonte adotada,
valores contestados pelo AG-CIN e classificação de cada desvio.

Desejos gerados das crenças (1 = mais prioritário):
  1 fonte_confiavel(conta)     planilha e ERP divergem
  2 explicar_desvio(conta)     desvio acima do limiar ainda sem explicação
  3 alertar_desvio(conta)      desvio (ajustado) acima do limiar
  3 encaminhar_controle(conta) desvio explicado por lançamento contestado
  4 projetar_forecast          sem explicações pendentes
  5 avaliar_execucao           tudo decidido: consolida e responde

O AG-ORC decide sozinho a fonte, se consulta o AG-CIN (PROT-QRY direto, sem o
Orquestrador) e como classifica cada desvio; a resposta do AG-CIN revisa crenças e
pode tornar a intenção de alertar sem sentido, que é então reconsiderada.
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.env.dataset import LIMIAR_ABSOLUTO, LIMIAR_PERCENTUAL, brl

PRAZO_CONSULTA = 10  # ticks lógicos até a expiração da query-ref ao AG-CIN
TOLERANCIA_FONTE = 1_00  # R$ 1,00: abaixo disso planilha e ERP são considerados iguais


def _k(nome, c, conta=None):
    return f"{nome}[{conta}]@{c}" if conta else f"{nome}@{c}"


# ---- contextos e corpos dos planos ----------------------------------------------
def _ctx_fonte(primaria):
    def ctx(a, d):
        ok = a.conhecimento["fonte_primaria"] == primaria
        return ok, (f"{primaria} é a fonte primária do realizado" if ok
                    else f"fonte primária é {a.conhecimento['fonte_primaria']}, não {primaria}")
    return ctx


def _corpo_fonte(primaria):
    def corpo(a, i):
        c, conta = i.desejo.params["c"], i.desejo.params["conta"]
        pl, erp = a.crencas.get(_k("realizado_planilha", c, conta)), a.crencas.get(_k("realizado_erp", c, conta))
        valor = erp if primaria == "ERP" else pl
        fonte = "mcp://erp/realizado_por_conta" if primaria == "ERP" else "mcp://planilhas/orcamento"
        a.crencas.revisar(_k("realizado", c, conta), valor, fonte, i.desejo.cid)
        a.crencas.revisar(_k("fonte", c, conta), primaria, "plano " + i.plano.id, i.desejo.cid)
        a.tarefa(c)["ressalvas"].append(
            f"divergência em {conta}: planilha {brl(pl)} x ERP {brl(erp)}; adotado {primaria}")
        a.decide(i.desejo.cid, f"divergência de fontes: adota {primaria} (fonte primária)",
                 {"conta": conta, "planilha": pl, "erp": erp}, valor)
        a.concluir(i, valor, f"realizado de {conta} definido pela fonte {primaria}")
    return corpo


def _ctx_consultar_cin(a, d):
    if "AG-CIN" not in a.bus.agents:
        return False, "AG-CIN fora do diretório de agentes"
    return True, "AG-CIN pode atestar lançamentos que inflam a conta"


def _corpo_consultar_cin(a, i):
    c, conta = i.desejo.params["c"], i.desejo.params["conta"]
    qid = a.bus.new_conversation_id("QRY")
    a.bus.audit.record(a.bus.now, "link", conversation_id=i.desejo.cid, filha=qid,
                       subtarefa=f"explicar desvio {conta}", agente=a.id)
    a.send("AG-CIN", "query-ref", "PROT-QRY", qid, {"assunto": "irregularidades", "conta": conta, "competencia": c},
           reply_by=a.bus.now + PRAZO_CONSULTA)
    a.suspender(i, qid, f"aguarda AG-CIN sobre {conta}")


def _continuar_consultar_cin(a, i, msg):
    c, conta = i.desejo.params["c"], i.desejo.params["conta"]
    valor = msg.content["valor_contestado"]
    a.crencas.revisar(_k("contestado", c, conta), valor, f"AG-CIN ({msg.conversation_id})", i.desejo.cid)
    a.crencas.revisar(_k("explicacao", c, conta), [lanc["lancamento"] for lanc in msg.content["lancamentos"]],
                      f"AG-CIN ({msg.conversation_id})", i.desejo.cid)
    a.concluir(i, valor, f"AG-CIN contesta {brl(valor)} em {conta}")


def _corpo_sem_explicacao(a, i):
    c, conta = i.desejo.params["c"], i.desejo.params["conta"]
    a.crencas.revisar(_k("contestado", c, conta), 0, "plano " + i.plano.id, i.desejo.cid)
    a.crencas.revisar(_k("explicacao", c, conta), "indisponível", "plano " + i.plano.id, i.desejo.cid)
    a.tarefa(c)["ressalvas"].append(f"desvio de {conta} sinalizado sem atribuição: AG-CIN indisponível")
    a.concluir(i, 0, "sem atribuição: segue com o desvio bruto")


def _sempre(motivo):
    return lambda a, d: (True, motivo)


def _corpo_alertar(a, i):
    c, conta = i.desejo.params["c"], i.desejo.params["conta"]
    pendente = a.desejos.get("explicar_desvio:" + a.chave_params(i.desejo.params))
    if pendente is not None and pendente.estado == "ativo":
        a.suspender(i, "desejo:" + pendente.id, "só sinaliza depois de tentar explicar o desvio")
        return
    desvio = a.desvio_ajustado(c, conta)
    a.crencas.revisar(_k("classificacao", c, conta), "desvio_orcamentario", "plano " + i.plano.id, i.desejo.cid)
    a.decide(i.desejo.cid, f"desvio >= {LIMIAR_PERCENTUAL}% e >= {LIMIAR_ABSOLUTO} centavos após atribuição",
             {"conta": conta, "desvio_ajustado": desvio}, "sinalizado")
    a.concluir(i, desvio, f"{conta} sinalizada como desvio orçamentário")


def _corpo_encaminhar(a, i):
    c, conta = i.desejo.params["c"], i.desejo.params["conta"]
    a.crencas.revisar(_k("classificacao", c, conta), "atribuido_a_controle", "plano " + i.plano.id, i.desejo.cid)
    contestado = a.crencas.get(_k("contestado", c, conta))
    a.tarefa(c)["ressalvas"].append(
        f"desvio de {conta} atribuído a lançamentos contestados pelo AG-CIN ({brl(contestado)}), não ao orçamento")
    a.decide(i.desejo.cid, "desvio explicado por lançamento irregular: problema de controle, não de orçamento",
             {"conta": conta, "contestado": contestado, "desvio_bruto": a.desvio_bruto(c, conta)},
             "atribuido_a_controle")
    a.concluir(i, contestado, f"{conta} encaminhada como problema de controle")


def _ctx_forecast_ajustado(a, d):
    c = d.params["c"]
    total = sum(a.crencas.get(_k("contestado", c, conta), 0) or 0 for conta in a.tarefa(c)["contas"])
    return (total > 0, "exclui valores contestados do run-rate" if total else "nenhum valor contestado")


def _corpo_forecast(ajustado):
    def corpo(a, i):
        c = i.desejo.params["c"]
        t = a.tarefa(c)
        meses = t["meses"]
        forecast = {}
        for conta in t["contas"]:
            base = a.crencas.get(_k("realizado", c, conta))
            if ajustado:
                base -= a.crencas.get(_k("contestado", c, conta), 0) or 0
            forecast[conta] = (base * 3 + meses // 2) // meses
        metodo = a.conhecimento["metodo_forecast"] + (" sem valores contestados" if ajustado else "")
        a.crencas.revisar(_k("forecast", c), forecast, "plano " + i.plano.id, i.desejo.cid)
        a.crencas.revisar(_k("metodo_forecast", c), metodo, "plano " + i.plano.id, i.desejo.cid)
        a.concluir(i, sum(forecast.values()), "forecast do trimestre projetado")
    return corpo


def _corpo_consolidar(a, i):
    c = i.desejo.params["c"]
    avaliacao = a.consolidar(c)
    a.concluir(i, avaliacao["sinalizadas"], "avaliação consolidada e entregue")
    a.responder(c)


PLANOS = [
    Plano("P-ADOTAR-ERP", "fonte_confiavel", "adotar o ERP como verdade e registrar ressalva", ("precisao",),
          _ctx_fonte("ERP"), _corpo_fonte("ERP"), preferencia=1),
    Plano("P-MANTER-PLANILHA", "fonte_confiavel", "manter a planilha e registrar ressalva", ("tempestividade",),
          _ctx_fonte("planilha"), _corpo_fonte("planilha")),
    Plano("P-CONSULTAR-CIN", "explicar_desvio", "perguntar ao AG-CIN se lançamentos irregulares inflam a conta",
          ("precisao",), _ctx_consultar_cin, _corpo_consultar_cin, _continuar_consultar_cin),
    Plano("P-SEM-EXPLICACAO", "explicar_desvio", "seguir sem atribuição (desvio bruto)", ("tempestividade",),
          _sempre("sempre aplicável (fallback)"), _corpo_sem_explicacao),
    Plano("P-SINALIZAR", "alertar_desvio", "sinalizar desvio orçamentário", ("precisao", "tempestividade"),
          _sempre("desvio acima do limiar"), _corpo_alertar),
    Plano("P-ENCAMINHAR-CONTROLE", "encaminhar_controle", "classificar como problema de controle interno",
          ("precisao",), _sempre("desvio explicado por lançamento contestado"), _corpo_encaminhar),
    Plano("P-FORECAST-AJUSTADO", "projetar_forecast", "run-rate sem valores contestados", ("precisao",),
          _ctx_forecast_ajustado, _corpo_forecast(True), preferencia=1),
    Plano("P-RUN-RATE", "projetar_forecast", "run-rate do realizado acumulado", ("tempestividade",),
          _sempre("método padrão"), _corpo_forecast(False)),
    Plano("P-CONSOLIDAR", "avaliar_execucao", "consolidar a avaliação e responder aos solicitantes",
          ("precisao", "tempestividade"), _sempre("todas as decisões da competência tomadas"), _corpo_consolidar),
]


class AgenteOrcamento(AgenteBDI):
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"precisao": 3, "tempestividade": 1}

    def __init__(self, bus, gateway):
        super().__init__("AG-ORC", bus, gateway)
        self.conhecimento = {
            "limiar_percentual": LIMIAR_PERCENTUAL,
            "limiar_absoluto": LIMIAR_ABSOLUTO,
            "metodo_forecast": "run-rate: realizado acumulado x 3 / meses decorridos",
            "fonte_primaria": "ERP",
            "tolerancia_fonte": TOLERANCIA_FONTE,
        }
        self.estado = {"avaliacao": None, "tarefas": {}}

    # ---- percepção ---------------------------------------------------------
    def on_message(self, msg) -> None:
        if msg.protocol == "PROT-DEL" and msg.performative == "request":
            self.send(msg.sender, "agree", "PROT-DEL", msg.conversation_id)
            if msg.content.get("tarefa") != "orcado_x_realizado":
                self.send(msg.sender, "failure", "PROT-DEL", msg.conversation_id,
                          {"motivo": f"tarefa desconhecida: {msg.content.get('tarefa')}"}, delay=1 + self.latencia)
                return
            self.iniciar(msg.content.get("competencia"), (msg.sender, msg.conversation_id, "PROT-DEL"))
        elif msg.protocol == "PROT-QRY" and msg.performative == "query-ref":
            if msg.content.get("assunto") != "desvios":
                self.send(msg.sender, "refuse", "PROT-QRY", msg.conversation_id,
                          {"motivo": f"assunto desconhecido: {msg.content.get('assunto')}"})
                return
            self.iniciar(msg.content.get("competencia"), (msg.sender, msg.conversation_id, "PROT-QRY"))
        elif msg.protocol == "PROT-QRY":  # resposta (ou timeout) de uma consulta que o AG-ORC fez
            self.entregar_resposta(msg)

    def iniciar(self, competencia, solicitante) -> None:
        c = competencia or self.gw.ambiente.principal
        t = self.estado["tarefas"].get(c)
        if t is not None and t["avaliacao"] is not None:
            t["solicitantes"].append(solicitante)
            self.responder(c)
            return
        if t is not None:  # avaliação em andamento: só acrescenta quem espera a resposta
            t["solicitantes"].append(solicitante)
            return
        cid = solicitante[1]
        planilha = self.gw.call(self.id, "planilhas.orcamento", cid, competencia=c)
        erp = self.gw.call(self.id, "erp.realizado_por_conta", cid, competencia=c)
        contas = [linha["conta"] for linha in planilha["dados"]["contas"]]
        self.estado["tarefas"][c] = {"cid": cid, "contas": contas, "meses": planilha["dados"]["meses_decorridos"],
                                     "solicitantes": [solicitante], "avaliacao": None, "ressalvas": [],
                                     "proveniencia": planilha["proveniencia"]}
        for linha in planilha["dados"]["contas"]:
            conta = linha["conta"]
            self.crencas.revisar(_k("orcado", c, conta), linha["orcado_acumulado"], "mcp://planilhas/orcamento", cid)
            self.crencas.revisar(_k("realizado_planilha", c, conta), linha["realizado_acumulado"],
                                 "mcp://planilhas/orcamento", cid)
            self.crencas.revisar(_k("realizado_erp", c, conta), erp["dados"]["realizado"][conta],
                                 "mcp://erp/realizado_por_conta", cid)
            if abs(linha["realizado_acumulado"] - erp["dados"]["realizado"][conta]) <= TOLERANCIA_FONTE:
                self.crencas.revisar(_k("realizado", c, conta), linha["realizado_acumulado"],
                                     "planilha = ERP", cid)
        self.ciclo()

    # ---- geração de opções e reconsideração ----------------------------------
    def tarefa(self, c) -> dict:
        return self.estado["tarefas"][c]

    def chave_params(self, params) -> str:
        return "|".join(f"{v}" for _, v in sorted(params.items()))

    def acima(self, c, conta, desvio) -> bool:
        orcado = self.crencas.get(_k("orcado", c, conta))
        return (abs(desvio) * 100 >= orcado * self.conhecimento["limiar_percentual"]
                and abs(desvio) >= self.conhecimento["limiar_absoluto"])

    def desvio_bruto(self, c, conta):
        realizado = self.crencas.get(_k("realizado", c, conta))
        return None if realizado is None else realizado - self.crencas.get(_k("orcado", c, conta))

    def desvio_ajustado(self, c, conta):
        bruto = self.desvio_bruto(c, conta)
        return bruto - (self.crencas.get(_k("contestado", c, conta)) or 0)

    def opcoes(self):
        ops = []
        for c, t in self.estado["tarefas"].items():
            if t["avaliacao"] is not None:
                continue
            cid, pendente = t["cid"], False
            for conta in t["contas"]:
                p = {"c": c, "conta": conta}
                if self.crencas.get(_k("realizado", c, conta)) is None:
                    pl = self.crencas.get(_k("realizado_planilha", c, conta))
                    erp = self.crencas.get(_k("realizado_erp", c, conta))
                    ops.append(("fonte_confiavel", p, 1, f"planilha {brl(pl)} x ERP {brl(erp)}", cid))
                    pendente = True
                    continue
                bruto = self.desvio_bruto(c, conta)
                if not self.acima(c, conta, bruto):
                    continue
                if _k("explicacao", c, conta) not in self.crencas:
                    ops.append(("explicar_desvio", p, 2, f"desvio de {brl(bruto)} acima do limiar", cid))
                    ops.append(("alertar_desvio", p, 3, f"desvio de {brl(bruto)} acima do limiar", cid))
                    pendente = True
                elif not self.acima(c, conta, self.desvio_ajustado(c, conta)):
                    ops.append(("encaminhar_controle", p, 3,
                                f"desvio ajustado {brl(self.desvio_ajustado(c, conta))} abaixo do limiar", cid))
            if pendente or any(i.desejo.params.get("c") == c and i.desejo.tipo != "avaliar_execucao"
                               for i in self.pendentes()):
                continue
            if _k("forecast", c) not in self.crencas:
                ops.append(("projetar_forecast", {"c": c}, 4, "explicações concluídas", cid))
            else:
                ops.append(("avaliar_execucao", {"c": c}, 5, "todas as decisões tomadas", cid))
        return ops

    def desejo_ativo(self, d):
        if d.tipo == "alertar_desvio":
            c, conta = d.params["c"], d.params["conta"]
            ajustado = self.desvio_ajustado(c, conta)
            if not self.acima(c, conta, ajustado):
                contestado = self.crencas.get(_k("contestado", c, conta)) or 0
                return False, (f"desvio ajustado {brl(ajustado)} abaixo do limiar após AG-CIN contestar "
                               f"{brl(contestado)}")
        return True, ""

    # ---- saída ------------------------------------------------------------------
    def consolidar(self, c) -> dict:
        t = self.tarefa(c)
        forecast = self.crencas.get(_k("forecast", c))
        contas, sinalizadas, atribuidas = [], [], []
        for conta in t["contas"]:
            classe = self.crencas.get(_k("classificacao", c, conta), "dentro_do_limiar")
            linha = {"conta": conta, "orcado_acumulado": self.crencas.get(_k("orcado", c, conta)),
                     "realizado_acumulado": self.crencas.get(_k("realizado", c, conta)),
                     "desvio": self.desvio_bruto(c, conta), "desvio_ajustado": self.desvio_ajustado(c, conta),
                     "sinalizado": classe == "desvio_orcamentario", "classificacao": classe,
                     "fonte": self.crencas.get(_k("fonte", c, conta), "planilha = ERP"),
                     "forecast_trimestre": forecast[conta]}
            contas.append(linha)
            if classe == "desvio_orcamentario":
                sinalizadas.append(conta)
            elif classe == "atribuido_a_controle":
                atribuidas.append(conta)
        avaliacao = {
            "desvios": contas, "sinalizadas": sorted(sinalizadas), "atribuidas_a_controle": sorted(atribuidas),
            "divergencias": sorted(x["conta"] for x in contas if x["fonte"] not in ("planilha = ERP",)),
            "ressalvas": list(t["ressalvas"]),
            "totais": {"orcado_acumulado": sum(x["orcado_acumulado"] for x in contas),
                       "realizado_acumulado": sum(x["realizado_acumulado"] for x in contas),
                       "forecast_trimestre": sum(forecast.values())},
            "metodo_forecast": self.crencas.get(_k("metodo_forecast", c)),
            "proveniencia": t["proveniencia"],
        }
        t["avaliacao"] = avaliacao
        self.estado["avaliacao"] = avaliacao
        return avaliacao

    def responder(self, c) -> None:
        t = self.tarefa(c)
        a = t["avaliacao"]
        for destino, cid, protocolo in t["solicitantes"]:
            if protocolo == "PROT-DEL":
                self.send(destino, "inform", "PROT-DEL", cid, a, delay=1 + self.latencia)
            else:
                self.send(destino, "inform", "PROT-QRY", cid,
                          {"desvios": a["desvios"], "totais": a["totais"], "proveniencia": a["proveniencia"]})
        t["solicitantes"] = []

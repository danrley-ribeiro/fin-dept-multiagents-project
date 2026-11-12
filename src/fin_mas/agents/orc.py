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

DSM3 — cognição assistida (ADR-008), só com proponentes ligados (níveis `local` e `llm`):
o agente percebe também o texto livre da planilha e o histórico mensal, recebe hipóteses
sobre a causa de cada desvio (`causa_controle`, `efeito_temporal`) e adota o desejo
epistêmico `verificar_hipotese(conta)`:

  2 verificar_hipotese(conta)  hipótese validada ainda sem evidência

  P-CONFERIR-EVIDENCIA      o AG-CIN já respondeu: a resposta confirma ou refuta, sem mensagem nova
  P-VERIFICAR-COM-CIN       a consulta normal se perdeu: nova consulta, se couber no prazo e no teto
  P-VERIFICAR-NO-HISTORICO  confere o padrão de calendário em todos os trimestres do histórico
  P-ARQUIVAR-HIPOTESE       sem evidência disponível: a hipótese é arquivada e nada muda

A hipótese nunca classifica um desvio: quem muda a classificação é a crença revisada pela
evidência (a resposta do AG-CIN, o cálculo sobre o histórico), pelos planos de sempre.
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.core.inferencia import EsquemaHipoteses, resolver
from fin_mas.env.dataset import LIMIAR_ABSOLUTO, LIMIAR_PERCENTUAL, brl
from fin_mas.mcp.gateway import ToolIndisponivel

PRAZO_CONSULTA = 10  # ticks lógicos até a expiração da query-ref ao AG-CIN
TOLERANCIA_FONTE = 1_00  # R$ 1,00: abaixo disso planilha e ERP são considerados iguais
MAX_VERIFICACOES = 3  # consultas de verificação de hipótese por tarefa (teto de custo de coordenação)
FOLGA_RESPOSTA = 5  # ticks entre a evidência chegar e a avaliação ser entregue ao solicitante
MIN_TRIMESTRES = 2  # trimestres completos do histórico exigidos para confirmar um padrão de calendário
TIPOS_HIPOTESE = {
    "causa_controle": "o desvio vem de lançamento irregular: problema de controle interno, não de orçamento",
    "efeito_temporal": "o desvio é efeito de calendário: gasto que se repete na mesma época e se compensa no trimestre",
}


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
    verificando = next((d for d in a.desejos.values() if d.tipo == "verificar_hipotese" and d.estado == "ativo"
                        and d.params["c"] == c and d.params["conta"] == conta), None)
    if verificando is not None:  # só existe com proponentes ligados (ADR-008)
        a.suspender(i, "desejo:" + verificando.id, "só sinaliza depois de verificar a hipótese sobre o desvio")
        return
    desvio = a.desvio_ajustado(c, conta)
    a.crencas.revisar(_k("classificacao", c, conta), "desvio_orcamentario", "plano " + i.plano.id, i.desejo.cid)
    lim = a.conhecimento
    a.decide(i.desejo.cid, f"desvio >= {lim['limiar_percentual']}% e >= {lim['limiar_absoluto']} centavos "
             f"após atribuição (porte {lim.get('porte', 'media')})",
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


# ---- verificação de hipóteses (ADR-008): só a evidência muda crença -----------------
def _hip(a, d):
    return a.hipoteses[d.params["h"]]


def _sem_atribuicao(conta) -> str:
    return f"desvio de {conta} sinalizado sem atribuição: AG-CIN indisponível"


def _ctx_conferir(a, d):
    h, c, conta = _hip(a, d), d.params["c"], d.params["conta"]
    if h.tipo != "causa_controle":
        return False, "só se aplica a hipótese de causa de controle"
    respondida = isinstance(a.crencas.get(_k("explicacao", c, conta)), list)
    return respondida, ("o AG-CIN já respondeu sobre a conta" if respondida else "ainda sem resposta do AG-CIN")


def _corpo_conferir(a, i):
    h, c, conta = _hip(a, i.desejo), i.desejo.params["c"], i.desejo.params["conta"]
    contestado = a.crencas.get(_k("contestado", c, conta)) or 0
    a.concluir_hipotese(i, h, contestado > 0, a.crencas.fonte(_k("contestado", c, conta)),
                        f"AG-CIN contesta {brl(contestado)} em {conta}" if contestado > 0
                        else f"AG-CIN não contesta lançamentos de {conta}")


def _ctx_verificar_cin(a, d):
    h, c, conta = _hip(a, d), d.params["c"], d.params["conta"]
    if h.tipo != "causa_controle":
        return False, "só se aplica a hipótese de causa de controle"
    if a.crencas.get(_k("explicacao", c, conta)) != "indisponível":
        return False, "a consulta normal ao AG-CIN não falhou"
    if "AG-CIN" not in a.bus.agents:
        return False, "AG-CIN fora do diretório de agentes"
    t = a.tarefa(c)
    if t["verificacoes"] >= MAX_VERIFICACOES:
        return False, f"teto de {MAX_VERIFICACOES} verificações por tarefa atingido"
    if t["prazo"] is not None and a.bus.now + PRAZO_CONSULTA + FOLGA_RESPOSTA > t["prazo"]:
        return False, f"não cabe no prazo do solicitante (t={t['prazo']})"
    return True, "hipótese validada justifica nova consulta ao AG-CIN, dentro do prazo"


def _corpo_verificar_cin(a, i):
    h, c, conta = _hip(a, i.desejo), i.desejo.params["c"], i.desejo.params["conta"]
    a.tarefa(c)["verificacoes"] += 1
    qid = a.bus.new_conversation_id("QRY")
    a.bus.audit.record(a.bus.now, "link", conversation_id=i.desejo.cid, filha=qid,
                       subtarefa=f"verificar hipótese {h.id} ({conta})", agente=a.id)
    a.send("AG-CIN", "query-ref", "PROT-QRY", qid, {"assunto": "irregularidades", "conta": conta, "competencia": c},
           reply_by=a.bus.now + PRAZO_CONSULTA)
    a.marcar_hipotese(h, "em_verificacao", f"consulta {qid} ao AG-CIN")
    a.suspender(i, qid, f"aguarda AG-CIN sobre a hipótese {h.id}")


def _continuar_verificar_cin(a, i, msg):
    h, c, conta = _hip(a, i.desejo), i.desejo.params["c"], i.desejo.params["conta"]
    valor, fonte = msg.content["valor_contestado"], f"AG-CIN ({msg.conversation_id})"
    a.crencas.revisar(_k("contestado", c, conta), valor, fonte, i.desejo.cid)
    a.crencas.revisar(_k("explicacao", c, conta), [lanc["lancamento"] for lanc in msg.content["lancamentos"]],
                      fonte, i.desejo.cid)
    t = a.tarefa(c)  # o AG-CIN respondeu: a ressalva de indisponibilidade deixou de ser verdadeira
    t["ressalvas"] = [r for r in t["ressalvas"] if r != _sem_atribuicao(conta)]
    a.concluir_hipotese(i, h, valor > 0, fonte, f"AG-CIN contesta {brl(valor)} em {conta}" if valor > 0
                        else f"AG-CIN não contesta lançamentos de {conta}")


def _ctx_historico(a, d):
    h, c, conta = _hip(a, d), d.params["c"], d.params["conta"]
    if h.tipo != "efeito_temporal":
        return False, "só se aplica a hipótese de efeito de calendário"
    tem = _k("historico", c, conta) in a.crencas
    return tem, "há histórico mensal da conta" if tem else "sem histórico mensal da conta"


def padrao_de_calendario(serie, mes_no_trimestre, limiar_percentual) -> dict:
    """Confere, em cada trimestre completo do histórico, se o acumulado até este mês passou do
    orçado além do limiar e se o trimestre mesmo assim fechou dentro do limiar."""
    trimestres, atual = [], []
    for m in serie:
        if m["mes_no_trimestre"] == 1:
            atual = []
        atual.append(m)
        if m["mes_no_trimestre"] == 3 and len(atual) == 3:
            trimestres.append(atual)
    repetiu = fechou = 0
    for tri in trimestres:
        orcado_ate = sum(m["orcado"] for m in tri[:mes_no_trimestre])
        excesso = sum(m["realizado"] for m in tri[:mes_no_trimestre]) - orcado_ate
        orcado_tri = sum(m["orcado"] for m in tri)
        fim = sum(m["realizado"] for m in tri) - orcado_tri
        repetiu += excesso * 100 >= orcado_ate * limiar_percentual
        fechou += abs(fim) * 100 < orcado_tri * limiar_percentual
    n = len(trimestres)
    return {"trimestres": n, "repetiu": int(repetiu), "fechou_no_orcado": int(fechou),
            "confirmado": n >= MIN_TRIMESTRES and repetiu == n and fechou == n}


def _corpo_historico(a, i):
    h, c, conta = _hip(a, i.desejo), i.desejo.params["c"], i.desejo.params["conta"]
    r = padrao_de_calendario(a.crencas.get(_k("historico", c, conta)), a.tarefa(c)["meses"],
                             a.conhecimento["limiar_percentual"])
    fonte = "cálculo sobre " + a.crencas.fonte(_k("historico", c, conta))
    if r["confirmado"]:
        a.crencas.revisar(_k("padrao_calendario", c, conta), r, fonte, i.desejo.cid)
        a.tarefa(c)["ressalvas"].append(
            f"desvio de {conta} repete o padrão de {r['trimestres']} trimestres anteriores, que fecharam dentro "
            f"do orçado: efeito de calendário")
    a.concluir_hipotese(i, h, r["confirmado"], fonte,
                        f"padrão repetido em {r['repetiu']} de {r['trimestres']} trimestres; "
                        f"{r['fechou_no_orcado']} fecharam dentro do orçado")


def _corpo_arquivar(a, i):
    h = _hip(a, i.desejo)
    a.marcar_hipotese(h, "arquivada", "sem evidência disponível dentro do prazo e do teto de verificações")
    a.concluir(i, "arquivada", f"hipótese {h.id} arquivada: nada muda na avaliação")


PLANOS = [
    Plano("P-CONFERIR-EVIDENCIA", "verificar_hipotese", "conferir a hipótese com a resposta que o AG-CIN já deu",
          ("precisao", "tempestividade"), _ctx_conferir, _corpo_conferir, preferencia=2),
    Plano("P-VERIFICAR-COM-CIN", "verificar_hipotese", "consultar de novo o AG-CIN para confirmar ou refutar a hipótese",
          ("precisao",), _ctx_verificar_cin, _corpo_verificar_cin, _continuar_verificar_cin, preferencia=1),
    Plano("P-VERIFICAR-NO-HISTORICO", "verificar_hipotese", "conferir o padrão de calendário no histórico mensal",
          ("precisao",), _ctx_historico, _corpo_historico, preferencia=1),
    Plano("P-ARQUIVAR-HIPOTESE", "verificar_hipotese", "arquivar a hipótese sem evidência (nada muda)",
          ("tempestividade",), _sempre("sempre aplicável (fallback)"), _corpo_arquivar),
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
    PAPEL = "ROLE-ORC"
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
            self.iniciar(msg.content.get("competencia"), (msg.sender, msg.conversation_id, "PROT-DEL"), msg.reply_by)
        elif msg.protocol == "PROT-QRY" and msg.performative == "query-ref":
            if msg.content.get("assunto") != "desvios":
                self.send(msg.sender, "refuse", "PROT-QRY", msg.conversation_id,
                          {"motivo": f"assunto desconhecido: {msg.content.get('assunto')}"})
                return
            self.iniciar(msg.content.get("competencia"), (msg.sender, msg.conversation_id, "PROT-QRY"), msg.reply_by)
        elif msg.protocol == "PROT-QRY":  # resposta (ou timeout) de uma consulta que o AG-ORC fez
            self.entregar_resposta(msg)

    def iniciar(self, competencia, solicitante, prazo=None) -> None:
        c = competencia or self.gw.ambiente.principal
        t = self.estado["tarefas"].get(c)
        if t is not None and t["avaliacao"] is not None:
            t["solicitantes"].append(solicitante)
            self.responder(c)
            return
        if t is not None:  # avaliação em andamento: só acrescenta quem espera a resposta
            t["solicitantes"].append(solicitante)
            if prazo is not None:  # vale o prazo mais apertado entre os solicitantes
                t["prazo"] = prazo if t["prazo"] is None else min(t["prazo"], prazo)
            return
        cid = solicitante[1]
        self._perceber_perfil(cid, c)
        planilha = self.ferramenta("planilhas.orcamento", cid, competencia=c)
        try:
            erp = self.ferramenta("erp.realizado_por_conta", cid, competencia=c)["dados"]["realizado"]
        except ToolIndisponivel:  # empresa sem ERP: a planilha é a única fonte, sem reconciliação possível
            erp = None
        contas = [linha["conta"] for linha in planilha["dados"]["contas"]]
        self.estado["tarefas"][c] = {"cid": cid, "contas": contas, "meses": planilha["dados"]["meses_decorridos"],
                                     "solicitantes": [solicitante], "avaliacao": None, "ressalvas": [],
                                     "proveniencia": planilha["proveniencia"], "prazo": prazo, "verificacoes": 0}
        for linha in planilha["dados"]["contas"]:
            conta = linha["conta"]
            self.crencas.revisar(_k("orcado", c, conta), linha["orcado_acumulado"], "mcp://planilhas/orcamento", cid)
            self.crencas.revisar(_k("realizado_planilha", c, conta), linha["realizado_acumulado"],
                                 "mcp://planilhas/orcamento", cid)
            if erp is None:
                self.crencas.revisar(_k("realizado", c, conta), linha["realizado_acumulado"],
                                     "planilha (empresa sem ERP)", cid)
                continue
            self.crencas.revisar(_k("realizado_erp", c, conta), erp[conta], "mcp://erp/realizado_por_conta", cid)
            if abs(linha["realizado_acumulado"] - erp[conta]) <= TOLERANCIA_FONTE:
                self.crencas.revisar(_k("realizado", c, conta), linha["realizado_acumulado"],
                                     "planilha = ERP", cid)
        self.ciclo()

    def _perceber_perfil(self, cid, c) -> None:
        """Regras do porte da empresa (base normativa): limiares, fonte primária e pesos dos desejos."""
        p = self.ferramenta("normas.perfil", cid, competencia=c)["dados"]
        self.crencas.revisar("porte", p["porte"], "mcp://normas/perfil", cid)
        self.crencas.revisar("tem_erp", p["tem_erp"], "mcp://normas/perfil", cid)
        self.conhecimento.update(porte=p["porte"], limiar_percentual=p["limiar_desvio"]["percentual"],
                                 limiar_absoluto=p["limiar_desvio"]["absoluto"], fonte_primaria=p["fonte_primaria"],
                                 norma_contabil=p["norma_contabil"], versao_normas=p["versao"])
        self.DESEJOS_PERMANENTES = dict(p["pesos_orc"])  # a utilidade dos planos muda com o porte

    # ---- hipóteses: percepções extras, gatilho e conclusão (ADR-008) -------------
    def gatilhos_inferencia(self):
        gatilhos = []
        for c, t in self.estado["tarefas"].items():
            chave = f"desvios@{c}"
            if t["avaliacao"] is not None or chave in self._gatilhos_usados:
                continue
            if any(self.crencas.get(_k("realizado", c, conta)) is None for conta in t["contas"]):
                continue  # ainda há fonte em reconciliação: o desvio não está definido
            acima = [conta for conta in t["contas"] if self.acima(c, conta, self.desvio_bruto(c, conta))]
            if not acima:
                continue
            self._perceber_contexto(c, t, acima)
            contas, valores = [], {}
            for conta in acima:
                chaves = {"orcado": _k("orcado", c, conta), "realizado": _k("realizado", c, conta)}
                x = {"conta": conta, "chaves": chaves, "mes_no_trimestre": t["meses"],
                     "limiar_percentual": self.conhecimento["limiar_percentual"],
                     "orcado": brl(self.crencas.get(chaves["orcado"])),
                     "realizado": brl(self.crencas.get(chaves["realizado"])),
                     "desvio": brl(self.desvio_bruto(c, conta))}
                valores[chaves["orcado"]], valores[chaves["realizado"]] = x["orcado"], x["realizado"]
                if _k("observacao", c, conta) in self.crencas:
                    chaves["observacao"] = _k("observacao", c, conta)
                    x["observacao"] = self.crencas.get(chaves["observacao"])
                    valores[chaves["observacao"]] = f"\"{x['observacao']}\""
                if _k("historico", c, conta) in self.crencas:
                    chaves["historico"] = _k("historico", c, conta)
                    x["historico"] = self.crencas.get(chaves["historico"])
                    valores[chaves["historico"]] = f"dos {len(x['historico'])} meses anteriores"
                contas.append(x)
            evidencias = tuple(sorted({k for x in contas for k in x["chaves"].values()}))
            t["valores_hipoteses"] = valores
            gatilhos.append({"chave": chave, "cid": t["cid"], "tarefa": "causas dos desvios orçamentários",
                             "competencia": c,
                             "contexto": {"competencia": c, "porte": self.conhecimento.get("porte"), "contas": contas},
                             "esquema": EsquemaHipoteses(TIPOS_HIPOTESE, tuple(acima), evidencias, valores=valores)})
        return gatilhos

    def _perceber_contexto(self, c, t, contas) -> None:
        """Texto livre da planilha e histórico mensal das contas com desvio: percepções, com fonte."""
        cid = t["cid"]
        obs = self.ferramenta("planilhas.observacoes", cid, competencia=c)
        for conta, texto in obs["dados"]["observacoes"].items():
            if conta in contas:
                self.crencas.revisar(_k("observacao", c, conta), texto, obs["proveniencia"]["fonte"], cid)
        try:
            hist = self.ferramenta("erp.historico", cid, competencia=c)
        except ToolIndisponivel:
            return  # empresa sem ERP: segue só com o texto livre
        for conta, serie in hist["dados"]["historico"].items():
            if conta in contas and serie:
                self.crencas.revisar(_k("historico", c, conta), serie, hist["proveniencia"]["fonte"], cid)

    def concluir_hipotese(self, i, h, confirmada: bool, fonte: str, motivo: str) -> None:
        self.marcar_hipotese(h, "confirmada" if confirmada else "refutada", motivo, fonte)
        self.decide(i.desejo.cid, "hipótese só muda a avaliação depois de evidência determinística (NORM-11)",
                    {"hipotese": h.id, "tipo": h.tipo, "conta": h.alvo, "origens": list(h.origens), "evidencia": fonte},
                    h.estado)
        self.concluir(i, h.estado, f"hipótese {h.id} {h.estado}: {motivo}")

    def insights(self, c) -> list[str]:
        """Frases sobre as hipóteses da competência, com origem e evidência (números vêm das crenças)."""
        t, linhas = self.tarefa(c), []
        for h in self.hipoteses.values():
            if h.competencia != c:
                continue
            texto = resolver(h.justificativa, h.alvo, t.get("valores_hipoteses", {}))
            desfecho = {"confirmada": f"confirmada por {h.verificacao}", "refutada": f"refutada por {h.verificacao}",
                        "arquivada": "arquivada sem evidência", "em_verificacao": "em verificação",
                        "proposta": "sem verificação"}[h.estado]
            linhas.append(f"{h.alvo}: hipótese {h.id} ({h.tipo}; origem {', '.join(h.origens)}) {desfecho}. {texto}")
        return linhas

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
                for h in self.hipoteses.values():  # vazio na cognição básica
                    if (h.competencia, h.alvo, h.estado) != (c, conta, "proposta"):
                        continue
                    if h.tipo == "causa_controle" and _k("explicacao", c, conta) not in self.crencas:
                        continue  # a consulta normal ao AG-CIN ainda vai responder
                    ops.append(("verificar_hipotese", {"c": c, "conta": conta, "h": h.id}, 2,
                                f"hipótese {h.id} ({h.tipo}) ainda sem evidência", cid))
                    pendente = True
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
                     "fonte": self.crencas.get(_k("fonte", c, conta),
                                               "planilha = ERP" if self.crencas.get("tem_erp", True) else "planilha"),
                     "forecast_trimestre": forecast[conta]}
            contas.append(linha)
            if classe == "desvio_orcamentario":
                sinalizadas.append(conta)
            elif classe == "atribuido_a_controle":
                atribuidas.append(conta)
        avaliacao = {
            "desvios": contas, "sinalizadas": sorted(sinalizadas), "atribuidas_a_controle": sorted(atribuidas),
            "divergencias": sorted(x["conta"] for x in contas if x["fonte"] not in ("planilha = ERP", "planilha")),
            "ressalvas": list(t["ressalvas"]),
            "totais": {"orcado_acumulado": sum(x["orcado_acumulado"] for x in contas),
                       "realizado_acumulado": sum(x["realizado_acumulado"] for x in contas),
                       "forecast_trimestre": sum(forecast.values())},
            "metodo_forecast": self.crencas.get(_k("metodo_forecast", c)),
            "proveniencia": t["proveniencia"],
        }
        if self.proponentes:  # cognição local ou com LLM: hipóteses e insights acompanham a avaliação
            avaliacao["hipoteses"] = [h.resumo() for h in self.hipoteses.values() if h.competencia == c]
            avaliacao["insights"] = self.insights(c)
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

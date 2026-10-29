"""AG-CIN — Agente de Controles Internos, cognitivo (BDI) com autonomia de veto.

Crenças: violações de cada lançamento (alçada, SoD, duplicidade, competência),
correções aplicadas, waivers e ciclos de correção por verificação.

Desejos permanentes concorrentes: conformidade (peso 10) e prazo do fechamento (peso 5).
O desejo `parecer(CMP)` é atendido por quatro planos; a utilidade de cada um é a soma
dos pesos dos desejos permanentes que ele serve:

  P-APROVAR             conformidade + prazo   sem violações
  P-APONTAR             conformidade + prazo   só violações não críticas
  P-VETAR-COM-CORRECAO  conformidade + prazo   críticas, todas corrigíveis, ciclo de correção disponível
  P-VETAR               conformidade           críticas

Com críticas corrigíveis os dois vetos são aplicáveis e vence o que preserva o prazo
(sugere correção). Após uma correção, as crenças são revisadas por nova percepção e a
intenção é reconsiderada: sem críticas, troca o veto por aprovar/apontar; com críticas
restantes, mantém o compromisso de vetar, agora sem novo ciclo de correção.
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.env.dataset import EFEITO_ORCAMENTARIO
from fin_mas.core.message import Message

MAX_CICLOS_CORRECAO = 1
CORRECAO_POR_REGRA = {"alcada": "reaprovar", "sod": "reaprovar", "duplicidade": "estornar",
                      "competencia": "reclassificar"}


def _ctx_aprovar(a, d):
    achados = a.achados(d)
    return (not achados, "nenhuma violação" if not achados else f"{len(achados)} violação(ões)")


def _ctx_apontar(a, d):
    achados = a.achados(d)
    if not achados:
        return False, "nada a apontar"
    if a.criticos(d):
        return False, "há violação crítica"
    return True, "só violações não críticas"


def _ctx_vetar_com_correcao(a, d):
    criticos = a.criticos(d)
    if not criticos:
        return False, "sem violação crítica"
    ciclos = a.crencas.get(f"ciclos_correcao[{d.params['cmp']}]", 0)
    if ciclos >= MAX_CICLOS_CORRECAO:
        return False, f"ciclo de correção já usado ({ciclos}/{MAX_CICLOS_CORRECAO})"
    nao_corrigiveis = [x for x in criticos if x["regra"] not in CORRECAO_POR_REGRA]
    if nao_corrigiveis:
        return False, "há crítica sem correção conhecida"
    return True, f"{len(criticos)} crítica(s), todas corrigíveis"


def _ctx_vetar(a, d):
    criticos = a.criticos(d)
    return (bool(criticos), f"{len(criticos)} crítica(s)" if criticos else "sem violação crítica")


def _corpo_parecer(evento, intencao_legado):
    def corpo(a, i):
        d = i.desejo
        cmp_id = d.params["cmp"]
        achados = a.achados(d)
        criticos = a.criticos(d)
        conteudo = {"achados": achados, "versao_normas": a.crencas.get("versao_normas"),
                    "proveniencia": a.estado["pareceres"][cmp_id]["proveniencia"]}
        if evento == "veto":
            sugeridas = a.correcoes_sugeridas(criticos) if i.plano.id == "P-VETAR-COM-CORRECAO" else []
            conteudo["correcoes_sugeridas"] = sugeridas
            conteudo["opcoes"] = (["corrigir"] if sugeridas else []) + ["waiver", "bloquear"]
        a.estado["intencao"] = intencao_legado
        regra = {"veto": "NORM-04: não conformidade crítica veta a publicação",
                 "conforme": "nenhuma violação nas regras de alçada, SoD, duplicidade e competência",
                 "nao_conforme_nao_critico": "só violações não críticas: libera com ressalva"}[evento]
        a.decide(cmp_id, f"parecer {evento} via {i.plano.id}: {regra}",
                 {"lancamentos": a.estado["pareceres"][cmp_id]["lancamentos"],
                  "normas": a.crencas.get("versao_normas")},
                 {"achados": len(achados), "criticos": len(criticos)})
        a.send(a.estado["pareceres"][cmp_id]["solicitante"], evento, "PROT-CMP", cmp_id, conteudo, delay=2)
        if evento == "veto":
            a.suspender(i, "cmp:" + cmp_id, "veto aguarda correção, waiver ou prazo")
        else:
            a.concluir(i, evento, f"parecer {evento} emitido")
    return corpo


PLANOS = [
    Plano("P-APROVAR", "parecer", "emitir parecer conforme", ("conformidade", "prazo"),
          _ctx_aprovar, _corpo_parecer("conforme", "aprovar")),
    Plano("P-APONTAR", "parecer", "liberar com ressalvas não críticas", ("conformidade", "prazo"),
          _ctx_apontar, _corpo_parecer("nao_conforme_nao_critico", "apontar")),
    Plano("P-VETAR-COM-CORRECAO", "parecer", "vetar e sugerir correções que destravam o fechamento",
          ("conformidade", "prazo"), _ctx_vetar_com_correcao, _corpo_parecer("veto", "vetar"), preferencia=1),
    Plano("P-VETAR", "parecer", "vetar a publicação", ("conformidade",), _ctx_vetar, _corpo_parecer("veto", "vetar")),
]


class AgenteControlesInternos(AgenteBDI):
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"conformidade": 10, "prazo": 5}

    def __init__(self, bus, gateway):
        super().__init__("AG-CIN", bus, gateway)
        self.conhecimento = {"regras": ["alcada", "sod", "duplicidade", "competencia"],
                             "correcao_por_regra": dict(CORRECAO_POR_REGRA),
                             "efeito_orcamentario": sorted(EFEITO_ORCAMENTARIO),
                             "max_ciclos_correcao": MAX_CICLOS_CORRECAO}
        self.estado = {"crencas": {}, "intencao": None, "pareceres": {}, "conhecidos": {}}

    # ---- mensagens ----------------------------------------------------------
    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-CMP":
            if msg.performative == "request":
                self._verificar(msg)
            elif msg.performative == "correcao":
                self._correcao(msg)
            elif msg.performative in ("waiver_humano", "prazo_esgotado"):
                self._decisao_humana(msg)
        else:
            super().on_message(msg)

    def _verificar(self, msg: Message) -> None:
        cmp_id = msg.conversation_id
        c = msg.content.get("competencia") or self.gw.ambiente.principal
        self.estado["pareceres"][cmp_id] = {"solicitante": msg.sender, "competencia": c}
        self.perceber(cmp_id, c)
        self._adotar_desejo("parecer", {"cmp": cmp_id}, 1, "verificação do pacote solicitada", cmp_id)
        self.ciclo()

    def _correcao(self, msg: Message) -> None:
        cmp_id = msg.conversation_id
        ciclos = self.crencas.get(f"ciclos_correcao[{cmp_id}]", 0) + 1
        self.crencas.revisar(f"ciclos_correcao[{cmp_id}]", ciclos, "correção informada pelo AG-ORQ", cmp_id)
        self.perceber(cmp_id, self.estado["pareceres"][cmp_id]["competencia"])  # nova percepção, não confiança cega
        i = self.intencao_aguardando("cmp:" + cmp_id)
        if i is None:
            return
        restantes = len(self.criticos(i.desejo))
        self._registrar("intention", cmp_id, intencao=i.id, desejo=i.desejo.id, plano=i.plano.id,
                        evento="reconsiderada", motivo=f"correção recebida: {restantes} crítica(s) restante(s)")
        self._encerrar_intencao(i, "abandonada", "substituída após reavaliação das crenças")
        self._selecionar_e_executar(i.desejo, tentados=[])

    def _decisao_humana(self, msg: Message) -> None:
        cmp_id = msg.conversation_id
        i = self.intencao_aguardando("cmp:" + cmp_id)
        if msg.performative == "waiver_humano":
            self.crencas.revisar(f"waiver[{cmp_id}]", msg.content.get("justificativa"), "decisão humana (APR)", cmp_id)
            if i is not None:
                self._encerrar_intencao(i, "abandonada", "waiver humano: autoridade superior assume o risco")
                self._encerrar_desejo(i.desejo, "descartado", "decisão humana prevalece; violações seguem nas crenças")
        elif i is not None:
            self.concluir(i, "BLOQUEADO", "veto mantido: publicação bloqueada")

    # ---- consulta de outros especialistas (PROT-QRY) ------------------------------
    def consultar(self, assunto, content, conversation_id):
        if assunto != "irregularidades":
            raise KeyError(assunto)
        c, conta = content.get("competencia") or self.gw.ambiente.principal, content["conta"]
        prov = self.perceber(conversation_id, c)
        contestados = []
        for lid in self.estado["conhecidos"].get(c, []):
            b = self.crencas.get(f"lanc[{lid}]@{c}")
            regras = [r for r in b["violacoes"] if r in EFEITO_ORCAMENTARIO]
            if b["conta"] == conta and regras:
                contestados.append({"lancamento": lid, "regras": regras, "valor": b["valor"]})
        valor = sum(x["valor"] for x in contestados)
        self.decide(conversation_id, "valor contestado = lançamentos da conta com duplicidade ou competência errada",
                    {"conta": conta, "competencia": c}, valor)
        return {"conta": conta, "valor_contestado": valor, "lancamentos": contestados, "proveniencia": prov}

    # ---- percepção e revisão de crenças ------------------------------------------
    def perceber(self, cid, c) -> dict:
        lancamentos = self.gw.call(self.id, "erp.lancamentos", cid, competencia=c)
        alcadas = self.gw.call(self.id, "normas.alcadas", cid, competencia=c)["dados"]
        regras = self.gw.call(self.id, "normas.regras", cid, competencia=c)["dados"]
        self.crencas.revisar("versao_normas", regras["versao"], "mcp://normas/regras", cid)
        self.estado["severidade"] = regras["severidade"]
        vistos, atuais = set(), []
        for lanc in lancamentos["dados"]:
            violacoes = []
            if lanc["valor"] > alcadas["limites"][alcadas["cargos"][lanc["aprovador"]]]:
                violacoes.append(("alcada", f"valor acima da alçada de {lanc['aprovador']}"))
            if lanc["criador"] == lanc["aprovador"]:
                violacoes.append(("sod", f"{lanc['criador']} criou e aprovou"))
            chave = (lanc["fornecedor"], lanc["documento"], lanc["valor"])
            if chave in vistos:
                violacoes.append(("duplicidade", "fornecedor, documento e valor já lançados"))
            vistos.add(chave)
            if lanc["competencia"] != c:
                violacoes.append(("competencia", f"competência {lanc['competencia']} fora de {c}"))
            self.crencas.revisar(f"lanc[{lanc['id']}]@{c}",
                                 {"conta": lanc.get("conta"), "valor": lanc["valor"],
                                  "violacoes": [r for r, _ in violacoes],
                                  "evidencias": {r: e for r, e in violacoes}},
                                 "mcp://erp/lancamentos", cid)
            self.estado["crencas"][lanc["id"]] = [r for r, _ in violacoes] or ["conforme"]
            atuais.append(lanc["id"])
        for lid in set(self.estado["conhecidos"].get(c, [])) - set(atuais):  # estornados desde a última percepção
            self.crencas.revisar(f"lanc[{lid}]@{c}", {"conta": None, "valor": 0, "violacoes": [], "evidencias": {},
                                                      "estornado": True}, "mcp://erp/lancamentos", cid)
            self.estado["crencas"][lid] = ["estornado"]
        self.estado["conhecidos"][c] = atuais
        if cid in self.estado["pareceres"]:
            self.estado["pareceres"][cid].update(proveniencia=lancamentos["proveniencia"], lancamentos=len(atuais))
        return lancamentos["proveniencia"]

    def achados(self, d) -> list[dict]:
        c = self.estado["pareceres"][d.params["cmp"]]["competencia"]
        sev = self.estado["severidade"]
        achados = []
        for lid in self.estado["conhecidos"].get(c, []):
            b = self.crencas.get(f"lanc[{lid}]@{c}")
            for regra in b["violacoes"]:
                achados.append({"regra": regra, "lancamento": lid, "severidade": sev[regra],
                                "evidencia": b["evidencias"][regra]})
        return sorted(achados, key=lambda a: (a["regra"], a["lancamento"]))

    def criticos(self, d) -> list[dict]:
        return [a for a in self.achados(d) if a["severidade"] == "critica"]

    def correcoes_sugeridas(self, criticos) -> list[dict]:
        por_lanc: dict[str, set] = {}
        for a in criticos:
            por_lanc.setdefault(a["lancamento"], set()).add(a["regra"])
        sugeridas = []
        for lid, regras in sorted(por_lanc.items()):
            acao = "estornar" if "duplicidade" in regras else CORRECAO_POR_REGRA[sorted(regras)[0]]
            sugeridas.append({"lancamento": lid, "regras": sorted(regras), "acao": acao})
        return sugeridas

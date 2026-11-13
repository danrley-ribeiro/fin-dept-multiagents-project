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

DSM3 — memória e Approval Gate. Antes de vetar, o AG-CIN consulta o SVC-MEM: um achado
crítico com o mesmo padrão (regra + aprovador, criador ou fornecedor) que já recebeu
waiver numa competência anterior é marcado como reincidente, com o id da memória e a
aprovação de origem; a política (POL-06) não admite novo waiver para ele. Waiver,
correção e bloqueio decididos por humano no PROT-APR são gravados na memória com a
proveniência da aprovação. O veto informa os envolvidos nos lançamentos críticos, para a
política impedir que um deles aprove a liberação (POL-03).
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.core.message import Message
from fin_mas.env.dataset import EFEITO_ORCAMENTARIO
from fin_mas.services.memoria import MemoriaRecusada

MAX_CICLOS_CORRECAO = 1
CORRECAO_POR_REGRA = {"alcada": "reaprovar", "sod": "reaprovar", "duplicidade": "estornar",
                      "competencia": "reclassificar"}
REINCIDENCIA_POR = {"alcada": "aprovador", "sod": "criador", "duplicidade": "fornecedor", "competencia": "criador"}
# O que o AG-CIN pergunta à base normativa para cada regra (CP8). A consulta descreve o fato, não cita a norma.
CONSULTA_POR_REGRA = {
    "alcada": "aprovação de transação por pessoa com limite de alçada compatível com o valor",
    "sod": "segregação de funções: quem registra a transação não a aprova",
    "duplicidade": "pagamento em duplicidade: mesmo fornecedor, documento e valor lançados duas vezes",
    "competencia": "regime de competência: despesa registrada no período a que se refere",
}


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
    maximo = a.conhecimento["max_ciclos_correcao"]
    if ciclos >= maximo:
        return False, f"ciclo de correção já usado ({ciclos}/{maximo})"
    nao_corrigiveis = [x["lancamento"] for x in criticos if a.acao_corretiva(x, a.competencia_de(d)) is None]
    if nao_corrigiveis:
        return False, f"sem correção possível para {', '.join(nao_corrigiveis)} (ninguém mais com alçada)"
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
        if a.base_normativa:  # CP8 (DSM4): cada achado cita o trecho que o fundamenta, ou declara que não há
            conteudo["fundamentos"] = a.fundamentar(achados, a.competencia_de(d), cmp_id)
        if evento == "veto":
            sugeridas = a.correcoes_sugeridas(criticos, a.competencia_de(d)) if i.plano.id == "P-VETAR-COM-CORRECAO" else []
            conteudo["correcoes_sugeridas"] = sugeridas
            conteudo["opcoes"] = (["corrigir"] if sugeridas else []) + ["waiver", "bloquear"]
            a.marcar_reincidencias(achados, a.competencia_de(d), cmp_id)
            conteudo["envolvidos"] = a.envolvidos(criticos, a.competencia_de(d))
            if a.informar_exposicao:  # DSM4 (POL-10): só com o SVC-IAM ligado; sem ele o veto é o de antes
                conteudo["exposicao"] = a.exposicao(criticos, a.competencia_de(d))
            a.estado["pareceres"][cmp_id]["ultimo_veto"] = achados
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
    PAPEL = "ROLE-CIN"
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"conformidade": 10, "prazo": 5}

    def __init__(self, bus, gateway):
        super().__init__("AG-CIN", bus, gateway)
        self.conhecimento = {"regras": ["alcada", "sod", "duplicidade", "competencia"], "porte": None,
                             "correcao_por_regra": dict(CORRECAO_POR_REGRA),
                             "efeito_orcamentario": sorted(EFEITO_ORCAMENTARIO),
                             "max_ciclos_correcao": MAX_CICLOS_CORRECAO}
        self.estado = {"crencas": {}, "intencao": None, "pareceres": {}, "conhecidos": {}}
        self.informar_exposicao = False  # DSM4: build_system liga quando há SVC-IAM (alçada por pessoa, POL-10)
        self.base_normativa = False  # DSM4 (CP8): ligada fora do nível `basico`; consulta `normas.buscar`

    # ---- conhecimento normativo com proveniência (CP8) --------------------------
    def fundamentar(self, achados, competencia, cid) -> list[dict]:
        """Busca na base normativa o trecho que sustenta cada regra violada e o anexa aos achados.

        Uma busca por regra. Com evidência, o achado leva documento, trecho e versão; sem evidência,
        leva `sem evidência` e nada é preenchido no lugar (o achado continua valendo pela regra
        interna do porte, que é de onde veio a severidade).
        """
        fundamentos = []
        for regra in sorted({a["regra"] for a in achados}):
            r = self.ferramenta("normas.buscar", cid, competencia=competencia, consulta=CONSULTA_POR_REGRA[regra], k=1)
            trechos = r["dados"]["trechos"]
            if trechos:
                t = trechos[0]
                f = {"regra": regra, "situacao": "fundamentado", "documento": t["documento"], "trecho": t["trecho"],
                     "versao": t["versao"], "texto": t["texto"], "pontuacao": t["pontuacao"]}
                citacao = f"fundamento: {t['documento']}, trecho {t['trecho']} ({t['versao']})"
            else:
                f = {"regra": regra, "situacao": "sem evidência", "corpus": r["dados"]["versao"],
                     "consulta": CONSULTA_POR_REGRA[regra]}
                citacao = f"sem evidência na base normativa ({r['dados']['versao']}): achado sustentado só pela regra interna"
            self.crencas.revisar(f"fundamento[{regra}]", {k: v for k, v in f.items() if k != "texto"},
                                 r["proveniencia"]["fonte"], cid)
            fundamentos.append(f)
            for a in achados:
                if a["regra"] == regra:
                    a["fundamento"] = {k: v for k, v in f.items() if k not in ("regra", "texto", "pontuacao")}
                    a["evidencia"] += f"; {citacao}"
        return fundamentos

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
        self.crencas.revisar(f"aprovacao[{cmp_id}]", msg.content["aprovacao"], "PROT-APR (validada pelo SVC-POL)",
                             cmp_id)
        competencia = self.estado["pareceres"][cmp_id]["competencia"]
        for c in msg.content["correcoes"]:
            antes = self.crencas.get(f"lanc[{c['lancamento']}]@{competencia}") or {}  # crença anterior à correção
            self._lembrar("correcao", f"{c['acao']}|lanc={c['lancamento']}",
                          # sem texto livre com nomes; conta e regras deixam o AG-ORC, o AG-RES e o AG-REL
                          # reconhecerem a reincidência numa competência seguinte (DSM4). Não vão para o trace.
                          {"lancamento": c["lancamento"], "acao": c["acao"], "conta": antes.get("conta"),
                           "regras": sorted(antes.get("violacoes") or [])},
                          competencia, msg.content["aprovacao"], cmp_id)
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
        parecer = self.estado["pareceres"][cmp_id]
        aprovacao = msg.content.get("aprovacao")
        if msg.performative == "waiver_humano":
            self.crencas.revisar(f"waiver[{cmp_id}]", {"justificativa": msg.content.get("justificativa"),
                                                       "aprovacao": aprovacao},
                                 "decisão humana (PROT-APR validada pelo SVC-POL)", cmp_id)
            for a in parecer.get("ultimo_veto", []):
                chave = self.chave_reincidencia(a, parecer["competencia"])
                if a["severidade"] == "critica" and chave:
                    self._lembrar("waiver", chave, {"regra": a["regra"], "lancamento": a["lancamento"]},
                                  parecer["competencia"], aprovacao, cmp_id)
            if i is not None:
                self._encerrar_intencao(i, "abandonada", "waiver humano: autoridade superior assume o risco")
                self._encerrar_desejo(i.desejo, "descartado", "decisão humana prevalece; violações seguem nas crenças")
        elif i is not None:
            if msg.content.get("decisao") == "bloquear":  # só a rejeição humana vira memória (NORM-08)
                for a in parecer.get("ultimo_veto", []):
                    if a["severidade"] == "critica":
                        self._lembrar("bloqueio", f"{a['regra']}|lanc={a['lancamento']}",
                                      {"regra": a["regra"], "lancamento": a["lancamento"]},
                                      parecer["competencia"], aprovacao, cmp_id)
            self.concluir(i, "BLOQUEADO", f"veto mantido: publicação bloqueada ({msg.content.get('decisao')})")

    # ---- memória (SVC-MEM) ----------------------------------------------------------
    def chave_reincidencia(self, achado, competencia) -> str | None:
        """Padrão que identifica reincidência: regra + pessoa (pseudônimo) ou fornecedor."""
        b = self.crencas.get(f"lanc[{achado['lancamento']}]@{competencia}") or {}
        campo = REINCIDENCIA_POR.get(achado["regra"])
        valor = b.get(campo)
        if not valor or self.memoria is None:
            return None
        return f"{achado['regra']}|{campo}={self.memoria.pseudonimo(valor) if campo != 'fornecedor' else valor}"

    def marcar_reincidencias(self, achados, competencia, cid) -> None:
        if self.memoria is None:
            return
        if not self.memoria.integra:  # falha fechada: sem o histórico confiável, nenhum waiver é reaberto
            for a in achados:
                if a["severidade"] == "critica":
                    a["reincidencia"] = {"memoria": "SVC-MEM comprometida", "competencia": None, "aprovacao": None}
                    a["evidencia"] += "; histórico de decisões indisponível (memória comprometida): waiver suspenso"
            self.crencas.revisar("memoria_integra", False, f"SVC-MEM: {self.memoria.motivo_comprometida}", cid)
            return
        for a in achados:
            chave = self.chave_reincidencia(a, competencia) if a["severidade"] == "critica" else None
            anteriores = self.memoria.consultar("waiver", chave, competencia_atual=competencia, cid=cid) if chave else []
            if not anteriores:
                continue
            m = anteriores[-1]
            a["reincidencia"] = {"memoria": m["id"], "competencia": m["competencia"],
                                 "aprovacao": m["proveniencia"]["aprovacao"]}
            a["evidencia"] += (f"; reincidente: waiver anterior {m['id']} em {m['competencia']} "
                               f"({m['proveniencia']['aprovacao']})")
            self.crencas.revisar(f"reincidencia[{a['lancamento']}]@{competencia}", a["reincidencia"],
                                 f"SVC-MEM {m['id']}", cid)

    def exposicao(self, criticos, competencia) -> int:
        """Valor sob decisão (centavos): soma dos lançamentos com achado crítico, cada um uma vez."""
        lancamentos = {a["lancamento"] for a in criticos}
        return sum(int((self.crencas.get(f"lanc[{lid}]@{competencia}") or {}).get("valor") or 0)
                   for lid in sorted(lancamentos))

    def envolvidos(self, criticos, competencia) -> list[str]:
        pessoas = set()
        for a in criticos:
            b = self.crencas.get(f"lanc[{a['lancamento']}]@{competencia}") or {}
            pessoas |= {p for p in (b.get("criador"), b.get("aprovador")) if p}
        return sorted(pessoas)

    def _lembrar(self, tipo, chave, valor, competencia, aprovacao, cid) -> None:
        if self.memoria is None or not aprovacao:
            return
        try:
            self.memoria.gravar(tipo, chave, valor, competencia=competencia, aprovacao=aprovacao,
                                fonte=f"PROT-APR {aprovacao}", cid=cid)
        except MemoriaRecusada:
            pass  # a recusa já foi auditada pelo SVC-MEM; a decisão segue sem virar memória

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
        perfil = self.ferramenta("normas.perfil", cid, competencia=c)["dados"]
        lancamentos = self.ferramenta("erp.lancamentos", cid, competencia=c)
        alcadas = self.ferramenta("normas.alcadas", cid, competencia=c)["dados"]
        regras = self.ferramenta("normas.regras", cid, competencia=c)["dados"]
        self.crencas.revisar("versao_normas", regras["versao"], "mcp://normas/regras", cid)
        self.crencas.revisar("porte", perfil["porte"], "mcp://normas/perfil", cid)
        self.conhecimento.update(porte=perfil["porte"], max_ciclos_correcao=perfil["max_ciclos_correcao"],
                                 norma_contabil=perfil["norma_contabil"])
        self.DESEJOS_PERMANENTES = dict(perfil["pesos_cin"])  # micro pesa mais o prazo; grande, a conformidade
        self.estado["severidade"] = regras["severidade"]
        self.estado["alcadas"] = alcadas
        compensatorio = regras.get("controle_compensatorio", {})
        vistos, atuais = set(), []
        for lanc in lancamentos["dados"]:
            violacoes = []
            teto = alcadas["limites"][alcadas["cargos"][lanc["aprovador"]]]
            if teto is not None and lanc["valor"] > teto:
                violacoes.append(("alcada", f"valor acima da alçada de {lanc['aprovador']}"))
            if lanc["criador"] == lanc["aprovador"]:
                extra = f"; {compensatorio['sod']}" if "sod" in compensatorio else ""
                violacoes.append(("sod", f"{lanc['criador']} criou e aprovou{extra}"))
            chave = (lanc["fornecedor"], lanc["documento"], lanc["valor"])
            if chave in vistos:
                violacoes.append(("duplicidade", "fornecedor, documento e valor já lançados"))
            vistos.add(chave)
            if lanc["competencia"] != c:
                violacoes.append(("competencia", f"competência {lanc['competencia']} fora de {c}"))
            self.crencas.revisar(f"lanc[{lanc['id']}]@{c}",
                                 {"conta": lanc.get("conta"), "valor": lanc["valor"], "criador": lanc["criador"],
                                  "aprovador": lanc["aprovador"], "fornecedor": lanc.get("fornecedor"),
                                  "violacoes": [r for r, _ in violacoes],
                                  "evidencias": {r: e for r, e in violacoes}},
                                 "mcp://erp/lancamentos", cid)
            self.estado["crencas"][lanc["id"]] = [r for r, _ in violacoes] or ["conforme"]
            atuais.append(lanc["id"])
        # estornados desde a última percepção; em ordem fixa, para o trace não depender do hash das strings
        for lid in sorted(set(self.estado["conhecidos"].get(c, [])) - set(atuais)):
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

    def competencia_de(self, d) -> str:
        return self.estado["pareceres"][d.params["cmp"]]["competencia"]

    def acao_corretiva(self, achado, competencia) -> str | None:
        """Correção possível para o achado, ou None (ex.: reaprovar sem ninguém mais com alçada)."""
        b = self.crencas.get(f"lanc[{achado['lancamento']}]@{competencia}")
        regras = set(b["violacoes"]) if b else {achado["regra"]}
        if "duplicidade" in regras:
            return "estornar"
        acao = CORRECAO_POR_REGRA.get(achado["regra"])
        if acao == "reaprovar" and b is not None:
            alc = self.estado["alcadas"]
            # com SoD não crítica (micro, controle compensatório), o próprio sócio pode reaprovar
            pode_criador = self.estado["severidade"].get("sod") != "critica"
            alternativas = [u for u, cargo in alc["cargos"].items()
                            if (u != b["criador"] or pode_criador) and cargo in alc["aprovadores"]
                            and (alc["limites"][cargo] is None or alc["limites"][cargo] >= b["valor"])]
            return "reaprovar" if alternativas else None
        return acao

    def correcoes_sugeridas(self, criticos, competencia) -> list[dict]:
        por_lanc: dict[str, list] = {}
        for a in criticos:
            por_lanc.setdefault(a["lancamento"], []).append(a)
        sugeridas = []
        for lid, achados in sorted(por_lanc.items()):
            acoes = {self.acao_corretiva(a, competencia) for a in achados}
            acao = "estornar" if "estornar" in acoes else sorted(x for x in acoes if x)[0]
            sugeridas.append({"lancamento": lid, "regras": sorted(a["regra"] for a in achados), "acao": acao})
        return sugeridas

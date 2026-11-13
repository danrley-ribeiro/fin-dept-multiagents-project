"""AG-RES — variante cognitiva (BDI) do Agente de Resultados (DSM4, ADR-010).

A classe reativa `AgenteResultados` (agents/res.py) continua sendo a do nível `basico`: consulta
Custos e Orçamento, e se qualquer um não responde devolve `failure` ao Orquestrador. Esta
variante é escolhida nos níveis `local` e `llm`. As fórmulas da DRE e dos KPIs são as mesmas.

Crenças (com fonte): receita do ERP, situação de cada insumo (aguardando, recebido, sem
resposta, recusado, indisponível), linhas da DRE e KPIs (cálculo sobre a resposta do AG-CUS),
médias do histórico de resultado (`mcp://erp/historico_resultado`), variação do EBITDA% contra
o histórico e, quando verificada, a explicação da variação.

Desejos gerados das crenças (1 = mais prioritário):
  1 obter_insumo(tarefa, insumo)     custos e orçamento ainda não chegaram
  2 explicar_variacao(tarefa, h)     há hipótese validada sobre a causa de uma variação relevante
  3 consolidar(tarefa)               insumos resolvidos e nada mais a verificar

Planos (utilidade = pesos de completude, tempestividade e explicabilidade do porte):

  obter_insumo
    P-CONSULTAR-ESPECIALISTA    completude + tempestividade   query-ref ao dono do insumo
    P-CONSULTAR-DE-NOVO         completude + tempestividade   a consulta expirou, há tentativa e cabe no prazo
    P-DAR-POR-INDISPONIVEL      tempestividade                desiste do insumo e registra a crença
  explicar_variacao
    P-DETALHAR-COM-CUSTOS       explicabilidade               pede ao AG-CUS os custos fixos por centro
    P-CONFERIR-NO-HISTORICO     tempestividade                confere a linha da DRE contra o histórico, sem mensagem
    P-ARQUIVAR-HIPOTESE         (nenhum)                      sem evidência: nada muda
  consolidar
    P-CONSOLIDAR-COMPLETO       completude + tempestividade   os dois insumos chegaram
    P-CONSOLIDAR-COM-RESSALVA   tempestividade                só falta o orçamento (não crítico para a DRE)
    P-FALHAR-EXPLICITAMENTE     completude                    falta insumo, ou a receita não confere

Quando um especialista não responde, o plano de consulta falha e o agente replaneja: consulta de
novo se couber no prazo; senão dá o insumo por indisponível. A partir daí a escolha depende da
criticidade e do porte: sem custos não há DRE (só resta falhar); sem orçamento, quem pesa
tempestividade publica a DRE com ressalva e quem pesa completude (grande empresa, auditada)
prefere falhar a entregar indicador incompleto.

A variação relevante do EBITDA% gera hipóteses pelas regras locais (`REGRAS_RES`), validadas como
as do AG-ORC (NORM-11). A hipótese não explica nada sozinha: quem grava a crença `explicacao` é o
cálculo sobre a resposta do AG-CUS e o histórico. As frases dos insights são montadas por
template deste agente, só com números das crenças.

Reconsideração: se a delegação do Orquestrador já foi encerrada (prazo esgotado), os desejos da
tarefa deixam de fazer sentido e as intenções são abandonadas (compromisso aberto).
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.core.inferencia import EsquemaHipoteses
from fin_mas.core.message import Message
from fin_mas.env.dataset import brl
from fin_mas.mcp.gateway import ToolIndisponivel

PRAZO_CONSULTA = 10  # ticks lógicos até a expiração de uma query-ref
FOLGA_RESPOSTA = 3  # ticks entre a última resposta e a entrega ao Orquestrador
MAX_CONSULTAS = 2  # consultas por insumo (a original e uma repetição)
INSUMOS = {"custos": ("AG-CUS", "custos_por_UN"), "orcamento": ("AG-ORC", "desvios")}
CRITICO = {"custos": True, "orcamento": False}  # sem custos não há DRE; sem orçamento falta só um KPI
INDICADOR = "ebitda_pct"
TIPOS_HIPOTESE = {
    "causa_custo_fixo": "a variação do indicador vem de alta dos custos fixos",
    "causa_custo_variavel": "a variação do indicador vem de alta dos custos variáveis",
    "causa_receita": "a variação do indicador vem de queda da receita",
}
LINHA_DO_TIPO = {"causa_custo_fixo": "custos_fixos", "causa_custo_variavel": "custos_variaveis",
                 "causa_receita": "receita"}
ROTULO_LINHA = {"custos_fixos": "custos fixos", "custos_variaveis": "custos variáveis", "receita": "receita"}
LIMIARES_PADRAO = {"confianca_minima_consulta": 0.5, "variacao_indicador_pp": 3, "variacao_linha_percentual": 10,
                   "participacao_minima_percentual": 50}


def _k(nome, ref, item=None):
    return f"{nome}[{item}]@{ref}" if item else f"{nome}@{ref}"


def _pct(valor) -> str:
    return f"{valor:.2f}".replace(".", ",") + "%"


def _cabe_no_prazo(a, t) -> bool:
    return t["prazo"] is None or a.bus.now + PRAZO_CONSULTA + FOLGA_RESPOSTA <= t["prazo"]


# ---- obter_insumo ------------------------------------------------------------------
def _ctx_consultar(a, d):
    destino = INSUMOS[d.params["insumo"]][0]
    ok = destino in a.bus.agents
    return ok, f"{destino} é o dono de {d.params['insumo']}" if ok else f"{destino} fora do diretório de agentes"


def _corpo_consultar(a, i):
    t, chave = a.tarefa(i.desejo.params["t"]), i.desejo.params["insumo"]
    destino, assunto = INSUMOS[chave]
    t["tentativas"][chave] += 1
    qid = a.bus.new_conversation_id("QRY")
    t["consultas"][qid] = chave
    a.estado["consulta_para_tarefa"][qid] = t["cid"]
    a.bus.audit.record(a.bus.now, "link", conversation_id=t["cid"], filha=qid, subtarefa=f"consulta {chave}", agente=a.id)
    a.send(destino, "query-ref", "PROT-QRY", qid, {"assunto": assunto, "competencia": t["c"]},
           reply_by=a.bus.now + PRAZO_CONSULTA)
    a.crencas.revisar(_k("insumo", t["cid"], chave), {"estado": "aguardando", "tentativas": t["tentativas"][chave]},
                      "plano " + i.plano.id, t["cid"])
    a.suspender(i, qid, f"aguarda {destino} sobre {chave}")


def _continuar_consultar(a, i, msg):
    t, chave = a.tarefa(i.desejo.params["t"]), i.desejo.params["insumo"]
    t["insumos"][chave] = msg.content
    t["fonte"][chave] = f"{msg.sender} ({msg.conversation_id})"
    t["proveniencia"].append(msg.content["proveniencia"])
    a.crencas.revisar(_k("insumo", t["cid"], chave), {"estado": "recebido", "tentativas": t["tentativas"][chave]},
                      t["fonte"][chave], t["cid"])
    if chave == "custos":
        a.apurar_indicadores(t)
    a.concluir(i, "recebido", f"{chave} recebido de {msg.sender}")


def _ctx_consultar_de_novo(a, d):
    t, chave = a.tarefa(d.params["t"]), d.params["insumo"]
    estado = (a.crencas.get(_k("insumo", t["cid"], chave)) or {}).get("estado")
    if estado == "recusado":
        return False, "o especialista recusou ou falhou: repetir a pergunta não muda a resposta"
    if estado != "sem_resposta":
        return False, "nenhuma consulta expirou sem resposta"
    if t["tentativas"][chave] >= MAX_CONSULTAS:
        return False, f"teto de {MAX_CONSULTAS} consultas por insumo atingido"
    if not _cabe_no_prazo(a, t):
        return False, f"não cabe no prazo do Orquestrador (t={t['prazo']})"
    return True, "a consulta expirou e outra cabe no prazo"


def _corpo_indisponivel(a, i):
    t, chave = a.tarefa(i.desejo.params["t"]), i.desejo.params["insumo"]
    anterior = a.crencas.get(_k("insumo", t["cid"], chave)) or {}
    motivo = anterior.get("motivo") or f"{t['tentativas'][chave]} consulta(s) sem resposta"
    a.crencas.revisar(_k("insumo", t["cid"], chave),
                      {"estado": "indisponivel", "tentativas": t["tentativas"][chave], "motivo": motivo},
                      "plano " + i.plano.id, t["cid"])
    a.concluir(i, "indisponivel", f"{chave} dado por indisponível: {motivo}")


# ---- explicar_variacao: só a evidência grava a explicação (NORM-11) ---------------------
def _hip(a, d):
    return a.hipoteses[d.params["h"]]


def _ctx_detalhar(a, d):
    h, t = _hip(a, d), a.tarefa(d.params["t"])
    if h.tipo != "causa_custo_fixo":
        return False, "só se aplica a hipótese de custo fixo (o detalhe por centro é do AG-CUS)"
    if "AG-CUS" not in a.bus.agents:
        return False, "AG-CUS fora do diretório de agentes"
    minimo = a.limiares["confianca_minima_consulta"]
    if h.confianca is not None and h.confianca < minimo:
        return False, f"confiança {h.confianca:.2f} da hipótese abaixo de {minimo}: não justifica mensagem nova"
    if not _cabe_no_prazo(a, t):
        return False, f"não cabe no prazo do Orquestrador (t={t['prazo']})"
    return True, "o AG-CUS pode dizer em que centro de custo está o aumento, dentro do prazo"


def _corpo_detalhar(a, i):
    h, t = _hip(a, i.desejo), a.tarefa(i.desejo.params["t"])
    qid = a.bus.new_conversation_id("QRY")
    a.estado["consulta_para_tarefa"][qid] = t["cid"]
    a.bus.audit.record(a.bus.now, "link", conversation_id=t["cid"], filha=qid,
                       subtarefa=f"verificar hipótese {h.id} ({INDICADOR})", agente=a.id)
    a.send("AG-CUS", "query-ref", "PROT-QRY", qid, {"assunto": "custos_fixos_por_centro", "competencia": t["c"]},
           reply_by=a.bus.now + PRAZO_CONSULTA)
    a.marcar_hipotese(h, "em_verificacao", f"consulta {qid} ao AG-CUS")
    a.suspender(i, qid, f"aguarda AG-CUS sobre a hipótese {h.id}")


def _continuar_detalhar(a, i, msg):
    h, t = _hip(a, i.desejo), a.tarefa(i.desejo.params["t"])
    c = t["c"]
    hist = a.crencas.get(_k("historico_resultado", c))
    aumentos = {x["centro"]: x["valor"] - hist["centros"].get(x["centro"], 0) for x in msg.content["centros"]}
    centro = max(sorted(aumentos), key=lambda nome: aumentos[nome])
    fonte = f"cálculo sobre AG-CUS ({msg.conversation_id}) e {a.crencas.fonte(_k('historico_resultado', c))}"
    a.concluir_explicacao(i, h, t, "custos_fixos", fonte, centro=centro, aumento_centro=aumentos[centro])


def _ctx_conferir(a, d):
    t = a.tarefa(d.params["t"])
    tem = _k("historico_resultado", t["c"]) in a.crencas
    return tem, "há histórico das linhas da DRE" if tem else "sem histórico de resultado"


def _corpo_conferir(a, i):
    h, t = _hip(a, i.desejo), a.tarefa(i.desejo.params["t"])
    c = t["c"]
    fonte = f"cálculo sobre {a.crencas.fonte(_k('dre', c))} e {a.crencas.fonte(_k('historico_resultado', c))}"
    a.concluir_explicacao(i, h, t, LINHA_DO_TIPO[h.tipo], fonte)


def _corpo_arquivar(a, i):
    h = _hip(a, i.desejo)
    a.marcar_hipotese(h, "arquivada", "sem evidência disponível dentro do prazo")
    a.concluir(i, "arquivada", f"hipótese {h.id} arquivada: a variação segue sem explicação")


# ---- consolidar ---------------------------------------------------------------------
def _situacao(a, t) -> dict:
    return {chave: (a.crencas.get(_k("insumo", t["cid"], chave)) or {}).get("estado") for chave in INSUMOS}


def _receita_confere(t) -> bool:
    custos = t["insumos"]["custos"]
    return custos is not None and custos["totais"]["receita"] == t["receita"]


def _ctx_completo(a, d):
    t = a.tarefa(d.params["t"])
    s = _situacao(a, t)
    faltam = [chave for chave in INSUMOS if s[chave] != "recebido"]
    if faltam:
        return False, f"falta {', '.join(faltam)}"
    if not _receita_confere(t):
        return False, "receita do ERP diverge da receita usada na apuração de custos"
    return True, "custos e orçamento recebidos; receita conferida"


def _ctx_com_ressalva(a, d):
    t = a.tarefa(d.params["t"])
    s = _situacao(a, t)
    if s["custos"] != "recebido":
        return False, "custos é insumo crítico: sem ele não há DRE"
    if not _receita_confere(t):
        return False, "receita do ERP diverge da receita usada na apuração de custos"
    if s["orcamento"] == "recebido":
        return False, "não falta insumo: não há o que ressalvar"
    return True, "só falta o orçamento, que não é crítico para a DRE: sai com ressalva"


def _ctx_falhar(a, d):
    t = a.tarefa(d.params["t"])
    s = _situacao(a, t)
    faltam = [chave for chave in INSUMOS if s[chave] != "recebido"]
    if faltam:
        return True, f"falta {', '.join(faltam)}"
    if not _receita_confere(t):
        return True, "receita do ERP diverge da receita usada na apuração de custos"
    return False, "não falta insumo e a receita confere"


def _corpo_consolidar(a, i):
    a.consolidar(i)


def _corpo_falhar(a, i):
    t = a.tarefa(i.desejo.params["t"])
    s = _situacao(a, t)
    faltam = [chave for chave in INSUMOS if s[chave] != "recebido"]
    if faltam:
        chave = faltam[0]
        detalhe = (a.crencas.get(_k("insumo", t["cid"], chave)) or {}).get("motivo") or "sem resposta"
        motivo = f"insumo indisponível ({chave}): {detalhe}"
    else:
        motivo = "receita do ERP diverge da receita usada na apuração de custos"
    a.decide(t["cid"], f"falha explícita via {i.plano.id}: resultado incompleto não é entregue",
             {"insumos": s, "porte": a.conhecimento.get("porte"), "pesos_dos_desejos": dict(a.DESEJOS_PERMANENTES)},
             "failure")
    t["encerrada"] = True
    a.send(t["solicitante"], "failure", "PROT-DEL", t["cid"], {"motivo": motivo})
    a.concluir(i, "failure", f"falha explícita ao Orquestrador: {motivo}")


def _sempre(motivo):
    return lambda a, d: (True, motivo)


PLANOS = [
    Plano("P-CONSULTAR-ESPECIALISTA", "obter_insumo", "consultar o especialista dono do insumo",
          ("completude", "tempestividade"), _ctx_consultar, _corpo_consultar, _continuar_consultar, preferencia=1),
    Plano("P-CONSULTAR-DE-NOVO", "obter_insumo", "repetir a consulta que expirou, se couber no prazo",
          ("completude", "tempestividade"), _ctx_consultar_de_novo, _corpo_consultar, _continuar_consultar),
    Plano("P-DAR-POR-INDISPONIVEL", "obter_insumo", "desistir do insumo e registrar que está indisponível",
          ("tempestividade",), _sempre("sempre aplicável (fallback)"), _corpo_indisponivel),
    Plano("P-DETALHAR-COM-CUSTOS", "explicar_variacao", "pedir ao AG-CUS os custos fixos por centro e localizar o aumento",
          ("explicabilidade",), _ctx_detalhar, _corpo_detalhar, _continuar_detalhar, preferencia=1),
    Plano("P-CONFERIR-NO-HISTORICO", "explicar_variacao", "conferir a linha da DRE contra o histórico, sem mensagem",
          ("tempestividade",), _ctx_conferir, _corpo_conferir),
    Plano("P-ARQUIVAR-HIPOTESE", "explicar_variacao", "arquivar a hipótese sem evidência (nada muda)", (),
          _sempre("sempre aplicável (fallback)"), _corpo_arquivar),
    Plano("P-CONSOLIDAR-COMPLETO", "consolidar", "consolidar DRE e KPIs com todos os insumos",
          ("completude", "tempestividade"), _ctx_completo, _corpo_consolidar, preferencia=1),
    Plano("P-CONSOLIDAR-COM-RESSALVA", "consolidar", "entregar a DRE sem o KPI de orçamento, com ressalva",
          ("tempestividade",), _ctx_com_ressalva, _corpo_consolidar),
    Plano("P-FALHAR-EXPLICITAMENTE", "consolidar", "devolver falha explícita em vez de resultado incompleto",
          ("completude",), _ctx_falhar, _corpo_falhar),
]


class AgenteResultadosBDI(AgenteBDI):
    PAPEL = "ROLE-RES"
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"completude": 2, "tempestividade": 3, "explicabilidade": 4}

    def __init__(self, bus, gateway):
        super().__init__("AG-RES", bus, gateway)
        self.conhecimento = {"estrutura_dre": ["receita", "custos_variaveis", "margem_contribuicao",
                                               "custos_fixos", "ebitda"]}
        self.estado = {"tarefas": {}, "consulta_para_tarefa": {}}
        self.limiares = dict(LIMIARES_PADRAO)
        self.modelos = None  # SVC-MOD: comentário opcional dos indicadores (uso `comentario`); None = sem LLM

    # ---- percepção ---------------------------------------------------------------------
    def on_message(self, msg: Message) -> None:
        if msg.protocol == "PROT-DEL" and msg.performative == "request":
            self._nova_tarefa(msg)
        elif msg.protocol == "PROT-QRY" and msg.performative in ("inform", "refuse", "failure", "timeout"):
            self._resposta(msg)
        else:
            super().on_message(msg)

    def _nova_tarefa(self, msg: Message) -> None:
        cid = msg.conversation_id
        self.send(msg.sender, "agree", "PROT-DEL", cid)
        if msg.content.get("tarefa") != "consolidar_resultado":
            self.send(msg.sender, "failure", "PROT-DEL", cid, {"motivo": f"tarefa desconhecida: {msg.content.get('tarefa')}"})
            return
        c = msg.content.get("competencia") or self.gw.ambiente.principal
        perfil = self.ferramenta("normas.cognicao", cid, competencia=c)
        fonte_perfil = perfil["proveniencia"]["fonte"]
        self.crencas.revisar("porte", perfil["dados"]["porte"], fonte_perfil, cid)
        self.crencas.revisar("tem_erp", perfil["dados"]["tem_erp"], fonte_perfil, cid)
        self.DESEJOS_PERMANENTES = dict(perfil["dados"]["pesos_res"])  # a utilidade dos planos muda com o porte
        self.limiares.update({k: v for k, v in perfil["dados"]["limiares"].items() if k in self.limiares})
        self.conhecimento.update(porte=perfil["dados"]["porte"], versao_cognicao=perfil["dados"]["versao"])
        balancete = self.ferramenta("erp.balancete", cid, competencia=c)
        receita = sum(p["preco"] * p["qtd"] for p in balancete["dados"]["produtos"])
        self.estado["tarefas"][cid] = {
            "cid": cid, "c": c, "solicitante": msg.sender, "prazo": msg.reply_by, "receita": receita,
            "proveniencia": [balancete["proveniencia"]], "insumos": {k: None for k in INSUMOS}, "fonte": {},
            "tentativas": {k: 0 for k in INSUMOS}, "consultas": {}, "encerrada": False}
        self.crencas.revisar(_k("receita", cid), receita, f"cálculo sobre {balancete['proveniencia']['fonte']}", cid)
        self.ciclo()

    def _resposta(self, msg: Message) -> None:
        """Resposta (ou timeout) de uma consulta: a crença sobre o insumo é revisada antes de o plano continuar."""
        cid = self.estado["consulta_para_tarefa"].get(msg.conversation_id)
        t = self.estado["tarefas"].get(cid)
        chave = t["consultas"].get(msg.conversation_id) if t else None
        if chave is not None and msg.performative != "inform":
            if msg.performative == "timeout":
                crenca = {"estado": "sem_resposta", "tentativas": t["tentativas"][chave],
                          "motivo": f"{msg.content.get('contraparte')} não respondeu a {t['tentativas'][chave]} consulta(s)"}
                fonte = f"SVC-A2A (timeout de {msg.conversation_id})"
            else:
                crenca = {"estado": "recusado", "tentativas": t["tentativas"][chave],
                          "motivo": msg.content.get("motivo") or f"consulta {msg.performative}"}
                fonte = f"{msg.sender} ({msg.conversation_id})"
            self.crencas.revisar(_k("insumo", cid, chave), crenca, fonte, cid)
        self.entregar_resposta(msg)

    def apurar_indicadores(self, t) -> None:
        """DRE e KPIs a partir da resposta do AG-CUS; histórico e variação do EBITDA% como crenças com fonte."""
        cid, c = t["cid"], t["c"]
        custos = t["insumos"]["custos"]["totais"]
        fonte = f"cálculo sobre {t['fonte']['custos']}"
        receita = t["receita"]
        margem = receita - custos["custos_variaveis"]
        dre = {"receita": receita, "custos_variaveis": custos["custos_variaveis"], "margem_contribuicao": margem,
               "custos_fixos": custos["custos_fixos"], "ebitda": margem - custos["custos_fixos"]}
        t["dre"] = dre
        self.crencas.revisar(_k("dre", c), dre, fonte, cid)
        self.crencas.revisar(_k("kpi", c, INDICADOR), round(dre["ebitda"] * 100 / receita, 2), fonte, cid)
        if _k("historico_resultado", c) not in self.crencas:
            try:
                hist = self.ferramenta("erp.historico_resultado", cid, competencia=c)
            except ToolIndisponivel:
                return  # empresa sem ERP: não há com o que comparar
            meses = hist["dados"]["meses"]
            if not meses:
                return
            n = len(meses)
            media = {linha: sum(m[linha] for m in meses) // n for linha in ("receita", "custos_variaveis", "custos_fixos")}
            media["ebitda"] = media["receita"] - media["custos_variaveis"] - media["custos_fixos"]
            centros = sorted({nome for m in meses for nome in m["custos_fixos_por_centro"]})
            self.crencas.revisar(_k("historico_resultado", c),
                                 {"meses": n, "media": media, "ebitda_pct": round(media["ebitda"] * 100 / media["receita"], 2),
                                  "centros": {nome: sum(m["custos_fixos_por_centro"].get(nome, 0) for m in meses) // n
                                              for nome in centros}},
                                 hist["proveniencia"]["fonte"], cid)
        hist = self.crencas.get(_k("historico_resultado", c))
        atual = self.crencas.get(_k("kpi", c, INDICADOR))
        delta = round(atual - hist["ebitda_pct"], 2)
        self.crencas.revisar(_k("variacao", c, INDICADOR),
                             {"atual": atual, "media": hist["ebitda_pct"], "delta_pp": delta,
                              "relevante": abs(delta) >= self.limiares["variacao_indicador_pp"]},
                             f"{fonte} e {self.crencas.fonte(_k('historico_resultado', c))}", cid)

    # ---- hipóteses sobre a variação (mesmo molde do AG-ORC, ADR-008) --------------------------
    def gatilhos_inferencia(self):
        gatilhos = []
        for t in self.estado["tarefas"].values():
            c, chave = t["c"], f"variacao@{t['c']}"
            variacao = self.crencas.get(_k("variacao", c, INDICADOR))
            if t["encerrada"] or chave in self._gatilhos_usados or not variacao or not variacao["relevante"]:
                continue
            if variacao["delta_pp"] > 0:
                continue  # melhora do indicador: as regras atuais só tratam de piora
            self._perceber_correcoes(t)
            hist, dre = self.crencas.get(_k("historico_resultado", c)), self.crencas.get(_k("dre", c))
            chaves = {"indicador": _k("variacao", c, INDICADOR), "historico": _k("historico_resultado", c)}
            linhas, valores = {}, {}
            for linha in ("receita", "custos_variaveis", "custos_fixos"):
                media, atual = hist["media"][linha], dre[linha]
                adverso = (media - atual) if linha == "receita" else (atual - media)
                linhas[linha] = {"atual": atual, "media": media, "adverso_percentual": round(adverso * 100 / media, 1)}
                chaves[linha] = _k("dre", c) + f"#{linha}"
                valores[chaves[linha]] = f"{brl(atual)} ({ROTULO_LINHA[linha]} do mês)"
            valores[chaves["indicador"]] = f"{_pct(variacao['atual'])} (EBITDA sobre a receita)"
            valores[chaves["historico"]] = f"dos {hist['meses']} meses anteriores"
            t["valores_hipoteses"] = valores
            item = {"conta": INDICADOR, "chaves": chaves, "linhas": linhas, "delta_pp": variacao["delta_pp"],
                    "limiar_linha": self.limiares["variacao_linha_percentual"]}
            gatilhos.append({"chave": chave, "cid": t["cid"], "tarefa": "causa da variação de um indicador de resultado",
                             "competencia": c, "contexto": {"competencia": c, "contas": [item]},
                             "esquema": EsquemaHipoteses(TIPOS_HIPOTESE, (INDICADOR,), tuple(sorted(chaves.values())),
                                                         valores=valores)})
        return gatilhos

    def _perceber_correcoes(self, t) -> None:
        """Memória aprovada (SVC-MEM): correções de meses do histórico mexem na base de comparação."""
        if self.memoria is None or not self.memoria.integra:
            return
        anteriores = self.memoria.consultar("correcao", competencia_atual=t["c"], cid=t["cid"])
        if anteriores:
            self.crencas.revisar(_k("correcoes_anteriores", t["c"]),
                                 [{"memoria": m["id"], "competencia": m["competencia"]} for m in anteriores],
                                 "SVC-MEM " + ", ".join(m["id"] for m in anteriores), t["cid"])

    def concluir_explicacao(self, i, h, t, linha, fonte, centro=None, aumento_centro=None) -> None:
        """Confere se a linha explica a queda do EBITDA; só o cálculo grava a crença `explicacao`."""
        c = t["c"]
        hist, dre = self.crencas.get(_k("historico_resultado", c)), self.crencas.get(_k("dre", c))
        queda = hist["media"]["ebitda"] - dre["ebitda"]
        adverso = (hist["media"][linha] - dre[linha]) if linha == "receita" else (dre[linha] - hist["media"][linha])
        participacao = adverso * 100 // queda if queda > 0 else 0
        confirmada = queda > 0 and participacao >= self.limiares["participacao_minima_percentual"]
        if confirmada:
            explicacao = {"indicador": INDICADOR, "linha": linha, "variacao_da_linha": adverso,
                          "queda_do_ebitda": queda, "participacao_percentual": participacao}
            if centro is not None:
                explicacao.update(centro=centro, aumento_do_centro=aumento_centro)
            self.crencas.revisar(_k("explicacao", c, INDICADOR), explicacao, fonte, i.desejo.cid)
        motivo = (f"{ROTULO_LINHA[linha]} respondem por {participacao}% da queda do EBITDA contra a média do histórico"
                  + (f"; maior aumento em {centro}" if centro and confirmada else ""))
        self.marcar_hipotese(h, "confirmada" if confirmada else "refutada", motivo, fonte)
        self.decide(i.desejo.cid, "hipótese só explica a variação depois de evidência determinística (NORM-11)",
                    {"hipotese": h.id, "tipo": h.tipo, "indicador": h.alvo, "origens": list(h.origens), "evidencia": fonte},
                    h.estado)
        self.concluir(i, h.estado, f"hipótese {h.id} {h.estado}: {motivo}")

    def insights(self, c) -> list[str]:
        """Frases por template deste agente; todo número vem das crenças (variação, explicação, histórico)."""
        variacao = self.crencas.get(_k("variacao", c, INDICADOR))
        hist = self.crencas.get(_k("historico_resultado", c))
        linhas = []
        for h in self.hipoteses.values():
            if h.competencia != c:
                continue
            desfecho = {"confirmada": f"confirmada por {h.verificacao}", "refutada": f"refutada por {h.verificacao}",
                        "arquivada": "arquivada sem evidência", "em_verificacao": "em verificação",
                        "proposta": "sem verificação"}[h.estado]
            frase = (f"EBITDA de {_pct(variacao['atual'])} da receita contra média de {_pct(variacao['media'])} "
                     f"nos {hist['meses']} meses anteriores")
            e = self.crencas.get(_k("explicacao", c, INDICADOR))
            if h.estado == "confirmada" and e and e["linha"] == LINHA_DO_TIPO[h.tipo]:
                lado = "abaixo" if e["linha"] == "receita" else "acima"
                frase += (f"; {ROTULO_LINHA[e['linha']]} {brl(e['variacao_da_linha'])} {lado} da média, "
                          f"{e['participacao_percentual']}% da queda do EBITDA")
                if e.get("centro"):
                    frase += f"; maior aumento em {e['centro']} ({brl(e['aumento_do_centro'])})"
            anteriores = self.crencas.get(_k("correcoes_anteriores", c))
            if anteriores:
                frase += ("; a base de comparação inclui correção aprovada em competência anterior ("
                          + ", ".join(f"{m['memoria']} em {m['competencia']}" for m in anteriores) + ")")
            linhas.append(f"{INDICADOR}: hipótese {h.id} ({h.tipo}; origem {', '.join(h.origens)}) {desfecho}. {frase}.")
        return linhas

    # ---- opções e reconsideração ---------------------------------------------------------
    def tarefa(self, cid) -> dict:
        return self.estado["tarefas"][cid]

    def opcoes(self):
        ops = []
        for cid, t in self.estado["tarefas"].items():
            conversa = self.bus.conversations.get(cid)
            if t["encerrada"] or (conversa is not None and conversa.is_final):
                continue  # entregue, ou a delegação já foi encerrada pelo prazo: nenhum desejo novo
            for chave, (destino, _) in INSUMOS.items():
                ops.append(("obter_insumo", {"t": cid, "insumo": chave}, 1, f"consolidação pede {chave} de {destino}", cid))
            situacao = _situacao(self, t)
            pendente = any(situacao[chave] not in ("recebido", "indisponivel") for chave in INSUMOS)
            for h in self.hipoteses.values():
                if (h.competencia, h.estado) == (t["c"], "proposta"):
                    ops.append(("explicar_variacao", {"t": cid, "h": h.id}, 2,
                                f"hipótese {h.id} ({h.tipo}) sobre a variação de {h.alvo} ainda sem evidência", cid))
                    pendente = True
            if pendente or any(i.desejo.params.get("t") == cid and i.desejo.tipo != "consolidar" for i in self.pendentes()):
                continue
            ops.append(("consolidar", {"t": cid}, 3, "insumos resolvidos e nada mais a verificar", cid))
        return ops

    def desejo_ativo(self, d):
        conv = self.bus.conversations.get(d.params.get("t"))
        if conv is not None and conv.is_final and not self.tarefa(d.params["t"])["encerrada"]:
            return False, f"a delegação {d.params['t']} foi encerrada ({conv.state}): o resultado não seria usado"
        return True, ""

    # ---- saída -------------------------------------------------------------------------
    def consolidar(self, i) -> None:
        t = self.tarefa(i.desejo.params["t"])
        cid, c, dre = t["cid"], t["c"], t["dre"]
        receita, margem = dre["receita"], dre["margem_contribuicao"]
        orcamento = t["insumos"]["orcamento"]
        kpis = {"margem_contribuicao_pct": round(margem * 100 / receita, 2),
                "ebitda_pct": round(dre["ebitda"] * 100 / receita, 2),
                "desvio_orcamentario": (orcamento["totais"]["realizado_acumulado"] - orcamento["totais"]["orcado_acumulado"])
                if orcamento else None}
        ressalvas = []  # a ressalva de critério de rateio é do AG-CUS e segue pela subtarefa de custos
        if orcamento is None:
            crenca = self.crencas.get(_k("insumo", cid, "orcamento")) or {}
            ressalvas.append(f"KPI de desvio orçamentário indisponível: {crenca.get('motivo', 'AG-ORC sem resposta')}; "
                             f"DRE consolidada sem o orçamento")
        self.decide(cid, f"DRE = receita - variáveis - fixos via {i.plano.id}; receita do ERP conferida com a de Custos",
                    {"consultas": sorted(t["consultas"]), "insumos": _situacao(self, t),
                     "porte": self.conhecimento.get("porte"), "pesos_dos_desejos": dict(self.DESEJOS_PERMANENTES)}, dre)
        self.estado["ultima_dre"] = dre
        conteudo = {"dre": dre, "kpis": kpis, "resultado_un": t["insumos"]["custos"]["resultado_un"],
                    "proveniencia": t["proveniencia"]}
        if ressalvas:
            conteudo["ressalvas"] = ressalvas
        hipoteses = [h.resumo() for h in self.hipoteses.values() if h.competencia == c]
        if hipoteses:
            conteudo["hipoteses"] = hipoteses
            conteudo["insights"] = self.insights(c)
        explicacao = self.crencas.get(_k("explicacao", c, INDICADOR))
        if explicacao:
            conteudo["explicacoes"] = [{**explicacao, "fonte": self.crencas.fonte(_k("explicacao", c, INDICADOR))}]
        if self.modelos:  # texto do LLM validado contra as linhas abaixo (NORM-05); só com a flag ligada
            base = (f"Receita: {brl(dre['receita'])}\nMargem de contribuição: {brl(margem)} "
                    f"({kpis['margem_contribuicao_pct']}%)\nEBITDA: {brl(dre['ebitda'])} ({kpis['ebitda_pct']}%)")
            if kpis["desvio_orcamentario"] is not None:
                base += f"\nDesvio orçamentário acumulado: {brl(kpis['desvio_orcamentario'])}"
            texto = self.modelos.gerar(self.id, cid, "comentar os indicadores do período", base, uso="comentario")
            if texto:
                conteudo["comentario"] = {"texto": texto, "modelo": self.modelos.config(self.id)["modelo"]}
        t["encerrada"] = True
        self.send(t["solicitante"], "inform", "PROT-DEL", cid, conteudo)
        self.concluir(i, "inform", "resultado consolidado e entregue ao Orquestrador")

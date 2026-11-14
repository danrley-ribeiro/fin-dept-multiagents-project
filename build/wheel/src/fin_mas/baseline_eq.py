"""Workflow centralizado FUNCIONALMENTE EQUIVALENTE ao SMA (DSM4, braço `wf_equivalente`).

A linha de base da DSM3 (`baseline.py`) não tem veto, correção nem aprovação; comparada com o
SMA, mede diferença de funções. Este módulo é a linha de base que isola o paradigma: **um
controlador único, sequencial**, que aplica as mesmas regras de negócio, na mesma ordem:

    custos -> orçamento -> DRE -> conformidade -> [aprovação -> correção -> reavaliação]* -> relatório

- orçamento: reconciliação planilha x ERP pela fonte primária do porte e atribuição do desvio a
  lançamentos irregulares (duplicidade ou competência errada inflando a conta);
- conformidade: alçada, SoD, duplicidade e competência, com a severidade do porte; achado crítico
  **veta** a publicação, com correção sugerida enquanto houver ciclo de correção;
- aprovação: o veto vira um ticket do **mesmo SVC-POL** (`services/politica.py`) e é decidido
  pelo **mesmo aprovador simulado** (`env/scenarios.Aprovador`) numa conversa PROT-APR; a
  correção só toca o ERP depois de `autorizar_efeito`, e o pacote é reavaliado.

O que **não** existe aqui, de propósito: agentes, mensagens entre componentes, consulta entre
especialistas, reenvio, negociação de prazo, replanejamento, reserva de período (há um só
controlador, que faz uma coisa de cada vez) e hipóteses. As únicas mensagens são as duas do
Approval Gate, porque o aprovador é uma pessoa fora do controlador.

O controlador concentra tudo o que no SMA está separado: lê todas as fontes, calcula, julga a
conformidade e executa a correção. É essa a diferença de arquitetura que o experimento compara.

A equivalência é conferida por teste (`tests/e2e/test_equivalencia_workflow.py`): sem falhas, o
mesmo status final, a mesma DRE, as mesmas contas sinalizadas e atribuídas e as mesmas correções
que o SMA com cognição básica. Latência lógica: `TICKS_POR_ETAPA` por etapa (a premissa do
`baseline.py`) mais a espera pelo aprovador no relógio do barramento.
"""
from dataclasses import dataclass, field

from fin_mas.agents.cin import CORRECAO_POR_REGRA
from fin_mas.agents.orc import TOLERANCIA_FONTE
from fin_mas.agents.orq import ressalvas as linhas_de_ressalva
from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus
from fin_mas.env.dataset import EFEITO_ORCAMENTARIO, RATEIO, Ambiente, brl, ratear
from fin_mas.env.portes import PORTE_PADRAO
from fin_mas.env.scenarios import Aprovador
from fin_mas.parametros import PADRAO
from fin_mas.services.politica import PRAZO_APROVACAO, PoliticaAprovacao

CONTROLADOR = "WF-CTRL"
SOLICITACAO = "WF-001"
VERIFICACAO = "WF-CMP-001"
TICKS_POR_ETAPA = 3
BLOQUEIO = "publicação bloqueada por veto (NORM-04)"


@dataclass
class ResultadoEq:
    intencao: str
    status: str  # publicado | publicado_com_ressalva | bloqueado
    sinalizadas: list
    atribuidas: list
    dre: dict | None
    kpis: dict | None
    totais: dict
    achados: list  # primeiro parecer de conformidade (regra, lançamento, severidade)
    ressalvas: list
    notas: list
    correcoes: list  # correções executadas no ERP, em ordem
    aprovacoes: list  # [(ticket, desfecho)], um por ciclo de veto
    ticks: int
    etapas: list
    audit: object = None
    decisoes: list = field(default_factory=list)
    dataset: object = None  # a empresa depois das correções (o gabarito está em `dataset.gold`)

    @property
    def publicado(self) -> bool:
        return self.status.startswith("publicado")


class Controlador(Agent):
    """O único componente que decide. Está no barramento só para falar com o aprovador (PROT-APR)."""

    PAPEL = "ROLE-ORQ"

    def __init__(self, bus, ds, politica, parametros):
        super().__init__(CONTROLADOR, bus)
        self.ds, self.politica, self.p = ds, politica, parametros
        self.caixa, self.etapas = [], []

    def on_message(self, msg) -> None:
        self.caixa.append(msg)

    def _etapa(self, nome: str) -> None:
        self.etapas.append(nome)
        self.bus.now += TICKS_POR_ETAPA

    # ---- fluxo ------------------------------------------------------------------------
    def executar(self, intencao: str) -> ResultadoEq:
        fechar = intencao == "fechar_mes"
        custos = self._custos() if fechar else None
        orc = self._orcamento()
        ressalvas, notas = list(orc["ressalvas"]), []
        dre = kpis = None
        achados, correcoes, aprovacoes, bloqueado = [], [], [], False
        if fechar:
            dre, kpis = self._resultados(custos, orc)
            achados, bloqueado = self._conformidade(ressalvas, notas, correcoes, aprovacoes)
        if bloqueado:
            status = "bloqueado"
            self.decide(SOLICITACAO, "veto sem liberação: nada é publicado", {"aprovacoes": aprovacoes}, status)
        else:
            self._etapa("relatorio")
            status = "publicado_com_ressalva" if ressalvas else "publicado"
            self.decide(SOLICITACAO, "todas as etapas concluídas", {"ressalvas": len(ressalvas)}, status)
        return ResultadoEq(intencao, status, orc["sinalizadas"], orc["atribuidas"], dre, kpis, orc["totais"],
                           [{k: a[k] for k in ("regra", "lancamento", "severidade")} for a in achados],
                           ressalvas, notas, correcoes, aprovacoes, self.bus.now, list(self.etapas), self.bus.audit,
                           [r for r in self.bus.audit.records if r["kind"] == "decision"])

    # ---- custos e resultado -----------------------------------------------------------------
    def _custos(self) -> dict:
        self._etapa("custos")
        ds = self.ds
        margem_un = {un: 0 for un in RATEIO}
        receita = cv = 0
        for p in ds.produtos:
            r, c = p["preco"] * p["qtd"], p["custo_variavel_unit"] * p["qtd"]
            receita, cv = receita + r, cv + c
            margem_un[p["un"]] += r - c
        fixo = sum(c["valor"] for c in ds.custos_fixos)
        fixo_un = ratear(fixo, RATEIO)
        self.decide(SOLICITACAO, "margem = receita - custo variável; rateio fixo por UN", {"produtos": len(ds.produtos)},
                    {"receita": receita, "custos_variaveis": cv, "custos_fixos": fixo})
        return {"receita": receita, "custos_variaveis": cv, "custos_fixos": fixo,
                "resultado_un": {un: {"margem": m, "custo_fixo_rateado": fixo_un[un], "resultado": m - fixo_un[un]}
                                 for un, m in margem_un.items()}}

    def _resultados(self, custos, orc) -> tuple[dict, dict]:
        self._etapa("resultados")
        receita = custos["receita"]
        margem = receita - custos["custos_variaveis"]
        dre = {"receita": receita, "custos_variaveis": custos["custos_variaveis"], "margem_contribuicao": margem,
               "custos_fixos": custos["custos_fixos"], "ebitda": margem - custos["custos_fixos"]}
        kpis = {"margem_contribuicao_pct": round(margem * 100 / receita, 2),
                "ebitda_pct": round(dre["ebitda"] * 100 / receita, 2),
                "desvio_orcamentario": orc["totais"]["realizado_acumulado"] - orc["totais"]["orcado_acumulado"]}
        self.decide(SOLICITACAO, "DRE = receita - variáveis - fixos", {}, dre)
        return dre, kpis

    # ---- orçamento: reconciliação de fontes e atribuição do desvio ------------------------------
    def _orcamento(self) -> dict:
        self._etapa("orcamento")
        ds, perfil = self.ds, self.ds.perfil
        limiar, primaria, meses = perfil["limiar_desvio"], perfil["fonte_primaria"], ds.gold["meses_decorridos"]

        def acima(desvio, orcado):
            return abs(desvio) * 100 >= orcado * limiar["percentual"] and abs(desvio) >= limiar["absoluto"]

        violacoes = self._violacoes()
        ressalvas, sinalizadas, atribuidas, linhas = [], [], [], []
        for linha in ds.orcamento:
            conta, orcado, planilha = linha["conta"], linha["orcado_acumulado"], linha["realizado_acumulado"]
            realizado = planilha
            if perfil["tem_erp"]:  # sem ERP a planilha é a única fonte: não há o que reconciliar
                erp = ds.realizado_erp[conta]
                if abs(planilha - erp) > TOLERANCIA_FONTE:
                    realizado = erp if primaria == "ERP" else planilha
                    ressalvas.append(f"divergência em {conta}: planilha {brl(planilha)} x ERP {brl(erp)}; "
                                     f"adotado {primaria}")
                    self.decide(SOLICITACAO, f"divergência de fontes: adota {primaria} (fonte primária)",
                                {"conta": conta, "planilha": planilha, "erp": erp}, realizado)
            bruto, contestado = realizado - orcado, 0
            if acima(bruto, orcado):
                contestado = sum(lanc["valor"] for lanc in ds.lancamentos if lanc.get("conta") == conta
                                 and any(r in EFEITO_ORCAMENTARIO for r, _ in violacoes[lanc["id"]]))
                if acima(bruto - contestado, orcado):
                    sinalizadas.append(conta)
                    self.decide(SOLICITACAO, "desvio acima do limiar após atribuição", {"conta": conta}, "sinalizado")
                else:
                    atribuidas.append(conta)
                    ressalvas.append(f"desvio de {conta} atribuído a lançamentos contestados pela conformidade "
                                     f"({brl(contestado)}), não ao orçamento")
                    self.decide(SOLICITACAO, "desvio explicado por lançamento irregular", {"conta": conta},
                                "atribuido_a_controle")
            linhas.append({"conta": conta, "orcado": orcado, "realizado": realizado, "contestado": contestado})
        ajustar = sum(x["contestado"] for x in linhas) > 0  # run-rate sem os valores contestados
        forecast = sum(((x["realizado"] - (x["contestado"] if ajustar else 0)) * 3 + meses // 2) // meses for x in linhas)
        return {"sinalizadas": sorted(sinalizadas), "atribuidas": sorted(atribuidas), "ressalvas": ressalvas,
                "totais": {"orcado_acumulado": sum(x["orcado"] for x in linhas),
                           "realizado_acumulado": sum(x["realizado"] for x in linhas),
                           "forecast_trimestre": forecast}}

    # ---- conformidade, veto, aprovação e correção ---------------------------------------------
    def _violacoes(self) -> dict:
        """lançamento -> [(regra, evidência)] pelo estado atual do ERP (as quatro regras do AG-CIN)."""
        ds, p = self.ds, self.ds.perfil
        compensatorio = p["controle_compensatorio"]
        vistos, por_lancamento = set(), {}
        for lanc in ds.lancamentos:
            v = []
            teto = p["limites_alcada"][p["pessoas"][lanc["aprovador"]]]
            if teto is not None and lanc["valor"] > teto:
                v.append(("alcada", f"valor acima da alçada de {lanc['aprovador']}"))
            if lanc["criador"] == lanc["aprovador"]:
                extra = f"; {compensatorio['sod']}" if "sod" in compensatorio else ""
                v.append(("sod", f"{lanc['criador']} criou e aprovou{extra}"))
            chave = (lanc["fornecedor"], lanc["documento"], lanc["valor"])
            if chave in vistos:
                v.append(("duplicidade", "fornecedor, documento e valor já lançados"))
            vistos.add(chave)
            if lanc["competencia"] != ds.competencia:
                v.append(("competencia", f"competência {lanc['competencia']} fora de {ds.competencia}"))
            por_lancamento[lanc["id"]] = v
        return por_lancamento

    def _achados(self) -> list:
        sev = self.ds.perfil["severidade"]
        achados = [{"regra": r, "lancamento": lid, "severidade": sev[r], "evidencia": e}
                   for lid, v in self._violacoes().items() for r, e in v]
        return sorted(achados, key=lambda a: (a["regra"], a["lancamento"]))

    def _acao_corretiva(self, achado, violacoes) -> str | None:
        p = self.ds.perfil
        lanc = next(x for x in self.ds.lancamentos if x["id"] == achado["lancamento"])
        if any(r == "duplicidade" for r, _ in violacoes[lanc["id"]]):
            return "estornar"
        acao = CORRECAO_POR_REGRA.get(achado["regra"])
        if acao != "reaprovar":
            return acao
        pode_criador = p["severidade"]["sod"] != "critica"  # controle compensatório (micro)
        alternativas = [u for u, cargo in p["pessoas"].items()
                        if (u != lanc["criador"] or pode_criador) and cargo in p["aprovadores"]
                        and (p["limites_alcada"][cargo] is None or p["limites_alcada"][cargo] >= lanc["valor"])]
        return "reaprovar" if alternativas else None

    def _sugerir(self, criticos) -> list:
        """Uma correção por lançamento crítico; lista vazia se algum não tiver correção possível."""
        violacoes, por_lancamento = self._violacoes(), {}
        for a in criticos:
            por_lancamento.setdefault(a["lancamento"], []).append(a)
        sugeridas = []
        for lid, grupo in sorted(por_lancamento.items()):
            acoes = {self._acao_corretiva(a, violacoes) for a in grupo}
            if None in acoes:
                return []
            sugeridas.append({"lancamento": lid, "regras": sorted(a["regra"] for a in grupo),
                              "acao": "estornar" if "estornar" in acoes else sorted(acoes)[0]})
        return sugeridas

    def _conformidade(self, ressalvas, notas, correcoes, aprovacoes) -> tuple[list, bool]:
        """Devolve (achados do primeiro parecer, bloqueado). Repete enquanto houver correção aprovada."""
        max_ciclos = self.ds.perfil["max_ciclos_correcao"]
        primeiro, ciclos = None, 0
        while True:
            self._etapa("conformidade" if primeiro is None else "reavaliacao")
            achados = self._achados()
            primeiro = achados if primeiro is None else primeiro
            criticos = [a for a in achados if a["severidade"] == "critica"]
            if not criticos:
                if achados:
                    ressalvas += linhas_de_ressalva(achados)
                self.decide(SOLICITACAO, "parecer de conformidade", {"achados": len(achados)},
                            "conforme com ressalvas" if achados else "conforme")
                return primeiro, False
            sugeridas = self._sugerir(criticos) if ciclos < max_ciclos else []
            opcoes = (["corrigir"] if sugeridas and len(correcoes_ciclos(aprovacoes)) < self.p.max_correcoes else []) \
                + ["waiver", "bloquear"]
            self.decide(SOLICITACAO, "NORM-04: não conformidade crítica bloqueia a publicação",
                        {"achados": [a["lancamento"] for a in criticos]}, "VETADO")
            envolvidos = sorted({p for a in criticos for p in self._pessoas(a["lancamento"])})
            ticket = self.politica.emitir(solicitacao=SOLICITACAO, competencia=self.ds.competencia, cmp=VERIFICACAO,
                                          ciclo=len(aprovacoes) + 1, aprovador="APR",
                                          veto={"achados": achados, "correcoes_sugeridas": sugeridas, "opcoes": opcoes,
                                                "envolvidos": envolvidos})
            desfecho = self._aprovacao(ticket)
            aprovacoes.append((ticket["id"], desfecho))
            if desfecho == "corrigir":
                ciclos += 1
                quem = ticket["aprovado_por"]["titulo"]
                for registro in self._corrigir(ticket):
                    correcoes.append(registro)
                    notas.append(f"correção aprovada por {quem} ({ticket['id']}): {registro['detalhe']}")
                continue
            if desfecho == "waiver":
                quem, justificativa = ticket["aprovado_por"]["titulo"], ticket["justificativa"]
                ressalvas += [f"waiver de {a['regra']} em {a['lancamento']} por {quem} ({ticket['id']}): {justificativa}"
                              for a in criticos]
                ressalvas += linhas_de_ressalva([a for a in achados if a["severidade"] != "critica"])
                self.avancar(ticket["id"], "execute")
                return primeiro, False
            return primeiro, True  # rejeitada, expirada, negada ou em estado inesperado: fica bloqueado

    def _pessoas(self, lancamento) -> list:
        lanc = next(x for x in self.ds.lancamentos if x["id"] == lancamento)
        return [lanc["criador"], lanc["aprovador"]]

    def _aprovacao(self, ticket) -> str:
        """Abre o PROT-APR, espera a decisão (ou o prazo) e devolve corrigir | waiver | bloquear | expirada | negada."""
        tid = ticket["id"]
        self.caixa.clear()
        self.send("APR", "propose-action", "PROT-APR", tid, self.politica.conteudo_proposta(tid),
                  reply_by=ticket["expira_em"])
        if self.politica.classificar(tid) == "deny":
            return "negada"
        # o controlador para aqui até o aprovador decidir ou o prazo do ticket esgotar (aviso do barramento)
        while not any(m.conversation_id == tid for m in self.caixa) and self.bus.step():
            pass
        resposta = next((m for m in self.caixa if m.conversation_id == tid), None)
        if resposta is not None and resposta.performative == "approve" and ticket["estado"] == "aprovado":
            return ticket["decisao"]
        if resposta is not None and resposta.performative == "reject" and ticket["estado"] == "rejeitado":
            return "bloquear"
        self.politica.expirar(tid)
        return "expirada"

    def _corrigir(self, ticket) -> list:
        """Efeito externo: cada correção só é aplicada depois de a política confirmar a aprovação."""
        tid, executadas = ticket["id"], []
        for pedido in ticket["correcoes_aprovadas"]:
            try:
                self.politica.autorizar_efeito(tid, self.id, pedido["lancamento"], pedido["acao"])
                registro = self.ds.corrigir(pedido["lancamento"], pedido["acao"])
            except Exception as erro:  # correção inviável: a reavaliação mantém o veto
                self.politica.registrar_falha(tid, pedido, str(erro) or type(erro).__name__)
                continue
            self.politica.registrar_execucao(tid, registro)
            self.bus.audit.record(self.bus.now, "mcp_call", conversation_id=tid, agente=self.id, tool="erp.corrigir",
                                  consulta={"aprovacao": tid, **pedido}, fonte="erp")
            executadas.append(registro)
        self.avancar(tid, "execute")
        return executadas


class AprovadorDoWorkflow(Aprovador):
    """O mesmo aprovador simulado do SMA; só o destinatário da decisão muda (o controlador, não o AG-ORQ)."""

    def send(self, receiver, *args, **kwargs) -> None:
        super().send(CONTROLADOR if receiver == "AG-ORQ" else receiver, *args, **kwargs)


def correcoes_ciclos(aprovacoes) -> list:
    return [t for t, desfecho in aprovacoes if desfecho == "corrigir"]


def executar(seed=42, plantar=(), intencao="fechar_mes", porte=PORTE_PADRAO, decisao_aprovador="nenhuma",
             parametros=None, caos=None) -> ResultadoEq:
    """Roda o workflow sobre a mesma empresa sintética que `build_system(seed, plantar, porte=...)` monta."""
    p = parametros or PADRAO
    bus = Bus(caos=caos)
    ambiente = Ambiente(seed, plantar=plantar, porte=porte)
    ds = ambiente.dataset()
    p.aplicar_limiares(ds)
    compensatorio = "; ".join(f"{k}: {v}" for k, v in sorted(ds.perfil["controle_compensatorio"].items())) or None
    politica = PoliticaAprovacao(bus, prazo=p.prazo_aprovacao or PRAZO_APROVACAO, controle_compensatorio=compensatorio)
    controlador = Controlador(bus, ds, politica, p)
    aprovador = AprovadorDoWorkflow(bus, decisao_aprovador, ambiente)
    if caos is not None:  # do modelo de falhas, só o que alcança o workflow: o comportamento do aprovador
        caos.instalar_aprovador(aprovador, bus, politica.prazo)
    resultado = controlador.executar(intencao)
    resultado.dataset = ds
    return resultado

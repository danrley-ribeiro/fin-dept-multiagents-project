"""AG-CUS — variante cognitiva (BDI) do Agente de Custos (DSM4, ADR-010).

A classe reativa `AgenteCustos` (agents/cus.py) continua sendo a do nível `basico`: aplica o
rateio fixo que conhece e não olha o direcionador do período. Esta variante é escolhida nos
níveis `local` e `llm`. O cálculo de margem é o mesmo; o que muda é que o critério de rateio
dos custos fixos passa a ser uma decisão tomada sob crenças.

Crenças (com fonte): porte e existência de ERP (`mcp://normas/cognicao`), receita por unidade
de negócio (cálculo sobre o balancete), situação do direcionador de rateio do período
(`mcp://erp/direcionadores`: ok, ausente ou inconsistente) e critério adotado (plano).

Desejos:
  1 definir_rateio(c)   ainda não há critério de rateio para a competência
  2 apurar_custos(c)    critério definido: calcula margens e resultado por unidade

Planos de `definir_rateio` (utilidade = pesos de precisão e simplicidade do porte):

  P-RATEIO-PADRAO                precisão + simplicidade   direcionador do período válido (ou ainda não lido)
  P-RATEIO-ULTIMO-VALIDO         precisão + simplicidade   direcionador ausente: vale a última tabela aprovada
  P-RATEIO-PROPORCIONAL-RECEITA  precisão                  todas as unidades têm receita no período
  P-RATEIO-IGUALITARIO           simplicidade              sempre (não depende de dado nenhum)

O agente começa pelo padrão. Ao ler o direcionador, a crença é revisada; se ele está ausente
ou inconsistente, o plano **falha** e o agente replaneja entre as alternativas aplicáveis.
Tabela inconsistente não libera a "última válida" (alguém a alterou: a anterior deixou de
valer), e aí o porte decide: quem pesa precisão rateia pela receita, quem pesa simplicidade
(microempresa) divide em partes iguais. O critério usado e o motivo vão para a proveniência,
para a decisão registrada e, quando não é o padrão, para uma ressalva do fechamento.

O desenho inicial previa precisão x tempestividade. Aqui todos os critérios se calculam no
mesmo instante, então tempo não distingue nada; o custo real do critério mais fiel é depender
de dado e de manutenção, e por isso o segundo desejo se chama simplicidade.

Sem LLM (NORM-07): nenhum texto deste agente vem de modelo.
"""
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.env.dataset import RATEIO, VERSAO_RATEIO
from fin_mas.mcp.gateway import ToolIndisponivel

ROTULO = {"padrao": "padrão (direcionador do período)", "ultimo_valido": "última tabela aprovada",
          "proporcional_receita": "proporcional à receita", "igualitario": "igualitário"}


def _k(nome, c, item=None):
    return f"{nome}[{item}]@{c}" if item else f"{nome}@{c}"


def ratear_por_pesos(valor: int, pesos: dict) -> dict:
    """Divide em inteiros na proporção dos pesos; o resto vai à última unidade para a soma fechar."""
    unidades, soma = list(pesos), sum(pesos.values())
    partes = {u: valor * pesos[u] // soma for u in unidades}
    partes[unidades[-1]] += valor - sum(partes.values())
    return partes


def _percentuais(pesos: dict) -> str:
    soma = sum(pesos.values())
    return ", ".join(f"{u} {pesos[u] * 100 / soma:.1f}%".replace(".", ",") for u in pesos)


# ---- contextos e corpos -----------------------------------------------------------
def _ctx_padrao(a, d):
    dirc = a.crencas.get(_k("direcionador", d.params["c"]))
    if dirc is None:
        return True, "direcionador do período ainda não lido: o critério padrão é a primeira opção"
    if dirc["estado"] == "ok":
        return True, "direcionador do período publicado e consistente"
    return False, f"direcionador do período {dirc['estado']}: {dirc['motivo']}"


def _corpo_padrao(a, i):
    c = i.desejo.params["c"]
    dirc = a.perceber_direcionador(c, i.desejo.cid)
    if dirc["estado"] != "ok":
        a.falhar(i, f"direcionador do período {dirc['estado']}: {dirc['motivo']}")
        return
    a.definir_criterio(i, "padrao", dirc["valores"], "direcionador do período publicado e consistente")


def _ctx_ultimo_valido(a, d):
    dirc = a.crencas.get(_k("direcionador", d.params["c"]))
    if dirc is None:
        return False, "direcionador do período ainda não lido"
    if dirc["estado"] == "ok":
        return False, "direcionador do período disponível: não há o que substituir"
    if dirc["estado"] == "inconsistente":
        return False, "a tabela do período foi alterada: a versão anterior deixou de valer"
    return True, f"tabela do período não publicada: vale a última aprovada ({a.conhecimento['versao_rateio']})"


def _corpo_ultimo_valido(a, i):
    a.definir_criterio(i, "ultimo_valido", a.conhecimento["rateio"],
                       f"direcionador do período ausente; usada a última tabela aprovada "
                       f"({a.conhecimento['versao_rateio']})")


def _ctx_proporcional(a, d):
    receitas = a.tarefa(d.params["t"])["receita_un"]
    sem = sorted(un for un, v in receitas.items() if v <= 0)
    if sem:
        return False, f"{', '.join(sem)} sem receita no período: a proporção não se define"
    return True, "todas as unidades têm receita no período"


def _corpo_proporcional(a, i):
    c = i.desejo.params["c"]
    dirc = a.crencas.get(_k("direcionador", c)) or {"estado": "não lido", "motivo": ""}
    a.definir_criterio(i, "proporcional_receita", a.tarefa(i.desejo.params["t"])["receita_un"],
                       f"direcionador do período {dirc['estado']} ({dirc['motivo']}); rateio pela receita de cada unidade")


def _corpo_igualitario(a, i):
    c = i.desejo.params["c"]
    dirc = a.crencas.get(_k("direcionador", c)) or {"estado": "não lido", "motivo": ""}
    a.definir_criterio(i, "igualitario", {un: 1 for un in a.tarefa(i.desejo.params["t"])["receita_un"]},
                       f"direcionador do período {dirc['estado']} ({dirc['motivo']}); partes iguais entre as unidades")


def _corpo_apurar(a, i):
    a.apurar(i)


PLANOS = [
    Plano("P-RATEIO-PADRAO", "definir_rateio", "ratear pelo direcionador do período", ("precisao", "simplicidade"),
          _ctx_padrao, _corpo_padrao, preferencia=2),
    Plano("P-RATEIO-ULTIMO-VALIDO", "definir_rateio", "reusar a última tabela de rateio aprovada",
          ("precisao", "simplicidade"), _ctx_ultimo_valido, _corpo_ultimo_valido, preferencia=1),
    Plano("P-RATEIO-PROPORCIONAL-RECEITA", "definir_rateio", "ratear na proporção da receita de cada unidade",
          ("precisao",), _ctx_proporcional, _corpo_proporcional, preferencia=1),
    Plano("P-RATEIO-IGUALITARIO", "definir_rateio", "dividir os custos fixos em partes iguais", ("simplicidade",),
          lambda a, d: (True, "sempre aplicável (não depende de dado)"), _corpo_igualitario),
    Plano("P-APURAR-CUSTOS", "apurar_custos", "calcular margens e resultado por unidade com o critério definido",
          ("precisao", "simplicidade"), lambda a, d: (True, "critério de rateio definido"), _corpo_apurar),
]


class AgenteCustosBDI(AgenteBDI):
    PAPEL = "ROLE-CUS"
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"precisao": 3, "simplicidade": 1}

    def __init__(self, bus, gateway):
        super().__init__("AG-CUS", bus, gateway)
        self.conhecimento = {"rateio": dict(RATEIO), "versao_rateio": VERSAO_RATEIO}
        self.estado = {"custos": {}, "pendencias": [], "tarefas": {}}

    # ---- interface de especialista (PROT-DEL e PROT-QRY), igual à da classe reativa -------------
    def executar(self, tarefa, content, conversation_id):
        if tarefa != "apurar_custos":
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        return self._apurar(conversation_id, content.get("competencia"))

    def consultar(self, assunto, content, conversation_id):
        c = content.get("competencia") or self.gw.ambiente.principal
        if assunto == "custos_por_UN":
            custos = self.estado["custos"].get(c) or self._apurar(conversation_id, c)
            return {"resultado_un": custos["resultado_un"], "totais": custos["totais"],
                    "proveniencia": custos["proveniencia"]}
        if assunto == "custos_fixos_por_centro":  # detalhe pedido pelo AG-RES para explicar uma variação
            custos = self.estado["custos"].get(c) or self._apurar(conversation_id, c)
            self.decide(conversation_id, "custos fixos por centro, como lidos do balancete", {"competencia": c},
                        custos["totais"]["custos_fixos"])
            return {"centros": [dict(x) for x in custos["custos_fixos_por_centro"]],
                    "custos_fixos": custos["totais"]["custos_fixos"], "proveniencia": custos["proveniencia"]}
        raise KeyError(assunto)

    # ---- percepção ---------------------------------------------------------------------
    def _apurar(self, cid, competencia=None) -> dict:
        c = competencia or self.gw.ambiente.principal
        perfil = self.ferramenta("normas.cognicao", cid, competencia=c)
        fonte_perfil = perfil["proveniencia"]["fonte"]
        self.crencas.revisar("porte", perfil["dados"]["porte"], fonte_perfil, cid)
        self.crencas.revisar("tem_erp", perfil["dados"]["tem_erp"], fonte_perfil, cid)
        self.DESEJOS_PERMANENTES = dict(perfil["dados"]["pesos_cus"])  # a utilidade dos critérios muda com o porte
        self.conhecimento["porte"] = perfil["dados"]["porte"]
        resposta = self.ferramenta("erp.balancete", cid, competencia=c)
        dados, fonte = resposta["dados"], resposta["proveniencia"]["fonte"]
        if not dados["produtos"]:
            self.estado["pendencias"].append("balancete sem produtos")
            raise ValueError("dado de origem ausente: balancete sem produtos")
        unidades = list(self.conhecimento["rateio"]) + sorted({p["un"] for p in dados["produtos"]}
                                                              - set(self.conhecimento["rateio"]))
        receita_un = {un: sum(p["preco"] * p["qtd"] for p in dados["produtos"] if p["un"] == un) for un in unidades}
        self.estado["tarefas"][cid] = {"c": c, "cid": cid, "dados": dados, "proveniencia": resposta["proveniencia"],
                                       "receita_un": receita_un, "custos": None}
        for un, valor in receita_un.items():
            self.crencas.revisar(_k("receita_un", c, un), valor, f"cálculo sobre {fonte}", cid)
        self.crencas.revisar(_k("custos_fixos", c), sum(x["valor"] for x in dados["custos_fixos"]), fonte, cid)
        self.ciclo()
        custos = self.estado["tarefas"][cid]["custos"]
        if custos is None:  # nenhum plano aplicável: falha explícita ao solicitante, nunca silêncio
            raise ValueError("não foi possível definir um critério de rateio para a competência")
        return custos

    def perceber_direcionador(self, c, cid) -> dict:
        """Lê o direcionador do período e revisa a crença sobre ele (ok, ausente ou inconsistente)."""
        t = next(t for t in self.estado["tarefas"].values() if t["cid"] == cid)
        try:
            r = self.ferramenta("erp.direcionadores", cid, competencia=c)
        except ToolIndisponivel as erro:
            crenca = {"estado": "ausente", "motivo": str(erro), "valores": {}, "versao": None}
            self.crencas.revisar(_k("direcionador", c), crenca, "mcp://erp/direcionadores (indisponível)", cid)
            return crenca
        valores = dict(r["dados"]["valores"])
        com_produto = [un for un, v in t["receita_un"].items() if any(p["un"] == un for p in t["dados"]["produtos"])]
        faltam = [un for un in com_produto if un not in valores]
        if not valores:
            estado, motivo = "ausente", "tabela de direcionadores do período não publicada"
        elif any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in valores.values()):
            estado, motivo = "inconsistente", "há percentual negativo ou não inteiro"
        elif sum(valores.values()) != 100:
            estado, motivo = "inconsistente", f"os percentuais somam {sum(valores.values())}, não 100"
        elif faltam:
            estado, motivo = "inconsistente", f"sem direcionador para {', '.join(faltam)}"
        else:
            estado, motivo = "ok", "publicado e consistente"
        crenca = {"estado": estado, "motivo": motivo, "valores": valores, "versao": r["dados"].get("versao")}
        self.crencas.revisar(_k("direcionador", c), crenca, r["proveniencia"]["fonte"], cid)
        return crenca

    # ---- opções ----------------------------------------------------------------------
    def tarefa(self, cid) -> dict:
        return self.estado["tarefas"][cid]

    def opcoes(self):
        ops = []
        for cid, t in self.estado["tarefas"].items():
            if t["custos"] is not None:
                continue
            p = {"c": t["c"], "t": cid}
            if "criterio" not in t:
                ops.append(("definir_rateio", p, 1, "apuração pedida e ainda sem critério de rateio", cid))
            else:
                ops.append(("apurar_custos", p, 2, f"critério de rateio definido: {t['criterio']['criterio']}", cid))
        return ops

    # ---- ações dos planos ----------------------------------------------------------------
    def definir_criterio(self, i, criterio, pesos, motivo) -> None:
        c, t = i.desejo.params["c"], self.tarefa(i.desejo.params["t"])
        t["criterio"] = {"criterio": criterio, "pesos": dict(pesos), "motivo": motivo, "plano": i.plano.id}
        self.crencas.revisar(_k("criterio_rateio", c), {"criterio": criterio, "pesos": dict(pesos), "motivo": motivo},
                             "plano " + i.plano.id, i.desejo.cid)
        self.decide(i.desejo.cid, f"critério de rateio dos custos fixos via {i.plano.id}: {motivo}",
                    {"competencia": c, "porte": self.conhecimento.get("porte"),
                     "pesos_dos_desejos": dict(self.DESEJOS_PERMANENTES)}, criterio)
        self.concluir(i, criterio, f"critério de rateio: {ROTULO[criterio]}")

    def apurar(self, i) -> None:
        c, t = i.desejo.params["c"], self.tarefa(i.desejo.params["t"])
        dados, criterio = t["dados"], t["criterio"]
        margens = {}
        for p in dados["produtos"]:
            receita, cv = p["preco"] * p["qtd"], p["custo_variavel_unit"] * p["qtd"]
            margens[p["id"]] = {"receita": receita, "custo_variavel": cv, "margem": receita - cv}
        fixo_total = sum(x["valor"] for x in dados["custos_fixos"])
        fixo_un = ratear_por_pesos(fixo_total, criterio["pesos"])
        resultado_un = {}
        for un in criterio["pesos"]:
            margem = sum(margens[p["id"]]["margem"] for p in dados["produtos"] if p["un"] == un)
            resultado_un[un] = {"margem": margem, "custo_fixo_rateado": fixo_un[un], "resultado": margem - fixo_un[un]}
        receita = sum(m["receita"] for m in margens.values())
        cv = sum(m["custo_variavel"] for m in margens.values())
        custos = {
            "margens_produto": margens, "resultado_un": resultado_un,
            "totais": {"receita": receita, "custos_variaveis": cv, "margem_contribuicao": receita - cv,
                       "custos_fixos": fixo_total},
            "proveniencia": {**t["proveniencia"], "versao_rateio": self.conhecimento["versao_rateio"],
                             "criterio_rateio": criterio["criterio"], "motivo_criterio": criterio["motivo"]},
            "custos_fixos_por_centro": [dict(x) for x in dados["custos_fixos"]],
        }
        if criterio["criterio"] != "padrao":  # o gestor precisa saber que o rateio não foi o de sempre
            custos["ressalvas"] = [f"rateio dos custos fixos pelo critério {ROTULO[criterio['criterio']]} "
                                   f"({_percentuais(criterio['pesos'])}): {criterio['motivo']}"]
        t["custos"] = custos
        self.estado["custos"][c] = custos
        self.decide(i.desejo.cid, "margem = receita - custo variável; custos fixos rateados pelo critério definido",
                    {"produtos": len(margens), "versao_rateio": self.conhecimento["versao_rateio"],
                     "criterio_rateio": criterio["criterio"]}, custos["totais"])
        self.concluir(i, custos["totais"], "custos apurados")

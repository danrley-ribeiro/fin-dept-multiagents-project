"""AG-REL — variante cognitiva (BDI) do Agente de Relatórios (DSM4, ADR-010).

A classe reativa `AgenteRelatorios` (agents/rel.py) continua sendo a do nível `basico`: um único
template, na mesma ordem, para qualquer situação e qualquer leitor. Esta variante é escolhida nos
níveis `local` e `llm`. O texto continua saindo de template determinístico e todo número continua
vindo do conteúdo recebido; o que o agente decide é **como comunicar**.

Crenças (com fonte): o que o período teve (parecer, correções aprovadas, waivers, ressalvas,
desvios sinalizados e atribuídos, insights), vindas do pedido do Orquestrador; o público do
relatório e os pesos dos desejos (`mcp://normas/cognicao`); o histórico de decisões humanas de
competências anteriores (SVC-MEM); a base normativa de cada exceção (`mcp://normas/buscar`).

Desejo: comunicar(tarefa). Planos (utilidade = pesos de clareza, completude e concisão do porte):

  P-RELATORIO-DE-EXCECAO   clareza + completude   o Approval Gate foi acionado (correção ou waiver)
  P-SUMARIO-EXECUTIVO      clareza + concisão     tudo conforme: sem exceção, ressalva nem desvio
  P-RELATORIO-COMPLETO     completude             sempre (o template da DSM3, na mesma ordem)

No relatório de exceção as exceções vêm antes dos indicadores, as ressalvas são ordenadas por
destaque (waiver, violação de controle, atribuição a controle, divergência de fonte, demais), só
entram insights de hipóteses verificadas (os demais são contados, não reproduzidos; o público
que pesa completude recebe todos) e cada exceção cita a base normativa ou declara que não há.
O sumário traz só as linhas-chave. Para o público que pesa completude (grande empresa, conselho
e auditoria) o sumário perde para o relatório completo mesmo com tudo conforme.

Texto de modelo (síntese deste agente, comentário do AG-RES, narrativa do AG-ORC) nunca se
mistura às frases do template: vai ao fim, rotulado como texto de modelo.

Este agente não tem plano que falhe por causa do ambiente: recebe tudo no pedido. Ver ADR-010
sobre onde a deliberação pesa pouco.
"""
from fin_mas.agents.rel import VERSAO_TEMPLATE, AgenteRelatorios
from fin_mas.core.bdi import AgenteBDI, Plano
from fin_mas.env.empresa import EMPRESA

VERSAO_EXCECAO, VERSAO_SUMARIO = "tpl-excecao-v1", "tpl-sumario-v1"
TITULO = {"relatorio_executivo": "Relatório executivo", "relatorio_orcamentario": "Relatório orçamentário"}
LINHAS_CHAVE = {"relatorio_executivo": ("Receita:", "EBITDA:", "Parecer de conformidade:"),
                "relatorio_orcamentario": ("Orçado acumulado:", "Realizado acumulado:", "Forecast do trimestre:",
                                           "Nenhum desvio acima do limiar.")}
# O que a nota de uma correção ou a ressalva de um waiver diz -> tema e pergunta à base normativa (CP8).
TEMAS = (
    ("reaprovado", "aprovação por alçada", "aprovação de transação por pessoa com autoridade compatível com o valor"),
    ("estornado", "lançamento em duplicidade", "pagamento em duplicidade: mesmo fornecedor, documento e valor lançados duas vezes"),
    ("reclassificado", "regime de competência", "regime de competência: despesa registrada no período a que se refere"),
    ("waiver de alcada", "aprovação por alçada", "aprovação de transação por pessoa com autoridade compatível com o valor"),
    ("waiver de sod", "segregação de funções", "segregação de funções: quem registra a transação não a aprova"),
    ("waiver de duplicidade", "lançamento em duplicidade", "pagamento em duplicidade: mesmo fornecedor, documento e valor lançados duas vezes"),
    ("waiver de competencia", "regime de competência", "regime de competência: despesa registrada no período a que se refere"),
    ("waiver de", "liberação por waiver", "não conformidade crítica veta a publicação até correção reavaliada ou waiver humano"),
)


def _k(nome, cid):
    return f"{nome}@{cid}"


def destaque(ressalva: str) -> int:
    """Ordem de leitura das ressalvas no relatório de exceção (menor = antes)."""
    texto = ressalva.lower()
    if texto.startswith("waiver de"):
        return 0
    if texto.startswith(("alcada em", "sod em", "duplicidade em", "competencia em")):
        return 1
    if "contestados pelo ag-cin" in texto or "atribuído a" in texto:
        return 2
    if texto.startswith("divergência em"):
        return 3
    return 4


def verificado(insight: str) -> bool:
    """Insight de hipótese com evidência (confirmada ou refutada), pelo texto que o especialista monta por template."""
    return " confirmada por " in insight or " refutada por " in insight


# ---- contextos ----------------------------------------------------------------------
def _ctx_excecao(a, d):
    x = a.crencas.get(_k("achados", d.params["t"]))
    n = x["correcoes"] + x["waivers"]
    if not n:
        return False, "nenhuma correção ou waiver no período: o Approval Gate não foi acionado"
    return True, f"{x['correcoes']} correção(ões) aprovada(s) e {x['waivers']} waiver(s) no período"


def _ctx_sumario(a, d):
    x = a.crencas.get(_k("achados", d.params["t"]))
    motivos = [nome for nome in ("correcoes", "waivers", "ressalvas", "notas", "sinalizadas", "atribuidas", "insights")
               if x[nome]]
    if x["parecer"] not in (None, "conforme"):
        motivos.append(f"parecer '{x['parecer']}'")
    if motivos:
        return False, "há o que detalhar: " + ", ".join(motivos)
    return True, "tudo conforme: sem exceção, ressalva, desvio ou insight"


PLANOS = [
    Plano("P-RELATORIO-DE-EXCECAO", "comunicar", "abrir pelas exceções tratadas, com base normativa e histórico",
          ("clareza", "completude"), _ctx_excecao, lambda a, i: a.redigir(i, "excecao"), preferencia=1),
    Plano("P-SUMARIO-EXECUTIVO", "comunicar", "sumário só com as linhas-chave", ("clareza", "concisao"),
          _ctx_sumario, lambda a, i: a.redigir(i, "sumario")),
    Plano("P-RELATORIO-COMPLETO", "comunicar", "template completo, na ordem de sempre", ("completude",),
          lambda a, d: (True, "sempre aplicável (template da DSM3)"), lambda a, i: a.redigir(i, "completo")),
]


class AgenteRelatoriosBDI(AgenteBDI):
    PAPEL = "ROLE-REL"
    PLANOS = PLANOS
    DESEJOS_PERMANENTES = {"clareza": 3, "completude": 2, "concisao": 2}

    def __init__(self, bus, gateway):
        super().__init__("AG-REL", bus, gateway)
        self.conhecimento = {"templates": {"relatorio_executivo": VERSAO_TEMPLATE, "relatorio_orcamentario": VERSAO_TEMPLATE,
                                           "excecao": VERSAO_EXCECAO, "sumario": VERSAO_SUMARIO}}
        self.estado = {"rascunho": None, "tarefas": {}}
        self.modelos = None  # SVC-MOD (services/modelos.py); None = só template

    # ---- interface de especialista (PROT-DEL), igual à da classe reativa ---------------------
    def executar(self, tarefa, content, conversation_id):
        if tarefa not in TITULO:
            raise ValueError(f"tarefa desconhecida: {tarefa}")
        cid = conversation_id
        perfil = self.ferramenta("normas.cognicao", cid, competencia=content.get("competencia"))
        fonte_perfil = perfil["proveniencia"]["fonte"]
        self.crencas.revisar("porte", perfil["dados"]["porte"], fonte_perfil, cid)
        self.crencas.revisar("publico", perfil["dados"]["publico"], fonte_perfil, cid)
        self.DESEJOS_PERMANENTES = dict(perfil["dados"]["pesos_rel"])  # o que o leitor do porte valoriza
        self.conhecimento["porte"] = perfil["dados"]["porte"]
        ressalvas, notas = list(content.get("ressalvas", [])), list(content.get("notas", []))
        self.crencas.revisar(_k("achados", cid), {
            "parecer": content.get("parecer"),
            "correcoes": sum(1 for n in notas if n.startswith("correção aprovada")),
            "waivers": sum(1 for r in ressalvas if r.startswith("waiver de")),
            "ressalvas": len(ressalvas), "notas": len(notas),
            "sinalizadas": len(content.get("sinalizadas", [])), "atribuidas": len(content.get("atribuidas_a_controle", [])),
            "insights": len(content.get("insights", [])),
        }, f"pedido do AG-ORQ ({cid})", cid)
        self.estado["tarefas"][cid] = {"tarefa": tarefa, "content": content, "resultado": None}
        self.ciclo()
        resultado = self.estado["tarefas"][cid]["resultado"]
        if resultado is None:
            raise ValueError("nenhuma estrutura de relatório aplicável")
        return resultado

    def opcoes(self):
        return [("comunicar", {"t": cid}, 1, f"{TITULO[t['tarefa']].lower()} pedido pelo Orquestrador", cid)
                for cid, t in self.estado["tarefas"].items() if t["resultado"] is None]

    # ---- percepções usadas pelo relatório de exceção --------------------------------------------
    def _historico(self, cid, competencia) -> list[str]:
        """Decisões humanas de competências anteriores (memória aprovada), para o leitor ver a reincidência."""
        if self.memoria is None or not self.memoria.integra or not competencia:
            return []
        anteriores = sorted(self.memoria.consultar("correcao", competencia_atual=competencia, cid=cid),
                            key=lambda m: m["id"])  # o AG-REL só lê correções (services/memoria.py, ACESSO)
        if not anteriores:
            return []
        self.crencas.revisar(_k("historico_decisoes", cid),
                             [{"memoria": m["id"], "tipo": m["tipo"], "competencia": m["competencia"],
                               "acao": (m.get("valor") or {}).get("acao")} for m in anteriores],
                             "SVC-MEM " + ", ".join(m["id"] for m in anteriores), cid)
        return [f"Histórico: {len(anteriores)} correção(ões) aprovada(s) em competências anteriores: "
                + ", ".join(f"{(m.get('valor') or {}).get('acao')} em {m['competencia']} ({m['id']})" for m in anteriores)]

    def _base_normativa(self, cid, competencia, excecoes, com_texto) -> list[str]:
        """Um trecho da base normativa por tema de exceção, ou a declaração de que não há evidência (CP8)."""
        linhas, fundamentos, vistos = [], [], set()
        for marca, tema, consulta in TEMAS:
            if tema in vistos or not any(marca in e for e in excecoes):
                continue
            vistos.add(tema)
            r = self.ferramenta("normas.buscar", cid, competencia=competencia, consulta=consulta, k=1)
            trechos = r["dados"]["trechos"]
            if trechos:
                t = trechos[0]
                fundamentos.append({"tema": tema, "situacao": "fundamentado", "documento": t["documento"],
                                    "trecho": t["trecho"], "versao": t["versao"]})
                linhas.append(f"Base normativa ({tema}): {t['titulo']}, trecho {t['trecho']} ({t['versao']})"
                              + (f": {t['texto']}" if com_texto else ""))
            else:
                fundamentos.append({"tema": tema, "situacao": "sem evidência", "corpus": r["dados"]["versao"]})
                linhas.append(f"Base normativa ({tema}): sem evidência na base normativa ({r['dados']['versao']})")
        if fundamentos:
            self.crencas.revisar(_k("base_normativa", cid), fundamentos, "mcp://normas/buscar", cid)
        return linhas

    # ---- redação por template ---------------------------------------------------------------
    def redigir(self, i, estrutura) -> None:
        cid = i.desejo.params["t"]
        t = self.estado["tarefas"][cid]
        tarefa, c = t["tarefa"], t["content"]
        publico, quer_tudo = self.crencas.get("publico"), self.DESEJOS_PERMANENTES.get("completude", 0) >= 4
        base = getattr(AgenteRelatorios, "_" + tarefa)(self, c)  # mesmas linhas do template da DSM3
        insights = list(c.get("insights", []))
        ressalvas, notas = list(c.get("ressalvas", [])), list(c.get("notas", []))
        omitidos = 0
        if estrutura == "completo":
            linhas = base + [f"Insight: {x}" for x in insights] + [f"Ressalva: {x}" for x in ressalvas] \
                + [f"Nota: {x}" for x in notas]
            versao = VERSAO_TEMPLATE
        elif estrutura == "sumario":
            linhas = [base[0], base[1].replace(TITULO[tarefa], "Sumário executivo" if tarefa == "relatorio_executivo"
                                               else "Sumário orçamentário"), f"Destinatário: {publico}"]
            linhas += [x for x in base[2:] if x.startswith(LINHAS_CHAVE[tarefa])]
            linhas.append("Sem exceções, ressalvas ou desvios acima do limiar no período.")
            versao = VERSAO_SUMARIO
        else:
            correcoes = [n for n in notas if n.startswith("correção aprovada")]
            waivers = [r for r in ressalvas if r.startswith("waiver de")]
            demais = sorted((r for r in ressalvas if r not in waivers), key=destaque)  # ordenação estável
            incluidos = insights if quer_tudo else [x for x in insights if verificado(x)]
            omitidos = len(insights) - len(incluidos)
            linhas = [base[0], base[1].replace(TITULO[tarefa], TITULO[tarefa] + " de exceção"),
                      f"Destinatário: {publico}",
                      f"Exceções tratadas no período: {len(correcoes) + len(waivers)}"]
            linhas += [f"Nota: {x}" for x in correcoes] + [f"Ressalva: {x}" for x in waivers]
            linhas += self._historico(cid, c.get("competencia"))
            linhas += self._base_normativa(cid, c.get("competencia"), correcoes + waivers, quer_tudo)
            linhas.append("Indicadores do período:")
            linhas += base[2:]
            linhas += [f"Ressalva: {x}" for x in demais] + [f"Nota: {x}" for x in notas if x not in correcoes]
            linhas += [f"Insight: {x}" for x in incluidos]
            if omitidos:
                linhas.append(f"{omitidos} hipótese(s) sem evidência não reproduzida(s) neste relatório de exceção.")
            versao = VERSAO_EXCECAO
        texto = "\n".join(linhas)
        # textos de modelo, sempre ao fim e rotulados; nunca junto das frases do template
        rodape = [f"Texto de modelo ({autor}; gerado por {c[campo]['modelo']}; só os números foram conferidos): "
                  f"{c[campo]['texto']}" for campo, autor in (("comentario", "AG-RES"), ("narrativa", "AG-ORC")) if c.get(campo)]
        sintese = self.modelos.gerar(self.id, cid, tarefa, texto) if self.modelos else None
        modo = "template"
        if sintese:
            modelo = self.modelos.config(self.id)["modelo"]
            rodape.append(f"Texto de modelo (síntese; gerada por {modelo}; só os números foram conferidos): {sintese}")
            modo = "template+llm"
        if rodape:
            texto += "\n\n" + "\n".join(rodape)
        self.estado["rascunho"] = texto
        achados = self.crencas.get(_k("achados", cid))
        self.decide(cid, f"estrutura do relatório via {i.plano.id}; texto por template determinístico"
                    + (" com síntese validada" if sintese else ""),
                    {"tarefa": tarefa, "publico": publico, "porte": self.conhecimento.get("porte"), "achados": achados,
                     "pesos_dos_desejos": dict(self.DESEJOS_PERMANENTES), "insights_omitidos": omitidos}, versao)
        t["resultado"] = {"texto": texto, "modo": modo, "versao_template": versao, "estrutura": estrutura}
        self.concluir(i, estrutura, f"relatório redigido na estrutura '{estrutura}' para {publico}")

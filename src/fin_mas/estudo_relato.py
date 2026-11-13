"""Tabelas (Markdown) e figuras (SVG escrito à mão) do experimento da DSM4, a partir do resumo de `estudo.analisar`.

Sem dependência nova: o SVG é texto, como em `experimentos.figura_svg`. As figuras são pequenos
múltiplos de barras horizontais, um eixo por painel, com legenda, valor escrito em cada barra e,
onde há intervalo de confiança, um traço fino sobre a barra. As cores identificam o braço, sempre
as mesmas e na mesma ordem (quatro primeiras posições da paleta validada da skill dataviz).
"""
from fin_mas.estudo import ABLACAO, BRACOS, CONDICOES_A, INTENCOES, ROTULOS

CORES = dict(zip(BRACOS, ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")))
FUNDO, TEXTO, TEXTO_2, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#d6d5d0"
NOMES = {
    "classificacao_correta": "Classificação correta", "sinalizacao_correta": "Sinalização correta (exploratória)",
    "conformidade_correta": "Conformidade correta",
    "dre_correta": "DRE correta", "criticas_publicadas_sem_tratamento": "Críticas publicadas sem tratamento",
    "concluida": "Conclusão", "resposta_explicita": "Resposta explícita", "execucao_correta": "Execução correta",
    "degradacao_segura": "Degradação segura", "mensagens": "Mensagens", "mensagens_coordenacao": "Mensagens de coordenação",
    "latencia_ticks": "Latência (ticks)", "decisoes": "Decisões", "intervencoes_humanas": "Intervenções humanas",
    "registros_trace": "Registros de auditoria", "mensagens_rejeitadas": "Mensagens rejeitadas",
    "ataques_tentados": "Ataques tentados", "ataques_aceitos": "Ataques aceitos",
    "ataques_sem_premissa": "Aceitos sem a premissa do ataque",
    "criticas_corrigidas": "Críticas corrigidas", "aprovacoes_expiradas": "Aprovações expiradas",
    "publicacoes_do_periodo": "Publicações do período", "efeitos_falhos": "Correções que falharam",
    "reenvios": "Reenvios", "negociacoes_de_prazo": "Negociações de prazo",
    "hipoteses_confirmadas": "Hipóteses confirmadas", "hipoteses_refutadas": "Hipóteses refutadas",
    "hipoteses_arquivadas": "Hipóteses arquivadas", "consultas_de_verificacao": "Consultas de verificação",
    "recuperacao_ticks": "Recuperação (ticks)",
}
FRACOES = {"classificacao_correta", "sinalizacao_correta", "conformidade_correta", "dre_correta", "concluida", "resposta_explicita",
           "execucao_correta", "degradacao_segura"}


# ---- números ------------------------------------------------------------------------------------
def _n(v, pct=False, casas=2) -> str:
    if v is None:
        return "—"
    if pct:
        return f"{v * 100:.1f}%".replace(".", ",")
    if isinstance(v, float):
        return f"{v:.{casas}f}".replace(".", ",")
    return str(v)


def _d(d, metrica) -> str:
    """Média por seed com IC de 95%: `87,5% [80,0%; 93,3%]`."""
    if not d or d.get("media") is None:
        return "—"
    pct = metrica in FRACOES
    return f"{_n(d['media'], pct)} [{_n(d['ic95'][0], pct)}; {_n(d['ic95'][1], pct)}]"


def _tabela(cabecalho, linhas) -> list[str]:
    return ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho),
            *("| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas), ""]


# ---- resumo.md ------------------------------------------------------------------------------------
def resumo_md(resumo, manifesto) -> str:
    t = resumo["tabelas"]
    out = ["<!-- gerado por `python -m fin_mas experimento`; não editar à mão -->",
           f"Execuções: {resumo['execucoes']} ({', '.join(f'bloco {k}: {v}' for k, v in manifesto['execucoes_por_bloco'].items())}). "
           f"Seeds: {resumo['seeds'][0]} a {resumo['seeds'][-1]}. Cada célula mostra a média por seed e o IC de 95% "
           f"por bootstrap entre colchetes.", ""]
    metricas = list(next(iter(t["rq1_qualidade_nominal"].values())))
    out += ["**RQ1 — qualidade na condição nominal (bloco A)**", ""]
    out += _tabela(["Braço", *(NOMES[m] for m in metricas)],
                   [[ROTULOS[b], *(_d(v[m], m) for m in metricas)] for b, v in t["rq1_qualidade_nominal"].items()])
    out += _tabela(["Par comparado, sem falhas", "Pares", "Pares com resultado diferente"],
                   [[k.replace("_x_", " × "), v["pares"], v["diferentes"]] for k, v in resumo["identidade"].items()])
    metricas = list(next(iter(next(iter(t["rq2_robustez"].values())).values()))) if t["rq2_robustez"] else []
    out += ["**RQ2 — robustez sob falha (bloco A)**", ""]
    out += _tabela(["Condição", "Braço", *(NOMES[m] for m in metricas)],
                   [[f"`{c}`", ROTULOS[b], *(_d(v[m], m) for m in metricas)]
                    for c, por_braco in t["rq2_robustez"].items() for b, v in por_braco.items()])
    out += ["**RQ3 — custo de coordenação (bloco A)**", ""]
    metricas = ["mensagens", "mensagens_coordenacao", "latencia_ticks", "decisoes", "intervencoes_humanas"]
    out += _tabela(["Condição", "Braço", *(NOMES[m] for m in metricas)],
                   [[f"`{c}`", ROTULOS[b], *(_d(v[m], m) for m in metricas)]
                    for c, por_braco in t["rq3_custo"].items() for b, v in por_braco.items()])
    if t["rq3_acesso"]:
        metricas = list(next(iter(t["rq3_acesso"].values()))["com_acesso"])
        out += ["**RQ3 — custo do controle de acesso (bloco D × mesmas seeds do bloco A, porte médio, SMA básico)**", ""]
        out += _tabela(["Condição", "SVC-IAM", *(NOMES[m] for m in metricas)],
                       [[f"`{c}`", "ligado" if k == "com_acesso" else "desligado", *(_d(v[m], m) for m in metricas)]
                        for c, par in t["rq3_acesso"].items() for k, v in par.items()])
    out += ["**RQ4 — recuperação das execuções do SMA atingidas por falha (bloco A)**", "",
            "Atingida: houve pelo menos uma mensagem perdida ou um prazo esgotado na solicitação.", ""]
    out += _tabela(["Braço", "Condição", "Execuções", "Atingidas", "Mesmo resultado da nominal", "Degradação segura",
                    "Sem resposta", "Recuperação: mediana (ticks)", "média", "máximo"],
                   [[ROTULOS[b], f"`{c}`", v["execucoes"], v["atingidas"], v["mesmo_resultado"], v["degradacao_segura"],
                     v["sem_resposta"], _n(v["recuperacao_ticks"]["mediana"]), _n(v["recuperacao_ticks"]["media"]),
                     _n(v["recuperacao_ticks"]["maximo"])]
                    for b, por_c in t["rq4_recuperacao"].items() for c, v in por_c.items()])
    out += ["**RQ5 — porte (bloco A, condição nominal; última coluna na condição `combinadas`)**", ""]
    metricas = list(next(iter(next(iter(t["rq5_porte"].values())).values())))
    out += _tabela(["Porte", "Braço", *(NOMES.get(m, "Execução correta em `combinadas`") for m in metricas)],
                   [[p, ROTULOS[b], *(_d(v[m], m.replace("_combinadas", "")) for m in metricas)]
                    for p, por_braco in t["rq5_porte"].items() for b, v in por_braco.items()])
    if t["rq5_parametros"]:
        out += ["**RQ5 — varredura de parâmetros (bloco B, porte médio; um parâmetro por vez)**", ""]
        metricas = ["execucao_correta", "concluida", "resposta_explicita", "classificacao_correta", "criticas_corrigidas",
                    "latencia_ticks", "aprovacoes_expiradas"]
        out += _tabela(["Variante", "Condição", "Braço", *(NOMES[m] for m in metricas)],
                       [[f"`{v}`", f"`{c}`", ROTULOS[b], *(_d(d[m], m) for m in metricas)]
                        for v, por_c in t["rq5_parametros"].items() for c, por_b in por_c.items() for b, d in por_b.items()])
    out += ["**RQ6 — ataques sob falha**", ""]
    out += _tabela(["Recorte", "Valores"], [[k, "; ".join(f"{a.replace('_', ' ')}: {b}" for a, b in v.items() if a != "quais")]
                                           for k, v in t["rq6_ataques"].items()])
    out += ["**RQ7 — cognição local × básica (bloco A)**", ""]
    metricas = list(next(iter(next(iter(t["rq7_cognicao"].values())).values())))
    out += _tabela(["Condição", "Braço", *(NOMES[m] for m in metricas)],
                   [[f"`{c}`", ROTULOS[b], *(_d(v[m], m) for m in metricas)]
                    for c, por_braco in t["rq7_cognicao"].items() for b, v in por_braco.items()])
    metricas = list(next(iter(t["rq7_subgrupo_com_pista"].values())))
    out += ["Subgrupo registrado: execuções com perda de mensagens, `desvio_irregular` plantado e observação não parafraseada.", ""]
    out += _tabela(["Braço", *(NOMES[m] for m in metricas)],
                   [[ROTULOS[b], *(_d(v[m], m) for m in metricas)] for b, v in t["rq7_subgrupo_com_pista"].items()])
    if t["ablacao"]:
        out += ["**Ablação (bloco C, porte médio, `desvio_irregular` plantado; no fechamento, pedido concorrente)**", ""]
        metricas = list(next(iter(next(iter(next(iter(t["ablacao"].values())).values())).values())))
        out += _tabela(["Variante", "Condição", "Intenção", *(NOMES[m] for m in metricas)],
                       [[f"`{v}`", f"`{c}`", f"`{i}`", *(_d(d[m], m) for m in metricas)]
                        for v, por_c in t["ablacao"].items() for c, por_i in por_c.items() for i, d in por_i.items()])
    inv = t["invariantes"]
    out += ["**Invariantes, ataques e erros (todas as execuções do SMA)**", ""]
    out += _tabela(["Medida", "Valor"], [
        ["Execuções do SMA", inv["execucoes_do_sma"]],
        ["Execuções com violação de invariante", inv["execucoes_com_violacao"]],
        ["Execuções por invariante violado", ", ".join(f"{k}: {v}" for k, v in inv["execucoes_por_invariante"].items()) or "nenhuma"],
        ["Avisos de prazo sem transição (contados à parte do INV-03)", inv["avisos_de_prazo_sem_transicao"]],
        ["Ataques aceitos / tentados", f"{inv['ataques_aceitos']} / {inv['ataques_tentados']}"],
        ["Aceitos em que a premissa do ataque não vale (decisão legítima)", inv["ataques_sem_premissa"]],
        ["Aceitos indevidos", inv["ataques_aceitos"] - inv["ataques_sem_premissa"]],
        ["Execuções que levantaram exceção", inv["execucoes_com_erro"]]])
    out += _tabela(["Bloco/condição", "Execuções do SMA", "Sem resposta explícita"],
                   [[f"`{k}`", v["execucoes"], v["sem_resposta"]] for k, v in inv["sem_resposta_por_condicao"].items()])
    return "\n".join(out)


# ---- testes.md --------------------------------------------------------------------------------------
def testes_md(resumo) -> str:
    out = ["<!-- gerado por `python -m fin_mas experimento`; não editar à mão -->",
           "Testes bilaterais sobre a média por seed (Wilcoxon pareado) ou sobre execuções (Mann-Whitney). "
           "`p (Holm)` é o p ajustado dentro da família; `sig.` marca p (Holm) < 0,05. A diferença é a − b. "
           "Efeito: delta de Cliff (desprezível < 0,147; pequeno < 0,33; médio < 0,474; grande acima).", ""]
    familias = list(dict.fromkeys(t["familia"] for t in resumo["testes"]))
    for familia in familias:
        out += [f"**Família {familia}**", ""]
        linhas = []
        for t in (x for x in resumo["testes"] if x["familia"] == familia):
            if t.get("p") is None:
                linhas.append([t["comparacao"], NOMES.get(t["metrica"], t["metrica"]), t["n"], "—", "—",
                               t.get("observacao", "—"), "—", "—", "—", "—", "—", "—", ""])
                continue
            pct = t["metrica"] in FRACOES
            dif = _n(t["diferenca_media"], pct)
            if "ic95_diferenca" in t:
                dif += f" [{_n(t['ic95_diferenca'][0], pct)}; {_n(t['ic95_diferenca'][1], pct)}]"
            identico = t.get("pares_diferentes") == 0
            linhas.append([t["comparacao"], NOMES.get(t["metrica"], t["metrica"]), t["n"], _n(t["media_a"], pct),
                           _n(t["media_b"], pct), dif, t.get("pares_diferentes", "—"),
                           "idêntico em todos os pares" if identico else f"{t['tipo']}, {t['metodo']}: {_n(float(t['estatistica']), casas=1)}",
                           "—" if identico else _n(float(t["p"]), casas=4), "—" if identico else _n(float(t["p_holm"]), casas=4),
                           _n(float(t["cliff"])), t["magnitude"], "sim" if t["significativo"] and not identico else "não"])
        out += _tabela(["Comparação (a × b)", "Métrica", "n", "Média a", "Média b", "Diferença [IC 95%]", "Pares ≠",
                        "Teste e estatística", "p", "p (Holm)", "δ de Cliff", "Efeito", "sig."], linhas)
    v = resumo["validacao_estatistica"]
    out += ["**Conferência da biblioteca estatística** (exemplos pequenos, com resultado calculado à mão; o teste de "
            "integração confere estes valores)", ""]
    out += _tabela(["Exemplo", "Valor calculado pelo código"], [
        ["média, desvio amostral e mediana de 2, 4, 4, 4, 5, 5, 7, 9", f"{v['media']}; {v['desvio']}; {v['mediana']}"],
        ["Wilcoxon exato, diferenças 8, −3, 5, 12, −1, 7, 10, 2", f"W− = {v['wilcoxon_exato']['w_menos']}; p = {v['wilcoxon_exato']['p']}"],
        ["Wilcoxon normal com empates, diferenças 1, 1, 2, −2, 3, 3, −1, 4, 5, 5",
         f"W− = {v['wilcoxon_normal']['w_menos']}; z = {v['wilcoxon_normal']['z']}; p = {v['wilcoxon_normal']['p']}"],
        ["Mann-Whitney exato, x = 19, 22, 16, 29, 24 e y = 20, 11, 17, 12",
         f"U = {v['mann_whitney_exato']['u1']} e {v['mann_whitney_exato']['u2']}; p = {v['mann_whitney_exato']['p']}"],
        ["o mesmo, aproximação normal", f"z = {v['mann_whitney_normal']['z']}; p = {v['mann_whitney_normal']['p']}"],
        ["delta de Cliff dos mesmos x e y", f"{v['cliff']} ({v['cliff_magnitude']})"],
        ["Holm sobre p = 0,01; 0,04; 0,03; 0,005", "; ".join(str(p) for p in v["holm"])],
        ["bootstrap com semente fixa", f"reprodutível: {v['bootstrap']['reprodutivel']}; contém a média: {v['bootstrap']['contem_a_media']}"]])
    return "\n".join(out)


# ---- figuras ----------------------------------------------------------------------------------------
def _figura(titulo, subtitulo, series, paineis, colunas=4, largura_painel=220, rotulo_w=0) -> str:
    """Pequenos múltiplos de barras horizontais.

    `paineis`: [{"titulo", "pct", "grupos": [(rótulo do grupo, {série: (valor, ic95 ou None)})]}].
    Cada painel tem a sua escala (um eixo por painel); a cor é sempre a da série.
    """
    barra, vao, entre_grupos, margem, topo_painel = 9, 2, 10, 14, 30
    passo = rotulo_w + largura_painel + 26

    def altura_do_painel(p):
        return topo_painel + sum(len(g[1]) * (barra + vao) + entre_grupos for g in p["grupos"]) + 6

    linhas_de_paineis = [paineis[i:i + colunas] for i in range(0, len(paineis), colunas)]
    alturas = [max(altura_do_painel(p) for p in linha) for linha in linhas_de_paineis]
    largura = margem * 2 + min(colunas, len(paineis)) * passo
    topo = 70
    altura = topo + sum(alturas) + margem
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" width="{largura}" height="{altura}" '
           f'font-family="Arial, Helvetica, sans-serif" font-size="11">',
           f'<rect width="{largura}" height="{altura}" fill="{FUNDO}"/>',
           f'<text x="{margem}" y="20" font-size="14" font-weight="700" fill="{TEXTO}">{titulo}</text>',
           f'<text x="{margem}" y="36" fill="{TEXTO_2}">{subtitulo}</text>']
    x = margem
    for serie in series:
        out.append(f'<rect x="{x}" y="46" width="10" height="10" rx="2" fill="{CORES[serie]}"/>'
                   f'<text x="{x + 14}" y="55" fill="{TEXTO_2}">{ROTULOS[serie]}</text>')
        x += 24 + 6.2 * len(ROTULOS[serie])
    y0 = topo
    for linha, h in zip(linhas_de_paineis, alturas):
        for j, p in enumerate(linha):
            x0 = margem + j * passo + rotulo_w
            valores = [v[0] for _, por_serie in p["grupos"] for v in por_serie.values() if v[0] is not None]
            tetos = [v[1][1] for _, por_serie in p["grupos"] for v in por_serie.values() if v[0] is not None and v[1]]
            maximo = 1.0 if p.get("pct") else max(valores + tetos + [1e-9])
            escala = (largura_painel - 62) / maximo
            out.append(f'<text x="{x0 - rotulo_w}" y="{y0 + 12}" font-weight="700" fill="{TEXTO_2}">{p["titulo"]}</text>')
            y = y0 + topo_painel - 8
            fim = y + sum(len(g[1]) * (barra + vao) + entre_grupos for g in p["grupos"]) - entre_grupos
            out.append(f'<line x1="{x0}" y1="{y - 3}" x2="{x0}" y2="{fim + 3}" stroke="{GRADE}"/>')
            for rotulo, por_serie in p["grupos"]:
                if rotulo_w:
                    meio = y + len(por_serie) * (barra + vao) / 2 + 2
                    out.append(f'<text x="{x0 - 8}" y="{meio:.1f}" text-anchor="end" fill="{TEXTO}">{rotulo}</text>')
                for serie, (v, ic) in por_serie.items():
                    if v is None:
                        out.append(f'<text x="{x0 + 4}" y="{y + barra - 1}" font-size="9" fill="{TEXTO_2}">n/d</text>')
                        y += barra + vao
                        continue
                    w = max(v * escala, 0)
                    texto = _n(v, p.get("pct"), casas=1)
                    if w > 0:
                        out.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{barra}" rx="2" fill="{CORES[serie]}">'
                                   f'<title>{p["titulo"]} · {rotulo + " · " if rotulo else ""}{ROTULOS[serie]}: {texto}</title></rect>')
                    fim_x = x0 + w
                    if ic and ic[1] > ic[0]:
                        a, b = x0 + ic[0] * escala, x0 + ic[1] * escala
                        meio = y + barra / 2
                        out.append(f'<line x1="{a:.1f}" y1="{meio}" x2="{b:.1f}" y2="{meio}" stroke="{TEXTO}" stroke-width="1"/>'
                                   f'<line x1="{a:.1f}" y1="{meio - 3}" x2="{a:.1f}" y2="{meio + 3}" stroke="{TEXTO}" stroke-width="1"/>'
                                   f'<line x1="{b:.1f}" y1="{meio - 3}" x2="{b:.1f}" y2="{meio + 3}" stroke="{TEXTO}" stroke-width="1"/>')
                        fim_x = max(fim_x, b)
                    out.append(f'<text x="{fim_x + 4:.1f}" y="{y + barra - 1}" font-size="9" fill="{TEXTO_2}">{texto}</text>')
                    y += barra + vao
                y += entre_grupos
        y0 += h
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _v(d):
    """(média, IC de 95%) de uma descrição; (None, None) quando não há dado."""
    if not d or d.get("media") is None:
        return (None, None)
    return (d["media"], tuple(d["ic95"]))


def figuras(resumo) -> dict:
    """nome do arquivo -> SVG."""
    t, saida = resumo["tabelas"], {}
    n = len(resumo["seeds"])
    sub = f"Média por seed em {n} seeds; o traço é o IC de 95% por bootstrap. Bloco A do experimento."
    tres = BRACOS[:3]
    q = t["rq1_qualidade_nominal"]
    saida["fig_qualidade.svg"] = _figura(
        "Qualidade sem falhas: com as mesmas funções, SMA e workflow equivalente empatam", sub, list(q),
        [{"titulo": NOMES[m] + (" (%)" if m in FRACOES else " (média)"), "pct": m in FRACOES,
          "grupos": [("", {b: _v(q[b][m]) for b in q})]}
         for m in ("classificacao_correta", "conformidade_correta", "criticas_publicadas_sem_tratamento")],
        colunas=3, largura_painel=250)
    if t["rq2_robustez"]:
        saida["fig_robustez.svg"] = _figura(
            "Robustez: fração de execuções com o mesmo resultado da execução sem falha", sub, tres,
            [{"titulo": c, "pct": True, "grupos": [("", {b: _v(v[b]["execucao_correta"]) for b in tres if b in v})]}
             for c, v in t["rq2_robustez"].items()], colunas=4, largura_painel=200)
    condicoes = [c for c in CONDICOES_A if c in t["rq3_custo"]]
    saida["fig_custo.svg"] = _figura(
        "Custo de coordenação por condição", sub, [b for b in BRACOS if b in t["rq3_custo"]["nominal"]],
        [{"titulo": NOMES[m] + " por solicitação", "grupos": [(c, {b: _v(v[m]) for b, v in t["rq3_custo"][c].items()})
                                                              for c in condicoes]}
         for m in ("mensagens_coordenacao", "latencia_ticks")], colunas=2, largura_painel=300, rotulo_w=120)
    cog = t["rq7_cognicao"]
    saida["fig_cognicao.svg"] = _figura(
        "Cognição local × básica: classificação correta e o que ela custa", sub, ["sma_basico", "sma_local"],
        [{"titulo": NOMES[m] + (" (%)" if m in FRACOES else ""), "pct": m in FRACOES,
          "grupos": [(c, {b: _v(cog[c][b][m]) for b in ("sma_basico", "sma_local")}) for c in cog]}
         for m in ("classificacao_correta", "mensagens_coordenacao")]
        + [{"titulo": "Subgrupo com pista na planilha, sob perda (%)", "pct": True,
            "grupos": [("classificação", {b: _v(v["classificacao_correta"]) for b, v in t["rq7_subgrupo_com_pista"].items()})]}],
        colunas=3, largura_painel=230, rotulo_w=120)
    par = t["rq5_parametros"]
    if par:
        desenho = (("max_tentativas", "execucao_correta", "combinadas"), ("prazo_subtarefa", "latencia_ticks", "combinadas"),
                   ("prazo_aprovacao", "concluida", "combinadas"), ("limiar_percentual", "classificacao_correta", "nominal"),
                   ("ttl_reserva", "concluida", "combinadas"), ("max_correcoes", "criticas_corrigidas", "nominal"))
        from fin_mas.estudo import PADRAO_VARREDURA, VARREDURA
        paineis = []
        for parametro, metrica, condicao in desenho:
            grupos = []
            for nivel in VARREDURA[parametro]:
                variante = "padrao" if nivel == PADRAO_VARREDURA[parametro] else f"{parametro}={nivel}"
                if variante in par:
                    grupos.append((f"{nivel}{' (padrão)' if variante == 'padrao' else ''}",
                                   {b: _v(d[metrica]) for b, d in par[variante][condicao].items()
                                    if b == "sma_basico" or parametro in ("max_correcoes", "prazo_aprovacao", "limiar_percentual")}))
            if len(grupos) > 1:
                paineis.append({"titulo": f"{parametro}: {NOMES[metrica].lower()}, {condicao}", "pct": metrica in FRACOES,
                                "grupos": grupos})
        saida["fig_sensibilidade.svg"] = _figura(
            "Sensibilidade a parâmetros (porte médio, um parâmetro por vez)",
            f"Média por seed em {n} seeds; o traço é o IC de 95%. Bloco B.", ["sma_basico", "wf_equivalente"], paineis,
            colunas=3, largura_painel=230, rotulo_w=80)
    abl = t["ablacao"]
    if abl:
        desenho = (("sem_reenvio", "execucao_correta", "perda_media", None),
                   ("sem_reserva", "publicacoes_do_periodo", "nominal", "fechar_mes"),
                   ("sem_correcao", "criticas_corrigidas", "nominal", "fechar_mes"),
                   ("sem_negociacao", "classificacao_correta", "consulta_instavel", "avaliar_orcamento"),
                   ("sem_cognicao_local", "classificacao_correta", "consulta_instavel", None))
        paineis = []
        for variante, metrica, condicao, intencao in desenho:
            if variante not in abl or condicao not in abl[variante]:
                continue
            grupos = []
            for v in ("completo", variante):
                braco = "sma_local" if ABLACAO[v][1] == "local" else "sma_basico"
                for i in ((intencao,) if intencao else INTENCOES):
                    grupos.append((f"{v}{'' if intencao else ' · ' + i.split('_')[0]}", {braco: _v(abl[v][condicao][i][metrica])}))
            paineis.append({"titulo": f"{variante}: {NOMES[metrica].lower()}, {condicao}", "pct": metrica in FRACOES,
                            "grupos": grupos})
        saida["fig_ablacao.svg"] = _figura(
            "Ablação: um mecanismo desligado por vez, na medida em que ele deveria aparecer",
            f"Média por seed em {n} seeds; o traço é o IC de 95%. Bloco C (porte médio).", ["sma_basico", "sma_local"],
            paineis, colunas=3, largura_painel=220, rotulo_w=150)
    return saida

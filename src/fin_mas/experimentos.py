"""Comparação SMA x workflow centralizado (baseline) sob as mesmas seeds (CP4 e CP12).

    python -m fin_mas comparar --seeds 10 --out docs/dsm2/resultados

Grava os dados brutos (`comparacao.csv`) antes de qualquer agregação, o resumo
(`comparacao.json` e `comparacao.md`) e a figura (`comparacao.svg`).
"""
import csv
import json
from pathlib import Path
from statistics import mean

from fin_mas import baseline, metricas
from fin_mas.env.scenarios import CENARIOS, run_scenario

CENARIOS_COMPARADOS = ["fechar_mes", "avaliar_orcamento", "veto_waiver", "veto_bloqueio", "veto_correcao",
                       "correcao_parcial", "divergencia_fonte", "desvio_irregular", "orc_sem_cin",
                       "falha_especialista", "depuracao"]
CAMPOS = ["cenario", "seed", "estrategia", "status", "concluida", "resposta_explicita", "dre_correta",
          "desvios_corretos", "falsos_desvios", "criticas_publicadas_sem_tratamento", "criticas_corrigidas",
          "mensagens_a2a", "latencia_ticks", "decisoes", "distribuicao_decisoria", "reconsideracoes",
          "intervencoes_humanas", "trace_completo", "hash"]
SERIES = {"SMA": "#2a78d6", "workflow": "#eb6834"}  # slots 1 e 2 da paleta validada (skill dataviz)


def executar(seeds=range(1, 11), cenarios=None) -> list[dict]:
    linhas = []
    for nome in cenarios or CENARIOS_COMPARADOS:
        for seed in seeds:
            e = run_scenario(nome, seed=seed)
            linhas.append({"cenario": nome, "seed": seed, "estrategia": "SMA", **metricas.medir(e), "hash": e.hash})
            ds = e.system.ambiente.dataset()
            # o baseline lê o dataset como o ERP o entregou, antes das correções humanas
            original = type(ds)(seed=ds.seed, competencia=ds.competencia, plantar=ds.plantar)
            res = baseline.executar(original, CENARIOS[nome].intencao)
            linhas.append({"cenario": nome, "seed": seed, "estrategia": "workflow",
                           **metricas.medir_baseline(res, original), "hash": ""})
    return linhas


def reprodutibilidade(cenarios=None, seed=7) -> float:
    """MET-12: fração de cenários cujo hash do trace se repete na segunda execução."""
    nomes = cenarios or CENARIOS_COMPARADOS
    iguais = sum(run_scenario(n, seed=seed).hash == run_scenario(n, seed=seed).hash for n in nomes)
    return iguais / len(nomes)


def resumir(linhas) -> dict:
    def media(valores):
        v = [x for x in valores if x is not None and x != ""]
        return round(mean(v), 3) if v else None

    resumo = {}
    for nome in dict.fromkeys(r["cenario"] for r in linhas):
        resumo[nome] = {}
        for estrategia in SERIES:
            grupo = [r for r in linhas if r["cenario"] == nome and r["estrategia"] == estrategia]
            resumo[nome][estrategia] = {
                "runs": len(grupo),
                "status": max(set(r["status"] for r in grupo), key=[r["status"] for r in grupo].count),
                **{campo: media(r[campo] for r in grupo) for campo in CAMPOS[4:-1] if campo != "status"},
            }
    respostas_sma = [r for r in linhas if r["estrategia"] == "SMA"]
    resumo["_global"] = {
        "MET-01_conclusao": media(r["concluida"] for r in respostas_sma),
        "MET-13_resposta_explicita": media(r["resposta_explicita"] for r in respostas_sma),
        "MET-14_distribuicao_decisoria": media(r["distribuicao_decisoria"] for r in respostas_sma),
        "MET-07_trace_completo": media(r["trace_completo"] for r in respostas_sma),
        "seeds": sorted({r["seed"] for r in linhas}),
    }
    return resumo


def gravar(linhas, resumo, out) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "comparacao.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows({k: ("" if r.get(k) is None else r.get(k)) for k in CAMPOS} for r in linhas)
    (out / "comparacao.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                         encoding="utf-8")
    (out / "comparacao.md").write_text(tabela_md(resumo), encoding="utf-8")
    (out / "comparacao.svg").write_text(figura_svg(resumo), encoding="utf-8")


def _fmt(v, pct=False):
    if v is None:
        return "—"
    return f"{v * 100:.0f}%" if pct else (f"{v:.1f}" if isinstance(v, float) else str(v))


def tabela_md(resumo) -> str:
    g = resumo["_global"]
    linhas = [
        "<!-- gerado por `python -m fin_mas comparar`; não editar à mão -->",
        f"Seeds: {g['seeds'][0]} a {g['seeds'][-1]} ({len(g['seeds'])} por cenário e estratégia).",
        "",
        "| Cenário | Estratégia | Status típico | Desvios corretos | Falsos desvios | Críticas publicadas "
        "sem tratamento | Críticas corrigidas | Mensagens A2A | Latência (ticks) | Decisões fora do ORQ "
        "| Reconsiderações |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for nome, por_estrategia in resumo.items():
        if nome.startswith("_"):
            continue
        for estrategia, m in por_estrategia.items():
            linhas.append(
                f"| `{nome}` | {estrategia} | {m['status']} | {_fmt(m['desvios_corretos'], True)} "
                f"| {_fmt(m['falsos_desvios'])} | {_fmt(m['criticas_publicadas_sem_tratamento'])} "
                f"| {_fmt(m['criticas_corrigidas'])} | {_fmt(m['mensagens_a2a'])} | {_fmt(m['latencia_ticks'])} "
                f"| {_fmt(m['distribuicao_decisoria'], True)} | {_fmt(m['reconsideracoes'])} |")
    linhas += ["", f"MET-01 (conclusão com `inform`): {_fmt(g['MET-01_conclusao'], True)} · "
               f"MET-13 (resposta explícita): {_fmt(g['MET-13_resposta_explicita'], True)} · "
               f"MET-14 (decisões fora do Orquestrador): {_fmt(g['MET-14_distribuicao_decisoria'], True)} · "
               f"MET-07 (trace completo): {_fmt(g['MET-07_trace_completo'], True)}", ""]
    if "MET-12_reprodutibilidade" in g:
        linhas[-1:] = [f"MET-12 (mesmo hash na segunda execução): {_fmt(g['MET-12_reprodutibilidade'], True)}", ""]
    return "\n".join(linhas)


def figura_svg(resumo) -> str:
    """Três painéis (pequenos múltiplos, um eixo cada) de barras horizontais SMA x workflow."""
    nomes = [n for n in resumo if not n.startswith("_")]
    paineis = [("desvios_corretos", "Desvios classificados como no gabarito (%)", True),
               ("criticas_publicadas_sem_tratamento", "Críticas publicadas sem tratamento (média)", False),
               ("mensagens_a2a", "Mensagens A2A por solicitação (média)", False)]
    rotulo_w, painel_w, barra_h, gap = 150, 230, 7, 2
    linha_h = 2 * barra_h + gap + 10
    topo = 64
    altura = topo + len(nomes) * linha_h + 30
    largura = rotulo_w + len(paineis) * (painel_w + 30) + 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" width="{largura}" '
           f'height="{altura}" font-family="Arial, Helvetica, sans-serif" font-size="11">',
           f'<rect width="{largura}" height="{altura}" fill="#fcfcfb"/>',
           '<text x="10" y="20" font-size="14" font-weight="700" fill="#0b0b0b">SMA (agentes) x workflow '
           'centralizado, médias em 10 seeds</text>']
    lx = 10
    for estrategia, cor in SERIES.items():
        out.append(f'<rect x="{lx}" y="32" width="10" height="10" rx="2" fill="{cor}"/>'
                   f'<text x="{lx + 14}" y="41" fill="#52514e">{"SMA (agentes)" if estrategia == "SMA" else "workflow centralizado"}</text>')
        lx += 160
    for i, nome in enumerate(nomes):
        y = topo + i * linha_h
        out.append(f'<text x="{rotulo_w - 8}" y="{y + barra_h + 4}" text-anchor="end" fill="#0b0b0b">{nome}</text>')
    for p, (campo, titulo, pct) in enumerate(paineis):
        x0 = rotulo_w + p * (painel_w + 30)
        maximo = 1.0 if pct else max([resumo[n][e][campo] or 0 for n in nomes for e in SERIES] + [1])
        out.append(f'<text x="{x0}" y="{topo - 8}" font-weight="700" fill="#52514e">{titulo}</text>')
        out.append(f'<line x1="{x0}" y1="{topo - 2}" x2="{x0}" y2="{topo + len(nomes) * linha_h - 6}" '
                   f'stroke="#d6d5d0"/>')
        for i, nome in enumerate(nomes):
            for j, (estrategia, cor) in enumerate(SERIES.items()):
                v = resumo[nome][estrategia][campo]
                y = topo + i * linha_h + j * (barra_h + gap)
                if v is None:
                    out.append(f'<text x="{x0 + 4}" y="{y + barra_h}" font-size="9" fill="#8a8984">n/a</text>')
                    continue
                w = 0 if maximo == 0 else max(v / maximo * (painel_w - 40), 0)
                if w > 0:
                    out.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{barra_h}" rx="2" fill="{cor}">'
                               f'<title>{nome} · {estrategia}: {_fmt(v, pct)}</title></rect>')
                out.append(f'<text x="{x0 + w + 4:.1f}" y="{y + barra_h}" font-size="9" fill="#52514e">'
                           f'{_fmt(v, pct)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"

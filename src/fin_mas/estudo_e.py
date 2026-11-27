"""Bloco E do experimento da DSM4 (revisão de 26/11, depois do feedback da DSM3).

O professor pediu, além do que os blocos A a D já cobrem, três fatores que estavam fracos ou ausentes:

- **pedidos concorrentes** (1, 2 e 4 fechamentos ao mesmo tempo, da mesma competência ou de competências
  diferentes): o SMA reserva o período (PROT-LCK) e atende em paralelo; o workflow centralizado atende em fila;
- **frequência de irregularidades** (baixa, média e alta), com quatro tipos plantados (alçada, SoD,
  duplicidade, competência), cada um com probabilidade própria por seed. Os sorteios são aninhados: o que
  está plantado na frequência baixa também está na média e na alta (comparação pareada por seed);
- **volume de lançamentos** (12, 96 e 400 lançamentos de base), com **tempo de parede** medido. O tempo
  lógico (ticks) não depende do volume, por construção do relógio do barramento; quem mede o custo do volume
  é o tempo de parede, que fica num CSV separado porque varia entre execuções e máquinas.

Dois braços, sob as mesmas seeds: o SMA básico e o workflow centralizado equivalente (`baseline_eq`), com o
mesmo aprovador (decide corrigir). Cada execução vira uma linha de `execucoes.csv`, gravada antes da análise.
A análise usa a seed como unidade, IC de 95% por bootstrap, desvio-padrão, Wilcoxon pareado SMA x workflow em
cada nível e Holm dentro de cada fator (`estudo.comparar`, `estudo.ajustar`).

    python -m fin_mas.estudo_e --replicas 30 --out docs/dsm4/resultados/bloco_e
"""
import argparse
import csv
import hashlib
import json
import random
import time
from pathlib import Path

from fin_mas import __version__, baseline_eq, estatistica, metricas
from fin_mas.env.dataset import Ambiente, Dataset
from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.estudo import ajustar, comparar, medir_sma, protocolos_em_cache, selecionar

BRACOS = ("sma_basico", "wf_equivalente")
PORTE = "media"
CONCORRENCIA = (1, 2, 4)
MODOS = ("mesma", "distintas")  # mesma competência (conflito pelo período) ou competências diferentes
COMPETENCIAS = ("2026-09", "2026-08", "2026-07", "2026-06")
FREQUENCIAS = {"baixa": 0.15, "media": 0.40, "alta": 0.80}
TIPOS = ("alcada", "sod", "duplicidade", "competencia")
VOLUMES = (12, 96, 400)
CAMPOS = ["fator", "nivel", "modo", "braco", "seed", "pedidos", "plantios", "lancamentos", "publicados", "recusados",
          "falhas", "publicacoes_indevidas", "conformidade_correta", "criticas_corrigidas",
          "criticas_publicadas_sem_tratamento", "intervencoes_humanas", "reconsideracoes", "mensagens",
          "makespan_ticks", "hash"]
METRICAS = ("publicados", "recusados", "publicacoes_indevidas", "conformidade_correta", "criticas_corrigidas",
            "criticas_publicadas_sem_tratamento", "intervencoes_humanas", "reconsideracoes", "mensagens",
            "makespan_ticks")


def plantios(seed: int, frequencia: float) -> tuple:
    """Tipos plantados nesta seed: um sorteio por tipo, o mesmo em todas as frequências (aninhado)."""
    sorteio = random.Random(f"bloco-e:{seed}")
    return tuple(t for t in TIPOS if sorteio.random() < frequencia)


# ---- execução de um braço ------------------------------------------------------------------------
def _sma(seed, pedidos: list[tuple[str, tuple]], volume=12) -> dict:
    """`pedidos`: [(competência, plantios), ...] abertos ao mesmo tempo (atraso 1)."""
    agenda = {}
    for c, p in pedidos:
        agenda.setdefault(c, p)
    if len(agenda) == 1 and volume != 12:  # volume: um mês só, com a base de lançamentos pedida
        (c, p), = agenda.items()
        ambiente = Ambiente.de_dataset(Dataset(seed, competencia=c, porte=PORTE, plantar=p, volume_base=volume))
    else:
        ambiente = Ambiente(seed, agenda=agenda, porte=PORTE)
    sc = Scenario("bloco_e", "bloco E", "fechar_mes", decisao_aprovador="corrigir",
                  pedidos=tuple(("fechar_mes", c, 1) for c, _ in pedidos))
    inicio = time.perf_counter()
    e = run_scenario(sc, seed=seed, ambiente=ambiente)
    segundos = time.perf_counter() - inicio  # só o fechamento; as medidas abaixo ficam fora do tempo de parede
    medidas = [metricas.medir(e, sid) for sid in e.sids]
    respostas = e.respostas
    publicados = [sid for sid, r in respostas.items() if r is not None and r.performative == "inform"]
    por_mes = {}
    for sid in publicados:
        por_mes[respostas[sid].content.get("competencia")] = por_mes.get(respostas[sid].content.get("competencia"), 0) + 1
    abertura = {r["conversation_id"]: r["t"] for r in e.audit.records if r["kind"] == "open" and r.get("protocol") == "PROT-SOL"}
    fins = [abertura[sid] + m["latencia_ticks"] for sid, m in zip(e.sids, medidas) if m["latencia_ticks"] is not None]
    return {
        "pedidos": len(pedidos), "lancamentos": sum(len(ambiente.dataset(c).lancamentos) for c in agenda),
        "publicados": len(publicados),
        "recusados": sum(1 for r in respostas.values() if r is not None and r.performative == "refuse"),
        "falhas": sum(1 for r in respostas.values() if r is None or r.performative == "failure"),
        "publicacoes_indevidas": sum(n - 1 for n in por_mes.values() if n > 1),
        "conformidade_correta": medir_sma(e)["conformidade_correta"] if len(pedidos) == 1 else None,
        "criticas_corrigidas": _criticas_corrigidas(ambiente.dataset(c) for c in agenda),
        **{k: sum(m[k] or 0 for m in medidas) for k in ("criticas_publicadas_sem_tratamento", "intervencoes_humanas",
                                                         "reconsideracoes")},
        "mensagens": sum(m["mensagens_a2a"] for m in medidas),
        "makespan_ticks": (max(fins) - min(abertura[s] for s in e.sids)) if fins else None, "hash": e.hash,
        "segundos": segundos,
    }


def _workflow(seed, pedidos: list[tuple[str, tuple]], volume=12) -> dict:
    """O controlador centralizado atende os pedidos em fila, sobre os mesmos dados (o ERP guarda as correções)."""
    ambientes, linhas, digest, segundos = {}, [], hashlib.sha256(), 0.0
    for c, p in pedidos:
        if c not in ambientes:
            ds = Dataset(seed, competencia=c, porte=PORTE, plantar=p, volume_base=volume) if volume != 12 else \
                Ambiente(seed, agenda={c: p}, porte=PORTE).dataset(c)
            ambientes[c] = Ambiente.de_dataset(ds)
        inicio = time.perf_counter()
        w = baseline_eq.executar(seed=seed, ambiente=ambientes[c], decisao_aprovador="corrigir")
        segundos += time.perf_counter() - inicio
        criticas = [n for n in w.dataset.gold["nao_conformidades"] if n["severidade"] == "critica"]
        corrigidos = {x["lancamento"] for x in w.dataset.correcoes}
        linhas.append((c, w, criticas, corrigidos))
        digest.update(w.audit.digest().encode())
    por_mes = {}
    for c, w, _, _ in linhas:
        if w.publicado:
            por_mes[c] = por_mes.get(c, 0) + 1
    w0 = linhas[0][1]
    return {
        "pedidos": len(pedidos), "lancamentos": sum(len(a.dataset().lancamentos) for a in ambientes.values()),
        "publicados": sum(1 for _, w, _, _ in linhas if w.publicado), "recusados": 0,
        "falhas": sum(1 for _, w, _, _ in linhas if not w.publicado),
        "publicacoes_indevidas": sum(n - 1 for n in por_mes.values() if n > 1),
        "conformidade_correta": (estudo_conformidade(w0) if len(pedidos) == 1 else None),
        "criticas_corrigidas": _criticas_corrigidas(a.dataset() for a in ambientes.values()),
        "criticas_publicadas_sem_tratamento": sum(
            sum(1 for n in cr if n["lancamento"] not in co
                and not any(x.startswith(f"waiver de {n['regra']} em {n['lancamento']}") for x in w.ressalvas))
            for _, w, cr, co in linhas if w.publicado),
        "intervencoes_humanas": sum(sum(1 for r in w.audit.records if r["kind"] == "send"
                                        and r["performative"] in ("approve", "reject")) for _, w, _, _ in linhas),
        "reconsideracoes": 0,
        "mensagens": sum(sum(1 for r in w.audit.records if r["kind"] in ("open", "send") and r.get("protocol"))
                         for _, w, _, _ in linhas),
        "makespan_ticks": sum(w.ticks for _, w, _, _ in linhas),  # em fila: um depois do outro
        "hash": digest.hexdigest(), "segundos": segundos,
    }


def _criticas_corrigidas(datasets) -> int:
    """Lançamentos com não conformidade crítica corrigidos, cada um uma vez por competência (dois pedidos do mesmo
    mês corrigindo o mesmo lançamento contam uma correção, não duas)."""
    total = 0
    for ds in datasets:
        corrigidos = {x["lancamento"] for x in ds.correcoes}
        total += len({n["lancamento"] for n in ds.gold["nao_conformidades"]
                      if n["severidade"] == "critica" and n["lancamento"] in corrigidos})
    return total


def estudo_conformidade(w) -> int | None:
    from fin_mas.estudo import _conformidade
    return _conformidade(w.achados, w.dataset.gold)


# ---- plano ----------------------------------------------------------------------------------------
def celulas(replicas: int = 30):
    for seed in range(1, replicas + 1):
        # concorrência e volume: irregularidades sorteadas por seed (frequência média), para o efeito estrutural
        # (reserva, paralelismo, custo do volume) aparecer sobre dados que variam, e não sobre um plantio fixo
        base = plantios(seed, FREQUENCIAS["media"])
        for n in CONCORRENCIA:
            for modo in MODOS:
                if n == 1 and modo == "distintas":
                    continue  # um pedido só: os dois modos são a mesma coisa
                comps = [COMPETENCIAS[0]] * n if modo == "mesma" else list(COMPETENCIAS[:n])
                yield "concorrencia", str(n), modo, seed, [(c, base) for c in comps], 12
        for nivel, p in FREQUENCIAS.items():
            yield "frequencia", nivel, "-", seed, [(COMPETENCIAS[0], plantios(seed, p))], 12
        for v in VOLUMES:
            yield "volume", str(v), "-", seed, [(COMPETENCIAS[0], base)], v


def executar(replicas: int = 30) -> tuple[list[dict], list[dict]]:
    linhas, tempos = [], []
    with protocolos_em_cache():
        _sma(1, [(COMPETENCIAS[0], ())])  # aquecimento (imports e caches): fora do tempo de parede medido
        _workflow(1, [(COMPETENCIAS[0], ())])
        for fator, nivel, modo, seed, pedidos, volume in celulas(replicas):
            for braco in BRACOS:
                medidas = (_sma if braco == "sma_basico" else _workflow)(seed, pedidos, volume)
                linha = {"fator": fator, "nivel": nivel, "modo": modo, "braco": braco, "seed": seed,
                         "plantios": "+".join(sorted({t for _, p in pedidos for t in p})) or "nenhum", **medidas}
                linhas.append({k: linha.get(k) for k in CAMPOS})
                tempos.append({"fator": fator, "nivel": nivel, "modo": modo, "braco": braco, "seed": seed,
                               "segundos": round(medidas["segundos"], 4)})
    return linhas, tempos


# ---- análise --------------------------------------------------------------------------------------
def analisar(linhas, tempos) -> dict:
    niveis = {"concorrencia": [(str(n), m) for n in CONCORRENCIA for m in MODOS if not (n == 1 and m == "distintas")],
              "frequencia": [(n, "-") for n in FREQUENCIAS], "volume": [(str(v), "-") for v in VOLUMES]}
    descricao, testes = [], []
    for fator, combinacoes in niveis.items():
        for nivel, modo in combinacoes:
            for braco in BRACOS:
                sel = selecionar(linhas, fator=fator, nivel=nivel, modo=modo, braco=braco)
                d = {"fator": fator, "nivel": nivel, "modo": modo, "braco": braco}
                for m in METRICAS:
                    valores = [r[m] for r in sel if r[m] is not None]
                    if valores:
                        d[m] = estatistica.descrever(_por_seed(sel, m).values())
                t = selecionar(tempos, fator=fator, nivel=nivel, modo=modo, braco=braco)
                d["segundos"] = estatistica.descrever(_por_seed(t, "segundos").values())
                descricao.append(d)
            sma = selecionar(linhas, fator=fator, nivel=nivel, modo=modo, braco="sma_basico")
            wf = selecionar(linhas, fator=fator, nivel=nivel, modo=modo, braco="wf_equivalente")
            for m in ("makespan_ticks", "mensagens", "publicacoes_indevidas", "criticas_publicadas_sem_tratamento",
                      "criticas_corrigidas"):
                testes.append(comparar(f"E:{fator}", f"{nivel}/{modo}", m, sma, wf, "SMA", "workflow"))
    for braco in BRACOS:  # o custo do volume está no tempo de parede: 400 x 12 lançamentos, pareado por seed
        maior = selecionar(tempos, fator="volume", nivel=str(VOLUMES[-1]), braco=braco)
        menor = selecionar(tempos, fator="volume", nivel=str(VOLUMES[0]), braco=braco)
        testes.append(comparar("E:volume", f"{VOLUMES[-1]} x {VOLUMES[0]} ({braco})", "segundos", maior, menor,
                               str(VOLUMES[-1]), str(VOLUMES[0])))
    return {"versao": __version__, "descricao": descricao, "testes": ajustar(testes)}


def _por_seed(linhas, metrica) -> dict:
    grupos = {}
    for r in linhas:
        if r.get(metrica) is not None:
            grupos.setdefault(r["seed"], []).append(float(r[metrica]))
    return {s: sum(v) / len(v) for s, v in sorted(grupos.items())}


def _p(t) -> str:
    """p ajustado (Holm); sem nenhum par diferente o teste não se aplica (identidade)."""
    if t.get("pares_diferentes") == 0:
        return "idênticos"
    p = t.get("p_holm")
    return "—" if p is None else ("< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ","))


def _fmt(d) -> str:
    if not d:
        return "—"
    ic = d["ic95"]
    return f"{d['media']:.2f} ± {d['desvio']:.2f} [{ic[0]:.2f}; {ic[1]:.2f}]"


def tabela_md(resumo) -> str:
    seeds = max((d["segundos"]["n"] for d in resumo["descricao"]), default=0)
    linhas = ["# Bloco E: concorrência, frequência de irregularidades e volume", "",
              f"Versão {resumo['versao']}. Cada célula: média ± desvio-padrão [IC 95% por bootstrap], com a seed como",
              f"unidade ({seeds} seeds). Testes: Wilcoxon pareado por seed (SMA − workflow), Holm dentro de cada fator.", ""]
    cols = ("publicados", "recusados", "publicacoes_indevidas", "criticas_publicadas_sem_tratamento", "mensagens",
            "makespan_ticks", "reconsideracoes", "intervencoes_humanas", "segundos")
    for fator in ("concorrencia", "frequencia", "volume"):
        linhas += [f"## {fator}", "", "| nível | modo | braço | " + " | ".join(cols) + " |",
                   "|" + "---|" * (3 + len(cols))]
        for d in resumo["descricao"]:
            if d["fator"] == fator:
                linhas.append(f"| {d['nivel']} | {d['modo']} | {d['braco']} | " + " | ".join(_fmt(d.get(c)) for c in cols) + " |")
        linhas += ["", "A = SMA e B = workflow; nas linhas `400 x 12`, A = 400 e B = 12 lançamentos, no mesmo braço.", "",
                   "| comparação | métrica | média A | média B | dif. A − B [IC 95%] | p (Holm) | Cliff |",
                   "|---|---|---|---|---|---|---|"]
        for t in resumo["testes"]:
            if t["familia"] == f"E:{fator}" and t.get("p") is not None:
                ic = t["ic95_diferenca"]
                linhas.append(f"| {t['comparacao']} | {t['metrica']} | {t['media_a']} | {t['media_b']} | "
                              f"{t['diferenca_media']} [{ic[0]}; {ic[1]}] | {_p(t)} | {t['cliff']} |")
        linhas.append("")
    return "\n".join(linhas) + "\n"


def gravar(out: Path, linhas, tempos, resumo) -> str:
    out.mkdir(parents=True, exist_ok=True)
    for nome, dados, campos in (("execucoes.csv", linhas, CAMPOS),
                                ("tempo_parede.csv", tempos, ["fator", "nivel", "modo", "braco", "seed", "segundos"])):
        with (out / nome).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
            w.writeheader()
            w.writerows(dados)
    (out / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
    (out / "resumo.md").write_text(tabela_md(resumo), encoding="utf-8")
    return hashlib.sha256((out / "execucoes.csv").read_bytes()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="bloco E do experimento da DSM4")
    ap.add_argument("--replicas", type=int, default=30)
    ap.add_argument("--out", type=Path, default=Path("docs/dsm4/resultados/bloco_e"))
    args = ap.parse_args(argv)
    linhas, tempos = executar(args.replicas)
    resumo = analisar(linhas, tempos)
    sha = gravar(args.out, linhas, tempos, resumo)
    print(f"{len(linhas)} execuções em {args.out} (execucoes.csv sha256 {sha[:16]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

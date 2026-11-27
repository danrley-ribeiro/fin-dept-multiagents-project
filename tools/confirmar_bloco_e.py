"""Confere as hipóteses H-E1 a H-E8 do bloco E contra os critérios pré-registrados.

Os critérios estão em docs/dsm4/experimento-bloco-e.md (commit anterior ao da replicação). Este script só lê o
que `python -m fin_mas.estudo_e` gravou (execucoes.csv e resumo.json) e decide, hipótese a hipótese, se o critério
vale. Não ajusta nada: o que não passa é relatado como refutado.

    python tools/confirmar_bloco_e.py docs/dsm4/resultados/bloco_e_confirmatorio
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ALFA = 0.05
BRACOS = ("sma_basico", "wf_equivalente")
INTEIRAS = ("seed", "pedidos", "publicados", "recusados", "publicacoes_indevidas", "criticas_publicadas_sem_tratamento",
            "intervencoes_humanas", "mensagens", "makespan_ticks", "waivers")


def carregar(pasta: Path) -> tuple[list[dict], dict]:
    with (pasta / "execucoes.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    for r in linhas:
        for c in INTEIRAS:
            r[c] = int(r[c]) if r.get(c) not in (None, "") else None
    resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf-8"))
    return linhas, resumo


def _sel(linhas, **filtro):
    return [r for r in linhas if all(r[k] == v for k, v in filtro.items())]


def _teste(resumo, fator, comparacao, metrica) -> dict:
    achados = [t for t in resumo["testes"] if t["familia"] == f"E:{fator}" and t["comparacao"] == comparacao
               and t["metrica"] == metrica]
    if len(achados) != 1:
        raise LookupError(f"teste ausente: E:{fator} {comparacao} {metrica}")
    return achados[0]


def _significativo(t, sentido: int) -> bool:
    """Diferença A − B no sentido pedido (+1 ou −1) com p de Holm < 0,05."""
    p = t.get("p_holm")
    return t.get("pares_diferentes", 0) > 0 and p is not None and p < ALFA and t["diferenca_media"] * sentido > 0


def _p(t) -> str:
    if t.get("pares_diferentes") == 0:
        return "idênticos"
    p = t.get("p_holm")
    return "—" if p is None else ("< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ","))


def _dif(t) -> str:
    return f"{t['media_a']} × {t['media_b']} (dif. {t['diferenca_media']}, p {_p(t)})"


def _sem_critica(linhas) -> tuple[bool, int]:
    ruins = [r for r in linhas if r["criticas_publicadas_sem_tratamento"] != 0]
    return not ruins, len(ruins)


def h1(linhas, resumo):
    ok, ev = True, []
    for n in (2, 4):
        sel = _sel(linhas, fator="concorrencia", nivel=str(n), modo="mesma")
        indevidas = sum(r["publicacoes_indevidas"] for r in sel)
        fora = [r for r in sel if r["recusados"] != n - 1]
        ok &= bool(sel) and indevidas == 0 and not fora
        ev.append(f"{n} pedidos: {len(sel)} execuções, publicações indevidas {indevidas}, "
                  f"execuções com recusados ≠ {n - 1}: {len(fora)}")
    return ok, ev


def h2(linhas, resumo):
    ok, ev = True, []
    for n in (2, 4):
        t = _teste(resumo, "concorrencia", f"{n}/distintas", "makespan_ticks")
        ok &= _significativo(t, -1)
        ev.append(f"{n} meses, makespan SMA × workflow: {_dif(t)}")
    return ok, ev


def h3(linhas, resumo):
    ok, ev = True, []
    for comp in ("1/mesma", "2/mesma", "2/distintas", "4/mesma", "4/distintas"):
        t = _teste(resumo, "concorrencia", comp, "mensagens")
        ok &= _significativo(t, +1)
        ev.append(f"{comp}, mensagens SMA × workflow: {_dif(t)}")
    return ok, ev


def h4(linhas, resumo):
    ok, ev = True, []
    for fator in ("concorrencia", "porte"):
        sma = {(r["nivel"], r["modo"], r["seed"]): r for r in _sel(linhas, fator=fator, braco="sma_basico")}
        wf = {(r["nivel"], r["modo"], r["seed"]): r for r in _sel(linhas, fator=fator, braco="wf_equivalente")}
        pares = sorted(set(sma) & set(wf))
        diferentes = {m: sum(sma[k][m] != wf[k][m] for k in pares)
                      for m in ("publicados", "recusados", "waivers", "criticas_publicadas_sem_tratamento")}
        ok &= bool(pares) and len(pares) == len(sma) == len(wf) and not any(diferentes.values())
        ev.append(f"{fator}: {len(pares)} pares seed a seed; pares diferentes por métrica: "
                  + ", ".join(f"{m} {v}" for m, v in diferentes.items()))
    return ok, ev


def h5(linhas, resumo):
    ok, ev = True, []
    for n in (2, 4):
        t = _teste(resumo, "concorrencia_perda", f"{n}/distintas", "publicados")
        ok &= _significativo(t, -1)
        ev.append(f"{n} meses, publicados SMA × workflow: {_dif(t)}")
    limpo, ruins = _sem_critica(_sel(linhas, fator="concorrencia_perda"))
    ok &= limpo
    ev.append(f"execuções com crítica publicada sem tratamento: {ruins}")
    return ok, ev


def h6(linhas, resumo):
    ok, ev = True, []
    for n in (2, 4):
        t = _teste(resumo, "concorrencia_indisponibilidade", f"{n}/distintas", "publicados")
        igual = abs(t["diferenca_media"]) <= 0.1 and not _significativo(t, +1) and not _significativo(t, -1)
        ok &= igual
        ev.append(f"{n} meses, publicados SMA × workflow: {_dif(t)}")
    t = _teste(resumo, "concorrencia_indisponibilidade", "4/distintas", "makespan_ticks")
    ok &= _significativo(t, -1)
    ev.append(f"4 meses, makespan SMA × workflow: {_dif(t)}")
    limpo, ruins = _sem_critica(_sel(linhas, fator="concorrencia_indisponibilidade"))
    ok &= limpo
    ev.append(f"execuções com crítica publicada sem tratamento: {ruins}")
    return ok, ev


def h7(linhas, resumo):
    ok, ev = True, []
    for braco in BRACOS:
        medias = []
        for nivel in ("baixa", "media", "alta"):
            sel = _sel(linhas, fator="frequencia", nivel=nivel, braco=braco)
            medias.append(sum(r["intervencoes_humanas"] for r in sel) / len(sel) if sel else float("nan"))
        ok &= medias[0] < medias[1] < medias[2]
        ev.append(f"{braco}: intervenções médias baixa {medias[0]:.2f}, média {medias[1]:.2f}, alta {medias[2]:.2f}")
    limpo, ruins = _sem_critica(_sel(linhas, fator="frequencia"))
    ok &= limpo
    ev.append(f"execuções com crítica publicada sem tratamento: {ruins}")
    return ok, ev


def h8(linhas, resumo):
    ok, ev = True, []
    for braco in BRACOS:
        por_seed: dict[int, set] = {}
        for r in _sel(linhas, fator="volume", braco=braco):
            por_seed.setdefault(r["seed"], set()).add(r["makespan_ticks"])
        variam = [s for s, v in por_seed.items() if len(v) != 1]
        ok &= bool(por_seed) and not variam
        ev.append(f"{braco}: seeds em que o makespan muda com o volume: {len(variam)} de {len(por_seed)}")
    t = _teste(resumo, "volume", "400 x 12 (sma_basico)", "segundos")
    ok &= _significativo(t, +1)
    ev.append(f"SMA, segundos 400 × 12 lançamentos: {_dif(t)}")
    return ok, ev


HIPOTESES = (("H-E1", "o mesmo mês é publicado no máximo uma vez; os demais pedidos são recusados", h1),
             ("H-E2", "com meses diferentes, o SMA termina antes do workflow em fila", h2),
             ("H-E3", "o SMA troca mais mensagens que o workflow", h3),
             ("H-E4", "com os mesmos mecanismos, os dois braços chegam ao mesmo resultado", h4),
             ("H-E5", "sob 15% de perda, o SMA publica menos e nunca publica crítica sem tratamento", h5),
             ("H-E6", "com um especialista fora do ar, o reenvio recupera", h6),
             ("H-E7", "mais irregularidades exigem mais intervenções, sem crítica publicada sem tratamento", h7),
             ("H-E8", "o tempo lógico não depende do volume; o tempo de parede, sim", h8))


def conferir(pasta: Path) -> list[dict]:
    linhas, resumo = carregar(pasta)
    resultado = []
    for ident, enunciado, f in HIPOTESES:
        ok, evidencias = f(linhas, resumo)
        resultado.append({"id": ident, "hipotese": enunciado, "confirmada": bool(ok), "evidencias": evidencias})
    return resultado


def relatorio_md(pasta: Path, resultado: list[dict]) -> str:
    linhas, resumo = carregar(pasta)
    seeds = sorted({r["seed"] for r in linhas})
    confirmadas = sum(h["confirmada"] for h in resultado)
    texto = [f"# Bloco E: conferência das hipóteses pré-registradas", "",
             f"Versão {resumo['versao']}; seeds {seeds[0]} a {seeds[-1]} ({len(seeds)}); {len(linhas)} execuções.",
             "Critérios: docs/dsm4/experimento-bloco-e.md. Gerado por `tools/confirmar_bloco_e.py`.", "",
             f"**{confirmadas} de {len(resultado)} hipóteses confirmadas.**", "",
             "| Id | Hipótese | Resultado |", "|---|---|---|"]
    texto += [f"| {h['id']} | {h['hipotese']} | {'confirmada' if h['confirmada'] else '**refutada**'} |"
              for h in resultado]
    texto.append("")
    for h in resultado:
        texto += [f"## {h['id']}: {'confirmada' if h['confirmada'] else 'refutada'}", ""]
        texto += [f"- {e}" for e in h["evidencias"]]
        texto.append("")
    return "\n".join(texto)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pasta", type=Path)
    ap.add_argument("--gravar", action="store_true", help="grava confirmacao.md na pasta")
    args = ap.parse_args(argv)
    resultado = conferir(args.pasta)
    texto = relatorio_md(args.pasta, resultado)
    if args.gravar:
        (args.pasta / "confirmacao.md").write_text(texto, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Números do relatório técnico da DSM4, gerados a partir das fontes (nada escrito à mão).

Lê:
  - docs/dsm4/resultados/resumo.json, manifesto.json e execucoes.csv (experimento);
  - a coleta do pytest (`pytest --co`) e, com --suite, o resultado da suíte inteira e do vitest;
  - a saída de `tools/trace.py --check` e os modelos (`models/*.yaml`) para os grafos de rastreabilidade;
  - o catálogo `CENARIOS` e a conferência `fin_mas cenarios --verificar`.

Grava:
  - entregas/dsm4/documentacao/numeros.tex          macros \\V{chave} e tabelas \\Tab... (\\newcommand)
  - entregas/dsm4/documentacao/rastreabilidade.tex  grafos TikZ por parte (no máximo 4 requisitos por figura)
  - docs/dsm4/cenarios-de-teste.md                  catálogo dos cenários e testes novos da DSM4

Uso (da raiz do repositório):
  python tools/relatorio_numeros.py            # coleta dos testes, sem rodar a suíte (segundos)
  python tools/relatorio_numeros.py --suite    # também roda pytest e vitest (cerca de 4 minutos)

As medidas exploratórias do experimento (RQ7, execução correta local x básico) são recalculadas aqui a
partir de execucoes.csv, com a mesma estatística do comando do experimento (src/fin_mas/estatistica.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "docs" / "dsm4" / "resultados"
DOC = RAIZ / "entregas" / "dsm4" / "documentacao"
CATALOGO = RAIZ / "docs" / "dsm4" / "cenarios-de-teste.md"
TAG_DSM3 = "dsm3-v0.5.0"  # catálogo de cenários e testes entregues na DSM3
RODADA1 = "cfa6b6f"       # commit com os dados da primeira rodada do experimento (antes da correção)
sys.path.insert(0, str(RAIZ / "src"))

CONDICOES = ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "humano_lento", "combinadas",
             "combinadas_ataque")
COND_ROTULO = {"nominal": "sem falhas", "perda_baixa": "perda de 5\\%", "perda_media": "perda de 15\\%",
               "perda_alta": "perda de 30\\%", "indisponibilidade": "indisponibilidade",
               "humano_lento": "humano lento", "combinadas": "combinadas", "combinadas_ataque": "combinadas + ataque",
               "consulta_instavel": "consulta instável"}
BRACOS = ("sma_basico", "sma_local", "wf_equivalente", "wf_minimo")


# ---------------------------------------------------------------- formatação pt-BR para o LaTeX
def _dec(x: float, casas: int) -> str:
    """Arredonda meio para cima (como na análise escrita) e formata com vírgula decimal e ponto de milhar."""
    q = Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    s = f"{q:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def num(x, casas=1) -> str:
    if x is None:
        return "---"
    if casas == 0 or float(x).is_integer() and casas == 0:
        return _dec(round(x), 0)
    s = _dec(x, casas)
    return s.replace("-", "$-$", 1) if s.startswith("-") else s


def inteiro(x) -> str:
    return _dec(int(x), 0)


def pct(x, casas=1) -> str:
    if x is None:
        return "---"
    v = 100 * x
    if abs(v - round(v)) < 1e-9 and round(v) in (0, 100):
        return f"{int(round(v))}\\%"
    return num(v, casas) + "\\%"


def pp(x, casas=1) -> str:
    """Diferença de proporções em pontos percentuais, com sinal."""
    if x is None:
        return "---"
    v = 100 * x
    s = _dec(abs(v), casas)
    return ("$-$" if v < -1e-12 else "+" if v > 1e-12 else "") + s + " pp"


def ic_pct(ic) -> str:
    return f"[{pct(ic[0])}; {pct(ic[1])}]" if ic else "---"


def ic_pp(ic) -> str:
    def f(v):
        s = _dec(abs(100 * v), 1)
        return ("$-$" if v < -1e-12 else "") + s
    return f"[{f(ic[0])}; {f(ic[1])}]" if ic else "---"


def ic_num(ic, casas=1) -> str:
    return f"[{num(ic[0], casas)}; {num(ic[1], casas)}]" if ic else "---"


def pval(p) -> str:
    if p is None:
        return "---"
    if p < 0.001:
        return "$<$\\,0,001"
    s = _dec(p, 4).rstrip("0")
    return s + "0" * max(0, 3 - len(s.split(",")[1]))


def tex(s: str) -> str:
    """Escapa texto livre para o LaTeX."""
    rep = {"\\": "\\textbackslash{}", "&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#", "_": "\\_",
           "{": "\\{", "}": "\\}", "~": "\\textasciitilde{}", "^": "\\textasciicircum{}"}
    return "".join(rep.get(c, c) for c in str(s))


# ---------------------------------------------------------------- fontes
def rodar(cmd, **kw) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src")}
    return subprocess.run(cmd, cwd=kw.pop("cwd", RAIZ), env=env, capture_output=True, text=True, **kw)


def coleta_pytest() -> dict[str, int]:
    """Testes coletados por pasta de tests/ (unit, e2e, integration, tui)."""
    r = rodar([sys.executable, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider"])
    por_pasta: dict[str, int] = {}
    for linha in r.stdout.splitlines():
        m = re.match(r"^tests/([^/]+)/\S+\.py: (\d+)$", linha.strip())  # formato -qq: "arquivo: n"
        if m:
            por_pasta[m.group(1)] = por_pasta.get(m.group(1), 0) + int(m.group(2))
            continue
        m = re.match(r"^tests/([^/]+)/\S+\.py::", linha.strip())       # formato -q: um id por linha
        if m:
            por_pasta[m.group(1)] = por_pasta.get(m.group(1), 0) + 1
    if not por_pasta:
        raise SystemExit(f"coleta do pytest falhou:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return por_pasta


def suite_pytest() -> dict:
    r = rodar([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", "-q"])
    fim = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""
    out = {"codigo": r.returncode, "resumo": fim}
    for chave in ("passed", "failed", "skipped", "error", "errors"):
        m = re.search(rf"(\d+) {chave}", fim)
        out[chave] = int(m.group(1)) if m else 0
    m = re.search(r"in ([\d.]+)s", fim)
    out["segundos"] = float(m.group(1)) if m else None
    return out


def suite_vitest() -> dict | None:
    bun = shutil.which("bun") or str(Path.home() / ".bun" / "bin" / "bun")
    if not Path(bun).exists() or not (RAIZ / "web" / "node_modules").exists():
        return None
    r = rodar([bun, "run", "test"], cwd=RAIZ / "web")
    m = re.search(r"Tests\s+(\d+) passed", r.stdout)
    return {"codigo": r.returncode, "passaram": int(m.group(1)) if m else 0}


def contar_vitest() -> int:
    n = 0
    for p in (RAIZ / "web" / "src").rglob("*.test.ts"):
        n += len(re.findall(r"^\s*(?:it|test)\(", p.read_text(encoding="utf-8"), re.M))
    return n


def contar_playwright() -> int:
    return sum(len(re.findall(r"^\s*test\(", p.read_text(encoding="utf-8"), re.M))
               for p in (RAIZ / "web" / "e2e").glob("*.spec.ts"))


def trace_check() -> dict:
    r = rodar([sys.executable, "tools/trace.py", "--check"])
    m = re.search(r"Objetos rastreados: (\d+) \| requisitos: (\d+) \| testes: (\d+) \((\d+) executados\) \| métricas: (\d+)",
                  r.stdout)
    if not m:
        raise SystemExit(f"saída inesperada de tools/trace.py --check:\n{r.stdout}\n{r.stderr}")
    erros = re.search(r"(\d+) erros", r.stdout)
    return {"objetos": int(m.group(1)), "requisitos": int(m.group(2)), "testes": int(m.group(3)),
            "executados": int(m.group(4)), "metricas": int(m.group(5)),
            "erros": int(erros.group(1)) if erros else (0 if r.returncode == 0 else -1), "codigo": r.returncode}


def cenarios_verificar() -> tuple[dict, str]:
    r = rodar([sys.executable, "-m", "fin_mas", "cenarios", "--verificar"])
    linhas = {}
    for linha in r.stdout.splitlines():
        partes = linha.split()
        if len(partes) >= 5 and partes[1] in ("basico", "local", "llm"):
            linhas[partes[0]] = {"cognicao": partes[1], "resposta": partes[2], "invariantes": partes[3],
                                 "repetivel": partes[4]}
    resumo = next((l for l in r.stdout.splitlines() if "cenário(s)" in l), "")
    return linhas, resumo


def cenarios_dsm3() -> set[str]:
    r = rodar(["git", "show", f"{TAG_DSM3}:src/fin_mas/env/scenarios.py"])
    return set(re.findall(r'^    Scenario\("([a-z0-9_]+)"', r.stdout, re.M)) if r.returncode == 0 else set()


def carregar_trace():
    spec = importlib.util.spec_from_file_location("trace_modelos", RAIZ / "tools" / "trace.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    data, index, _ = mod.load()
    for itens in data.values():
        for i in itens:
            index[i["id"]] = i
    _, back = mod.validate(data, index)
    return mod, data, index, back


# ---------------------------------------------------------------- experimento
class Experimento:
    def __init__(self):
        self.resumo = json.loads((RES / "resumo.json").read_text(encoding="utf-8"))
        self.manifesto = json.loads((RES / "manifesto.json").read_text(encoding="utf-8"))
        self.t = self.resumo["tabelas"]

    def teste(self, familia: str, comparacao: str, metrica: str) -> dict:
        achados = [x for x in self.resumo["testes"] if x["familia"] == familia and x["comparacao"] == comparacao
                   and x["metrica"] == metrica]
        if len(achados) != 1:
            raise KeyError(f"teste não encontrado: {familia} | {comparacao} | {metrica}")
        return achados[0]


def exploratorio_rq7() -> list[dict]:
    """Execução correta, SMA local x básico, bloco A (medida exploratória, sem correção de Holm)."""
    from fin_mas import estudo
    linhas = estudo.ler_csv(RES / "execucoes.csv")
    out = []
    for cond in ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "combinadas"):
        a = estudo.selecionar(linhas, bloco="A", braco="sma_local", condicao=cond)
        b = estudo.selecionar(linhas, bloco="A", braco="sma_basico", condicao=cond)
        r = estudo.comparar("exploratório", cond, "execucao_correta", a, b, "sma_local", "sma_basico")
        out.append({"condicao": cond, **r})
    return out


def decisoes_distribuidas() -> dict:
    """Fração das decisões tomadas fora do Orquestrador e decisões por fechamento, sem falhas (bloco A)."""
    from fin_mas import estudo
    linhas = estudo.ler_csv(RES / "execucoes.csv")
    out = {}
    for braco in ("sma_basico", "sma_local", "wf_equivalente"):
        sel = estudo.selecionar(linhas, bloco="A", braco=braco, condicao="nominal", intencao="fechar_mes")
        dist = [r["distribuicao_decisoria"] for r in sel if r.get("distribuicao_decisoria") is not None]
        dec = [r["decisoes"] for r in sel if r.get("decisoes") is not None]
        out[braco] = {"distribuicao": sum(dist) / len(dist) if dist else None,
                      "decisoes": sum(dec) / len(dec) if dec else None}
    return out


# ---------------------------------------------------------------- macros
class Macros:
    def __init__(self):
        self.v: dict[str, str] = {}
        self.tabelas: dict[str, str] = {}

    def __setitem__(self, chave, valor):
        if chave in self.v:
            raise KeyError(f"chave repetida: {chave}")
        self.v[chave] = str(valor)

    def tabela(self, nome, linhas):
        self.tabelas[nome] = "\n".join(linhas)

    def escrever(self, destino: Path, cabecalho: str):
        out = [f"% {cabecalho}", "% Gerado por tools/relatorio_numeros.py; não edite à mão.",
               "\\providecommand{\\V}[1]{\\ifcsname V@#1\\endcsname\\csname V@#1\\endcsname"
               "\\else\\textbf{??\\detokenize{#1}??}\\PackageWarning{numeros}{chave indefinida: #1}\\fi}"]
        for k in sorted(self.v):
            out.append(f"\\expandafter\\newcommand\\csname V@{k}\\endcsname{{{self.v[k]}}}")
        for nome in sorted(self.tabelas):
            out.append(f"\\newcommand{{\\{nome}}}{{%\n{self.tabelas[nome]}%\n}}")
        destino.write_text("\n".join(out) + "\n", encoding="utf-8")


def numeros_experimento(M: Macros, E: Experimento):
    man, t = E.manifesto, E.t
    M["exp.execucoes"] = inteiro(man["execucoes"])
    for b, n in man["execucoes_por_bloco"].items():
        M[f"exp.bloco.{b}"] = inteiro(n)
    M["exp.seeds"] = len(man["seeds"])
    M["exp.seed.min"], M["exp.seed.max"] = min(man["seeds"]), max(man["seeds"])
    M["exp.sha"] = man["arquivos"]["execucoes.csv"]["sha256"][:8]
    M["exp.sha.completo"] = man["arquivos"]["execucoes.csv"]["sha256"]
    M["exp.reamostragens"] = inteiro(man["estatistica"]["reamostragens_bootstrap"])
    M["exp.alfa"] = num(man["estatistica"]["alfa"], 2)
    M["exp.portes"] = len(man["portes"])
    M["exp.condicoes"] = len(man["condicoes"])
    M["exp.p_plantio"] = num(man["modelo_de_falhas"]["p_plantio"], 2)
    M["exp.plantios"] = len(man["modelo_de_falhas"]["plantios"])
    inv = t["invariantes"]
    M["exp.sma.execucoes"] = inteiro(inv["execucoes_do_sma"])
    M["exp.violacoes"] = inteiro(inv["execucoes_com_violacao"])
    M["exp.erros"] = inteiro(inv["execucoes_com_erro"])
    M["exp.ataques.tentados"] = inteiro(inv["ataques_tentados"])
    M["exp.ataques.aceitos"] = inteiro(inv["ataques_aceitos"])
    M["exp.ataques.sem_premissa"] = inteiro(inv["ataques_sem_premissa"])
    M["exp.ataques.indevidos"] = inteiro(inv["ataques_aceitos"] - inv["ataques_sem_premissa"])
    M["exp.sem_resposta"] = inteiro(sum(v["sem_resposta"] for v in inv["sem_resposta_por_condicao"].values()))
    idt = E.resumo["identidade"]
    M["rq1.pares"] = idt["sma_basico_x_wf_equivalente"]["pares"]
    M["rq1.pares.diferentes"] = idt["sma_basico_x_wf_equivalente"]["diferentes"]
    M["rq7.pares"] = idt["sma_local_x_sma_basico"]["pares"]
    M["rq7.pares.diferentes"] = idt["sma_local_x_sma_basico"]["diferentes"]

    # RQ1 — qualidade sem falhas
    linhas = []
    nomes = man["bracos"]
    for b in BRACOS:
        q = t["rq1_qualidade_nominal"][b]
        for met in ("classificacao_correta", "conformidade_correta", "dre_correta", "concluida", "sinalizacao_correta"):
            M[f"rq1.{b}.{met}"] = pct(q[met]["media"])
            M[f"rq1.{b}.{met}.ic"] = ic_pct(q[met]["ic95"])
        M[f"rq1.{b}.criticas"] = num(q["criticas_publicadas_sem_tratamento"]["media"], 2)
        M[f"rq1.{b}.criticas.ic"] = ic_num(q["criticas_publicadas_sem_tratamento"]["ic95"], 2)
        linhas.append(f"{tex(nomes[b])} & {pct(q['classificacao_correta']['media'])} {ic_pct(q['classificacao_correta']['ic95'])}"
                      f" & {pct(q['conformidade_correta']['media'])} & {pct(q['dre_correta']['media'])}"
                      f" & {num(q['criticas_publicadas_sem_tratamento']['media'], 2)} & {pct(q['concluida']['media'])} \\\\")
    M.tabela("TabRQum", linhas)
    x = E.teste("RQ1", "sma_basico x wf_minimo, nominal", "classificacao_correta")
    M["rq1.min.dif"], M["rq1.min.dif.ic"], M["rq1.min.p"] = pp(x["diferenca_media"]), ic_pp(x["ic95_diferenca"]), pval(x["p_holm"])
    M["rq1.min.cliff"] = num(x["cliff"], 2)
    x = E.teste("RQ1", "sma_basico x wf_minimo, nominal", "criticas_publicadas_sem_tratamento")
    M["rq1.min.criticas.cliff"] = num(-x["cliff"], 2) if x["cliff"] > 0 else num(x["cliff"], 2)

    # RQ2 — robustez
    linhas = []
    for c in CONDICOES:
        r = t["rq2_robustez"][c]
        for b in ("sma_basico", "sma_local", "wf_equivalente"):
            M[f"rq2.{c}.{b}"] = pct(r[b]["execucao_correta"]["media"])
            M[f"rq2.{c}.{b}.ic"] = ic_pct(r[b]["execucao_correta"]["ic95"])
            M[f"rq2.{c}.{b}.resposta"] = pct(r[b]["resposta_explicita"]["media"])
            M[f"rq2.{c}.{b}.criticas"] = num(r[b]["criticas_publicadas_sem_tratamento"]["media"], 0)
        x = E.teste("RQ2", f"sma_basico x wf_equivalente, {c}", "execucao_correta")
        M[f"rq2.{c}.dif"], M[f"rq2.{c}.dif.ic"] = pp(x["diferenca_media"]), ic_pp(x["ic95_diferenca"])
        M[f"rq2.{c}.p"] = pval(x["p_holm"])
        M[f"rq2.{c}.cliff"] = num(x["cliff"], 2)
        M[f"rq2.{c}.seeds"] = x["pares_diferentes"]
        dif = "idêntico em todos os pares" if x["pares_diferentes"] == 0 else f"{pp(x['diferenca_media'])} {ic_pp(x['ic95_diferenca'])}"
        linhas.append(f"{COND_ROTULO[c]} & {pct(r['sma_basico']['execucao_correta']['media'])} {ic_pct(r['sma_basico']['execucao_correta']['ic95'])}"
                      f" & {pct(r['sma_local']['execucao_correta']['media'])}"
                      f" & {pct(r['wf_equivalente']['execucao_correta']['media'])}"
                      f" & {dif} & {x['pares_diferentes']} & {pval(x['p_holm'])} \\\\")
    M.tabela("TabRQdois", linhas)
    for rot, comp in (("baixa_media", "sma_basico, perda_baixa x perda_media"), ("media_alta", "sma_basico, perda_media x perda_alta")):
        x = E.teste("RQ2", comp, "execucao_correta")
        M[f"rq2.ordem.{rot}.p"] = pval(x["p_holm"])

    # RQ3 — custo
    linhas = []
    for c in ("nominal", "perda_media", "combinadas"):
        r = t["rq3_custo"][c]
        for b in r:
            M[f"rq3.{c}.{b}.msg"] = num(r[b]["mensagens_coordenacao"]["media"], 2)
            M[f"rq3.{c}.{b}.lat"] = num(r[b]["latencia_ticks"]["media"], 1)
            if "decisoes" in r[b]:
                M[f"rq3.{c}.{b}.decisoes"] = num(r[b]["decisoes"]["media"], 1)
        linhas.append(f"{COND_ROTULO[c]} & {num(r['sma_basico']['mensagens_coordenacao']['media'], 2)}"
                      f" & {num(r['sma_local']['mensagens_coordenacao']['media'], 2)}"
                      f" & {num(r['wf_equivalente']['mensagens_coordenacao']['media'], 2)}"
                      f" & {num(r['sma_basico']['latencia_ticks']['media'], 1)}"
                      f" & {num(r['sma_local']['latencia_ticks']['media'], 1)}"
                      f" & {num(r['wf_equivalente']['latencia_ticks']['media'], 1)} \\\\")
    M.tabela("TabRQtres", linhas)
    for c in ("nominal", "combinadas"):
        for met, rot in (("mensagens_coordenacao", "msg"), ("latencia_ticks", "lat")):
            x = E.teste("RQ3", f"sma_basico x wf_equivalente, {c}", met)
            casas = 2 if rot == "msg" else 1
            M[f"rq3.{c}.{rot}.dif"] = num(x["diferenca_media"], casas)
            M[f"rq3.{c}.{rot}.dif.ic"] = ic_num(x["ic95_diferenca"], casas)
            M[f"rq3.{c}.{rot}.p"] = pval(x["p_holm"])
            M[f"rq3.{c}.{rot}.cliff"] = num(x["cliff"], 2)
    ac = t["rq3_acesso"]["nominal"]
    for lado in ("com_acesso", "sem_acesso"):
        M[f"rq3.acesso.{lado}.msg"] = num(ac[lado]["mensagens"]["media"], 2)
        M[f"rq3.acesso.{lado}.lat"] = num(ac[lado]["latencia_ticks"]["media"], 1)
        M[f"rq3.acesso.{lado}.trace"] = num(ac[lado]["registros_trace"]["media"], 1)
    for met in ("mensagens", "latencia_ticks", "registros_trace"):
        x = E.teste("RQ3", "controle de acesso ligado x desligado, nominal, porte médio", met)
        M[f"rq3.acesso.{met}.pares"] = x["pares_diferentes"]

    # RQ4 — recuperação
    linhas = []
    for c in ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "combinadas"):
        r = t["rq4_recuperacao"]["sma_basico"][c]
        frac = r["mesmo_resultado"] / r["atingidas"] if r["atingidas"] else None
        M[f"rq4.{c}.atingidas"] = r["atingidas"]
        M[f"rq4.{c}.execucoes"] = r["execucoes"]
        M[f"rq4.{c}.mesmo"] = r["mesmo_resultado"]
        M[f"rq4.{c}.mesmo.pct"] = pct(frac, 0) if frac is not None else "---"
        M[f"rq4.{c}.degradacao"] = r["degradacao_segura"]
        M[f"rq4.{c}.sem_resposta"] = r["sem_resposta"]
        M[f"rq4.{c}.mediana"] = num(r["recuperacao_ticks"]["mediana"], 0)
        linhas.append(f"{COND_ROTULO[c]} & {r['atingidas']} de {r['execucoes']} & {r['mesmo_resultado']} ({pct(frac, 0)})"
                      f" & {r['degradacao_segura']} & {r['sem_resposta']} & {num(r['recuperacao_ticks']['mediana'], 0)} \\\\")
    M.tabela("TabRQquatro", linhas)
    x = E.teste("RQ4", "sma_basico: perda de mensagens x indisponibilidade", "recuperacao_ticks")
    M["rq4.tipo.a"], M["rq4.tipo.b"] = num(x["media_a"], 1), num(x["media_b"], 1)
    M["rq4.tipo.p"], M["rq4.tipo.cliff"] = pval(x["p_holm"]), num(x["cliff"], 2)
    x = E.teste("RQ4", "sma_local x sma_basico, falhas de comunicação", "recuperacao_ticks")
    M["rq4.local.a"], M["rq4.local.b"] = num(x["media_a"], 1), num(x["media_b"], 1)
    M["rq4.local.p"], M["rq4.local.cliff"] = pval(x["p_holm"]), num(x["cliff"], 2)
    pb = t["rq2_robustez"]["perda_alta"]["sma_basico"]
    M["rq4.perda_alta.falhas"] = inteiro(round(pb["degradacao_segura"]["media"] * pb["degradacao_segura"]["execucoes"]))

    # RQ5 — porte e parâmetros
    for p in t["rq5_porte"]:
        for b in ("sma_basico", "wf_equivalente"):
            M[f"rq5.porte.{p}.{b}.classificacao"] = pct(t["rq5_porte"][p][b]["classificacao_correta"]["media"])
            M[f"rq5.porte.{p}.{b}.msg"] = num(t["rq5_porte"][p][b]["mensagens_coordenacao"]["media"], 1)
    x = E.teste("RQ5-porte", "sma_basico, nominal, micro x pequena", "classificacao_correta")
    M["rq5.porte.dif"], M["rq5.porte.dif.ic"], M["rq5.porte.p"] = pp(x["diferenca_media"]), ic_pp(x["ic95_diferenca"]), pval(x["p_holm"])
    linhas = []
    designada = {"max_tentativas": ("combinadas", "execucao_correta", "pct"),
                 "prazo_subtarefa": ("combinadas", "latencia_ticks", "num"),
                 "prazo_aprovacao": ("combinadas", "concluida", "pct"),
                 "ttl_reserva": ("combinadas", "concluida", "pct"),
                 "limiar_percentual": ("nominal", "classificacao_correta", "pct"),
                 "max_correcoes": ("nominal", "criticas_corrigidas", "num2")}
    padrao = man["parametros_padrao"]
    valores_padrao = {"max_tentativas": padrao["max_tentativas"], "prazo_subtarefa": padrao["prazo_subtarefa"],
                      "prazo_aprovacao": 20, "ttl_reserva": padrao["ttl_reserva"], "limiar_percentual": 10,
                      "max_correcoes": padrao["max_correcoes"]}
    rotulos = {"max_tentativas": "máximo de tentativas", "prazo_subtarefa": "prazo de subtarefa",
               "prazo_aprovacao": "prazo de aprovação", "ttl_reserva": "TTL da reserva",
               "limiar_percentual": "limiar de desvio (\\%)", "max_correcoes": "máximo de correções"}
    metrica_rot = {"execucao_correta": "execução correta", "latencia_ticks": "latência (ticks)",
                   "concluida": "publicação", "classificacao_correta": "classificação correta",
                   "criticas_corrigidas": "críticas corrigidas"}
    from fin_mas import estudo
    B = estudo.selecionar(estudo.ler_csv(RES / "execucoes.csv"), bloco="B", braco="sma_basico")
    filtro = {"prazo_aprovacao": {"intencao": "fechar_mes"}, "ttl_reserva": {"intencao": "fechar_mes"},
              "max_correcoes": {"intencao": "fechar_mes"}}  # como nos testes designados (src/fin_mas/estudo.py)
    variantes = sorted({r["variante"] for r in B})
    for par, (cond, met, fmt) in designada.items():
        niveis = [(float(v.split("=")[1]), v) for v in variantes if v.startswith(par + "=")]
        niveis = sorted(niveis + [(float(valores_padrao[par]), "padrao")])
        vals = []
        for nivel, variante in niveis:
            sel = estudo.selecionar(B, variante=variante, condicao=cond, **filtro.get(par, {}))
            seeds = estudo.por_seed(sel, met)
            d = sum(seeds.values()) / len(seeds)
            v = pct(d) if fmt == "pct" else num(d, 1) if fmt == "num" else num(d, 2)
            n_txt = inteiro(nivel)
            M[f"rq5.{par}.{n_txt}"] = v
            vals.append(f"\\textbf{{{n_txt}}}: {v}" if nivel == valores_padrao[par] else f"{n_txt}: {v}")
        alvo = " (fechamento)" if par in filtro else ""
        linhas.append(f"{rotulos[par]} & {COND_ROTULO[cond]} & {metrica_rot[met]}{alvo} & {'; '.join(vals)} \\\\")
    M.tabela("TabRQcinco", linhas)
    for comp, met, chave in (("sma_basico, combinadas, max_tentativas=1 x max_tentativas=3", "execucao_correta", "tentativas"),
                             ("sma_basico, combinadas, prazo_subtarefa=15 x prazo_subtarefa=60", "latencia_ticks", "prazo_subtarefa"),
                             ("sma_basico, combinadas, prazo_aprovacao=10 x prazo_aprovacao=40", "concluida", "prazo_aprovacao"),
                             ("sma_basico, nominal, limiar_percentual=20 x padrao", "classificacao_correta", "limiar20"),
                             ("sma_basico, nominal, limiar_percentual=5 x padrao", "classificacao_correta", "limiar5"),
                             ("sma_basico, combinadas, ttl_reserva=40 x padrao", "concluida", "ttl"),
                             ("sma_basico, nominal, max_correcoes=0 x padrao", "criticas_corrigidas", "correcoes")):
        x = E.teste("RQ5-parametros", comp, met)
        M[f"rq5.teste.{chave}.p"] = pval(x["p_holm"])
        M[f"rq5.teste.{chave}.p_bruto"] = pval(x["p"])
        M[f"rq5.teste.{chave}.seeds"] = x["pares_diferentes"]
    linhas = []

    # RQ6 — ataques sob falha
    a = t["rq6_ataques"]["bloco A: ataques ao Approval Gate"]
    d = t["rq6_ataques"]["bloco D: com ataques ao controle de acesso"]
    for rot, x in (("A", a), ("D", d)):
        for k in ("ataques_tentados", "ataques_aceitos", "aceitos_indevidos", "aceitos_sem_a_premissa_do_ataque",
                  "execucoes", "execucoes_atacadas", "criticas_publicadas_sem_tratamento"):
            M[f"rq6.{rot}.{k}"] = inteiro(x[k])
    for b in ("sma_basico", "sma_local"):
        x = t["rq6_ataques"][f"{b}: atacada x mesma execução sem ataque"]
        M[f"rq6.{b}.pares"], M[f"rq6.{b}.diferentes"] = x["pares"], x["diferentes"]

    # RQ7 — cognição local
    for c in ("nominal",) + CONDICOES:
        r = t["rq7_cognicao"][c]
        for b in ("sma_basico", "sma_local"):
            for met in ("classificacao_correta", "execucao_correta"):
                M[f"rq7.{c}.{b}.{met}"] = pct(r[b][met]["media"])
            M[f"rq7.{c}.{b}.msg"] = num(r[b]["mensagens_coordenacao"]["media"], 2)
            M[f"rq7.{c}.{b}.confirmadas"] = num(r[b]["hipoteses_confirmadas"]["media"], 2)
            M[f"rq7.{c}.{b}.refutadas"] = num(r[b]["hipoteses_refutadas"]["media"], 2)
    linhas = []
    for c in ("perda_baixa", "perda_media", "perda_alta", "combinadas"):
        x = E.teste("RQ7", f"sma_local x sma_basico, {c}", "classificacao_correta")
        r = t["rq7_cognicao"][c]
        M[f"rq7.{c}.p"], M[f"rq7.{c}.seeds"] = pval(x["p_holm"]), x["pares_diferentes"]
        linhas.append(f"{COND_ROTULO[c]} & {pct(r['sma_basico']['classificacao_correta']['media'])}"
                      f" & {pct(r['sma_local']['classificacao_correta']['media'])} & {x['pares_diferentes']}"
                      f" & {pval(x['p_holm'])} \\\\")
    sub = t["rq7_subgrupo_com_pista"]
    x = E.teste("RQ7", "sma_local x sma_basico, perda (3 níveis), desvio irregular com pista na planilha", "classificacao_correta")
    M["rq7.sub.basico"], M["rq7.sub.local"] = pct(sub["sma_basico"]["classificacao_correta"]["media"]), pct(sub["sma_local"]["classificacao_correta"]["media"])
    M["rq7.sub.n"], M["rq7.sub.seeds"] = sub["sma_local"]["classificacao_correta"]["n"], x["pares_diferentes"]
    linhas.append(f"subgrupo registrado (desvio irregular com pista, sob perda; {sub['sma_local']['classificacao_correta']['n']} seeds)"
                  f" & {M.v['rq7.sub.basico']} & {M.v['rq7.sub.local']} & {x['pares_diferentes']}"
                  f" & {pval(x['p_holm'])} \\\\")
    M.tabela("TabRQsete", linhas)
    x = E.teste("RQ7", "sma_local x sma_basico, perda_media", "mensagens_coordenacao")
    M["rq7.msg.dif"], M["rq7.msg.dif.ic"], M["rq7.msg.p"] = num(x["diferenca_media"], 2), ic_num(x["ic95_diferenca"], 2), pval(x["p_holm"])
    linhas = []
    for x in exploratorio_rq7():
        c = x["condicao"]
        M[f"rq7.expl.{c}.dif"], M[f"rq7.expl.{c}.ic"] = pp(x["diferenca_media"]), ic_pp(x["ic95_diferenca"])
        M[f"rq7.expl.{c}.seeds"], M[f"rq7.expl.{c}.p"] = x["pares_diferentes"], pval(x["p"])
        linhas.append(f"{COND_ROTULO[c]} & {pct(x['media_b'])} & {pct(x['media_a'])} & {pp(x['diferenca_media'])} {ic_pp(x['ic95_diferenca'])}"
                      f" & {x['pares_diferentes']} & {pval(x['p'])} \\\\")
    M.tabela("TabRQseteExpl", linhas)
    nom = t["rq3_custo"]["nominal"]
    M["rq7.nominal.decisoes.basico"] = num(nom["sma_basico"]["decisoes"]["media"], 1)
    M["rq7.nominal.decisoes.local"] = num(nom["sma_local"]["decisoes"]["media"], 1)

    # Ablação
    linhas = []
    abl = (("sem_reenvio", "sem_reenvio x completo, perda_media", "execucao_correta", "reenvio do Orquestrador",
            "execução correta, perda de 15\\%", "pct"),
           ("sem_reserva", "sem_reserva x completo, nominal, fechar_mes", "publicacoes_do_periodo", "reserva de período",
            "publicações do mesmo mês (certo: 1)", "num"),
           ("sem_correcao", "sem_correcao x completo, nominal, fechar_mes", "criticas_corrigidas", "veto com correção",
            "críticas corrigidas por fechamento", "num"),
           ("sem_negociacao", "sem_negociacao x completo, consulta_instavel, avaliar_orcamento", "classificacao_correta",
            "negociação de prazo", "classificação correta, consulta instável", "pct"),
           ("sem_cognicao_local", "sem_cognicao_local x completo, consulta_instavel", "classificacao_correta",
            "cognição local", "classificação correta, consulta instável", "pct"))
    for chave, comp, met, rot, medida, fmt in abl:
        x = E.teste("Ablação", comp, met)
        f = pct if fmt == "pct" else (lambda v: num(v, 2))
        dif = pp(x["diferenca_media"]) if fmt == "pct" else num(x["diferenca_media"], 2)
        M[f"abl.{chave}.com"], M[f"abl.{chave}.sem"] = f(x["media_b"]), f(x["media_a"])
        M[f"abl.{chave}.p"], M[f"abl.{chave}.seeds"] = pval(x["p_holm"]), x["pares_diferentes"]
        M[f"abl.{chave}.dif"] = dif
        linhas.append(f"{rot} & {medida} & {f(x['media_b'])} & {f(x['media_a'])} & {x['pares_diferentes']}"
                      f" & {pval(x['p_holm'])} \\\\")
    M.tabela("TabAblacao", linhas)
    c = t["ablacao"]["sem_correcao"]["nominal"]["fechar_mes"]["concluida"]["media"]
    M["abl.sem_correcao.publicacao"] = pct(c)

    # Comportamento coletivo: decisões fora do Orquestrador
    dd = decisoes_distribuidas()
    for b, v in dd.items():
        M[f"coletivo.{b}.distribuicao"] = pct(v["distribuicao"], 0)
        M[f"coletivo.{b}.decisoes"] = num(v["decisoes"], 1)

    # Holm: número de testes por família e total
    familias: dict[str, int] = {}
    for x in E.resumo["testes"]:
        familias[x["familia"]] = familias.get(x["familia"], 0) + 1
    M["exp.testes"] = len(E.resumo["testes"])
    M["exp.familias"] = len(familias)


def numeros_rodada1(M: Macros, E: Experimento):
    """Primeira rodada (antes da correção do barramento), lida do histórico do git, ao lado da segunda."""
    def git_json(caminho):
        r = rodar(["git", "show", f"{RODADA1}:{caminho}"])
        if r.returncode != 0:
            raise SystemExit(f"não consegui ler {caminho} no commit {RODADA1}: {r.stderr}")
        return json.loads(r.stdout)
    r1 = git_json("docs/dsm4/resultados/resumo.json")
    m1 = git_json("docs/dsm4/resultados/manifesto.json")
    M["r1.commit"], M["r2.commit"] = RODADA1, rodar(["git", "log", "-1", "--format=%h", "--", "docs/dsm4/resultados/execucoes.csv"]).stdout.strip()
    M["r1.sha"] = m1["arquivos"]["execucoes.csv"]["sha256"][:8]
    t1, t2 = r1["tabelas"], E.t
    linhas = []

    def linha(rotulo, f, extra="---"):
        linhas.append(f"{rotulo} & {f(t1)} & {f(t2)} & {extra} \\\\")
    linha("pares diferentes do workflow, sem falhas (RQ1)",
          lambda t: f"{(r1 if t is t1 else E.resumo)['identidade']['sma_basico_x_wf_equivalente']['diferentes']} de "
                    f"{(r1 if t is t1 else E.resumo)['identidade']['sma_basico_x_wf_equivalente']['pares']}")
    for c in ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "humano_lento", "combinadas"):
        linha(f"execução correta, {COND_ROTULO[c]}", lambda t, c=c: pct(t["rq2_robustez"][c]["sma_basico"]["execucao_correta"]["media"]),
              pct(t2["rq2_robustez"][c]["wf_equivalente"]["execucao_correta"]["media"]))
        M[f"r1.rq2.{c}"] = pct(t1["rq2_robustez"][c]["sma_basico"]["execucao_correta"]["media"])
        M[f"r1.rq2.{c}.resposta"] = pct(t1["rq2_robustez"][c]["sma_basico"]["resposta_explicita"]["media"])
    linha("resposta explícita, perda de 5\\% / 15\\% / 30\\%",
          lambda t: " / ".join(pct(t["rq2_robustez"][c]["sma_basico"]["resposta_explicita"]["media"])
                               for c in ("perda_baixa", "perda_media", "perda_alta")), "100\\%")
    linha("execuções do SMA com invariante violado",
          lambda t: f"{inteiro(t['invariantes']['execucoes_com_violacao'])} de {inteiro(t['invariantes']['execucoes_do_sma'])}"
                    + (" (" + ", ".join(t["invariantes"]["execucoes_por_invariante"]) + ")" if t["invariantes"]["execucoes_por_invariante"] else ""),
          "não se aplica")
    linha("mensagens de coordenação, sem falhas", lambda t: num(t["rq3_custo"]["nominal"]["sma_basico"]["mensagens_coordenacao"]["media"], 2),
          num(t2["rq3_custo"]["nominal"]["wf_equivalente"]["mensagens_coordenacao"]["media"], 2))
    linha("latência sem falhas (ticks)", lambda t: num(t["rq3_custo"]["nominal"]["sma_basico"]["latencia_ticks"]["media"], 1),
          num(t2["rq3_custo"]["nominal"]["wf_equivalente"]["latencia_ticks"]["media"], 1))
    lat1 = t1["rq3_custo"]["combinadas"]["sma_basico"]["latencia_ticks"]
    linhas.append(f"latência, combinadas (ticks) & {num(lat1['media'], 1)} (só as {lat1['n']} seeds com resposta)"
                  f" & {num(t2['rq3_custo']['combinadas']['sma_basico']['latencia_ticks']['media'], 1)}"
                  f" & {num(t2['rq3_custo']['combinadas']['wf_equivalente']['latencia_ticks']['media'], 1)} \\\\")
    M["r1.lat.combinadas"], M["r1.lat.combinadas.n"] = num(lat1["media"], 1), lat1["n"]
    linha("críticas publicadas sem tratamento (SMA)", lambda t: inteiro(sum(
        t["rq2_robustez"][c][b]["criticas_publicadas_sem_tratamento"]["media"] for c in t["rq2_robustez"]
        for b in ("sma_basico", "sma_local"))), "0")
    linha("ataques aceitos indevidamente",
          lambda t: f"0 de {inteiro(t['invariantes']['ataques_tentados'])}" if t["invariantes"]["ataques_aceitos"]
          == t["invariantes"]["ataques_sem_premissa"] else "ver CSV", "não atacado")
    def abl(r):
        x = [y for y in r["testes"] if y["familia"] == "Ablação" and y["comparacao"].startswith("sem_reenvio")][0]
        return f"{pct(x['media_b'])} $\\times$ {pct(x['media_a'])} (p ajustado {pval(x['p_holm'])})"
    linhas.append(f"ablação do reenvio, perda de 15\\% (com $\\times$ sem) & {abl(r1)} & {abl(E.resumo)} & --- \\\\")
    M.tabela("TabDuasRodadas", linhas)
    inv1 = t1["invariantes"]
    M["r1.violacoes"], M["r1.inv03"] = inteiro(inv1["execucoes_com_violacao"]), inteiro(inv1["avisos_de_prazo_sem_transicao"])
    M["r1.ataques"] = inteiro(inv1["ataques_tentados"])
    for c in ("perda_baixa", "perda_media", "perda_alta", "indisponibilidade", "combinadas"):
        M[f"r1.rq4.{c}.sem_resposta"] = t1["rq4_recuperacao"]["sma_basico"][c]["sem_resposta"]
        r = t1["rq4_recuperacao"]["sma_basico"][c]
        M[f"r1.rq4.{c}.mesmo.pct"] = pct(r["mesmo_resultado"] / r["atingidas"], 0)
    x = [y for y in r1["testes"] if y["familia"] == "Ablação" and y["comparacao"].startswith("sem_reenvio")][0]
    M["r1.abl.reenvio.com"], M["r1.abl.reenvio.sem"] = pct(x["media_b"]), pct(x["media_a"])
    M["r1.rq6.atacadas"] = t1["rq6_ataques"]["bloco A: ataques ao Approval Gate"]["execucoes_atacadas"]


def numeros_sistema(M: Macros, suite: bool):
    import yaml
    por_pasta = coleta_pytest()
    for pasta, n in por_pasta.items():
        M[f"testes.{pasta}"] = n
    M["testes.total"] = inteiro(sum(por_pasta.values()))
    M["testes.playwright"] = contar_playwright()
    v = suite_vitest()  # um segundo; sem bun, conta no código
    M["testes.vitest"] = v["passaram"] if v and v["codigo"] == 0 else contar_vitest()
    if suite:
        s = suite_pytest()
        M["testes.passaram"] = inteiro(s["passed"])
        M["testes.falharam"] = inteiro(s["failed"] + s["error"] + s["errors"])
        M["testes.minutos"] = num((s["segundos"] or 0) / 60, 1)
        M["testes.vitest.passaram"] = v["passaram"] if v else "não executado"
        M["testes.suite"] = "executada"
    else:
        M["testes.passaram"] = "não executada nesta geração"
        M["testes.falharam"] = "---"
        M["testes.minutos"] = "---"
        M["testes.vitest.passaram"] = "não executado"
        M["testes.suite"] = "não executada nesta geração (use --suite)"
    tr = trace_check()
    for k, v in tr.items():
        M[f"trace.{k}"] = v
    verif, resumo = cenarios_verificar()
    from fin_mas.env.scenarios import CENARIOS
    antigos = cenarios_dsm3()
    M["cenarios.total"] = len(CENARIOS)
    M["cenarios.verificados"] = sum(1 for v in verif.values() if v["invariantes"] == "ok" and v["repetivel"] == "sim")
    M["cenarios.dsm3"] = len(antigos & set(CENARIOS))
    M["cenarios.dsm4"] = len(set(CENARIOS) - antigos)
    for nivel in ("basico", "local", "llm"):
        M[f"cenarios.{nivel}"] = sum(1 for c in CENARIOS.values() if c.cognicao == nivel)
    invs = re.findall(r"INV-\d{2}", (RAIZ / "src" / "fin_mas" / "invariantes.py").read_text(encoding="utf-8"))
    M["invariantes"] = len(set(invs))
    pyproj = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    M["versao"] = re.search(r'^version = "([^"]+)"', pyproj, re.M).group(1)
    for nome in ("agents", "protocols", "norms", "services", "roles", "components", "metrics"):
        itens = yaml.safe_load((RAIZ / "models" / f"{nome}.yaml").read_text(encoding="utf-8"))["items"]
        M[f"modelos.{nome}"] = len(itens)
    for chave, cenario in (("barramento", "ataque_decisao_forjada"), ("acesso", "ataque_acesso"),
                           ("acesso_avancado", "ataque_acesso_avancado")):
        if cenario not in CENARIOS:  # lote ainda não integrado nesta branch
            M[f"ataques.{chave}"], M[f"ataques.{chave}.rejeitados"] = "---", "---"
            continue
        saida = rodar([sys.executable, "-m", "fin_mas", "run", "--scenario", cenario]).stdout
        m = re.search(r"ATAQUES (\d+) de (\d+) (?:rejeitados|recusados)", saida)
        M[f"ataques.{chave}"], M[f"ataques.{chave}.rejeitados"] = (m.group(2), m.group(1)) if m else ("?", "?")
    return verif, resumo, antigos


# ---------------------------------------------------------------- grafos de rastreabilidade


def grafos(mod, data, index, back) -> tuple[str, int]:
    grupos: dict[str, list[dict]] = {}
    for r in data["requirements"]:
        grupos.setdefault(r["tipo"], []).append(r)
    juntos: dict[str, list[dict]] = {}
    for tipo, reqs in grupos.items():
        juntos.setdefault(tipo if len(reqs) >= mod.GRAPH_MIN_GROUP else "Demais requisitos", []).extend(reqs)
    out, n = [], 0
    for tipo, reqs in juntos.items():
        for i in range(0, len(reqs), mod.GRAPH_CHUNK):
            parte = reqs[i:i + mod.GRAPH_CHUNK]
            n += 1
            span = parte[0]["id"] if len(parte) == 1 else f"{parte[0]['id']} a {parte[-1]['id']}"
            linhas = ["\\begin{figure}[H]\\centering",
                      "\\begin{tikzpicture}[font=\\sffamily\\scriptsize, >={Stealth[length=1.6mm]},",
                      " caixa/.style={draw=black!45, rounded corners=1.5pt, align=left, inner sep=2.5pt, anchor=north west}]"]
            y = 0.0
            colunas = ((0.0, 3.7, "req"), (4.0, 3.2, "papel"), (7.5, 4.0, "prot"), (11.8, 1.8, "teste"), (13.9, 3.6, "met"))
            cab = ("Requisito", "Papéis", "Protocolos e normas", "Testes", "Métricas")
            for (x, w, _), c in zip(colunas, cab):
                linhas.append(f"\\node[anchor=south west, inner sep=0pt, font=\\sffamily\\scriptsize\\bfseries] at ({x},0.15) {{{c}}};")
            for r in parte:
                ch = mod.chain_for(r, index, back)
                textos = (f"\\textbf{{{r['id']}}} ({r['entrega']})\\\\{tex(r['titulo'])}",
                          ", ".join(ch["papeis"]) or "---",
                          ", ".join(ch["protocolos"] + ch["normas"]) or "---",
                          f"{len(ch['testes'])} teste(s)",
                          ", ".join(ch["metricas"]) or "---")
                crus = (r["id"] + " " + r["titulo"], *textos[1:])
                nomes, alt = [], 1
                for (x, w, cor), txt, cru in zip(colunas, textos, crus):
                    nome = f"c{len(nomes)}r{len(linhas)}"
                    nomes.append(nome)
                    por_linha = max(8, int((w - 0.3) / 0.135))
                    alt = max(alt, -(-len(cru) // por_linha) + (1 if cor == "req" else 0))
                    linhas.append(f"\\node[caixa, fill=tr{cor}, text width={w - 0.25:.2f}cm] ({nome}) at ({x},{-y:.2f}) {{{txt}}};")
                for a, b in zip(nomes, nomes[1:]):
                    linhas.append(f"\\draw[->, black!55] ([yshift=-0.22cm]{a}.north east) -- ([yshift=-0.22cm]{a}.north east -| {b}.west);")
                y += 0.34 * alt + 0.32
            linhas += ["\\end{tikzpicture}",
                       f"\\caption{{Rastreabilidade, {tex(tipo).lower() if tipo != 'Demais requisitos' else 'demais requisitos'}: "
                       f"{span}. Cadeia requisito $\\rightarrow$ papéis $\\rightarrow$ protocolos e normas $\\rightarrow$ "
                       f"testes $\\rightarrow$ métricas, lida de \\texttt{{models/*.yaml}}.}}",
                       f"\\label{{fig:trace{n}}}", "\\end{figure}"]
            out.append("\n".join(linhas))
    return "\n\n".join(out), n


# ---------------------------------------------------------------- catálogo de cenários (Sphinx)
def catalogo(verif: dict, resumo_verif: str, antigos: set[str], data: dict) -> str:
    from fin_mas.env.scenarios import CENARIOS
    novos = [c for c in CENARIOS.values() if c.nome not in antigos]
    codigo = {p: p.read_text(encoding="utf-8") for p in sorted((RAIZ / "tests").rglob("test_*.py"))}
    traces = RAIZ / "web" / "public" / "traces"
    out = ["# Catálogo de cenários de teste da DSM4", "",
           "Página **gerada** por `python tools/relatorio_numeros.py` a partir de `CENARIOS`",
           "(`src/fin_mas/env/scenarios.py`), da conferência `python -m fin_mas cenarios --verificar` e dos testes",
           f"modelados com `entrega: DSM4` em `models/tests.yaml`. O catálogo da DSM3 ({len(antigos)} cenários) continua em",
           "{doc}`../dsm3/cenarios-de-teste`; aqui ficam só os cenários que não existiam na tag",
           f"`{TAG_DSM3}`. Não edite à mão: rode o gerador de novo.", "",
           f"Conferência no momento da geração: **{resumo_verif.strip() or 'não executada'}**.", "",
           "## Terminal", "", "```bash",
           "python -m fin_mas cenarios --verificar --filtro <nome>   # resposta, invariantes e repetibilidade",
           "python -m fin_mas run --scenario <nome>                  # trilha causal legível",
           "python -m fin_mas run --scenario <nome> --trace t.jsonl && python -m fin_mas invariantes t.jsonl",
           "```", "",
           "| Cenário | Cognição | Porte | Segmento | Resposta | Invariantes | Repetível | O que observar |",
           "|---|---|---|---|---|---|---|---|"]
    for c in novos:
        v = verif.get(c.nome, {})
        out.append(f"| `{c.nome}` | `{c.cognicao}` | {c.porte} | {c.segmento} | `{v.get('resposta', '?')}` | "
                   f"{v.get('invariantes', '?')} | {v.get('repetivel', '?')} | {(c.esperado or c.descricao).replace('|', '/')} |")
    out += ["", "## Dashboard", "",
            "Qualquer cenário do catálogo roda ao vivo no escritório e, se o trace foi exportado",
            "(`python -m fin_mas export --out web/public/traces`), também no replay offline.", "",
            "```bash",
            "python -m fin_mas serve --demo --scenario <nome>        # ao vivo: http://127.0.0.1:8765 (avaliador / Demonstracao-SMA-2026)",
            "./iniciar.sh replay                                     # replay dos traces exportados: http://127.0.0.1:4173",
            "```", "",
            "| Cenário | Ao vivo | Replay (trace exportado) | Onde olhar |", "|---|---|---|---|"]
    for c in novos:
        tem = (traces / f"{c.nome}.json").exists()
        onde = ("mente do agente (crenças, desejos, deliberações)" if c.cognicao != "basico"
                else "aba Porte e o relatório publicado" if c.porte != "media" or c.segmento != "software_servicos"
                else "feed de eventos")
        out.append(f"| `{c.nome}` | `serve --demo --scenario {c.nome}` | {'sim' if tem else 'não (rode `fin-mas export`)'} | {onde} |")
    out += ["", "## Testes que exercitam cada cenário", "",
            "Arquivos de `tests/` que citam o nome do cenário.", "",
            "| Cenário | Arquivos de teste |", "|---|---|"]
    for c in novos:
        arqs = sorted({p.relative_to(RAIZ).as_posix() for p, txt in codigo.items() if f'"{c.nome}"' in txt})
        out.append(f"| `{c.nome}` | {', '.join(f'`{a}`' for a in arqs) or '— (só `cenarios --verificar`)'} |")
    out += ["", "## Testes modelados da DSM4", "",
            "Testes com `entrega: DSM4` em `models/tests.yaml` (o `tools/trace.py --check` confere que cada função",
            "existe); o título é o campo `esperado` do modelo.", "",
            "| Teste | Função | Arquivo | Tipo | O que verifica |", "|---|---|---|---|---|"]
    for t in data["tests"]:
        if t.get("entrega") != "DSM4":
            continue
        arq = next((p.relative_to(RAIZ).as_posix() for p, txt in codigo.items() if f"def {t['nome']}(" in txt), "—")
        if arq == "—":
            web = [p for p in (RAIZ / "web" / "e2e").glob("*.spec.ts") if t["nome"] in p.read_text(encoding="utf-8")]
            arq = web[0].relative_to(RAIZ).as_posix() if web else "—"
        out.append(f"| {t['id']} | `{t['nome']}` | `{arq}` | {t.get('tipo', '')} | {str(t.get('esperado', '')).replace('|', '/')} |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--suite", action="store_true", help="roda também a suíte pytest e o vitest (cerca de 4 min)")
    args = ap.parse_args()
    DOC.mkdir(parents=True, exist_ok=True)
    M = Macros()
    E = Experimento()
    numeros_experimento(M, E)
    numeros_rodada1(M, E)
    verif, resumo_verif, antigos = numeros_sistema(M, args.suite)
    commit = rodar(["git", "rev-parse", "--short", "HEAD"]).stdout.strip() or "?"
    M["gerado.commit"] = commit
    M["gerado.data"] = dt.date.today().strftime("%d/%m/%Y")
    mod, data, index, back = carregar_trace()
    corpo, n = grafos(mod, data, index, back)
    M["trace.grafos"] = n
    M.escrever(DOC / "numeros.tex", f"commit {commit}, {M.v['gerado.data']}")
    (DOC / "rastreabilidade.tex").write_text("% Gerado por tools/relatorio_numeros.py; não edite à mão.\n" + corpo + "\n",
                                             encoding="utf-8")
    CATALOGO.write_text(catalogo(verif, resumo_verif, antigos, data), encoding="utf-8")
    print(f"numeros.tex: {len(M.v)} valores e {len(M.tabelas)} tabelas; rastreabilidade.tex: {n} grafos; "
          f"{CATALOGO.relative_to(RAIZ)}: {M.v['cenarios.dsm4']} cenários novos; suíte: {M.v['testes.suite']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

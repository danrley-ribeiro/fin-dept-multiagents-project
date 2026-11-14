"""Base de conhecimento normativo com proveniência (CP8, DSM4).

Corpus versionado em `models/conhecimento.yaml`: trechos curtos, em paráfrase, das normas que o
projeto já cita. `buscar(consulta, k)` faz recuperação lexical offline (BM25, só biblioteca
padrão) e devolve, para cada trecho, o documento, o identificador do trecho, o texto, a versão
e a referência para conferência no texto oficial.

Ausência de evidência não é preenchida. Um trecho só conta como evidência se cobrir pelo menos
`COBERTURA_MINIMA` do peso informativo da consulta (a soma dos IDF dos termos da consulta que
aparecem no trecho, sobre a soma dos IDF de todos os termos da consulta). Termo que não existe
no corpus pesa o máximo: uma pergunta sobre um assunto que o corpus não trata tem cobertura
baixa em qualquer trecho, e a busca devolve lista vazia. Quem chama declara "sem evidência".

A busca é determinística: mesma consulta, mesmo corpus, mesma resposta, na mesma ordem
(empate decidido pelo identificador do trecho).
"""
import math
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir

K1, B = 1.5, 0.75  # parâmetros usuais do BM25 (Okapi)
COBERTURA_MINIMA = 0.5
PALAVRA = re.compile(r"[a-z0-9]+")
VAZIAS = frozenset("""a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre entre ate
e ou que se como quando onde quem qual quais nao nem mas mais menos muito ja ser sao foi era esta este esse essa isso
isto aquele aquela seu sua seus suas lhe ele ela eles elas ao aos pela pelo pelas pelos ha tem ter deve devem pode
podem cada todo toda todos todas mesmo mesma duas dois vezes desse dessa deste desta disso nesse nessa neste nesta
tambem so apenas""".split())


@dataclass(frozen=True)
class Trecho:
    documento: str
    titulo: str
    trecho: str
    texto: str
    versao: str
    referencia: str
    termos: tuple


def termos(texto: str) -> list[str]:
    """Minúsculas, sem acento, sem palavras vazias; plural reduzido de forma grosseira (ções→ção, s final)."""
    plano = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    saida = []
    for p in PALAVRA.findall(plano):
        if p in VAZIAS or (len(p) < 3 and not p.isdigit()):
            continue
        if p.endswith("coes"):
            p = p[:-4] + "cao"
        elif p.endswith("oes"):
            p = p[:-3] + "ao"
        elif p.endswith("s") and len(p) > 4:
            p = p[:-1]
        saida.append(p)
    return saida


class BaseNormativa:
    def __init__(self, dados: dict):
        self.versao = dados["versao"]
        self.trechos = [Trecho(d["id"], d["titulo"], t["id"], " ".join(t["texto"].split()),
                               f"{self.versao}; {d['versao']}", d["referencia"], tuple(termos(t["texto"])))
                        for d in dados["documentos"] for t in d["trechos"]]
        self.n = len(self.trechos)
        self.media = sum(len(t.termos) for t in self.trechos) / self.n
        self.df: dict[str, int] = {}
        for t in self.trechos:
            for termo in set(t.termos):
                self.df[termo] = self.df.get(termo, 0) + 1

    def idf(self, termo: str) -> float:
        n = self.df.get(termo, 0)
        return math.log(1 + (self.n - n + 0.5) / (n + 0.5))

    def buscar(self, consulta: str, k: int = 3) -> list[dict]:
        """Até `k` trechos que sustentam a consulta, do mais ao menos relevante; lista vazia = sem evidência."""
        q = list(dict.fromkeys(termos(consulta)))  # termos distintos, na ordem da consulta
        peso_total = sum(self.idf(t) for t in q)
        if not q or peso_total <= 0:
            return []
        achados = []
        for t in self.trechos:
            presentes = [x for x in q if x in t.termos]
            if not presentes:
                continue
            cobertura = sum(self.idf(x) for x in presentes) / peso_total
            if cobertura < COBERTURA_MINIMA:
                continue
            pontuacao = 0.0
            for x in presentes:
                f = t.termos.count(x)
                pontuacao += self.idf(x) * f * (K1 + 1) / (f + K1 * (1 - B + B * len(t.termos) / self.media))
            achados.append((round(pontuacao, 4), round(cobertura, 2), t))
        achados.sort(key=lambda a: (-a[0], a[2].trecho))
        return [{"documento": t.documento, "titulo": t.titulo, "trecho": t.trecho, "texto": t.texto,
                 "versao": t.versao, "referencia": t.referencia, "pontuacao": p, "cobertura": c}
                for p, c, t in achados[:max(0, k)]]


@lru_cache(maxsize=None)
def base() -> BaseNormativa:
    return BaseNormativa(yaml.safe_load((models_dir() / "conhecimento.yaml").read_text(encoding="utf-8")))


def versao() -> str:
    return base().versao


def buscar(consulta: str, k: int = 3) -> list[dict]:
    return base().buscar(consulta, k)

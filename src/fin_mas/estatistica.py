"""Estatística do experimento da DSM4, só com a biblioteca padrão.

Descrição (média, desvio padrão amostral, mediana, IC de 95% por bootstrap percentil com semente
fixa), testes não paramétricos (Wilcoxon de postos sinalizados para pares, Mann-Whitney U para
grupos independentes), tamanho de efeito (delta de Cliff) e correção de Holm para comparações
múltiplas. Não há suposição de normalidade em nenhum ponto: as métricas do experimento são
proporções por seed e contagens, com muitos empates.

Os dois testes usam a distribuição **exata** de permutação quando a amostra é pequena (com
empates, sobre os postos médios observados) e a aproximação normal, com correção de empates e de
continuidade, acima disso. `autoteste()` roda exemplos pequenos, cujos resultados foram
calculados à mão; o experimento grava a saída em `resumo.json` e o teste de integração confere.
"""
import math
import random
from statistics import mean, median, stdev

SEMENTE_BOOTSTRAP = 20261202
REAMOSTRAGENS = 2000
N_EXATO_WILCOXON = 25  # até aqui, distribuição exata dos postos sinalizados
N_EXATO_MANN_WHITNEY = 30  # n1 + n2 até aqui e sem empates: distribuição exata de U


def media(xs) -> float:
    return mean(xs)


def desvio(xs) -> float:
    """Desvio padrão amostral (n - 1); zero com menos de dois valores."""
    return stdev(xs) if len(xs) > 1 else 0.0


def mediana(xs) -> float:
    return median(xs)


def ic_bootstrap(xs, estatistica=mean, reamostragens=REAMOSTRAGENS, semente=SEMENTE_BOOTSTRAP,
                 confianca=0.95) -> tuple[float, float]:
    """Intervalo de confiança por bootstrap percentil: reamostra com reposição e lê os percentis."""
    xs = list(xs)
    if not xs:
        raise ValueError("amostra vazia")
    if min(xs) == max(xs):
        return float(xs[0]), float(xs[0])
    rng = random.Random(semente)
    n = len(xs)
    valores = sorted(estatistica(rng.choices(xs, k=n)) for _ in range(reamostragens))
    alfa = 1 - confianca
    inferior = valores[max(0, math.floor(alfa / 2 * reamostragens))]
    superior = valores[min(reamostragens - 1, math.ceil((1 - alfa / 2) * reamostragens) - 1)]
    return float(inferior), float(superior)


def postos(valores) -> tuple[list[float], list[int]]:
    """Postos médios (empates dividem o posto) e o tamanho de cada grupo de empate."""
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    r, grupos, i = [0.0] * len(valores), [], 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and valores[ordem[j + 1]] == valores[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            r[ordem[k]] = (i + j) / 2 + 1
        grupos.append(j - i + 1)
        i = j + 1
    return r, grupos


def _fi(z: float) -> float:
    """Função de distribuição da normal padrão."""
    return 0.5 * math.erfc(-z / math.sqrt(2))


def _p_bilateral_normal(distancia: float, dp: float) -> tuple[float, float]:
    """z com correção de continuidade (0,5) e p bilateral."""
    if dp == 0:
        return 0.0, 1.0
    z = max(distancia - 0.5, 0.0) / dp
    return z, min(1.0, 2 * (1 - _fi(z)))


def wilcoxon_pareado(x, y, metodo: str = "auto") -> dict:
    """Wilcoxon de postos sinalizados, bilateral, sobre as diferenças x - y.

    Diferenças nulas são descartadas. `metodo`: `exato` (permutação dos sinais sobre os postos
    observados), `normal` (com correção de empates e de continuidade) ou `auto` (exato até
    `N_EXATO_WILCOXON` pares não nulos). Sem nenhuma diferença não nula o teste não se aplica: p = 1.
    """
    if len(x) != len(y):
        raise ValueError("amostras pareadas precisam ter o mesmo tamanho")
    d = [a - b for a, b in zip(x, y) if a != b]
    n = len(d)
    if n == 0:
        return {"n": len(x), "n_efetivo": 0, "w_mais": 0.0, "w_menos": 0.0, "z": None, "p": 1.0, "metodo": "sem diferenças"}
    r, grupos = postos([abs(v) for v in d])
    w_mais = sum(ri for ri, v in zip(r, d) if v > 0)
    total = n * (n + 1) / 2
    w_menos = total - w_mais
    usar = metodo if metodo != "auto" else ("exato" if n <= N_EXATO_WILCOXON else "normal")
    if usar == "exato":
        pesos = [round(2 * ri) for ri in r]  # postos médios dobrados: inteiros
        contagem = {0: 1}
        for w in pesos:
            novo = dict(contagem)
            for s, c in contagem.items():
                novo[s + w] = novo.get(s + w, 0) + c
            contagem = novo
        centro, obs = sum(pesos) / 2, abs(2 * w_mais - sum(pesos) / 2)
        extremos = sum(c for s, c in contagem.items() if abs(s - centro) >= obs - 1e-9)
        return {"n": len(x), "n_efetivo": n, "w_mais": w_mais, "w_menos": w_menos, "z": None,
                "p": min(1.0, extremos / 2 ** n), "metodo": "exato"}
    variancia = n * (n + 1) * (2 * n + 1) / 24 - sum(t ** 3 - t for t in grupos) / 48
    z, p = _p_bilateral_normal(abs(w_mais - total / 2), math.sqrt(variancia))
    return {"n": len(x), "n_efetivo": n, "w_mais": w_mais, "w_menos": w_menos, "z": z, "p": p, "metodo": "normal"}


def mann_whitney(x, y, metodo: str = "auto") -> dict:
    """Mann-Whitney U, bilateral, para dois grupos independentes.

    `u1` conta os pares em que x supera y (empate vale meio). Exato quando não há empates e
    n1 + n2 <= `N_EXATO_MANN_WHITNEY`; senão, aproximação normal com correção de empates e de continuidade.
    """
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        raise ValueError("os dois grupos precisam ter observações")
    r, grupos = postos(list(x) + list(y))
    u1 = sum(r[:n1]) - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1
    n = n1 + n2
    sem_empates = all(t == 1 for t in grupos)
    usar = metodo if metodo != "auto" else ("exato" if sem_empates and n <= N_EXATO_MANN_WHITNEY else "normal")
    if usar == "exato":
        if not sem_empates:
            raise ValueError("o método exato de Mann-Whitney exige amostras sem empates")
        # modos[k][s]: maneiras de escolher k postos de 1..n com soma s
        modos = [{0: 1}] + [{} for _ in range(n1)]
        for posto in range(1, n + 1):
            for k in range(min(posto, n1), 0, -1):
                for s, c in modos[k - 1].items():
                    modos[k][s + posto] = modos[k].get(s + posto, 0) + c
        base, centro = n1 * (n1 + 1) / 2, n1 * n2 / 2
        obs = abs(u1 - centro)
        extremos = sum(c for s, c in modos[n1].items() if abs((s - base) - centro) >= obs - 1e-9)
        return {"n1": n1, "n2": n2, "u1": u1, "u2": u2, "z": None, "p": min(1.0, extremos / math.comb(n, n1)),
                "metodo": "exato"}
    variancia = n1 * n2 / 12 * ((n + 1) - sum(t ** 3 - t for t in grupos) / (n * (n - 1)))
    z, p = _p_bilateral_normal(abs(u1 - n1 * n2 / 2), math.sqrt(max(variancia, 0.0)))
    return {"n1": n1, "n2": n2, "u1": u1, "u2": u2, "z": z, "p": p, "metodo": "normal"}


def cliff(x, y) -> float:
    """Delta de Cliff: P(x > y) - P(x < y), entre -1 e 1."""
    if not x or not y:
        raise ValueError("os dois grupos precisam ter observações")
    maior = sum(1 for a in x for b in y if a > b)
    menor = sum(1 for a in x for b in y if a < b)
    return (maior - menor) / (len(x) * len(y))


def magnitude(delta: float) -> str:
    """Faixas de Romano et al. (2006) para o delta de Cliff."""
    d = abs(delta)
    return "desprezível" if d < 0.147 else "pequeno" if d < 0.33 else "médio" if d < 0.474 else "grande"


def holm(ps) -> list[float]:
    """p ajustados pelo método de Holm (descendente), na ordem em que vieram."""
    m = len(ps)
    ordem = sorted(range(m), key=lambda i: ps[i])
    ajustados, anterior = [0.0] * m, 0.0
    for posicao, i in enumerate(ordem):
        anterior = max(anterior, min(1.0, (m - posicao) * ps[i]))
        ajustados[i] = anterior
    return ajustados


def descrever(xs, semente=SEMENTE_BOOTSTRAP) -> dict:
    """Resumo de uma amostra: n, média, desvio, mediana e IC de 95% da média por bootstrap."""
    xs = list(xs)
    if not xs:
        return {"n": 0, "media": None, "desvio": None, "mediana": None, "ic95": None}
    inferior, superior = ic_bootstrap(xs, semente=semente)
    return {"n": len(xs), "media": round(media(xs), 4), "desvio": round(desvio(xs), 4),
            "mediana": round(mediana(xs), 4), "ic95": [round(inferior, 4), round(superior, 4)]}


def autoteste() -> dict:
    """Exemplos pequenos, de resultado conhecido (ver `tests/integration/test_experimento.py`)."""
    amostra = [2, 4, 4, 4, 5, 5, 7, 9]
    sem_empates = [8, -3, 5, 12, -1, 7, 10, 2]  # diferenças pareadas: W- = 1 + 3 = 4
    com_empates = [1, 1, 2, -2, 3, 3, -1, 4, 5, 5]  # W- = 2 + 4,5 = 6,5
    x, y = [19, 22, 16, 29, 24], [20, 11, 17, 12]  # U de x = 17, U de y = 3
    zeros = [0] * len(sem_empates)
    w = wilcoxon_pareado(sem_empates, zeros)
    wn = wilcoxon_pareado(com_empates, [0] * len(com_empates), metodo="normal")
    u = mann_whitney(x, y)
    un = mann_whitney(x, y, metodo="normal")
    ic1, ic2 = ic_bootstrap(amostra), ic_bootstrap(amostra)
    return {
        "media": media(amostra), "desvio": round(desvio(amostra), 6), "mediana": mediana(amostra),
        "wilcoxon_exato": {"w_menos": w["w_menos"], "w_mais": w["w_mais"], "p": w["p"], "metodo": w["metodo"]},
        "wilcoxon_normal": {"w_menos": wn["w_menos"], "w_mais": wn["w_mais"], "z": round(wn["z"], 4),
                            "p": round(wn["p"], 4)},
        "wilcoxon_sem_diferencas": wilcoxon_pareado([3, 3, 3], [3, 3, 3])["p"],
        "mann_whitney_exato": {"u1": u["u1"], "u2": u["u2"], "p": round(u["p"], 6), "metodo": u["metodo"]},
        "mann_whitney_normal": {"z": round(un["z"], 4), "p": round(un["p"], 4)},
        "cliff": cliff(x, y), "cliff_magnitude": magnitude(cliff(x, y)),
        "holm": [round(p, 6) for p in holm([0.01, 0.04, 0.03, 0.005])],
        "bootstrap": {"reprodutivel": ic1 == ic2, "contem_a_media": ic1[0] <= media(amostra) <= ic1[1],
                      "amostra_constante": list(ic_bootstrap([7, 7, 7])), "ic95": [round(v, 4) for v in ic1]},
    }

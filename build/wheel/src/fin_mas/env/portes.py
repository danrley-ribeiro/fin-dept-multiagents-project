"""Perfis de porte lidos de models/portes.yaml (base normativa).

DSM4: aos quatro portes da DSM2/DSM3 (micro, pequena, média, grande) somam-se o MEI, antes da
micro, e a Média empresa II do BNDES (`media_ii`), subdivisão de cima da média. A ordem de
`PORTES` vai do menor ao maior; os quatro de antes não mudaram de valor.
"""
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir

PORTES = ("mei", "micro", "pequena", "media", "media_ii", "grande")
PORTE_PADRAO = "media"


@lru_cache(maxsize=None)
def _base() -> dict:
    return yaml.safe_load((models_dir() / "portes.yaml").read_text(encoding="utf-8"))


def versao_normas() -> str:
    return _base()["versao"]


def perfil(porte: str = PORTE_PADRAO) -> dict:
    """Cópia do perfil do porte, com o nome e a versão das normas."""
    if porte not in PORTES:
        raise ValueError(f"porte desconhecido: {porte} (use {', '.join(PORTES)})")
    p = _base()["portes"][porte]
    return {**{k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in p.items()},
            "porte": porte, "versao": versao_normas()}


def limite(p: dict, cargo: str) -> float:
    """Alçada do cargo; sem limite (null) vira infinito."""
    valor = p["limites_alcada"][cargo]
    return float("inf") if valor is None else valor


def classe_legal(porte: str) -> str:
    """Porte da classificação legal: a subdivisão `media_ii` pertence à classe `media`."""
    return _base()["portes"][porte].get("subdivide", porte)


def porte_por_receita(receita_anual_centavos: int, mei: bool = False) -> str:
    """Classificação pelo faturamento anual (LC 123/2006 e BNDES).

    O MEI é um enquadramento por opção (SIMEI, LC 123/2006, art. 18-A), não só uma faixa de receita:
    sem `mei=True`, uma receita abaixo do teto do MEI é microempresa. Dentro da classe legal, a
    subdivisão que cobre a receita (Média Empresa II do BNDES) tem precedência sobre a classe.
    """
    base = _base()["portes"]
    for nome in PORTES:
        p = base[nome]
        if "subdivide" in p or (p.get("exige_opcao") and not mei):
            continue
        teto = p["receita_bruta_anual_max"]
        if teto is None or receita_anual_centavos <= teto:
            for sub in PORTES:
                s = base[sub]
                if s.get("subdivide") == nome and s["receita_bruta_anual_min"] < receita_anual_centavos <= s[
                        "receita_bruta_anual_max"]:
                    return sub
            return nome
    return "grande"

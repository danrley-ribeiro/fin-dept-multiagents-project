"""Perfis de porte (micro, pequena, média, grande) lidos de models/portes.yaml (base normativa)."""
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir

PORTES = ("micro", "pequena", "media", "grande")
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


def porte_por_receita(receita_anual_centavos: int) -> str:
    """Classificação legal pelo faturamento anual (LC 123/2006 e BNDES)."""
    for nome in PORTES:
        teto = _base()["portes"][nome]["receita_bruta_anual_max"]
        if teto is None or receita_anual_centavos <= teto:
            return nome
    return "grande"

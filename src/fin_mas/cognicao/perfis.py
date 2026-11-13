"""Perfil cognitivo por porte, lido de models/cognicao.yaml (ADR-010).

Pesos dos desejos permanentes de AG-RES, AG-CUS e AG-REL, público do relatório, estratégia de
compromisso por agente e limiares da cognição. Porte que o arquivo não conhece (ex.: um porte
novo criado depois) recebe o bloco `padrao`, de modo que acrescentar um porte não quebra os agentes.
"""
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir

COMPROMISSOS = ("cego", "obstinado", "aberto")


@lru_cache(maxsize=None)
def _base() -> dict:
    return yaml.safe_load((models_dir() / "cognicao.yaml").read_text(encoding="utf-8"))


def versao() -> str:
    return _base()["versao"]


def limiares() -> dict:
    return dict(_base()["limiares"])


def perfil_cognitivo(porte: str) -> dict:
    """Cópia do perfil do porte (ou do padrão), com a versão e os limiares."""
    base = _base()
    p = {**base["padrao"], **(base["portes"].get(porte) or {})}
    return {**{k: (dict(v) if isinstance(v, dict) else v) for k, v in p.items()},
            "porte": porte, "versao": base["versao"], "limiares": dict(base["limiares"])}


def compromisso_de(porte: str, agente: str) -> str:
    return perfil_cognitivo(porte)["compromisso"].get(agente, "aberto")

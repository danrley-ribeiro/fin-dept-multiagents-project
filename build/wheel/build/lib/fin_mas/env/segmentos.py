"""Eixo segmento (DSM4): comércio, serviços e indústria, além do padrão (software e serviços).

Lido de models/segmentos.yaml. O segmento muda plano de contas, estrutura de custos, unidades de
negócio, centros de custo e o direcionador de rateio dos custos fixos (conhecimento do AG-CUS). O
porte (env/portes.py) continua dando a escala e as regras. O segmento padrão reproduz a SMA de
sempre: com ele, o Dataset gera exatamente os mesmos dados da DSM3.
"""
import copy
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir


@lru_cache(maxsize=None)
def _base() -> dict:
    return yaml.safe_load((models_dir() / "segmentos.yaml").read_text(encoding="utf-8"))


SEGMENTO_PADRAO = "software_servicos"
SEGMENTOS = ("software_servicos", "comercio", "servicos", "industria")


def versao_segmentos() -> str:
    return _base()["versao"]


def percentuais(base: dict) -> dict:
    """Direcionador (quantidades por unidade) em percentuais inteiros que somam 100; o resto vai à última."""
    total = sum(base.values())
    pct = {u: q * 100 // total for u, q in base.items()}
    ultima = list(base)[-1]
    pct[ultima] += 100 - sum(pct.values())
    return pct


def segmento(nome: str = SEGMENTO_PADRAO) -> dict:
    """Cópia do perfil do segmento, com o rateio já em percentuais (`rateio_pct`)."""
    if nome not in SEGMENTOS:
        raise ValueError(f"segmento desconhecido: {nome} (use {', '.join(SEGMENTOS)})")
    s = copy.deepcopy(_base()["segmentos"][nome])
    s["segmento"] = nome
    s["versao"] = versao_segmentos()
    s["rateio_pct"] = percentuais(s["rateio"]["base"])
    return s


def ficha(nome: str) -> dict:
    """Resumo para a aba "Porte" do dashboard e para o assistente de instalação."""
    s = segmento(nome)
    return {"segmento": nome, "titulo": s["titulo"], "descricao": s["descricao"],
            "natureza_dos_custos": s["natureza_dos_custos"], "unidades": s["unidades"],
            "centros_custo": s["centros_custo"], "contas": s["contas"] + [s["conta_chamariz"]],
            "produtos": {p["id"]: p["nome"] for p in s["produtos"]},
            "composicao_custo_variavel": s["composicao_custo_variavel"],
            "rateio": {**s["rateio"], "percentuais": s["rateio_pct"]}, "padrao": nome == SEGMENTO_PADRAO}

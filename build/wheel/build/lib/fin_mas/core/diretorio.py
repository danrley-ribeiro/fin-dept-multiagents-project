"""Diretório de identidades: agente -> papéis declarados nos modelos (DSM3).

O barramento só registra um agente cujo papel exista em `models/roles.yaml` ou
`models/services.yaml`; se o identificador estiver em `models/agents.yaml`, o papel
declarado precisa ser um dos papéis do agente ali. Humanos simulados (SOL, APR) têm o
papel fixado aqui. É a raiz de confiança do barramento em processo; numa implantação
distribuída esse papel caberia a certificados (mTLS) ou assinaturas.
"""
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir

HUMANOS = {"SOL": frozenset({"ROLE-SOL"}), "APR": frozenset({"ROLE-APR"})}


@lru_cache(maxsize=1)
def carregar_diretorio() -> dict[str, frozenset]:
    itens = yaml.safe_load((models_dir() / "agents.yaml").read_text(encoding="utf-8"))["items"]
    diretorio = {a["id"]: frozenset(a.get("papeis", [])) for a in itens}
    diretorio.update(HUMANOS)
    return diretorio


@lru_cache(maxsize=1)
def papeis_validos() -> frozenset:
    ids = set()
    for arquivo in ("roles.yaml", "services.yaml"):
        ids |= {i["id"] for i in yaml.safe_load((models_dir() / arquivo).read_text(encoding="utf-8"))["items"]}
    return frozenset(ids)

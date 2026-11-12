"""Papéis e permissões da plataforma, lidos dos modelos (ADR-009): `roles.yaml` e `permissions.yaml`."""
from functools import lru_cache

import yaml

from fin_mas.core.fsm import models_dir


@lru_cache(maxsize=1)
def _base() -> dict:
    perm = yaml.safe_load((models_dir() / "permissions.yaml").read_text(encoding="utf-8"))
    papeis = yaml.safe_load((models_dir() / "roles.yaml").read_text(encoding="utf-8"))["items"]
    conhecidas = {p["id"] for p in perm["items"]}
    por_papel = {}
    for papel in papeis:
        if "permissoes" not in papel:
            continue  # papel de agente: não é atribuído a contas
        estranhas = set(papel["permissoes"]) - conhecidas
        if estranhas:
            raise ValueError(f"{papel['id']}: permissões fora de permissions.yaml: {sorted(estranhas)}")
        por_papel[papel["id"]] = {"titulo": papel["titulo"], "permissoes": frozenset(papel["permissoes"])}
    return {"permissoes": {p["id"]: p for p in perm["items"]}, "papeis": por_papel,
            "decisoes_por_cargo": {c: tuple(d) for c, d in perm["decisoes_por_cargo"].items()},
            "incompativeis": [frozenset(par) for par in perm["incompativeis"]]}


def papeis_humanos() -> dict:
    """Papéis que uma conta pode receber: id -> {titulo, permissoes}."""
    return _base()["papeis"]


def catalogo() -> dict:
    return _base()["permissoes"]


def permissoes_de(papeis) -> frozenset:
    base = _base()["papeis"]
    return frozenset().union(*(base[p]["permissoes"] for p in papeis if p in base))


def decisoes_do_cargo(cargo: str | None) -> tuple:
    return _base()["decisoes_por_cargo"].get(cargo or "", ())


def cargos() -> tuple:
    return tuple(_base()["decisoes_por_cargo"])


def incompatibilidade(papeis) -> frozenset | None:
    """Par de papéis que a mesma conta não pode acumular (IAM-06), ou None."""
    conjunto = set(papeis)
    return next((par for par in _base()["incompativeis"] if par <= conjunto), None)

"""Onde estão os modelos YAML e o dashboard construído (DSM4, implantação).

Instalado por `pip`/`pipx` a partir do wheel (`make wheel`), o pacote leva os dados dentro de
si, em `fin_mas/_dados/` (lidos com `importlib.resources`): `models/*.yaml` (a base normativa,
os protocolos e os portes) e `web/` (o build do dashboard). Em modo desenvolvimento (checkout
do repositório, `PYTHONPATH=src`), `_dados/` não existe e os mesmos arquivos são lidos da raiz
do checkout: `models/` e `web/dist/`. Os dados do pacote têm precedência.

`_dados/` nunca é versionado: `tools/empacotar_wheel.py` monta uma cópia do código num
diretório de build, copia ali os YAML e o build do dashboard e gera o wheel.
"""
from importlib import resources
from pathlib import Path

CHECKOUT = Path(__file__).resolve().parents[2]  # raiz do repositório quando rodando do checkout


def _embutido(*partes: str) -> Path | None:
    try:
        alvo = resources.files("fin_mas").joinpath("_dados", *partes)
    except (ModuleNotFoundError, TypeError):
        return None
    caminho = Path(str(alvo))
    return caminho if caminho.is_dir() else None


def models_dir() -> Path:
    """Pasta dos modelos YAML: a do pacote instalado ou, no checkout, `models/` na raiz."""
    return _embutido("models") or CHECKOUT / "models"


def web_dist() -> Path:
    """Build do dashboard: o do pacote instalado ou, no checkout, `web/dist/`."""
    return _embutido("web") or CHECKOUT / "web" / "dist"


def origem() -> str:
    """'pacote' quando os dados vêm do wheel instalado; 'checkout' no modo desenvolvimento."""
    return "pacote" if _embutido("models") else "checkout"

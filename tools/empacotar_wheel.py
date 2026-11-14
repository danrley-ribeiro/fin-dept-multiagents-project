#!/usr/bin/env python3
"""Gera o wheel instalável do fin-mas com os modelos YAML e o dashboard embutidos (DSM4).

    python tools/empacotar_wheel.py [--saida dist] [--sem-dashboard]
    make wheel                       # constrói o dashboard (bun) e chama este script

O repositório não guarda cópias: o código de `src/` é copiado para um diretório de build
(`build/wheel/`), e só ali `models/*.yaml` e `web/dist/` entram como dados do pacote
(`fin_mas/_dados/models` e `fin_mas/_dados/web`, lidos por `fin_mas/recursos.py`). O wheel sai
em `dist/` e funciona fora do checkout: `pipx install dist/fin_mas-*.whl` ou
`pip install dist/fin_mas-*.whl`. Usa só a biblioteca padrão e o `pip` do Python que o chama
(o setuptools do build vem do isolamento de build do pip).
"""
import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "build" / "wheel"


def montar(com_dashboard: bool) -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "src").mkdir(parents=True)
    for arquivo in ("pyproject.toml", "README.md"):
        shutil.copy2(RAIZ / arquivo, BUILD / arquivo)
    shutil.copytree(RAIZ / "src" / "fin_mas", BUILD / "src" / "fin_mas",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_dados"))
    dados = BUILD / "src" / "fin_mas" / "_dados"
    (dados / "models").mkdir(parents=True)
    for yaml in sorted((RAIZ / "models").glob("*.yaml")):
        shutil.copy2(yaml, dados / "models" / yaml.name)
    if com_dashboard:
        dist = RAIZ / "web" / "dist"
        if not (dist / "index.html").exists():
            raise SystemExit("web/dist não existe: rode `make web` (ou `cd web && bun install && bun run build`)")
        shutil.copytree(dist, dados / "web")
    return BUILD


def gerar(saida: Path, com_dashboard: bool = True) -> Path:
    base = montar(com_dashboard)
    saida.mkdir(parents=True, exist_ok=True)
    antes = set(saida.glob("fin_mas-*.whl"))
    for velho in antes:  # um wheel por versão: o novo substitui o antigo
        velho.unlink()
    subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--quiet", "-w", str(saida), str(base)],
                   check=True)
    wheel = next(iter(sorted(saida.glob("fin_mas-*.whl"))))
    with zipfile.ZipFile(wheel) as z:
        nomes = set(z.namelist())
    exigidos = ["fin_mas/_dados/models/portes.yaml", "fin_mas/_dados/models/segmentos.yaml",
                "fin_mas/_dados/models/protocols.yaml"] + (["fin_mas/_dados/web/index.html"] if com_dashboard else [])
    faltando = [n for n in exigidos if n not in nomes]
    if faltando:
        raise SystemExit(f"wheel incompleto, faltam: {', '.join(faltando)}")
    return wheel


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--saida", default=str(RAIZ / "dist"))
    parser.add_argument("--sem-dashboard", action="store_true", help="não exige nem embute web/dist")
    args = parser.parse_args()
    wheel = gerar(Path(args.saida), not args.sem_dashboard)
    with zipfile.ZipFile(wheel) as z:
        dados = [n for n in z.namelist() if "/_dados/" in n]
    print(f"{wheel} ({wheel.stat().st_size // 1024} KiB; {len(dados)} arquivo(s) de dados embutidos)")
    print(f"instale fora do repositório com: pipx install {wheel}   (ou pip install {wheel})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

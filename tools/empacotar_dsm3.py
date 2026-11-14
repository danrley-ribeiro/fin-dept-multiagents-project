"""Monta o pacote de entrega da DSM3 (entregas/dsm3/DSM3-entrega.zip).

Estrutura do zip:
    DSM3-entrega/
      README.md, USO_DE_IA.md       da pasta entregas/dsm3/
      diagramas/, modelos-editaveis/ (a apresentação fica fora do pacote)
      codigo/                        código-fonte executável, testes, modelos e documentação

Só entram arquivos versionados ou não ignorados pelo git (sem .venv, node_modules, dist, saidas).
Uso: python tools/empacotar_dsm3.py
"""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTREGA = RAIZ / "entregas" / "dsm3"
DESTINO = ENTREGA / "DSM3-entrega.zip"
PREFIXO = "DSM3-entrega"

# Itens da raiz do repositório copiados para codigo/
CODIGO = (
    "src/", "tests/", "web/", "models/", "tools/", "assets/", "docs/",
    "pyproject.toml", "requirements-dev.txt", "requirements-lock.txt", ".env.example",
    "iniciar.ps1", "iniciar.sh", "Makefile", "README.md", "CHANGELOG.md", ".gitattributes", ".gitignore",
)
# O projeto usa bun: web/bun.lock entra (versões exatas do dashboard); o package-lock.json do npm fica fora.
EXCLUIR = ("web/package-lock.json",)


def arquivos_git() -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=RAIZ, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    return sorted(p for p in saida.split("\0") if p and (RAIZ / p).is_file())


def main() -> int:
    arquivos = arquivos_git()
    entrada: list[tuple[str, str]] = []
    for rel in arquivos:
        if rel.startswith("entregas/dsm3/"):
            if not rel.endswith(".zip") and not rel.startswith("entregas/dsm3/apresentacao/"):
                entrada.append((rel, rel.removeprefix("entregas/dsm3/")))
        elif rel.startswith(CODIGO) and rel not in EXCLUIR:
            entrada.append((rel, "codigo/" + rel))

    DESTINO.unlink(missing_ok=True)
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        for origem, alvo in entrada:
            z.write(RAIZ / origem, f"{PREFIXO}/{alvo}")

    codigo = sum(1 for _, a in entrada if a.startswith("codigo/"))
    print(f"{DESTINO.relative_to(RAIZ)}: {len(entrada)} arquivos "
          f"({len(entrada) - codigo} da entrega, {codigo} em codigo/), "
          f"{DESTINO.stat().st_size / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Monta o pacote de entrega da DSM3 (entregas/dsm3/DSM3-entrega.zip).

Estrutura do zip:
    DSM3-entrega/
      README.md, USO_DE_IA.md       da pasta entregas/dsm3/
      diagramas/, modelos-editaveis/ (a apresentação fica fora do pacote)
      codigo/                        código-fonte executável, testes, modelos e documentação

Só entram arquivos versionados ou não ignorados pelo git (sem .venv, node_modules, dist, saidas).

No repositório, o README.md e o USO_DE_IA.md da entrega apontam para `../../docs/...` (caminho a
partir de entregas/dsm3/). No zip eles ficam em DSM3-entrega/ e o resto do projeto em codigo/:
as cópias que entram no zip têm os links reescritos para `codigo/...`, para abrirem no pacote
descompactado. Os arquivos do repositório não mudam (no GitHub os links continuam valendo).
Uso: python tools/empacotar_dsm3.py
"""
from __future__ import annotations

import re
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
    "enunciados/DSM3.txt",  # o README da entrega aponta para o enunciado
)
# O projeto usa bun: web/bun.lock entra (versões exatas do dashboard); o package-lock.json do npm fica fora.
EXCLUIR = ("web/package-lock.json",)
# Markdown da entrega cujos links relativos à raiz do repositório são reescritos para dentro do zip
REESCREVER = ("README.md", "USO_DE_IA.md")
LINK_RAIZ = re.compile(r"\]\(\.\./\.\./")


def links_para_o_zip(texto: str) -> str:
    """`[x](../../docs/a.md)` -> `[x](codigo/docs/a.md)`: no zip, o projeto fica em codigo/."""
    return LINK_RAIZ.sub("](codigo/", texto)


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
            if alvo in REESCREVER:
                texto = (RAIZ / origem).read_text(encoding="utf-8")
                z.writestr(f"{PREFIXO}/{alvo}", links_para_o_zip(texto).encode("utf-8"))
            else:
                z.write(RAIZ / origem, f"{PREFIXO}/{alvo}")

    codigo = sum(1 for _, a in entrada if a.startswith("codigo/"))
    destino = DESTINO.relative_to(RAIZ) if DESTINO.is_relative_to(RAIZ) else DESTINO
    print(f"{destino}: {len(entrada)} arquivos "
          f"({len(entrada) - codigo} da entrega, {codigo} em codigo/), "
          f"{DESTINO.stat().st_size / 1024:.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

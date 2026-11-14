"""Monta o pacote da entrega final (entregas/dsm4/DSM4-entrega.zip).

Estrutura do zip:
    DSM4-entrega/
      README.md, USO_DE_IA.md        da pasta entregas/dsm4/
      documentacao/                  relatório técnico (PDF e fontes LaTeX, números gerados, figuras)
      diagramas/, modelos-editaveis/ PNG e fontes Mermaid
      apresentacao/                  slides.md, roteiro.md, DSM4-apresentacao.pptx (e o tema)
      codigo/                        código-fonte, configurações, testes, modelos, documentação e resultados

Só entram arquivos versionados ou não ignorados pelo git (sem .venv, node_modules, dist, build, saidas), e
nunca a apostila da disciplina nem zips de entregas anteriores.
Uso: python tools/empacotar_dsm4.py [--destino ARQUIVO.zip] [--listar]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTREGA = RAIZ / "entregas" / "dsm4"
DESTINO = ENTREGA / "DSM4-entrega.zip"
PREFIXO = "DSM4-entrega"

# Itens da raiz do repositório copiados para codigo/
CODIGO = (
    "src/", "tests/", "web/", "models/", "tools/", "assets/", "docs/", "docker/",
    "Dockerfile", "compose.yaml", ".dockerignore",
    "pyproject.toml", "requirements-dev.txt", "requirements-lock.txt", ".env.example",
    "iniciar.ps1", "iniciar.sh", "Makefile", "README.md", "CHANGELOG.md", ".gitattributes", ".gitignore",
)
# O projeto usa bun: web/bun.lock entra; o package-lock.json do npm fica fora.
EXCLUIR = ("web/package-lock.json",)
NUNCA = ("node_modules/", ".venv/", "/dist/", "/build/", "docs/_build/", "Sistemas Multiagentes Inteligentes",
         "SistemasMultiAGentes_")


def arquivos_git() -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=RAIZ, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    return sorted(p for p in saida.split("\0") if p and (RAIZ / p).is_file())


def entradas() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for rel in arquivos_git():
        if rel.endswith(".zip") or any(n in "/" + rel for n in NUNCA):
            continue
        if rel.startswith("entregas/dsm4/"):
            out.append((rel, rel.removeprefix("entregas/dsm4/")))
        elif rel.startswith(CODIGO) and rel not in EXCLUIR:
            out.append((rel, "codigo/" + rel))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="pacote da entrega final da DSM4")
    ap.add_argument("--destino", type=Path, default=DESTINO, help="arquivo .zip (padrão: entregas/dsm4/DSM4-entrega.zip)")
    ap.add_argument("--listar", action="store_true", help="só lista o que entraria, sem gravar o zip")
    args = ap.parse_args()
    lista = entradas()
    obrigatorios = ("README.md", "USO_DE_IA.md", "documentacao/relatorio.pdf", "documentacao/relatorio.tex",
                    "apresentacao/slides.md", "apresentacao/roteiro.md", "codigo/docs/dsm4/resultados/execucoes.csv",
                    "codigo/Dockerfile", "codigo/compose.yaml", "codigo/pyproject.toml")
    faltam = [o for o in obrigatorios if o not in {a for _, a in lista}]
    if faltam:
        print("faltam no pacote: " + ", ".join(faltam), file=sys.stderr)
        return 1
    if args.listar:
        for _, alvo in lista:
            print(f"{PREFIXO}/{alvo}")
    else:
        args.destino.unlink(missing_ok=True)
        with zipfile.ZipFile(args.destino, "w", zipfile.ZIP_DEFLATED) as z:
            for origem, alvo in lista:
                z.write(RAIZ / origem, f"{PREFIXO}/{alvo}")
    codigo = sum(1 for _, a in lista if a.startswith("codigo/"))
    tamanho = "" if args.listar else f", {args.destino.stat().st_size / 1024:.0f} KiB"
    nome = "(lista)" if args.listar else args.destino
    print(f"{nome}: {len(lista)} arquivos ({len(lista) - codigo} da entrega, {codigo} em codigo/){tamanho}",
          file=sys.stderr if args.listar else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

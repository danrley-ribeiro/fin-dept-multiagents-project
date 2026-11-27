"""Monta o pacote da entrega final (entregas/dsm4/DSM4-entrega.zip).

Estrutura do zip:
    DSM4-entrega/
      README.md, USO_DE_IA.md        da pasta entregas/dsm4/
      documentacao/                  relatório técnico (PDF e fontes LaTeX, números gerados, figuras)
      diagramas/, modelos-editaveis/ PNG e fontes Mermaid
      apresentacao/                  slides.md, roteiro.md, DSM4-apresentacao.pptx (e o tema)
      codigo/                        código-fonte, configurações, testes, modelos, documentação e resultados

Só entram arquivos versionados ou não ignorados pelo git (sem .venv, node_modules, dist, build, saidas), e
nunca a apostila da disciplina nem zips de entregas anteriores. A exceção é a build do dashboard (`web/dist/`):
entra pronta em `codigo/web/dist/`, para `serve --demo` abrir o dashboard sem bun nem Node na máquina de quem
avalia. Ela precisa ser mais nova que todas as fontes da interface; se não for, o pacote não é gerado.
Uso: python tools/empacotar_dsm4.py [--destino ARQUIVO.zip] [--listar]
"""
from __future__ import annotations

import argparse
import os
import posixpath
import re
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
    "enunciados/DSM4.txt",
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
        elif any(rel.startswith(p) if p.endswith("/") else rel == p for p in CODIGO) and rel not in EXCLUIR:
            out.append((rel, "codigo/" + rel))
    return out


# fontes que a build do dashboard (vite) compila ou copia para web/dist
FONTES_WEB = ("web/src/", "web/public/", "web/index.html", "web/vite.config.ts", "web/package.json", "web/tsconfig")


def dashboard() -> tuple[list[tuple[str, str]], str | None]:
    """Arquivos de web/dist para codigo/web/dist e, se a build faltar ou estiver velha, o motivo."""
    dist = RAIZ / "web" / "dist"
    if not (dist / "index.html").is_file():
        return [], "web/dist não existe: rode `bun install && bun run build` em web/ antes de empacotar"
    fontes = [p for p in arquivos_git() if p.startswith(FONTES_WEB)]
    mais_nova = max((os.path.getmtime(RAIZ / p) for p in fontes), default=0)
    if (dist / "index.html").stat().st_mtime < mais_nova:
        return [], "web/dist é mais velho que as fontes da interface: rode `bun run build` em web/ antes de empacotar"
    return [(a.relative_to(RAIZ).as_posix(), "codigo/" + a.relative_to(RAIZ).as_posix())
            for a in sorted(dist.rglob("*")) if a.is_file()], None


def links_do_pacote(origem: str, alvo: str, conteudo: str) -> str:
    """A entrega sobe para a raiz do ZIP; a árvore de código desce para codigo/."""
    def converter(m):
        caminho, ancora = m.groups()
        if ":" in caminho or caminho.startswith("/"):
            return m[0]
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(origem), caminho))
        if rel == "enunciados":
            rel = "enunciados/DSM4.txt"
        if rel.startswith("entregas/dsm4/"):
            destino = rel.removeprefix("entregas/dsm4/")
        elif rel.startswith("entregas/"):
            return "](" + "https://github.com/danrley-ribeiro/fin-dept-multiagents-project/blob/main/" + rel + ancora + ")"
        elif not rel.startswith("../"):
            destino = "codigo/" + rel
        else:
            return m[0]
        return "](" + posixpath.relpath(destino, posixpath.dirname(alvo) or ".") + ancora + ")"
    return re.sub(r"\]\(([^ )#]+)(#[^)]*|)\)", converter, conteudo)


def main() -> int:
    ap = argparse.ArgumentParser(description="pacote da entrega final da DSM4")
    ap.add_argument("--destino", type=Path, default=DESTINO, help="arquivo .zip (padrão: entregas/dsm4/DSM4-entrega.zip)")
    ap.add_argument("--listar", action="store_true", help="só lista o que entraria, sem gravar o zip")
    args = ap.parse_args()
    lista = entradas()
    construido, motivo = dashboard()
    if motivo:
        print(motivo, file=sys.stderr)
        return 1
    lista += construido
    obrigatorios = ("README.md", "USO_DE_IA.md", "documentacao/relatorio.pdf", "documentacao/relatorio.tex",
                    "apresentacao/slides.md", "apresentacao/roteiro.md", "codigo/docs/dsm4/resultados/execucoes.csv",
                    "codigo/Dockerfile", "codigo/compose.yaml", "codigo/pyproject.toml",
                    "apresentacao/DSM4-apresentacao.pptx", "codigo/docs/dsm4/resultados/carga.csv",
                    "codigo/docs/dsm4/resultados/bloco_e/execucoes.csv", "codigo/docs/dsm4/resultados/bloco_e/resumo.md",
                    "codigo/src/fin_mas/estudo_e.py")
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
                nome = f"{PREFIXO}/{alvo}"
                if alvo.endswith(".md"):
                    conteudo = (RAIZ / origem).read_text(encoding="utf-8")
                    z.writestr(nome, links_do_pacote(origem, alvo, conteudo))
                else:
                    z.write(RAIZ / origem, nome)
    codigo = sum(1 for _, a in lista if a.startswith("codigo/"))
    tamanho = "" if args.listar else f", {args.destino.stat().st_size / 1024:.0f} KiB"
    nome = "(lista)" if args.listar else args.destino
    print(f"{nome}: {len(lista)} arquivos ({len(lista) - codigo} da entrega, {codigo} em codigo/){tamanho}",
          file=sys.stderr if args.listar else sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

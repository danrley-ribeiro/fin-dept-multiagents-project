"""Pacote da entrega final: todo link relativo dos Markdown abre dentro do ZIP.

O empacotador reescreve os links dos `.md` (a entrega sobe para a raiz do ZIP e o projeto desce para codigo/).
Este teste monta o pacote numa pasta temporária e confere cada link. O empacotador lista os arquivos pelo Git:
sem `.git` (a suíte rodada de dentro do próprio ZIP, como na correção da DSM3) o teste é pulado, não falha.
"""
import importlib.util
import posixpath
import re
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
CERCA = re.compile(r"```.*?```", re.S)  # links dentro de blocos de código não são links


def _carregar_empacotador():
    spec = importlib.util.spec_from_file_location("empacotar_dsm4", RAIZ / "tools" / "empacotar_dsm4.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _empacotador():
    if not (RAIZ / ".git").exists() or shutil.which("git") is None:
        pytest.skip("sem repositório Git: o empacotador lista os arquivos versionados (no ZIP extraído, os links são "
                    "conferidos por test_links_open_inside_the_extracted_package)")
    return _carregar_empacotador()


def test_every_relative_link_in_the_package_opens_inside_the_zip(tmp_path, monkeypatch, capsys):
    empacotar = _empacotador()
    monkeypatch.setattr(empacotar, "dashboard", lambda: ([], None))  # a build da interface não tem links .md
    destino = tmp_path / "DSM4-entrega.zip"
    monkeypatch.setattr(sys, "argv", ["empacotar_dsm4.py", "--destino", str(destino)])
    assert empacotar.main() == 0
    capsys.readouterr()
    with zipfile.ZipFile(destino) as z:
        nomes = set(z.namelist())
        pastas = {n.rsplit("/", i)[0] + "/" for n in nomes for i in range(1, n.count("/") + 1)}
        quebrados = []
        for nome in sorted(n for n in nomes if n.endswith(".md")):
            texto = CERCA.sub("", z.read(nome).decode("utf-8"))
            for alvo in LINK.findall(texto):
                if re.match(r"[a-z]+:", alvo) or alvo.startswith("/"):
                    continue  # URL ou caminho absoluto (fora do escopo do pacote)
                caminho = posixpath.normpath(posixpath.join(posixpath.dirname(nome), alvo))
                if caminho not in nomes and caminho.rstrip("/") + "/" not in pastas:
                    quebrados.append(f"{nome}: {alvo}")
        assert not quebrados, "links que não abrem no ZIP:\n" + "\n".join(quebrados[:40])


def test_package_carries_the_dashboard_build_only_when_it_is_fresh(tmp_path, monkeypatch):
    """O ZIP leva web/dist pronto (serve --demo abre sem bun nem Node), mas só se a build for mais nova que as
    fontes da interface: build ausente ou velha impede o pacote, em vez de entregar uma interface desatualizada."""
    import os

    empacotar = _carregar_empacotador()  # não usa o Git: a lista de fontes é substituída abaixo
    monkeypatch.setattr(empacotar, "RAIZ", tmp_path)
    fonte = tmp_path / "web" / "src" / "App.tsx"
    fonte.parent.mkdir(parents=True)
    fonte.write_text("x", encoding="utf-8")
    monkeypatch.setattr(empacotar, "arquivos_git", lambda: ["web/src/App.tsx"])
    arquivos, motivo = empacotar.dashboard()
    assert arquivos == [] and "não existe" in motivo
    indice = tmp_path / "web" / "dist" / "index.html"
    (tmp_path / "web" / "dist" / "assets").mkdir(parents=True)
    indice.write_text("<html>", encoding="utf-8")
    (tmp_path / "web" / "dist" / "assets" / "app.js").write_text("js", encoding="utf-8")
    os.utime(indice, (1_000, 1_000))  # build velha
    arquivos, motivo = empacotar.dashboard()
    assert arquivos == [] and "mais velho" in motivo
    os.utime(indice, None)  # build nova
    os.utime(fonte, (1_000, 1_000))
    arquivos, motivo = empacotar.dashboard()
    assert motivo is None
    assert sorted(alvo for _, alvo in arquivos) == ["codigo/web/dist/assets/app.js", "codigo/web/dist/index.html"]


IGNORAR = {".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "saidas", "dados", "build", "dist"}  # gerados


def test_links_open_inside_the_extracted_package():
    """Rodando de dentro do ZIP extraído (sem Git, como o professor): todo link relativo dos Markdown do pacote abre
    na própria árvore, e o dashboard vem construído. No repositório, quem confere é o teste que monta o ZIP."""
    pacote = RAIZ.parent
    if (RAIZ / ".git").exists() or RAIZ.name != "codigo" or not (pacote / "USO_DE_IA.md").is_file():
        pytest.skip("fora do ZIP extraído: o teste que monta o pacote confere os links")
    assert (RAIZ / "web" / "dist" / "index.html").is_file()  # serve --demo abre sem bun nem Node
    quebrados = []
    for md in sorted(pacote.rglob("*.md")):
        if IGNORAR & set(md.relative_to(pacote).parts):
            continue
        texto = CERCA.sub("", md.read_text(encoding="utf-8"))
        for alvo in LINK.findall(texto):
            if re.match(r"[a-z]+:", alvo) or alvo.startswith("/"):
                continue
            if not (md.parent / alvo).exists():
                quebrados.append(f"{md.relative_to(pacote).as_posix()}: {alvo}")
    assert not quebrados, "links que não abrem no pacote:" + chr(10) + chr(10).join(quebrados[:40])

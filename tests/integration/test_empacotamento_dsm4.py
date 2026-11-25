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


def _empacotador():
    if not (RAIZ / ".git").exists() or shutil.which("git") is None:
        pytest.skip("sem repositório Git: o empacotador lista os arquivos versionados")
    spec = importlib.util.spec_from_file_location("empacotar_dsm4", RAIZ / "tools" / "empacotar_dsm4.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_every_relative_link_in_the_package_opens_inside_the_zip(tmp_path, monkeypatch, capsys):
    empacotar = _empacotador()
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

"""Pacote da entrega da DSM3: o que o professor abre primeiro (README e USO_DE_IA) tem de funcionar no zip.

No repositório esses arquivos apontam para `../../docs/...`; no zip o projeto fica em `codigo/`. O
empacotador reescreve os links das cópias que entram no zip; este teste monta o pacote numa pasta
temporária e confere que todo link relativo abre dentro dele.
"""
import importlib.util
import posixpath
import re
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
LINK = re.compile(r"\]\(([^)#\s]+)")


def _empacotador():
    spec = importlib.util.spec_from_file_location("empacotar_dsm3", RAIZ / "tools" / "empacotar_dsm3.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_every_relative_link_in_the_delivery_docs_opens_inside_the_zip(tmp_path, capsys):
    empacotar = _empacotador()
    empacotar.DESTINO = tmp_path / "DSM3-entrega.zip"  # não toca no zip de entrega
    assert empacotar.main() == 0
    capsys.readouterr()
    with zipfile.ZipFile(empacotar.DESTINO) as z:
        nomes = set(z.namelist())
        pastas = {posixpath.dirname(n.rstrip("/")) + "/" for n in nomes} | {n.rsplit("/", 1)[0] + "/" for n in nomes}
        for doc in ("README.md", "USO_DE_IA.md"):
            texto = z.read(f"DSM3-entrega/{doc}").decode("utf-8")
            assert "](../../" not in texto, f"{doc}: link para fora do pacote"
            quebrados = []
            for alvo in LINK.findall(texto):
                if alvo.startswith(("http://", "https://", "mailto:")):
                    continue
                caminho = posixpath.normpath(posixpath.join("DSM3-entrega", alvo))
                if caminho not in nomes and caminho.rstrip("/") + "/" not in pastas:
                    quebrados.append(alvo)
            assert not quebrados, f"{doc}: links que não abrem no zip: {quebrados}"
    # no repositório os arquivos continuam com os caminhos de lá (valem no GitHub)
    assert "](../../docs/" in (RAIZ / "entregas" / "dsm3" / "README.md").read_text(encoding="utf-8")


def test_link_rewrite_only_touches_links_to_the_repository_root():
    reescrever = _empacotador().links_para_o_zip
    assert reescrever("[a](../../docs/x.md) e [b](modelos-editaveis/y.mmd) e [c](https://e.x/../../z)") == \
        "[a](codigo/docs/x.md) e [b](modelos-editaveis/y.mmd) e [c](https://e.x/../../z)"

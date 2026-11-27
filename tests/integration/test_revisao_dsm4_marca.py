"""Correção simulada da DSM4: o nome dos arquivos de estado (chave e contador, na pasta de chaves) vinha do caminho
do arquivo de dados escrito como foi passado. No Windows, `MEMORIA.JSON` e `memoria.json` são o mesmo arquivo, mas
davam nomes diferentes: a outra grafia achava outra chave e a memória ficava "comprometida". A marca agora usa
`os.path.normcase`; instalações com o nome antigo são migradas na primeira abertura."""
import os

import pytest

from fin_mas.env.scenarios import CENARIOS, run_scenario
from fin_mas.services import selado
from fin_mas.services.audit import AuditLog
from fin_mas.services.memoria import Memoria

pytestmark = pytest.mark.integracao


def _memoria(caminho):
    return Memoria(AuditLog(), lambda: 0, caminho=caminho)


def test_two_spellings_of_a_file_not_yet_created_get_the_same_state_name(tmp_path):
    """Dois processos criando a memória ao mesmo tempo, cada um com uma grafia do caminho: antes de o arquivo existir o
    sistema operacional não corrige a grafia, e a marca antiga (sem normcase) dava duas chaves para o mesmo arquivo
    (o segundo acusava "selo não confere"). A marca nova é a mesma."""
    if os.path.normcase("A") == "A":
        pytest.skip("só num sistema de arquivos que não diferencia maiúsculas (Windows)")
    minusculas = tmp_path / "dados" / "memoria.json"
    maiusculas = tmp_path / "dados" / "MEMORIA.JSON"
    assert not minusculas.exists()
    assert selado.marca(minusculas) == selado.marca(maiusculas)
    assert selado.marca_legada(minusculas) != selado.marca_legada(maiusculas)  # o defeito que a marca nova fecha


def test_state_files_with_the_legacy_name_are_migrated(tmp_path, monkeypatch):
    chaves = tmp_path / "chaves"
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(chaves))
    arquivo = tmp_path / "dados" / "memoria.json"
    run_scenario(CENARIOS["reincidencia_waiver"], memoria=arquivo)
    nova, antiga = selado.marca(arquivo), selado.marca_legada(arquivo)
    if nova == antiga:
        pytest.skip("o caminho não muda com normcase (Linux, macOS ou caminho todo em minúsculas)")
    for f in chaves.glob(f"*-{nova}.*"):  # simula uma instalação da versão anterior
        f.rename(f.with_name(f.name.replace(nova, antiga)))
    m = _memoria(arquivo)
    assert m.integra and any(e["tipo"] == "waiver" for e in m.entradas)
    assert not list(chaves.glob(f"memoria-{antiga}.*"))  # migrado para o nome novo
    assert list(chaves.glob(f"memoria-{nova}.chave"))

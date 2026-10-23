"""E8 — TEST-24: mesmo seed, mesmo hash de saída, sem rede."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fin_mas.env.scenarios import CENARIOS, run_scenario

pytestmark = pytest.mark.e2e
RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("nome", sorted(CENARIOS))
def test_offline_seeded_reproducibility(nome):
    # a fixture autouse de conftest.py bloqueia socket.connect: qualquer acesso à rede falharia
    a, b = run_scenario(nome), run_scenario(nome)
    assert a.hash == b.hash
    assert a.resposta.content == b.resposta.content


def test_seeds_diferentes_mudam_o_hash():
    assert run_scenario("fechar_mes", seed=1).hash != run_scenario("fechar_mes", seed=2).hash


def test_mesmo_hash_em_processos_distintos_com_hashseed_diferente(tmp_path):
    """Pega ordem de iteração de sets/dicts: PYTHONHASHSEED muda a cada processo."""
    hashes = []
    for hashseed in ("0", "123"):
        env = {**os.environ, "PYTHONHASHSEED": hashseed, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
        saida = subprocess.run(
            [sys.executable, "-m", "fin_mas", "run", "--scenario", "depuracao", "--trace",
             str(tmp_path / f"trace-{hashseed}.jsonl")],
            capture_output=True, text=True, env=env, check=True, cwd=RAIZ,
        ).stdout
        hashes.append(next(linha for linha in saida.splitlines() if linha.startswith("hash do trace:")))
    assert hashes[0] == hashes[1]
    assert (tmp_path / "trace-0.jsonl").read_bytes() == (tmp_path / "trace-123.jsonl").read_bytes()

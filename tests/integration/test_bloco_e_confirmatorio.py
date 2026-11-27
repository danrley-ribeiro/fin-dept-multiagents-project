"""Replicação confirmatória do bloco E (docs/dsm4/experimento-bloco-e.md).

O bloco E foi exploratório (seeds 1 a 30, desenhado depois dos blocos A a D). As hipóteses H-E1 a H-E8 e os
critérios foram pré-registrados antes de rodar as seeds 31 a 60. Estes testes conferem o aparato da replicação:
as seeds novas não se sobrepõem às do exploratório, o verificador aplica os critérios (e refuta quando o dado não
os satisfaz) e a conferência publicada bate com os dados publicados.
"""
import csv
import importlib.util
import shutil
from pathlib import Path

import pytest

from fin_mas import estudo_e

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
RESULTADOS = RAIZ / "docs" / "dsm4" / "resultados"


def _verificador():
    spec = importlib.util.spec_from_file_location("confirmar_bloco_e", RAIZ / "tools" / "confirmar_bloco_e.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_confirmatory_replication_uses_only_new_seeds():
    exploratorio = {c[3] for c in estudo_e.celulas(30)}
    confirmatorio = {c[3] for c in estudo_e.celulas(30, primeira=31)}
    assert exploratorio == set(range(1, 31))
    assert confirmatorio == set(range(31, 61))
    # o plano é o mesmo, só as seeds mudam: mesmas células por seed
    assert [c[:3] for c in estudo_e.celulas(1)] == [c[:3] for c in estudo_e.celulas(1, primeira=31)]


def test_hypothesis_checker_confirms_and_refutes_from_the_data(tmp_path):
    v = _verificador()
    confirmacao = RESULTADOS / "bloco_e_confirmatorio"
    resultado = v.conferir(confirmacao)
    assert [h["id"] for h in resultado] == [f"H-E{i}" for i in range(1, 9)]
    # a conferência publicada é a que o verificador produz hoje a partir dos dados publicados
    assert (confirmacao / "confirmacao.md").read_text(encoding="utf-8") == v.relatorio_md(confirmacao, resultado)

    # um dado que viola o critério refuta a hipótese: uma publicação indevida com dois pedidos do mesmo mês
    copia = tmp_path / "adulterado"
    shutil.copytree(confirmacao, copia)
    with (copia / "execucoes.csv").open(encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    alvo = next(r for r in linhas if r["fator"] == "concorrencia" and r["nivel"] == "2" and r["modo"] == "mesma")
    alvo["publicacoes_indevidas"] = "1"
    with (copia / "execucoes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    adulterado = {h["id"]: h["confirmada"] for h in v.conferir(copia)}
    assert adulterado["H-E1"] is False

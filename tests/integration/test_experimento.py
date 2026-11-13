"""Experimento da DSM4 pela linha de comando, em modo rápido: arquivos, reprodutibilidade e estatística.

O comando roda de verdade, em outro processo, duas vezes. A biblioteca estatística é conferida
dentro do próprio pipeline: `resumo.json` traz os resultados dos exemplos pequenos de
`estatistica.autoteste()`, e os valores esperados abaixo foram **calculados à mão**.
"""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fin_mas import estatistica, estudo

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
ARQUIVOS = ("execucoes.csv", "tempo_parede.csv", "resumo.json", "resumo.md", "testes.md", "manifesto.json",
            "fig_qualidade.svg", "fig_robustez.svg", "fig_custo.svg", "fig_cognicao.svg", "fig_sensibilidade.svg",
            "fig_ablacao.svg")


def _experimento(pasta, semente_de_hash):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1", "PYTHONHASHSEED": semente_de_hash}
    return subprocess.run([sys.executable, "-m", "fin_mas", "experimento", "--rapido", "--out", str(pasta)],
                          capture_output=True, text=True, cwd=RAIZ, env=env, stdin=subprocess.DEVNULL)


@pytest.fixture(scope="module")
def rodadas(tmp_path_factory):
    base = tmp_path_factory.mktemp("experimento")
    primeira, segunda = _experimento(base / "a", "1"), _experimento(base / "b", "2")
    assert primeira.returncode == 0, primeira.stderr
    assert segunda.returncode == 0, segunda.stderr
    return base / "a", base / "b", primeira.stdout


def test_quick_experiment_writes_every_output_and_repeats_byte_for_byte(rodadas):
    a, b, saida = rodadas
    assert sorted(p.name for p in a.iterdir()) == sorted(ARQUIVOS)
    # tudo o que não é tempo de parede sai idêntico numa segunda execução, em outro processo
    for nome in ARQUIVOS:
        if nome != "tempo_parede.csv":
            assert (a / nome).read_bytes() == (b / nome).read_bytes(), nome
    manifesto = json.loads((a / "manifesto.json").read_text(encoding="utf-8"))
    sha = hashlib.sha256((a / "execucoes.csv").read_bytes()).hexdigest()
    assert manifesto["arquivos"]["execucoes.csv"] == {"sha256": sha, "reproduzivel": True} and sha in saida
    assert manifesto["arquivos"]["tempo_parede.csv"]["reproduzivel"] is False
    assert manifesto["versao_do_pacote"] == "0.5.0" and manifesto["seeds"] == [1, 2, 3] and manifesto["rapido"] is True
    assert manifesto["parametros_padrao"]["prazo_subtarefa"] == 30 and manifesto["estatistica"]["correcao"] == "Holm por família"
    with open(a / "execucoes.csv", newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert list(linhas[0]) == estudo.CAMPOS and len(linhas) == manifesto["execucoes"] == len(estudo.plano(rapido=True))
    assert {r["bloco"] for r in linhas} == set("ABCD") and {r["braco"] for r in linhas} == set(estudo.BRACOS)
    assert not any(r["status"] == "erro" for r in linhas)
    with open(a / "tempo_parede.csv", newline="", encoding="utf-8") as f:
        tempos = list(csv.DictReader(f))
    assert len(tempos) == len(linhas) and all(float(t["ms"]) > 0 for t in tempos)
    for nome in ARQUIVOS:
        if nome.endswith(".svg"):
            svg = (a / nome).read_text(encoding="utf-8")
            assert svg.startswith("<svg") and "<title>" in svg and "SMA básico" in svg, nome
    assert "RQ1" in (a / "resumo.md").read_text(encoding="utf-8")
    testes = (a / "testes.md").read_text(encoding="utf-8")
    assert "Família RQ2" in testes and "p (Holm)" in testes and "Conferência da biblioteca estatística" in testes


def test_pipeline_statistics_match_hand_computed_references(rodadas):
    """Os valores esperados foram calculados à mão; o que está sendo conferido é o que o pipeline gravou."""
    v = json.loads((rodadas[0] / "resumo.json").read_text(encoding="utf-8"))["validacao_estatistica"]
    # 2, 4, 4, 4, 5, 5, 7, 9: soma 40, média 5; desvios ao quadrado somam 32; amostral = raiz(32/7)
    assert v["media"] == 5 and v["mediana"] == 4.5 and v["desvio"] == pytest.approx(2.138090, abs=1e-6)
    # diferenças 8, -3, 5, 12, -1, 7, 10, 2: postos de |d| = 6, 3, 4, 8, 1, 5, 7, 2; W- = 3 + 1 = 4, W+ = 36 - 4 = 32.
    # Dos 2^8 = 256 sinais, 7 dão soma <= 4 ({}, {1}, {2}, {3}, {1,2}, {4}, {1,3}); bilateral: 14/256
    assert v["wilcoxon_exato"] == {"w_menos": 4.0, "w_mais": 32.0, "p": 14 / 256, "metodo": "exato"}
    # diferenças 1, 1, 2, -2, 3, 3, -1, 4, 5, 5: postos médios 2, 2, 4.5, 4.5, 6.5, 6.5, 2, 8, 9.5, 9.5; W- = 4.5 + 2 = 6.5.
    # média 27.5; variância 10*11*21/24 - (24 + 6 + 6 + 6)/48 = 96.25 - 0.875 = 95.375; z = (21 - 0.5)/9.76601 = 2.0991
    assert v["wilcoxon_normal"] == {"w_menos": 6.5, "w_mais": 48.5, "z": 2.0991, "p": 0.0358}
    assert v["wilcoxon_sem_diferencas"] == 1.0
    # x = 19, 22, 16, 29, 24 e y = 20, 11, 17, 12: postos de x = 5, 7, 3, 9, 8 (soma 32); U_x = 32 - 15 = 17; U_y = 3.
    # C(9,4) = 126 arranjos; 7 têm soma de postos de y <= 13; bilateral: 14/126
    assert v["mann_whitney_exato"] == {"u1": 17.0, "u2": 3.0, "p": round(14 / 126, 6), "metodo": "exato"}
    # aproximação normal: média 10, variância 5*4*10/12 = 16.667; z = (7 - 0.5)/4.0825 = 1.5922
    assert v["mann_whitney_normal"] == {"z": 1.5922, "p": 0.1113}
    # delta de Cliff: 17 pares com x > y e 3 com x < y, em 20: (17 - 3)/20
    assert v["cliff"] == 0.7 and v["cliff_magnitude"] == "grande"
    # Holm sobre 0.01, 0.04, 0.03, 0.005: ordenados 0.005*4, 0.01*3, 0.03*2, 0.04*1 -> 0.02, 0.03, 0.06, max(0.06, 0.04)
    assert v["holm"] == [0.03, 0.06, 0.06, 0.02]
    assert v["bootstrap"]["reprodutivel"] and v["bootstrap"]["contem_a_media"] and v["bootstrap"]["amostra_constante"] == [7.0, 7.0]
    assert v == json.loads(json.dumps(estatistica.autoteste()))  # o que o pipeline gravou é o que a biblioteca calcula


def test_summary_and_tests_are_recomputed_from_the_raw_rows(rodadas):
    """A análise depende só de `execucoes.csv`: refeita a partir do arquivo, dá o mesmo resumo."""
    a = rodadas[0]
    gravado = json.loads((a / "resumo.json").read_text(encoding="utf-8"))
    linhas = estudo.ler_csv(a / "execucoes.csv")
    assert json.loads(json.dumps(estudo.analisar(linhas))) == gravado
    # um teste do plano, refeito aqui com as funções da biblioteca: robustez do SMA básico x workflow, sob perda
    def por_seed(braco):
        return estudo.por_seed(estudo.selecionar(linhas, bloco="A", braco=braco, condicao="perda_media"), "execucao_correta")
    sma, wf = por_seed("sma_basico"), por_seed("wf_equivalente")
    teste = next(t for t in gravado["testes"] if t["comparacao"] == "sma_basico x wf_equivalente, perda_media")
    x, y = [sma[s] for s in sorted(sma)], [wf[s] for s in sorted(wf)]
    assert teste["media_a"] == round(sum(x) / len(x), 4) and teste["media_b"] == round(sum(y) / len(y), 4)
    assert teste["p"] == round(estatistica.wilcoxon_pareado(x, y)["p"], 6) and teste["cliff"] == round(estatistica.cliff(x, y), 4)
    familia = [t for t in gravado["testes"] if t["familia"] == "RQ2" and t["p"] is not None and t["pares_diferentes"]]
    assert [t["p_holm"] for t in familia] == [round(p, 6) for p in estatistica.holm([t["p"] for t in familia])]
    # o workflow não troca mensagens entre componentes: sob perda, o resultado é o da execução sem falha
    assert all(v == 1 for v in wf.values())
    # sem falhas, os dois braços dão o mesmo resultado em todos os pares, e a cognição local também
    assert gravado["identidade"]["sma_basico_x_wf_equivalente"]["diferentes"] == 0
    assert gravado["identidade"]["sma_local_x_sma_basico"]["diferentes"] == 0
    inv = gravado["tabelas"]["invariantes"]
    assert inv["ataques_tentados"] > 0 and inv["ataques_aceitos"] == inv["ataques_sem_premissa"]
    assert set(inv["execucoes_por_invariante"]) <= {"INV-07"} and inv["execucoes_com_erro"] == 0

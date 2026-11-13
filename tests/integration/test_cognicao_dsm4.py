"""Cognição da DSM4 pelo terminal e com arquivos reais (ADR-010, CP8).

Linha de comando por subprocesso (catálogo de cenários, compromisso, base normativa) e o registro
selado de aprendizado em pasta temporária: persistência entre execuções, contagem única por
hipótese, adulteração detectada com falha fechada.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from fin_mas.env.scenarios import Scenario, run_scenario

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
NOVOS = ("res_explica_variacao", "res_insumo_faltante", "cus_rateio_alternativo", "rel_relatorio_de_excecao",
         "aprendizado_regra", "compromisso_cego", "compromisso_obstinado", "compromisso_aberto",
         "memoria_reincidencia_orc", "normas_sem_evidencia", "normas_fundamentam_achado")


def cli(*args, check=True):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
    return subprocess.run([sys.executable, "-m", "fin_mas", *args], capture_output=True, text=True, env=env, cwd=RAIZ,
                          check=check)


def mes(competencia, plantio):
    return Scenario(f"aprendizado_{competencia}", "um mês por execução", "avaliar_orcamento", cognicao="local",
                    agenda=((competencia, plantio),), pedidos=(("avaliar_orcamento", competencia, 1),))


def test_cli_checks_every_new_scenario_against_the_invariants():
    for filtro in ("res_", "cus_", "rel_", "aprendizado", "compromisso", "memoria_reincidencia", "normas_"):
        saida = cli("cenarios", "--verificar", "--filtro", filtro).stdout
        assert "VIOLAÇÃO" not in saida and "NÃO" not in saida and "SEM RESPOSTA" not in saida
    listados = cli("list").stdout
    assert all(nome in listados for nome in NOVOS)


def test_cli_shows_deliberation_of_the_new_bdi_specialists():
    saida = cli("run", "--scenario", "cus_rateio_alternativo").stdout
    assert "DELIBERA AG-CUS: definir_rateio:2026-09|DEL-001 -> P-RATEIO-PROPORCIONAL-RECEITA" in saida
    assert "INTENCAO AG-CUS: AG-CUS-I001 P-RATEIO-PADRAO falhou" in saida
    assert "ressalva: rateio dos custos fixos pelo critério proporcional à receita" in saida
    saida = cli("run", "--scenario", "res_explica_variacao").stdout
    assert "HIPOTESE AG-RES: AG-RES-H001 causa_custo_fixo(ebitda_pct) confirmada" in saida
    assert "APRENDIZADO AG-RES: local:R-RES-CUSTO-FIXO confirmada" in saida
    # um cenário revisado da DSM3 com outra estratégia de compromisso, pela linha de comando
    cego = cli("run", "--scenario", "orc_sem_cin", "--cognicao", "local", "--compromisso", "cego").stdout
    assert "P-CONSULTAR-CIN insistida (compromisso cego" in cego and "P-SINALIZAR mantida" in cego
    assert cli("run", "--scenario", "orc_sem_cin", "--compromisso", "teimoso", check=False).returncode == 2


def test_cli_searches_the_normative_base_and_reports_missing_evidence():
    ok = cli("normas", "segregação de funções: quem registra a transação não a aprova", "-k", "1")
    assert ok.returncode == 0 and "COSO-2013 | trecho COSO-SEGREGACAO | corpus-v1; paráfrase" in ok.stdout
    vazio = cli("normas", "pagamento em duplicidade ao mesmo fornecedor", check=False)
    assert vazio.returncode == 1 and vazio.stdout.startswith("sem evidência na base normativa (corpus-v1)")


def test_learning_persists_between_runs_in_a_sealed_file(tmp_path):
    arquivo = tmp_path / "dados" / "aprendizado.json"
    falso = ("desvio_orcamentario", "observacao_alarme_falso")
    a = run_scenario(mes("2026-07", falso), aprendizado=str(arquivo))
    assert [r["confianca"] for r in a.audit.records if r["kind"] == "hipotese" and r["evento"] == "aceita"] == [0.8]
    gravado = json.loads(arquivo.read_text(encoding="utf-8"))
    assert gravado["versao"] == 1 and gravado["contador"] == 1 and len(gravado["selo"]) == 64
    (obs,) = gravado["dados"]["observacoes"]
    assert (obs["agente"], obs["regra"], obs["desfecho"], obs["competencia"]) == ("AG-ORC", "local:R-OBS-REPETICAO", "refutada", "2026-07")
    assert obs["fonte"].startswith("AG-CIN (QRY-")  # proveniência da evidência; nenhum nome de pessoa
    # outra execução, mês seguinte: a confiança vem do arquivo
    b = run_scenario(mes("2026-08", falso), aprendizado=str(arquivo))
    carregado = next(r for r in b.audit.records if r["kind"] == "aprendizado" and r["evento"] == "carregado")
    assert carregado["observacoes"] == 1 and carregado["integro"] is True
    assert [r["confianca"] for r in b.audit.records if r["kind"] == "hipotese" and r["evento"] == "aceita"] == [0.53]
    # reprocessar o mesmo mês não conta duas vezes (uma observação por hipótese)
    run_scenario(mes("2026-08", falso), aprendizado=str(arquivo))
    assert len(json.loads(arquivo.read_text(encoding="utf-8"))["dados"]["observacoes"]) == 2
    # a mesma coisa pela linha de comando
    saida = cli("run", "--scenario", "hipotese_refutada", "--aprendizado", str(arquivo)).stdout
    assert "APRENDIZADO AG-ORC: local:R-OBS-REPETICAO refutada" in saida


def test_tampered_learning_file_fails_closed(tmp_path):
    arquivo = tmp_path / "aprendizado.json"
    falso = ("desvio_orcamentario", "observacao_alarme_falso")
    run_scenario(mes("2026-07", falso), aprendizado=str(arquivo))
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    dados["dados"]["observacoes"][0]["desfecho"] = "confirmada"  # alguém "melhora" o histórico da regra por fora
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    e = run_scenario(mes("2026-08", falso), aprendizado=str(arquivo))
    eventos = [r for r in e.audit.records if r["kind"] == "aprendizado"]
    assert eventos[0]["evento"] == "comprometido" and "selo não confere" in eventos[0]["motivo"]
    # falha fechada: a regra volta à confiança inicial e nada novo é gravado no arquivo adulterado
    assert [r["confianca"] for r in e.audit.records if r["kind"] == "hipotese" and r["evento"] == "aceita"] == [0.8]
    assert not [r for r in eventos if r["evento"] == "observada"] and [r for r in eventos if r["evento"] == "indisponivel"]
    assert json.loads(arquivo.read_text(encoding="utf-8")) == dados
    assert e.resposta.performative == "inform"  # o fechamento não depende do aprendizado

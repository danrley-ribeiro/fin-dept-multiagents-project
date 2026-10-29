"""Empresas sem ERP: modelos Excel, leitura validada, correções gravadas na planilha, servidor MCP de
Excel por stdio e envio pelo dashboard (TEST-38 a TEST-40). Arquivos reais em pastas temporárias."""
import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

from fin_mas.env.dataset import Dataset
from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.fontes import planilha
from fin_mas.live import Simulacao
from fin_mas.server import tratar

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def modelos(tmp_path):
    return {p.name: p for p in planilha.gerar_modelos(tmp_path / "modelos")}


def test_spreadsheet_templates_validate_and_report_errors(modelos, tmp_path):
    assert set(modelos) == {"modelo_controladoria_em_branco.xlsx", "exemplo_micro.xlsx", "exemplo_pequena.xlsx",
                            "exemplo_media.xlsx", "exemplo_grande.xlsx"}
    ds = planilha.ler(modelos["exemplo_pequena.xlsx"])
    assert (ds.porte, ds.competencia, ds.tem_erp) == ("pequena", "2026-09", False)
    with pytest.raises(planilha.ModeloInvalido) as vazio:
        planilha.ler(modelos["modelo_controladoria_em_branco.xlsx"])
    assert "Pessoas: nenhuma linha preenchida" in vazio.value.erros
    # planilha preenchida com erros reais de digitação: cargo inexistente, aprovador desconhecido, valor texto
    quebrada = tmp_path / "quebrada.xlsx"
    shutil.copy(modelos["exemplo_media.xlsx"], quebrada)
    wb = load_workbook(quebrada)
    wb["Pessoas"]["C2"] = "estagiario"
    wb["Lancamentos"]["H3"] = "zeca"
    wb["Lancamentos"]["F4"] = "mil reais"
    wb.save(quebrada)
    with pytest.raises(planilha.ModeloInvalido) as e:
        planilha.ler(quebrada)
    texto = " | ".join(e.value.erros)
    assert "Lancamentos!Valor (R$) linha 4: valor inválido 'mil reais'" in texto
    assert "Valor (R$) é obrigatório" in texto


def test_agents_close_month_from_filled_spreadsheet_and_write_back_correction(tmp_path):
    pasta = tmp_path / "empresa"
    ds_origem = Dataset(seed=7, porte="micro", plantar=("alcada",))
    arquivo = planilha.gerar_modelo(pasta / "fechamento.xlsx", exemplo=ds_origem)
    e = run_scenario(Scenario("planilha", "empresa real", "fechar_mes", decisao_aprovador="corrigir"), pasta=pasta)
    respostas = e.respostas
    assert [r.performative for r in respostas.values()] == ["inform", "inform"]  # avaliar orçamento + fechar mês
    fontes = {r["fonte"] for r in e.audit.records if r["kind"] == "mcp_call" and "fonte" in r}
    assert f"mcp://excel/{arquivo.name}#Lancamentos" in fontes
    # a correção aceita pelo aprovador foi gravada na própria planilha (a pasta segue como fonte da verdade)
    plantado = next(n for n in ds_origem.gold["nao_conformidades"] if n["regra"] == "alcada")["lancamento"]
    ws = load_workbook(arquivo)["Lancamentos"]
    linha = next(r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] == plantado)
    assert linha[7] == "elisa"  # reaprovado pela sócia (controle compensatório da micro)
    assert planilha.ler(pasta).lancamentos  # e a planilha continua válida


def _rpc(proc, mensagem):
    proc.stdin.write(json.dumps(mensagem) + "\n")
    proc.stdin.flush()
    if "id" not in mensagem:
        return None
    return json.loads(proc.stdout.readline())


def test_excel_mcp_server_over_stdio(modelos, tmp_path):
    pasta = tmp_path / "mcp"
    pasta.mkdir()
    shutil.copy(modelos["exemplo_micro.xlsx"], pasta)
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "fin_mas", "mcp-excel", "--pasta", str(pasta)], cwd=RAIZ, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    try:
        init = _rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                      "clientInfo": {"name": "teste", "version": "1"}}})
        assert init["result"]["serverInfo"]["name"] == "sma-excel"
        _rpc(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        ferramentas = _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        assert {f["name"] for f in ferramentas} >= {"listar_planilhas", "ler_aba", "validar_planilha", "resumo_empresa"}

        def chamar(i, nome, **args):
            r = _rpc(proc, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                            "params": {"name": nome, "arguments": args}})["result"]
            return r["isError"], r["content"][0]["text"]

        erro, texto = chamar(3, "listar_planilhas")
        assert not erro and json.loads(texto)["planilhas"][0] == {
            "arquivo": "exemplo_micro.xlsx", "bytes": (pasta / "exemplo_micro.xlsx").stat().st_size, "valido": True,
            "erros": []}
        erro, texto = chamar(4, "ler_aba", arquivo="exemplo_micro.xlsx", aba="Pessoas")
        assert not erro and json.loads(texto)["linhas"][0]["Cargo"] == "assistente"
        erro, texto = chamar(5, "resumo_empresa", arquivo="exemplo_micro.xlsx")
        resumo = json.loads(texto)
        assert resumo["porte"] == "micro" and resumo["tem_erp"] is False and "ITG 1000" in resumo["norma_contabil"]
        erro, texto = chamar(6, "ler_aba", arquivo="../fora.xlsx", aba="Pessoas")  # fora da pasta: negado
        assert erro and "fora da pasta" in texto
        erro, texto = chamar(7, "criar_modelo_em_branco", arquivo="exemplo_micro.xlsx")  # não sobrescreve
        assert erro and "já existe" in texto
        desconhecido = _rpc(proc, {"jsonrpc": "2.0", "id": 8, "method": "resources/list"})
        assert desconhecido["error"]["code"] == -32601
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)


def test_dashboard_downloads_template_uploads_spreadsheet_and_runs(tmp_path):
    sim = Simulacao("fechar_mes", pausado=True, pasta_dados=tmp_path / "dados")
    status, cab, xlsx = tratar(sim, "GET", "/api/modelos/exemplo_pequena.xlsx")
    assert status == 200 and cab["Content-Type"].endswith("spreadsheetml.sheet") and xlsx[:2] == b"PK"
    assert tratar(sim, "GET", "/api/modelos/../../segredo.txt")[0] == 404
    # planilha inválida é recusada com a lista de erros e não substitui a pasta
    _, _, branco = tratar(sim, "GET", "/api/modelos/modelo_controladoria_em_branco.xlsx")
    status, _, corpo = tratar(sim, "POST", "/api/dados/planilha", json.dumps(
        {"nome": "vazia.xlsx", "conteudo_base64": base64.b64encode(branco).decode()}).encode())
    assert status == 422 and "Produtos: nenhuma linha preenchida" in json.loads(corpo)["erros"]
    status, _, corpo = tratar(sim, "POST", "/api/dados/planilha", json.dumps(
        {"nome": "minha_empresa.xlsx", "conteudo_base64": base64.b64encode(xlsx).decode()}).encode())
    assert status == 200 and json.loads(corpo)["porte"] == "pequena"
    assert json.loads(tratar(sim, "GET", "/api/dados")[2])["planilha"] == "minha_empresa.xlsx"
    # reinicia o escritório sobre a planilha enviada e roda até o fim
    sim.comando({"tipo": "reiniciar", "cenario": "fechar_mes", "fonte": "planilha"})
    for _ in range(5000):
        if not sim.passo():
            break
    estado = sim.snapshot()
    assert estado["controle"]["fonte"] == "planilha" and estado["controle"]["porte"] == "pequena"
    assert all(r is not None and r["performative"] in ("inform", "failure") for r in estado["solicitacoes"].values())

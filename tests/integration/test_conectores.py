"""Conectores e entendimento de fontes (ADR-011): servidores HTTP reais em loopback, servidor MCP por stdio,
planilhas reais em pastas temporárias e a CLI por subprocesso. Nada sai da máquina."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fakes.servidor_rest import ServidorFalso
from fin_mas.conectores import descoberta
from fin_mas.conectores.base import (AmbienteConector, CredencialRecusada, FonteIndisponivel, PoliticaRede,
                                     RedeNaoLiberada, RespostaInvalida)
from fin_mas.conectores.cenarios import gerar_planilha_fora_do_modelo, mapeamento_erp_demo
from fin_mas.conectores.erp_demo import ErpDemo, openapi
from fin_mas.conectores.mcp_cliente import ClienteMCP, ConectorMCP, comando_excel
from fin_mas.conectores.planilhas import ConectorPastaPlanilhas
from fin_mas.conectores.rest import ConectorREST
from fin_mas.conectores.simulado import ConectorSimulado
from fin_mas.env.dataset import Ambiente, Dataset
from fin_mas.env.scenarios import CENARIOS, Scenario, build_system, run_scenario
from fin_mas.fontes import entendimento, planilha
from fin_mas.mcp.gateway import ToolDenied
from fin_mas.services.politica import AprovacaoNecessaria

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


def _resultado(execucao):
    return [(r.performative, r.content.get("status"), r.content.get("resultado"), r.content.get("ressalvas"))
            for r in execucao.respostas.values()]


# ---- gabaritos de mapeamento (o que uma pessoa confirmaria) ---------------------------------------
GABARITO_ERP_DEMO = {
    "Pessoas": ("users", {"usuario": "username", "nome": "full_name", "cargo": "job_title"}),
    "Produtos": ("products", {"id": "sku", "un": "business_unit", "qtd": "units_sold", "preco": "unit_price",
                              "custo_variavel_unit": "unit_variable_cost"}),
    "CustosFixos": ("cost-centers", {"centro": "cost_center", "valor": "monthly_amount"}),
    "Orcamento": ("budget", {"conta": "account", "orcado_trimestre": "quarter_budget",
                             "orcado_acumulado": "budget_to_date", "realizado_acumulado": "actual_to_date",
                             "observacao": "notes"}),
    "Lancamentos": ("journal-entries", {"id": "entry_id", "competencia": "posting_date", "conta": "account",
                                        "fornecedor": "vendor", "documento": "invoice_number", "valor": "amount",
                                        "criador": "created_by", "aprovador": "approved_by", "situacao": "status"}),
    "Realizado": ("actuals", {"conta": "account", "realizado_acumulado": "ledger_actual_to_date"}),
    "Historico": ("history", {"conta": "account", "competencia": "period", "orcado": "budget", "realizado": "actual"}),
}
GABARITO_PLANILHA = {
    "Pessoas": ("Equipe", {"usuario": "Login", "nome": "Nome completo", "cargo": "Função"}),
    "Produtos": ("Vendas do mês", {"id": "Código do produto", "nome": "Descrição", "un": "Unidade",
                                   "qtd": "Quantidade", "preco": "Preço de venda", "custo_variavel_unit": "Custo unitário"}),
    "CustosFixos": ("Despesas fixas", {"centro": "Departamento", "valor": "Valor mensal"}),
    "Orcamento": ("Orçamento x realizado", {"conta": "Conta contábil", "orcado_trimestre": "Meta trimestre",
                                            "orcado_acumulado": "Orçado até o mês",
                                            "realizado_acumulado": "Realizado até o mês", "observacao": "Obs"}),
    "Lancamentos": ("Lançamentos contábeis", {"id": "Nº lançamento", "competencia": "Data do lançamento",
                                              "conta": "Conta", "fornecedor": "Credor", "documento": "Nota fiscal",
                                              "valor": "Valor", "criador": "Lançado por",
                                              "aprovador": "Aprovado por", "situacao": "Status"}),
}


def _conferir(sugestao, gabarito):
    m = sugestao["mapeamento"]["abas"]
    for aba, (recurso, campos) in gabarito.items():
        assert m[aba]["recurso"] == recurso, aba
        assert {k: v["origem"] for k, v in m[aba]["campos"].items()} == campos, aba
    for s in sugestao["sugestoes"]:
        if s["origem"]:
            assert s["motivo"] and 0 < s["confianca"] <= 1, s


def test_understanding_openapi_samples_spreadsheet_and_mcp_match_the_answer_key(tmp_path):
    """TEST-250: OpenAPI (só o contrato, sem rede), amostras JSON, planilha fora do modelo e tools MCP: as sugestões
    batem com o gabarito, cada uma com confiança e motivo; conversões de moeda e data inferidas."""
    sug = entendimento.sugerir_mapeamento(entendimento.de_openapi(openapi()))
    _conferir(sug, GABARITO_ERP_DEMO)
    lanc = sug["mapeamento"]["abas"]["Lancamentos"]["campos"]
    assert lanc["valor"]["conversao"] == "reais" and lanc["competencia"]["conversao"] == "data_competencia"
    assert lanc["situacao"]["conversao"] == "situacao"
    assert sug["escrita"]["acoes"] == {"estornar": "reverse", "reaprovar": "reapprove", "reclassificar": "reclassify"}
    # amostras JSON com nomes em inglês, valor em centavos e envelope próprio
    amostras = {"vendors_payments": {"results": [
        {"transactionId": "T-1", "supplier": "F-10", "amount_cents": 123456, "date": "2026-09-03"},
        {"transactionId": "T-2", "supplier": "F-11", "amount_cents": 990, "date": "2026-08-30"}]}}
    est = entendimento.de_amostras_json(amostras)
    campos = {c["nome"]: c["tipo"] for c in est["recursos"][0]["campos"]}
    assert campos == {"transactionId": "identificador", "supplier": "identificador", "amount_cents": "moeda_centavos",
                      "date": "data"} and est["recursos"][0]["raiz"] == "results"
    s = {(x["aba"], x["campo"]): x for x in entendimento.sugerir_mapeamento(est)["sugestoes"]}
    assert s[("Lancamentos", "valor")]["origem"] == "amount_cents" and s[("Lancamentos", "valor")]["conversao"] == "centavos"
    assert s[("Lancamentos", "fornecedor")]["origem"] == "supplier" and "(en)" in s[("Lancamentos", "fornecedor")]["motivo"]
    # planilha "da casa": abas e colunas renomeadas, cabeçalho na linha 3, linha de total
    arquivo = gerar_planilha_fora_do_modelo(tmp_path / "casa.xlsx", Dataset(seed=7, porte="pequena"))
    est = entendimento.de_planilha(arquivo)
    r = entendimento.entender(est, "2026-09")
    _conferir(r["sugestao"], GABARITO_PLANILHA)
    assert {p["mensagem"] for p in r["qualidade"]["problemas"] if p["tipo"] == "total"} == {
        "CustosFixos.valor: a linha de total fecha com a soma dos registros",
        "Lancamentos.valor: a linha de total fecha com a soma dos registros"}
    assert r["previa"]["Lancamentos"][0]["valor"] > 0 and isinstance(r["previa"]["Lancamentos"][0]["valor"], int)
    # MCP: a tool ler_aba(aba=enum) vira um recurso por aba canônica
    pasta = tmp_path / "mcp"
    planilha.gerar_modelo(pasta / "fechamento.xlsx", exemplo=Dataset(seed=11, porte="micro"))
    conector = ConectorMCP("mcp", {"comando": comando_excel(pasta)})
    est = descoberta.estrutura_mcp(conector)
    assert {r["nome"] for r in est["recursos"]} >= {"ler_aba:Pessoas", "ler_aba:Lancamentos", "ler_aba:Empresa"}
    sug = entendimento.sugerir_mapeamento(est)
    assert sug["mapeamento"]["abas"]["Lancamentos"]["recurso"] == "ler_aba:Lancamentos"
    assert sug["mapeamento"]["abas"]["Lancamentos"]["campos"]["valor"] == {"origem": "Valor (R$)", "conversao": "reais"}
    assert sug["mapeamento"]["empresa"]["porte"]["origem"] == "Porte"


def test_quality_report_flags_missing_duplicates_out_of_period_totals_and_negatives(tmp_path):
    """TEST-251: relatório de qualidade sobre uma planilha com defeitos reais; prévia redigida."""
    ds = Dataset(seed=7, porte="pequena")
    ds.lancamentos[1]["id"] = ds.lancamentos[0]["id"]  # código repetido
    ds.lancamentos[2]["competencia"] = "2026-07"  # outro mês
    ds.lancamentos[3]["valor"] = -500_00  # negativo inesperado
    ds.lancamentos[4]["fornecedor"] = "contato: fulano@exemplo.com.br"  # dado pessoal na prévia
    arquivo = gerar_planilha_fora_do_modelo(tmp_path / "defeitos.xlsx", ds)
    from openpyxl import load_workbook
    wb = load_workbook(arquivo)
    ws = wb["Despesas fixas"]
    ws.cell(ws.max_row, 2, 1.0)  # total que não fecha
    ws = wb["Equipe"]
    ws.cell(4, 2).value = None  # login vazio
    wb.save(arquivo)
    r = entendimento.entender(entendimento.de_planilha(arquivo), "2026-09")
    tipos = {(p["tipo"], p["gravidade"]) for p in r["qualidade"]["problemas"]}
    assert {("duplicado", "erro"), ("fora_da_competencia", "aviso"), ("negativo", "aviso"), ("total", "erro"),
            ("faltante", "erro")} <= tipos
    assert not r["qualidade"]["ok"]
    texto = json.dumps(r["previa"], ensure_ascii=False)
    assert "fulano@exemplo.com.br" not in texto and "[EMAIL REDIGIDO]" in texto


def test_rest_demo_closes_the_month_like_the_simulated_erp_and_writes_only_with_approval():
    """TEST-252: fechamento inteiro sobre o ERP de demonstração em loopback = ERP simulado na mesma seed; a correção
    chega ao ERP pela API só com o ticket aprovado; a proveniência não carrega host nem porta."""
    a = run_scenario("conector_rest_demo")
    b = run_scenario("veto_correcao")
    assert _resultado(a) == _resultado(b) and a.resposta.performative == "inform"
    erp = a.system.ambiente.conector.erp
    assert [e["action"] for e in erp.escritas] == ["reapprove"]
    assert a.hash == run_scenario("conector_rest_demo").hash
    fontes = {r["fonte"] for r in a.audit.records if r["kind"] == "mcp_call"}
    assert "conector://erp-demo/journal-entries" in fontes and not any("127.0.0.1" in f for f in fontes)
    meta = a.audit.records[0]
    assert meta["fonte"] == "conector" and meta["conector"]["tipo"] == "rest"
    # sem aprovação: o gateway recusa e nada chega ao ERP
    demo = ErpDemo(42, plantar=("alcada",))
    url = demo.iniciar()
    try:
        recursos, mapeamento = mapeamento_erp_demo()
        conector = ConectorREST("erp", {"url_base": url, "recursos": recursos, "autenticacao": {"tipo": "bearer"},
                                        "escrita": {"caminho": "/api/v1/journal-entries/{lancamento}/actions",
                                                    "corpo": {"action": "{acao}", "period": "{competencia}"},
                                                    "acoes": {"reaprovar": "reapprove"}}},
                                segredo=demo.token, mapeamento=mapeamento)
        s = build_system(ambiente=AmbienteConector(conector, competencia="2026-09"))
        for credencial in (s.orq._Agent__credencial,):
            with pytest.raises(AprovacaoNecessaria):
                s.gateway.call("AG-ORQ", "erp.corrigir", "SOL-X", credencial=credencial, aprovacao="APR-999",
                               lancamento="L-013", acao="reaprovar")
        with pytest.raises(ToolDenied):
            s.gateway.call("AG-CIN", "erp.corrigir", "SOL-X", credencial="forjada", lancamento="L-013", acao="reaprovar")
        assert demo.escritas == []
        sem_token = ConectorREST("erp", {"url_base": url, "autenticacao": {"tipo": "nenhuma"}})
        with pytest.raises(CredencialRecusada):
            sem_token.pedir("/api/v1/journal-entries/L-013/actions", metodo="POST", corpo={"action": "reverse"})
        assert demo.escritas == []
    finally:
        demo.parar()


def test_source_down_fails_explicitly_and_does_not_hang():
    """TEST-253: ERP fora do ar: resposta de falha com o motivo, leituras negadas auditadas, nada publicado, rápido."""
    inicio = time.monotonic()
    e = run_scenario("conector_fora_do_ar")
    assert time.monotonic() - inicio < 15
    assert e.resposta.performative == "failure" and "fonte fora do ar" in e.resposta.content["motivo"]
    negadas = [r for r in e.audit.records if r["kind"] == "mcp_denied"]
    assert negadas and all("fonte indisponível" in r["motivo"] for r in negadas)
    assert not any(r["kind"] == "advance" and r.get("evento") == "publicar" for r in e.audit.records)


def test_rest_connector_errors_401_500_timeout_invalid_json_and_redirect_are_redacted():
    """TEST-254: cada falha vira um erro tipado, com mensagem sem a credencial (mesmo quando o servidor a ecoa)."""
    falso = ServidorFalso(atraso=3.0)
    segredo = "tok-SUPERSECRETO-123456789"
    try:
        c = ConectorREST("x", {"url_base": falso.url, "autenticacao": {"tipo": "bearer"}, "tempo_limite": 0.5},
                         segredo=segredo)
        assert c.pedir("/ok") == {"data": [{"id": "A-1", "amount": 10.5}]}
        casos = {"/negado": CredencialRecusada, "/quebrado": FonteIndisponivel, "/lento": FonteIndisponivel,
                 "/invalido": RespostaInvalida, "/desvio": RespostaInvalida}
        for rota, classe in casos.items():
            with pytest.raises(classe) as erro:
                c.pedir(rota)
            assert segredo not in str(erro.value) and falso.url.split("//")[1] not in str(erro.value), rota
        assert "tempo esgotado" in str(pytest.raises(FonteIndisponivel, c.pedir, "/lento").value)
        assert not any("erp.exemplo" in r["rota"] for r in falso.recebidos)  # o redirecionamento não foi seguido
        # credencial vinculada a outro host não é enviada
        outro = ConectorREST("x", {"url_base": falso.url}, segredo=segredo, host_credencial="127.0.0.1:1")
        antes = len(falso.recebidos)
        outro.config["autenticacao"] = {"tipo": "bearer"}
        outro.pedir("/ok")
        assert falso.recebidos[antes]["authorization"] is None
        assert c.testar()["ok"] is False  # sem recursos configurados: diagnóstico explica
    finally:
        falso.parar()


def test_external_host_is_denied_without_admin_release():
    """TEST-255: só loopback por padrão; host externo é recusado antes de qualquer socket; liberado, a política deixa
    passar (e o ambiente offline dos testes é quem bloqueia a rede)."""
    c = ConectorREST("ext", {"url_base": "https://erp.exemplo.com.br", "autenticacao": {"tipo": "bearer"}},
                     segredo="tok-externo-1234567890")
    with pytest.raises(RedeNaoLiberada) as erro:
        c.pedir("/api")
    assert "PERM-DAD-REDE" in str(erro.value)
    assert c.testar()["rede_bloqueada"] is True
    liberado = ConectorREST("ext", {"url_base": "https://erp.exemplo.com.br"}, politica=PoliticaRede(["erp.exemplo.com.br"]))
    with pytest.raises(FonteIndisponivel) as erro:
        liberado.pedir("/api")
    assert "rede indisponível" in str(erro.value)
    for url in ("file:///etc/passwd", "ftp://127.0.0.1/x"):
        with pytest.raises(RedeNaoLiberada):
            PoliticaRede().verificar(url)


def test_simulated_connector_and_spreadsheet_folder_preserve_the_current_behavior(tmp_path):
    """TEST-256: o ERP simulado por conector dá o mesmo trace do Ambiente sintético; a pasta com uma planilha dá o
    mesmo resultado de `--pasta`, e com duas competências cada mês vem da sua planilha."""
    base = build_system(42, plantar=("alcada",), decisao_aprovador="corrigir")
    via = build_system(42, decisao_aprovador="corrigir", ambiente=Ambiente.de_conector(ConectorSimulado(42, plantar=("alcada",))))
    for s in (base, via):
        s.usuario.solicitar("fechar_mes")
        s.bus.run()
    assert base.bus.audit.digest() == via.bus.audit.digest()
    pasta = tmp_path / "empresa"
    planilha.gerar_modelo(pasta / "setembro.xlsx", exemplo=Dataset(seed=7, porte="micro"))
    ref = run_scenario(Scenario("p", "p", "fechar_mes"), pasta=pasta)
    amb = Ambiente.de_conector(ConectorPastaPlanilhas("pasta", pasta))
    e = run_scenario(Scenario("p", "p", "fechar_mes"), ambiente=amb)
    assert _resultado(e)[0] == _resultado(ref)[-1]
    planilha.gerar_modelo(pasta / "agosto.xlsx", exemplo=Dataset(seed=8, porte="micro", competencia="2026-08"))
    amb = Ambiente.de_conector(ConectorPastaPlanilhas("pasta", pasta))
    assert amb.principal == "2026-09" and amb.dataset("2026-08").competencia == "2026-08"
    assert sorted(ConectorPastaPlanilhas("pasta", pasta).validos()) == ["2026-08", "2026-09"]


def test_spreadsheet_off_model_and_mcp_scenarios_match_the_canonical_reading(tmp_path):
    """TEST-257: `planilha_fora_do_modelo` e `mcp_tools_entendidas` dão o mesmo fechamento da mesma empresa lida no
    modelo canônico; repetem com o mesmo hash."""
    for nome in ("planilha_fora_do_modelo", "mcp_tools_entendidas"):
        sc = CENARIOS[nome]
        e = run_scenario(nome)
        pasta = tmp_path / nome
        planilha.gerar_modelo(pasta / "x.xlsx", exemplo=Dataset(seed=sc.seed, porte=sc.porte))
        ref = run_scenario(Scenario("r", "r", "fechar_mes"), pasta=pasta)
        assert _resultado(e)[0] == _resultado(ref)[-1], nome
        assert e.hash == run_scenario(nome).hash, nome
    fontes = {r["fonte"] for r in e.audit.records if r["kind"] == "mcp_call"}
    assert "mcp://mcp-excel/ler_aba#Lancamentos" in fontes


def test_mcp_client_talks_to_the_excel_server_over_stdio(tmp_path):
    """TEST-258: cliente MCP real (initialize, tools/list, tools/call, erro de tool) contra o servidor embutido."""
    planilha.gerar_modelo(tmp_path / "f.xlsx", exemplo=Dataset(seed=3, porte="pequena"))
    with ClienteMCP(comando_excel(tmp_path)) as c:
        assert {t["name"] for t in c.tools()} >= {"ler_aba", "listar_planilhas", "validar_planilha"}
        assert c.tool("validar_planilha", {"arquivo": "f.xlsx"})["ok"] is True
        with pytest.raises(RespostaInvalida):
            c.tool("ler_aba", {"arquivo": "../fora.xlsx", "aba": "Pessoas"})
    diag = ConectorMCP("m", {"comando": [sys.executable, "-c", "import sys; sys.exit(0)"], "tempo_limite": 3}).testar()
    assert diag["ok"] is False


def test_optional_llm_only_suggests_and_goes_through_the_same_validation(tmp_path):
    """TEST-259: LLM (mock) desligado por padrão; ligado, sugere só campos pendentes, envia só nomes e tipos, e as
    sugestões inválidas (campo inexistente, outro recurso) são rejeitadas com o motivo; externo sem consentimento
    não envia nada."""
    ds = Dataset(seed=7, porte="pequena")
    arquivo = gerar_planilha_fora_do_modelo(tmp_path / "casa.xlsx", ds)
    est = entendimento.de_planilha(arquivo)
    sug = entendimento.sugerir_mapeamento(est)
    r = entendimento.sugerir_com_llm(est, sug, {"provedor": "mock", "modelo": "mock-mapeador"})
    assert {x["motivo"].split(":")[0] for x in r["rejeitadas"]} >= {"campo canônico inexistente"}
    assert all(x["confianca"] < 0.5 and x["fonte_sugestao"] == "llm" for x in r["aceitas"])
    assert ds.lancamentos[0]["fornecedor"] not in r["enviado"] and "Credor" in r["enviado"]
    externo = entendimento.sugerir_com_llm(est, sug, {"provedor": "openai", "modelo": "qualquer"})
    assert externo["enviado"] is None and "sem consentimento" in externo["erro"]


def test_cli_understands_tests_and_serves_the_demo_erp(tmp_path):
    """TEST-260: `fontes entender` (xlsx e JSON), `erp-demo` por subprocesso e `fontes testar` com o token por
    variável de ambiente (que não aparece na saída)."""
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
    arquivo = gerar_planilha_fora_do_modelo(tmp_path / "casa.xlsx", Dataset(seed=7, porte="pequena"))
    saida = subprocess.run([sys.executable, "-m", "fin_mas", "fontes", "entender", str(arquivo), "--json"],
                           capture_output=True, text=True, env=env, timeout=120, check=True).stdout
    r = json.loads(saida)
    assert r["sugestao"]["mapeamento"]["abas"]["Lancamentos"]["recurso"] == "Lançamentos contábeis"
    contrato = tmp_path / "contrato.json"
    contrato.write_text(json.dumps(openapi()), encoding="utf-8")
    texto = subprocess.run([sys.executable, "-m", "fin_mas", "fontes", "entender", str(contrato)], capture_output=True,
                           text=True, env=env, timeout=120, check=True).stdout
    assert "Lancamentos.valor" in texto and "amount" in texto
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    token = "tok-cli-ABCDEFGHIJKLMNOP"
    erp = subprocess.Popen([sys.executable, "-m", "fin_mas", "erp-demo", "--porta", str(porta), "--token", token],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    try:
        assert "ERP de demonstração em" in erp.stdout.readline()
        teste = subprocess.run([sys.executable, "-m", "fin_mas", "fontes", "testar", f"http://127.0.0.1:{porta}",
                                "--token-env", "ERP_TOKEN"], capture_output=True, text=True, timeout=120,
                               env={**env, "ERP_TOKEN": token})
        assert teste.returncode == 0, teste.stdout + teste.stderr
        assert "[ok] contrato" in teste.stdout and "[ok] recurso journal-entries" in teste.stdout
        assert token not in teste.stdout + teste.stderr
        ruim = subprocess.run([sys.executable, "-m", "fin_mas", "fontes", "testar", f"http://127.0.0.1:{porta}",
                               "--token-env", "ERP_TOKEN"], capture_output=True, text=True, timeout=120,
                              env={**env, "ERP_TOKEN": "errado-0123456789"})
        assert ruim.returncode == 1 and "credencial recusada" in ruim.stdout
    finally:
        erp.terminate()
        erp.wait(timeout=10)

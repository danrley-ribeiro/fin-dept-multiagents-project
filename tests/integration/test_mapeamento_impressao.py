"""Mapeamento confirmado só vale para a fonte que a pessoa viu (correção simulada da DSM4, M4).

Servidor do dashboard e ERP de demonstração reais, em loopback. Antes da correção, depois de confirmado o mapeamento,
o ERP podia renomear a coluna mapeada ou passar a mandar centavos em vez de reais e a ativação seguia, lendo dado
errado (lançamento estornado ativo; valores 100 vezes maiores). Agora a confirmação guarda a impressão digital da
fonte; divergiu, a fonte volta a "a confirmar" e a ativação (ou o reinício) falha com o motivo.
"""
import copy

import pytest

from test_dashboard_fontes import _esperar, entrar, painel  # noqa: F401 (fixture)

pytestmark = pytest.mark.integracao


def _confirmar(op):
    status, ent = op.post("/api/fontes/entender", {"id": "erp-demo", "competencia": "2026-09"})
    assert status == 200, ent
    linhas = [s for s in ent["sugestao"]["sugestoes"] if s["aba"] != "Historico"]
    for s in linhas:
        if (s["aba"], s["campo"]) == ("Empresa", "porte"):
            s.update(origem=None, valor="media")
    status, conf = op.post("/api/fontes/confirmar", {"id": "erp-demo", "sugestoes": linhas})
    assert status == 200, conf
    return conf


def _situacao(op):
    return next(c for c in op.get("/api/fontes")[1]["conectores"] if c["id"] == "erp-demo")["mapeamento"]


def test_confirmed_mapping_stops_counting_when_the_source_renames_a_column_or_changes_the_unit(painel):  # noqa: F811
    sim, acesso, porta, url, erp, _ = painel
    fase = {"valor": "como confirmada"}
    original = erp.recurso

    def recurso(rota, q):  # o ERP muda depois da confirmação, sem ninguém entender e confirmar de novo
        dados = copy.deepcopy(original(rota, q))
        if rota == "/journal-entries":
            for x in dados["data"]:
                if fase["valor"] == "centavos":
                    x["amount"] = int(round(x["amount"] * 100))
                if fase["valor"] == "renomeada":
                    x["state"] = x.pop("status")
        return dados
    erp.recurso = recurso
    op = entrar(porta, "operador")
    assert op.post("/api/fontes/conectores", {"id": "erp-demo", "nome": "ERP", "tipo": "rest",
                                              "config": {"url_base": url, "openapi": "/openapi.json",
                                                         "autenticacao": {"tipo": "bearer"}},
                                              "credencial": "tok-erp-NAO-PODE-VAZAR-987654321"})[0] == 200
    _confirmar(op)
    assert op.post("/api/fontes/ativar", {"id": "erp-demo"})[0] == 202  # a mesma fonte: vale
    _esperar(sim, lambda: sim.fonte == "conector")

    # unidade trocada (reais -> centavos): falha explícita, a fonte volta a "a confirmar"
    fase["valor"] = "centavos"
    status, dados = op.post("/api/fontes/ativar", {"id": "erp-demo"})
    assert status == 409 and "escala mudou" in dados["erro"] and "amount" in dados["erro"], dados
    situacao = _situacao(op)
    assert situacao["situacao"].startswith("a confirmar") and any("amount" in m for m in situacao["motivos"])
    assert op.post("/api/fontes/ativar", {"id": "erp-demo"})[0] == 409  # sem nova confirmação, nada se ativa
    invalidado = [r for r in acesso.trilha.ler() if r["evento"] == "mapeamento_invalidado"]
    assert invalidado and invalidado[-1]["resultado"] == "negado" and invalidado[-1]["regra"] == "ADR-011"

    # a pessoa entende e confirma de novo a fonte como ela está agora: volta a valer
    _confirmar(op)
    assert _situacao(op)["situacao"] == "confirmado"
    assert op.post("/api/fontes/ativar", {"id": "erp-demo"})[0] == 202
    _esperar(sim, lambda: sim.fonte == "conector")
    geracao = sim.geracao

    # coluna renomeada depois da ativação: o reinício seguinte relê a fonte e não monta com o mapeamento velho
    fase["valor"] = "renomeada"
    assert op.post("/api/comando", {"tipo": "reiniciar", "cenario": "fechar_mes", "fonte": "conector"})[0] == 202
    sim.processar_comandos()
    assert sim.geracao == geracao  # a simulação ficou como estava; nada foi lido com o mapeamento de outra fonte
    situacao = _situacao(op)
    assert situacao["situacao"].startswith("a confirmar") and any("colunas mudaram" in m for m in situacao["motivos"])
    status, dados = op.post("/api/fontes/ativar", {"id": "erp-demo"})
    assert status == 409 and "confirm" in dados["erro"]

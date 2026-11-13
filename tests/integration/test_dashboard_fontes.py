"""Aba Fontes de dados pelo HTTP real (ADR-011): servidor do dashboard em loopback, contas reais, ERP de
demonstração em loopback, planilhas reais. Credencial nunca volta; host externo só com o administrador."""
import base64
import http.client
import json
import threading
import time

import pytest

from fin_mas.conectores.cenarios import gerar_planilha_fora_do_modelo
from fin_mas.conectores.erp_demo import ErpDemo
from fin_mas.env.dataset import Dataset
from fin_mas.fontes import planilha
from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor
from fin_mas.services.iam import SENHA_DEMO, criar_demo

pytestmark = pytest.mark.integracao
TOKEN = "tok-erp-NAO-PODE-VAZAR-987654321"


class Cliente:
    def __init__(self, porta):
        self.porta, self.cookie, self.csrf = porta, None, None

    def pedir(self, metodo, caminho, corpo=None):
        con = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=30)
        h = {"Cookie": self.cookie} if self.cookie else {}
        if metodo == "POST" and self.csrf:
            h["X-SMA-Token"] = self.csrf
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode() if corpo is not None else None
        con.request(metodo, caminho, body=dados, headers=h)
        r = con.getresponse()
        bruto = r.read()
        cab = dict(r.getheaders())
        con.close()
        self.bruto = bruto.decode("utf-8", "replace")
        try:
            return r.status, json.loads(bruto or b"null"), cab
        except ValueError:
            return r.status, bruto, cab

    def get(self, caminho):
        return self.pedir("GET", caminho)[:2]

    def post(self, caminho, corpo=None):
        return self.pedir("POST", caminho, {} if corpo is None else corpo)[:2]


def entrar(porta, usuario):
    c = Cliente(porta)
    status, dados, cab = c.pedir("POST", "/api/login", {"usuario": usuario, "senha": SENHA_DEMO})
    assert status == 200
    c.cookie, c.csrf = cab["Set-Cookie"].split(";")[0], dados["csrf"]
    return c


@pytest.fixture
def painel(tmp_path):
    acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
    sim = Simulacao("fechar_mes", interativo=True, ms_por_tick=0, pausado=True, acesso=acesso,
                    pasta_dados=str(tmp_path / "dados"))
    servidor = criar_servidor(sim, porta=0, acesso=acesso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    erp = ErpDemo(42, plantar=("alcada",), token=TOKEN)
    url = erp.iniciar()
    yield sim, acesso, servidor.server_address[1], url, erp, tmp_path
    erp.parar()
    servidor.shutdown()
    servidor.server_close()
    sim.parar()


def _esperar(sim, condicao, limite=20000):
    for _ in range(limite):
        sim.processar_comandos()
        if condicao():
            return
        if not sim.passo():
            sim.processar_comandos()
            if condicao():
                return
    raise AssertionError("a condição não chegou")


def test_sources_flow_register_test_understand_adjust_confirm_activate_and_close(painel):
    """TEST-261: operador cadastra o ERP de demonstração (token no cofre), testa, entende, ajusta uma linha, confirma
    e ativa; a simulação reinicia sobre o conector e o fechamento é publicado. A credencial nunca aparece em
    resposta, trace, trilha nem no arquivo do cofre."""
    sim, acesso, porta, url, erp, base = painel
    op = entrar(porta, "operador")
    status, r = op.post("/api/fontes/conectores", {"id": "erp-demo", "nome": "ERP de demonstração", "tipo": "rest",
                                                   "config": {"url_base": url, "openapi": "/openapi.json",
                                                              "autenticacao": {"tipo": "bearer"}},
                                                   "credencial": TOKEN})
    assert status == 200 and r["conector"]["tem_credencial"] and r["conector"]["credencial_vinculada"]
    respostas = [op.bruto]
    status, diag = op.post("/api/fontes/testar", {"id": "erp-demo"})
    respostas.append(op.bruto)
    assert status == 200 and diag["ok"], diag
    status, ent = op.post("/api/fontes/entender", {"id": "erp-demo", "competencia": "2026-09"})
    respostas.append(op.bruto)
    assert status == 200 and ent["qualidade"]["ok"]
    linhas = ent["sugestao"]["sugestoes"]
    assert all(s["motivo"] for s in linhas)
    # ajuste manual: a pessoa não quer o histórico e informa o porte como constante
    linhas = [s for s in linhas if s["aba"] != "Historico"]
    for s in linhas:
        if (s["aba"], s["campo"]) == ("Empresa", "porte"):
            s.update(origem=None, valor="media")
    status, conf = op.post("/api/fontes/confirmar", {"id": "erp-demo", "sugestoes": linhas})
    assert status == 200 and conf["por"] == "operador" and "Historico" not in conf["abas"], conf
    status, lista = op.get("/api/fontes")
    respostas.append(op.bruto)
    c = next(x for x in lista["conectores"] if x["id"] == "erp-demo")
    assert c["mapeamento"]["situacao"] == "confirmado" and c["mapeamento"]["por"] == "operador"
    assert op.post("/api/fontes/ativar", {"id": "erp-demo"})[0] == 202
    _esperar(sim, lambda: sim.fonte == "conector")
    assert sim.controle()["fonte"] == "conector" and sim.cenario.nome == "fechar_mes"
    _esperar(sim, lambda: sim.sistema.aprovador.pendentes)  # alçada vetada: a pessoa decide
    apr = entrar(porta, "controller")
    assert apr.post("/api/comando", {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "corrigir",
                                     "justificativa": "reaprovar por quem tem alçada"})[0] == 202
    _esperar(sim, lambda: sim.sistema.usuario.resposta("SOL-001") is not None)
    assert sim.sistema.usuario.resposta("SOL-001").performative == "inform"
    assert [e["action"] for e in erp.escritas] == ["reapprove"]  # a correção aprovada chegou ao ERP
    trace = json.dumps(list(sim.registros), ensure_ascii=False, default=str)
    trilha = json.dumps(acesso.trilha.ler(), ensure_ascii=False, default=str)
    for texto in (*respostas, trace, trilha, (base / "fontes" / "cofre.json").read_text(encoding="utf-8"),
                  (base / "fontes" / "fontes.json").read_text(encoding="utf-8")):
        assert TOKEN not in texto
    eventos = [r["evento"] for r in acesso.trilha.ler()]
    for e in ("credencial_guardada", "conector_cadastrado", "conector_testado", "fonte_entendida",
              "mapeamento_confirmado", "fonte_ativada"):
        assert e in eventos, e


def test_sources_permissions_external_host_and_body_validation(painel):
    """TEST-262: auditor não cadastra (403); corpo que não é objeto JSON é 400; host externo fica bloqueado até um
    administrador liberar (o operador não pode); a liberação vai para a trilha; trocar a URL desvincula a credencial."""
    sim, acesso, porta, url, erp, _ = painel
    aud = entrar(porta, "auditor")
    assert aud.get("/api/fontes")[0] == 200
    assert aud.post("/api/fontes/conectores", {"id": "x", "tipo": "rest", "config": {}})[0] == 403
    op = entrar(porta, "operador")
    assert op.pedir("POST", "/api/fontes/conectores", b"[1, 2]")[0] == 400
    assert op.pedir("POST", "/api/fontes/testar", b"{nao-json")[0] == 400
    assert op.post("/api/fontes/conectores", {"id": "ext", "tipo": "rest", "credencial": "tok-ext-1234567890ab",
                                              "config": {"url_base": "https://erp.exemplo.com.br",
                                                         "openapi": "/openapi.json",
                                                         "autenticacao": {"tipo": "bearer"}}})[0] == 200
    status, diag = op.post("/api/fontes/testar", {"id": "ext"})
    assert status == 200 and not diag["ok"] and "PERM-DAD-REDE" in diag["etapas"][0]["detalhe"]
    assert op.post("/api/fontes/rede", {"host": "erp.exemplo.com.br"})[0] == 403
    adm = entrar(porta, "admin")
    assert adm.post("/api/fontes/rede", {"host": "127.0.0.1"})[0] == 400  # loopback já é permitido
    assert adm.post("/api/fontes/rede", {"host": "erp.exemplo.com.br"})[0] == 200
    lista = op.get("/api/fontes")[1]
    assert next(c for c in lista["conectores"] if c["id"] == "ext")["rede"] == "liberado por administrador"
    status, diag = op.post("/api/fontes/testar", {"id": "ext"})
    assert diag["etapas"][0]["ok"] and "rede indisponível" in json.dumps(diag, ensure_ascii=False)  # offline nos testes
    assert any(r["evento"] == "rede_liberada" and r["ator"] == "admin" for r in acesso.trilha.ler())
    # credencial vinculada ao host do cadastro: trocar a URL sem informar a credencial a desvincula
    op.post("/api/fontes/conectores", {"id": "ext", "tipo": "rest", "config": {
        "url_base": url, "autenticacao": {"tipo": "bearer"}, "openapi": "/openapi.json"}})
    c = next(c for c in op.get("/api/fontes")[1]["conectores"] if c["id"] == "ext")
    assert c["tem_credencial"] and not c["credencial_vinculada"]
    status, diag = op.post("/api/fontes/testar", {"id": "ext"})
    assert not diag["ok"] and any(e["etapa"] == "credencial" for e in diag["etapas"])
    assert op.post("/api/fontes/ativar", {"id": "ext"})[0] == 409  # sem mapeamento confirmado
    assert op.post("/api/fontes/confirmar", {"id": "ext", "sugestoes": []})[0] == 409  # sem entendimento


def test_spreadsheet_uploads_history_and_off_model_activation(painel):
    """TEST-263: envio de planilha do modelo (vira a competência na pasta) e de uma fora do modelo (vira fonte para
    entender); histórico de envios; a fora do modelo é entendida, confirmada e ativada; o fechamento é publicado."""
    sim, acesso, porta, _, _, base = painel
    op = entrar(porta, "operador")
    planilha.gerar_modelo(base / "modelo.xlsx", exemplo=Dataset(seed=7, porte="micro"))
    gerar_planilha_fora_do_modelo(base / "casa.xlsx", Dataset(seed=7, porte="pequena"))
    envio = lambda nome: op.post("/api/fontes/envios", {"nome": nome, "conteudo_base64": base64.b64encode(  # noqa: E731
        (base / nome).read_bytes()).decode()})
    status, r = envio("modelo.xlsx")
    assert status == 200 and r["modelo"] and r["competencia"] == "2026-09" and r["conector"] == "planilhas"
    status, r = envio("casa.xlsx")
    assert status == 200 and not r["modelo"] and r["conector"] == "planilha-casa"
    assert op.post("/api/fontes/envios", {"nome": "x.xlsx", "conteudo_base64": base64.b64encode(b"lixo").decode()})[0] == 422
    lista = op.get("/api/fontes")[1]
    assert [e["arquivo"] for e in lista["envios"]][:3] == ["x.xlsx", "casa.xlsx", "modelo.xlsx"]
    assert {"planilhas", "planilha-casa"} <= {c["id"] for c in lista["conectores"]}
    status, ent = op.post("/api/fontes/entender", {"id": "planilha-casa"})
    assert status == 200 and ent["competencia"] == "2026-09"
    assert op.post("/api/fontes/confirmar", {"id": "planilha-casa", "sugestoes": ent["sugestao"]["sugestoes"]})[0] == 200
    assert op.post("/api/fontes/ativar", {"id": "planilha-casa"})[0] == 202
    _esperar(sim, lambda: sim.fonte == "conector" and sim.sistema.usuario.resposta("SOL-001") is not None)
    assert sim.sistema.usuario.resposta("SOL-001").performative == "inform"
    assert sim.registros[0]["conector"]["tipo"] == "planilha"
    # voltar ao ERP simulado
    assert op.post("/api/fontes/ativar", {"id": "erp-simulado"})[0] == 202
    _esperar(sim, lambda: sim.fonte == "sintetico")

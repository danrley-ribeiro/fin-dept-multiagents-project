"""Fluxo de eventos ao vivo (SSE) sob o controle de acesso (correção simulada da DSM4, M5).

Servidor HTTP real em loopback e cadastro real em arquivo selado; o relógio do SVC-IAM é adiantado. Antes da
correção, o fluxo conferia só se a sessão existia, e essa conferência contava como uso: com o dashboard aberto a
sessão nunca caía por inatividade, e quem perdia a empresa ou a permissão seguia recebendo o trace.
"""
import http.client
import json
import threading
import time

import pytest

from fin_mas.services.iam import INATIVIDADE_S, SENHA_DEMO
from test_dashboard_acesso_avancado import entrar, servico  # noqa: F401 (fixture)

pytestmark = pytest.mark.integracao


class Fluxo:
    """GET /api/eventos lido numa thread: guarda cada evento e o fim do fluxo."""

    def __init__(self, porta, cookie):
        self.eventos, self.fim = [], threading.Event()
        self.con = http.client.HTTPConnection("127.0.0.1", porta, timeout=60)
        self.con.request("GET", "/api/eventos", headers={"Cookie": cookie})
        self.resposta = self.con.getresponse()
        assert self.resposta.status == 200
        threading.Thread(target=self._ler, daemon=True).start()

    def _ler(self):
        try:
            while linha := self.resposta.fp.readline():
                if linha.startswith(b"data: "):
                    self.eventos.append(json.loads(linha[6:]))
        except (OSError, ValueError):
            pass
        self.fim.set()

    def encerrado(self, limite=15.0) -> dict | None:
        """O último evento, se o servidor fechou o fluxo dentro do limite; None se continuou aberto."""
        if not self.fim.wait(limite):
            return None
        return self.eventos[-1] if self.eventos else {}

    def fechar(self):
        self.con.close()


def test_open_dashboard_does_not_keep_an_idle_session_alive(servico):  # noqa: F811
    _, acesso, porta, _ = servico()
    salto = [0.0]
    acesso.relogio = lambda: time.time() + salto[0]
    auditor = entrar(porta, "auditor")
    fluxo = Fluxo(porta, auditor.cookie)
    # o dashboard fica aberto: fluxo de eventos e releituras automáticas, mas ninguém mexe
    for passo in range(4):  # 4 x (225 + 5) s: passa dos 15 min no quarto passo
        salto[0] += INATIVIDADE_S / 4 + 5
        assert auditor.get("/api/estado", **{"X-SMA-Automatico": "1"})[0] == (200 if passo < 3 else 401)
        time.sleep(2.5)  # pelo menos uma conferência do fluxo a cada passo
    ultimo = fluxo.encerrado()
    assert ultimo == {"tipo": "sessao_encerrada"}, "o fluxo tem de fechar quando a sessão cai por inatividade"
    assert auditor.get("/api/sessao")[0] == 401
    fluxo.fechar()
    # controle: quem usa de verdade (requisição sem a marca de automática) continua dentro
    ativo = entrar(porta, "auditor")
    for _ in range(4):
        salto[0] += INATIVIDADE_S / 4 + 5
        assert ativo.get("/api/estado")[0] == 200
    assert ativo.get("/api/sessao")[0] == 200
    encerrados = [r for r in acesso.trilha.ler() if r["evento"] == "eventos_encerrados"]
    assert encerrados and encerrados[-1]["regra"] == "IAM-04" and encerrados[-1]["resultado"] == "negado"


def test_stream_closes_when_the_account_loses_the_company_or_the_permission(servico):  # noqa: F811
    sim, acesso, porta, servidor = servico(fabrica=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "alfa", "Alfa S.A.", "media")
    acesso.definir_escopo(admin, "elisa", ["alfa"])
    acesso.definir_escopo(admin, "bruno", ["alfa"])
    elisa, bruno = entrar(porta, "elisa"), entrar(porta, "bruno")
    fluxo_elisa, fluxo_bruno = Fluxo(porta, elisa.cookie), Fluxo(porta, bruno.cookie)
    assert fluxo_elisa.encerrado(3) is None and fluxo_bruno.encerrado(0.1) is None  # tudo certo: segue aberto
    acesso.definir_escopo(admin, "elisa", [])  # elisa perde a empresa
    acesso.atribuir_papeis(admin, "bruno", [])  # bruno perde a permissão de ver a simulação
    ultimo = fluxo_elisa.encerrado()
    assert ultimo is not None and ultimo["tipo"] == "fluxo_encerrado" and ultimo["regra"] == "IAM-09", ultimo
    ultimo = fluxo_bruno.encerrado()
    assert ultimo is not None and ultimo["tipo"] == "fluxo_encerrado" and ultimo["regra"] == "IAM-05", ultimo
    # e o que o fluxo entregava não volta por outro caminho
    assert elisa.get("/api/eventos")[0] == 403 and bruno.get("/api/eventos")[0] == 403
    regras = {(r["ator"], r["regra"]) for r in acesso.trilha.ler() if r["evento"] == "eventos_encerrados"}
    assert {("elisa", "IAM-09"), ("bruno", "IAM-05")} <= regras
    for f in (fluxo_elisa, fluxo_bruno):
        f.fechar()

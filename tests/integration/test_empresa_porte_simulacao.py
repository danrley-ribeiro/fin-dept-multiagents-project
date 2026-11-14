"""Simulação de cada empresa (correção simulada da DSM4, M6 e M7), pelo servidor HTTP real em loopback.

- M6: o porte (e o segmento) cadastrados da empresa definem alçadas e dupla aprovação da simulação dela; quem só opera a
  simulação (PERM-SIM-OPERAR) não troca o porte ao reiniciar; isso é administrar a empresa (PERM-IAM-EMPRESAS);
- M7: requisições simultâneas da mesma empresa criam uma simulação só.
"""
import threading
import time

import pytest

from fin_mas.services.iam import SENHA_DEMO
from test_dashboard_acesso_avancado import entrar, servico  # noqa: F401 (fixture)

pytestmark = pytest.mark.integracao


def test_company_size_comes_from_the_registry_and_an_operator_cannot_change_it(servico):  # noqa: F811
    _, acesso, porta, servidor = servico(fabrica=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "grandeco", "Grande Co", "grande", segmento="comercio")
    acesso.definir_escopo(admin, "operador", ["grandeco"])
    op = entrar(porta, "operador")
    status, portes = op.get("/api/portes")
    assert status == 200 and portes["atual"] == "grande" and portes["segmento_atual"] == "comercio"
    sim = servidor.simulacoes.por_empresa["grandeco"]
    assert sim.sistema.politica is not None and sim.porte == "grande"
    # trocar porte ou segmento ao reiniciar é administrar a empresa: o operador não pode
    for troca in ({"porte": "pequena"}, {"segmento": "industria"}):
        negado = op.post("/api/comando", {"tipo": "reiniciar", "cenario": "dupla_aprovacao", **troca})
        assert negado[0] == 403 and "PERM-IAM-EMPRESAS" in negado[1]["erro"], negado
    # reiniciar sem dizer o porte (ou com o mesmo) mantém o da empresa
    assert op.post("/api/comando", {"tipo": "reiniciar", "cenario": "dupla_aprovacao"})[0] == 202
    assert op.post("/api/comando", {"tipo": "reiniciar", "cenario": "dupla_aprovacao", "porte": "grande"})[0] == 202
    sim.processar_comandos()
    assert sim.porte == "grande" and op.get("/api/portes")[1]["atual"] == "grande"
    negados = [r for r in acesso.trilha.ler() if r["evento"] == "permissao" and r.get("permissao") == "PERM-IAM-EMPRESAS"]
    assert negados and all(r["ator"] == "operador" and r["resultado"] == "negado" for r in negados)


def test_simultaneous_requests_create_a_single_simulation_per_company(servico):  # noqa: F811
    _, acesso, porta, servidor = servico(fabrica=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "alfa", "Alfa S.A.", "media")
    acesso.definir_escopo(admin, "operador", ["alfa"])
    original, chamadas = servidor.simulacoes.fabrica, []

    def fabrica_lenta(empresa):  # alarga a janela da corrida: a criação demora
        chamadas.append(empresa)
        time.sleep(0.3)
        return original(empresa)
    servidor.simulacoes.fabrica = fabrica_lenta
    op = entrar(porta, "operador")
    respostas = []
    threads = [threading.Thread(target=lambda: respostas.append(op.get("/api/estado")[0])) for _ in range(5)]  # o servidor aceita 5 conexões na fila
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert respostas == [200] * 5
    assert chamadas == ["alfa"], f"a mesma empresa ganhou {len(chamadas)} simulações"

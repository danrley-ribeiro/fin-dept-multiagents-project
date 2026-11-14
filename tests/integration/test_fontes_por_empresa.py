"""Fontes de dados por empresa (correção simulada da DSM4, C4): registro, planilhas e credenciais não cruzam empresas.

Servidor HTTP real em loopback, uma simulação por empresa (IAM-09). Antes da correção o registro de fontes era um só
para todas as empresas: o operador de uma empresa ativava a planilha da outra e removia o conector alheio.
"""
import base64

import pytest

from fin_mas.env.dataset import Dataset
from fin_mas.fontes import planilha
from fin_mas.services.iam import SENHA_DEMO
from test_dashboard_acesso_avancado import entrar, servico  # noqa: F401 (fixture)

pytestmark = pytest.mark.integracao


def _xlsx(tmp_path, nome) -> str:
    caminho = planilha.gerar_modelo(tmp_path / nome, exemplo=Dataset(seed=42, porte="media", plantar=("competencia",)))
    return base64.b64encode(caminho.read_bytes()).decode()


def test_sources_of_one_company_cannot_be_listed_activated_removed_downloaded_or_overwritten_by_another(
        servico, tmp_path):  # noqa: F811
    sim, acesso, porta, servidor = servico(fabrica=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "alfa", "Alfa S.A.", "media")
    acesso.criar_empresa(admin, "beta", "Beta Ltda", "media")
    acesso.definir_escopo(admin, "operador", ["alfa"])
    acesso.definir_escopo(admin, "avaliador", ["beta"])
    alfa, beta = entrar(porta, "operador"), entrar(porta, "avaliador")
    assert alfa.get("/api/empresa")[1]["ativa"] == "alfa" and beta.get("/api/empresa")[1]["ativa"] == "beta"

    # enviar: a planilha de alfa fica na pasta de alfa
    status, enviada = alfa.post("/api/fontes/envios", {"nome": "razao_alfa.xlsx", "conteudo_base64": _xlsx(tmp_path, "a.xlsx")})
    assert status == 200 and enviada["ok"] and enviada["conector"] == "planilhas"
    status, conector = alfa.post("/api/fontes/conectores", {"id": "erp-alfa", "nome": "ERP Alfa", "tipo": "rest",
                                                            "config": {"url_base": "http://127.0.0.1:9"},
                                                            "credencial": "tok-ALFA-secreto"})
    assert status == 200 and conector["conector"]["tem_credencial"] is True
    assert list((tmp_path / "dados" / "alfa" / "fontes" / "planilhas").glob("*.xlsx"))
    assert not list((tmp_path / "dados" / "beta" / "fontes" / "planilhas").glob("*.xlsx"))

    # listar: beta não vê nada de alfa (nem conectores nem envios)
    status, lista = beta.get("/api/fontes")
    assert status == 200 and [c["id"] for c in lista["conectores"]] == ["erp-simulado"] and lista["envios"] == []
    # ativar e remover: o que é de alfa não existe para beta
    assert beta.post("/api/fontes/ativar", {"id": "planilhas"})[0] == 404
    assert beta.post("/api/fontes/ativar", {"id": "erp-alfa"})[0] == 404
    assert beta.post("/api/fontes/remover", {"id": "erp-alfa"})[0] == 404
    testado = beta.post("/api/fontes/testar", {"id": "erp-alfa"})[1]
    assert testado["ok"] is False and "conector desconhecido" in str(testado)
    # baixar: a situação dos dados de beta não traz a planilha de alfa
    assert beta.get("/api/dados")[1].get("planilha") is None
    # mesmo id em beta: credencial própria, com a empresa no nome; a de alfa continua a mesma
    status, _ = beta.post("/api/fontes/conectores", {"id": "erp-alfa", "nome": "homônimo", "tipo": "rest",
                                                     "config": {"url_base": "http://127.0.0.1:9"},
                                                     "credencial": "tok-BETA"})
    assert status == 200
    reg_alfa = servidor.simulacoes.por_empresa["alfa"].registro_fontes
    reg_beta = servidor.simulacoes.por_empresa["beta"].registro_fontes
    assert reg_alfa.pasta != reg_beta.pasta and reg_alfa.cofre.caminho != reg_beta.cofre.caminho
    assert reg_alfa.cofre.ler("conector:erp-alfa@alfa") == "tok-ALFA-secreto"
    assert reg_beta.cofre.ler("conector:erp-alfa@beta") == "tok-BETA" and reg_beta.cofre.ler("conector:erp-alfa@alfa") is None
    assert beta.post("/api/fontes/remover", {"id": "erp-alfa"})[0] == 200  # remove só o seu
    lista_alfa = {c["id"]: c for c in alfa.get("/api/fontes")[1]["conectores"]}
    assert set(lista_alfa) == {"erp-simulado", "planilhas", "erp-alfa"} and lista_alfa["erp-alfa"]["tem_credencial"]
    assert alfa.post("/api/fontes/ativar", {"id": "planilhas"})[0] == 202  # e alfa ainda ativa a sua planilha
    # a trilha diz de que empresa era cada ação de fontes
    fontes = [r for r in acesso.trilha.ler() if r["evento"] in ("planilha_recebida", "conector_cadastrado",
                                                                "conector_removido", "fonte_ativada")]
    assert fontes and all(r.get("empresa") in ("alfa", "beta") for r in fontes)
    assert {(r["ator"], r["empresa"]) for r in fontes if r["evento"] == "conector_removido"} == {("avaliador", "beta")}

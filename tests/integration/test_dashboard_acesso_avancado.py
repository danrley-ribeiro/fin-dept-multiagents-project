"""Acesso avançado no dashboard (DSM4, ADR-012): servidor HTTP real em loopback, cadastro real em arquivo selado.

Login em dois passos (IAM-08), política do cadastro, cofre (IAM-10) e empresas (IAM-09), falando
com o servidor por HTTP como o navegador: cookie de sessão, token CSRF, cookie da pré-sessão.
"""
import threading
import time

import pytest

from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor
from fin_mas.services import totp
from fin_mas.services.iam import SENHA_DEMO, Acesso, criar_demo
from test_dashboard_acesso import Navegador

pytestmark = pytest.mark.integracao


@pytest.fixture
def servico(tmp_path, monkeypatch):
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(tmp_path / "chaves"))
    criados = []

    def criar(fabrica=False):
        acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
        sim = Simulacao("fechar_mes", interativo=True, ms_por_tick=0, pausado=True, acesso=acesso)

        def nova(empresa):
            outra = Simulacao("fechar_mes", interativo=True, ms_por_tick=0, pausado=True, acesso=acesso,
                              empresa=empresa, pasta_dados=str(tmp_path / "dados" / empresa),
                              memoria=str(tmp_path / "dados" / empresa / "memoria.json"))
            criados.append((outra, None))
            return outra
        servidor = criar_servidor(sim, porta=0, acesso=acesso, fabrica=nova if fabrica else None)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        criados.append((sim, servidor))
        return sim, acesso, servidor.server_address[1], servidor
    yield criar
    for sim, servidor in criados:
        if servidor is not None:
            servidor.shutdown()
            servidor.server_close()
        sim.parar()


def entrar(porta, usuario):
    n = Navegador(porta)
    assert n.login(usuario)[0] == 200
    return n


def ativar_2fa(n) -> tuple[str, list]:
    status, info = n.post("/api/2fa/ativar")
    assert status == 200 and info["uri"].startswith("otpauth://")
    status, confirmado = n.post("/api/2fa/confirmar", {"codigo": totp.codigo(info["segredo"], time.time())})
    assert status == 200
    return info["segredo"], confirmado["codigos_recuperacao"]


def test_two_step_login_with_short_lived_pre_session(servico):
    _, acesso, porta, _ = servico()
    carla = entrar(porta, "carla")
    segredo, codigos = ativar_2fa(carla)
    assert carla.post("/api/logout")[0] == 200
    n = Navegador(porta)
    status, dados = n.pedir("POST", "/api/login", {"usuario": "carla", "senha": SENHA_DEMO})
    assert status == 200 and dados["segundo_fator"] == "pendente" and "csrf" not in dados
    pre = n.ultimos_cabecalhos["set-cookie"]
    assert pre.startswith("sma_pre2fa=") and "Path=/api/login/2fa" in pre and "HttpOnly" in pre and "Max-Age=300" in pre
    desafio = pre.split(";")[0].split("=", 1)[1]
    # a pré-sessão não abre nenhuma rota comum, nem posta como se fosse a sessão
    assert n.get("/api/estado", Cookie=f"sma_sessao={desafio}")[0] == 401
    assert n.get("/api/sessao", Cookie=f"sma_sessao={desafio}")[0] == 401
    cookie_pre = {"Cookie": f"sma_pre2fa={desafio}"}
    assert n.post("/api/login/2fa", [1, 2], **cookie_pre)[0] == 400  # corpo precisa ser objeto JSON
    assert n.post("/api/login/2fa", {"codigo": 123456}, **cookie_pre)[0] == 400
    errado = n.post("/api/login/2fa", {"codigo": "000000"}, **cookie_pre)
    assert errado[0] == 401 and "IAM-08" in errado[1]["erro"]
    assert n.post("/api/login/2fa", {"codigo": codigos[0]}, Cookie="sma_pre2fa=forjado")[0] == 401
    status, dados = n.post("/api/login/2fa", {"codigo": codigos[0]}, **cookie_pre)
    assert status == 200 and dados["sessao"]["usuario"] == "carla"
    n.cookie, n.csrf = n.ultimos_cabecalhos["set-cookie"].split(";")[0], dados["csrf"]
    assert n.get("/api/estado")[0] == 200
    assert n.post("/api/login/2fa", {"codigo": codigos[1]}, **cookie_pre)[0] == 401  # pré-sessão já consumida
    trilha = [r for r in acesso.trilha.ler() if r.get("regra") == "IAM-08"]
    assert ("entrada", "pendente") in [(r["evento"], r["resultado"]) for r in trilha]
    assert ("segundo_fator", "ok") in [(r["evento"], r["resultado"]) for r in trilha]
    assert segredo not in str(acesso.trilha.ler())


def test_policy_requiring_second_factor_only_lets_the_account_enrol(servico):
    _, acesso, porta, _ = servico()
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.definir_politica(admin, exigir_2fa_para=["ROLE-APR"])
    diego = entrar(porta, "diego")
    assert diego.get("/api/sessao")[1]["sessao"]["pendente_2fa"] is True
    negado = diego.get("/api/estado")
    assert negado[0] == 403 and "IAM-08" in negado[1]["erro"]
    ativar_2fa(diego)
    assert diego.get("/api/estado")[0] == 200
    assert entrar(porta, "operador").get("/api/estado")[0] == 200  # ROLE-OPE fora da exigência


def test_vault_routes_store_llm_keys_without_returning_them(servico):
    _, acesso, porta, _ = servico()
    valor = "sk-cofre-" + "x" * 24
    assert entrar(porta, "operador").post("/api/segredos", {"nome": "llm:OPENAI_API_KEY", "valor": valor})[0] == 403
    admin = entrar(porta, "admin")
    status, dados = admin.post("/api/segredos", {"nome": "llm:OPENAI_API_KEY", "valor": valor})
    assert status == 200 and dados == {"nome": "llm:OPENAI_API_KEY", "existe": True}
    assert admin.post("/api/segredos", {"nome": "totp:admin", "valor": "X"})[0] == 403
    assert admin.post("/api/segredos", "texto")[0] == 400
    status, lista = admin.get("/api/segredos")
    assert status == 200 and [s["nome"] for s in lista["segredos"]] == ["llm:OPENAI_API_KEY"] and valor not in str(lista)
    assert Acesso(acesso.pasta, custo_scrypt=10).cofre.ler("llm:OPENAI_API_KEY") == valor  # quem usa, lê por dentro
    assert admin.post("/api/segredos/remover", {"nome": "llm:OPENAI_API_KEY"})[1]["removido"] is True
    assert admin.get("/api/segredos")[1]["segredos"] == []


def test_each_company_gets_its_own_simulation_and_nothing_crosses_over(servico):
    sim, acesso, porta, servidor = servico(fabrica=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "alfa", "Alfa S.A.", "media")
    acesso.criar_empresa(admin, "beta", "Beta Ltda", "pequena")
    acesso.definir_escopo(admin, "elisa", ["alfa"])
    acesso.definir_escopo(admin, "avaliador", ["alfa", "beta"])
    elisa = entrar(porta, "elisa")  # uma empresa só no escopo: já entra nela
    status, dados = elisa.get("/api/empresa")
    assert status == 200 and dados["ativa"] == "alfa" and [e["id"] for e in dados["empresas"]] == ["alfa"]
    outra = elisa.post("/api/empresa", {"empresa": "beta"})
    assert outra[0] == 403 and "IAM-09" in outra[1]["erro"]
    assert elisa.post("/api/empresa", ["beta"])[0] == 400
    assert elisa.post("/api/comando", {"tipo": "solicitar", "intencao": "avaliar_orcamento"})[0] == 202
    alfa = servidor.simulacoes.por_empresa["alfa"]
    alfa.processar_comandos()
    assert alfa is not sim and alfa.empresa == "alfa" and alfa.sistema.politica.empresa == "alfa"
    avaliador = entrar(porta, "avaliador")  # duas empresas: escolhe antes de usar
    sem_escolha = avaliador.get("/api/estado")
    assert sem_escolha[0] == 403 and "IAM-09" in sem_escolha[1]["erro"]
    assert avaliador.post("/api/empresa", {"empresa": "beta"})[0] == 200
    beta = avaliador.get("/api/solicitacoes")[1]["solicitacoes"]
    assert not [s for s in beta if s.get("solicitado_por") == "elisa"]  # o pedido de alfa não aparece em beta
    assert avaliador.post("/api/empresa", {"empresa": "alfa"})[0] == 200
    em_alfa = avaliador.get("/api/solicitacoes")[1]["solicitacoes"]
    assert [s for s in em_alfa if s.get("solicitado_por") == "elisa"]
    assert servidor.simulacoes.por_empresa["beta"].memoria != alfa.memoria  # memória em dados/<empresa>/
    # quem perde a empresa do escopo perde o acesso na requisição seguinte
    acesso.definir_escopo(admin, "elisa", [])
    assert elisa.get("/api/estado")[0] == 403

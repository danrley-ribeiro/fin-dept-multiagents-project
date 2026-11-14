"""Aprovação e acesso pelo servidor HTTP real (correção simulada da DSM4, M8 e m7).

- M8: a delegação (POL-11) é usada ao vivo pelo comando `decidir`; trocar a senha derruba as outras sessões da conta;
  a rajada de entradas anônimas não segura o cadastro (o scrypt roda fora da trava);
- m7: duas contas da mesma pessoa do ERP não cumprem a dupla aprovação; o aval de conta bloqueada depois deixa de
  valer; veto sem exposição é tratado como acima de qualquer alçada (falha fechada); delegação feita numa empresa não
  vale em outra; preço infinito é recusado; cofre adulterado responde 503 com o motivo; a trilha leva a empresa.
"""
import contextlib
import json
import threading
import time


import pytest

from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor
from fin_mas.services import iam
from fin_mas.services.cofre import caminho_padrao
from fin_mas.services.iam import SENHA_DEMO, criar_demo
from test_dashboard_acesso import Navegador

pytestmark = pytest.mark.integracao
JUST = "liberação analisada e justificada pelo aprovador responsável"


@pytest.fixture
def subir(tmp_path, monkeypatch):
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(tmp_path / "chaves"))
    criados = []

    def criar(cenario, multi=False):
        acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
        sim = Simulacao(cenario, interativo=True, ms_por_tick=0, pausado=True, acesso=acesso)

        def fabrica(empresa):
            outra = Simulacao(cenario, interativo=True, ms_por_tick=0, pausado=True, acesso=acesso, empresa=empresa,
                              pasta_dados=str(tmp_path / "dados" / empresa))
            criados.append((outra, None))
            return outra
        servidor = criar_servidor(sim, porta=0, acesso=acesso, fabrica=fabrica if multi else None)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        criados.append((sim, servidor))
        return sim, acesso, servidor.server_address[1], servidor
    yield criar
    for sim, servidor in criados:
        if servidor is not None:
            servidor.shutdown()
            servidor.server_close()
        sim.parar()


def entrar(porta, usuario, senha=SENHA_DEMO):
    n = Navegador(porta)
    assert n.login(usuario, senha)[0] == 200
    return n


def ate_humano(sim, limite=20000):
    for _ in range(limite):
        sim.processar_comandos()
        if sim.sistema.aprovador.pendentes or not sim.passo():
            return bool(sim.sistema.aprovador.pendentes)
    return False


def ticket(sim):
    return next(iter(sim.sistema.politica.tickets.values()))


def decidir(sim, n, decisao="corrigir", **extra):
    antes = len([r for r in sim.registros if r["kind"] == "rejected"])
    status, _ = n.post("/api/comando", {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": decisao,
                                        "justificativa": JUST, **extra})
    sim.processar_comandos()
    return status, [r["motivo"] for r in sim.registros if r["kind"] == "rejected"][antes:]


def test_delegation_is_usable_live_and_does_not_cross_companies(subir):
    sim, acesso, porta, _ = subir("delegacao_valida")
    diego, _ = acesso.autenticar("diego", SENHA_DEMO)
    d = acesso.delegar(diego, "ana", ate=time.time() + 3600, teto=1_000_000, competencia=sim.sistema.ambiente.principal)
    assert ate_humano(sim)
    ana = entrar(porta, "ana")
    assert ana.post("/api/comando", {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "waiver",
                                     "justificativa": JUST, "delegacao": "qualquer"})[0] == 400  # formato DLG-…
    status, rejeitadas = decidir(sim, ana, "waiver")  # sem a delegação, o cargo de analista não basta
    assert status == 202 and any("POL-02" in m for m in rejeitadas)
    status, rejeitadas = decidir(sim, ana, "waiver", delegacao=d["id"])  # com ela, decide com a alçada de diego
    assert status == 202 and not rejeitadas, rejeitadas
    t = ticket(sim)
    assert t["estado"] == "aprovado" and t["aprovado_por"]["por_delegacao_de"] == "diego"
    assert t["aprovado_por"]["delegacao"] == d["id"]


def test_delegation_made_in_one_company_is_refused_in_another(subir):
    _, acesso, porta, servidor = subir("delegacao_valida", multi=True)
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_empresa(admin, "alfa", "Alfa", "media")
    acesso.criar_empresa(admin, "beta", "Beta", "media")
    acesso.definir_escopo(admin, "diego", ["alfa"])
    acesso.definir_escopo(admin, "ana", ["alfa", "beta"])
    diego, _ = acesso.autenticar("diego", SENHA_DEMO)  # ativa: alfa
    ana = entrar(porta, "ana")
    assert ana.post("/api/empresa", {"empresa": "beta"})[0] == 200 and ana.get("/api/estado")[0] == 200
    beta = servidor.simulacoes.por_empresa["beta"]
    d = acesso.delegar(diego, "ana", ate=time.time() + 3600, teto=1_000_000, competencia=beta.sistema.ambiente.principal)
    assert d["empresa"] == "alfa" and ate_humano(beta)
    status, rejeitadas = decidir(beta, ana, "waiver", delegacao=d["id"])
    assert status == 202 and any("POL-11" in m and "empresa alfa" in m for m in rejeitadas), rejeitadas
    assert ticket(beta)["estado"] == "pendente"
    negadas = [r for r in acesso.trilha.ler() if r["evento"] == "decisao" and r["resultado"] == "negado"]
    assert negadas and negadas[-1]["regra"] == "POL-11" and negadas[-1]["empresa"] == "beta"  # a trilha diz a empresa


def test_double_approval_needs_two_real_people_and_a_still_valid_endorsement(subir, tmp_path):
    sim, acesso, porta, _ = subir("dupla_aprovacao")
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.criar_conta(admin, "diego2", "Diego Rocha (2)", "Outra-Senha-Forte-2026", ["ROLE-APR"], pessoa_erp="diego",
                       cargo="gerente", trocar_senha=False)
    assert ate_humano(sim) and ticket(sim)["dupla"] is True
    diego, diego2, carla = entrar(porta, "diego"), entrar(porta, "diego2", "Outra-Senha-Forte-2026"), entrar(porta, "carla")
    assert decidir(sim, diego) == (202, []) and len(ticket(sim)["endossos"]) == 1  # o aval de diego
    status, rejeitadas = decidir(sim, diego2)  # outra conta, a mesma pessoa do ERP
    assert any("POL-12" in m and "mesma pessoa do ERP" in m for m in rejeitadas), rejeitadas
    acesso.bloquear(admin, "diego")  # quem avalizou é bloqueado depois do aval
    status, rejeitadas = decidir(sim, carla)
    assert any("POL-12" in m and "não vale mais" in m for m in rejeitadas), rejeitadas
    assert ticket(sim)["estado"] == "pendente" and ticket(sim)["endossos"] == []  # precisa de um aval novo
    assert decidir(sim, carla) == (202, []) and len(ticket(sim)["endossos"]) == 1  # carla avaliza
    assert decidir(sim, diego2) == (202, [])  # e diego2 (pessoa diferente de carla) aprova
    assert ticket(sim)["estado"] == "aprovado"
    eventos = {r["evento"] for r in acesso.trilha.ler()}
    assert "aval_invalidado" in eventos


def test_veto_without_exposure_fails_closed(subir):
    sim, acesso, porta, _ = subir("dupla_aprovacao")
    sim.sistema.bus.agents["AG-CIN"].exposicao = lambda *a: None  # o veto chega sem a exposição
    assert ate_humano(sim)
    t = ticket(sim)
    assert t["exposicao"] is None and t["exposicao_invalida"] and t["dupla"] is True
    controller = entrar(porta, "controller")  # a maior alçada do porte
    status, rejeitadas = decidir(sim, controller, "corrigir")
    assert any("POL-10" in m and "falha fechada" in m for m in rejeitadas), rejeitadas
    assert decidir(sim, controller, "bloquear") == (202, []) and ticket(sim)["estado"] == "rejeitado"


def test_password_change_revokes_other_sessions_and_wrong_current_password_counts(subir):
    _, acesso, porta, _ = subir("fechar_mes")
    ladrao, vitima = entrar(porta, "auditor"), entrar(porta, "auditor")
    assert vitima.post("/api/senha", {"atual": SENHA_DEMO, "nova": "Nova-Senha-Forte-2026"})[0] == 200
    assert ladrao.get("/api/estado")[0] == 401 and vitima.get("/api/estado")[0] == 200
    for _ in range(iam.MAX_FALHAS):  # chutar a senha atual pela sessão também conta (IAM-03)
        assert vitima.post("/api/senha", {"atual": "chute-errado-123", "nova": "Outra-Senha-Forte-77"})[0] == 400
    assert Navegador(porta).login("auditor", "Nova-Senha-Forte-2026")[0] == 401  # entrada bloqueada por 15 min
    trocas = [r for r in acesso.trilha.ler() if r["evento"] == "senha_trocada" and r["resultado"] == "ok"]
    assert trocas and trocas[0]["sessoes_revogadas"]


def test_burst_of_anonymous_logins_does_not_hold_the_registry_lock(subir, monkeypatch):
    _, acesso, porta, _ = subir("fechar_mes")
    original, durante, dono = iam._confere_senha, [], threading.local()
    transacao = acesso._contas.transacao

    @contextlib.contextmanager
    def transacao_marcada():  # marca a thread que segura a trava do cadastro de contas
        with transacao() as dados:
            dono.dentro = True
            try:
                yield dados
            finally:
                dono.dentro = False

    def conferir(senha, guardado):  # o scrypt nunca roda com o cadastro travado por esta mesma thread
        durante.append(getattr(dono, "dentro", False))
        return original(senha, guardado)
    monkeypatch.setattr(acesso._contas, "transacao", transacao_marcada)
    monkeypatch.setattr(iam, "_confere_senha", conferir)
    fim = time.monotonic() + 2
    resultados = []

    def rajada(k):
        while time.monotonic() < fim:
            Navegador(porta).login(f"ninguem{k}", "senha-qualquer-errada")
    threads = [threading.Thread(target=rajada, args=(k,)) for k in range(4)]
    [t.start() for t in threads]
    for _ in range(3):  # quem acerta entra durante a rajada, sem esperar a trava
        t0 = time.monotonic()
        resultados.append((Navegador(porta).login("auditor")[0], time.monotonic() - t0 < 4))
    [t.join() for t in threads]
    assert resultados == [(200, True)] * 3
    assert durante and not any(durante)


def test_infinite_price_is_refused_and_a_tampered_vault_answers_503(subir):
    _, acesso, porta, _ = subir("fechar_mes")
    controller = entrar(porta, "controller")
    status, _ = controller.pedir("POST", "/api/comando", b'{"tipo": "modelo", "agente": "AG-ORC", "preco_entrada": 1e999}')
    assert status == 400
    status, corpo = controller.pedir("GET", "/api/llm", cru=True)
    assert status == 200 and b"Infinity" not in corpo
    json.loads(corpo, parse_constant=lambda c: pytest.fail(f"JSON com {c}"))  # JSON estrito, como no navegador
    admin = entrar(porta, "admin")
    assert admin.post("/api/segredos", {"nome": "llm:OPENAI_API_KEY", "valor": "sk-" + "z" * 30})[0] == 200
    cofre = caminho_padrao(acesso.pasta)
    cofre.write_text(cofre.read_text().replace("sk-", "sx-"))  # adulterado fora do sistema
    status, dados = admin.get("/api/segredos")
    assert status == 503 and "IAM-10" in dados["erro"] and "comprometido" in dados["erro"]
    assert admin.post("/api/segredos", {"nome": "llm:OUTRA", "valor": "v"})[0] == 503
    assert Navegador(porta).get("/api/saude")[0] == 200  # o servidor segue vivo
    assert any(r["evento"] == "cofre_comprometido" and r["regra"] == "IAM-10" for r in acesso.trilha.ler())

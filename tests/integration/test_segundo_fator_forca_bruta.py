"""Segundo fator contra força bruta (correção simulada da DSM4, C3): o contador de códigos errados é da conta.

Servidor HTTP real em loopback e cadastro real em arquivo selado. Antes da correção, `desativar` não contava erros e
o limite de cinco códigos valia por pré-sessão, que se renovava a cada senha certa: com uma sessão viva (ou a senha)
o segundo fator caía por força bruta em minutos.
"""
import threading
import time

import pytest

from fin_mas.services import totp
from fin_mas.services.acesso_avancado import BLOQUEIO_2FA_S, MAX_FALHAS_2FA
from fin_mas.services.iam import SENHA_DEMO, Acesso, AcessoNegado, SegundoFatorPendente, criar_demo
from test_dashboard_acesso import Navegador
from test_dashboard_acesso_avancado import ativar_2fa, entrar, servico  # noqa: F401 (fixture)

pytestmark = pytest.mark.integracao


def _pre_sessao(porta):
    n = Navegador(porta)
    status, dados = n.pedir("POST", "/api/login", {"usuario": "carla", "senha": SENHA_DEMO})
    return n, status, dados, ({"Cookie": n.ultimos_cabecalhos["set-cookie"].split(";")[0]}
                              if status == 200 and dados.get("segundo_fator") == "pendente" else {})


def test_brute_force_through_disable_route_locks_the_second_factor_and_needs_the_password(servico):  # noqa: F811
    _, acesso, porta, _ = servico()
    carla = entrar(porta, "carla")
    segredo, _ = ativar_2fa(carla)
    certo = totp.codigo(segredo, time.time() + 30)
    assert carla.post("/api/2fa/desativar", {"codigo": certo})[0] == 400  # sem a senha atual nem confere o código
    errada = carla.post("/api/2fa/desativar", {"codigo": certo, "senha": "Outra-Senha-Qualquer-1"})
    assert errada[0] == 403 and "senha atual não confere" in errada[1]["erro"]
    assert carla.post("/api/2fa/recuperacao", {"codigo": certo, "senha": "Outra-Senha-Qualquer-1"})[0] == 403
    for k in range(MAX_FALHAS_2FA):  # quem tem a sessão e a senha ainda só erra cinco vezes
        status, dados = carla.post("/api/2fa/desativar", {"codigo": f"{k:06d}", "senha": SENHA_DEMO})
        assert status == 403 and "fora da janela" in dados["erro"]
    bloqueado = carla.post("/api/2fa/desativar", {"codigo": certo, "senha": SENHA_DEMO})  # nem o código certo passa
    assert bloqueado[0] == 403 and "segundo fator bloqueado" in bloqueado[1]["erro"]
    assert carla.post("/api/2fa/recuperacao", {"codigo": certo, "senha": SENHA_DEMO})[0] == 403
    assert carla.get("/api/2fa")[1]["ativo"] is True
    # a entrada também fica bloqueada: outra senha certa não renova as tentativas
    _, status, dados, _ = _pre_sessao(porta)
    assert status == 401 and "segundo fator bloqueado" in dados["erro"]
    eventos = [(r["evento"], r["resultado"], r.get("regra")) for r in acesso.trilha.ler() if r.get("ator") == "carla"]
    assert ("2fa_bloqueado", "negado", "IAM-08") in eventos
    # o administrador desbloqueia; o código certo volta a valer e zera o contador
    admin, _ = acesso.autenticar("admin", SENHA_DEMO)
    acesso.desbloquear(admin, "carla")
    assert carla.post("/api/2fa/desativar", {"codigo": certo, "senha": SENHA_DEMO}) == (200, {"ativo": False})
    assert acesso._ler_contas()["carla"].get("falhas_2fa") == 0


def test_new_pre_sessions_do_not_renew_the_attempts_and_parallel_guesses_respect_the_limit(servico):  # noqa: F811
    _, acesso, porta, _ = servico()
    carla = entrar(porta, "carla")
    segredo, codigos = ativar_2fa(carla)
    n, status, dados, pre = _pre_sessao(porta)
    assert dados["tentativas"] == MAX_FALHAS_2FA
    for _ in range(3):
        assert n.post("/api/login/2fa", {"codigo": "000000"}, **pre)[0] == 401
    n, status, dados, pre = _pre_sessao(porta)  # senha certa de novo: restam 2, não 5
    assert status == 200 and dados["tentativas"] == MAX_FALHAS_2FA - 3
    resultados, trava = [], threading.Lock()

    def palpite(k):  # corrida: vinte palpites ao mesmo tempo na mesma pré-sessão
        try:
            r = Navegador(porta).pedir("POST", "/api/login/2fa", {"codigo": f"{900000 + k:06d}"}, **pre)
        except OSError as erro:
            r = (0, repr(erro))
        with trava:
            resultados.append(r)
    threads = [threading.Thread(target=palpite, args=(k,)) for k in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    conferidos = [r for r in acesso.trilha.ler() if r.get("evento") == "segundo_fator" and r.get("ator") == "carla"
                  and "fora da janela" in str(r.get("motivo"))]
    assert len(conferidos) <= MAX_FALHAS_2FA  # nunca mais códigos conferidos contra o segredo do que o limite
    _, status, dados, _ = _pre_sessao(porta)
    assert status == 401 and "segundo fator bloqueado" in dados["erro"]
    # nem um código de recuperação válido abre a conta enquanto dura o bloqueio
    assert codigos[0] and acesso._ler_contas()["carla"]["bloqueio_2fa_ate"] is not None


def test_lock_holds_for_fifteen_minutes_counts_activation_and_only_a_correct_code_resets(tmp_path, monkeypatch):
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(tmp_path / "chaves"))
    criar_demo(tmp_path / "acesso", custo_scrypt=10)
    agora = [1_800_000_000.0]
    acesso = Acesso(tmp_path / "acesso", relogio=lambda: agora[0], custo_scrypt=10)
    carla, _ = acesso.autenticar("carla", SENHA_DEMO)
    segredo = acesso.iniciar_2fa(carla)["segredo"]
    for _ in range(MAX_FALHAS_2FA):  # a confirmação da ativação também conta
        with pytest.raises(AcessoNegado, match="não confere"):
            acesso.confirmar_2fa(carla, "000000")
    with pytest.raises(AcessoNegado, match="segundo fator bloqueado"):
        acesso.confirmar_2fa(carla, totp.codigo(segredo, agora[0]))
    for _ in range(2):  # a sessão segue em uso (sem uso por 15 min ela cairia) enquanto o bloqueio corre
        agora[0] += BLOQUEIO_2FA_S / 2 + 1
        assert acesso.sessao_por_id(carla.id) is not None
    codigos = acesso.confirmar_2fa(carla, totp.codigo(segredo, agora[0]))  # passou o prazo: o código certo ativa
    assert acesso._ler_contas()["carla"]["falhas_2fa"] == 0
    acesso.sair(carla)
    for _ in range(MAX_FALHAS_2FA):  # cada senha certa abre uma pré-sessão nova; o contador continua o mesmo
        with pytest.raises(SegundoFatorPendente) as pendente:
            acesso.autenticar("carla", SENHA_DEMO)
        with pytest.raises(AcessoNegado):
            acesso.confirmar_entrada(pendente.value.desafio, "123456")
    with pytest.raises(AcessoNegado, match="segundo fator bloqueado"):
        acesso.autenticar("carla", SENHA_DEMO)
    agora[0] += BLOQUEIO_2FA_S + 1
    with pytest.raises(SegundoFatorPendente) as pendente:  # depois do prazo, sem acerto, resta uma tentativa só
        acesso.autenticar("carla", SENHA_DEMO)
    assert pendente.value.tentativas == 1
    with pytest.raises(AcessoNegado):
        acesso.confirmar_entrada(pendente.value.desafio, "654321")
    with pytest.raises(AcessoNegado, match="segundo fator bloqueado"):
        acesso.autenticar("carla", SENHA_DEMO)
    agora[0] += BLOQUEIO_2FA_S + 1
    with pytest.raises(SegundoFatorPendente) as pendente:
        acesso.autenticar("carla", SENHA_DEMO)
    sessao, _ = acesso.confirmar_entrada(pendente.value.desafio, codigos[0])  # o acerto zera
    assert sessao.usuario == "carla" and acesso._ler_contas()["carla"]["falhas_2fa"] == 0

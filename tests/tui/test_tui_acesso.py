"""Console de administração de acesso (TUI): automação da interface com o Pilot do Textual, em modo headless.

Cada teste abre a aplicação sobre um cadastro numa pasta temporária, dirige a interface como a
pessoa faria (digita nos campos, aperta teclas, clica em botões) e confere o efeito de dois
jeitos: no que a tela mostra e no cadastro em disco, lido por **outra** instância de `Acesso`,
como faz o servidor do dashboard. Não há teste unitário das telas.

As chaves dos arquivos selados ficam numa pasta própria de cada teste (`FIN_MAS_DIR_CHAVES`).
O Pilot espera a aplicação ficar ociosa a cada tecla (cerca de 60 ms). Por isso os testes rodam
com a pasta temporária como diretório atual e digitam nomes de arquivo curtos, e as senhas
longas entram por colagem (o evento de colar do terminal, entregue ao campo com o foco); os
testes de login digitam a senha tecla a tecla.
"""
import asyncio
import json

import pytest

pytest.importorskip("textual")  # extra opcional `tui`: sem ele a suíte pula inteira

from textual import events  # noqa: E402
from textual.widgets import DataTable, Static  # noqa: E402

from fin_mas.env.scenarios import run_scenario  # noqa: E402
from fin_mas.services.explicacao import explicar  # noqa: E402
from fin_mas.services.iam import SENHA_DEMO, Acesso, AcessoNegado, criar_demo  # noqa: E402
from fin_mas.tui.app import ConsoleAcesso, TelaConsole  # noqa: E402
from fin_mas.tui.telas import Confirmar, FormConta, FormPapeis, FormTrocarSenha, TelaEntrada  # noqa: E402

pytestmark = pytest.mark.integracao
TAMANHO = (140, 45)
CUSTO = 10  # scrypt barato: os testes não medem a força do hash
FORTE, TEMPORARIA = "Administrador-2026-forte", "Temporaria-2026-abcd"
PAPEIS = ("ROLE-SOL", "ROLE-APR", "ROLE-OPE", "ROLE-AUD", "ROLE-ADM")  # ordem das linhas na lista de papéis


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(tmp_path / "chaves"))
    monkeypatch.setenv("FIN_MAS_CHAVE_TRACE", "chave-de-teste-do-trace")
    monkeypatch.chdir(tmp_path)  # arquivos de trace e de exportação são digitados pelo nome
    return tmp_path / "acesso"


@pytest.fixture
def demo(pasta):
    criar_demo(pasta, custo_scrypt=CUSTO)
    return pasta


def no_console(pasta, roteiro):
    """Abre a aplicação headless e entrega o Pilot ao roteiro do teste."""
    async def rodar():
        app = ConsoleAcesso(pasta, custo_scrypt=CUSTO)
        app.animation_level = "none"  # sem a animação das abas: o Pilot não precisa esperar por ela
        async with app.run_test(size=TAMANHO) as pilot:
            await pilot.pause()
            await roteiro(pilot)
    asyncio.run(rodar())


def servidor(pasta) -> Acesso:
    """Outra instância sobre a mesma pasta: o que o servidor do dashboard enxerga."""
    return Acesso(pasta, custo_scrypt=CUSTO)


def texto(pilot, seletor: str) -> str:
    return str(pilot.app.screen.query_one(seletor, Static).content)


def tabela(pilot, seletor: str) -> DataTable:
    return pilot.app.screen.query_one(seletor, DataTable)


def linha(pilot, seletor: str, chave: str) -> list:
    return [str(celula) for celula in tabela(pilot, seletor).get_row(chave)]


async def digitar(pilot, seletor: str, valor: str) -> None:
    await pilot.click(seletor)
    await pilot.press("end", "ctrl+u", *valor)


async def colar(pilot, seletor: str, valor: str) -> None:
    """Cola o valor no campo, como a pessoa colaria no terminal (um evento só, em vez de uma tecla por letra)."""
    await pilot.click(seletor)
    await pilot.press("end", "ctrl+u")
    pilot.app.post_message(events.Paste(valor))
    await pilot.pause()


async def entrar(pilot, usuario: str, senha: str = SENHA_DEMO, teclado: bool = False) -> None:
    await digitar(pilot, "#usuario", usuario)
    await (digitar if teclado else colar)(pilot, "#senha", senha)
    await pilot.click("#entrar")
    await pilot.pause()


async def selecionar(pilot, seletor: str, chave: str) -> None:
    """Leva o cursor da tabela (já com o foco) até a linha da chave, pelas setas."""
    t = tabela(pilot, seletor)
    assert pilot.app.focused is t
    passos = t.get_row_index(chave) - t.cursor_row
    if passos:
        await pilot.press(*(["down"] * passos if passos > 0 else ["up"] * -passos))
    await pilot.pause()


async def marcar_papel(pilot, seletor: str, papel: str) -> None:
    await pilot.click(seletor, offset=(6, PAPEIS.index(papel)))


def test_first_use_wizard_creates_the_first_administrator(pasta):
    async def roteiro(pilot):
        assert isinstance(pilot.app.screen, TelaEntrada) and "Primeiro uso" in texto(pilot, "#primeiro-uso")
        await digitar(pilot, "#usuario", "raiz")
        await digitar(pilot, "#senha", "curta")
        await digitar(pilot, "#senha2", "curta")
        await pilot.click("#criar-admin")
        await pilot.pause()
        assert "IAM-02" in texto(pilot, "#erro-entrada") and servidor(pasta).vazio()  # senha fraca: nada foi criado
        await colar(pilot, "#senha", FORTE)
        await colar(pilot, "#senha2", FORTE + "x")
        await pilot.click("#criar-admin")
        await pilot.pause()
        assert "não conferem" in texto(pilot, "#erro-entrada") and servidor(pasta).vazio()
        await colar(pilot, "#senha", FORTE)
        await colar(pilot, "#senha2", FORTE)
        await pilot.click("#criar-admin")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)  # já entra no console com a conta criada
        assert texto(pilot, "#status").startswith("raiz — Administração de Acesso [ROLE-ADM]")
        assert linha(pilot, "#tabela-usuarios", "raiz")[2:4] == ["ativa", "ROLE-ADM"]
    no_console(pasta, roteiro)
    conta = servidor(pasta).conta("raiz")
    assert conta["papeis"] == ["ROLE-ADM"] and conta["estado"] == "ativa" and conta["trocar_senha"] is False
    assert [r["evento"] for r in servidor(pasta).trilha.ler()][:2] == ["bootstrap", "entrada"]


def test_invalid_login_shows_the_error_and_stays_out(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin", "senha-errada-123", teclado=True)
        assert isinstance(pilot.app.screen, TelaEntrada) and pilot.app.sessao is None
        assert texto(pilot, "#erro-entrada") == "acesso negado: IAM-03: usuário ou senha inválidos"
        await entrar(pilot, "ninguem", SENHA_DEMO, teclado=True)
        assert isinstance(pilot.app.screen, TelaEntrada) and "IAM-03" in texto(pilot, "#erro-entrada")
    no_console(demo, roteiro)
    negadas = [r for r in servidor(demo).trilha.ler() if r["evento"] == "entrada" and r["resultado"] == "negado"]
    assert [(r["ator"], r["regra"], r["origem"]) for r in negadas] == [("admin", "IAM-03", "tui"),
                                                                       ("ninguem", "IAM-03", "tui")]
    assert not [s for s in servidor(demo).sessoes() if s["viva"]]


def test_account_without_administration_or_audit_permission_is_refused(demo):
    async def roteiro(pilot):
        await entrar(pilot, "bruno")  # só ROLE-SOL: usa a plataforma pela web, não administra nem audita
        assert isinstance(pilot.app.screen, TelaEntrada) and pilot.app.sessao is None
        assert "IAM-05" in texto(pilot, "#erro-entrada")
    no_console(demo, roteiro)
    assert not [s for s in servidor(demo).sessoes() if s["viva"]]  # a sessão aberta na conferência foi encerrada
    ultimo = [r for r in servidor(demo).trilha.ler() if r["ator"] == "bruno"][-1]
    assert (ultimo["evento"], ultimo["resultado"], ultimo["regra"]) == ("permissao", "negado", "IAM-05")


def test_compromised_registry_lets_nobody_in(demo):
    arquivo = demo / "contas.json"
    arquivo.write_text(arquivo.read_text(encoding="utf-8").replace("ROLE-AUD", "ROLE-ADM"), encoding="utf-8")

    async def roteiro(pilot):
        assert isinstance(pilot.app.screen, TelaEntrada) and "IAM-07" in texto(pilot, "#erro-entrada")
        assert not pilot.app.screen.query("#criar-admin")  # cadastro comprometido não vira "primeiro uso"
        await entrar(pilot, "admin")
        assert isinstance(pilot.app.screen, TelaEntrada) and "IAM-07" in texto(pilot, "#erro-entrada")
    no_console(demo, roteiro)


def test_administrator_login_opens_the_console_and_quitting_ends_the_session(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin", teclado=True)
        assert isinstance(pilot.app.screen, TelaConsole)
        assert texto(pilot, "#status") == f"admin — Administração de Acesso [ROLE-ADM] · cadastro: {demo}"
        assert pilot.app.screen.abas == ("aba-usuarios", "aba-papeis", "aba-sessoes", "aba-trilha", "aba-traces")
        assert tabela(pilot, "#tabela-usuarios").row_count == 10 and pilot.app.focused is tabela(pilot, "#tabela-usuarios")
        assert linha(pilot, "#tabela-usuarios", "carla")[:6] == ["carla", "Carla Mendes", "ativa", "ROLE-APR", "gerente",
                                                                 "carla"]
        assert "n nova conta" in texto(pilot, "#atalhos")
        vivas = [s for s in servidor(demo).sessoes() if s["viva"]]
        assert [(s["usuario"], s["origem"]) for s in vivas] == [("admin", "tui")]
        await pilot.press("f3")
        await pilot.pause()
        assert "(este console)" in linha(pilot, "#tabela-sessoes", vivas[0]["id"])[0]
        await pilot.press("ctrl+q")
        await pilot.pause()
    no_console(demo, roteiro)
    assert not [s for s in servidor(demo).sessoes() if s["viva"]]
    assert servidor(demo).trilha.ler()[-1]["evento"] == "saida"


def test_roles_matrix_and_incompatible_combinations_board(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await pilot.press("f2")
        await pilot.pause()
        matriz = tabela(pilot, "#tabela-matriz")
        assert [str(c.label) for c in matriz.columns.values()] == ["permissão", "título", *PAPEIS]
        assert linha(pilot, "#tabela-matriz", "PERM-APR-DECIDIR") == ["PERM-APR-DECIDIR", "Decidir no Approval Gate",
                                                                      "·", "sim", "·", "·", "·"]
        assert linha(pilot, "#tabela-matriz", "PERM-IAM-USUARIOS")[2:] == ["·", "·", "·", "·", "sim"]
        quadro = texto(pilot, "#incompativeis")
        assert "IAM-06" not in quadro  # o serviço não deixa nascer conta com ROLE-ADM e ROLE-APR
        for conta in ("ana", "avaliador", "controller", "elisa"):  # solicitam e aprovam: aviso da POL-13
            assert f"aviso POL-13  {conta} solicita e aprova" in quadro
        assert "bruno" not in quadro and "carla" not in quadro
    no_console(demo, roteiro)


def test_create_account_through_the_form(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FormConta)
        await digitar(pilot, "#conta-usuario", "maria")
        await digitar(pilot, "#conta-nome", "Maria Souza")
        await marcar_papel(pilot, "#conta-papeis", "ROLE-APR")
        await marcar_papel(pilot, "#conta-papeis", "ROLE-SOL")
        await pilot.click("#conta-cargo")  # abre a lista de cargos
        await pilot.press("g", "enter")  # a inicial leva a "gerente"
        await digitar(pilot, "#conta-pessoa", "carla")
        await digitar(pilot, "#conta-senha", "curta")
        await digitar(pilot, "#conta-senha2", "curta")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FormConta) and "IAM-02" in texto(pilot, "#erro-modal")  # segue aberto
        assert servidor(demo).conta("maria") is None
        await colar(pilot, "#conta-senha", TEMPORARIA)
        await colar(pilot, "#conta-senha2", TEMPORARIA)
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert "conta maria criada" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-usuarios", "maria") == ["maria", "Maria Souza", "ativa", "ROLE-SOL, ROLE-APR",
                                                             "gerente", "carla", "senha temporária"]
    no_console(demo, roteiro)
    conta = servidor(demo).conta("maria")
    assert conta["papeis"] == ["ROLE-SOL", "ROLE-APR"] and conta["cargo"] == "gerente" and conta["pessoa_erp"] == "carla"
    sessao, _ = servidor(demo).autenticar("maria", TEMPORARIA, "web")
    assert sessao.trocar_senha is True and sessao.pode("PERM-APR-DECIDIR")
    criada = [r for r in servidor(demo).trilha.ler() if r["evento"] == "conta_criada"][-1]
    assert (criada["ator"], criada["alvo"]) == ("admin", "maria")


def test_assigning_approver_role_to_the_administrator_is_refused_with_iam06(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await selecionar(pilot, "#tabela-usuarios", "admin")
        await pilot.click("#editar-papeis")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FormPapeis)
        await marcar_papel(pilot, "#papeis", "ROLE-APR")  # ROLE-ADM já vem marcado
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FormPapeis)
        assert "IAM-06" in texto(pilot, "#erro-modal") and "ROLE-ADM e ROLE-APR" in texto(pilot, "#erro-modal")
        assert servidor(demo).conta("admin")["papeis"] == ["ROLE-ADM"]
        await marcar_papel(pilot, "#papeis", "ROLE-APR")  # desfaz o aprovador e tenta tirar a administração
        await marcar_papel(pilot, "#papeis", "ROLE-ADM")
        await marcar_papel(pilot, "#papeis", "ROLE-AUD")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "IAM-06" in texto(pilot, "#erro-modal") and "último administrador" in texto(pilot, "#erro-modal")
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert linha(pilot, "#tabela-usuarios", "admin")[3] == "ROLE-ADM"
    no_console(demo, roteiro)
    assert servidor(demo).conta("admin")["papeis"] == ["ROLE-ADM"]


def test_change_roles_and_link_of_an_account(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await selecionar(pilot, "#tabela-usuarios", "bruno")
        await pilot.press("p")
        await pilot.pause()
        await marcar_papel(pilot, "#papeis", "ROLE-AUD")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "papéis de bruno: ROLE-SOL, ROLE-AUD" in texto(pilot, "#mensagem")
        assert pilot.app.focused is tabela(pilot, "#tabela-usuarios") and linha(pilot, "#tabela-usuarios", "bruno")[3] \
            == "ROLE-SOL, ROLE-AUD"
        await pilot.press("v")  # o cursor continua em bruno depois da recarga
        await pilot.pause()
        await digitar(pilot, "#vinculo-pessoa", "bruno.souza")
        await pilot.press("enter")
        await pilot.pause()
        assert "vínculo de bruno: pessoa do ERP bruno.souza, cargo analista" in texto(pilot, "#mensagem")
    no_console(demo, roteiro)
    conta = servidor(demo).conta("bruno")
    assert (conta["papeis"], conta["pessoa_erp"], conta["cargo"]) == (["ROLE-SOL", "ROLE-AUD"], "bruno.souza", "analista")


def test_blocking_an_account_drops_its_session_and_its_login(demo):
    web = servidor(demo)
    _, token = web.autenticar("bruno", SENHA_DEMO, "web")

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await selecionar(pilot, "#tabela-usuarios", "bruno")
        await pilot.press("b")
        await pilot.pause()
        assert isinstance(pilot.app.screen, Confirmar) and "Bloquear a conta bruno" in texto(pilot, "#pergunta")
        await pilot.click("#nao")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and web.conta("bruno")["estado"] == "ativa"
        assert web.sessao(token) is not None
        await pilot.click("#bloquear")
        await pilot.pause()
        await pilot.click("#sim")
        await pilot.pause()
        assert "conta bruno bloqueada" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-usuarios", "bruno")[2] == "bloqueada"
        assert web.conta("bruno")["estado"] == "bloqueada" and web.sessao(token) is None  # caiu na requisição seguinte
        with pytest.raises(AcessoNegado, match="IAM-03: conta bloqueada"):
            web.autenticar("bruno", SENHA_DEMO, "web")
        await pilot.press("d")  # desbloquear não pede confirmação
        await pilot.pause()
        assert "conta bruno desbloqueada" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-usuarios", "bruno")[2] == "ativa"
        assert web.autenticar("bruno", SENHA_DEMO, "web")[0].usuario == "bruno"
        await pilot.press("x")
        await pilot.pause()
        assert "Desativar a conta bruno" in texto(pilot, "#pergunta")
        await pilot.press("s")
        await pilot.pause()
        assert linha(pilot, "#tabela-usuarios", "bruno")[2] == "desativada"
    no_console(demo, roteiro)
    assert servidor(demo).conta("bruno")["estado"] == "desativada"
    with pytest.raises(AcessoNegado):
        servidor(demo).autenticar("bruno", SENHA_DEMO, "web")


def test_last_administrator_cannot_be_blocked(demo):
    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await selecionar(pilot, "#tabela-usuarios", "admin")
        await pilot.press("b")
        await pilot.pause()
        await pilot.click("#sim")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert "IAM-06" in texto(pilot, "#mensagem") and "último administrador" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-usuarios", "admin")[2] == "ativa"
    no_console(demo, roteiro)
    assert servidor(demo).conta("admin")["estado"] == "ativa"


def test_reset_password_gives_a_temporary_one_and_drops_sessions(demo):
    web = servidor(demo)
    _, token = web.autenticar("carla", SENHA_DEMO, "web")

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await selecionar(pilot, "#tabela-usuarios", "carla")
        await pilot.press("s")
        await pilot.pause()
        await colar(pilot, "#senha-nova", TEMPORARIA)
        await colar(pilot, "#senha-nova2", TEMPORARIA + "!")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "não conferem" in texto(pilot, "#erro-modal") and web.sessao(token) is not None
        await colar(pilot, "#senha-nova2", TEMPORARIA)
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "senha de carla redefinida" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-usuarios", "carla")[6] == "senha temporária"
    no_console(demo, roteiro)
    assert web.sessao(token) is None
    with pytest.raises(AcessoNegado, match="IAM-03"):
        web.autenticar("carla", SENHA_DEMO, "web")
    assert web.autenticar("carla", TEMPORARIA, "web")[0].trocar_senha is True


def test_temporary_password_must_be_changed_before_using_the_console(demo):
    web = servidor(demo)
    adm, _ = web.autenticar("admin", SENHA_DEMO, "teste")
    web.criar_conta(adm, "segunda", "Segunda Administração", TEMPORARIA, ["ROLE-ADM"])
    web.sair(adm)

    async def roteiro(pilot):
        await entrar(pilot, "segunda", TEMPORARIA)
        assert isinstance(pilot.app.screen, FormTrocarSenha)
        await pilot.press("escape")  # sem trocar não fica no console
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaEntrada) and "IAM-02" in texto(pilot, "#erro-entrada")
        assert pilot.app.sessao is None and not [s for s in web.sessoes() if s["viva"]]
        await entrar(pilot, "segunda", TEMPORARIA)
        await colar(pilot, "#senha-atual", TEMPORARIA)
        await colar(pilot, "#senha-nova", FORTE)
        await colar(pilot, "#senha-nova2", FORTE)
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and "senha trocada" in texto(pilot, "#mensagem")
        assert pilot.app.sessao.trocar_senha is False
    no_console(demo, roteiro)
    assert web.conta("segunda")["trocar_senha"] is False
    assert web.autenticar("segunda", FORTE, "web")[0].usuario == "segunda"


def test_revoking_a_session_opened_by_the_server_drops_it(demo):
    web = servidor(demo)
    sessao, token = web.autenticar("operador", SENHA_DEMO, "127.0.0.1")
    _, ana1 = web.autenticar("ana", SENHA_DEMO, "127.0.0.1")
    _, ana2 = web.autenticar("ana", SENHA_DEMO, "10.0.0.7")

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await pilot.press("f3")
        await pilot.pause()
        assert tabela(pilot, "#tabela-sessoes").row_count == 5  # a da criação do demo (encerrada), 3 da web e a do console
        assert linha(pilot, "#tabela-sessoes", sessao.id)[1:3] == ["operador", "127.0.0.1"]
        assert linha(pilot, "#tabela-sessoes", sessao.id)[6] == "viva"
        await selecionar(pilot, "#tabela-sessoes", sessao.id)
        await pilot.press("r")
        await pilot.pause()
        assert f"Revogar a sessão {sessao.id} de operador" in texto(pilot, "#pergunta") and web.sessao(token) is not None
        await pilot.click("#sim")
        await pilot.pause()
        assert web.sessao(token) is None  # o servidor recusa o token na requisição seguinte
        assert linha(pilot, "#tabela-sessoes", sessao.id)[6] == "encerrada: revogada por admin"
        assert f"sessão {sessao.id} de operador revogada" in texto(pilot, "#mensagem")
        await pilot.press("r")  # a mesma sessão, já encerrada: nada a revogar
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and "já está encerrada" in texto(pilot, "#mensagem")
        # todas as vivas de um usuário, a partir de qualquer sessão dele
        de_ana = next(s["id"] for s in web.sessoes() if s["usuario"] == "ana")
        await selecionar(pilot, "#tabela-sessoes", de_ana)
        await pilot.click("#revogar-usuario")
        await pilot.pause()
        assert "Revogar 2 sessão(ões) viva(s) de ana" in texto(pilot, "#pergunta")
        await pilot.press("s")
        await pilot.pause()
        assert web.sessao(ana1) is None and web.sessao(ana2) is None
        assert pilot.app.sessao is not None and isinstance(pilot.app.screen, TelaConsole)
    no_console(demo, roteiro)
    revogadas = [r["sessao"] for r in servidor(demo).trilha.ler() if r["evento"] == "sessao_revogada"]
    assert len(revogadas) == 3 and revogadas[0] == sessao.id


def test_console_returns_to_login_when_its_own_session_is_revoked(demo):
    web = servidor(demo)

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        outro, _ = web.autenticar("admin", SENHA_DEMO, "teste")
        web.revogar(outro, pilot.app.sessao.id)  # outro administrador derruba a sessão deste console
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaEntrada) and pilot.app.sessao is None
        assert "IAM-04" in texto(pilot, "#erro-entrada")
    no_console(demo, roteiro)
    assert servidor(demo).conta("maria") is None


def test_console_follows_role_changes_made_elsewhere(demo):
    web = servidor(demo)
    adm, _ = web.autenticar("admin", SENHA_DEMO, "teste")

    async def roteiro(pilot):
        await entrar(pilot, "auditor")
        assert pilot.app.screen.abas == ("aba-trilha", "aba-traces")
        web.atribuir_papeis(adm, "auditor", ["ROLE-AUD", "ROLE-ADM"])  # outro administrador promove a conta
        await pilot.press("ctrl+r")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and "papéis mudaram" in texto(pilot, "#mensagem")
        assert pilot.app.screen.abas == ("aba-usuarios", "aba-papeis", "aba-sessoes", "aba-trilha", "aba-traces")
        assert tabela(pilot, "#tabela-usuarios").row_count == 10 and "[ROLE-AUD, ROLE-ADM]" in texto(pilot, "#status")
        web.atribuir_papeis(adm, "auditor", ["ROLE-SOL"])  # e depois tira dela a auditoria e a administração
        await pilot.press("n")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaEntrada) and "IAM-05" in texto(pilot, "#erro-entrada")
        assert pilot.app.sessao is None
    no_console(demo, roteiro)
    assert servidor(demo).conta("maria") is None and len(servidor(demo).contas()) == 10


def test_access_trail_filters_export_integrity_and_tampering(demo, tmp_path):
    recorte = tmp_path / "recorte.jsonl"

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await pilot.press("f4")
        await pilot.pause()
        registros = servidor(demo).trilha.ler()
        assert tabela(pilot, "#tabela-trilha").row_count == len(registros) == 13
        await pilot.click("#verificar-trilha")
        await pilot.pause()
        assert texto(pilot, "#integridade-trilha").startswith("ÍNTEGRA — 13 registro(s)")
        assert "ÍNTEGRA" in texto(pilot, "#mensagem")
        await digitar(pilot, "#trilha-evento", "conta_criada")
        await pilot.pause()
        assert tabela(pilot, "#tabela-trilha").row_count == 9
        await pilot.click("#resultado-negado")
        await pilot.pause()
        assert tabela(pilot, "#tabela-trilha").row_count == 0
        await pilot.click("#resultado-ok")
        await pilot.pause()
        assert tabela(pilot, "#tabela-trilha").row_count == 9
        await pilot.click("#exportar-trilha")
        await pilot.pause()
        await pilot.press(*recorte.name, "enter")  # o campo do arquivo já vem com o foco e o padrão selecionado
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert "9 registro(s) exportados para recorte.jsonl" in texto(pilot, "#mensagem")
        exportados = [json.loads(x) for x in recorte.read_text(encoding="utf-8").splitlines()]
        assert [r["seq"] for r in exportados] == list(range(3, 12)) and {r["evento"] for r in exportados} == {"conta_criada"}
        await pilot.press("e")  # não sobrescreve um arquivo que já existe
        await pilot.pause()
        await pilot.press(*recorte.name, "enter")
        await pilot.pause()
        assert "já existe" in texto(pilot, "#erro-modal")
        await pilot.press("escape")
        await pilot.pause()
        # adulteração no disco, por fora do sistema: troca o ator de um registro antigo
        arquivo = demo / "trilha.jsonl"
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        linhas[2] = linhas[2].replace('"ator": "admin"', '"ator": "outro"')
        arquivo.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        await pilot.press("i")
        await pilot.pause()
        assert texto(pilot, "#integridade-trilha").startswith("ADULTERADA — cadeia quebrada no registro 3")
        assert "ADULTERADA" in texto(pilot, "#mensagem")
    no_console(demo, roteiro)
    assert json.loads(recorte.read_text(encoding="utf-8").splitlines()[0])["alvo"] == "operador"


def test_auditor_sees_the_trail_and_cannot_administer(demo):
    async def roteiro(pilot):
        await entrar(pilot, "auditor")
        assert isinstance(pilot.app.screen, TelaConsole)
        assert pilot.app.screen.abas == ("aba-trilha", "aba-traces")  # só as abas de auditoria
        assert not pilot.app.screen.query("#nova-conta") and not pilot.app.screen.query("#tabela-usuarios")
        assert not pilot.app.screen.query("#tabela-sessoes")
        assert tabela(pilot, "#tabela-trilha").row_count == 13 and texto(pilot, "#integridade-trilha").startswith("ÍNTEGRA")
        assert pilot.app.focused is tabela(pilot, "#tabela-trilha")
        await pilot.press("n")  # a tecla de "nova conta" não abre formulário: o serviço nega
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert "IAM-05" in texto(pilot, "#mensagem") and "PERM-IAM-USUARIOS" in texto(pilot, "#mensagem")
        await pilot.press("r")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and "PERM-IAM-SESSOES" in texto(pilot, "#mensagem")
        await pilot.press("f1")
        await pilot.pause()
        assert pilot.app.screen.query_one("#abas").active == "aba-trilha" and "IAM-05" in texto(pilot, "#mensagem")
        await pilot.press("ctrl+r")
        await pilot.pause()
        vistos = [str(c) for c in tabela(pilot, "#tabela-trilha").get_row_at(0)]
        assert vistos[2:6] == ["permissao", "auditor", "negado", "IAM-05"]  # as próprias tentativas, a mais recente em cima
    no_console(demo, roteiro)
    web = servidor(demo)
    assert len(web.contas()) == 10
    negadas = [r["permissao"] for r in web.trilha.ler() if r["ator"] == "auditor" and r["resultado"] == "negado"]
    assert negadas == ["PERM-IAM-USUARIOS", "PERM-IAM-SESSOES", "PERM-IAM-USUARIOS"]


def test_open_a_recorded_trace_filter_explain_and_export(demo, tmp_path):
    caminho, recorte = tmp_path / "trace.jsonl", tmp_path / "decisoes.jsonl"
    registros = run_scenario("orc_hipotese_local").audit.records
    run_scenario("orc_hipotese_local").audit.write_jsonl(caminho)
    decisoes = [r for r in registros if r["kind"] == "decision"]
    assert len(decisoes) >= 2

    async def roteiro(pilot):
        await entrar(pilot, "auditor")
        await pilot.press("f5", "a")
        await pilot.press(*caminho.name, "enter")
        await pilot.pause()
        assert texto(pilot, "#trace-estado").startswith(
            f"ÍNTEGRO — a cadeia de hashes e o selo conferem: {len(registros)} registro(s)")
        assert texto(pilot, "#invariantes") == "invariantes: 8 conferidos, nenhuma violação"
        assert tabela(pilot, "#tabela-trace").row_count == len(registros)
        await digitar(pilot, "#trace-tipo", "decision")
        await pilot.press("enter")
        await pilot.pause()
        assert tabela(pilot, "#tabela-trace").row_count == len(decisoes)
        assert pilot.app.focused is tabela(pilot, "#tabela-trace")
        await pilot.press("down", "enter")  # Enter na linha explica o registro
        await pilot.pause()
        alvo = decisoes[1]
        esperado = explicar(registros, alvo["seq"])
        painel = texto(pilot, "#explicacao")
        assert painel.startswith(f"por que: {esperado['alvo']['texto']}")
        assert f"agente {esperado['agente']} | conversa {esperado['conversa']} | tarefa {esperado['tarefa']}" in painel
        assert esperado["cadeia"] and all(f"[{item['papel']}] {item['texto']}" in painel for item in esperado["cadeia"])
        assert f"registro {alvo['seq']} explicado" in texto(pilot, "#mensagem")
        await digitar(pilot, "#trace-agente", esperado["agente"])
        await pilot.press("enter")
        await pilot.pause()
        do_agente = [r for r in decisoes if r.get("agente") == esperado["agente"]]
        assert tabela(pilot, "#tabela-trace").row_count == len(do_agente)
        await pilot.click("#exportar-trace")
        await pilot.pause()
        await pilot.press(*recorte.name, "enter")
        await pilot.pause()
        assert f"{len(do_agente)} registro(s) exportados" in texto(pilot, "#mensagem")
    no_console(demo, roteiro)
    assert [json.loads(x) for x in recorte.read_text(encoding="utf-8").splitlines()] == [
        r for r in decisoes if r.get("agente") == explicar(registros, decisoes[1]["seq"])["agente"]]
    exportacao = next(r for r in servidor(demo).trilha.ler() if r["evento"] == "auditoria_exportada")
    assert (exportacao["evento"], exportacao["ator"], exportacao["fonte"]) == ("auditoria_exportada", "auditor", "trace")


def test_tampered_or_missing_trace_shows_the_error(demo, tmp_path):
    caminho = tmp_path / "trace.jsonl"
    run_scenario("orc_hipotese_local").audit.write_jsonl(caminho)
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    alterada = json.loads(linhas[4])
    alterada["t"] += 1
    linhas[4] = json.dumps(alterada, sort_keys=True, ensure_ascii=False)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")

    async def roteiro(pilot):
        await entrar(pilot, "auditor")
        await pilot.press("f5")
        await digitar(pilot, "#trace-caminho", caminho.name)
        await pilot.click("#abrir-trace")
        await pilot.pause()
        assert texto(pilot, "#trace-estado").startswith("ADULTERADO — linha 5")
        assert "hash não confere" in texto(pilot, "#trace-estado")
        assert tabela(pilot, "#tabela-trace").row_count == 0  # registros sem garantia não são mostrados
        assert "não conferidos" in texto(pilot, "#invariantes")
        await pilot.click("#explicar")
        await pilot.pause()
        assert "abra um trace" in texto(pilot, "#mensagem")
        await digitar(pilot, "#trace-caminho", "nao-existe.jsonl")
        await pilot.press("enter")
        await pilot.pause()
        assert texto(pilot, "#trace-estado").startswith("ERRO — não foi possível ler o arquivo")
    no_console(demo, roteiro)

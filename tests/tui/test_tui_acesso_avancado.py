"""Acesso avançado no console (DSM4, ADR-012): automação da interface com o Pilot do Textual, headless.

Mesmo molde de `test_tui_acesso.py`: a pessoa digita, clica e aperta teclas; o efeito é conferido
na tela e no cadastro em disco, lido por outra instância de `Acesso`. Os códigos TOTP são gerados
pelo teste com o segredo que a tela mostra (relógio de verdade).
"""
import time

import pytest

pytest.importorskip("textual")

from textual.widgets import Static  # noqa: E402

from fin_mas.services import totp  # noqa: E402
from fin_mas.tui.avancado import FormCodigo, MostrarCodigos  # noqa: E402
from fin_mas.tui.app import TelaConsole  # noqa: E402
from fin_mas.tui.telas import FormCodigoEntrada  # noqa: E402
from tui.test_tui_acesso import (CUSTO, colar, demo, digitar, entrar, linha, no_console, pasta, servidor,  # noqa: E402,F401
                             tabela, texto)

pytestmark = pytest.mark.integracao


def tela(pilot) -> str:
    return " ".join(str(w.content) for w in pilot.app.screen.query(Static))


async def aba(pilot, tecla):
    await pilot.press(tecla)
    await pilot.pause()


def test_enrol_second_factor_then_log_in_with_a_recovery_code(demo):
    guardado = {}

    async def ativar(pilot):
        await entrar(pilot, "admin")
        await aba(pilot, "f6")
        assert "segundo fator desativado" in texto(pilot, "#estado-2fa")
        await pilot.click("#ativar-2fa")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FormCodigo)
        mostrado = texto(pilot, "#segredo-2fa")
        segredo = mostrado.splitlines()[1]
        assert "otpauth://totp/" in mostrado
        await digitar(pilot, "#codigo-2fa", "000000")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "IAM-08" in texto(pilot, "#erro-modal")  # código errado: o formulário continua aberto
        await digitar(pilot, "#codigo-2fa", totp.codigo(segredo, time.time()))
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MostrarCodigos)
        guardado["codigos"] = texto(pilot, "#codigos-recuperacao").splitlines()
        await pilot.click("#fechar-codigos")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole)
        assert "ATIVO" in texto(pilot, "#estado-2fa") and segredo not in tela(pilot)  # o segredo não volta à tela
    no_console(demo, ativar)
    assert len(guardado["codigos"]) == 10
    conta = servidor(demo).conta("admin")
    assert conta["segundo_fator"]["ativo"] and conta["segundo_fator"]["codigos_restantes"] == 10

    async def entrar_com_codigo(pilot):
        await entrar(pilot, "admin")
        assert isinstance(pilot.app.screen, FormCodigoEntrada)  # a senha certa só leva ao segundo passo
        await digitar(pilot, "#codigo-entrada", "1111-2222")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "IAM-08" in texto(pilot, "#erro-modal")
        await digitar(pilot, "#codigo-entrada", guardado["codigos"][0])
        await pilot.click("#confirmar")
        await pilot.pause()
        assert isinstance(pilot.app.screen, TelaConsole) and pilot.app.sessao.usuario == "admin"
    no_console(demo, entrar_com_codigo)
    assert servidor(demo).conta("admin")["segundo_fator"]["codigos_restantes"] == 9


def test_approver_creates_and_revokes_a_delegation(demo):
    async def roteiro(pilot):
        await entrar(pilot, "diego")
        await aba(pilot, "f7")
        await pilot.click("#nova-delegacao")
        await pilot.pause()
        await digitar(pilot, "#delegacao-para", "bruno")
        await digitar(pilot, "#delegacao-teto", "1000000")
        await digitar(pilot, "#delegacao-competencia", "2026-09")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "POL-11" in texto(pilot, "#erro-modal")  # bruno não é aprovador
        await digitar(pilot, "#delegacao-para", "ana")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "delegação DLG-001 para ana criada" in texto(pilot, "#mensagem")
        assert linha(pilot, "#tabela-delegacoes", "DLG-001")[1:3] == ["diego", "ana"]
        tabela(pilot, "#tabela-delegacoes").focus()
        await pilot.click("#revogar-delegacao")
        await pilot.pause()
        await pilot.click("#sim")
        await pilot.pause()
        assert linha(pilot, "#tabela-delegacoes", "DLG-001")[-1] == "revogada"
    no_console(demo, roteiro)
    (d,) = servidor(demo).delegacoes()
    assert (d["de"], d["para"], d["teto"], d["situacao"]) == ("diego", "ana", 1000000, "revogada")


def test_administrator_sets_policy_vault_companies_and_sees_authority_limits(demo):
    valor = "sk-tui-" + "q" * 30

    async def roteiro(pilot):
        await entrar(pilot, "admin")
        await aba(pilot, "f9")
        assert linha(pilot, "#tabela-alcadas", "media:gerente") == ["media", "gerente", "R$ 50.000,00", "R$ 50.000,00"]
        assert linha(pilot, "#tabela-alcadas", "micro:socio")[2:] == ["sem limite", "não se aplica"]
        await aba(pilot, "f10")
        await pilot.click("#editar-politica")
        await pilot.pause()
        await digitar(pilot, "#politica-escalonamento", "5")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "POL-14" in texto(pilot, "#erro-modal")
        await digitar(pilot, "#politica-2fa", "ROLE-APR")
        await digitar(pilot, "#politica-escalonamento", "50")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "ROLE-APR" in texto(pilot, "#politica-atual") and "50% do prazo" in texto(pilot, "#politica-atual")
        await aba(pilot, "f11")
        await pilot.click("#definir-segredo")
        await pilot.pause()
        await digitar(pilot, "#segredo-nome", "llm:ANTHROPIC_API_KEY")
        await colar(pilot, "#segredo-valor", valor)
        await pilot.click("#confirmar")
        await pilot.pause()
        assert linha(pilot, "#tabela-cofre", "llm:ANTHROPIC_API_KEY")[:2] == ["llm:ANTHROPIC_API_KEY", "admin"]
        assert valor not in tela(pilot)
        await aba(pilot, "f12")
        await pilot.click("#nova-empresa")
        await pilot.pause()
        await digitar(pilot, "#empresa-id", "alfa")
        await digitar(pilot, "#empresa-nome", "Alfa S.A.")
        await pilot.click("#confirmar")
        await pilot.pause()
        await pilot.click("#escopo-empresa")
        await pilot.pause()
        await digitar(pilot, "#escopo-usuario", "carla")
        await digitar(pilot, "#escopo-lista", "alfa,inexistente")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert "IAM-09" in texto(pilot, "#erro-modal")
        await digitar(pilot, "#escopo-lista", "alfa")
        await pilot.click("#confirmar")
        await pilot.pause()
        assert linha(pilot, "#tabela-empresas", "alfa")[3] == "admin, carla"  # o criador entra no escopo da primeira
    no_console(demo, roteiro)
    outro = servidor(demo)
    assert outro.politica() == {"exigir_2fa_para": ["ROLE-APR"], "escalonamento_percentual": 50}
    assert outro.cofre.ler("llm:ANTHROPIC_API_KEY") == valor
    assert outro.conta("carla")["empresas"] == ["alfa"]
    assert valor not in (demo / "contas.json").read_text(encoding="utf-8")

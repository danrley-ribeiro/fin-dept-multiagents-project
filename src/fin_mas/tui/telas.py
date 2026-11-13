"""Tela de entrada e formulários modais do console de acesso (a aplicação está em `tui/app.py`).

Nenhuma regra de acesso mora aqui: cada formulário recebe uma função `aplicar`, que chama o
SVC-IAM. Se o serviço nega (`AcessoNegado`, com a regra: IAM-02, IAM-05, IAM-06…), a mensagem
aparece em `#erro-modal` e o formulário **continua aberto**, para a pessoa corrigir e tentar de
novo; só fecha quando a alteração foi gravada ou a pessoa cancela (Esc). Enter no último campo
de texto confirma; nos outros, passa ao campo seguinte.

As únicas conferências locais são as de digitação, que o serviço não tem como fazer: senha
repetida igual e campo obrigatório preenchido (`Invalido`).

Ids estáveis (os testes de interface dirigem por eles):

- entrada: `#usuario`, `#senha`, `#entrar`; no primeiro uso também `#nome`, `#senha2`,
  `#criar-admin`; erros em `#erro-entrada`;
- todo formulário: `#confirmar`, `#cancelar`, `#erro-modal`;
- conta nova: `#conta-usuario`, `#conta-nome`, `#conta-papeis`, `#conta-cargo`, `#conta-pessoa`,
  `#conta-senha`, `#conta-senha2`;
- papéis: `#papeis`; vínculo: `#vinculo-pessoa`, `#vinculo-cargo`;
- senha temporária e troca da própria senha: `#senha-atual`, `#senha-nova`, `#senha-nova2`;
- exportação: `#arquivo`; confirmação: `#pergunta`, `#sim`, `#nao`.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, SelectionList, Static
from textual.widgets.selection_list import Selection

from fin_mas.core import permissoes
from fin_mas.services.iam import AcessoNegado
from fin_mas.services.selado import ArquivoComprometido, TravaOcupada

# Só entra no console quem administra o acesso ou audita (ao menos uma destas permissões).
PERMISSOES_CONSOLE = ("PERM-IAM-USUARIOS", "PERM-IAM-SESSOES", "PERM-AUD-VER")


class Invalido(ValueError):
    """Erro de digitação no formulário (não é negação de acesso)."""


# `AcessoNegado` é um `PermissionError`, portanto um `OSError`: `descrever` separa os casos.
ERROS = (AcessoNegado, Invalido, ArquivoComprometido, TravaOcupada, OSError)


def descrever(erro) -> str:
    """Texto do erro para a tela; a negação do serviço sai inteira, com a regra na frente."""
    if isinstance(erro, AcessoNegado):
        return f"acesso negado: {erro}"
    if isinstance(erro, Invalido):
        return f"corrija: {erro}"
    if isinstance(erro, ArquivoComprometido):
        return f"acesso negado: IAM-07: cadastro comprometido: {erro}"
    if isinstance(erro, TravaOcupada):
        return f"cadastro ocupado por outro processo, tente de novo: {erro}"
    return f"erro de arquivo: {erro}"


def _linha(rotulo: str, campo) -> Horizontal:
    return Horizontal(Label(rotulo, classes="rotulo"), campo, classes="linha")


def _papeis(marcados, id: str) -> SelectionList:
    return SelectionList(*[Selection(f"{papel}  {d['titulo']}", papel, papel in marcados)
                           for papel, d in permissoes.papeis_humanos().items()], id=id, compact=True)


def _cargos(atual, id: str) -> Select:
    conhecido = atual in permissoes.cargos()
    return Select([(c, c) for c in permissoes.cargos()], prompt="(sem cargo)", allow_blank=True,
                  value=atual if conhecido else Select.NULL, id=id, compact=True)


class TelaEntrada(Screen):
    """Login; com o cadastro vazio, o assistente de primeiro uso cria o primeiro administrador (IAM-01)."""

    AUTO_FOCUS = "#usuario"

    def __init__(self, aviso: str = ""):
        super().__init__()
        self.aviso = aviso
        self.primeiro_uso = False

    def compose(self) -> ComposeResult:
        aviso = self.aviso
        try:
            self.primeiro_uso = self.app.acesso.vazio()
        except ERROS as erro:  # IAM-07: cadastro comprometido não deixa ninguém entrar, nem recomeçar do zero
            aviso = descrever(erro)
        with Vertical(id="entrada"):
            yield Static("SMA de Controladoria — administração de acesso e auditoria", classes="titulo", markup=False)
            yield Static(f"cadastro: {self.app.pasta}", id="pasta-entrada", markup=False)
            if self.primeiro_uso:
                yield Static("Primeiro uso: ainda não há contas neste cadastro. Crie o primeiro administrador de "
                             "acesso (IAM-01). Senha: 12 caracteres ou mais (IAM-02).", id="primeiro-uso", markup=False)
                yield Input(placeholder="usuário (3 a 32 letras minúsculas, números, ponto ou sublinhado)", id="usuario")
                yield Input(placeholder="nome (padrão: Administração de Acesso)", id="nome")
                yield Input(placeholder="senha", password=True, id="senha")
                yield Input(placeholder="repita a senha", password=True, id="senha2")
                yield Button("Criar administrador", id="criar-admin", variant="primary")
            else:
                yield Static("Entre com uma conta de administrador de acesso ou de auditor.", markup=False)
                yield Input(placeholder="usuário", id="usuario")
                yield Input(placeholder="senha", password=True, id="senha")
                yield Button("Entrar", id="entrar", variant="primary")
            yield Static(aviso, id="erro-entrada", markup=False)
        yield Footer()

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        self._submeter()

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        if evento.input.id == ("senha2" if self.primeiro_uso else "senha"):
            self._submeter()
        else:
            self.focus_next()

    def _valor(self, id: str) -> str:
        return self.query_one(f"#{id}", Input).value

    def _submeter(self) -> None:
        acesso, usuario, senha = self.app.acesso, self._valor("usuario").strip(), self._valor("senha")
        try:
            if self.primeiro_uso:
                if senha != self._valor("senha2"):
                    raise Invalido("as senhas digitadas não conferem")
                acesso.iniciar(usuario, self._valor("nome").strip() or "Administração de Acesso", senha)
            sessao, _ = acesso.autenticar(usuario, senha, origem="tui")
            if not any(sessao.pode(p) for p in PERMISSOES_CONSOLE):
                acesso.sair(sessao)
                acesso.registrar("permissao", usuario, "negado", regra="IAM-05", origem="tui",
                                 permissao=" ou ".join(PERMISSOES_CONSOLE))
                raise AcessoNegado("IAM-05", f"{usuario} não administra o acesso nem audita; este console é só para "
                                             f"isso (a plataforma é usada pelo dashboard web)")
        except ERROS as erro:
            for campo in self.query("Input"):
                if campo.password:
                    campo.value = ""
            try:
                virou_login = self.primeiro_uso and not acesso.vazio()
            except ERROS:
                virou_login = False
            if virou_login:  # outro processo criou o primeiro administrador no meio tempo: o assistente não vale mais
                self.app.switch_screen(TelaEntrada(descrever(erro)))
                return
            self.query_one("#erro-entrada", Static).update(descrever(erro))
            return
        self.app.entrar(sessao)


class Confirmar(ModalScreen):
    """Confirmação de ação destrutiva. Devolve True só no "Sim"; o foco começa no "Não"."""

    BINDINGS = [Binding("s", "responder(True)", "Sim"), Binding("n,escape", "responder(False)", "Não")]
    AUTO_FOCUS = "#nao"

    def __init__(self, pergunta: str):
        super().__init__()
        self.pergunta = pergunta

    def compose(self) -> ComposeResult:
        with Vertical(classes="caixa"):
            yield Static(self.pergunta, id="pergunta", markup=False)
            with Horizontal(classes="botoes"):
                yield Button("Sim (s)", id="sim", variant="error")
                yield Button("Não (n)", id="nao")

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        self.dismiss(evento.button.id == "sim")

    def action_responder(self, resposta: bool) -> None:
        self.dismiss(resposta)


class Formulario(ModalScreen):
    """Base dos formulários: `campos()` desenha, `valores()` lê, `aplicar(**valores)` grava pelo serviço."""

    BINDINGS = [Binding("escape", "cancelar", "Cancelar")]
    AUTO_FOCUS = "Input, SelectionList"

    def __init__(self, aplicar, titulo: str):
        super().__init__()
        self.aplicar = aplicar
        self.titulo = titulo

    def compose(self) -> ComposeResult:
        with VerticalScroll(classes="caixa"):
            yield Static(self.titulo, classes="titulo", markup=False)
            yield from self.campos()
            yield Static("", id="erro-modal", markup=False)
            with Horizontal(classes="botoes"):
                yield Button("Confirmar", id="confirmar", variant="primary")
                yield Button("Cancelar (Esc)", id="cancelar")

    def campos(self) -> ComposeResult:
        yield from ()

    def valores(self) -> dict:
        return {}

    def _texto(self, id: str, limpar: bool = True) -> str:
        valor = self.query_one(f"#{id}", Input).value
        return valor.strip() if limpar else valor

    def _senha_repetida(self, id: str) -> str:
        senha = self._texto(id, limpar=False)
        if senha != self._texto(id + "2", limpar=False):
            raise Invalido("as senhas digitadas não conferem")
        return senha

    def _cargo(self, id: str):
        valor = self.query_one(f"#{id}", Select).value
        return valor if isinstance(valor, str) else None

    def _marcados(self, id: str) -> list:
        marcados = set(self.query_one(f"#{id}", SelectionList).selected)
        return [papel for papel in permissoes.papeis_humanos() if papel in marcados]

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        if evento.button.id == "confirmar":
            self._confirmar()
        else:
            self.dismiss(None)

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        if evento.input is self.query(Input).last():  # Enter no último campo confirma; nos outros, avança
            self._confirmar()
        else:
            self.focus_next()

    def action_cancelar(self) -> None:
        self.dismiss(None)

    def _confirmar(self) -> None:
        try:
            resultado = self.aplicar(**self.valores())
        except ERROS as erro:
            self.query_one("#erro-modal", Static).update(descrever(erro))
            return
        self.dismiss(True if resultado is None else resultado)


class FormConta(Formulario):
    """Conta nova: nasce com senha temporária, trocada pela pessoa na primeira entrada (IAM-02)."""

    def campos(self) -> ComposeResult:
        yield _linha("usuário", Input(id="conta-usuario", compact=True))
        yield _linha("nome", Input(id="conta-nome", compact=True))
        yield Label("papéis (espaço marca; ROLE-ADM e ROLE-APR não se acumulam: IAM-06)")
        yield _papeis((), "conta-papeis")
        yield _linha("cargo (alçada, POL-02)", _cargos(None, "conta-cargo"))
        yield _linha("pessoa no ERP", Input(id="conta-pessoa", compact=True))
        yield _linha("senha temporária", Input(password=True, id="conta-senha", compact=True))
        yield _linha("repita a senha", Input(password=True, id="conta-senha2", compact=True))

    def valores(self) -> dict:
        papeis = self._marcados("conta-papeis")
        if not papeis:
            raise Invalido("marque ao menos um papel (conta sem papel não faz nada)")
        return {"usuario": self._texto("conta-usuario"), "nome": self._texto("conta-nome") or self._texto("conta-usuario"),
                "papeis": papeis, "cargo": self._cargo("conta-cargo"), "pessoa_erp": self._texto("conta-pessoa") or None,
                "senha": self._senha_repetida("conta-senha")}


class FormPapeis(Formulario):
    def __init__(self, aplicar, conta: dict):
        super().__init__(aplicar, f"Papéis de {conta['usuario']} ({conta['nome']})")
        self.conta = conta

    def campos(self) -> ComposeResult:
        yield Label("espaço marca ou desmarca; ROLE-ADM e ROLE-APR não se acumulam (IAM-06)")
        yield _papeis(self.conta["papeis"], "papeis")

    def valores(self) -> dict:
        return {"papeis": self._marcados("papeis")}


class FormVinculo(Formulario):
    """Pessoa do ERP e cargo da conta: o que a segregação de funções e a alçada (POL-02) conferem."""

    def __init__(self, aplicar, conta: dict):
        super().__init__(aplicar, f"Vínculo de {conta['usuario']} ({conta['nome']})")
        self.conta = conta

    def campos(self) -> ComposeResult:
        yield _linha("pessoa no ERP", Input(self.conta.get("pessoa_erp") or "", id="vinculo-pessoa", compact=True))
        yield _linha("cargo (alçada, POL-02)", _cargos(self.conta.get("cargo"), "vinculo-cargo"))

    def valores(self) -> dict:
        return {"pessoa_erp": self._texto("vinculo-pessoa") or None, "cargo": self._cargo("vinculo-cargo")}


class FormSenha(Formulario):
    """Senha temporária definida pelo administrador (as sessões da conta caem)."""

    def campos(self) -> ComposeResult:
        yield _linha("senha temporária", Input(password=True, id="senha-nova", compact=True))
        yield _linha("repita a senha", Input(password=True, id="senha-nova2", compact=True))

    def valores(self) -> dict:
        return {"nova": self._senha_repetida("senha-nova")}


class FormTrocarSenha(Formulario):
    """Troca da própria senha; obrigatória quando a conta entrou com senha temporária."""

    def campos(self) -> ComposeResult:
        yield _linha("senha atual", Input(password=True, id="senha-atual", compact=True))
        yield _linha("senha nova", Input(password=True, id="senha-nova", compact=True))
        yield _linha("repita a nova", Input(password=True, id="senha-nova2", compact=True))

    def valores(self) -> dict:
        return {"atual": self._texto("senha-atual", limpar=False), "nova": self._senha_repetida("senha-nova")}


class FormArquivo(Formulario):
    """Caminho do arquivo de exportação (nunca sobrescreve: quem grava recusa arquivo que já existe)."""

    def __init__(self, aplicar, titulo: str, padrao: str):
        super().__init__(aplicar, titulo)
        self.padrao = padrao

    def campos(self) -> ComposeResult:
        yield _linha("arquivo (JSONL)", Input(self.padrao, id="arquivo", compact=True))

    def valores(self) -> dict:
        return {"caminho": self._texto("arquivo")}

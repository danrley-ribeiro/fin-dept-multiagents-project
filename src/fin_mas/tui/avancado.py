"""Abas e formulários do acesso avançado no console (DSM4, ADR-012). A tela é `TelaConsole` (`tui/app.py`).

Nenhuma regra mora aqui: cada ação chama o SVC-IAM e mostra a negação com a regra.

- F6 Segundo fator (toda conta): ativar (o segredo e a URI aparecem **uma vez**, num formulário
  que pede o primeiro código; depois os dez códigos de recuperação aparecem **uma vez**) e
  desativar (pede a senha atual e um código válido);
- F7 Delegações (PERM-APR-DELEGAR): lista, nova delegação (para, horas, teto, competência), revogar;
- F9 Alçadas (toda conta): alçada por cargo e limite de dupla aprovação de cada porte;
- F10 Política do cadastro (PERM-IAM-POLITICA): segundo fator obrigatório por papel e escalonamento;
- F11 Cofre (PERM-MOD-SEGREDOS): nomes dos segredos (nunca o valor), definir e remover;
- F12 Empresas (PERM-IAM-EMPRESAS): lista, nova empresa, escopo de uma conta.

Ids estáveis (os testes de interface dirigem por eles): `#estado-2fa`, `#ativar-2fa`,
`#desativar-2fa`, `#segredo-2fa`, `#codigo-2fa`, `#senha-2fa`, `#codigos-recuperacao`, `#fechar-codigos`,
`#tabela-delegacoes`, `#nova-delegacao`, `#revogar-delegacao`, `#delegacao-para`, `#delegacao-horas`,
`#delegacao-teto`, `#delegacao-competencia`, `#tabela-alcadas`, `#politica-atual`, `#editar-politica`,
`#politica-2fa`, `#politica-escalonamento`, `#tabela-cofre`, `#definir-segredo`, `#remover-segredo`,
`#segredo-nome`, `#segredo-valor`, `#tabela-empresas`, `#nova-empresa`, `#escopo-empresa`,
`#empresa-id`, `#empresa-nome`, `#empresa-porte`, `#escopo-usuario`, `#escopo-lista`; na entrada,
`#codigo-entrada`.
"""
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static, TabPane

from fin_mas.env.portes import PORTES, perfil
from fin_mas.services.politica import _reais
from fin_mas.tui.telas import Formulario, Invalido, _linha

ABAS_AVANCADAS = {
    "aba-2fa": ("F6 Segundo fator", None, None, "ativar ou desativar o segundo fator TOTP da sua conta (IAM-08)"),
    "aba-delegacoes": ("F7 Delegações", "PERM-APR-DELEGAR", "tabela-delegacoes",
                       "nova delegação da sua alçada (prazo, teto, competência) · revogar a selecionada (POL-11)"),
    "aba-alcadas": ("F9 Alçadas", None, "tabela-alcadas",
                    "somente leitura: models/portes.yaml (POL-10 alçada por cargo, POL-12 dupla aprovação)"),
    "aba-politica": ("F10 Política", "PERM-IAM-POLITICA", None,
                     "segundo fator obrigatório por papel (IAM-08) e escalonamento de tickets (POL-14)"),
    "aba-cofre": ("F11 Cofre", "PERM-MOD-SEGREDOS", "tabela-cofre",
                  "definir ou remover chaves de LLM e credenciais; o valor nunca aparece (IAM-10)"),
    "aba-empresas": ("F12 Empresas", "PERM-IAM-EMPRESAS", "tabela-empresas",
                     "nova empresa · escopo de empresas de uma conta (IAM-09)"),
}
BINDINGS_AVANCADAS = [Binding("f6", "aba('aba-2fa')", "Segundo fator", show=False),
                      Binding("f7", "aba('aba-delegacoes')", "Delegações", show=False),
                      Binding("f9", "aba('aba-alcadas')", "Alçadas", show=False),
                      Binding("f10", "aba('aba-politica')", "Política", show=False),
                      Binding("f11", "aba('aba-cofre')", "Cofre", show=False),
                      Binding("f12", "aba('aba-empresas')", "Empresas", show=False)]
BOTOES_AVANCADOS = {"ativar-2fa": "ativar_2fa", "desativar-2fa": "desativar_2fa", "nova-delegacao": "nova_delegacao",
                    "revogar-delegacao": "revogar_delegacao", "editar-politica": "editar_politica",
                    "definir-segredo": "definir_segredo", "remover-segredo": "remover_segredo",
                    "nova-empresa": "nova_empresa", "escopo-empresa": "escopo_empresa"}
COLUNAS_AVANCADAS = {
    "tabela-delegacoes": ("id", "de", "para", "teto", "até", "escopo", "situação"),
    "tabela-alcadas": ("porte", "cargo", "alçada", "dupla aprovação acima de"),
    "tabela-cofre": ("segredo", "definido por", "quando"),
    "tabela-empresas": ("id", "nome", "porte", "contas no escopo"),
}


class FormCodigo(Formulario):
    """Pede um código TOTP (ou de recuperação); com `segredo`, mostra-o (uma vez) para o cadastro no aplicativo."""

    def __init__(self, aplicar, titulo: str, segredo: str | None = None, uri: str | None = None,
                 pedir_senha: bool = False):
        super().__init__(aplicar, titulo)
        self.segredo, self.uri, self.pedir_senha = segredo, uri, pedir_senha

    def campos(self) -> ComposeResult:
        if self.segredo:
            yield Static(f"segredo (cadastre no aplicativo autenticador; não aparece de novo):\n{self.segredo}\n{self.uri}",
                         id="segredo-2fa", markup=False)
        if self.pedir_senha:  # desativar exige a senha atual além do código (IAM-08)
            yield _linha("senha atual", Input(id="senha-2fa", password=True, compact=True))
        yield _linha("código", Input(id="codigo-2fa", compact=True))

    def valores(self) -> dict:
        codigo = self._texto("codigo-2fa")
        if not codigo:
            raise Invalido("digite o código do aplicativo (ou um código de recuperação)")
        if not self.pedir_senha:
            return {"codigo": codigo}
        senha = self._texto("senha-2fa", limpar=False)
        if not senha:
            raise Invalido("digite a sua senha atual")
        return {"codigo": codigo, "senha": senha}


class MostrarCodigos(ModalScreen):
    """Os códigos de recuperação, mostrados uma única vez."""

    BINDINGS = [Binding("escape", "fechar", "Fechar")]
    AUTO_FOCUS = "#fechar-codigos"

    def __init__(self, codigos: list[str]):
        super().__init__()
        self.codigos = codigos

    def compose(self) -> ComposeResult:
        with Vertical(classes="caixa"):
            yield Static("Segundo fator ativo. Guarde os códigos de recuperação: cada um vale uma vez e eles não "
                         "aparecem de novo.", classes="titulo", markup=False)
            yield Static("\n".join(self.codigos), id="codigos-recuperacao", markup=False)
            with Horizontal(classes="botoes"):
                yield Button("Guardei os códigos", id="fechar-codigos", variant="primary")

    def on_button_pressed(self, evento) -> None:
        self.dismiss(True)

    def action_fechar(self) -> None:
        self.dismiss(True)


class FormDelegacao(Formulario):
    def campos(self) -> ComposeResult:
        yield _linha("para (conta aprovadora)", Input(id="delegacao-para", compact=True))
        yield _linha("prazo (horas)", Input("8", id="delegacao-horas", compact=True))
        yield _linha("teto (centavos)", Input(id="delegacao-teto", compact=True))
        yield _linha("competência (AAAA-MM)", Input(id="delegacao-competencia", compact=True))

    def valores(self) -> dict:
        try:
            horas, teto = float(self._texto("delegacao-horas")), int(self._texto("delegacao-teto"))
        except ValueError:
            raise Invalido("prazo em horas e teto em centavos são números") from None
        return {"para": self._texto("delegacao-para"), "horas": horas, "teto": teto,
                "competencia": self._texto("delegacao-competencia")}


class FormPolitica(Formulario):
    def __init__(self, aplicar, politica: dict):
        super().__init__(aplicar, "Política do cadastro")
        self.politica = politica

    def campos(self) -> ComposeResult:
        yield _linha("2FA obrigatório para", Input(",".join(self.politica["exigir_2fa_para"]), id="politica-2fa",
                                                   placeholder="ROLE-ADM,ROLE-APR (vazio: ninguém)", compact=True))
        pct = self.politica["escalonamento_percentual"]
        yield _linha("escalonamento (% do prazo)", Input("" if pct is None else str(pct), id="politica-escalonamento",
                                                         placeholder="10 a 90 (vazio: desligado)", compact=True))

    def valores(self) -> dict:
        texto = self._texto("politica-escalonamento")
        try:
            pct = int(texto) if texto else None
        except ValueError:
            raise Invalido("escalonamento: número inteiro de 10 a 90, ou vazio") from None
        return {"exigir_2fa_para": [p.strip() for p in self._texto("politica-2fa").split(",") if p.strip()],
                "escalonamento_percentual": pct}


class FormSegredo(Formulario):
    def campos(self) -> ComposeResult:
        yield _linha("nome", Input(placeholder="llm:ANTHROPIC_API_KEY", id="segredo-nome", compact=True))
        yield _linha("valor (não aparece)", Input(password=True, id="segredo-valor", compact=True))

    def valores(self) -> dict:
        return {"nome": self._texto("segredo-nome"), "valor": self._texto("segredo-valor", limpar=False)}


class FormEmpresa(Formulario):
    def campos(self) -> ComposeResult:
        yield _linha("id (vira dados/<id>/)", Input(id="empresa-id", compact=True))
        yield _linha("nome", Input(id="empresa-nome", compact=True))
        yield _linha(f"porte ({', '.join(PORTES)})", Input("media", id="empresa-porte", compact=True))

    def valores(self) -> dict:
        return {"empresa": self._texto("empresa-id"), "nome": self._texto("empresa-nome"),
                "porte": self._texto("empresa-porte")}


class FormEscopo(Formulario):
    def campos(self) -> ComposeResult:
        yield _linha("conta", Input(id="escopo-usuario", compact=True))
        yield _linha("empresas (vírgula)", Input(id="escopo-lista", compact=True))

    def valores(self) -> dict:
        return {"usuario": self._texto("escopo-usuario"),
                "empresas": [e.strip() for e in self._texto("escopo-lista").split(",") if e.strip()]}


class AbasAvancadas:
    """Mistura de `TelaConsole`: desenho, carga e ações das abas do acesso avançado."""

    def abas_avancadas(self) -> ComposeResult:
        if "aba-2fa" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-2fa"][0], id="aba-2fa"):
                with Horizontal(classes="barra"):
                    yield Button("Ativar", id="ativar-2fa", compact=True)
                    yield Button("Desativar", id="desativar-2fa", compact=True)
                yield Static("", id="estado-2fa", markup=False)
        if "aba-delegacoes" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-delegacoes"][0], id="aba-delegacoes"):
                with Horizontal(classes="barra"):
                    yield Button("Nova delegação", id="nova-delegacao", compact=True)
                    yield Button("Revogar", id="revogar-delegacao", compact=True)
                yield DataTable(id="tabela-delegacoes", cursor_type="row", zebra_stripes=True)
        if "aba-alcadas" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-alcadas"][0], id="aba-alcadas"):
                yield DataTable(id="tabela-alcadas", cursor_type="row", zebra_stripes=True)
        if "aba-politica" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-politica"][0], id="aba-politica"):
                with Horizontal(classes="barra"):
                    yield Button("Editar política", id="editar-politica", compact=True)
                yield Static("", id="politica-atual", markup=False)
        if "aba-cofre" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-cofre"][0], id="aba-cofre"):
                with Horizontal(classes="barra"):
                    yield Button("Definir segredo", id="definir-segredo", compact=True)
                    yield Button("Remover", id="remover-segredo", compact=True)
                yield DataTable(id="tabela-cofre", cursor_type="row", zebra_stripes=True)
        if "aba-empresas" in self.abas_extras:
            with TabPane(ABAS_AVANCADAS["aba-empresas"][0], id="aba-empresas"):
                with Horizontal(classes="barra"):
                    yield Button("Nova empresa", id="nova-empresa", compact=True)
                    yield Button("Escopo de uma conta", id="escopo-empresa", compact=True)
                yield DataTable(id="tabela-empresas", cursor_type="row", zebra_stripes=True)

    def _carregar_avancado(self, sessao) -> None:
        acesso = self.app.acesso
        if self.query("#estado-2fa"):
            sf = (acesso.conta(sessao.usuario) or {}).get("segundo_fator") or {}
            exigido = " A política do cadastro exige o segundo fator para a sua conta." if sessao.pendente_2fa else ""
            self.query_one("#estado-2fa", Static).update(
                (f"segundo fator ATIVO; {sf.get('codigos_restantes', 0)} código(s) de recuperação restante(s)"
                 if sf.get("ativo") else "segundo fator desativado") + "." + exigido)
        tabela = self._tabela("tabela-delegacoes")
        if tabela is not None:
            todas = acesso.delegacoes(None if sessao.pode("PERM-IAM-USUARIOS") else sessao.usuario)
            self._preencher(tabela, [(d["id"], (d["id"], d["de"], d["para"], _reais(d["teto"]), d["ate"],
                                                ", ".join(f"{k} {v}" for k, v in d["escopo"].items()), d["situacao"]))
                                     for d in todas])
        tabela = self._tabela("tabela-alcadas")
        if tabela is not None and not tabela.row_count:
            linhas = []
            for porte in PORTES:
                p = perfil(porte)
                dupla = "não se aplica" if p.get("dupla_aprovacao") is None else _reais(p["dupla_aprovacao"])
                linhas += [(f"{porte}:{cargo}", (porte, cargo, _reais(limite), dupla))
                           for cargo, limite in p["limites_alcada"].items()]
            self._preencher(tabela, linhas)
        if self.query("#politica-atual"):
            pol = acesso.politica()
            self.query_one("#politica-atual", Static).update(
                f"segundo fator obrigatório para: {', '.join(pol['exigir_2fa_para']) or 'ninguém'}\n"
                f"escalonamento: {str(pol['escalonamento_percentual']) + '% do prazo' if pol['escalonamento_percentual'] else 'desligado'}")
        tabela = self._tabela("tabela-cofre")
        if tabela is not None:
            self._preencher(tabela, [(s["nome"], (s["nome"], s["por"], s["em"])) for s in acesso.segredos(sessao)])
        tabela = self._tabela("tabela-empresas")
        if tabela is not None:
            contas = acesso.contas()
            self._preencher(tabela, [(e["id"], (e["id"], e["nome"], e["porte"],
                                                ", ".join(c["usuario"] for c in contas if e["id"] in (c.get("empresas") or []))
                                                or "-")) for e in acesso.empresas().values()])

    # ---- ações ---------------------------------------------------------------------------------
    def action_ativar_2fa(self) -> None:
        if self._ator() is None:
            return
        acesso = self.app.acesso

        def iniciar():
            try:
                return acesso.iniciar_2fa(self._vivo())
            except Exception as erro:  # noqa: BLE001 (a negação vai para a tela)
                self._avisar(f"acesso negado: {erro}", negado=True)
                return None
        info = iniciar()
        if info is None:
            return

        def ao_confirmar(codigos) -> None:
            if isinstance(codigos, list):
                self.app.push_screen(MostrarCodigos(codigos), lambda _: self._feito("segundo fator ativado")(True))
            else:
                self._recarregar()
        self.app.push_screen(FormCodigo(lambda codigo: acesso.confirmar_2fa(self._vivo(), codigo),
                                        "Ativar o segundo fator: cadastre o segredo e digite o primeiro código",
                                        info["segredo"], info["uri"]), ao_confirmar)

    def action_desativar_2fa(self) -> None:
        if self._ator() is not None:
            self.app.push_screen(FormCodigo(lambda codigo, senha: self.app.acesso.desativar_2fa(self._vivo(), codigo, senha),
                                            "Desativar o segundo fator: confirme com a senha atual e um código válido",
                                            pedir_senha=True),
                                 self._feito("segundo fator desativado"))

    def action_nova_delegacao(self) -> None:
        if self._ator("PERM-APR-DELEGAR") is None:
            return
        acesso = self.app.acesso
        self.app.push_screen(
            FormDelegacao(lambda para, horas, teto, competencia: acesso.delegar(
                self._vivo(), para, ate=acesso.relogio() + horas * 3600, teto=teto, competencia=competencia or None),
                "Nova delegação da sua alçada (sem subdelegação; expira sozinha)"),
            self._feito(lambda d: f"delegação {d['id']} para {d['para']} criada"))

    def action_revogar_delegacao(self) -> None:
        if self._ator() is None:
            return
        did = self._chave(self._tabela("tabela-delegacoes"))
        if did is None:
            self._avisar("selecione uma delegação", negado=True)
            return
        self._confirmar(f"Revogar a delegação {did}?", lambda ator: self.app.acesso.revogar_delegacao(ator, did),
                        f"delegação {did} revogada")

    def action_editar_politica(self) -> None:
        if self._ator("PERM-IAM-POLITICA") is None:
            return
        acesso = self.app.acesso
        self.app.push_screen(FormPolitica(lambda **campos: acesso.definir_politica(self._vivo(), **campos),
                                          acesso.politica()),
                             self._feito("política do cadastro alterada"))

    def action_definir_segredo(self) -> None:
        if self._ator("PERM-MOD-SEGREDOS") is None:
            return
        self.app.push_screen(FormSegredo(lambda nome, valor: self.app.acesso.definir_segredo(self._vivo(), nome, valor),
                                         "Definir segredo no cofre (o valor não é mostrado nem aqui nem depois)"),
                             self._feito(lambda r: f"segredo {r['nome']} guardado no cofre"))

    def action_remover_segredo(self) -> None:
        if self._ator("PERM-MOD-SEGREDOS") is None:
            return
        nome = self._chave(self._tabela("tabela-cofre"))
        if nome is None:
            self._avisar("selecione um segredo", negado=True)
            return
        self._confirmar(f"Remover o segredo {nome} do cofre?", lambda ator: self.app.acesso.remover_segredo(ator, nome),
                        f"segredo {nome} removido")

    def action_nova_empresa(self) -> None:
        if self._ator("PERM-IAM-EMPRESAS") is None:
            return
        self.app.push_screen(FormEmpresa(lambda empresa, nome, porte: self.app.acesso.criar_empresa(
            self._vivo(), empresa, nome, porte), "Nova empresa cliente (dados, memória e trace em dados/<id>/)"),
            self._feito(lambda e: f"empresa {e['id']} criada"))

    def action_escopo_empresa(self) -> None:
        if self._ator("PERM-IAM-EMPRESAS") is None:
            return
        self.app.push_screen(FormEscopo(lambda usuario, empresas: self.app.acesso.definir_escopo(
            self._vivo(), usuario, empresas), "Escopo de empresas de uma conta"),
            self._feito(lambda c: f"escopo de {c['usuario']}: {', '.join(c.get('empresas') or []) or 'nenhuma'}"))


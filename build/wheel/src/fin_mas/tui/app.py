"""Console de administração de acesso e de auditoria (Textual) — SVC-IAM, ADR-009, DSM3.

    python -m fin_mas acesso --acesso PASTA tui

Para quem é: o **administrador de acesso** e o **auditor**. A TUI gerencia; a plataforma (a
simulação dos agentes) é usada pelo dashboard web e não aparece aqui. O console grava nos
mesmos arquivos selados que o servidor lê (`contas.json`, `sessoes.json`, `trilha.jsonl`):
bloquear uma conta ou revogar uma sessão aqui derruba a pessoa no dashboard na requisição
seguinte. Nada do SVC-IAM é reimplementado: toda alteração é uma chamada a `services/iam.py`.

Regras do console:

- só entra quem tem ao menos uma de `PERM-IAM-USUARIOS`, `PERM-IAM-SESSOES`, `PERM-AUD-VER`;
  os demais são recusados na entrada com IAM-05 (e a recusa vai para a trilha);
- cada aba só existe para quem tem a permissão dela: o auditor vê Trilha e Traces; se ele
  aperta a tecla de uma ação de administração, a negação IAM-05 do serviço aparece na tela e
  fica na trilha (negado por padrão, sem atalho escondido);
- toda negação do serviço aparece com a regra (IAM-02 senha fraca, IAM-03 senha errada ou
  bloqueio, IAM-05 sem permissão, IAM-06 papéis incompatíveis e último administrador, IAM-07
  cadastro comprometido): em `#erro-entrada` no login, em `#erro-modal` nos formulários e em
  `#mensagem` no console;
- a sessão do console é conferida de novo no cadastro antes de cada ação e a cada recarga
  (`sessao_por_id`): revogada, expirada ou com 15 minutos sem uso (IAM-04), o console volta à
  tela de entrada; se os papéis da conta mudaram, as abas são remontadas (ou, sem permissão
  de administração nem de auditoria, a conta sai com IAM-05);
- quem entra com senha temporária troca a senha antes de qualquer outra coisa (IAM-02);
- ações destrutivas (bloquear, desativar, revogar) pedem confirmação, com o foco no "Não";
- os dados são relidos do disco depois de cada ação e por Ctrl+R (o servidor grava no meio tempo);
- a exportação nunca sobrescreve um arquivo existente, exige `PERM-AUD-EXPORTAR` e fica
  registrada na trilha (`auditoria_exportada`, como no servidor).

Abas (F1 a F5) e tabelas:

1. Usuários (`#tabela-usuarios`): contas com estado, papéis, cargo e pessoa do ERP;
2. Papéis × permissões (`#tabela-matriz`): matriz somente leitura dos modelos e o quadro
   `#incompativeis` (contas que violam IAM-06 e contas que solicitam e aprovam: aviso da POL-13);
3. Sessões (`#tabela-sessoes`): abertas e encerradas, com a situação;
4. Trilha de acesso (`#tabela-trilha`): filtros por ator, evento e resultado, integridade em
   `#integridade-trilha` (ÍNTEGRA ou ADULTERADA, com o motivo) e exportação do recorte;
5. Traces (`#tabela-trace`): abre um JSONL de simulação, mostra em `#trace-estado` se cadeia e
   selo conferem, filtra (agente, tipo, tarefa, texto), explica o registro selecionado em
   `#explicacao`, confere os invariantes em `#invariantes` e exporta o recorte.

Botões (os mesmos comandos das teclas, para o mouse e para os testes de interface): `#nova-conta`,
`#editar-papeis`, `#vinculo`, `#redefinir-senha`, `#bloquear`, `#desbloquear`, `#desativar`;
`#revogar-sessao`, `#revogar-usuario`; `#verificar-trilha`, `#exportar-trilha`; `#abrir-trace`,
`#explicar`, `#exportar-trace`. Campos: `#trilha-ator`, `#trilha-evento`, `#trilha-resultado`
(`#resultado-todos`, `#resultado-ok`, `#resultado-negado`), `#trace-caminho`, `#trace-agente`,
`#trace-tipo`, `#trace-tarefa`, `#trace-texto`. Barra: `#status` (quem entrou e a pasta do
cadastro), `#mensagem` (resultado da última ação) e `#atalhos` (teclas da aba ativa). Os ids
da entrada e dos formulários estão em `tui/telas.py`.

Atalhos de teclado:

    em qualquer lugar   Ctrl+Q  encerra a sessão e sai        Ctrl+R  relê os dados do disco
                        F1..F5  troca de aba                  F8      troca a própria senha
                        /       vai para os filtros da aba    Esc     volta para a tabela
    Usuários            n  nova conta       p  papéis         v  vínculo (pessoa do ERP, cargo)
                        s  redefinir senha  b  bloquear       d  desbloquear      x  desativar
    Sessões             r  revogar a sessão selecionada       t  revogar todas as vivas do usuário
    Trilha de acesso    i  verificar integridade              e  exportar o recorte
    Traces              a  caminho do arquivo (Enter abre)    l ou Enter  explicar o registro
                        i  ler e conferir de novo             e  exportar o recorte
    formulários         Enter confirma, Esc cancela; confirmações: s = sim, n ou Esc = não

As letras valem com o foco numa tabela (dentro de um campo de texto elas são digitadas); as
teclas de função e as com Ctrl valem sempre. O filtro da trilha aplica enquanto se digita; o
do trace, que relê todos os registros, aplica com Enter.
"""
import contextlib
import json
import time
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, RadioButton, RadioSet, Static, TabbedContent, TabPane

from fin_mas import invariantes
from fin_mas.core import permissoes
from fin_mas.services import consulta
from fin_mas.services.audit import AuditLog, TraceAdulterado, formatar
from fin_mas.services.explicacao import explicar
from fin_mas.services.iam import Acesso, AcessoNegado
from fin_mas.services.trilha import TrilhaAdulterada
from fin_mas.tui.avancado import (ABAS_AVANCADAS, BINDINGS_AVANCADAS, BOTOES_AVANCADOS, COLUNAS_AVANCADAS,
                                  AbasAvancadas)
from fin_mas.tui.telas import (ERROS, PERMISSOES_CONSOLE, Confirmar, FormArquivo, FormConta, FormPapeis, FormSenha,
                               FormTrocarSenha, FormVinculo, Invalido, TelaEntrada, descrever)

LIMITE_LINHAS = 3000  # linhas desenhadas por tabela; o recorte exportado é sempre completo

# aba -> (título, permissão que dá a aba, tabela principal, atalhos mostrados em `#atalhos`)
ABAS = {
    "aba-usuarios": ("F1 Usuários", "PERM-IAM-USUARIOS", "tabela-usuarios",
                     "n nova conta · p papéis · v vínculo · s redefinir senha · b bloquear · d desbloquear · "
                     "x desativar"),
    "aba-papeis": ("F2 Papéis × permissões", "PERM-IAM-PAPEIS", "tabela-matriz",
                   "somente leitura: models/roles.yaml e models/permissions.yaml"),
    "aba-sessoes": ("F3 Sessões", "PERM-IAM-SESSOES", "tabela-sessoes",
                    "r revogar a sessão selecionada · t revogar todas as vivas do usuário"),
    "aba-trilha": ("F4 Trilha de acesso", "PERM-AUD-VER", "tabela-trilha",
                   "i verificar integridade · e exportar o recorte · / filtros · Esc tabela"),
    "aba-traces": ("F5 Traces", "PERM-AUD-VER", "tabela-trace",
                   "a caminho do arquivo · l ou Enter explicar · i conferir de novo · e exportar o recorte · / filtros"),
}
# ação que só vale numa aba (com outra aba ativa a tecla não faz nada)
ACOES_DA_ABA = {
    "aba-usuarios": ("nova_conta", "papeis", "vinculo", "redefinir_senha", "bloquear", "desbloquear", "desativar"),
    "aba-sessoes": ("revogar", "revogar_usuario"),
    "aba-trilha": ("verificar", "exportar", "filtros"),
    "aba-traces": ("verificar", "exportar", "filtros", "abrir_trace", "explicar"),
}
BOTOES = {"nova-conta": "nova_conta", "editar-papeis": "papeis", "vinculo": "vinculo", "redefinir-senha": "redefinir_senha",
          "bloquear": "bloquear", "desbloquear": "desbloquear", "desativar": "desativar", "revogar-sessao": "revogar",
          "revogar-usuario": "revogar_usuario", "verificar-trilha": "verificar", "exportar-trilha": "exportar",
          "explicar": "explicar", "exportar-trace": "exportar"}
COLUNAS = {
    "tabela-usuarios": ("usuário", "nome", "estado", "papéis", "cargo", "pessoa do ERP", "observações"),
    "tabela-sessoes": ("id", "usuário", "origem", "criada", "vista", "expira", "situação"),
    "tabela-trilha": ("#", "quando", "evento", "ator", "resultado", "regra", "detalhes"),
    "tabela-trace": ("#", "tipo", "agente", "registro"),
}
ABAS.update(ABAS_AVANCADAS)  # DSM4: F6 a F12, acesso avançado (tui/avancado.py)
BOTOES.update(BOTOES_AVANCADOS)
COLUNAS.update(COLUNAS_AVANCADAS)
FORA_DOS_DETALHES = ("seq", "t", "evento", "ator", "resultado", "regra", "_hash")
SOLICITA_E_APROVA = {"ROLE-SOL", "ROLE-APR"}
ERROS_DE_FORMATO = (KeyError, TypeError, AttributeError, ValueError)  # arquivo que não é um trace do sistema


def _quando(t) -> str:
    try:
        return time.strftime("%d/%m %H:%M:%S", time.localtime(t))
    except (TypeError, ValueError, OverflowError, OSError):
        return "-"


def _estado(conta: dict, agora: float) -> str:
    if conta["estado"] == "bloqueada" and conta.get("bloqueada_ate"):
        return f"bloqueada até {time.strftime('%H:%M', time.localtime(conta['bloqueada_ate']))} (senhas erradas)" \
            if agora < conta["bloqueada_ate"] else "bloqueada (prazo vencido: a próxima entrada libera)"
    return conta["estado"]


def _observacoes(conta: dict) -> str:
    notas = (["senha temporária"] if conta.get("trocar_senha") else []) \
        + ([f"{conta['falhas']} senha(s) errada(s)"] if conta.get("falhas") else [])
    return "; ".join(notas) or "-"


def _situacao(sessao: dict, agora: float) -> str:
    if sessao["revogada"]:
        return f"encerrada: {sessao['revogada']}"
    if sessao["viva"]:
        return "viva"
    return "expirada" if agora >= sessao["expira_em"] else "inativa (15 min sem uso)"


def _linha_do_trace(registro: dict) -> str:
    try:
        return formatar(registro)
    except ERROS_DE_FORMATO:
        return f"{registro.get('kind')} (registro fora do formato)"


class TelaConsole(AbasAvancadas, Screen):
    """As cinco abas. Cada ação confere a sessão, chama o SVC-IAM e relê os dados do disco."""

    BINDINGS = [
        Binding("f1", "aba('aba-usuarios')", "Usuários", show=False),
        Binding("f2", "aba('aba-papeis')", "Papéis", show=False),
        Binding("f3", "aba('aba-sessoes')", "Sessões", show=False),
        Binding("f4", "aba('aba-trilha')", "Trilha", show=False),
        Binding("f5", "aba('aba-traces')", "Traces", show=False),
        Binding("ctrl+r", "recarregar", "Recarregar", priority=True),
        Binding("f8", "minha_senha", "Minha senha"),
        Binding("slash", "filtros", "Filtros", show=False),
        Binding("escape", "tabela", "Tabela", show=False),
        Binding("n", "nova_conta", "Nova conta", show=False),
        Binding("p", "papeis", "Papéis", show=False),
        Binding("v", "vinculo", "Vínculo", show=False),
        Binding("s", "redefinir_senha", "Redefinir senha", show=False),
        Binding("b", "bloquear", "Bloquear", show=False),
        Binding("d", "desbloquear", "Desbloquear", show=False),
        Binding("x", "desativar", "Desativar", show=False),
        Binding("r", "revogar", "Revogar sessão", show=False),
        Binding("t", "revogar_usuario", "Revogar as do usuário", show=False),
        Binding("i", "verificar", "Verificar", show=False),
        Binding("e", "exportar", "Exportar", show=False),
        Binding("a", "abrir_trace", "Abrir trace", show=False),
        Binding("l", "explicar", "Explicar", show=False),
        *BINDINGS_AVANCADAS,
    ]

    def __init__(self, aviso: str = ""):
        super().__init__()
        self.aviso = aviso
        self.abas: tuple = ()
        self.abas_extras: tuple = ()
        self._permissoes = frozenset()
        self._contas: dict = {}
        self._sessoes: dict = {}
        self._trilha: list = []
        self._trilha_visiveis: list = []
        self._trilha_integra = True
        self._trace = None  # AuditLog do arquivo aberto (já conferido), ou None
        self._trace_visiveis: list = []

    # ---- desenho ---------------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        sessao = self.app.sessao
        self._permissoes = sessao.permissoes
        self.abas = tuple(aba for aba, (_, permissao, _, _) in ABAS.items()
                          if aba not in ABAS_AVANCADAS and sessao.pode(permissao))
        self.abas_extras = tuple(aba for aba, (_, permissao, _, _) in ABAS_AVANCADAS.items()  # DSM4: F6 a F12
                                 if permissao is None or sessao.pode(permissao))
        yield Static("", id="status", markup=False)
        with TabbedContent(id="abas"):
            if "aba-usuarios" in self.abas:
                with TabPane(ABAS["aba-usuarios"][0], id="aba-usuarios"):
                    with Horizontal(classes="barra"):
                        yield Button("Nova conta", id="nova-conta", compact=True)
                        yield Button("Papéis", id="editar-papeis", compact=True)
                        yield Button("Vínculo", id="vinculo", compact=True)
                        yield Button("Senha", id="redefinir-senha", compact=True)
                        yield Button("Bloquear", id="bloquear", compact=True)
                        yield Button("Desbloquear", id="desbloquear", compact=True)
                        yield Button("Desativar", id="desativar", compact=True)
                    yield DataTable(id="tabela-usuarios", cursor_type="row", zebra_stripes=True)
            if "aba-papeis" in self.abas:
                with TabPane(ABAS["aba-papeis"][0], id="aba-papeis"):
                    yield DataTable(id="tabela-matriz", cursor_type="row", zebra_stripes=True)
                    with VerticalScroll(id="quadro-incompativeis"):
                        yield Static("", id="incompativeis", markup=False)
            if "aba-sessoes" in self.abas:
                with TabPane(ABAS["aba-sessoes"][0], id="aba-sessoes"):
                    with Horizontal(classes="barra"):
                        yield Button("Revogar sessão", id="revogar-sessao", compact=True)
                        yield Button("Revogar todas do usuário", id="revogar-usuario", compact=True)
                    yield DataTable(id="tabela-sessoes", cursor_type="row", zebra_stripes=True)
            if "aba-trilha" in self.abas:
                with TabPane(ABAS["aba-trilha"][0], id="aba-trilha"):
                    with Horizontal(classes="barra"):
                        yield Input(placeholder="ator contém", id="trilha-ator", compact=True)
                        yield Input(placeholder="evento contém", id="trilha-evento", compact=True)
                        with RadioSet(id="trilha-resultado", compact=True):
                            yield RadioButton("todos", value=True, id="resultado-todos", compact=True)
                            yield RadioButton("ok", id="resultado-ok", compact=True)
                            yield RadioButton("negado", id="resultado-negado", compact=True)
                        yield Button("Verificar", id="verificar-trilha", compact=True)
                        yield Button("Exportar", id="exportar-trilha", compact=True)
                    yield Static("", id="integridade-trilha", markup=False)
                    yield DataTable(id="tabela-trilha", cursor_type="row", zebra_stripes=True)
                with TabPane(ABAS["aba-traces"][0], id="aba-traces"):
                    with Horizontal(classes="barra"):
                        yield Input(placeholder="caminho do trace JSONL (Enter abre)", id="trace-caminho", compact=True)
                        yield Button("Abrir", id="abrir-trace", compact=True)
                    yield Static("nenhum trace aberto", id="trace-estado", markup=False)
                    with Horizontal(classes="barra"):
                        yield Input(placeholder="agente", id="trace-agente", compact=True)
                        yield Input(placeholder="tipo (ex.: decision,belief)", id="trace-tipo", compact=True)
                        yield Input(placeholder="tarefa (ex.: SOL-001)", id="trace-tarefa", compact=True)
                        yield Input(placeholder="texto (Enter aplica)", id="trace-texto", compact=True)
                        yield Button("Explicar", id="explicar", compact=True)
                        yield Button("Exportar", id="exportar-trace", compact=True)
                    with Horizontal(id="trace-corpo"):
                        yield DataTable(id="tabela-trace", cursor_type="row", zebra_stripes=True)
                        with Vertical(id="trace-lateral"):
                            yield Static("invariantes: abra um trace", id="invariantes", markup=False)
                            with VerticalScroll(id="quadro-explicacao"):
                                yield Static("selecione um registro e aperte Enter (ou l) para ver a cadeia que levou "
                                             "a ele", id="explicacao", markup=False)
            yield from self.abas_avancadas()
        yield Static(self.aviso, id="mensagem", markup=False)
        yield Static("", id="atalhos", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        for id, colunas in COLUNAS.items():
            tabela = self._tabela(id)
            if tabela is not None:
                tabela.add_columns(*colunas)
        self._montar_matriz()
        for id, titulo in (("quadro-incompativeis", "combinações incompatíveis"), ("quadro-explicacao", "explicação")):
            for quadro in self.query(f"#{id}"):
                quadro.border_title = titulo
        self._recarregar()
        self._ao_trocar_aba()
        if self.app.sessao is not None and self.app.sessao.trocar_senha:
            self._pedir_troca_de_senha(obrigatoria=True)

    def _tabela(self, id: str):
        achadas = self.query(f"#{id}")
        return achadas.first(DataTable) if achadas else None

    def _aba(self) -> str:
        abas = self.query("#abas")  # vazio enquanto a tela ainda está sendo montada
        return abas.first(TabbedContent).active if abas else ""

    def _avisar(self, texto: str, negado: bool = False) -> None:
        mensagem = self.query_one("#mensagem", Static)
        mensagem.set_class(negado, "negado")
        mensagem.update(texto)

    def _texto(self, id: str) -> str:
        campos = self.query(f"#{id}")
        return campos.first(Input).value.strip() if campos else ""

    @staticmethod
    def _chave(tabela):
        """Chave da linha sob o cursor (usuário ou id da sessão), ou None com a tabela vazia."""
        if tabela is None or not tabela.row_count:
            return None
        return tabela.coordinate_to_cell_key(tabela.cursor_coordinate).row_key.value

    def _preencher(self, tabela, linhas, manter: bool = True) -> None:
        """Redesenha a tabela; com `manter`, o cursor fica na mesma chave (ou na mesma altura)."""
        chave, altura = self._chave(tabela), tabela.cursor_row
        tabela.clear()
        for chave_da_linha, celulas in linhas:  # Text: o conteúdo não é interpretado como marcação
            tabela.add_row(*[Text(str(c)) for c in celulas], key=chave_da_linha)
        chaves = [c for c, _ in linhas]
        if manter and linhas:
            tabela.move_cursor(row=chaves.index(chave) if chave in chaves else min(altura, len(linhas) - 1))

    # ---- sessão do console -------------------------------------------------------------------
    def _vivo(self):
        """Sessão do console conferida agora no cadastro; levanta IAM-04 se caiu (ou IAM-07)."""
        atual = self.app.sessao
        sessao = self.app.acesso.sessao_por_id(atual.id) if atual is not None else None
        if sessao is None:
            raise AcessoNegado("IAM-04", "a sessão deste console expirou ou foi revogada: entre de novo")
        self.app.sessao = sessao
        return sessao

    def _ator(self, permissao: str | None = None):
        """Sessão viva (e com a permissão), ou None: a negação já foi mostrada e, sem sessão, o console saiu."""
        try:
            sessao = self._vivo()
        except ERROS as erro:
            self.app.voltar_a_entrada(descrever(erro))
            return None
        if sessao.permissoes != self._permissoes:  # outro administrador mudou os papéis desta conta
            if any(sessao.pode(p) for p in PERMISSOES_CONSOLE):
                self.app.entrar(sessao, "seus papéis mudaram: as abas foram remontadas; repita a ação")
            else:
                self.app.voltar_a_entrada("acesso negado: IAM-05: sua conta não administra mais o acesso nem audita")
            return None
        if permissao is not None:
            try:
                self.app.acesso.exigir(sessao, permissao)  # IAM-05, com registro na trilha
            except AcessoNegado as erro:
                self._avisar(descrever(erro), negado=True)
                return None
        return sessao

    # ---- leitura do disco --------------------------------------------------------------------
    def action_recarregar(self) -> None:
        if self._recarregar():
            self._avisar("dados relidos do disco")

    def _recarregar(self) -> bool:
        sessao = self._ator()
        if sessao is None:
            return False
        for carregar in (self._carregar_contas, self._carregar_sessoes, self._carregar_trilha, self._carregar_avancado):
            try:
                carregar(sessao)
            except ERROS as erro:
                self._avisar(descrever(erro), negado=True)
                return False
        papeis = ", ".join(sessao.papeis) or "sem papel"
        self.query_one("#status", Static).update(f"{sessao.usuario} — {sessao.nome} [{papeis}] · "
                                                 f"cadastro: {self.app.pasta}")
        return True

    def _carregar_contas(self, sessao) -> None:
        if not {"aba-usuarios", "aba-papeis"} & set(self.abas):
            return
        self._contas = {c["usuario"]: c for c in self.app.acesso.contas()}
        agora = self.app.acesso.relogio()
        tabela = self._tabela("tabela-usuarios")
        if tabela is not None:
            self._preencher(tabela, [(u, (u, c["nome"], _estado(c, agora), ", ".join(c["papeis"]) or "(nenhum)",
                                          c.get("cargo") or "-", c.get("pessoa_erp") or "-", _observacoes(c)))
                                     for u, c in self._contas.items()])
        quadro = self.query("#incompativeis")
        if quadro:
            quadro.first(Static).update(self._incompativeis())

    def _incompativeis(self) -> str:
        linhas = []
        for u, c in self._contas.items():
            estado = "" if c["estado"] == "ativa" else f" (conta {c['estado']})"
            par = permissoes.incompatibilidade(c["papeis"])
            if par:
                linhas.append(f"IAM-06  {u}{estado} acumula {' e '.join(sorted(par))}: papéis que a mesma conta "
                              f"não pode ter")
        for u, c in self._contas.items():
            estado = "" if c["estado"] == "ativa" else f" (conta {c['estado']})"
            if SOLICITA_E_APROVA <= set(c["papeis"]):
                linhas.append(f"aviso POL-13  {u}{estado} solicita e aprova: quem faz a solicitação não decide sobre "
                              f"o próprio pedido")
        return "\n".join(linhas) or "nenhuma conta com papéis incompatíveis nem com solicitação e aprovação juntas"

    def _montar_matriz(self) -> None:
        tabela = self._tabela("tabela-matriz")
        if tabela is None:
            return
        papeis = permissoes.papeis_humanos()
        tabela.add_columns("permissão", "título", *papeis)
        for permissao, dados in permissoes.catalogo().items():
            tabela.add_row(Text(permissao), Text(dados["titulo"]),
                           *[Text("sim" if permissao in papel["permissoes"] else "·") for papel in papeis.values()],
                           key=permissao)

    def _carregar_sessoes(self, sessao) -> None:
        tabela = self._tabela("tabela-sessoes")
        if tabela is None:
            return
        agora = self.app.acesso.relogio()
        sessoes = sorted(self.app.acesso.sessoes(sessao), key=lambda s: s["criada_em"], reverse=True)
        self._sessoes = {s["id"]: s for s in sessoes}
        self._preencher(tabela, [(s["id"], (s["id"] + (" (este console)" if s["id"] == sessao.id else ""), s["usuario"],
                                           s["origem"] or "-", _quando(s["criada_em"]), _quando(s["vista_em"]),
                                           _quando(s["expira_em"]), _situacao(s, agora))) for s in sessoes])

    def _carregar_trilha(self, sessao) -> None:
        if self._tabela("tabela-trilha") is None:
            return
        try:
            self._trilha = self.app.acesso.trilha.ler()
        except ValueError:  # linha ilegível: a verificação abaixo acusa a adulteração
            self._trilha = []
        self._verificar_trilha()
        self._filtrar_trilha()

    def _verificar_trilha(self) -> str:
        try:
            resumo = self.app.acesso.trilha.verificar()
            self._trilha_integra = True
            texto = (f"ÍNTEGRA — {resumo['registros']} registro(s); a cadeia de hashes e a cabeça selada conferem "
                     f"(hash final {str(resumo['hash_final'])[:16]}…)")
        except TrilhaAdulterada as erro:
            self._trilha_integra = False
            texto = f"ADULTERADA — {erro}"
        estado = self.query_one("#integridade-trilha", Static)
        estado.set_class(not self._trilha_integra, "adulterada")
        estado.set_class(self._trilha_integra, "integra")
        estado.update(texto)
        return texto

    def _filtros_da_trilha(self) -> dict:
        marcado = self.query_one("#trilha-resultado", RadioSet).pressed_button
        resultado = marcado.id.removeprefix("resultado-") if marcado is not None else "todos"
        filtros = {"ator": self._texto("trilha-ator").lower(), "evento": self._texto("trilha-evento").lower(),
                   "resultado": "" if resultado == "todos" else resultado}
        return {k: v for k, v in filtros.items() if v}

    def _filtrar_trilha(self) -> None:
        tabela = self._tabela("tabela-trilha")
        if tabela is None:
            return
        f = self._filtros_da_trilha()
        self._trilha_visiveis = [r for r in self._trilha if isinstance(r, dict)
                                 and f.get("ator", "") in str(r.get("ator") or "").lower()
                                 and f.get("evento", "") in str(r.get("evento") or "").lower()
                                 and ("resultado" not in f or r.get("resultado") == f["resultado"])]
        recentes = list(reversed(self._trilha_visiveis[-LIMITE_LINHAS:]))  # o mais recente em cima
        self._preencher(tabela, [(None, (r.get("seq", "?"), _quando(r.get("t")), r.get("evento"), r.get("ator") or "-",
                                         r.get("resultado"), r.get("regra") or "-",
                                         " ".join(f"{k}={v}" for k, v in r.items() if k not in FORA_DOS_DETALHES)))
                                 for r in recentes], manter=False)

    # ---- navegação ---------------------------------------------------------------------------
    def check_action(self, action: str, parameters) -> bool | None:
        abas = [aba for aba, acoes in ACOES_DA_ABA.items() if action in acoes]
        presentes = [aba for aba in abas if aba in self.abas]
        if not presentes:  # ação geral, ou de uma aba que esta conta não tem: roda e o serviço nega (IAM-05)
            return True
        return self._aba() in presentes

    def on_tabbed_content_tab_activated(self, evento: TabbedContent.TabActivated) -> None:
        self._ao_trocar_aba()

    def _ao_trocar_aba(self) -> None:
        aba = self._aba()
        if aba not in ABAS:
            return
        self.query_one("#atalhos", Static).update(f"{ABAS[aba][3]}   |   F1–F12 abas")
        self.refresh_bindings()
        self.action_tabela()

    def action_aba(self, aba: str) -> None:
        if self._ator(ABAS[aba][1]) is None:
            return
        if aba in self.abas + self.abas_extras:
            self.query_one("#abas", TabbedContent).active = aba
            self._ao_trocar_aba()

    def action_tabela(self) -> None:
        tabela = self._tabela(ABAS[self._aba()][2]) if self._aba() in ABAS else None
        if tabela is not None and self.app.screen is self:
            tabela.focus()

    def action_filtros(self) -> None:
        campo = {"aba-trilha": "trilha-ator", "aba-traces": "trace-agente"}.get(self._aba())
        if campo:
            self.query_one(f"#{campo}", Input).focus()

    def on_button_pressed(self, evento: Button.Pressed) -> None:
        if evento.button.id == "abrir-trace":
            self._abrir_trace()
        elif evento.button.id in BOTOES:
            getattr(self, "action_" + BOTOES[evento.button.id])()

    def on_input_changed(self, evento: Input.Changed) -> None:
        if evento.input.id in ("trilha-ator", "trilha-evento"):
            self._filtrar_trilha()

    def on_input_submitted(self, evento: Input.Submitted) -> None:
        if evento.input.id == "trace-caminho":
            self._abrir_trace()
        elif (evento.input.id or "").startswith("trace-"):
            self._filtrar_trace()
            self.action_tabela()
        else:
            self.action_tabela()

    def on_radio_set_changed(self, evento: RadioSet.Changed) -> None:
        self._filtrar_trilha()

    def on_data_table_row_selected(self, evento: DataTable.RowSelected) -> None:
        if evento.data_table.id == "tabela-trace":
            self.action_explicar()

    # ---- ações: execução comum ---------------------------------------------------------------
    def _feito(self, sucesso):
        """Callback de formulário e de ação direta: mensagem de sucesso e releitura do disco."""
        def ao_fechar(resultado) -> None:
            if not resultado:
                self._recarregar()  # cancelado: mesmo assim confere a sessão e mostra o estado atual
            elif self._recarregar():
                self._avisar(sucesso(resultado) if callable(sucesso) else sucesso)
        return ao_fechar

    def _executar(self, chamada, sucesso: str) -> None:
        """Alteração sem formulário: chama o serviço com a sessão conferida e mostra o resultado."""
        try:
            chamada(self._vivo())
        except ERROS as erro:
            if self._recarregar():
                self._avisar(descrever(erro), negado=True)
            return
        self._feito(sucesso)(True)

    def _confirmar(self, pergunta: str, chamada, sucesso: str) -> None:
        self.app.push_screen(Confirmar(pergunta), lambda sim: self._executar(chamada, sucesso) if sim else None)

    def _conta_alvo(self, permissao: str):
        """Conta selecionada na tabela, para quem tem a permissão; None se a ação não pode seguir."""
        if self._ator(permissao) is None:
            return None
        conta = self._contas.get(self._chave(self._tabela("tabela-usuarios")))
        if conta is None:
            self._avisar("selecione uma conta na aba Usuários", negado=True)
        return conta

    # ---- ações: usuários ---------------------------------------------------------------------
    def action_nova_conta(self) -> None:
        if self._ator("PERM-IAM-USUARIOS") is None:
            return
        acesso = self.app.acesso
        self.app.push_screen(
            FormConta(lambda usuario, nome, senha, papeis, cargo, pessoa_erp: acesso.criar_conta(
                self._vivo(), usuario, nome, senha, papeis, pessoa_erp=pessoa_erp, cargo=cargo),
                "Nova conta (a senha é temporária: a pessoa troca na primeira entrada)"),
            self._feito(lambda conta: f"conta {conta['usuario']} criada com {', '.join(conta['papeis'])}"))

    def action_papeis(self) -> None:
        conta = self._conta_alvo("PERM-IAM-PAPEIS")
        if conta is not None:
            u = conta["usuario"]
            self.app.push_screen(FormPapeis(lambda papeis: self.app.acesso.atribuir_papeis(self._vivo(), u, papeis), conta),
                                 self._feito(lambda c: f"papéis de {u}: {', '.join(c['papeis']) or '(nenhum)'}"))

    def action_vinculo(self) -> None:
        conta = self._conta_alvo("PERM-IAM-PAPEIS")
        if conta is not None:
            u = conta["usuario"]
            self.app.push_screen(
                FormVinculo(lambda pessoa_erp, cargo: self.app.acesso.definir_vinculo(
                    self._vivo(), u, pessoa_erp=pessoa_erp, cargo=cargo), conta),
                self._feito(lambda c: f"vínculo de {u}: pessoa do ERP {c['pessoa_erp'] or '-'}, cargo {c['cargo'] or '-'}"))

    def action_redefinir_senha(self) -> None:
        conta = self._conta_alvo("PERM-IAM-USUARIOS")
        if conta is not None:
            u = conta["usuario"]
            self.app.push_screen(
                FormSenha(lambda nova: self.app.acesso.redefinir_senha(self._vivo(), u, nova),
                          f"Redefinir a senha de {u}: senha temporária (trocada na primeira entrada); as sessões "
                          f"abertas de {u} caem"),
                self._feito(f"senha de {u} redefinida: a conta troca a senha na próxima entrada"))

    def action_bloquear(self) -> None:
        conta = self._conta_alvo("PERM-IAM-USUARIOS")
        if conta is not None:
            u = conta["usuario"]
            self._confirmar(f"Bloquear a conta {u} ({conta['nome']})? Ela não entra mais e as sessões abertas caem agora.",
                            lambda ator: self.app.acesso.bloquear(ator, u), f"conta {u} bloqueada")

    def action_desbloquear(self) -> None:
        conta = self._conta_alvo("PERM-IAM-USUARIOS")
        if conta is not None:
            u = conta["usuario"]
            self._executar(lambda ator: self.app.acesso.desbloquear(ator, u), f"conta {u} desbloqueada")

    def action_desativar(self) -> None:
        conta = self._conta_alvo("PERM-IAM-USUARIOS")
        if conta is not None:
            u = conta["usuario"]
            self._confirmar(f"Desativar a conta {u} ({conta['nome']})? Ela deixa de entrar e as sessões abertas caem "
                            f"agora.",
                            lambda ator: self.app.acesso.desativar(ator, u), f"conta {u} desativada")

    def action_minha_senha(self) -> None:
        if self._ator() is not None:
            self._pedir_troca_de_senha(obrigatoria=False)

    def _pedir_troca_de_senha(self, obrigatoria: bool) -> None:
        def ao_fechar(resultado) -> None:
            if resultado:
                self._feito("senha trocada")(True)
                self.action_tabela()
            elif obrigatoria:
                self.app.voltar_a_entrada("acesso negado: IAM-02: a senha temporária precisa ser trocada para usar "
                                          "o console")
        titulo = "Sua senha é temporária: troque para continuar (IAM-02)" if obrigatoria else "Trocar a própria senha"
        self.app.push_screen(FormTrocarSenha(lambda atual, nova: self.app.acesso.trocar_senha(self._vivo(), atual, nova),
                                             titulo), ao_fechar)

    # ---- ações: sessões ----------------------------------------------------------------------
    def _sessao_alvo(self):
        if self._ator("PERM-IAM-SESSOES") is None:
            return None
        alvo = self._sessoes.get(self._chave(self._tabela("tabela-sessoes")))
        if alvo is None:
            self._avisar("selecione uma sessão na aba Sessões", negado=True)
        return alvo

    def action_revogar(self) -> None:
        alvo = self._sessao_alvo()
        if alvo is None:
            return
        if not alvo["viva"]:
            self._avisar(f"a sessão {alvo['id']} já está encerrada", negado=True)
            return
        sid = alvo["id"]
        propria = " É a sessão deste console: você volta à tela de entrada." if sid == self.app.sessao.id else ""
        self._confirmar(f"Revogar a sessão {sid} de {alvo['usuario']} (origem: {alvo['origem'] or '-'})? A pessoa cai na "
                        f"requisição seguinte.{propria}",
                        lambda ator: self.app.acesso.revogar(ator, sid), f"sessão {sid} de {alvo['usuario']} revogada")

    def action_revogar_usuario(self) -> None:
        alvo = self._sessao_alvo()
        if alvo is None:
            return
        usuario = alvo["usuario"]
        vivas = [s["id"] for s in self._sessoes.values()
                 if s["usuario"] == usuario and s["viva"] and s["id"] != self.app.sessao.id]
        if not vivas:
            self._avisar(f"{usuario} não tem outra sessão viva para revogar", negado=True)
            return

        def revogar_todas(ator) -> None:
            for sid in vivas:
                self.app.acesso.revogar(ator, sid)
        self._confirmar(f"Revogar {len(vivas)} sessão(ões) viva(s) de {usuario}? A sessão deste console não entra "
                        f"na conta.",
                        revogar_todas, f"{len(vivas)} sessão(ões) de {usuario} revogada(s)")

    # ---- ações: trilha e traces --------------------------------------------------------------
    def action_verificar(self) -> None:
        if self._ator("PERM-AUD-VER") is None:
            return
        if self._aba() == "aba-traces":
            self._abrir_trace()
        elif self._recarregar():
            self._avisar("trilha de acesso " + self._verificar_trilha(), negado=not self._trilha_integra)

    def action_abrir_trace(self) -> None:
        if self._ator("PERM-AUD-VER") is not None:
            self.query_one("#trace-caminho", Input).focus()

    def _abrir_trace(self) -> None:
        if self._ator("PERM-AUD-VER") is None:
            return
        caminho = self._texto("trace-caminho")
        if not caminho:
            self._avisar("informe o caminho de um trace JSONL gravado pela simulação", negado=True)
            return
        self._trace, texto, violacoes = None, "", None
        try:
            log = AuditLog.read_jsonl(Path(caminho).expanduser())
            if not all(isinstance(r, dict) and {"seq", "t", "kind"} <= r.keys() for r in log.records):
                raise KeyError("há linhas sem seq, t e kind")
        except TraceAdulterado as erro:
            texto = f"ADULTERADO — {erro}"
        except OSError as erro:
            texto = f"ERRO — não foi possível ler o arquivo: {erro}"
        except ERROS_DE_FORMATO as erro:
            texto = f"ERRO — o arquivo não é um trace JSONL do sistema: {erro}"
        else:
            self._trace = log
            texto = (f"ÍNTEGRO — a cadeia de hashes e o selo conferem: {len(log.records)} registro(s), hash final "
                     f"{str(log.hash_final)[:16]}…") if log.encadeado else \
                (f"SEM CADEIA — trace anterior à DSM3, sem hash encadeado nem selo: {len(log.records)} registro(s) "
                 f"lidos, integridade não verificável")
            try:
                violacoes = invariantes.verificar(log.records)
            except ERROS_DE_FORMATO as erro:
                violacoes = [f"não foi possível conferir os invariantes: {erro!r}"]
        estado = self.query_one("#trace-estado", Static)
        estado.set_class(self._trace is None or not self._trace.encadeado, "adulterada")
        estado.set_class(self._trace is not None and self._trace.encadeado, "integra")
        estado.update(texto)
        if violacoes is None:
            resumo = "invariantes: não conferidos (trace não aberto)"
        elif violacoes:
            resumo = f"invariantes: {len(violacoes)} VIOLAÇÃO(ÕES)\n" + "\n".join("  " + v for v in violacoes)
        else:
            resumo = f"invariantes: {len(invariantes.INVARIANTES)} conferidos, nenhuma violação"
        invariantes_ = self.query_one("#invariantes", Static)
        invariantes_.set_class(bool(violacoes) or violacoes is None, "adulterada")
        invariantes_.set_class(violacoes == [], "integra")
        invariantes_.update(resumo)
        self.query_one("#explicacao", Static).update("selecione um registro e aperte Enter (ou l) para ver a cadeia "
                                                     "que levou a ele")
        self._filtrar_trace()
        self._avisar(f"trace {caminho}: {texto}", negado=self._trace is None)
        self.action_tabela()

    def _filtros_do_trace(self) -> dict:
        filtros = {nome: self._texto(f"trace-{nome}") for nome in ("agente", "tipo", "tarefa", "texto")}
        return {k: v for k, v in filtros.items() if v}

    def _filtrar_trace(self) -> None:
        tabela = self._tabela("tabela-trace")
        if tabela is None:
            return
        registros = self._trace.records if self._trace is not None else []
        try:
            self._trace_visiveis = consulta.filtrar(registros, **self._filtros_do_trace())
        except ERROS_DE_FORMATO as erro:
            self._trace_visiveis = []
            self._avisar(f"filtro não aplicado: {erro!r}", negado=True)
        self._preencher(tabela, [(None, (r["seq"], r["kind"], r.get("agente") or r.get("sender") or "-", _linha_do_trace(r)))
                                 for r in self._trace_visiveis[:LIMITE_LINHAS]], manter=False)
        if self._trace is not None:
            cortado = f" (a tabela mostra os {LIMITE_LINHAS} primeiros)" if len(self._trace_visiveis) > LIMITE_LINHAS else ""
            self._avisar(f"{len(self._trace_visiveis)} de {len(registros)} registro(s) no recorte{cortado}")

    def action_explicar(self) -> None:
        if self._ator("PERM-AUD-VER") is None:
            return
        tabela = self._tabela("tabela-trace")
        if self._trace is None or not tabela.row_count:
            self._avisar("abra um trace e selecione um registro para explicar", negado=True)
            return
        seq = self._trace_visiveis[tabela.cursor_row]["seq"]
        try:
            e = explicar(self._trace.records, seq)
        except ERROS_DE_FORMATO + (LookupError,) as erro:
            self._avisar(f"não foi possível explicar o registro {seq}: {erro}", negado=True)
            return
        resumo = ", ".join(f"{papel} × {n}" for papel, n in e["resumo"].items()) or "nenhum registro anterior do agente"
        linhas = [f"por que: {e['alvo']['texto']}",
                  f"agente {e['agente']} | conversa {e['conversa']} | tarefa {e['tarefa']}", f"cadeia: {resumo}", ""]
        linhas += [f"[{item['papel']}] {item['texto']}" for item in e["cadeia"]]
        self.query_one("#explicacao", Static).update("\n".join(linhas))
        self._avisar(f"registro {seq} explicado: {len(e['cadeia'])} registro(s) na cadeia")

    def action_exportar(self) -> None:
        if self._ator("PERM-AUD-EXPORTAR") is None:
            return
        if self._aba() == "aba-traces":
            if self._trace is None:
                self._avisar("abra um trace antes de exportar o recorte", negado=True)
                return
            registros, fonte, filtros = list(self._trace_visiveis), "trace", self._filtros_do_trace()
            linha = lambda r: json.dumps(r, ensure_ascii=False, default=str)  # noqa: E731  (formato do servidor)
            ressalva = ""
        else:
            registros, fonte, filtros = list(self._trilha_visiveis), "trilha", self._filtros_da_trilha()
            linha = lambda r: json.dumps(r, ensure_ascii=False, sort_keys=True)  # noqa: E731  (formato da CLI)
            ressalva = "" if self._trilha_integra else \
                " — ATENÇÃO: a trilha está ADULTERADA; o recorte é evidência, não prova"

        def gravar(caminho: str):
            if not caminho:
                raise Invalido("informe o caminho do arquivo")
            ator = self._vivo()
            self.app.acesso.exigir(ator, "PERM-AUD-EXPORTAR")
            destino = Path(caminho).expanduser()
            try:
                with open(destino, "x", encoding="utf-8") as f:
                    f.writelines(linha(r) + "\n" for r in registros)
            except FileExistsError:
                raise Invalido(f"{destino} já existe: escolha outro nome (o console não sobrescreve arquivos)") from None
            self.app.acesso.registrar("auditoria_exportada", ator.usuario, registros=len(registros), fonte=fonte,
                                      filtros=filtros, arquivo=destino.name, origem="tui")
            return destino
        self.app.push_screen(
            FormArquivo(gravar, f"Exportar {len(registros)} registro(s) do recorte ({fonte}) em JSONL",
                        f"{fonte}-recorte.jsonl"),
            self._feito(lambda destino: f"{len(registros)} registro(s) exportados para {destino}{ressalva}"))


class ConsoleAcesso(App):
    """Aplicação: guarda o `Acesso` e a sessão de quem entrou; as telas fazem o resto."""

    TITLE = "SMA de Controladoria — acesso e auditoria"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [Binding("ctrl+q", "quit", "Sair", priority=True)]
    CSS = """
    TelaEntrada { align: center middle; }
    #entrada { width: 78; max-width: 100%; height: auto; padding: 1 2; border: round $primary; }
    #entrada Input, #entrada Static { margin-bottom: 1; }
    #erro-entrada, #erro-modal { color: $error; height: auto; margin-bottom: 0; }
    .titulo { text-style: bold; margin-bottom: 1; }

    #status { height: auto; max-height: 2; padding: 0 1; background: $panel; }
    #mensagem { height: auto; max-height: 3; padding: 0 1; color: $success; }
    #mensagem.negado { color: $error; }
    #atalhos { height: 1; padding: 0 1; color: $text-muted; }
    #abas { height: 1fr; }
    #abas ContentSwitcher { height: 1fr; }
    TabPane { height: 1fr; padding: 0 1; }
    DataTable { height: 1fr; }
    .barra { height: 1; margin-bottom: 1; }
    .barra Button { min-width: 0; margin-right: 1; }
    .barra Input { width: 1fr; min-width: 10; margin-right: 1; }
    #trilha-resultado { layout: horizontal; width: auto; height: 1; margin-right: 1; }
    #trilha-resultado RadioButton { width: auto; margin-right: 1; }
    #integridade-trilha, #trace-estado { height: auto; margin-bottom: 1; text-style: bold; }
    #integridade-trilha.integra, #trace-estado.integra, #invariantes.integra { color: $success; }
    #integridade-trilha.adulterada, #trace-estado.adulterada, #invariantes.adulterada { color: $error; }
    #quadro-incompativeis { height: auto; max-height: 9; margin-top: 1; border: round $warning; padding: 0 1; }
    #trace-corpo { height: 1fr; }
    #tabela-trace { width: 2fr; }
    #trace-lateral { width: 1fr; min-width: 30; margin-left: 1; }
    #invariantes { height: auto; max-height: 12; margin-bottom: 1; }
    #quadro-explicacao { height: 1fr; border: round $primary; padding: 0 1; }

    Confirmar, Formulario { align: center middle; }
    .caixa { width: 84; max-width: 100%; height: auto; max-height: 100%; padding: 1 2; border: round $primary;
             background: $surface; }
    .linha { height: auto; }
    .rotulo { width: 24; }
    .linha Input, .linha Select { width: 1fr; }
    .linha Input { background: $panel; }
    .caixa SelectionList { height: auto; margin-bottom: 1; }
    .botoes { height: auto; margin-top: 1; }
    .botoes Button { margin-right: 2; }
    """

    def __init__(self, pasta_acesso, custo_scrypt: int = 15):
        super().__init__()
        self.pasta = Path(pasta_acesso).resolve()  # o caminho inteiro aparece na tela: qual cadastro está aberto
        self.acesso = Acesso(self.pasta, custo_scrypt=custo_scrypt)
        self.sessao = None

    def on_mount(self) -> None:
        self.push_screen(TelaEntrada())

    def entrar(self, sessao, aviso: str = "") -> None:
        """A tela de entrada autenticou (ou os papéis mudaram): monta o console para esta sessão."""
        self.sessao = sessao
        while len(self.screen_stack) > 2:  # formulário aberto sobre o console que vai ser remontado
            self.pop_screen()
        self.switch_screen(TelaConsole(aviso or f"entrada de {sessao.usuario} registrada na trilha de acesso"))

    def encerrar_sessao(self) -> None:
        sessao, self.sessao = self.sessao, None
        if sessao is not None:
            with contextlib.suppress(Exception):  # sair nunca impede o console de fechar
                self.acesso.sair(sessao)

    def voltar_a_entrada(self, aviso: str = "") -> None:
        """Encerra a sessão e volta à tela de entrada (fecha antes os formulários abertos)."""
        self.encerrar_sessao()

        def trocar() -> None:
            while len(self.screen_stack) > 2:
                self.pop_screen()
            if not isinstance(self.screen, TelaEntrada):  # duas negações seguidas não empilham duas entradas
                self.switch_screen(TelaEntrada(aviso))
        self.call_later(trocar)

    async def action_quit(self) -> None:
        self.encerrar_sessao()
        self.exit()

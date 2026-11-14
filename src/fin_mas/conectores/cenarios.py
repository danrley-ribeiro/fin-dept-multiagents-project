"""Fontes dos cenários de conectores (`Scenario.conector`), ADR-011. Tudo offline e em loopback.

    erp_demo[:plantios]      ERP de demonstração em loopback (porta livre, token sorteado); o conector REST
                             genérico lê o contrato OpenAPI, entende a fonte e o roteiro do cenário confirma
                             as sugestões (no dashboard, quem confirma é uma pessoa com PERM-DAD-CONECTAR)
    erp_fora_do_ar           o mesmo conector, apontado para uma porta de loopback onde nada escuta
    planilha_fora_do_modelo  .xlsx com abas e colunas renomeadas, reordenadas, título acima do cabeçalho e
                             linha de total, gerado da empresa sintética numa pasta temporária
    mcp_excel                servidor MCP de Excel embutido, por stdio, sobre o modelo preenchido

A proveniência é lógica (`conector://...`, `mcp://...`): nem porta nem pasta temporária entram no trace,
e o cenário se repete com o mesmo hash.
"""
import shutil
import socket
import tempfile
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from fin_mas.conectores import descoberta
from fin_mas.conectores.base import AmbienteConector
from fin_mas.conectores.erp_demo import ErpDemo, openapi
from fin_mas.conectores.mcp_cliente import ConectorMCP, comando_excel
from fin_mas.conectores.planilhas import ConectorPlanilha
from fin_mas.conectores.rest import ConectorREST
from fin_mas.env.dataset import Dataset
from fin_mas.env.empresa import EMPRESA, PESSOAS, PRODUTOS
from fin_mas.env.portes import PORTE_PADRAO
from fin_mas.fontes import entendimento, planilha

CONFIRMADO_POR = "roteiro do cenário"


def confirmar(estrutura: dict, competencia: str | None = None) -> dict:
    """O que a pessoa faria na tela: aceitar as sugestões. Devolve o mapeamento (validado)."""
    from fin_mas.conectores.canonico import validar_mapeamento
    mapeamento = entendimento.sugerir_mapeamento(estrutura)["mapeamento"]
    erros = validar_mapeamento(mapeamento, {r["nome"]: {c["nome"] for c in r["campos"]} for r in estrutura["recursos"]})
    if erros:
        raise ValueError("sugestões incompletas para confirmar: " + "; ".join(erros[:5]))
    return mapeamento


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ambiente_do_cenario(nome: str, seed: int, porte: str | None = None):
    tipo, _, resto = nome.partition(":")
    plantar = tuple(p for p in resto.split(",") if p)
    porte = porte or PORTE_PADRAO
    if tipo == "erp_demo":
        return _erp_demo(seed, porte, plantar)
    if tipo == "erp_fora_do_ar":
        return _erp_fora(porte)
    if tipo == "planilha_fora_do_modelo":
        return _planilha_fora(seed, porte, plantar)
    if tipo == "mcp_excel":
        return _mcp_excel(seed, porte, plantar)
    raise ValueError(f"fonte de cenário desconhecida: {nome}")


def _rest(url, token, porte):
    return ConectorREST("erp-demo", {"url_base": url, "autenticacao": {"tipo": "bearer"}, "openapi": "/openapi.json",
                                     "tempo_limite": 5, "porte": porte}, segredo=token)


def _erp_demo(seed, porte, plantar) -> AmbienteConector:
    erp = ErpDemo(seed, porte, plantar)
    url = erp.iniciar()
    conector = _rest(url, erp.token, porte)
    competencia = erp.ambiente.principal
    estrutura = descoberta.estrutura_rest(conector, competencia)
    for spec in conector.config["recursos"].values():  # páginas pequenas: a paginação também é exercitada
        if spec.get("paginacao"):
            spec["paginacao"]["tamanho"] = 5
    conector.mapeamento = confirmar(estrutura, competencia)
    conector.fechar = erp.parar
    conector.erp = erp
    return AmbienteConector(conector, competencia=competencia, porte=porte)


def mapeamento_erp_demo() -> tuple[dict, dict]:
    """Recursos e mapeamento do ERP de demonstração tirados só do contrato (sem rede)."""
    est = entendimento.de_openapi(openapi())
    recursos = {r["nome"]: r["descritor"] for r in est["recursos"]}
    return recursos, entendimento.sugerir_mapeamento(est)["mapeamento"]


def _erp_fora(porte) -> AmbienteConector:
    recursos, mapeamento = mapeamento_erp_demo()
    conector = ConectorREST("erp-demo", {"url_base": f"http://127.0.0.1:{_porta_livre()}", "recursos": recursos,
                                         "autenticacao": {"tipo": "bearer"}, "tempo_limite": 2, "porte": porte},
                            segredo="token-que-nao-vai-a-lugar-nenhum", mapeamento=mapeamento)
    return AmbienteConector(conector, competencia="2026-09", porte=porte)


class _Temporario(AmbienteConector):
    def __init__(self, conector, pasta, **kw):
        super().__init__(conector, **kw)
        self._pasta = pasta

    def fechar(self) -> None:
        super().fechar()
        shutil.rmtree(self._pasta, ignore_errors=True)


def _planilha_fora(seed, porte, plantar) -> AmbienteConector:
    pasta = Path(tempfile.mkdtemp(prefix="fin-mas-planilha-"))
    ds = Dataset(seed=seed, porte=porte, plantar=plantar)
    arquivo = gerar_planilha_fora_do_modelo(pasta / "controle_financeiro.xlsx", ds)
    conector = ConectorPlanilha("planilha-fora-do-modelo", arquivo, porte=porte)
    conector.mapeamento = confirmar(entendimento.de_planilha(arquivo), ds.competencia)
    return _Temporario(conector, pasta, competencia=ds.competencia, porte=porte)


def _mcp_excel(seed, porte, plantar) -> AmbienteConector:
    pasta = Path(tempfile.mkdtemp(prefix="fin-mas-mcp-"))
    ds = Dataset(seed=seed, porte=porte, plantar=plantar)
    planilha.gerar_modelo(pasta / "fechamento.xlsx", exemplo=ds)
    conector = ConectorMCP("mcp-excel", {"comando": comando_excel(pasta), "competencia": ds.competencia,
                                         "porte": porte})
    estrutura = descoberta.estrutura_mcp(conector)
    conector.mapeamento = confirmar(estrutura, ds.competencia)
    return _Temporario(conector, pasta, competencia=ds.competencia, porte=porte)


# ---------------------------------------------------------------- planilha fora do modelo (demonstração)
def gerar_planilha_fora_do_modelo(caminho, ds) -> Path:
    """A mesma empresa sintética, como uma planilha "da casa": outros nomes de abas e colunas, outra ordem,
    título acima do cabeçalho, valores em texto com R$, datas de lançamento e uma linha de total."""
    wb = Workbook()
    emp = wb.active
    emp.title = "Dados da empresa"
    emp.append(["Campo", "Valor"])
    for rotulo, valor in (("Nome da empresa", EMPRESA["razao_social"]), ("Código", ds.entidade),
                          ("Porte", ds.porte), ("Mês de referência", ds.competencia), ("Tem ERP", "não")):
        emp.append([rotulo, valor])

    def aba(titulo, cabecalho, linhas, total=None):
        ws = wb.create_sheet(titulo)
        ws.append([f"{EMPRESA['razao_social']} · {titulo}"])
        ws.append([])
        ws.append(cabecalho)
        for linha in linhas:
            ws.append(linha)
        if total:
            ws.append(total)

    def brl(c):
        reais, cents = divmod(abs(c), 100)
        return ("-" if c < 0 else "") + f"R$ {reais:,}".replace(",", ".") + f",{cents:02d}"

    pessoas = ds.perfil["pessoas"]
    aba("Equipe", ["Nome completo", "Login", "Função"], [[PESSOAS.get(u, (u,))[0], u, c] for u, c in pessoas.items()])
    aba("Vendas do mês", ["Unidade", "Código do produto", "Descrição", "Preço de venda", "Custo unitário", "Quantidade"],
        [[p["un"], p["id"], PRODUTOS.get(p["id"]), p["preco"] / 100, p["custo_variavel_unit"] / 100, p["qtd"]]
         for p in ds.produtos])
    aba("Despesas fixas", ["Departamento", "Valor mensal"], [[c["centro"], c["valor"] / 100] for c in ds.custos_fixos],
        total=["TOTAL", sum(c["valor"] for c in ds.custos_fixos) / 100])
    obs = getattr(ds, "observacoes", {}) or {}
    aba("Orçamento x realizado", ["Conta contábil", "Obs", "Meta trimestre", "Orçado até o mês", "Realizado até o mês"],
        [[o["conta"], obs.get(o["conta"]), brl(o["orcado_trimestre"]), brl(o["orcado_acumulado"]),
          brl(o["realizado_acumulado"])] for o in ds.orcamento])
    lancs = []
    for x in ds.lancamentos:
        a, m = int(x["competencia"][:4]), int(x["competencia"][5:])
        dia = 1 + int("".join(ch for ch in x["id"] if ch.isdigit())) % 27
        lancs.append([date(a, m, dia), x["id"], x["fornecedor"], x["documento"], x["conta"], brl(x["valor"]),
                      x["criador"], x["aprovador"], "Ativo"])
    aba("Lançamentos contábeis", ["Data do lançamento", "Nº lançamento", "Credor", "Nota fiscal", "Conta",
                                  "Valor", "Lançado por", "Aprovado por", "Status"], lancs,
        total=["Total", None, None, None, None, brl(sum(x["valor"] for x in ds.lancamentos))])
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho

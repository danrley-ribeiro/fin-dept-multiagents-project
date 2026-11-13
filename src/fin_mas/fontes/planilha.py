"""Modelos Excel para empresas sem ERP (modo manual) e leitura validada da pasta preenchida.

    python -m fin_mas modelos --out modelos/            # modelo em branco + exemplos por porte
    python -m fin_mas run --pasta dados/empresa ...     # agentes leem a planilha preenchida

Um único arquivo .xlsx por empresa e competência, com as abas abaixo. Valores em reais
na planilha (R$ 1.234,56) viram centavos inteiros no sistema. As correções que o
aprovador aceita (estornar, reaprovar, reclassificar) são gravadas de volta na planilha,
na coluna "Situação" ou no próprio campo, para a pasta continuar sendo a fonte da verdade.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from fin_mas.env.dataset import RATEIO, mes_no_trimestre
from fin_mas.env.empresa import EMPRESA, PESSOAS
from fin_mas.env.portes import PORTES, perfil
from fin_mas.env.segmentos import SEGMENTO_PADRAO, SEGMENTOS, segmento as perfil_segmento

VERSAO_MODELO = "modelo-controladoria-v1"
FORMATO_BRL = '"R$" #,##0.00'
SITUACOES = ("ativo", "estornado")
CARGOS = ("assistente", "analista", "gerente", "diretor", "socio", "titular")  # titular: MEI (DSM4)

# aba -> [(chave, título da coluna, tipo, obrigatório)]; tipo: texto | inteiro | reais | competencia
ABAS = {
    "Pessoas": [("usuario", "Usuário", "texto", True), ("nome", "Nome", "texto", True),
                ("cargo", "Cargo", "texto", True)],
    "Produtos": [("id", "Código", "texto", True), ("nome", "Produto ou serviço", "texto", False),
                 ("un", "Unidade de negócio", "texto", True), ("qtd", "Quantidade vendida no mês", "inteiro", True),
                 ("preco", "Preço unitário (R$)", "reais", True),
                 ("custo_variavel_unit", "Custo variável unitário (R$)", "reais", True)],
    "CustosFixos": [("centro", "Centro de custo", "texto", True), ("descricao", "Descrição", "texto", False),
                    ("valor", "Valor no mês (R$)", "reais", True)],
    "Orcamento": [("conta", "Conta", "texto", True), ("orcado_trimestre", "Orçado no trimestre (R$)", "reais", True),
                  ("orcado_acumulado", "Orçado acumulado até o mês (R$)", "reais", True),
                  ("realizado_acumulado", "Realizado acumulado até o mês (R$)", "reais", True)],
    "Lancamentos": [("id", "Código", "texto", True), ("competencia", "Competência (AAAA-MM)", "competencia", True),
                    ("conta", "Conta", "texto", True), ("fornecedor", "Fornecedor", "texto", True),
                    ("documento", "Documento (NF)", "texto", True), ("valor", "Valor (R$)", "reais", True),
                    ("criador", "Criado por (usuário)", "texto", True),
                    ("aprovador", "Aprovado por (usuário)", "texto", True),
                    ("situacao", "Situação", "texto", False)],
}
CAMPOS_EMPRESA = [("razao_social", "Razão social"), ("sigla", "Sigla"), ("porte", "Porte"),
                  ("competencia", "Competência do fechamento (AAAA-MM)"), ("tem_erp", "Possui ERP? (sim/não)"),
                  ("segmento", "Segmento (opcional)")]  # DSM4; ausente = software_servicos

LEIA_ME = [
    "Modelo de dados da controladoria para empresas sem ERP (ou que preferem planilha).",
    "1. Preencha a aba Empresa (porte define alçadas, materialidade e severidades: ver models/portes.yaml).",
    "2. Pessoas: todos que criam ou aprovam lançamentos e o cargo de cada um (o cargo define a alçada).",
    "3. Produtos e CustosFixos: vendas e custos do mês (base da margem de contribuição e da DRE).",
    "4. Orcamento: orçado e realizado acumulados por conta no trimestre.",
    "5. Lancamentos: um por linha; não apague lançamentos — marque a Situação como 'estornado'.",
    "Valores em reais (R$). Competência no formato AAAA-MM. Não renomeie abas nem colunas.",
    "Depois envie o arquivo pelo dashboard (Dados da empresa) ou coloque-o na pasta de dados.",
    f"Versão do modelo: {VERSAO_MODELO}.",
]


class ModeloInvalido(ValueError):
    def __init__(self, erros: list[str]):
        super().__init__("; ".join(erros[:5]) + (f" (+{len(erros) - 5})" if len(erros) > 5 else ""))
        self.erros = erros


# ---------------------------------------------------------------- geração dos modelos
def gerar_modelo(caminho, exemplo=None) -> Path:
    """Grava o modelo .xlsx; com `exemplo` (Dataset sintético), já vem preenchido para estudo."""
    wb = Workbook()
    leia = wb.active
    leia.title = "LEIA-ME"
    leia["A1"] = f"{EMPRESA['razao_social']} · modelo de controladoria"
    leia["A1"].font = Font(bold=True, size=14, color="1F4E79")
    for i, linha in enumerate(LEIA_ME, start=3):
        leia.cell(row=i, column=1, value=linha)
    leia.column_dimensions["A"].width = 110

    emp = wb.create_sheet("Empresa")
    _cabecalho(emp, ["Campo", "Valor"])
    valores = _empresa_exemplo(exemplo)
    for i, (chave, rotulo) in enumerate(CAMPOS_EMPRESA, start=2):
        emp.cell(row=i, column=1, value=rotulo)
        emp.cell(row=i, column=2, value=valores.get(chave, ""))
    emp.column_dimensions["A"].width, emp.column_dimensions["B"].width = 40, 36
    _lista(emp, "B4", PORTES)
    _lista(emp, "B6", ("sim", "não"))
    _lista(emp, "B7", SEGMENTOS)

    linhas = _linhas_exemplo(exemplo)
    for aba, colunas in ABAS.items():
        ws = wb.create_sheet(aba)
        _cabecalho(ws, [c[1] for c in colunas])
        for r, registro in enumerate(linhas.get(aba, []), start=2):
            for k, (chave, _, tipo, _) in enumerate(colunas, start=1):
                cel = ws.cell(row=r, column=k, value=registro.get(chave))
                if tipo == "reais":
                    cel.number_format = FORMATO_BRL
        for k, (_, titulo, tipo, _) in enumerate(colunas, start=1):
            letra = ws.cell(row=1, column=k).column_letter
            ws.column_dimensions[letra].width = max(14, len(titulo) + 2)
            if tipo == "reais":
                for r in range(2, 501):
                    ws.cell(row=r, column=k).number_format = FORMATO_BRL
        ws.freeze_panes = "A2"
    _lista(wb["Pessoas"], "C2:C200", CARGOS)
    seg = perfil_segmento(getattr(exemplo, "segmento", SEGMENTO_PADRAO))
    _lista(wb["Produtos"], "C2:C200", tuple(seg["rateio_pct"]))
    _lista(wb["Orcamento"], "A2:A200", tuple(seg["contas"]) + (seg["conta_chamariz"],), restrito=False)
    _lista(wb["Lancamentos"], "I2:I2000", SITUACOES)
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)
    return caminho


def gerar_modelos(pasta) -> list[Path]:
    """Modelo em branco, um exemplo preenchido por porte e um por segmento (média empresa)."""
    from fin_mas.env.dataset import Dataset
    pasta = Path(pasta)
    arquivos = [gerar_modelo(pasta / "modelo_controladoria_em_branco.xlsx")]
    for porte in PORTES:
        ds = Dataset(seed=42, porte=porte, plantar=("competencia",))
        arquivos.append(gerar_modelo(pasta / f"exemplo_{porte}.xlsx", exemplo=ds))
    for seg in SEGMENTOS:
        if seg != SEGMENTO_PADRAO:
            ds = Dataset(seed=42, segmento=seg, plantar=("competencia",))
            arquivos.append(gerar_modelo(pasta / f"exemplo_{seg}.xlsx", exemplo=ds))
    return arquivos


def _cabecalho(ws, titulos):
    for k, t in enumerate(titulos, start=1):
        c = ws.cell(row=1, column=k, value=t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E79")
        c.alignment = Alignment(vertical="center", wrap_text=True)


def _lista(ws, faixa, opcoes, restrito=True):
    dv = DataValidation(type="list", formula1='"' + ",".join(opcoes) + '"', allow_blank=True,
                        showErrorMessage=restrito)
    ws.add_data_validation(dv)
    dv.add(faixa)


def _empresa_exemplo(ds) -> dict:
    if ds is None:
        return {"porte": "micro", "competencia": date.today().strftime("%Y-%m"), "tem_erp": "não"}
    valores = {"razao_social": EMPRESA["razao_social"], "sigla": EMPRESA["sigla"], "porte": ds.porte,
               "competencia": ds.competencia, "tem_erp": "não"}
    if getattr(ds, "segmento", SEGMENTO_PADRAO) != SEGMENTO_PADRAO:
        valores["segmento"] = ds.segmento
    return valores


def _reais(centavos):
    return round(centavos / 100, 2)


def _linhas_exemplo(ds) -> dict:
    if ds is None:
        return {}
    from fin_mas.env.empresa import PRODUTOS
    nomes = {**PRODUTOS, **{p["id"]: p["nome"] for p in perfil_segmento(getattr(ds, "segmento", SEGMENTO_PADRAO))["produtos"]}}
    return {
        "Pessoas": [{"usuario": u, "nome": PESSOAS[u][0], "cargo": c} for u, c in ds.perfil["pessoas"].items()],
        "Produtos": [{"id": p["id"], "nome": nomes.get(p["id"]), "un": p["un"], "qtd": p["qtd"],
                      "preco": _reais(p["preco"]), "custo_variavel_unit": _reais(p["custo_variavel_unit"])}
                     for p in ds.produtos],
        "CustosFixos": [{"centro": c["centro"], "valor": _reais(c["valor"])} for c in ds.custos_fixos],
        "Orcamento": [{"conta": o["conta"], "orcado_trimestre": _reais(o["orcado_trimestre"]),
                       "orcado_acumulado": _reais(o["orcado_acumulado"]),
                       "realizado_acumulado": _reais(o["realizado_acumulado"])} for o in ds.orcamento],
        "Lancamentos": [{**{k: lanc[k] for k in ("id", "competencia", "conta", "fornecedor", "documento", "criador",
                                                  "aprovador")}, "valor": _reais(lanc["valor"]), "situacao": "ativo"}
                        for lanc in ds.lancamentos],
    }


# ---------------------------------------------------------------- leitura validada
def localizar(pasta) -> Path:
    pasta = Path(pasta)
    if pasta.is_file():
        return pasta
    arquivos = sorted(p for p in pasta.glob("*.xlsx") if not p.name.startswith("~$"))
    if not arquivos:
        raise ModeloInvalido([f"nenhuma planilha .xlsx em {pasta}"])
    if len(arquivos) > 1:
        raise ModeloInvalido([f"mais de uma planilha em {pasta}: deixe só a da competência ({', '.join(a.name for a in arquivos)})"])
    return arquivos[0]


def ler_abas(arquivo) -> dict[str, list[dict]]:
    """Linhas de cada aba como dicionários pelo título da coluna (sem conversão)."""
    wb = load_workbook(arquivo, data_only=True, read_only=True)
    abas = {}
    for ws in wb.worksheets:
        linhas = list(ws.iter_rows(values_only=True))
        if not linhas:
            abas[ws.title] = []
            continue
        cab = [str(c).strip() if c is not None else "" for c in linhas[0]]
        abas[ws.title] = [dict(zip(cab, linha)) for linha in linhas[1:] if any(v not in (None, "") for v in linha)]
    wb.close()
    return abas


def _converter(valor, tipo, onde, erros):
    if valor in (None, ""):
        return None
    try:
        if tipo == "reais":
            if isinstance(valor, str):
                valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            return int(round(float(valor) * 100))
        if tipo == "inteiro":
            return int(float(valor))
        if tipo == "competencia":
            texto = valor.strftime("%Y-%m") if hasattr(valor, "strftime") else str(valor).strip()
            if len(texto) != 7 or texto[4] != "-" or not (texto[:4] + texto[5:]).isdigit() or not 1 <= int(texto[5:]) <= 12:
                raise ValueError
            return texto
        return str(valor).strip()
    except (ValueError, TypeError):
        erros.append(f"{onde}: valor inválido {valor!r} (esperado {tipo})")
        return None


def ler(pasta_ou_arquivo) -> "DatasetPlanilha":
    arquivo = localizar(pasta_ou_arquivo)
    abas = ler_abas(arquivo)
    erros: list[str] = []
    for aba in ("Empresa", *ABAS):
        if aba not in abas:
            erros.append(f"aba ausente: {aba}")
    if erros:
        raise ModeloInvalido(erros)
    empresa = {}
    rotulos = {r: k for k, r in CAMPOS_EMPRESA}
    for linha in abas["Empresa"]:
        chave = rotulos.get(str(linha.get("Campo") or "").strip())
        if chave:
            empresa[chave] = linha.get("Valor")
    porte = str(empresa.get("porte") or "").strip().lower()
    if porte not in PORTES:
        erros.append(f"Empresa: porte inválido {empresa.get('porte')!r} (use {', '.join(PORTES)})")
    competencia = _converter(empresa.get("competencia"), "competencia", "Empresa: competência", erros)
    seg = str(empresa.get("segmento") or SEGMENTO_PADRAO).strip().lower()
    if seg not in SEGMENTOS:
        erros.append(f"Empresa: segmento inválido {empresa.get('segmento')!r} (use {', '.join(SEGMENTOS)})")
    dados = {}
    for aba, colunas in ABAS.items():
        cab = set(abas[aba][0]) if abas[aba] else {c[1] for c in colunas}
        faltando = [c[1] for c in colunas if c[3] and c[1] not in cab]
        if faltando:
            erros.append(f"{aba}: colunas ausentes: {', '.join(faltando)}")
            continue
        registros = []
        for n, linha in enumerate(abas[aba], start=2):
            r = {}
            for chave, titulo, tipo, obrigatorio in colunas:
                v = _converter(linha.get(titulo), tipo, f"{aba}!{titulo} linha {n}", erros)
                if v is None and obrigatorio:
                    erros.append(f"{aba} linha {n}: {titulo} é obrigatório")
                r[chave] = v
            r["_linha"] = n
            registros.append(r)
        dados[aba] = registros
    if not str(empresa.get("razao_social") or "").strip():
        erros.append("Empresa: razão social é obrigatória")
    for aba in ("Pessoas", "Produtos", "Orcamento"):
        if aba in dados and not dados[aba]:
            erros.append(f"{aba}: nenhuma linha preenchida")
    if not erros:
        _validar_referencias(dados, porte, erros, seg)
    if erros:
        raise ModeloInvalido(erros)
    return DatasetPlanilha(arquivo=arquivo, porte=porte, competencia=competencia,
                           razao_social=str(empresa.get("razao_social") or ""),
                           entidade=str(empresa.get("sigla") or "EMPRESA"),
                           tem_erp=str(empresa.get("tem_erp") or "não").strip().lower() == "sim", dados=dados,
                           segmento=seg)


def _validar_referencias(dados, porte, erros, seg=SEGMENTO_PADRAO):
    pessoas = {p["usuario"]: p["cargo"] for p in dados["Pessoas"]}
    limites = perfil(porte)["limites_alcada"]
    for p in dados["Pessoas"]:
        if p["cargo"] not in limites:
            erros.append(f"Pessoas linha {p['_linha']}: cargo {p['cargo']!r} não existe no porte {porte} "
                         f"(use {', '.join(limites)})")
    contas = {o["conta"] for o in dados["Orcamento"]}
    for lanc in dados["Lancamentos"]:
        for campo in ("criador", "aprovador"):
            if lanc[campo] not in pessoas:
                erros.append(f"Lancamentos linha {lanc['_linha']}: {campo} {lanc[campo]!r} não está na aba Pessoas")
        if lanc["conta"] not in contas:
            erros.append(f"Lancamentos linha {lanc['_linha']}: conta {lanc['conta']!r} não está na aba Orcamento")
        if (lanc.get("situacao") or "ativo") not in SITUACOES:
            erros.append(f"Lancamentos linha {lanc['_linha']}: situação {lanc['situacao']!r} (use ativo ou estornado)")
    unidades = perfil_segmento(seg)["rateio_pct"] if seg != SEGMENTO_PADRAO else RATEIO
    for p in dados["Produtos"]:
        if p["un"] not in unidades:
            erros.append(f"Produtos linha {p['_linha']}: unidade {p['un']!r} (use {', '.join(unidades)})")


@dataclass
class DatasetPlanilha:
    """Mesma interface do Dataset sintético, alimentada pela planilha preenchida (sem gabarito)."""

    arquivo: Path
    porte: str
    competencia: str
    razao_social: str
    entidade: str
    tem_erp: bool
    dados: dict
    seed: int = 0
    plantar: tuple = ()
    correcoes: list = field(default_factory=list)
    segmento: str = SEGMENTO_PADRAO  # DSM4: define unidades e o direcionador de rateio do AG-CUS

    def __post_init__(self):
        seg = perfil_segmento(self.segmento)
        self.rateio, self.versao_rateio, self.perfil_segmento = dict(seg["rateio_pct"]), seg["rateio"]["versao"], seg
        self.perfil = {**perfil(self.porte), "tem_erp": self.tem_erp}
        self.perfil["pessoas"] = {p["usuario"]: p["cargo"] for p in self.dados["Pessoas"]}
        self.perfil["fonte_primaria"] = "ERP" if self.tem_erp else "planilha"
        self.produtos = [{k: p[k] for k in ("id", "un", "qtd", "preco", "custo_variavel_unit")}
                         for p in self.dados["Produtos"]]
        self.custos_fixos = [{"centro": c["centro"], "valor": c["valor"]} for c in self.dados["CustosFixos"]]
        self.orcamento = [{k: o[k] for k in ("conta", "orcado_trimestre", "orcado_acumulado", "realizado_acumulado")}
                          for o in self.dados["Orcamento"]]
        self.lancamentos = [{k: lanc[k] for k in ("id", "competencia", "conta", "fornecedor", "documento", "valor",
                                                  "criador", "aprovador")}
                            for lanc in self.dados["Lancamentos"] if (lanc.get("situacao") or "ativo") == "ativo"]
        self.realizado_erp = {}  # sem ERP: a planilha é a única fonte do realizado
        self.gold = {"meses_decorridos": mes_no_trimestre(self.competencia)}  # dados reais não têm gabarito

    def proveniencia(self, aba) -> str:
        return f"mcp://excel/{self.arquivo.name}#{aba}"

    def corrigir(self, lancamento: str, acao: str) -> dict:
        """Aplica a correção aceita pelo aprovador e a grava na própria planilha."""
        lanc = next(x for x in self.lancamentos if x["id"] == lancamento)
        wb = load_workbook(self.arquivo)
        ws = wb["Lancamentos"]
        cab = {c.value: c.column for c in ws[1]}
        linha = next(r for r in range(2, ws.max_row + 1) if str(ws.cell(r, cab["Código"]).value) == lancamento)
        if acao == "estornar":
            ws.cell(linha, cab["Situação"], "estornado")
            self.lancamentos.remove(lanc)
            detalhe = f"{lancamento} marcado como estornado na planilha"
        elif acao == "reaprovar":
            limites = self.perfil["limites_alcada"]
            pode_criador = self.perfil["severidade"]["sod"] != "critica"  # controle compensatório (micro)
            novo = next((u for u, cargo in self.perfil["pessoas"].items() if (u != lanc["criador"] or pode_criador)
                         and cargo in self.perfil["aprovadores"]
                         and (limites[cargo] is None or limites[cargo] >= lanc["valor"])), None)
            if novo is None:
                raise ValueError(f"{lancamento}: não há outra pessoa com alçada para reaprovar")
            ws.cell(linha, cab["Aprovado por (usuário)"], novo)
            detalhe = f"{lancamento} reaprovado por {novo} (antes {lanc['aprovador']}) na planilha"
            lanc["aprovador"] = novo
        elif acao == "reclassificar":
            ws.cell(linha, cab["Competência (AAAA-MM)"], self.competencia)
            detalhe = f"{lancamento} reclassificado para {self.competencia} na planilha"
            lanc["competencia"] = self.competencia
        else:
            raise ValueError(f"ação de correção desconhecida: {acao}")
        wb.save(self.arquivo)
        registro = {"lancamento": lancamento, "acao": acao, "detalhe": detalhe}
        self.correcoes.append(registro)
        return registro

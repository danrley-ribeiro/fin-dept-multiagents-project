"""Conectores de planilha: pasta no modelo canônico (várias competências) e planilha fora do modelo.

`ConectorPastaPlanilhas`: uma pasta com uma planilha do modelo da SMA por competência
(`fontes/planilha.py`). Com uma planilha só, é exatamente o comportamento de `Ambiente.de_pasta`
(mesmo `DatasetPlanilha`, mesma proveniência, correção gravada de volta na planilha).

`ConectorPlanilha`: um arquivo .xlsx qualquer (abas e colunas com outros nomes, em outra ordem,
cabeçalho fora da primeira linha, linha de total no fim). As abas são lidas com detecção de
cabeçalho determinística e o mapeamento confirmado diz o que é cada coluna.
"""
from pathlib import Path

from openpyxl import load_workbook

from fin_mas.conectores.base import (ConectorMapeado, Conector, DadosCanonicos, ErroConector, FonteIndisponivel,
                                     diagnostico, etapa)
from fin_mas.conectores.canonico import normalizar
from fin_mas.fontes import planilha

LINHAS_PROCURA_CABECALHO = 15


# ---------------------------------------------------------------- leitura crua com detecção de cabeçalho
def detectar_cabecalho(linhas: list[tuple]) -> int:
    """Índice (0-based) da linha de cabeçalho: a primeira, entre as 15 primeiras, com mais células de texto
    distintas e seguida de uma linha com dados. Título, logotipo e linhas em branco acima são pulados."""
    melhor, pontos = 0, -1
    for i, linha in enumerate(linhas[:LINHAS_PROCURA_CABECALHO]):
        textos = [c for c in linha if isinstance(c, str) and c.strip()]
        if len(textos) < 2 or len(set(textos)) != len(textos):
            continue
        seguinte = linhas[i + 1] if i + 1 < len(linhas) else ()
        if sum(1 for c in seguinte if c not in (None, "")) < 2:
            continue
        if len(textos) > pontos:
            melhor, pontos = i, len(textos)
    return melhor


def linha_de_total(registro: dict) -> bool:
    """Linha de soma ao fim da tabela ("Total", "TOTAL GERAL", "Soma"): não é um registro."""
    for v in registro.values():
        if isinstance(v, str) and v.strip():
            return normalizar(v).split("_")[0] in ("total", "soma", "subtotal")
    return False


CHAVE_VALOR = ({"campo", "valor"}, {"field", "value"}, {"chave", "valor"}, {"item", "valor"}, {"key", "value"})


def eh_chave_valor(colunas) -> bool:
    """Tabela de pares campo/valor (ex.: a aba Empresa do modelo): vira um registro único."""
    return {normalizar(c) for c in list(colunas)[:2]} in CHAVE_VALOR and len(colunas) == 2


def chave_valor(registros: list[dict], colunas=None) -> list[dict]:
    if not registros:
        return []
    c1, c2 = (list(colunas) if colunas else list(registros[0]))[:2]
    return [{str(r[c1]).strip(): r.get(c2) for r in registros if r.get(c1) not in (None, "")}]


def ler_tabelas(arquivo) -> dict[str, dict]:
    """Por aba: cabeçalho detectado, registros (sem a linha de total) e o total, se houver."""
    try:
        wb = load_workbook(arquivo, data_only=True, read_only=True)
    except FileNotFoundError:
        raise FonteIndisponivel(f"planilha não encontrada: {Path(arquivo).name}") from None
    except Exception as e:  # arquivo que nem abre como xlsx
        raise ErroConector(f"não foi possível abrir {Path(arquivo).name}: {type(e).__name__}") from None
    saida = {}
    for ws in wb.worksheets:
        linhas = [tuple(r) for r in ws.iter_rows(values_only=True)]
        if not any(any(c not in (None, "") for c in r) for r in linhas):
            saida[ws.title] = {"cabecalho_linha": None, "colunas": [], "registros": [], "totais": []}
            continue
        i = detectar_cabecalho(linhas)
        colunas = [str(c).strip() if c not in (None, "") else f"coluna_{k + 1}" for k, c in enumerate(linhas[i])]
        registros, totais = [], []
        for linha in linhas[i + 1:]:
            if not any(c not in (None, "") for c in linha):
                continue
            r = dict(zip(colunas, linha))
            (totais if linha_de_total(r) else registros).append(r)
        formato = "tabela"
        if eh_chave_valor(colunas):
            registros, totais, formato = chave_valor(registros, colunas), [], "chave_valor"
        saida[ws.title] = {"cabecalho_linha": i + 1, "colunas": colunas, "registros": registros, "totais": totais,
                           "formato": formato}
    wb.close()
    return saida


# ---------------------------------------------------------------- pasta no modelo canônico
class ConectorPastaPlanilhas(Conector):
    tipo = "planilhas"

    def __init__(self, id: str, pasta, porte: str | None = None):
        super().__init__(id, porte)
        self.pasta = Path(pasta)
        self._cache: dict[str, tuple] = {}

    def capacidades(self) -> set:
        return {"leitura", "escrita", "competencias"}

    def arquivos(self) -> list[Path]:
        if self.pasta.is_file():
            return [self.pasta]
        return sorted(p for p in self.pasta.glob("*.xlsx") if not p.name.startswith("~$"))

    def validos(self) -> dict[str, "planilha.DatasetPlanilha"]:
        """Competência -> planilha válida (a mais recente por nome, se houver duas da mesma competência)."""
        saida = {}
        for arquivo in self.arquivos():
            marca = (arquivo.stat().st_mtime_ns, arquivo.stat().st_size)
            cache = self._cache.get(str(arquivo))
            if cache is None or cache[0] != marca:
                try:
                    cache = (marca, planilha.ler(arquivo), None)
                except planilha.ModeloInvalido as e:
                    cache = (marca, None, e.erros)
                self._cache[str(arquivo)] = cache
            if cache[1] is not None:
                saida[cache[1].competencia] = cache[1]
        return saida

    def competencia_padrao(self):
        competencias = sorted(self.validos())
        return competencias[-1] if competencias else None

    def dataset(self, competencia):
        validos = self.validos()
        if not validos:
            raise FonteIndisponivel(f"nenhuma planilha válida na pasta da fonte {self.id}")
        c = competencia or max(validos)
        if c not in validos:
            raise LookupError(f"não há planilha da competência {c} (há {', '.join(sorted(validos))})")
        return planilha.ler(validos[c].arquivo)  # leitura nova: as correções são gravadas nela

    def ler(self, competencia) -> DadosCanonicos:
        ds = self.dataset(competencia)
        dados = {**{aba: [{k: v for k, v in r.items()} for r in regs] for aba, regs in ds.dados.items()}}
        return DadosCanonicos(ds.competencia, {"razao_social": ds.razao_social, "sigla": ds.entidade,
                                               "porte": ds.porte, "tem_erp": ds.tem_erp},
                              dados, {aba: ds.proveniencia(aba) for aba in dados})

    def corrigir(self, competencia, lancamento, acao) -> dict:
        return self.dataset(competencia).corrigir(lancamento, acao)

    def testar(self) -> dict:
        arquivos = self.arquivos()
        if not arquivos:
            return diagnostico([etapa("pasta", False, "nenhuma planilha .xlsx na pasta")])
        etapas = [etapa("pasta", True, f"{len(arquivos)} planilha(s)")]
        self.validos()
        for a in arquivos:
            _, ds, erros = self._cache[str(a)]
            etapas.append(etapa(a.name, ds is not None, f"competência {ds.competencia}, porte {ds.porte}, "
                                                        f"{len(ds.lancamentos)} lançamentos" if ds else "; ".join(erros[:3])))
        return diagnostico(etapas)

    def descricao(self) -> dict:
        return {**super().descricao(), "competencias": sorted(self.validos())}


# ---------------------------------------------------------------- planilha fora do modelo
class ConectorPlanilha(ConectorMapeado):
    tipo = "planilha"

    def __init__(self, id: str, arquivo, mapeamento: dict | None = None, porte: str | None = None):
        super().__init__(id, mapeamento, porte)
        self.arquivo = Path(arquivo)

    def capacidades(self) -> set:
        campos = ((self.mapeamento or {}).get("abas", {}).get("Lancamentos", {}) or {}).get("campos", {})
        return {"leitura"} | ({"escrita"} if {"id", "situacao"} <= set(campos) else set())

    def competencia_padrao(self):
        origem = ((self.mapeamento or {}).get("empresa") or {}).get("competencia") or {}
        return origem.get("valor")

    def tabelas(self) -> dict:
        return ler_tabelas(self.arquivo)

    def ler(self, competencia):
        self._tabelas = self.tabelas()
        try:
            return super().ler(competencia)
        finally:
            self._tabelas = None

    def ler_recurso(self, recurso, competencia) -> list[dict]:
        tabelas = getattr(self, "_tabelas", None) or self.tabelas()
        if recurso not in tabelas:
            raise ErroConector(f"aba {recurso!r} não existe em {self.arquivo.name}")
        return tabelas[recurso]["registros"]

    def uri(self, recurso: str) -> str:
        return f"mcp://excel/{self.arquivo.name}#{recurso}"

    def testar(self) -> dict:
        try:
            tabelas = self.tabelas()
        except ErroConector as e:
            return diagnostico([etapa("arquivo", False, str(e))])
        etapas = [etapa("arquivo", True, f"{self.arquivo.name}: {len(tabelas)} aba(s)")]
        for aba, t in tabelas.items():
            etapas.append(etapa(f"aba {aba}", True, f"cabeçalho na linha {t['cabecalho_linha']}, "
                                                     f"{len(t['registros'])} registro(s)"
                                                     + (f", {len(t['totais'])} linha(s) de total" if t["totais"] else "")))
        return diagnostico(etapas)

    def corrigir(self, competencia, lancamento, acao) -> dict:
        """Estorno marcado na coluna de situação mapeada (a planilha continua sendo a fonte da verdade)."""
        spec = ((self.mapeamento or {}).get("abas") or {}).get("Lancamentos") or {}
        campos = spec.get("campos") or {}
        if acao != "estornar" or "situacao" not in campos or "id" not in campos:
            return super().corrigir(competencia, lancamento, acao)
        aba = spec["recurso"]
        cabecalho = self.tabelas()[aba]["cabecalho_linha"]
        wb = load_workbook(self.arquivo)
        ws = wb[aba]
        colunas = {str(c.value).strip(): c.column for c in ws[cabecalho] if c.value not in (None, "")}
        col_id, col_sit = colunas[campos["id"]["origem"]], colunas[campos["situacao"]["origem"]]
        for r in range(cabecalho + 1, ws.max_row + 1):
            if str(ws.cell(r, col_id).value).strip() == lancamento:
                ws.cell(r, col_sit, "estornado")
                wb.save(self.arquivo)
                return {"lancamento": lancamento, "acao": acao,
                        "detalhe": f"{lancamento} marcado como estornado na planilha {self.arquivo.name}"}
        raise ErroConector(f"lançamento {lancamento} não encontrado em {self.arquivo.name}")

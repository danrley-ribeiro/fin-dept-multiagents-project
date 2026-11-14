"""Modelo canônico de dados da controladoria e conversões determinísticas (ADR-011).

É o mesmo modelo da planilha (`fontes/planilha.py`: abas, chaves, tipos e obrigatoriedade),
acrescido do que só um ERP costuma ter (realizado contábil por conta, histórico mensal) e do
texto livre do orçamento. Todo conector entrega os dados neste formato: valores monetários em
centavos inteiros, competência como `AAAA-MM`, textos aparados.

Um **mapeamento** diz, para cada aba canônica, de qual recurso da fonte ela vem e, para cada
campo, a coluna de origem e a conversão:

    {"abas": {"Lancamentos": {"recurso": "journal-entries",
                              "campos": {"valor": {"origem": "amount", "conversao": "reais"}, ...}}},
     "empresa": {"porte": {"valor": "media"}, "razao_social": {"recurso": "company", "origem": "legal_name"}}}

O mapeamento só vale depois de confirmado por uma pessoa com permissão (`fontes/registro.py`).
"""
import re
import unicodedata
from datetime import date, datetime

from fin_mas.fontes.planilha import ABAS, CAMPOS_EMPRESA, SITUACOES

# aba -> [(chave, título, tipo, obrigatório)]; tipos: texto | inteiro | reais | competencia | booleano
CANONICO: dict[str, list[tuple]] = {
    "Empresa": [("razao_social", "Razão social", "texto", False), ("sigla", "Sigla", "texto", False),
                ("porte", "Porte", "texto", False), ("competencia", "Competência (AAAA-MM)", "competencia", False),
                ("tem_erp", "Possui ERP?", "booleano", False),
                ("segmento", "Segmento", "texto", False)],  # opcional; ausente = software_servicos
    **{aba: list(colunas) for aba, colunas in ABAS.items()},
    "Realizado": [("conta", "Conta", "texto", True),
                  ("realizado_acumulado", "Realizado contábil acumulado (R$)", "reais", True)],
    "Historico": [("conta", "Conta", "texto", True), ("competencia", "Competência (AAAA-MM)", "competencia", True),
                  ("orcado", "Orçado no mês (R$)", "reais", True), ("realizado", "Realizado no mês (R$)", "reais", True)],
}
CANONICO["Orcamento"] = CANONICO["Orcamento"] + [("observacao", "Observações", "texto", False)]
ABAS_OBRIGATORIAS = ("Pessoas", "Produtos", "CustosFixos", "Orcamento", "Lancamentos")
ABAS_OPCIONAIS = ("Empresa", "Realizado", "Historico")
assert {k for k, _ in CAMPOS_EMPRESA} == {c[0] for c in CANONICO["Empresa"]}

CONVERSOES = ("texto", "inteiro", "reais", "centavos", "competencia", "data_competencia", "booleano", "situacao")
# conversões aceitas por tipo canônico (a primeira é a padrão)
CONVERSOES_DO_TIPO = {"texto": ("texto", "situacao"), "inteiro": ("inteiro",), "reais": ("reais", "centavos"),
                      "competencia": ("competencia", "data_competencia"), "booleano": ("booleano",)}

SITUACAO_SINONIMOS = {
    "ativo": {"ativo", "ativa", "active", "posted", "lancado", "aprovado", "approved", "open", "aberto", "valido"},
    "estornado": {"estornado", "estornada", "estorno", "reversed", "reversal", "cancelled", "canceled", "cancelado",
                  "void", "anulado"},
}
assert set(SITUACAO_SINONIMOS) == set(SITUACOES)
VERDADEIRO = {"sim", "s", "yes", "y", "true", "1", "verdadeiro"}
FALSO = {"nao", "n", "no", "false", "0", "falso"}
COMPETENCIA = re.compile(r"^(\d{4})-(\d{2})$")
DATA_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})([T ].*)?$")
DATA_BR = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


class ConversaoInvalida(ValueError):
    pass


def campo(aba: str, chave: str) -> tuple | None:
    return next((c for c in CANONICO.get(aba, ()) if c[0] == chave), None)


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def normalizar(nome) -> str:
    """Nome comparável: sem acento, minúsculo, camelCase separado, só letras e números unidos por `_`."""
    texto = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(nome or ""))
    texto = re.sub(r"\(.*?\)", " ", sem_acento(texto).lower())  # "Valor (R$)" -> "valor"
    return "_".join(re.findall(r"[a-z0-9]+", texto))


def numero(valor) -> float:
    """Número de um valor de planilha ou JSON: 1234.5, "1234,50", "R$ 1.234,56", "1,234.56"."""
    if isinstance(valor, bool):
        raise ConversaoInvalida(f"booleano não é número: {valor!r}")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).replace("R$", "").replace(" ", "").replace(" ", "").strip()
    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()")
    if not texto or not re.fullmatch(r"[-+]?[\d.,]+", texto):
        raise ConversaoInvalida(f"não é número: {valor!r}")
    if "," in texto and "." in texto:
        decimal = "," if texto.rfind(",") > texto.rfind(".") else "."
        milhar = "." if decimal == "," else ","
        texto = texto.replace(milhar, "").replace(decimal, ".")
    elif "," in texto:
        texto = texto.replace(".", "").replace(",", ".") if texto.count(",") == 1 else texto.replace(",", "")
    elif texto.count(".") > 1 or re.fullmatch(r"[-+]?\d{1,3}\.\d{3}", texto):
        texto = texto.replace(".", "")  # 1.234.567 ou 1.234: separador de milhar (pt-BR)
    x = float(texto)
    return -x if negativo else x


def competencia_de(valor) -> str:
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m")
    texto = str(valor).strip()
    m = COMPETENCIA.match(texto) or DATA_ISO.match(texto)
    if m:
        ano, mes = m.group(1), m.group(2)
    else:
        m = DATA_BR.match(texto)
        if not m:
            raise ConversaoInvalida(f"não é competência nem data: {valor!r}")
        ano, mes = m.group(3), m.group(2)
    if not 1 <= int(mes) <= 12:
        raise ConversaoInvalida(f"mês inválido em {valor!r}")
    return f"{ano}-{mes}"


def converter(valor, conversao: str):
    """Aplica uma conversão do mapeamento. Vazio vira None; valor que não converte levanta ConversaoInvalida."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if conversao == "texto":
        if isinstance(valor, float) and valor.is_integer():
            return str(int(valor))  # código numérico lido do Excel como 1001.0
        if isinstance(valor, (datetime, date)):
            return valor.isoformat()
        return str(valor).strip()
    if conversao == "inteiro":
        x = numero(valor)
        if not x.is_integer():
            raise ConversaoInvalida(f"não é inteiro: {valor!r}")
        return int(x)
    if conversao == "reais":
        return int(round(numero(valor) * 100))
    if conversao == "centavos":
        x = numero(valor)
        if not x.is_integer():
            raise ConversaoInvalida(f"centavos com casas decimais: {valor!r}")
        return int(x)
    if conversao in ("competencia", "data_competencia"):
        return competencia_de(valor)
    if conversao == "booleano":
        if isinstance(valor, bool):
            return valor
        texto = normalizar(valor)
        if texto in VERDADEIRO:
            return True
        if texto in FALSO:
            return False
        raise ConversaoInvalida(f"não é sim/não: {valor!r}")
    if conversao == "situacao":
        texto = normalizar(valor)
        for situacao, sinonimos in SITUACAO_SINONIMOS.items():
            if texto in sinonimos:
                return situacao
        raise ConversaoInvalida(f"situação desconhecida: {valor!r} (use ativo ou estornado)")
    raise ConversaoInvalida(f"conversão desconhecida: {conversao}")


def conversao_padrao(tipo_canonico: str) -> str:
    return CONVERSOES_DO_TIPO[tipo_canonico][0]


def validar_mapeamento(mapeamento: dict, recursos: dict[str, set] | None = None) -> list[str]:
    """Erros de um mapeamento (vazio = válido): aba e campo existem, conversão compatível com o tipo
    canônico, origem existe no recurso (quando a estrutura da fonte é conhecida), obrigatórios presentes."""
    erros = []
    if not isinstance(mapeamento, dict) or not isinstance(mapeamento.get("abas"), dict):
        return ["mapeamento sem a seção 'abas'"]
    for aba, spec in mapeamento["abas"].items():
        if aba not in CANONICO or aba == "Empresa":
            erros.append(f"aba canônica inexistente: {aba}")
            continue
        if not isinstance(spec, dict) or not isinstance(spec.get("campos"), dict):
            erros.append(f"{aba}: sem recurso ou campos")
            continue
        recurso = spec.get("recurso")
        if recursos is not None and recurso not in recursos:
            erros.append(f"{aba}: recurso {recurso!r} não existe na fonte")
        for chave, origem in spec["campos"].items():
            c = campo(aba, chave)
            if c is None:
                erros.append(f"{aba}.{chave}: campo canônico inexistente")
                continue
            if not isinstance(origem, dict) or not (origem.get("origem") or "valor" in origem):
                erros.append(f"{aba}.{chave}: sem coluna de origem")
                continue
            conv = origem.get("conversao") or conversao_padrao(c[2])
            if conv not in CONVERSOES_DO_TIPO[c[2]]:
                erros.append(f"{aba}.{chave}: conversão {conv!r} incompatível com o tipo {c[2]}")
            if recursos is not None and origem.get("origem") and recurso in recursos \
                    and origem["origem"] not in recursos[recurso]:
                erros.append(f"{aba}.{chave}: coluna {origem['origem']!r} não existe em {recurso}")
        for chave, _, _, obrigatorio in CANONICO[aba]:
            if obrigatorio and chave not in spec["campos"]:
                erros.append(f"{aba}: campo obrigatório {chave} sem origem")
    for aba in ABAS_OBRIGATORIAS:
        if aba not in mapeamento["abas"]:
            erros.append(f"aba obrigatória sem mapeamento: {aba}")
    for chave, origem in (mapeamento.get("empresa") or {}).items():
        if campo("Empresa", chave) is None:
            erros.append(f"Empresa.{chave}: campo inexistente")
        elif not isinstance(origem, dict) or not ("valor" in origem or origem.get("origem")):
            erros.append(f"Empresa.{chave}: informe um valor ou uma origem")
    return erros

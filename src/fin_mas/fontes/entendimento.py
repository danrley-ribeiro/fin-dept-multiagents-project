"""Entendimento automático de fontes, determinístico (ADR-011): sem IA generativa.

Quatro adaptadores levam fontes diferentes a uma representação comum:

    de_openapi(spec, amostras=None)   contrato OpenAPI 3 (e, se houver, uma página de cada recurso)
    de_amostras_json(amostras)        respostas JSON de exemplo, por recurso
    de_mcp_tools(lista, amostras=None) `tools/list` de um servidor MCP (e resultados de tools)
    de_planilha(arquivo)              qualquer .xlsx: abas, cabeçalho detectado, linha de total

Representação comum: `{"origem", "recursos": [{"nome", "raiz", "linhas", "campos": [{"nome", "tipo",
"exemplos", "nulos", "total", "distintos", "unico"}], ...}], "avisos"}`. Tipos inferidos: inteiro,
decimal, moeda_reais, moeda_centavos, data, competencia, identificador, booleano, texto.

`sugerir_mapeamento(estrutura)` propõe, para cada aba e campo do modelo canônico, o recurso e a
coluna de origem, com **confiança** e **motivo legível** (nome normalizado e sinônimos pt/en,
compatibilidade de tipo e conteúdo). `qualidade(...)` aponta faltantes, duplicados, datas fora da
competência, totais que não fecham e negativos inesperados; `previa(...)` mostra registros já
convertidos, redigidos. Nada disso vale sozinho: o mapeamento só é usado depois de confirmado por
uma pessoa com permissão (PERM-DAD-CONECTAR).

LLM opcional (`sugerir_com_llm`): desligado por padrão; se ligado, só **sugere** e explica
mapeamentos para campos que ficaram sem sugestão, a partir de nomes e tipos (sem valores), e cada
sugestão passa pela mesma validação determinística (aba e campo existem, coluna existe, tipo
compatível). Extensão explícita da NORM-07 para um consumidor de plataforma (NORM-15).
"""
import json
import re
from datetime import date, datetime

from fin_mas.conectores.canonico import (ABAS_OBRIGATORIAS, CANONICO, COMPETENCIA, DATA_BR, DATA_ISO,
                                         ConversaoInvalida, conversao_padrao, converter, normalizar, numero,
                                         validar_mapeamento)
from fin_mas.services.redacao import redigir

MAX_VALORES = 200  # valores guardados por campo para as conferências de conteúdo (não saem na API)
LIMIAR_SUGESTAO = 0.5
LIMIAR_RECURSO = 0.3

# ---------------------------------------------------------------- vocabulário (pt e en)
SINONIMOS_ABA = {
    "Empresa": ["empresa", "company", "organization", "organizacao", "dados_da_empresa", "cadastro_empresa"],
    "Pessoas": ["pessoas", "users", "usuarios", "people", "employees", "funcionarios", "colaboradores", "equipe"],
    "Produtos": ["produtos", "products", "items", "itens", "vendas", "sales", "produtos_e_servicos"],
    "CustosFixos": ["custos_fixos", "fixed_costs", "cost_centers", "centros_de_custo", "despesas_fixas", "custos"],
    "Orcamento": ["orcamento", "budget", "budget_lines", "orcado", "orcamentos", "orcado_x_realizado"],
    "Lancamentos": ["lancamentos", "journal_entries", "entries", "transactions", "lancamentos_contabeis",
                    "ledger_entries", "movimentos", "contas_a_pagar", "pagamentos", "notas"],
    "Realizado": ["realizado", "actuals", "ledger_actuals", "balances", "saldos", "realizado_contabil"],
    "Historico": ["historico", "history", "monthly_history", "serie_historica", "historico_mensal"],
}
# (aba, campo) -> sinônimos (normalizados; os em inglês ficam marcados no motivo)
SINONIMOS = {
    ("Empresa", "razao_social"): ["razao_social", "legal_name", "company_name", "nome_empresarial", "empresa", "nome"],
    ("Empresa", "sigla"): ["sigla", "trade_code", "code", "codigo", "abreviacao", "short_name"],
    ("Empresa", "porte"): ["porte", "size_class", "size", "company_size", "porte_da_empresa"],
    ("Empresa", "competencia"): ["competencia", "fiscal_period", "period", "periodo", "competencia_do_fechamento",
                                 "mes_de_referencia", "reference_month"],
    ("Empresa", "tem_erp"): ["tem_erp", "has_erp", "possui_erp", "erp"],
    ("Pessoas", "usuario"): ["usuario", "username", "user", "login", "user_id", "usuario_id", "matricula"],
    ("Pessoas", "nome"): ["nome", "full_name", "name", "nome_completo", "display_name"],
    ("Pessoas", "cargo"): ["cargo", "job_title", "role", "position", "funcao", "title"],
    ("Produtos", "id"): ["id", "codigo", "sku", "product_id", "code", "codigo_do_produto", "item"],
    ("Produtos", "nome"): ["nome", "description", "descricao", "name", "product_name", "produto",
                           "produto_ou_servico"],
    ("Produtos", "un"): ["un", "unidade_de_negocio", "business_unit", "bu", "unidade", "segmento", "divisao"],
    ("Produtos", "qtd"): ["qtd", "quantidade", "units_sold", "quantity", "qty", "quantidade_vendida",
                          "quantidade_vendida_no_mes", "volume"],
    ("Produtos", "preco"): ["preco", "unit_price", "price", "preco_unitario", "preco_de_venda", "valor_unitario"],
    ("Produtos", "custo_variavel_unit"): ["custo_variavel_unit", "unit_variable_cost", "variable_cost", "unit_cost",
                                          "custo_variavel_unitario", "custo_variavel", "custo_unitario"],
    ("CustosFixos", "centro"): ["centro", "cost_center", "centro_de_custo", "cc", "departamento", "department"],
    ("CustosFixos", "descricao"): ["descricao", "description", "historico", "detalhe"],
    ("CustosFixos", "valor"): ["valor", "monthly_amount", "amount", "value", "valor_no_mes", "valor_mensal", "total"],
    ("Orcamento", "conta"): ["conta", "account", "conta_contabil", "account_name", "rubrica", "natureza"],
    ("Orcamento", "orcado_trimestre"): ["orcado_trimestre", "quarter_budget", "quarterly_budget", "budget_quarter",
                                       "orcado_no_trimestre", "orcamento_trimestral", "meta_trimestre"],
    ("Orcamento", "orcado_acumulado"): ["orcado_acumulado", "budget_to_date", "budget_ytd", "ytd_budget",
                                       "orcado_acumulado_ate_o_mes", "orcado_ate_o_mes", "budget_qtd"],
    ("Orcamento", "realizado_acumulado"): ["realizado_acumulado", "actual_to_date", "actual_ytd", "ytd_actual",
                                          "realizado_acumulado_ate_o_mes", "realizado_ate_o_mes", "realizado",
                                          "actual_qtd"],
    ("Orcamento", "observacao"): ["observacao", "observacoes", "notes", "note", "comments", "comentario", "obs"],
    ("Lancamentos", "id"): ["id", "codigo", "entry_id", "lancamento", "lancamento_id", "journal_entry_id",
                            "transaction_id", "numero_do_lancamento", "num_lancamento"],
    ("Lancamentos", "competencia"): ["competencia", "posting_date", "period", "periodo", "data", "date",
                                     "data_do_lancamento", "data_lancamento", "entry_date", "accounting_date",
                                     "mes_de_competencia"],
    ("Lancamentos", "conta"): ["conta", "account", "conta_contabil", "account_name", "rubrica"],
    ("Lancamentos", "fornecedor"): ["fornecedor", "vendor", "supplier", "credor", "beneficiario", "payee",
                                    "fornecedor_id", "vendor_id"],
    ("Lancamentos", "documento"): ["documento", "invoice_number", "invoice", "document", "nf", "nota_fiscal",
                                   "numero_da_nf", "documento_fiscal", "doc", "invoice_id"],
    ("Lancamentos", "valor"): ["valor", "amount", "value", "valor_do_lancamento", "valor_total", "total",
                               "montante", "net_amount"],
    ("Lancamentos", "criador"): ["criador", "created_by", "author", "criado_por", "lancado_por", "entered_by",
                                 "criado_por_usuario", "preparer"],
    ("Lancamentos", "aprovador"): ["aprovador", "approved_by", "approver", "aprovado_por", "autorizado_por",
                                   "aprovado_por_usuario", "authorized_by"],
    ("Lancamentos", "situacao"): ["situacao", "status", "state", "estado", "situacao_do_lancamento"],
    ("Realizado", "conta"): ["conta", "account", "conta_contabil", "account_name"],
    ("Realizado", "realizado_acumulado"): ["realizado_acumulado", "ledger_actual_to_date", "ledger_actual",
                                          "actual_to_date", "saldo", "balance", "realizado_contabil", "realizado"],
    ("Historico", "conta"): ["conta", "account", "conta_contabil"],
    ("Historico", "competencia"): ["competencia", "period", "periodo", "mes", "month", "reference_month"],
    ("Historico", "orcado"): ["orcado", "budget", "orcado_no_mes", "budget_amount", "meta"],
    ("Historico", "realizado"): ["realizado", "actual", "realizado_no_mes", "actual_amount"],
}
INGLES = {"company", "legal", "name", "code", "size", "class", "fiscal", "period", "has", "users", "username", "user",
          "full", "job", "title", "role", "position", "products", "sku", "product", "description", "business",
          "unit", "units", "sold", "quantity", "qty", "price", "variable", "cost", "fixed", "costs", "center",
          "centers", "monthly", "amount", "value", "budget", "lines", "account", "quarter", "quarterly", "to", "date",
          "actual", "actuals", "ytd", "notes", "comments", "entry", "entries", "journal", "posting", "vendor",
          "supplier", "invoice", "number", "created", "by", "approved", "approver", "author", "status", "ledger",
          "history", "transactions", "people", "employees", "items", "sales", "balances", "balance", "department"}
SINAL_ID = {"id", "codigo", "code", "sku", "entry", "lancamento", "numero", "num", "key", "chave", "matricula"}
SINAL_MOEDA = {"valor", "preco", "price", "amount", "custo", "cost", "total", "orcado", "realizado", "budget",
               "actual", "saldo", "balance", "receita", "despesa", "montante", "reais", "brl"}
SINAL_CENTAVOS = {"centavos", "cents", "cent", "em_centavos", "minor"}
IDENTIFICADOR = re.compile(r"^[A-Za-z]{1,6}[-_/]?\d{1,10}$")
COMPAT = {  # tipo canônico -> {tipo inferido: peso}
    "reais": {"moeda_reais": 1.0, "moeda_centavos": 1.0, "decimal": 0.8, "inteiro": 0.6},
    "competencia": {"competencia": 1.0, "data": 1.0},
    "inteiro": {"inteiro": 1.0, "decimal": 0.4, "moeda_reais": 0.3},
    "texto": {"texto": 1.0, "identificador": 1.0, "booleano": 0.3, "competencia": 0.3, "data": 0.3},
    "booleano": {"booleano": 1.0, "texto": 0.4},
}


# ---------------------------------------------------------------- inferência de tipos
def _decimais(x: float) -> int:
    texto = repr(float(x))
    return 0 if float(x).is_integer() else len(texto.split(".")[1]) if "." in texto else 0


def inferir_tipo(nome: str, valores: list) -> tuple[str, str]:
    """(tipo, por quê) a partir do nome do campo e dos valores não vazios."""
    tokens = set(normalizar(nome).split("_"))
    vals = [v for v in valores if v is not None and not (isinstance(v, str) and not v.strip())]
    if not vals:
        return "texto", "sem valores para inferir (assumido texto)"
    moeda = bool(tokens & SINAL_MOEDA)
    centavos = bool(tokens & SINAL_CENTAVOS)
    if all(isinstance(v, bool) for v in vals):
        return "booleano", "valores verdadeiro/falso"
    if all(isinstance(v, (datetime, date)) for v in vals):
        return "data", "células de data"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        inteiros = all(float(v).is_integer() for v in vals)
        if inteiros and tokens & SINAL_ID and not moeda:
            return "identificador", "números inteiros num campo de código"
        if moeda and centavos:
            return "moeda_centavos", "nome indica valor em centavos"
        if moeda and not inteiros and max(_decimais(v) for v in vals) <= 2:
            return "moeda_reais", "nome de valor monetário e até duas casas decimais (reais)"
        if moeda and inteiros:
            return "moeda_reais", "nome de valor monetário, inteiros sem casas decimais (assumido reais; confirme)"
        return ("inteiro", "números inteiros") if inteiros else ("decimal", "números com casas decimais")
    textos = [str(v).strip() for v in vals]
    normal = [normalizar(t) for t in textos]
    if all(n in {"sim", "nao", "s", "n", "true", "false", "yes", "no"} for n in normal):
        return "booleano", "valores sim/não"
    if all(COMPETENCIA.match(t) for t in textos):
        return "competencia", "valores no formato AAAA-MM"
    if all(DATA_ISO.match(t) or DATA_BR.match(t) for t in textos):
        return "data", "datas ISO (AAAA-MM-DD) ou dd/mm/aaaa"
    if all("R$" in t for t in textos):
        return "moeda_reais", "valores com R$"
    try:
        nums = [numero(t) for t in textos]
    except ConversaoInvalida:
        nums = None
    if nums is not None:
        if moeda:
            return ("moeda_centavos", "nome indica centavos") if centavos else \
                ("moeda_reais", "texto numérico num campo de valor (reais)")
        return ("inteiro", "texto numérico inteiro") if all(x.is_integer() for x in nums) else \
            ("decimal", "texto numérico com casas decimais")
    if all(IDENTIFICADOR.match(t) for t in textos) and (len(set(textos)) > 1 or tokens & SINAL_ID):
        return "identificador", "códigos curtos (letras e número, ex.: L-001)"
    return "texto", "texto livre"


def _json_valor(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _campos(registros: list[dict], ordem: list | None = None) -> list[dict]:
    nomes = list(ordem or [])
    for r in registros:
        for k in r:
            if k not in nomes:
                nomes.append(k)
    campos = []
    for nome in nomes:
        valores = [r.get(nome) for r in registros]
        cheios = [v for v in valores if v is not None and not (isinstance(v, str) and not v.strip())]
        tipo, porque = inferir_tipo(nome, cheios)
        distintos = len({json.dumps(_json_valor(v), default=str) for v in cheios})
        campos.append({"nome": nome, "tipo": tipo, "inferencia": porque,
                       "exemplos": redigir([_json_valor(v) for v in _unicos(cheios)[:3]]),
                       "nulos": len(valores) - len(cheios), "total": len(valores), "distintos": distintos,
                       "unico": bool(cheios) and distintos == len(cheios),
                       "_valores": [_json_valor(v) for v in cheios[:MAX_VALORES]]})
    return campos


def _unicos(valores):
    vistos, saida = set(), []
    for v in valores:
        chave = json.dumps(_json_valor(v), default=str)
        if chave not in vistos:
            vistos.add(chave)
            saida.append(v)
    return saida


def _achatar(registro: dict, prefixo="") -> dict:
    saida = {}
    for k, v in registro.items():
        if isinstance(v, dict):
            saida.update(_achatar(v, f"{prefixo}{k}."))
        elif not isinstance(v, list):
            saida[f"{prefixo}{k}"] = v
    return saida


RAIZES_PREFERIDAS = ("data", "items", "itens", "results", "resultado", "registros", "linhas", "rows", "records")


def _registros_de(payload) -> tuple[str, list[dict]]:
    """(raiz, registros) de uma resposta JSON: lista na raiz, lista dentro de um envelope ou objeto único."""
    if isinstance(payload, list):
        return "", [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        listas = [k for k, v in payload.items() if isinstance(v, list) and v and all(isinstance(x, dict) for x in v)]
        listas += [k for k, v in payload.items() if isinstance(v, list) and not v and k in RAIZES_PREFERIDAS]
        if listas:
            raiz = next((k for k in RAIZES_PREFERIDAS if k in listas), listas[0])
            return raiz, payload[raiz]
        return "", [payload]
    return "", []


# ---------------------------------------------------------------- adaptadores
def de_amostras_json(amostras: dict) -> dict:
    """`amostras`: {nome do recurso: resposta JSON}."""
    recursos = []
    for nome, payload in amostras.items():
        raiz, registros = _registros_de(payload)
        registros = [_achatar(r) for r in registros]
        recursos.append({"nome": nome, "raiz": raiz, "linhas": len(registros), "campos": _campos(registros),
                         "_registros": registros})
    return {"origem": "amostras", "recursos": recursos, "avisos": []}


def _resolver(spec: dict, esquema: dict, profundidade=0) -> dict:
    if profundidade > 10 or not isinstance(esquema, dict):
        return {}
    if "$ref" in esquema:
        alvo = spec
        for parte in esquema["$ref"].lstrip("#/").split("/"):
            alvo = alvo.get(parte, {}) if isinstance(alvo, dict) else {}
        return _resolver(spec, alvo, profundidade + 1)
    return esquema


def _tipo_openapi(nome: str, prop: dict) -> tuple[str, str]:
    t, fmt = prop.get("type"), prop.get("format")
    exemplo = prop.get("example")
    tokens = set(normalizar(nome).split("_"))
    descricao = normalizar(prop.get("description") or "")
    if fmt in ("date", "date-time"):
        return "data", f"OpenAPI: string format {fmt}"
    if t == "boolean":
        return "booleano", "OpenAPI: boolean"
    if t == "string" and prop.get("pattern") in (r"^\d{4}-\d{2}$", "^[0-9]{4}-[0-9]{2}$"):
        return "competencia", "OpenAPI: string com padrão AAAA-MM"
    if t in ("number", "integer"):
        moeda = bool(tokens & SINAL_MOEDA) or any(s in descricao for s in ("brl", "reais", "currency", "amount"))
        if moeda and (tokens & SINAL_CENTAVOS or "cents" in descricao or "centavos" in descricao):
            return "moeda_centavos", "OpenAPI: valor em centavos (nome ou descrição)"
        if moeda and t == "number":
            return "moeda_reais", f"OpenAPI: number ({fmt or 'decimal'}) em campo de valor" + \
                (" — descrição cita BRL/reais" if "brl" in descricao or "reais" in descricao else "")
        if t == "integer":
            return ("identificador", "OpenAPI: integer em campo de código") if tokens & SINAL_ID and not moeda \
                else ("inteiro", "OpenAPI: integer")
        return "decimal", "OpenAPI: number"
    if exemplo is not None:
        tipo, porque = inferir_tipo(nome, [exemplo])
        return tipo, f"OpenAPI: string; exemplo {porque}"
    return "texto", "OpenAPI: string"


PARAM_COMPETENCIA = {"period", "periodo", "competencia", "mes", "month", "fiscal_period", "reference_month"}
PARAM_PAGINA = {"page", "pagina", "page_number"}
PARAM_TAMANHO = {"page_size", "per_page", "limit", "tamanho", "size", "pagesize"}
CAMPO_MAIS = ("has_more", "hasMore", "has_next", "more", "tem_mais")
ACOES_SINONIMOS = {"estornar": {"reverse", "reversal", "estornar", "estorno", "void", "cancel"},
                   "reaprovar": {"reapprove", "re_approve", "reaprovar", "approve_again", "reaprovacao"},
                   "reclassificar": {"reclassify", "reclass", "reclassificar", "move_period"}}


def de_openapi(spec: dict, amostras: dict | None = None) -> dict:
    """Recursos de leitura (GET sem parâmetro de caminho) com campos, raiz, competência e paginação;
    e a operação de correção, se o contrato tiver uma. `amostras` ({recurso: resposta}) enriquece."""
    recursos, avisos, escrita = [], [], None
    for caminho, ops in sorted((spec.get("paths") or {}).items()):
        if not isinstance(ops, dict):
            continue
        if "post" in ops and "{" in caminho:
            escrita = escrita or _escrita(spec, caminho, ops["post"])
        get = ops.get("get")
        if not get or "{" in caminho:
            continue
        esquema = _resolver(spec, (((get.get("responses") or {}).get("200") or {}).get("content") or {})
                            .get("application/json", {}).get("schema") or {})
        raiz, item = "", esquema
        if esquema.get("type") == "array":
            item = _resolver(spec, esquema.get("items") or {})
        else:
            for k, p in (esquema.get("properties") or {}).items():
                p = _resolver(spec, p)
                if p.get("type") == "array" and _resolver(spec, p.get("items") or {}).get("type") == "object":
                    raiz, item = k, _resolver(spec, p["items"])
                    break
        props = {k: _resolver(spec, v) for k, v in (item.get("properties") or {}).items()}
        if not props:
            avisos.append(f"{caminho}: resposta sem esquema de objeto; ignorado")
            continue
        nome = [p for p in caminho.strip("/").split("/") if p and not re.fullmatch(r"v\d+|api", p)][-1]
        params = {p.get("name"): p for p in (_resolver(spec, x) for x in get.get("parameters") or [])}
        comp = next((p for p in params if normalizar(p) in PARAM_COMPETENCIA), None)
        descritor = {"caminho": caminho + (f"?{comp}={{competencia}}" if comp else ""), "raiz": raiz}
        pagina = next((p for p in params if normalizar(p) in PARAM_PAGINA), None)
        tamanho = next((p for p in params if normalizar(p) in PARAM_TAMANHO), None)
        mais = next((m for m in CAMPO_MAIS if m in (esquema.get("properties") or {})), None)
        if pagina and mais:
            descritor["paginacao"] = {"parametro": pagina, "mais": mais, "tamanho": 50,
                                      **({"tamanho_parametro": tamanho} if tamanho else {})}
        registros = []
        if amostras and nome in amostras:
            _, registros = _registros_de(amostras[nome])
            registros = [_achatar(r) for r in registros]
        campos = _campos(registros, list(props)) if registros else []
        for c in campos:
            if c["nome"] in props:
                tipo, porque = _tipo_openapi(c["nome"], props[c["nome"]])
                if tipo != c["tipo"] and tipo != "texto":
                    c["tipo"], c["inferencia"] = tipo, porque + f" (amostra: {c['inferencia']})"
        if not registros:
            for k, p in props.items():
                tipo, porque = _tipo_openapi(k, p)
                exemplos = [p["example"]] if "example" in p else []
                campos.append({"nome": k, "tipo": tipo, "inferencia": porque, "exemplos": redigir(exemplos),
                               "nulos": 0, "total": 0, "distintos": 0, "unico": False, "_valores": exemplos})
        recursos.append({"nome": nome, "raiz": raiz, "linhas": len(registros) if registros else None,
                         "campos": campos, "descritor": descritor, "resumo": get.get("summary"),
                         "_registros": registros})
    return {"origem": "openapi", "recursos": recursos, "avisos": avisos, "escrita": escrita,
            "titulo": (spec.get("info") or {}).get("title")}


def _escrita(spec, caminho, post) -> dict | None:
    """Operação de correção: POST com o id no caminho e uma `action` cujo enum casa com as correções."""
    corpo = _resolver(spec, (((post.get("requestBody") or {}).get("content") or {}).get("application/json") or {})
                      .get("schema") or {})
    for campo, p in (corpo.get("properties") or {}).items():
        valores = _resolver(spec, p).get("enum") or []
        acoes = {}
        for acao, sinonimos in ACOES_SINONIMOS.items():
            v = next((v for v in valores if normalizar(v) in sinonimos), None)
            if v:
                acoes[acao] = v
        if acoes:
            parametro = re.search(r"\{([^}]+)\}", caminho).group(1)
            corpo_modelo = {campo: "{acao}"}
            for outro in (corpo.get("properties") or {}):
                if normalizar(outro) in PARAM_COMPETENCIA:
                    corpo_modelo[outro] = "{competencia}"
            return {"caminho": caminho.replace("{" + parametro + "}", "{lancamento}"), "corpo": corpo_modelo,
                    "acoes": acoes, "motivo": f"POST {caminho} com {campo} em {', '.join(map(str, valores))}"}
    return None


def de_mcp_tools(lista: list[dict], amostras: dict | None = None) -> dict:
    """Tools de um servidor MCP. Uma tool com parâmetro enumerado cujos valores são nomes de abas canônicas
    (ex.: `ler_aba(aba=Lancamentos)`) vira um recurso por valor; `amostras` ({recurso: resultado}) dá os campos."""
    from fin_mas.conectores.planilhas import chave_valor, eh_chave_valor
    recursos, ferramentas = [], []
    abas = {normalizar(s): aba for aba, sins in SINONIMOS_ABA.items() for s in sins} | \
        {normalizar(a): a for a in CANONICO}
    for t in lista:
        props = (t.get("inputSchema") or {}).get("properties") or {}
        obrig = list((t.get("inputSchema") or {}).get("required") or [])
        ferramentas.append({"nome": t["name"], "descricao": t.get("description"), "parametros": {
            k: {"tipo": v.get("type"), "enum": v.get("enum"), "obrigatorio": k in obrig} for k, v in props.items()}})
        for param, p in props.items():
            casados = [v for v in (p.get("enum") or []) if normalizar(v) in abas]
            for valor in casados:
                nome = f"{t['name']}:{valor}"
                pendentes = [k for k in obrig if k != param]
                registros, raiz, formato = [], "", "tabela"
                if amostras and nome in amostras:
                    raiz, registros = _registros_de(amostras[nome])
                    registros = [_achatar(r) for r in registros]
                    if registros and eh_chave_valor(list(registros[0])):
                        registros, formato = chave_valor(registros), "chave_valor"
                recursos.append({"nome": nome, "raiz": raiz, "linhas": len(registros) if registros else None,
                                 "campos": _campos(registros) if registros else [],
                                 "descritor": {"tool": t["name"], "argumentos": {param: valor},
                                               "raiz": raiz, "pendentes": pendentes, "formato": formato},
                                 "_registros": registros})
    return {"origem": "mcp", "recursos": recursos, "ferramentas": ferramentas, "avisos": []}


def de_planilha(arquivo) -> dict:
    """Qualquer .xlsx: uma aba = um recurso; cabeçalho detectado; linha de total separada; aba de pares
    campo/valor (ex.: a aba Empresa do modelo) vira um registro único."""
    from fin_mas.conectores.planilhas import ler_tabelas
    recursos, avisos = [], []
    for aba, t in ler_tabelas(arquivo).items():
        if not t["registros"]:
            avisos.append(f"aba {aba}: vazia ou sem tabela; ignorada")
            continue
        registros = t["registros"]
        recursos.append({"nome": aba, "raiz": "", "linhas": len(registros), "campos": _campos(registros),
                         "descritor": {"aba": aba, "cabecalho_linha": t["cabecalho_linha"], "formato": t["formato"]},
                         "totais": [{k: _json_valor(v) for k, v in x.items()} for x in t["totais"]],
                         "_registros": registros})
        if t["cabecalho_linha"] and t["cabecalho_linha"] > 1:
            avisos.append(f"aba {aba}: cabeçalho detectado na linha {t['cabecalho_linha']} (linhas acima ignoradas)")
        if t["totais"]:
            avisos.append(f"aba {aba}: {len(t['totais'])} linha(s) de total separada(s) dos registros")
    return {"origem": "planilha", "recursos": recursos, "avisos": avisos}


# ---------------------------------------------------------------- sugestão de mapeamento
def _sinonimos(aba, chave) -> list[str]:
    titulo = next((c[1] for c in CANONICO[aba] if c[0] == chave), chave)
    return list(dict.fromkeys([normalizar(s) for s in SINONIMOS.get((aba, chave), [])] + [chave, normalizar(titulo)]))


def _nome_score(nome_fonte: str, sinonimos: list[str], chave: str = "") -> tuple[float, str]:
    n = normalizar(nome_fonte)
    tokens = set(n.split("_"))
    idioma = lambda s: " (en)" if set(s.split("_")) <= INGLES else ""  # noqa: E731
    if n in sinonimos:
        if n == chave:
            return 1.0, f"nome '{nome_fonte}' igual ao campo canônico"
        return 1.0, f"nome '{nome_fonte}' é sinônimo de '{chave}'{idioma(n)}"
    for s in sinonimos:
        partes = set(s.split("_"))
        if len(partes) > 1 and partes <= tokens:
            return 0.8, f"nome '{nome_fonte}' contém '{s}'{idioma(s)}"
    for s in sinonimos:
        if "_" not in s and len(s) >= 3 and s in tokens:
            return 0.6, f"nome '{nome_fonte}' contém a palavra '{s}'{idioma(s)}"
    return 0.0, ""


def _conversao(tipo_canonico: str, chave: str, tipo_fonte: str) -> str:
    if tipo_canonico == "reais":
        return "centavos" if tipo_fonte == "moeda_centavos" else "reais"
    if tipo_canonico == "competencia":
        return "data_competencia" if tipo_fonte == "data" else "competencia"
    if chave == "situacao":
        return "situacao"
    return conversao_padrao(tipo_canonico)


def _conteudo(aba, chave, campo_fonte, referencias) -> tuple[float, str]:
    valores = campo_fonte.get("_valores") or []
    if not valores:
        return 0.0, ""
    if aba == "Lancamentos" and chave in ("criador", "aprovador") and referencias.get("usuarios"):
        dentro = sum(1 for v in valores if str(v) in referencias["usuarios"])
        if dentro:
            return dentro / len(valores), f"{dentro} de {len(valores)} valores são usuários de Pessoas"
    if chave == "conta" and aba != "Orcamento" and referencias.get("contas"):
        dentro = sum(1 for v in valores if str(v) in referencias["contas"])
        if dentro:
            return dentro / len(valores), f"{dentro} de {len(valores)} valores são contas do Orcamento"
    if chave == "id" and campo_fonte.get("unico"):
        return 1.0, "valores únicos"
    if chave == "situacao":
        try:
            [converter(v, "situacao") for v in valores]
            return 1.0, "valores reconhecidos como ativo/estornado"
        except ConversaoInvalida:
            return 0.0, "valores fora de ativo/estornado"
    if chave == "competencia":
        return 1.0, "valores de data ou competência"
    return 0.0, ""


def _candidatos(aba, recurso, referencias) -> list[tuple]:
    saida = []
    for ordem_c, (chave, titulo, tipo, obrigatorio) in enumerate(CANONICO[aba]):
        sins = _sinonimos(aba, chave)
        for ordem_f, cf in enumerate(recurso["campos"]):
            peso_tipo = COMPAT[tipo].get(cf["tipo"], 0.0)
            if peso_tipo == 0:
                continue
            nome, motivo_nome = _nome_score(cf["nome"], sins, chave)
            conteudo, motivo_conteudo = _conteudo(aba, chave, cf, referencias)
            if nome == 0 and conteudo < 0.8:
                continue
            confianca = round(0.6 * nome + 0.3 * peso_tipo + 0.1 * conteudo, 2)
            motivos = [m for m in (motivo_nome, f"tipo {cf['tipo']} compatível com {tipo}"
                                   + ("" if peso_tipo == 1 else f" (peso {peso_tipo:g})"), motivo_conteudo) if m]
            saida.append((confianca, -ordem_c, -ordem_f, chave, cf, "; ".join(motivos)))
    return sorted(saida, key=lambda x: (x[0], x[1], x[2]), reverse=True)


def _atribuir(aba, recurso, referencias) -> dict:
    campos, usados = {}, set()
    for confianca, _, _, chave, cf, motivo in _candidatos(aba, recurso, referencias):
        if chave in campos or cf["nome"] in usados:
            continue
        tipo = next(c[2] for c in CANONICO[aba] if c[0] == chave)
        campos[chave] = {"origem": cf["nome"], "conversao": _conversao(tipo, chave, cf["tipo"]),
                         "confianca": confianca, "motivo": motivo}
        usados.add(cf["nome"])
    return campos


def _referencias(estrutura) -> dict:
    """Valores de Pessoas.usuario e Orcamento.conta, de qualquer recurso que pareça essas abas (conteúdo)."""
    ref = {"usuarios": set(), "contas": set()}
    for r in estrutura["recursos"]:
        for cf in r["campos"]:
            n = normalizar(cf["nome"])
            if n in _sinonimos("Pessoas", "usuario") and cf.get("unico"):
                ref["usuarios"] |= {str(v) for v in cf.get("_valores") or []}
            if n in _sinonimos("Orcamento", "conta") and cf.get("unico"):
                ref["contas"] |= {str(v) for v in cf.get("_valores") or []}
    return ref


def sugerir_mapeamento(estrutura: dict, canonico: dict = CANONICO) -> dict:
    """Sugestões por aba e campo canônicos, com confiança e motivo; e o mapeamento pronto para confirmar."""
    referencias = _referencias(estrutura)
    pares = []
    for aba in canonico:
        sins_aba = [normalizar(s) for s in SINONIMOS_ABA.get(aba, [])] + [normalizar(aba)]
        obrig = [c[0] for c in canonico[aba] if c[3]] or [c[0] for c in canonico[aba]]
        for ordem, r in enumerate(estrutura["recursos"]):
            nome_r = normalizar(r["nome"].split(":")[-1])
            tokens = set(nome_r.split("_"))
            if nome_r in sins_aba:
                pn, mn = 1.0, f"recurso '{r['nome']}' corresponde à aba {aba}"
            elif any(set(s.split("_")) <= tokens for s in sins_aba if s):
                pn, mn = 0.8, f"nome do recurso '{r['nome']}' contém um sinônimo de {aba}"
            else:
                pn, mn = 0.0, ""
            if aba == "Empresa" and (r.get("linhas") or 0) > 1:
                continue  # Empresa é um registro único
            campos = _atribuir(aba, r, referencias)
            fortes = [k for k in obrig if k in campos and campos[k]["confianca"] >= LIMIAR_SUGESTAO]
            cobertura = len(fortes) / len(obrig)
            score = round(0.4 * pn + 0.6 * cobertura, 2)
            if cobertura == 0 or score < LIMIAR_RECURSO:
                continue
            motivo = "; ".join(m for m in (mn, f"{len(fortes)} de {len(obrig)} campos "
                                               f"{'obrigatórios ' if any(c[3] for c in canonico[aba]) else ''}"
                                               "reconhecidos") if m)
            pares.append((score, pn, -ordem, aba, r, campos, motivo))
    pares.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    abas, usados = {}, set()
    for score, _, _, aba, r, campos, motivo in pares:
        if aba in abas or r["nome"] in usados:
            continue
        abas[aba] = {"recurso": r["nome"], "confianca": score, "motivo": motivo, "campos": campos}
        usados.add(r["nome"])
    sugestoes = []
    for aba, campos in canonico.items():
        s = abas.get(aba)
        for chave, titulo, tipo, obrigatorio in campos:
            c = (s or {}).get("campos", {}).get(chave)
            sugestoes.append({"aba": aba, "campo": chave, "titulo": titulo, "tipo": tipo, "obrigatorio": obrigatorio,
                              "recurso": s["recurso"] if s and c else None, "origem": c["origem"] if c else None,
                              "conversao": c["conversao"] if c else conversao_padrao(tipo),
                              "confianca": c["confianca"] if c else 0.0,
                              "motivo": c["motivo"] if c else ("aba sem recurso correspondente" if not s
                                                               else "nenhuma coluna compatível"),
                              "fonte_sugestao": "regras" if c else None,
                              "revisar": bool(c) and c["confianca"] < 0.7})
    nao_mapeados = {r["nome"]: [cf["nome"] for cf in r["campos"]
                                if not any(x["recurso"] == r["nome"] and x["origem"] == cf["nome"] for x in sugestoes)]
                    for r in estrutura["recursos"]}
    return {"abas": {a: {k: v for k, v in s.items() if k != "campos"} for a, s in abas.items()},
            "sugestoes": sugestoes, "nao_mapeados": {k: v for k, v in nao_mapeados.items() if v},
            "mapeamento": mapeamento_de(sugestoes), "escrita": estrutura.get("escrita")}


def mapeamento_de(sugestoes: list[dict], minimo: float = LIMIAR_SUGESTAO) -> dict:
    """Mapeamento no formato do conector a partir das sugestões (ou das linhas ajustadas pela pessoa)."""
    abas, empresa = {}, {}
    for s in sugestoes:
        if not s.get("origem") and "valor" not in s:
            continue
        if s.get("confianca", 1.0) < minimo and s.get("fonte_sugestao") != "pessoa":
            continue
        alvo = {"conversao": s.get("conversao") or conversao_padrao(s["tipo"])}
        if "valor" in s and not s.get("origem"):
            alvo["valor"] = s["valor"]
        else:
            alvo["origem"] = s["origem"]
        if s["aba"] == "Empresa":
            empresa[s["campo"]] = {**alvo, **({"recurso": s["recurso"]} if s.get("recurso") else {})}
        else:
            abas.setdefault(s["aba"], {"recurso": s["recurso"], "campos": {}})["campos"][s["campo"]] = alvo
    return {"abas": abas, "empresa": empresa}


# ---------------------------------------------------------------- qualidade e prévia
def _converter_recurso(estrutura, mapeamento, aba) -> tuple[list[dict], list[str]]:
    spec = mapeamento["abas"].get(aba)
    if not spec:
        return [], []
    recurso = next((r for r in estrutura["recursos"] if r["nome"] == spec["recurso"]), None)
    if recurso is None:
        return [], [f"{aba}: recurso {spec['recurso']} não está na estrutura"]
    linhas, erros = [], []
    for n, bruto in enumerate(recurso.get("_registros") or [], start=1):
        r = {}
        for chave, origem in spec["campos"].items():
            valor = origem.get("valor") if "valor" in origem else bruto.get(origem["origem"])
            try:
                r[chave] = converter(valor, origem.get("conversao") or "texto")
            except ConversaoInvalida as e:
                erros.append(f"{aba} registro {n} ({origem.get('origem')}): {e}")
                r[chave] = None
        linhas.append(r)
    return linhas, erros


def qualidade(estrutura: dict, mapeamento: dict, competencia: str | None = None) -> dict:
    """Relatório de qualidade sobre os registros de amostra, já convertidos pelo mapeamento."""
    problemas = []

    def p(tipo, gravidade, aba, mensagem, quantos=1):
        problemas.append({"tipo": tipo, "gravidade": gravidade, "aba": aba, "mensagem": mensagem, "quantos": quantos})

    for erro in validar_mapeamento(mapeamento, {r["nome"]: {c["nome"] for c in r["campos"]}
                                                for r in estrutura["recursos"]}):
        p("faltante", "erro", erro.split(":")[0].split(".")[0], erro)
    convertidos = {}
    for aba in mapeamento.get("abas") or {}:
        if aba not in CANONICO:
            continue
        linhas, erros = _converter_recurso(estrutura, mapeamento, aba)
        convertidos[aba] = linhas
        for e in erros[:20]:
            p("conversao", "erro", aba, e)
        for chave, _, _, obrigatorio in CANONICO[aba]:
            vazios = sum(1 for r in linhas if chave in r and r[chave] is None)
            if vazios and obrigatorio:
                p("faltante", "erro", aba, f"{aba}.{chave}: {vazios} registro(s) sem valor", vazios)
    lanc = convertidos.get("Lancamentos") or []
    ids = [r.get("id") for r in lanc if r.get("id")]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        p("duplicado", "erro", "Lancamentos", f"códigos repetidos: {', '.join(map(str, repetidos[:10]))}", len(repetidos))
    chaves = [(r.get("fornecedor"), r.get("documento"), r.get("valor")) for r in lanc]
    duplas = sorted({c for c in chaves if chaves.count(c) > 1 and all(x is not None for x in c)}, key=str)
    if duplas:
        p("duplicado", "aviso", "Lancamentos", f"{len(duplas)} combinação(ões) de fornecedor, documento e valor "
                                               "repetidas: o AG-CIN avalia a duplicidade", len(duplas))
    if competencia:
        fora = [r.get("id") for r in lanc if r.get("competencia") and r["competencia"] != competencia]
        if fora:
            p("fora_da_competencia", "aviso", "Lancamentos", f"{len(fora)} lançamento(s) de outra competência "
                                                             f"(não {competencia}): {', '.join(map(str, fora[:10]))}",
              len(fora))
    for aba, campos in (("Lancamentos", ("valor",)), ("Produtos", ("qtd", "preco", "custo_variavel_unit")),
                        ("CustosFixos", ("valor",)), ("Orcamento", ("orcado_trimestre", "orcado_acumulado"))):
        for chave in campos:
            negativos = [r for r in convertidos.get(aba) or [] if isinstance(r.get(chave), int) and r[chave] < 0]
            if negativos:
                p("negativo", "aviso", aba, f"{aba}.{chave}: {len(negativos)} valor(es) negativo(s) inesperado(s)",
                  len(negativos))
    for r in convertidos.get("Orcamento") or []:
        if isinstance(r.get("orcado_acumulado"), int) and isinstance(r.get("orcado_trimestre"), int) \
                and r["orcado_acumulado"] > r["orcado_trimestre"]:
            p("total", "aviso", "Orcamento", f"{r.get('conta')}: orçado acumulado maior que o do trimestre")
    _totais(estrutura, mapeamento, p)
    return {"ok": not any(x["gravidade"] == "erro" for x in problemas), "problemas": problemas,
            "registros": {aba: len(v) for aba, v in convertidos.items()}}


def _totais(estrutura, mapeamento, p) -> None:
    """Linha de total da planilha confere com a soma dos registros (por coluna de valor mapeada)."""
    for aba, spec in (mapeamento.get("abas") or {}).items():
        recurso = next((r for r in estrutura["recursos"] if r["nome"] == spec.get("recurso")), None)
        if not recurso or not recurso.get("totais"):
            continue
        for chave, origem in spec["campos"].items():
            if origem.get("conversao") not in ("reais", "centavos") or not origem.get("origem"):
                continue
            try:
                soma = sum(converter(r.get(origem["origem"]), origem["conversao"]) or 0
                           for r in recurso.get("_registros") or [])
                total = converter(recurso["totais"][-1].get(origem["origem"]), origem["conversao"])
            except ConversaoInvalida:
                continue
            if total is None:
                continue
            if abs(total - soma) > 1:
                p("total", "erro", aba, f"{aba}.{chave}: a linha de total ({total / 100:.2f}) não fecha com a soma "
                                        f"dos registros ({soma / 100:.2f})")
            else:
                p("total", "ok", aba, f"{aba}.{chave}: a linha de total fecha com a soma dos registros")


def previa(estrutura: dict, mapeamento: dict, linhas: int = 5) -> dict:
    """Primeiros registros de cada aba já no modelo canônico, redigidos (CPF, e-mail, segredos...)."""
    saida = {}
    for aba in (mapeamento.get("abas") or {}):
        if aba in CANONICO:
            convertidos, _ = _converter_recurso(estrutura, mapeamento, aba)
            saida[aba] = redigir(convertidos[:linhas])
    return saida


def publico(estrutura: dict) -> dict:
    """Estrutura sem os valores internos (`_valores`, `_registros`): é o que a API devolve."""
    def limpar(x):
        if isinstance(x, dict):
            return {k: limpar(v) for k, v in x.items() if not k.startswith("_")}
        if isinstance(x, list):
            return [limpar(v) for v in x]
        return x
    return redigir(limpar(estrutura))


def entender(estrutura: dict, competencia: str | None = None) -> dict:
    sugestao = sugerir_mapeamento(estrutura)
    return {"estrutura": publico(estrutura), "sugestao": sugestao,
            "qualidade": qualidade(estrutura, sugestao["mapeamento"], competencia),
            "previa": previa(estrutura, sugestao["mapeamento"])}


# ---------------------------------------------------------------- LLM opcional (só sugere)
SISTEMA_LLM = ("Você sugere a correspondência entre colunas de uma fonte de dados e o modelo canônico de uma "
               "controladoria. Responda só JSON: {\"sugestoes\": [{\"aba\", \"campo\", \"recurso\", \"origem\", "
               "\"explicacao\"}]}. Não invente colunas: use só as listadas.")


def _mock_mapeador(prompt: str) -> str:
    """Modelo de teste: casa campos canônicos pendentes com colunas pelo começo do nome; sempre devolve também
    uma sugestão inválida (campo inexistente), para mostrar a validação."""
    ctx = json.loads(prompt.split("CONTEXTO:\n", 1)[1])
    sugestoes = []
    for pend in ctx["pendentes"]:
        for r in ctx["recursos"]:
            for c in r["campos"]:
                if normalizar(c["nome"])[:3] == pend["campo"][:3]:
                    sugestoes.append({"aba": pend["aba"], "campo": pend["campo"], "recurso": r["nome"],
                                      "origem": c["nome"], "explicacao": "o começo do nome coincide"})
                    break
    sugestoes.append({"aba": "Lancamentos", "campo": "centro_de_lucro", "recurso": "x", "origem": "y",
                      "explicacao": "campo inventado"})
    return json.dumps({"sugestoes": sugestoes})


def sugerir_com_llm(estrutura: dict, sugestao: dict, config: dict) -> dict:
    """Pede ao LLM (opcional) sugestões para os campos sem sugestão determinística e as valida.

    `config`: {"provedor", "modelo", "base_url"?, "consentimento_externo"?}. Envia só nomes e tipos
    (sem valores). Provedor externo sem consentimento: nada é enviado."""
    from fin_mas.services import provedores
    provedor_id, modelo = config.get("provedor") or "mock", config.get("modelo") or "mock-mapeador"
    pendentes = [{"aba": s["aba"], "campo": s["campo"], "tipo": s["tipo"]} for s in sugestao["sugestoes"]
                 if not s["origem"] and s["aba"] in (sugestao["abas"] or {})]
    contexto = {"pendentes": pendentes, "recursos": [
        {"nome": r["nome"], "campos": [{"nome": c["nome"], "tipo": c["tipo"]} for c in r["campos"]]}
        for r in estrutura["recursos"]]}
    prompt = "CONTEXTO:\n" + json.dumps(contexto, ensure_ascii=False)
    resultado = {"provedor": provedor_id, "modelo": modelo, "enviado": prompt, "aceitas": [], "rejeitadas": [],
                 "erro": None}
    if not pendentes:
        resultado["erro"] = "nenhum campo pendente: nada a pedir ao LLM"
        return resultado
    try:
        if provedor_id == "mock" and modelo == "mock-mapeador":
            texto = _mock_mapeador(prompt)
        else:
            prov = provedores.REGISTRO.get(provedor_id)
            if prov is None:
                raise provedores.ErroProvedor(f"provedor desconhecido: {provedor_id}")
            if prov.externo(config.get("base_url")) and not config.get("consentimento_externo"):
                resultado["enviado"] = None
                resultado["erro"] = "provedor externo sem consentimento: nada foi enviado"
                return resultado
            texto = prov.completar(modelo, provedores.PedidoLLM(SISTEMA_LLM, prompt, 2000),
                                   base_url=config.get("base_url")).texto
        propostas = json.loads(texto)["sugestoes"]
    except (provedores.ErroProvedor, ValueError, KeyError, TypeError) as e:
        resultado["erro"] = f"LLM indisponível ou fora do formato: {e}"
        return resultado
    recursos = {r["nome"]: {c["nome"]: c for c in r["campos"]} for r in estrutura["recursos"]}
    ja = {(s["aba"], s["campo"]) for s in sugestao["sugestoes"] if s["origem"]}
    for prop in propostas if isinstance(propostas, list) else []:
        motivo = _validar_llm(prop, recursos, ja, sugestao)
        item = {k: prop.get(k) for k in ("aba", "campo", "recurso", "origem")}
        item["explicacao"] = redigir(str(prop.get("explicacao") or ""))[:200]
        if motivo:
            resultado["rejeitadas"].append({**item, "motivo": motivo})
            continue
        tipo = next(c[2] for c in CANONICO[prop["aba"]] if c[0] == prop["campo"])
        cf = recursos[prop["recurso"]][prop["origem"]]
        resultado["aceitas"].append({**item, "conversao": _conversao(tipo, prop["campo"], cf["tipo"]),
                                     "confianca": 0.4, "fonte_sugestao": "llm",
                                     "motivo": f"sugerido pelo LLM ({modelo}): {item['explicacao']}; validado: "
                                               f"coluna existe e tipo {cf['tipo']} compatível com {tipo}"})
        ja.add((prop["aba"], prop["campo"]))
    return resultado


def _validar_llm(prop, recursos, ja, sugestao) -> str | None:
    if not isinstance(prop, dict):
        return "sugestão fora do formato"
    aba, chave, recurso, origem = (prop.get(k) for k in ("aba", "campo", "recurso", "origem"))
    if aba not in CANONICO or not any(c[0] == chave for c in CANONICO[aba]):
        return f"campo canônico inexistente: {aba}.{chave}"
    if recurso not in recursos or origem not in recursos[recurso]:
        return f"coluna inexistente na fonte: {recurso}.{origem}"
    if (aba, chave) in ja:
        return "o campo já tem sugestão determinística (que prevalece)"
    if (sugestao["abas"].get(aba) or {}).get("recurso") not in (None, recurso):
        return f"a aba {aba} vem de outro recurso ({sugestao['abas'][aba]['recurso']})"
    tipo = next(c[2] for c in CANONICO[aba] if c[0] == chave)
    if COMPAT[tipo].get(recursos[recurso][origem]["tipo"], 0) == 0:
        return f"tipo {recursos[recurso][origem]['tipo']} incompatível com {tipo}"
    return None


__all__ = ["de_openapi", "de_amostras_json", "de_mcp_tools", "de_planilha", "inferir_tipo", "sugerir_mapeamento",
           "mapeamento_de", "qualidade", "previa", "entender", "publico", "sugerir_com_llm", "ABAS_OBRIGATORIAS"]

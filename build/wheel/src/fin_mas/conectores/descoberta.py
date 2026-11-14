"""Descoberta da estrutura de uma fonte pelo próprio conector, para o entendimento automático (ADR-011).

Liga cada conector ao adaptador certo de `fontes/entendimento.py`:

- REST: lê o contrato OpenAPI (se houver), configura os recursos de leitura e a operação de
  correção que ele descreve, e busca uma página de cada recurso como amostra;
- MCP: `tools/list`, preenche os argumentos pendentes (ex.: o arquivo, a partir de
  `listar_planilhas`) e chama cada tool candidata para ter amostras;
- planilha: lê as abas do arquivo.

Nada aqui decide o mapeamento: só produz a estrutura que `sugerir_mapeamento` usa.
"""
from fin_mas.conectores.base import RespostaInvalida
from fin_mas.fontes import entendimento


def estrutura_rest(conector, competencia: str | None) -> dict:
    spec = conector.contrato()
    if spec is not None:
        inicial = entendimento.de_openapi(spec)
        if not conector.config.get("recursos"):
            conector.config["recursos"] = {r["nome"]: {k: v for k, v in r["descritor"].items()}
                                           for r in inicial["recursos"]}
        if inicial.get("escrita") and not conector.config.get("escrita"):
            conector.config["escrita"] = {k: v for k, v in inicial["escrita"].items() if k != "motivo"}
    if not conector.config.get("recursos"):
        raise RespostaInvalida("sem contrato OpenAPI nem recursos configurados: informe ao menos um caminho")
    amostras = conector.amostras(competencia)
    if spec is not None:
        return entendimento.de_openapi(spec, amostras)
    estrutura = entendimento.de_amostras_json(amostras)
    for r in estrutura["recursos"]:
        r["descritor"] = dict(conector.config["recursos"][r["nome"]], raiz=r["raiz"])
    return estrutura


def estrutura_mcp(conector, contexto: dict | None = None) -> dict:
    """`contexto`: valores para argumentos obrigatórios que a tool não enumera (ex.: {"arquivo": "x.xlsx"})."""
    contexto = dict(contexto or {})
    with conector.cliente() as c:
        tools = c.tools()
        nomes = {t["name"] for t in tools}
        if "arquivo" not in contexto and "listar_planilhas" in nomes:
            validas = [p["arquivo"] for p in c.tool("listar_planilhas").get("planilhas", []) if p.get("valido")]
            todas = [p["arquivo"] for p in c.tool("listar_planilhas").get("planilhas", [])]
            if validas or todas:
                contexto["arquivo"] = (validas or todas)[-1]
        candidatas = entendimento.de_mcp_tools(tools)
        amostras, recursos = {}, {}
        for r in candidatas["recursos"]:
            d = r["descritor"]
            args = {**d["argumentos"], **{k: contexto[k] for k in d["pendentes"] if k in contexto}}
            if "limite" in _parametros(tools, d["tool"]):
                args["limite"] = 1000
            if any(k not in args for k in d["pendentes"]):
                continue
            try:
                amostras[r["nome"]] = c.tool(d["tool"], args)
            except RespostaInvalida:
                continue
            recursos[r["nome"]] = {"tool": d["tool"], "argumentos": args}
    estrutura = entendimento.de_mcp_tools(tools, amostras)
    estrutura["recursos"] = [r for r in estrutura["recursos"] if r["nome"] in recursos]
    conector.config["recursos"] = {}
    for r in estrutura["recursos"]:
        conector.config["recursos"][r["nome"]] = {**recursos[r["nome"]], "raiz": r["descritor"]["raiz"],
                                                  "formato": r["descritor"]["formato"]}
    estrutura["contexto"] = contexto
    return estrutura


def _parametros(tools, nome) -> dict:
    t = next((t for t in tools if t["name"] == nome), {})
    return (t.get("inputSchema") or {}).get("properties") or {}


def estrutura_planilha(conector) -> dict:
    return entendimento.de_planilha(conector.arquivo)


def estrutura_de(conector, competencia: str | None = None, contexto: dict | None = None) -> dict:
    tipo = conector.tipo
    if tipo == "rest":
        return estrutura_rest(conector, competencia)
    if tipo == "mcp":
        return estrutura_mcp(conector, contexto)
    if tipo == "planilha":
        return estrutura_planilha(conector)
    if tipo == "planilhas":
        arquivos = conector.arquivos()
        if not arquivos:
            raise RespostaInvalida("pasta sem planilhas")
        return entendimento.de_planilha(arquivos[-1])
    if tipo == "erp_simulado":
        dados = conector.ler(competencia)
        return entendimento.de_amostras_json({aba: regs for aba, regs in dados.dados.items()})
    raise RespostaInvalida(f"tipo de conector sem descoberta: {tipo}")

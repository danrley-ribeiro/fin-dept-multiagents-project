"""Linha de comando das fontes de dados (ADR-011): entender, testar e o ERP de demonstração.

  python -m fin_mas fontes entender planilha.xlsx [--json]
  python -m fin_mas fontes entender contrato.json | amostra.json [--json]
  python -m fin_mas fontes entender http://127.0.0.1:8790 --token-env ERP_TOKEN [--competencia 2026-09]
  python -m fin_mas fontes entender --mcp-pasta dados/planilhas
  python -m fin_mas fontes testar http://127.0.0.1:8790 --token-env ERP_TOKEN | planilha.xlsx | pasta/
  python -m fin_mas erp-demo --porta 8790 [--seed 42] [--porte media] [--plantar alcada] [--token T]

O entendimento é determinístico (sem IA generativa). `--llm mock:mock-mapeador` liga a sugestão
opcional por LLM, que passa pela mesma validação. A credencial vem de uma variável de ambiente
(`--token-env`), nunca da linha de comando, e não aparece na saída. Rede: só loopback, salvo
`--liberar-host` (o dono da máquina responde pelo que libera).
"""
import json
import os
import sys
from pathlib import Path

from fin_mas.env.portes import PORTES


def configurar(sub) -> None:
    f = sub.add_parser("fontes", help="entender e testar fontes de dados (planilha, OpenAPI, amostra JSON, API, MCP)")
    acoes = f.add_subparsers(dest="acao", required=True)
    for nome, ajuda in (("entender", "estrutura, sugestões de mapeamento com motivo, qualidade e prévia"),
                        ("testar", "diagnóstico de conexão e leitura")):
        p = acoes.add_parser(nome, help=ajuda)
        p.add_argument("alvo", nargs="?", help="arquivo .xlsx ou .json, pasta de planilhas ou URL http(s)")
        p.add_argument("--mcp-pasta", default=None, help="usa o servidor MCP de Excel embutido sobre esta pasta")
        p.add_argument("--token-env", default=None, help="variável de ambiente com o token (Bearer) da API")
        p.add_argument("--openapi", default="/openapi.json", help="caminho do contrato na API (padrão /openapi.json)")
        p.add_argument("--competencia", default=None)
        p.add_argument("--liberar-host", action="append", default=[], help="host externo permitido (padrão: só loopback)")
        p.add_argument("--json", action="store_true")
        if nome == "entender":
            p.add_argument("--llm", default=None, metavar="PROVEDOR:MODELO",
                           help="sugestão opcional por LLM (ex.: mock:mock-mapeador); validada pelas mesmas regras")
    e = sub.add_parser("erp-demo", help="ERP de demonstração em loopback (API JSON, token, escrita para correções)")
    e.add_argument("--porta", type=int, default=8790)
    e.add_argument("--seed", type=int, default=42)
    e.add_argument("--porte", choices=PORTES, default="media")
    e.add_argument("--plantar", default="", help="plantios separados por vírgula (ex.: alcada,sod)")
    e.add_argument("--token", default=None, help="token fixo (padrão: sorteado e impresso)")


def _conector(args):
    from fin_mas.conectores.base import PoliticaRede
    from fin_mas.conectores.mcp_cliente import ConectorMCP, comando_excel
    from fin_mas.conectores.planilhas import ConectorPastaPlanilhas, ConectorPlanilha
    from fin_mas.conectores.rest import ConectorREST
    if args.mcp_pasta:
        return ConectorMCP("mcp-excel", {"comando": comando_excel(args.mcp_pasta), "competencia": args.competencia})
    alvo = args.alvo or ""
    if alvo.startswith(("http://", "https://")):
        segredo = os.environ.get(args.token_env) if args.token_env else None
        return ConectorREST("api", {"url_base": alvo, "openapi": args.openapi, "competencia": args.competencia,
                                    "autenticacao": {"tipo": "bearer" if segredo else "nenhuma"}},
                            segredo=segredo, politica=PoliticaRede(args.liberar_host))
    caminho = Path(alvo)
    if caminho.is_dir():
        return ConectorPastaPlanilhas("pasta", caminho)
    if caminho.suffix.lower() == ".xlsx":
        return ConectorPlanilha("planilha", caminho)
    return None


def _estrutura(args):
    from fin_mas.conectores import descoberta
    from fin_mas.fontes import entendimento
    alvo = Path(args.alvo or "")
    if not args.mcp_pasta and alvo.suffix.lower() == ".json":
        dados = json.loads(alvo.read_text(encoding="utf-8"))
        if isinstance(dados, dict) and ("openapi" in dados or "swagger" in dados):
            return entendimento.de_openapi(dados)
        return entendimento.de_amostras_json(dados if isinstance(dados, dict) and all(
            isinstance(v, (list, dict)) for v in dados.values()) and len(dados) > 1 else {alvo.stem: dados})
    conector = _conector(args)
    if conector is None:
        raise ValueError(f"não sei ler {args.alvo!r}: use .xlsx, .json, uma pasta, uma URL ou --mcp-pasta")
    return descoberta.estrutura_de(conector, args.competencia)


def _imprimir_entendimento(r) -> None:
    est = r["estrutura"]
    print(f"origem: {est['origem']} | recursos: {len(est['recursos'])}")
    for aviso in est.get("avisos", []):
        print(f"  aviso: {aviso}")
    for rec in est["recursos"]:
        print(f"  recurso {rec['nome']} ({rec.get('linhas') if rec.get('linhas') is not None else '?'} registros): "
              + ", ".join(f"{c['nome']}:{c['tipo']}" for c in rec["campos"]))
    print("-- sugestões de mapeamento (confirme antes de usar) --")
    for s in r["sugestao"]["sugestoes"]:
        if s["origem"] or s["obrigatorio"]:
            alvo = f"{s['recurso']}.{s['origem']}" if s["origem"] else "(sem sugestão)"
            print(f"  {s['aba']}.{s['campo']:<22} <- {alvo:<40} {s['conversao']:<16} {s['confianca']:.2f}  {s['motivo']}")
    q = r["qualidade"]
    print(f"-- qualidade: {'ok' if q['ok'] else 'com erros'} --")
    for p in q["problemas"]:
        print(f"  [{p['gravidade']}] {p['tipo']}: {p['mensagem']}")
    if r.get("llm"):
        print(f"-- LLM ({r['llm']['modelo']}): {len(r['llm']['aceitas'])} aceita(s), "
              f"{len(r['llm']['rejeitadas'])} rejeitada(s) pela validação --")
        for x in r["llm"]["rejeitadas"]:
            print(f"  rejeitada: {x['aba']}.{x['campo']} <- {x['recurso']}.{x['origem']}: {x['motivo']}")


def executar(args) -> int:
    from fin_mas.conectores.base import ErroConector
    if args.comando == "erp-demo":
        from fin_mas.conectores.erp_demo import servir
        servir(args.porta, args.seed, args.porte, tuple(p for p in args.plantar.split(",") if p), args.token)
        return 0
    try:
        if args.acao == "testar":
            conector = _conector(args)
            if conector is None:
                print(f"não sei testar {args.alvo!r}", file=sys.stderr)
                return 2
            diag = conector.testar()
            if args.json:
                print(json.dumps(diag, ensure_ascii=False, indent=2))
            else:
                for e in diag["etapas"]:
                    print(f"  [{'ok' if e['ok'] else 'FALHA'}] {e['etapa']}: {e['detalhe']}")
                print("conexão em ordem" if diag["ok"] else "conexão com falha")
            return 0 if diag["ok"] else 1
        from fin_mas.fontes import entendimento
        estrutura = _estrutura(args)
        r = entendimento.entender(estrutura, args.competencia)
        if args.llm:
            provedor, _, modelo = args.llm.partition(":")
            r["llm"] = entendimento.sugerir_com_llm(estrutura, r["sugestao"], {"provedor": provedor, "modelo": modelo})
    except (ErroConector, ValueError, OSError) as e:
        print(f"não foi possível entender a fonte: {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    else:
        _imprimir_entendimento(r)
    return 0

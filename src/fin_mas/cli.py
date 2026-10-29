"""Linha de comando: executa cenários, grava o trace JSONL e reconstrói conversas.

  python -m fin_mas list
  python -m fin_mas run --scenario fechar_mes --seed 42 [--trace trace.jsonl] [--verbose]
  python -m fin_mas replay trace.jsonl SOL-001
  python -m fin_mas comparar [--seeds 10] [--out docs/dsm2/resultados]
  python -m fin_mas export [--out web/public/traces]
  python -m fin_mas relatorio --scenario fechar_mes [--out saidas]
  python -m fin_mas serve [--porta 8765] [--scenario expediente_sma] [--pasta-dados dados/empresa]
  python -m fin_mas run --scenario fechar_mes --porte micro         # regras do porte (models/portes.yaml)
  python -m fin_mas modelos --out modelos                            # planilhas modelo para empresas sem ERP
  python -m fin_mas run --scenario fechar_mes --pasta dados/empresa  # agentes sobre a planilha preenchida
  python -m fin_mas mcp-excel --pasta dados/empresa                  # servidor MCP (stdio) das planilhas
"""
import argparse
import sys

from fin_mas.env.portes import PORTES
from fin_mas.env.scenarios import CENARIOS, run_scenario
from fin_mas.fontes.planilha import ModeloInvalido
from fin_mas.services.audit import AuditLog


def _resumo(execucao) -> list[str]:
    r = execucao.resposta
    linhas = [f"resposta final: {r.performative} para {execucao.sid}"]
    c = r.content
    if r.performative == "inform":
        linhas.append(f"status: {c['status']}")
        if "dre" in c["resultado"]:
            linhas.append(f"EBITDA (centavos): {c['resultado']['dre']['ebitda']}")
        for ressalva in c["ressalvas"]:
            linhas.append(f"ressalva: {ressalva}")
        linhas += ["", c["relatorio"]]
    else:
        linhas.append(f"motivo: {c.get('motivo')} (subtarefa: {c.get('subtarefa')}; publicado: {c.get('publicado')})")
    return linhas


def _run(args) -> int:
    if args.scenario not in CENARIOS:
        print(f"cenário desconhecido: {args.scenario}. Use 'list'.", file=sys.stderr)
        return 2
    try:
        execucao = run_scenario(args.scenario, args.seed, porte=args.porte, pasta=args.pasta)
    except ModeloInvalido as e:
        print("planilha inválida:\n  " + "\n  ".join(e.erros), file=sys.stderr)
        return 2
    sc = execucao.scenario
    ds = execucao.system.dataset
    print(f"cenário: {sc.nome} | seed: {args.seed if args.seed is not None else sc.seed} | {sc.descricao}")
    print(f"empresa: {getattr(ds, 'razao_social', '') or 'SMA S.A.'} | porte: {ds.perfil['titulo']} | "
          f"{'ERP' if ds.perfil['tem_erp'] else 'sem ERP (planilhas)'}"
          f"{' | planilha: ' + str(ds.arquivo) if hasattr(ds, 'arquivo') else ''}")
    print("-- trilha causal --")
    print("\n".join(execucao.audit.trilha(execucao.sid, verbose=args.verbose)))
    print("-- resultado --")
    print("\n".join(_resumo(execucao)))
    if args.trace:
        execucao.audit.write_jsonl(args.trace)
        print(f"trace gravado em {args.trace}")
    print(f"hash do trace: {execucao.hash}")
    return 0


def _replay(args) -> int:
    log = AuditLog.read_jsonl(args.trace)
    if not log.by_conversation(args.conversation_id):
        print(f"conversation_id sem registros: {args.conversation_id}", file=sys.stderr)
        return 2
    print("\n".join(log.trilha(args.conversation_id, verbose=args.verbose)))
    return 0


def _comparar(args) -> int:
    from fin_mas import experimentos
    linhas = experimentos.executar(seeds=range(1, args.seeds + 1))
    resumo = experimentos.resumir(linhas)
    resumo["_global"]["MET-12_reprodutibilidade"] = experimentos.reprodutibilidade()
    experimentos.gravar(linhas, resumo, args.out)
    print(experimentos.tabela_md(resumo))
    print(f"dados brutos, resumo e figura em {args.out}")
    return 0


def _export(args) -> int:
    from fin_mas.exportar import exportar_traces
    nomes = exportar_traces(args.out)
    print(f"{len(nomes)} traces exportados para {args.out}: {', '.join(nomes)}")
    return 0


def _relatorio(args) -> int:
    from fin_mas.exportar import gravar_relatorio
    if args.scenario not in CENARIOS:
        print(f"cenário desconhecido: {args.scenario}. Use 'list'.", file=sys.stderr)
        return 2
    html_path, json_path = gravar_relatorio(args.scenario, args.out, args.seed)
    print(f"relatório: {html_path}")
    print(f"resultado: {json_path}")
    return 0


def _serve(args) -> int:
    from fin_mas.server import servir
    servir(args.scenario, args.seed, args.porta, args.ms_por_tick, args.pasta_dados)
    return 0


def _modelos(args) -> int:
    from fin_mas.fontes.planilha import gerar_modelos
    for caminho in gerar_modelos(args.out):
        print(caminho)
    return 0


def _mcp_excel(args) -> int:
    from fin_mas.mcp.excel_server import ServidorExcel
    ServidorExcel(args.pasta).servir()
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="fin_mas", description="SMA de controladoria da SMA S.A. (fictícia)")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("list", help="lista os cenários")
    run = sub.add_parser("run", help="executa um cenário")
    run.add_argument("--scenario", required=True)
    run.add_argument("--seed", type=int, default=None)
    run.add_argument("--trace", help="grava o trace JSONL neste arquivo")
    run.add_argument("--verbose", action="store_true", help="inclui as entregas de mensagem")
    run.add_argument("--porte", choices=PORTES, default=None, help="porte da empresa (regras de models/portes.yaml)")
    run.add_argument("--pasta", default=None, help="pasta (ou arquivo .xlsx) com a planilha preenchida")
    rep = sub.add_parser("replay", help="reconstrói uma conversa a partir de um trace JSONL")
    rep.add_argument("trace")
    rep.add_argument("conversation_id")
    rep.add_argument("--verbose", action="store_true")
    cmp_ = sub.add_parser("comparar", help="SMA x workflow centralizado sob as mesmas seeds")
    cmp_.add_argument("--seeds", type=int, default=10)
    cmp_.add_argument("--out", default="docs/dsm2/resultados")
    exp = sub.add_parser("export", help="exporta os traces de todos os cenários para o replay do dashboard")
    exp.add_argument("--out", default="web/public/traces")
    rel = sub.add_parser("relatorio", help="grava o relatório final em HTML (com logo) e JSON")
    rel.add_argument("--scenario", required=True)
    rel.add_argument("--seed", type=int, default=None)
    rel.add_argument("--out", default="saidas")
    srv = sub.add_parser("serve", help="executa o SMA ao vivo e serve a API do dashboard")
    srv.add_argument("--porta", type=int, default=8765)
    srv.add_argument("--scenario", default="expediente_sma")
    srv.add_argument("--seed", type=int, default=None)
    srv.add_argument("--ms-por-tick", type=int, default=350)
    srv.add_argument("--pasta-dados", default="dados/empresa", help="onde ficam as planilhas enviadas pelo dashboard")
    mod = sub.add_parser("modelos", help="grava o modelo Excel em branco e um exemplo por porte")
    mod.add_argument("--out", default="modelos")
    mcp = sub.add_parser("mcp-excel", help="servidor MCP (stdio) das planilhas da pasta")
    mcp.add_argument("--pasta", required=True)
    args = parser.parse_args(argv)
    if args.comando == "list":
        for sc in CENARIOS.values():
            print(f"{sc.nome:<20} seed={sc.seed:<5} {sc.descricao}")
        return 0
    comandos = {"run": _run, "replay": _replay, "comparar": _comparar, "export": _export,
                "relatorio": _relatorio, "serve": _serve, "modelos": _modelos, "mcp-excel": _mcp_excel}
    return comandos[args.comando](args)


if __name__ == "__main__":
    raise SystemExit(main())

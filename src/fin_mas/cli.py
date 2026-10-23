"""Linha de comando: executa cenários, grava o trace JSONL e reconstrói conversas.

  python -m fin_mas list
  python -m fin_mas run --scenario fechar_mes --seed 42 [--trace trace.jsonl] [--verbose]
  python -m fin_mas replay trace.jsonl SOL-001
"""
import argparse
import sys

from fin_mas.env.scenarios import CENARIOS, run_scenario
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
    execucao = run_scenario(args.scenario, args.seed)
    sc = execucao.scenario
    print(f"cenário: {sc.nome} | seed: {args.seed if args.seed is not None else sc.seed} | {sc.descricao}")
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


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="fin_mas", description="Protótipo do MAS de controladoria (DSM2)")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("list", help="lista os cenários")
    run = sub.add_parser("run", help="executa um cenário")
    run.add_argument("--scenario", required=True)
    run.add_argument("--seed", type=int, default=None)
    run.add_argument("--trace", help="grava o trace JSONL neste arquivo")
    run.add_argument("--verbose", action="store_true", help="inclui as entregas de mensagem")
    rep = sub.add_parser("replay", help="reconstrói uma conversa a partir de um trace JSONL")
    rep.add_argument("trace")
    rep.add_argument("conversation_id")
    rep.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.comando == "list":
        for sc in CENARIOS.values():
            print(f"{sc.nome:<20} seed={sc.seed:<5} {sc.descricao}")
        return 0
    return _run(args) if args.comando == "run" else _replay(args)


if __name__ == "__main__":
    raise SystemExit(main())

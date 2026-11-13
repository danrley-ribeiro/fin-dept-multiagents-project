"""Linha de comando: executa cenários, grava o trace JSONL e reconstrói conversas.

  python -m fin_mas list
  python -m fin_mas run --scenario fechar_mes --seed 42 [--trace trace.jsonl] [--verbose]
  python -m fin_mas replay trace.jsonl SOL-001
  python -m fin_mas comparar [--seeds 10] [--out docs/dsm3/resultados]
  python -m fin_mas export [--out web/public/traces]
  python -m fin_mas relatorio --scenario fechar_mes [--out saidas]
  python -m fin_mas serve [--porta 8765] [--scenario expediente_sma] [--pasta-dados dados/empresa]
  python -m fin_mas run --scenario fechar_mes --porte micro         # regras do porte (models/portes.yaml)
  python -m fin_mas modelos --out modelos                            # planilhas modelo para empresas sem ERP
  python -m fin_mas run --scenario fechar_mes --pasta dados/empresa  # agentes sobre a planilha preenchida
  python -m fin_mas mcp-excel --pasta dados/empresa                  # servidor MCP (stdio) das planilhas
  python -m fin_mas run --scenario reincidencia_waiver --memoria .fin_mas/memoria.json   # SVC-MEM persistente
  python -m fin_mas run --scenario ataque_decisao_forjada            # ataques ao Approval Gate (DSM3)
  python -m fin_mas verificar trace.jsonl                            # confere a cadeia de hashes do trace
  python -m fin_mas run --scenario fechar_mes --llm mock-narrador    # síntese por LLM (offline), validada
"""
import argparse
import sys

from fin_mas import cli_acesso, cli_fontes, implantacao
from fin_mas.cognicao import NIVEIS
from fin_mas.env.portes import PORTES
from fin_mas.env.scenarios import CENARIOS, run_scenario
from fin_mas.fontes.planilha import ModeloInvalido
from fin_mas.services.audit import AuditLog, TraceAdulterado
from fin_mas.services.modelos import USOS_POR_AGENTE, ConfiguracaoInvalida


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


def _config_llm(args):
    """`--llm` em texto simples liga só a síntese do AG-REL; com `--llm-agentes` vira configuração por agente."""
    if not args.llm:
        return None
    provedor, _, modelo = args.llm.partition(":")
    campos = {"provedor": provedor, "modelo": modelo} if modelo else {"modelo": args.llm}
    if not modelo and not (args.llm_agentes or args.llm_base_url or args.llm_usos or args.llm_consentimento):
        return args.llm
    if args.llm_base_url:
        campos["base_url"] = args.llm_base_url
    if args.llm_consentimento:
        campos["consentimento_externo"] = True
    agentes = [a.strip() for a in (args.llm_agentes or "AG-REL").split(",") if a.strip()]
    usos = tuple(u.strip() for u in args.llm_usos.split(",") if u.strip()) if args.llm_usos else None
    return {a: {**campos, "usos": usos or USOS_POR_AGENTE.get(a, ("sintese",))} for a in agentes}


def _run(args) -> int:
    if args.scenario not in CENARIOS:
        print(f"cenário desconhecido: {args.scenario}. Use 'list'.", file=sys.stderr)
        return 2
    try:
        execucao = run_scenario(args.scenario, args.seed, porte=args.porte, pasta=args.pasta, memoria=args.memoria,
                                llm=_config_llm(args), cognicao=args.cognicao)
    except ModeloInvalido as e:
        print("planilha inválida:\n  " + "\n  ".join(e.erros), file=sys.stderr)
        return 2
    except ConfiguracaoInvalida as e:
        print(f"configuração de LLM inválida: {e}", file=sys.stderr)
        return 2
    sc = execucao.scenario
    ds = execucao.system.dataset
    print(f"cenário: {sc.nome} | seed: {args.seed if args.seed is not None else sc.seed} | {sc.descricao}")
    print(f"empresa: {getattr(ds, 'razao_social', '') or 'SMA'} | porte: {ds.perfil['titulo']} | "
          f"{'ERP' if ds.perfil['tem_erp'] else 'sem ERP (planilhas)'}"
          f"{' | planilha: ' + str(ds.arquivo) if hasattr(ds, 'arquivo') else ''}")
    print("-- trilha causal --")
    print("\n".join(execucao.audit.trilha(execucao.sid, verbose=args.verbose)))
    print("-- resultado --")
    print("\n".join(_resumo(execucao)))
    if args.trace:
        execucao.audit.write_jsonl(args.trace)
        print(f"trace gravado em {args.trace} (âncora: {execucao.audit.hash_cadeia()})")
    print(f"hash do trace: {execucao.hash}")
    return 0


def _replay(args) -> int:
    try:
        log = AuditLog.read_jsonl(args.trace, ancora=args.ancora)
    except FileNotFoundError:
        print(f"arquivo não encontrado: {args.trace}", file=sys.stderr)
        return 2
    except (TraceAdulterado, ValueError) as erro:
        print(f"trace adulterado: {erro}", file=sys.stderr)
        return 3
    if not log.by_conversation(args.conversation_id):
        print(f"conversation_id sem registros: {args.conversation_id}", file=sys.stderr)
        return 2
    if not log.encadeado and not args.sem_verificar:
        print("trace sem cadeia de hashes nem selo: não é possível garantir que não foi alterado. "
              "Use --sem-verificar para ler mesmo assim (trace anterior à DSM3).", file=sys.stderr)
        return 3
    if not log.encadeado:
        print("AVISO: trace NÃO verificado (sem cadeia de hashes)", file=sys.stderr)
    print("\n".join(log.trilha(args.conversation_id, verbose=args.verbose)))
    return 0


def _verificar(args) -> int:
    try:
        log = AuditLog.read_jsonl(args.trace, ancora=args.ancora)
    except FileNotFoundError:
        print(f"arquivo não encontrado: {args.trace}", file=sys.stderr)
        return 2
    except (TraceAdulterado, ValueError) as erro:
        print(f"FALHA NA VERIFICAÇÃO: {erro}", file=sys.stderr)
        return 3
    if not log.encadeado:
        if args.ancora:  # pediram conferência contra uma âncora e o arquivo não tem cadeia: não há o que conferir
            print(f"FALHA NA VERIFICAÇÃO: {args.trace} não tem cadeia de hashes; a âncora não pode ser conferida",
                  file=sys.stderr)
            return 3
        print(f"{args.trace}: {len(log.records)} registros, sem cadeia de hashes (trace anterior à DSM3)")
        return 1
    rejeicoes = sum(1 for r in log.records if r["kind"] == "rejected")
    modo = f"âncora {args.ancora[:16]}… confere" if args.ancora else "selo HMAC íntegro"
    print(f"{args.trace}: {len(log.records)} registros, cadeia de hashes íntegra, {modo}; "
          f"{rejeicoes} rejeição(ões) auditada(s)")
    print(f"âncora (hash final da cadeia): {log.hash_final}")
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
    if args.instalacao:  # pasta preparada pelo `instalar`: porte, cognição, porta e cadastro vêm de lá
        from pathlib import Path

        from fin_mas.implantacao import ler_instalacao
        c = ler_instalacao(args.instalacao)
        base = Path(args.instalacao)
        servir(c["cenario"], args.seed, c["porta"], args.ms_por_tick, str(base / "empresa"), str(base / "acesso"),
               False, c["cognicao"], porte=c["porte"])
        return 0
    servir(args.scenario, args.seed, args.porta, args.ms_por_tick, args.pasta_dados, args.pasta_acesso, args.demo,
           args.cognicao)
    return 0


def _ler_trace(args):
    try:
        return AuditLog.read_jsonl(args.trace, ancora=getattr(args, "ancora", None))
    except FileNotFoundError:
        print(f"arquivo não encontrado: {args.trace}", file=sys.stderr)
    except (TraceAdulterado, ValueError) as erro:
        print(f"trace adulterado: {erro}", file=sys.stderr)
    return None


def _auditoria(args) -> int:
    """Recorte de um trace gravado, com os mesmos filtros do dashboard (REQ-O04)."""
    import json as _json

    from fin_mas.services import consulta
    from fin_mas.services.audit import formatar
    log = _ler_trace(args)
    if log is None:
        return 3
    registros = consulta.filtrar(log.records, agente=args.agente, de_t=args.de_t, ate_t=args.ate_t,
                                 competencia=args.competencia, tarefa=args.tarefa, tipo=args.tipo,
                                 custo_min=args.custo_min, texto=args.q)
    if args.json:
        print(_json.dumps(registros, ensure_ascii=False, default=str))
    else:
        print("\n".join(formatar(r) for r in registros))
        print(f"{len(registros)} de {len(log.records)} registro(s)")
    return 0


def _explicar(args) -> int:
    from fin_mas.services import explicacao
    log = _ler_trace(args)
    if log is None:
        return 3
    try:
        if args.comando == "sequencia":
            print(explicacao.sequencia(log.records, args.conversa), end="")
            return 0
        r = explicacao.explicar(log.records, args.seq)
    except LookupError as erro:
        print(str(erro), file=sys.stderr)
        return 2
    print(f"por que: {r['alvo']['texto']}")
    print(f"agente {r['agente']} | conversa {r['conversa']} | tarefa {r['tarefa']}")
    for item in r["cadeia"]:
        print(f"  [{item['papel']:<22}] {item['texto']}")
    return 0


def _cenarios(args) -> int:
    """Catálogo de cenários: roda cada um e confere que termina com resposta explícita e se repete (mesmo hash)."""
    from fin_mas import invariantes
    nomes = [n for n in CENARIOS if not args.filtro or args.filtro in n]
    falhas = 0
    print(f"{'cenário':<30} {'cognição':<8} {'resposta':<9} {'invariantes':<11} {'repetível':<9} o que observar")
    for nome in nomes:
        sc = CENARIOS[nome]
        a = run_scenario(nome)
        violacoes = invariantes.verificar(a.audit.records)
        repetivel = a.hash == run_scenario(nome).hash if args.verificar else None
        respostas = [r.performative if r is not None else "SEM RESPOSTA" for r in a.respostas.values()]
        ok = "SEM RESPOSTA" not in respostas and not violacoes and repetivel is not False
        falhas += not ok
        print(f"{nome:<30} {sc.cognicao:<8} {'/'.join(dict.fromkeys(respostas)):<9} "
              f"{'ok' if not violacoes else str(len(violacoes)) + ' VIOLAÇÃO':<11} "
              f"{'-' if repetivel is None else 'sim' if repetivel else 'NÃO':<9} {sc.esperado or sc.descricao[:70]}")
        for v in violacoes:
            print(f"    {v}")
    print(f"{len(nomes) - falhas} de {len(nomes)} cenário(s) em ordem")
    return 1 if falhas else 0


def _modelos(args) -> int:
    from fin_mas.fontes.planilha import gerar_modelos
    for caminho in gerar_modelos(args.out):
        print(caminho)
    return 0


def _invariantes(args) -> int:
    from fin_mas import invariantes
    log = _ler_trace(args)
    if log is None:
        return 3
    violacoes = invariantes.verificar(log.records)
    for v in violacoes:
        print(f"VIOLAÇÃO: {v}")
    print(f"{args.trace}: {len(log.records)} registros, {len(invariantes.INVARIANTES)} invariantes, "
          f"{len(violacoes)} violação(ões)")
    return 1 if violacoes else 0


def _llm(args) -> int:
    from fin_mas.services import provedores
    if args.acao == "provedores":
        for p in provedores.situacao():
            chave = "não usa chave" if p["variavel_chave"] is None else \
                f"{p['variavel_chave']}: {'definida' if p['tem_chave'] else 'ausente'}" \
                f"{' (opcional)' if p['chave_opcional'] else ''}"
            print(f"{p['id']:<14} {'externo' if p['externo'] else 'local':<8} {chave}"
                  f"{' (exige --base-url)' if p['exige_base_url'] else ''}")
        return 0
    import json as _json

    from fin_mas.cognicao import bancada
    config = {"provedor": args.provedor, "modelo": args.modelo}
    if args.base_url:
        config["base_url"] = args.base_url
    if args.consentimento:
        config["consentimento_externo"] = True
    try:
        resultado = bancada.avaliar(config)
    except ConfiguracaoInvalida as e:
        print(f"configuração de LLM inválida: {e}", file=sys.stderr)
        return 2
    print(_json.dumps(resultado, ensure_ascii=False, indent=2) if args.json else bancada.tabela(resultado))
    return 0


def _mcp_excel(args) -> int:
    from fin_mas.mcp.excel_server import ServidorExcel
    ServidorExcel(args.pasta).servir()
    return 0


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="fin-mas", description="Sistema multiagente de controladoria da SMA (fictícia)")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("list", help="lista os cenários")
    run = sub.add_parser("run", help="executa um cenário")
    run.add_argument("--scenario", required=True)
    run.add_argument("--seed", type=int, default=None)
    run.add_argument("--trace", help="grava o trace JSONL neste arquivo")
    run.add_argument("--verbose", action="store_true", help="inclui as entregas de mensagem")
    run.add_argument("--porte", choices=PORTES, default=None, help="porte da empresa (regras de models/portes.yaml)")
    run.add_argument("--pasta", default=None, help="pasta (ou arquivo .xlsx) com a planilha preenchida")
    run.add_argument("--memoria", default=None, help="arquivo JSON do SVC-MEM (persiste entre execuções)")
    run.add_argument("--llm", default=None, metavar="MODELO | PROVEDOR:MODELO",
                     help="liga o LLM opcional: um apelido (mock-narrador, claude-opus-5-5) liga só a síntese do "
                          "AG-REL; PROVEDOR:MODELO aceita mock, anthropic, openai, gemini e openai-compat")
    run.add_argument("--llm-agentes", default=None, metavar="AG-ORC,AG-RES,AG-REL",
                     help="agentes em que o LLM é ligado (padrão: AG-REL); AG-ORQ, AG-CUS e AG-CIN não aceitam")
    run.add_argument("--llm-usos", default=None, metavar="hipoteses,narrativa",
                     help="usos ligados (padrão: os do agente): sintese, hipoteses, narrativa, comentario")
    run.add_argument("--llm-base-url", default=None, help="URL do servidor (obrigatória em openai-compat)")
    run.add_argument("--llm-consentimento", action="store_true",
                     help="autoriza enviar dados (com pseudônimos) a um provedor externo")
    run.add_argument("--cognicao", default=None, choices=NIVEIS,
                     help="nível de cognição dos agentes BDI (padrão: o do cenário); ver ADR-008")
    rep = sub.add_parser("replay", help="reconstrói uma conversa a partir de um trace JSONL")
    rep.add_argument("trace")
    rep.add_argument("conversation_id")
    rep.add_argument("--verbose", action="store_true")
    rep.add_argument("--sem-verificar", action="store_true", help="lê trace sem cadeia de hashes (anterior à DSM3)")
    rep.add_argument("--ancora", default=None,
                     help="hash final publicado: verifica sem a chave local (trace gravado em outra máquina)")
    cmp_ = sub.add_parser("comparar", help="SMA x workflow centralizado sob as mesmas seeds")
    cmp_.add_argument("--seeds", type=int, default=10)
    cmp_.add_argument("--out", default="docs/dsm3/resultados")
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
    srv.add_argument("--acesso", dest="pasta_acesso", default="dados/acesso", help="pasta do cadastro de acesso (SVC-IAM)")
    srv.add_argument("--demo", action="store_true", help="cria e usa as contas de demonstração (senha pública)")
    srv.add_argument("--cognicao", default=None, choices=NIVEIS, help="nível de cognição (padrão: o do cenário)")
    srv.add_argument("--instalacao", default=None, metavar="PASTA", help="sobe a partir da pasta criada pelo `instalar`")
    cli_acesso.configurar(sub)
    implantacao.configurar(sub)
    cli_fontes.configurar(sub)  # fontes entender|testar e erp-demo (ADR-011)
    aud = sub.add_parser("auditoria", help="recorte de um trace JSONL com os filtros do dashboard")
    aud.add_argument("trace")
    for filtro in ("agente", "competencia", "tarefa", "tipo", "q"):
        aud.add_argument(f"--{filtro}", default=None)
    aud.add_argument("--de-t", type=int, default=None)
    aud.add_argument("--ate-t", type=int, default=None)
    aud.add_argument("--custo-min", type=float, default=None)
    aud.add_argument("--json", action="store_true")
    exp_ = sub.add_parser("explicar", help="cadeia (percepção, crença, hipótese, plano, decisão) que levou a um registro")
    exp_.add_argument("trace")
    exp_.add_argument("seq", type=int)
    seq_ = sub.add_parser("sequencia", help="diagrama de sequência (Mermaid) de uma conversa do trace")
    seq_.add_argument("trace")
    seq_.add_argument("conversa")
    cen = sub.add_parser("cenarios", help="roda o catálogo de cenários e mostra a tabela de conferência")
    cen.add_argument("--verificar", action="store_true", help="roda cada cenário duas vezes e compara os hashes")
    cen.add_argument("--filtro", default=None, help="só os cenários cujo nome contém o texto")
    inv = sub.add_parser("invariantes", help="confere as propriedades de segurança num trace JSONL")
    inv.add_argument("trace")
    mod = sub.add_parser("modelos", help="grava o modelo Excel em branco e um exemplo por porte")
    mod.add_argument("--out", default="modelos")
    mcp = sub.add_parser("mcp-excel", help="servidor MCP (stdio) das planilhas da pasta")
    mcp.add_argument("--pasta", required=True)
    ver = sub.add_parser("verificar", help="confere a cadeia de hashes de um trace JSONL (adulteração)")
    ver.add_argument("trace")
    ver.add_argument("--ancora", default=None,
                     help="hash final publicado: verifica sem a chave local (ex.: em outra máquina)")
    llm = sub.add_parser("llm", help="provedores de LLM e bancada de avaliação de hipóteses (ADR-008)")
    llm_sub = llm.add_subparsers(dest="acao", required=True)
    llm_sub.add_parser("provedores", help="lista os provedores e se a chave de cada um está no ambiente")
    ava = llm_sub.add_parser("avaliar", help="roda os casos da bancada com um provedor e mostra a tabela")
    ava.add_argument("--provedor", default="mock")
    ava.add_argument("--modelo", default="mock-analista")
    ava.add_argument("--base-url", default=None)
    ava.add_argument("--consentimento", action="store_true", help="autoriza enviar os casos a um provedor externo")
    ava.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.comando == "list":
        for sc in CENARIOS.values():
            print(f"{sc.nome:<24} seed={sc.seed:<5} {sc.descricao}")
        return 0
    comandos = {"run": _run, "replay": _replay, "comparar": _comparar, "export": _export,
                "relatorio": _relatorio, "serve": _serve, "modelos": _modelos, "mcp-excel": _mcp_excel,
                "verificar": _verificar, "llm": _llm, "acesso": cli_acesso.executar, "auditoria": _auditoria,
                "explicar": _explicar, "sequencia": _explicar, "cenarios": _cenarios, "invariantes": _invariantes,
                "instalar": implantacao.instalar, "doctor": implantacao.doctor,
                "fontes": cli_fontes.executar, "erp-demo": cli_fontes.executar}
    return comandos[args.comando](args)


if __name__ == "__main__":
    raise SystemExit(main())

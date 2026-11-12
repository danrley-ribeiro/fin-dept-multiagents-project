"""Linha de comando do SVC-IAM (ADR-009): o mesmo que a TUI faz, para scripts e testes.

    python -m fin_mas acesso iniciar --usuario admin --nome "Administração"   primeiro administrador
    python -m fin_mas acesso demo                                             contas de demonstração
    python -m fin_mas acesso usuario listar | criar | bloquear | desbloquear | desativar | redefinir-senha
    python -m fin_mas acesso usuario papeis USUARIO ROLE-APR ROLE-SOL | vinculo USUARIO --pessoa carla --cargo gerente
    python -m fin_mas acesso papeis                                           matriz papel x permissão
    python -m fin_mas acesso sessao listar | revogar ID
    python -m fin_mas acesso trilha ver [--ator U --evento E --resultado negado] | verificar | exportar ARQ
    python -m fin_mas acesso tui                                              console de administração (Textual)

A pasta do cadastro vem de `--acesso` (padrão `dados/acesso`, ou a variável `FIN_MAS_ACESSO`).
Toda alteração exige um administrador: `--como USUARIO` e a senha, pedida no terminal ou lida
de `FIN_MAS_SENHA`. Senhas novas vêm de `FIN_MAS_SENHA_NOVA` ou do terminal, nunca de argumento
(argumentos aparecem na lista de processos e no histórico do shell).
"""
import getpass
import json
import os
import sys

from fin_mas.core import permissoes
from fin_mas.services.iam import SENHA_DEMO, Acesso, AcessoNegado, criar_demo
from fin_mas.services.trilha import TrilhaAdulterada

PASTA_PADRAO = "dados/acesso"


def configurar(sub) -> None:
    p = sub.add_parser("acesso", help="contas, papéis, sessões e trilha de acesso (SVC-IAM)")
    p.add_argument("--acesso", dest="pasta_acesso", default=os.environ.get("FIN_MAS_ACESSO", PASTA_PADRAO),
                   help="pasta do cadastro de acesso")
    p.add_argument("--como", default=None, help="administrador que executa a alteração")
    p.add_argument("--json", action="store_true")
    a = p.add_subparsers(dest="acao", required=True)
    ini = a.add_parser("iniciar", help="cria o primeiro administrador (só com o cadastro vazio)")
    ini.add_argument("--usuario", required=True)
    ini.add_argument("--nome", default="Administração de Acesso")
    a.add_parser("demo", help="cria as contas de demonstração (senha pública e documentada)")
    a.add_parser("papeis", help="matriz papel x permissão, lida dos modelos")
    a.add_parser("tui", help="console de administração no terminal (exige o extra `tui`)")
    u = a.add_parser("usuario", help="administra contas").add_subparsers(dest="operacao", required=True)
    u.add_parser("listar")
    criar = u.add_parser("criar")
    criar.add_argument("usuario")
    criar.add_argument("--nome", required=True)
    criar.add_argument("--papeis", required=True, help="separados por vírgula, ex.: ROLE-APR,ROLE-SOL")
    criar.add_argument("--pessoa", default=None, help="usuário desta pessoa no ERP (segregação de funções)")
    criar.add_argument("--cargo", default=None, help=f"um de: {', '.join(permissoes.cargos())}")
    for nome in ("bloquear", "desbloquear", "desativar", "redefinir-senha"):
        u.add_parser(nome).add_argument("usuario")
    pap = u.add_parser("papeis")
    pap.add_argument("usuario")
    pap.add_argument("papeis", nargs="+")
    vin = u.add_parser("vinculo")
    vin.add_argument("usuario")
    vin.add_argument("--pessoa", default=None)
    vin.add_argument("--cargo", default=None)
    s = a.add_parser("sessao", help="sessões abertas").add_subparsers(dest="operacao", required=True)
    s.add_parser("listar")
    s.add_parser("revogar").add_argument("id")
    t = a.add_parser("trilha", help="trilha de acesso").add_subparsers(dest="operacao", required=True)
    ver = t.add_parser("ver")
    for filtro in ("ator", "evento", "resultado"):
        ver.add_argument(f"--{filtro}", default=None)
    ver.add_argument("--ultimos", type=int, default=40)
    t.add_parser("verificar")
    t.add_parser("exportar").add_argument("arquivo")


def _senha(variavel: str, pergunta: str, confirmar=False) -> str:
    if os.environ.get(variavel):
        return os.environ[variavel]
    if not sys.stdin.isatty():
        raise AcessoNegado("IAM-02", f"defina {variavel} ou rode num terminal para digitar a senha")
    senha = getpass.getpass(pergunta + ": ")
    if confirmar and getpass.getpass("repita: ") != senha:
        raise AcessoNegado("IAM-02", "as senhas digitadas não conferem")
    return senha


def _administrador(acesso: Acesso, args):
    if not args.como:
        raise AcessoNegado("IAM-05", "informe quem executa a alteração: --como USUARIO")
    sessao, _ = acesso.autenticar(args.como, _senha("FIN_MAS_SENHA", f"senha de {args.como}"), origem="cli")
    return sessao


def _mostrar(args, dados, linhas) -> None:
    print(json.dumps(dados, ensure_ascii=False, indent=2, default=str) if args.json else "\n".join(linhas))


def _conta(c) -> str:
    vinculo = f" | ERP: {c['pessoa_erp']}" if c.get("pessoa_erp") else ""
    cargo = f" | cargo: {c['cargo']}" if c.get("cargo") else ""
    return f"{c['usuario']:<12} {c['estado']:<11} {', '.join(c['papeis']):<40} {c['nome']}{cargo}{vinculo}"


def executar(args) -> int:
    try:
        return _executar(args)
    except AcessoNegado as erro:
        print(f"acesso negado: {erro}", file=sys.stderr)
        return 3
    except TrilhaAdulterada as erro:
        print(f"TRILHA ADULTERADA: {erro}", file=sys.stderr)
        return 3


def _executar(args) -> int:
    if args.acao == "papeis":
        papeis = permissoes.papeis_humanos()
        dados = {p: sorted(d["permissoes"]) for p, d in papeis.items()}
        linhas = []
        for papel, d in papeis.items():
            linhas.append(f"{papel}  {d['titulo']}")
            linhas += [f"    {perm}  {permissoes.catalogo()[perm]['titulo']}" for perm in sorted(d["permissoes"])]
        _mostrar(args, dados, linhas)
        return 0
    if args.acao == "tui":
        from fin_mas.tui import executar as tui
        return tui(args.pasta_acesso)
    if args.acao == "demo":
        acesso = criar_demo(args.pasta_acesso)
        _mostrar(args, {"pasta": args.pasta_acesso, "contas": [c["usuario"] for c in acesso.contas()]},
                 [f"contas de demonstração em {args.pasta_acesso} (senha: {SENHA_DEMO}):"]
                 + ["  " + _conta(c) for c in acesso.contas()])
        return 0
    acesso = Acesso(args.pasta_acesso)
    if args.acao == "iniciar":
        conta = acesso.iniciar(args.usuario, args.nome, _senha("FIN_MAS_SENHA_NOVA", "senha do administrador", True))
        _mostrar(args, conta, [f"administrador {conta['usuario']} criado em {args.pasta_acesso}"])
        return 0
    if args.acao == "trilha":
        return _trilha(acesso, args)
    if args.acao == "usuario" and args.operacao == "listar":
        _mostrar(args, acesso.contas(), [_conta(c) for c in acesso.contas()] or ["nenhuma conta: use `acesso iniciar`"])
        return 0
    adm = _administrador(acesso, args)
    try:
        if args.acao == "sessao":
            return _sessoes(acesso, adm, args)
        return _usuarios(acesso, adm, args)
    finally:
        acesso.sair(adm)


def _usuarios(acesso, adm, args) -> int:
    op = args.operacao
    if op == "criar":
        conta = acesso.criar_conta(adm, args.usuario, args.nome, _senha("FIN_MAS_SENHA_NOVA", "senha temporária", True),
                                   [p.strip() for p in args.papeis.split(",") if p.strip()], pessoa_erp=args.pessoa,
                                   cargo=args.cargo)
    elif op == "redefinir-senha":
        conta = acesso.redefinir_senha(adm, args.usuario, _senha("FIN_MAS_SENHA_NOVA", "senha temporária", True))
    elif op == "papeis":
        conta = acesso.atribuir_papeis(adm, args.usuario, args.papeis)
    elif op == "vinculo":
        conta = acesso.definir_vinculo(adm, args.usuario, pessoa_erp=args.pessoa, cargo=args.cargo)
    else:
        conta = {"bloquear": acesso.bloquear, "desbloquear": acesso.desbloquear, "desativar": acesso.desativar}[op](
            adm, args.usuario)
    _mostrar(args, conta, [_conta(conta)])
    return 0


def _sessoes(acesso, adm, args) -> int:
    if args.operacao == "revogar":
        acesso.revogar(adm, args.id)
        _mostrar(args, {"revogada": args.id}, [f"sessão {args.id} revogada"])
        return 0
    sessoes = acesso.sessoes(adm)
    _mostrar(args, sessoes, [f"{s['id']:<16} {s['usuario']:<12} {'viva' if s['viva'] else 'encerrada':<10} "
                             f"{s['origem']}{' | ' + s['revogada'] if s['revogada'] else ''}" for s in sessoes])
    return 0


def _trilha(acesso, args) -> int:
    if args.operacao == "verificar":
        r = acesso.trilha.verificar()
        _mostrar(args, {"integra": True, **r}, [f"trilha de acesso íntegra: {r['registros']} registro(s), cadeia e "
                                                f"cabeça selada conferem (hash final {str(r['hash_final'])[:16]}…)"])
        return 0
    registros = acesso.trilha.ler()
    if args.operacao == "exportar":
        acesso.trilha.verificar()
        with open(args.arquivo, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in registros)
        _mostrar(args, {"arquivo": args.arquivo, "registros": len(registros)},
                 [f"{len(registros)} registro(s) exportados para {args.arquivo}"])
        return 0
    for campo in ("ator", "evento", "resultado"):
        if getattr(args, campo):
            registros = [r for r in registros if r.get(campo) == getattr(args, campo)]
    registros = registros[-args.ultimos:]
    extras = lambda r: " ".join(f"{k}={v}" for k, v in r.items()  # noqa: E731
                                if k not in ("seq", "t", "evento", "ator", "resultado", "_hash"))
    _mostrar(args, registros, [f"#{r['seq']:<4} {r['evento']:<22} {str(r['ator']):<12} {r['resultado']:<7} {extras(r)}"
                               for r in registros])
    return 0

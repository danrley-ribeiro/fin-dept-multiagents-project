"""Linha de comando do acesso avançado (DSM4, ADR-012): o mesmo que a TUI faz, para scripts e testes.

    python -m fin_mas acesso 2fa ativar | confirmar | desativar --como USUARIO      segundo fator da própria conta
    python -m fin_mas acesso 2fa redefinir USUARIO --como ADMIN                    aparelho perdido (administração)
    python -m fin_mas acesso politica ver | definir --exigir-2fa ROLE-ADM,ROLE-APR --escalonamento 50
    python -m fin_mas acesso delegacao listar | criar PARA --horas 8 --teto 1000000 --competencia 2026-09 | revogar ID
    python -m fin_mas acesso alcadas [--porte media]                               alçadas e limite de dupla aprovação
    python -m fin_mas acesso empresa listar | criar ID --nome N --porte P | escopo USUARIO E1 E2
    python -m fin_mas acesso segredo listar | definir NOME | remover NOME          cofre (o valor nunca é mostrado)
    python -m fin_mas memoria adotar ARQUIVO [--forcar] --como ADMIN               adota memória íntegra copiada

Como em `cli_acesso`: senhas, códigos e valores de segredo vêm de variáveis de ambiente
(`FIN_MAS_SENHA`, `FIN_MAS_CODIGO_2FA`, `FIN_MAS_SEGREDO`) ou do terminal, nunca de argumento.
Com várias empresas no cadastro, `--empresa` escolhe a empresa ativa da sessão da CLI.
"""
import getpass
import os
import sys

ACOES = ("2fa", "politica", "delegacao", "alcadas", "empresa", "segredo")


def configurar_acesso(a) -> None:
    f = a.add_parser("2fa", help="segundo fator TOTP da própria conta (IAM-08)").add_subparsers(dest="operacao",
                                                                                               required=True)
    f.add_parser("ativar", help="gera o segredo e mostra uma única vez")
    f.add_parser("confirmar", help="confere o primeiro código e mostra os códigos de recuperação uma única vez")
    f.add_parser("desativar", help="desativa, confirmando com um código válido")
    f.add_parser("redefinir", help="desliga o segundo fator de outra conta (aparelho perdido)").add_argument("usuario")
    pol = a.add_parser("politica", help="política do cadastro (IAM-08, POL-14)").add_subparsers(dest="operacao",
                                                                                               required=True)
    pol.add_parser("ver")
    d = pol.add_parser("definir")
    d.add_argument("--exigir-2fa", default=None, help="papéis separados por vírgula (ROLE-ADM,ROLE-APR) ou 'nenhum'")
    d.add_argument("--escalonamento", type=int, default=None, help="percentual do prazo (10 a 90)")
    d.add_argument("--sem-escalonamento", action="store_true")
    dl = a.add_parser("delegacao", help="delegações de aprovação (POL-11)").add_subparsers(dest="operacao", required=True)
    dl.add_parser("listar")
    c = dl.add_parser("criar")
    c.add_argument("para")
    c.add_argument("--horas", type=float, required=True, help="prazo da delegação, em horas a partir de agora")
    c.add_argument("--teto", type=int, required=True, help="valor máximo, em centavos")
    c.add_argument("--competencia", default=None)
    c.add_argument("--solicitacao", default=None)
    dl.add_parser("revogar").add_argument("id")
    al = a.add_parser("alcadas", help="alçadas por cargo e limite de dupla aprovação de cada porte (POL-10, POL-12)")
    al.add_argument("--porte", default=None)
    e = a.add_parser("empresa", help="empresas e escopo das contas (IAM-09)").add_subparsers(dest="operacao",
                                                                                            required=True)
    e.add_parser("listar")
    ce = e.add_parser("criar")
    ce.add_argument("id")
    ce.add_argument("--nome", required=True)
    ce.add_argument("--porte", default="media")
    es = e.add_parser("escopo")
    es.add_argument("usuario")
    es.add_argument("empresas", nargs="*")
    s = a.add_parser("segredo", help="cofre selado: chaves de LLM e credenciais (IAM-10)").add_subparsers(
        dest="operacao", required=True)
    s.add_parser("listar")
    s.add_parser("definir").add_argument("nome")
    s.add_parser("remover").add_argument("nome")


def configurar_memoria(sub) -> None:
    from fin_mas.cli_acesso import PASTA_PADRAO
    m = sub.add_parser("memoria", help="memória de longo prazo (SVC-MEM)")
    m.add_argument("--acesso", dest="pasta_acesso", default=os.environ.get("FIN_MAS_ACESSO", PASTA_PADRAO))
    m.add_argument("--como", default=None)
    m.add_argument("--json", action="store_true")
    ms = m.add_subparsers(dest="acao", required=True)
    ad = ms.add_parser("adotar", help="adota um arquivo íntegro copiado de outra pasta ou restaurado de backup")
    ad.add_argument("arquivo")
    ad.add_argument("--forcar", action="store_true", help="substitui uma memória já gravada neste caminho")


def segredo_do_terminal(variavel: str, pergunta: str) -> str:
    from fin_mas.services.iam import AcessoNegado
    if os.environ.get(variavel):
        return os.environ[variavel]
    if not sys.stdin.isatty():
        raise AcessoNegado("IAM-08", f"defina {variavel} ou rode num terminal para digitar")
    return getpass.getpass(pergunta + ": ")


def _ativa(acesso, sessao, args):
    if getattr(args, "empresa", None):
        return acesso.escolher_empresa(sessao, args.empresa)
    return sessao


def executar(acesso, args, entrar, mostrar) -> int:
    """`entrar(acesso, args)` autentica a conta de `--como` (com o segundo fator, se ativo)."""
    from fin_mas.env.portes import PORTES, perfil
    from fin_mas.services.politica import _reais
    if args.acao == "alcadas":
        portes = [args.porte] if args.porte else list(PORTES)
        dados = {p: {"limites_alcada": perfil(p)["limites_alcada"], "dupla_aprovacao": perfil(p).get("dupla_aprovacao"),
                     "aprovadores": perfil(p)["aprovadores"]} for p in portes}
        linhas = []
        for p, d in dados.items():
            limites = ", ".join(f"{c} {_reais(v)}" for c, v in d["limites_alcada"].items())
            dupla = "não se aplica" if d["dupla_aprovacao"] is None else f"acima de {_reais(d['dupla_aprovacao'])}"
            linhas.append(f"{p:<8} alçadas: {limites} | dupla aprovação: {dupla}")
        mostrar(args, dados, linhas)
        return 0
    if args.acao == "politica" and args.operacao == "ver":
        politica = acesso.politica()
        mostrar(args, politica, [f"segundo fator obrigatório para: {', '.join(politica['exigir_2fa_para']) or 'ninguém'}",
                                 f"escalonamento: {politica['escalonamento_percentual'] or 'desligado'}"
                                 f"{'% do prazo' if politica['escalonamento_percentual'] else ''}"])
        return 0
    if args.acao == "empresa" and args.operacao == "listar":
        empresas = acesso.empresas()
        mostrar(args, empresas, [f"{e['id']:<16} {e['porte']:<8} {e['nome']}" for e in empresas.values()]
                or ["nenhuma empresa: o cadastro atende uma empresa só"])
        return 0
    sessao = _ativa(acesso, entrar(acesso, args), args)
    try:
        return _com_sessao(acesso, sessao, args, mostrar)
    finally:
        acesso.sair(sessao)


def _com_sessao(acesso, sessao, args, mostrar) -> int:
    acao, op = args.acao, args.operacao
    if acao == "2fa":
        if op == "ativar":
            info = acesso.iniciar_2fa(sessao)
            mostrar(args, info, ["segredo do segundo fator (mostrado uma única vez; cadastre no aplicativo):",
                                 f"  {info['segredo']}", f"  {info['uri']}",
                                 "depois: python -m fin_mas acesso 2fa confirmar (com FIN_MAS_CODIGO_2FA)"])
        elif op == "confirmar":
            codigos = acesso.confirmar_2fa(sessao, segredo_do_terminal("FIN_MAS_CODIGO_2FA", "código atual"))
            mostrar(args, {"ativo": True, "codigos_recuperacao": codigos},
                    ["segundo fator ativo. Códigos de recuperação (uso único, mostrados uma única vez):"]
                    + [f"  {c}" for c in codigos])
        elif op == "desativar":
            acesso.desativar_2fa(sessao, segredo_do_terminal("FIN_MAS_CODIGO_2FA", "código atual"))
            mostrar(args, {"ativo": False}, ["segundo fator desativado"])
        else:
            conta = acesso.redefinir_2fa(sessao, args.usuario)
            mostrar(args, conta, [f"segundo fator de {args.usuario} desligado; as sessões dele caíram"])
        return 0
    if acao == "politica":
        campos = {}
        if args.exigir_2fa is not None:
            campos["exigir_2fa_para"] = [] if args.exigir_2fa.strip() in ("", "nenhum") else \
                [p.strip() for p in args.exigir_2fa.split(",") if p.strip()]
        if args.sem_escalonamento:
            campos["escalonamento_percentual"] = None
        elif args.escalonamento is not None:
            campos["escalonamento_percentual"] = args.escalonamento
        politica = acesso.definir_politica(sessao, **campos)
        mostrar(args, politica, [f"política do cadastro: {politica}"])
        return 0
    if acao == "delegacao":
        if op == "listar":
            lista = acesso.delegacoes(None if sessao.pode("PERM-IAM-USUARIOS") else sessao.usuario)
            mostrar(args, lista, [f"{d['id']} {d['de']} -> {d['para']} teto {d['teto']} até {d['ate']} {d['escopo']} "
                                  f"{d['situacao']}" for d in lista] or ["nenhuma delegação"])
        elif op == "criar":
            d = acesso.delegar(sessao, args.para, ate=acesso.relogio() + args.horas * 3600, teto=args.teto,
                               competencia=args.competencia, solicitacao=args.solicitacao)
            mostrar(args, d, [f"delegação {d['id']} de {d['de']} para {d['para']} criada (teto {d['teto']}, "
                              f"{d['escopo']})"])
        else:
            d = acesso.revogar_delegacao(sessao, args.id)
            mostrar(args, d, [f"delegação {d['id']} revogada"])
        return 0
    if acao == "empresa":
        if op == "criar":
            e = acesso.criar_empresa(sessao, args.id, args.nome, args.porte)
            mostrar(args, e, [f"empresa {e['id']} ({e['nome']}, porte {e['porte']}) criada"])
        else:
            c = acesso.definir_escopo(sessao, args.usuario, args.empresas)
            mostrar(args, c, [f"escopo de {args.usuario}: {', '.join(c.get('empresas') or []) or 'nenhuma empresa'}"])
        return 0
    if acao == "segredo":
        if op == "listar":
            nomes = acesso.segredos(sessao)
            mostrar(args, nomes, [f"{s['nome']:<40} definido por {s['por']}" for s in nomes] or ["cofre vazio"])
        elif op == "definir":
            r = acesso.definir_segredo(sessao, args.nome, segredo_do_terminal("FIN_MAS_SEGREDO", f"valor de {args.nome}"))
            mostrar(args, r, [f"segredo {args.nome} guardado no cofre (o valor não é mostrado)"])
        else:
            r = acesso.remover_segredo(sessao, args.nome)
            mostrar(args, r, [f"segredo {args.nome} {'removido' if r['removido'] else 'não existia'}"])
        return 0
    raise ValueError(acao)


def executar_memoria(args) -> int:
    from fin_mas.cli_acesso import _administrador, _mostrar
    from fin_mas.services.iam import Acesso, AcessoNegado
    from fin_mas.services.memoria import MemoriaRecusada, adotar
    acesso = Acesso(args.pasta_acesso)
    try:
        sessao = _administrador(acesso, args)
    except AcessoNegado as erro:
        print(f"acesso negado: {erro}", file=sys.stderr)
        return 3
    try:
        acesso.exigir(sessao, "PERM-MEM-ADOTAR")
        r = adotar(args.arquivo, forcar=args.forcar)
    except AcessoNegado as erro:
        print(f"acesso negado: {erro}", file=sys.stderr)
        return 3
    except MemoriaRecusada as erro:
        acesso.registrar("memoria_adotada", sessao.usuario, "negado", arquivo=os.path.basename(args.arquivo),
                         motivo=str(erro))
        print(f"adoção recusada: {erro}", file=sys.stderr)
        return 3
    finally:
        acesso.sair(sessao)
    acesso.registrar("memoria_adotada", sessao.usuario, arquivo=os.path.basename(args.arquivo), entradas=r["entradas"],
                     origem=r["origem"], chave_substituida=r["chave_substituida"], contador=r["contador"])
    _mostrar(args, r, [f"memória {args.arquivo} adotada: {r['entradas']} entrada(s), origem {r['origem']}, "
                       f"contador {r['contador']}"])
    return 0

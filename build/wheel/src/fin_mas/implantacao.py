"""Implantação local: assistente de primeiro uso (`instalar`) e diagnóstico (`doctor`).

    python -m fin_mas instalar            perguntas no terminal: porte, segmento, administrador, pasta de dados
    python -m fin_mas instalar --demo     contas de demonstração, sem perguntas (avaliação e aula)
    python -m fin_mas doctor              confere o ambiente e o que já foi instalado

`instalar` deixa uma pasta de dados pronta para uso:

    <pasta>/acesso/      cadastro selado de contas e sessões e a trilha de acesso (SVC-IAM)
    <pasta>/empresa/     onde o dashboard grava a planilha da empresa
    <pasta>/modelos/     planilha modelo em branco e o exemplo preenchido do porte escolhido
    <pasta>/instalacao.json   porte, segmento, cognição e porta escolhidos (o `serve --instalacao` lê daqui)

DSM4: o porte pode ser também `mei` (microempreendedor individual) ou `media_ii` (Média empresa II
do BNDES), e o segmento (`software_servicos`, `comercio`, `servicos`, `industria`) define o plano de
contas, a estrutura de custos e o rateio (models/segmentos.yaml). Backup, restauração e migração da
pasta: `fin-mas backup | restaurar | migrar` (fin_mas/manutencao.py).

As chaves de integridade ficam fora dessa pasta (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves`):
copiar a pasta de dados para outra máquina não leva as chaves junto, e o cadastro copiado é
recusado lá (falha fechada). Sem terminal interativo, as respostas vêm das opções e das
variáveis `FIN_MAS_SENHA_NOVA`; nada é perguntado.
"""
import getpass
import importlib.util
import json
import os
import socket
import sys
from pathlib import Path

from fin_mas import __version__
from fin_mas.cognicao import NIVEIS
from fin_mas.env.portes import PORTES, perfil
from fin_mas.env.segmentos import SEGMENTO_PADRAO, SEGMENTOS, ficha
from fin_mas.recursos import models_dir, origem, web_dist
from fin_mas.services import provedores
from fin_mas.services.iam import SENHA_DEMO, Acesso, AcessoNegado, criar_demo
from fin_mas.services.selado import ArquivoComprometido, pasta_de_chaves

PASTA_PADRAO = "dados"


def configurar(sub) -> None:
    ins = sub.add_parser("instalar", help="assistente de primeiro uso: pasta de dados, porte e administrador")
    ins.add_argument("--pasta", default=PASTA_PADRAO, help="pasta de dados (padrão: dados)")
    ins.add_argument("--porte", choices=PORTES, default=None)
    ins.add_argument("--segmento", choices=SEGMENTOS, default=None, help="comércio, serviços, indústria ou o padrão")
    ins.add_argument("--cognicao", choices=NIVEIS, default=None)
    ins.add_argument("--porta", type=int, default=8765)
    ins.add_argument("--usuario", default=None, help="usuário do administrador de acesso")
    ins.add_argument("--nome", default=None)
    ins.add_argument("--demo", action="store_true", help="cria as contas de demonstração (senha pública)")
    doc = sub.add_parser("doctor", help="diagnóstico do ambiente e da instalação")
    doc.add_argument("--pasta", default=PASTA_PADRAO)
    doc.add_argument("--json", action="store_true")


def _perguntar(texto, padrao, opcoes=None):
    if not sys.stdin.isatty():
        return padrao
    while True:
        r = input(f"{texto} [{padrao}]: ").strip() or padrao
        if opcoes is None or r in opcoes:
            return r
        print(f"  opções: {', '.join(opcoes)}")


def instalar(args) -> int:
    pasta = Path(args.pasta)
    print(f"SMA de Controladoria {__version__}: instalação em {pasta.resolve()}")
    if not args.porte and sys.stdin.isatty():
        print("Portes: " + "; ".join(f"{p} = {perfil(p)['titulo']}" for p in PORTES))
    porte = args.porte or _perguntar("Porte da empresa", "media", PORTES)
    if not args.segmento and sys.stdin.isatty():
        print("Segmentos: " + "; ".join(f"{s} = {ficha(s)['titulo']}" for s in SEGMENTOS))
    segmento = args.segmento or _perguntar("Segmento da empresa", SEGMENTO_PADRAO, SEGMENTOS)
    cognicao = args.cognicao or _perguntar("Nível de cognição dos agentes (basico, local, llm)", "local", NIVEIS)
    for sub in ("acesso", "empresa", "modelos"):
        (pasta / sub).mkdir(parents=True, exist_ok=True)
    if args.demo:
        acesso = criar_demo(pasta / "acesso")
        print(f"  contas de demonstração criadas (senha: {SENHA_DEMO}): " + ", ".join(c["usuario"] for c in acesso.contas()))
    else:
        acesso = Acesso(pasta / "acesso")
        if acesso.vazio():
            usuario = args.usuario or _perguntar("Usuário do administrador de acesso", "admin")
            nome = args.nome or _perguntar("Nome do administrador", "Administração de Acesso")
            senha = os.environ.get("FIN_MAS_SENHA_NOVA")
            if not senha:
                if not sys.stdin.isatty():
                    print("defina FIN_MAS_SENHA_NOVA (ou use --demo) para instalar sem terminal", file=sys.stderr)
                    return 2
                senha = getpass.getpass("Senha do administrador (12+ caracteres): ")
                if getpass.getpass("Repita a senha: ") != senha:
                    print("as senhas não conferem", file=sys.stderr)
                    return 2
            try:
                acesso.iniciar(usuario, nome, senha)
            except AcessoNegado as erro:
                print(f"não foi possível criar o administrador: {erro}", file=sys.stderr)
                return 2
            print(f"  administrador {usuario} criado; as demais contas você cria em `fin-mas acesso tui`")
        else:
            print(f"  cadastro de acesso já existe ({len(acesso.contas())} conta(s)): mantido como está")
    from fin_mas.env.dataset import Dataset
    from fin_mas.fontes.planilha import gerar_modelo
    gerar_modelo(pasta / "modelos" / "modelo_controladoria_em_branco.xlsx")
    gerar_modelo(pasta / "modelos" / f"exemplo_{porte}.xlsx",
                 exemplo=Dataset(seed=42, porte=porte, segmento=segmento, plantar=("competencia",)))
    p = perfil(porte)
    cenario = {"mei": "fechamento_mei", "micro": "fechamento_micro", "pequena": "fechamento_pequena",
               "media_ii": "fechamento_media_ii", "grande": "fechamento_grande"}.get(porte, "expediente_sma")
    config = {"versao": __version__, "porte": porte, "cognicao": cognicao, "porta": args.porta, "cenario": cenario,
              "tem_erp": p["tem_erp"], "fonte_primaria": p["fonte_primaria"], "segmento": segmento}
    (pasta / "instalacao.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  porte: {p['titulo']} ({'com ERP' if p['tem_erp'] else 'sem ERP: use a planilha modelo'}); cognição: {cognicao}")
    print(f"  segmento: {ficha(segmento)['titulo']} (rateio: {ficha(segmento)['rateio']['direcionador']})")
    print(f"  modelos de planilha em {pasta / 'modelos'}")
    print("\nPronto. Para subir o escritório:")
    print(f"  python -m fin_mas serve --instalacao {pasta}")
    print(f"  abra http://127.0.0.1:{args.porta} e entre com a conta criada")
    print(f"Diagnóstico a qualquer momento: python -m fin_mas doctor --pasta {pasta}")
    return 0


def ler_instalacao(pasta) -> dict:
    """Configuração gravada pelo `instalar` (para o `serve --instalacao`)."""
    arquivo = Path(pasta) / "instalacao.json"
    if not arquivo.exists():
        raise SystemExit(f"{arquivo} não existe: rode `python -m fin_mas instalar --pasta {pasta}`")
    return json.loads(arquivo.read_text(encoding="utf-8"))


def _item(nome, situacao, detalhe) -> dict:
    return {"item": nome, "situacao": situacao, "detalhe": detalhe}


def diagnosticar(pasta) -> list[dict]:
    pasta, itens = Path(pasta), []
    v = sys.version_info
    itens.append(_item("Python", "ok" if v >= (3, 11) else "erro", f"{v.major}.{v.minor}.{v.micro} (exige 3.11 ou mais novo)"))
    for modulo, opcional, para in (("yaml", False, "modelos"), ("openpyxl", False, "planilhas"),
                                   ("textual", True, 'console de administração: pip install "fin-mas[tui]"'),
                                   ("anthropic", True, 'provedor Claude: pip install "fin-mas[llm]"')):
        tem = importlib.util.find_spec(modulo) is not None
        itens.append(_item(f"biblioteca {modulo}", "ok" if tem else ("aviso" if opcional else "erro"),
                           "instalada" if tem else f"ausente ({'opcional; ' if opcional else ''}{para})"))
    modelos = sorted(models_dir().glob("*.yaml"))
    itens.append(_item("modelos YAML", "ok" if len(modelos) >= 14 else "erro",
                       f"{len(modelos)} arquivo(s) em {models_dir()} ({origem()})"))
    dist = web_dist() / "index.html"
    itens.append(_item("dashboard construído", "ok" if dist.exists() else "aviso",
                       str(dist.parent) if dist.exists() else "ausente: rode `cd web && bun install && bun run build`"))
    chaves = pasta_de_chaves()
    try:
        chaves.mkdir(parents=True, exist_ok=True)
        teste = chaves / ".doctor"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        itens.append(_item("pasta de chaves", "ok", f"{chaves} (gravável; fora da pasta de dados)"))
    except OSError as erro:
        itens.append(_item("pasta de chaves", "erro", f"{chaves}: {erro}"))
    instalacao = pasta / "instalacao.json"
    if instalacao.exists():
        c = json.loads(instalacao.read_text(encoding="utf-8"))
        itens.append(_item("instalação", "ok", f"porte {c['porte']}, cognição {c['cognicao']}, porta {c['porta']}, "
                                               f"segmento {c.get('segmento', SEGMENTO_PADRAO)}"))
        with socket.socket() as s:
            livre = s.connect_ex(("127.0.0.1", c["porta"])) != 0
        itens.append(_item("porta", "ok" if livre else "aviso",
                           f"{c['porta']} livre" if livre else f"{c['porta']} em uso (o servidor já está rodando?)"))
    else:
        itens.append(_item("instalação", "aviso", f"{instalacao} ausente: rode `python -m fin_mas instalar`"))
    if not (pasta / "acesso").exists():  # nada instalado: não cria chave nem cadastro só para diagnosticar
        itens.append(_item("cadastro de acesso", "aviso", f"{pasta / 'acesso'} ausente: rode `python -m fin_mas instalar`"))
        return itens + _chaves_de_llm()
    try:
        acesso = Acesso(pasta / "acesso")
        contas = acesso.contas()
        adms = [c["usuario"] for c in contas if "ROLE-ADM" in c["papeis"] and c["estado"] == "ativa"]
        itens.append(_item("cadastro de acesso", "ok" if adms else ("aviso" if not contas else "erro"),
                           f"{len(contas)} conta(s), administrador(es) ativo(s): {', '.join(adms) or 'nenhum'}"))
        com_2fa = [c["usuario"] for c in contas if c["segundo_fator"]["ativo"]]
        try:  # conta com segundo fator ativo e sem o segredo no cofre não entra (ex.: restaurada sem o cofre)
            orfas = [u for u in com_2fa if not acesso.cofre.existe(f"totp:{u}")]
            itens.append(_item("segundo fator no cofre", "aviso" if orfas else "ok",
                               f"conta(s) com segundo fator ativo sem o segredo no cofre: {', '.join(orfas)} (não "
                               "entram; restaure o cofre com o pacote de chaves ou peça ao administrador para "
                               "redefinir o segundo fator)" if orfas else
                               f"{len(com_2fa)} conta(s) com segundo fator, todas com o segredo no cofre"))
        except ArquivoComprometido as erro:
            itens.append(_item("segundo fator no cofre", "erro", f"cofre comprometido: {erro}"))
        resumo = acesso.trilha.verificar()
        itens.append(_item("trilha de acesso", "ok", f"íntegra, {resumo['registros']} registro(s)"))
    except AcessoNegado as erro:
        itens.append(_item("cadastro de acesso", "erro", str(erro)))
    except Exception as erro:  # trilha adulterada ou ilegível
        itens.append(_item("trilha de acesso", "erro", str(erro)))
    return itens + _chaves_de_llm()


def _chaves_de_llm() -> list[dict]:
    return [_item(f"chave de LLM ({p['id']})", "ok" if p["tem_chave"] else "aviso",
                  f"{p['variavel_chave']} {'definida' if p['tem_chave'] else 'ausente (o LLM é opcional)'}")
            for p in provedores.situacao() if p["variavel_chave"] and not p["chave_opcional"]]


def doctor(args) -> int:
    itens = diagnosticar(args.pasta)
    if args.json:
        print(json.dumps(itens, ensure_ascii=False, indent=2))
    else:
        marca = {"ok": "ok   ", "aviso": "AVISO", "erro": "ERRO "}
        for i in itens:
            print(f"[{marca[i['situacao']]}] {i['item']:<28} {i['detalhe']}")
        erros = sum(i["situacao"] == "erro" for i in itens)
        avisos = sum(i["situacao"] == "aviso" for i in itens)
        print(f"{erros} erro(s), {avisos} aviso(s)")
    return 1 if any(i["situacao"] == "erro" for i in itens) else 0

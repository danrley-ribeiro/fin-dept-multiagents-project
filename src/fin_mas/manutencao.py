"""Backup, restauração e migração da pasta de dados (DSM4, implantação).

    fin-mas backup --pasta dados --para backup.zip [--chaves-para backup.chaves.zip]
    fin-mas restaurar backup.zip --pasta dados-restaurados [--chaves backup.chaves.zip]
    fin-mas migrar --pasta dados [--simular]

**Backup.** Um `.zip` com `manifesto.json` e a pasta de dados em `dados/`. O manifesto lista cada
arquivo com SHA-256 e tamanho, e quais arquivos de estado (chave, contador, cabeça da trilha) ele tem
na pasta de chaves. O manifesto é **selado** com HMAC por uma chave de backup que fica, como as
outras, fora da pasta de dados (`FIN_MAS_DIR_CHAVES`): trocar um arquivo e corrigir o hash no
manifesto não passa. As chaves só saem se pedidas, num **arquivo separado** (`--chaves-para`,
modo 0600): quem tem só o zip de dados não consegue forjar nada, e o zip de chaves deve ser
guardado em outro lugar.

**Restauração** (falha fechada; nada é gravado no destino antes de tudo conferir):
1. o zip só pode ter o manifesto e `dados/...` (sem caminhos absolutos nem `..`);
2. o selo do manifesto confere com a chave de backup (do `--chaves` ou, na mesma máquina, da
   pasta de chaves) e cada arquivo confere com o hash e o tamanho do manifesto;
3. numa pasta temporária, com uma pasta de chaves temporária, os arquivos selados são lidos pelas
   classes de sempre: `ArquivoSelado` (selo e versão), `TrilhaAcesso.verificar()` (cadeia e cabeça)
   e `Memoria` (selo e assinaturas). Arquivo selado sem chave é recusado;
4. só então os dados vão para a pasta nova e as chaves são religadas a ela.

**Por que religar a chave é seguro.** Os arquivos de estado se chamam
`<rotulo>-<sha256(caminho absoluto)[:16]>.<sufixo>` (`services/selado.py::_estado`): o caminho
entra no **nome**, para cada arquivo ter a sua chave e o seu contador, mas o segredo é o
**conteúdo**. Restaurar em outra pasta copia o mesmo conteúdo para o nome derivado do caminho
novo, e isso só acontece depois de os selos conferirem com a chave original (não dá para usar a
restauração para aceitar dados forjados). A restauração se recusa se já houver estado para algum
caminho de destino: restaurar por cima de uma instalação viva seria um rollback, exatamente o
que o contador fora da pasta existe para impedir. A pasta e as chaves de origem não são tocadas.

**Migração.** Os arquivos selados têm versão de formato (`ArquivoSelado.versao`; hoje 1 nos dois
cadastros do SVC-IAM). `migrar` confere o selo na versão em que o arquivo está, aplica em cadeia as
funções registradas em `MIGRACOES[(rotulo, versao)]` até `VERSOES_ATUAIS[rotulo]` e grava selado na
versão nova, com contador novo, dentro da trava. Hoje não há o que migrar: `MIGRACOES` está vazio e
todos os arquivos estão na versão atual. A memória do SVC-MEM (versão 4) não tem migração possível:
os pseudônimos são HMAC sem volta e as chaves de reincidência de outra versão não são reconstruíveis
(`services/memoria.py`); arquivo de outra versão fica comprometido e uma memória nova é iniciada.
"""
import base64
import contextlib
import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fin_mas import __version__
from fin_mas.services.selado import ArquivoComprometido, ArquivoSelado, chave_de, pasta_de_chaves, trava

FORMATO = "fin-mas-backup"
VERSAO_FORMATO = 1
IGNORAR = (".lock", ".tmp")  # trava e gravação em andamento: não são dados
MANIFESTO = "manifesto.json"
MANIFESTO_CHAVES = "manifesto-chaves.json"
ROTULO_BACKUP = "backup"

# Migrações de formato dos arquivos selados: (rotulo, versão de origem) -> função(dados) -> dados da versão +1.
MIGRACOES: dict = {}
VERSOES_ATUAIS: dict = {}  # rotulo -> versão atual; preenchido a partir dos serviços em _versoes_atuais()


class BackupRecusado(RuntimeError):
    """O backup não pôde ser conferido (adulterado, incompleto ou sem chave): nada foi restaurado."""


def _marca(caminho) -> str:
    """Mesma regra de `services/selado.py::_estado`: o caminho absoluto entra no nome do estado."""
    return hashlib.sha256(str(Path(caminho).resolve()).encode("utf-8")).hexdigest()[:16]


def _estados(caminho, chaves: Path | None = None) -> dict[str, bytes]:
    """Arquivos de estado de um arquivo de dados na pasta de chaves: {"<rotulo>.<sufixo>": conteúdo}."""
    pasta = chaves or pasta_de_chaves()
    marca, achados = _marca(caminho), {}
    if not pasta.is_dir():
        return achados
    for arquivo in sorted(pasta.glob(f"*-{marca}.*")):
        rotulo, _, resto = arquivo.name.rpartition(f"-{marca}.")
        achados[f"{rotulo}.{resto}"] = arquivo.read_bytes()
    return achados


def _canonico(dados) -> bytes:
    return json.dumps(dados, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _arquivos(pasta: Path) -> list[Path]:
    chaves = pasta_de_chaves().resolve()
    return [a for a in sorted(pasta.rglob("*")) if a.is_file() and not a.name.endswith(IGNORAR)
            and chaves not in a.resolve().parents]


# ---------------------------------------------------------------------------------------------- backup
def backup(pasta, destino, chaves_para=None) -> dict:
    pasta = Path(pasta).resolve()
    if not pasta.is_dir():
        raise FileNotFoundError(f"pasta de dados não existe: {pasta}")
    itens, conteudos, estados = [], {}, {}
    for arquivo in _arquivos(pasta):
        rel = arquivo.relative_to(pasta).as_posix()
        if arquivo.suffix in (".json", ".jsonl"):  # selado: lê dentro da trava, sem gravação no meio
            with trava(arquivo):
                bruto = arquivo.read_bytes()
        else:
            bruto = arquivo.read_bytes()
        conteudos[rel] = bruto
        estados[rel] = _estados(arquivo)
        itens.append({"caminho": rel, "sha256": hashlib.sha256(bruto).hexdigest(), "tamanho": len(bruto),
                      "estado": sorted(estados[rel])})
    manifesto = {"formato": FORMATO, "versao_formato": VERSAO_FORMATO, "versao_sistema": __version__,
                 "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "origem": str(pasta),
                 "arquivos": itens}
    chave = chave_de(ROTULO_BACKUP, pasta)
    selo = hmac.new(chave, _canonico(manifesto), hashlib.sha256).hexdigest()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFESTO, json.dumps({"manifesto": manifesto, "selo": selo}, ensure_ascii=False, indent=1))
        for rel, bruto in conteudos.items():
            z.writestr(f"dados/{rel}", bruto)
    resumo = {"arquivo": str(destino), "arquivos": len(itens), "selados": sum(1 for i in itens if i["estado"]),
              "origem": str(pasta), "chaves": None}
    if chaves_para:
        alvo = Path(chaves_para)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        corpo = {"formato": FORMATO + "-chaves", "versao_formato": VERSAO_FORMATO, "origem": str(pasta),
                 "backup": base64.b64encode(chave).decode("ascii"),
                 "estados": {rel: {nome: base64.b64encode(b).decode("ascii") for nome, b in e.items()}
                             for rel, e in estados.items() if e}}
        with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(MANIFESTO_CHAVES, json.dumps(corpo, ensure_ascii=False))
        with contextlib.suppress(OSError):
            os.chmod(alvo, 0o600)
        resumo["chaves"] = str(alvo)
    return resumo


# ----------------------------------------------------------------------------------------- restauração
def _nome_seguro(nome: str) -> bool:
    p = PurePosixPath(nome)
    return not (p.is_absolute() or ".." in p.parts or "\\" in nome or ":" in p.parts[0])


def _ler_backup(arquivo) -> tuple[dict, str, dict[str, bytes]]:
    try:
        z = zipfile.ZipFile(arquivo)
    except (OSError, zipfile.BadZipFile) as erro:
        raise BackupRecusado(f"{arquivo}: não é um backup legível ({erro})") from None
    with z:
        nomes = z.namelist()
        if MANIFESTO not in nomes:
            raise BackupRecusado("backup sem manifesto.json")
        estranhos = [n for n in nomes if n != MANIFESTO and not (n.startswith("dados/") and _nome_seguro(n))]
        if estranhos:
            raise BackupRecusado(f"backup com entradas fora do formato: {', '.join(estranhos[:3])}")
        try:
            corpo = json.loads(z.read(MANIFESTO))
            manifesto, selo = corpo["manifesto"], corpo["selo"]
        except (ValueError, KeyError, TypeError):
            raise BackupRecusado("manifesto ilegível") from None
        dados = {n[len("dados/"):]: z.read(n) for n in nomes if n.startswith("dados/") and not n.endswith("/")}
    if manifesto.get("formato") != FORMATO or manifesto.get("versao_formato") != VERSAO_FORMATO:
        raise BackupRecusado(f"formato de backup não reconhecido: {manifesto.get('formato')} "
                             f"v{manifesto.get('versao_formato')}")
    return manifesto, selo, dados


def _ler_chaves(arquivo, origem: str) -> tuple[bytes, dict]:
    try:
        with zipfile.ZipFile(arquivo) as z:
            corpo = json.loads(z.read(MANIFESTO_CHAVES))
        if corpo.get("origem") != origem:
            raise BackupRecusado(f"o arquivo de chaves é de outra pasta ({corpo.get('origem')}), não de {origem}")
        return (base64.b64decode(corpo["backup"]),
                {rel: {n: base64.b64decode(b) for n, b in e.items()} for rel, e in corpo["estados"].items()})
    except BackupRecusado:
        raise
    except (OSError, zipfile.BadZipFile, ValueError, KeyError, TypeError) as erro:
        raise BackupRecusado(f"arquivo de chaves ilegível: {erro}") from None


def _chaves_locais(manifesto) -> tuple[bytes, dict]:
    """Mesma máquina: as chaves da pasta de origem ainda estão na pasta de chaves."""
    origem = Path(manifesto["origem"])
    arquivo = pasta_de_chaves() / f"{ROTULO_BACKUP}-{_marca(origem)}.chave"
    if not arquivo.exists():
        raise BackupRecusado("a chave deste backup não está nesta máquina: informe o arquivo de chaves (--chaves)")
    return arquivo.read_bytes(), {i["caminho"]: _estados(origem / i["caminho"]) for i in manifesto["arquivos"]}


@contextlib.contextmanager
def _pasta_de_chaves_temporaria(pasta: Path):
    anterior = os.environ.get("FIN_MAS_DIR_CHAVES")
    os.environ["FIN_MAS_DIR_CHAVES"] = str(pasta)
    try:
        yield
    finally:
        if anterior is None:
            os.environ.pop("FIN_MAS_DIR_CHAVES", None)
        else:
            os.environ["FIN_MAS_DIR_CHAVES"] = anterior


def _gravar_estados(base: Path, chaves: Path, estados: dict) -> list[Path]:
    """Religa os arquivos de estado aos caminhos de `base` (nome derivado do caminho novo)."""
    alvos = []
    for rel, e in estados.items():
        marca = _marca(base / rel)
        for nome, conteudo in e.items():
            rotulo, _, sufixo = nome.rpartition(".")
            alvos.append((chaves / f"{rotulo}-{marca}.{sufixo}", conteudo))
    ocupados = [a for a, _ in alvos if a.exists()]
    if ocupados:
        raise BackupRecusado(f"já existe estado de integridade para a pasta de destino ({ocupados[0].name}): "
                             "restaurar por cima de uma instalação seria um rollback; use uma pasta nova")
    chaves.mkdir(parents=True, exist_ok=True)
    for alvo, conteudo in alvos:
        alvo.write_bytes(conteudo)
        if alvo.suffix == ".chave":
            with contextlib.suppress(OSError):
                os.chmod(alvo, 0o600)
    return [a for a, _ in alvos]


def conferir_selados(base: Path, estados: dict) -> list[str]:
    """Lê cada arquivo selado com as classes do sistema (pasta de chaves já apontada). Devolve o que conferiu."""
    from fin_mas.services.audit import AuditLog
    from fin_mas.services.memoria import Memoria
    from fin_mas.services.trilha import TrilhaAcesso, TrilhaAdulterada
    conferidos = []
    for arquivo in sorted(p for p in base.rglob("*") if p.is_file()):
        rel = arquivo.relative_to(base).as_posix()
        rotulos = {n.rpartition(".")[0] for n in estados.get(rel, {})}
        if arquivo.suffix == ".jsonl" and "trilha" in rotulos:
            try:
                TrilhaAcesso(arquivo).verificar()
            except (TrilhaAdulterada, ValueError) as erro:
                raise BackupRecusado(f"{rel}: {erro}") from None
            conferidos.append(f"{rel} (cadeia e cabeça da trilha)")
            continue
        if arquivo.suffix != ".json":
            continue
        try:
            bruto = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not (isinstance(bruto, dict) and "selo" in bruto and "contador" in bruto):
            continue  # JSON comum (ex.: instalacao.json): vale o hash do manifesto
        if not rotulos:
            raise BackupRecusado(f"{rel}: arquivo selado sem a chave correspondente; não há como conferir o selo")
        if "dados" in bruto:
            rotulo = next(r for r in sorted(rotulos))
            try:
                ArquivoSelado(arquivo, rotulo, bruto.get("versao"), {}).ler()
            except ArquivoComprometido as erro:
                raise BackupRecusado(f"{rel}: {erro}") from None
            conferidos.append(f"{rel} (selo de {rotulo}, versão {bruto.get('versao')})")
        elif "entradas" in bruto:
            memoria = Memoria(AuditLog(), lambda: 0, caminho=arquivo)
            if not memoria.integra:
                raise BackupRecusado(f"{rel}: memória comprometida: {memoria.comprometida}")
            conferidos.append(f"{rel} (selo e assinaturas da memória)")
    return conferidos


def restaurar(arquivo, pasta_nova, chaves=None) -> dict:
    destino = Path(pasta_nova).resolve()
    if destino.exists() and any(destino.iterdir()):
        raise BackupRecusado(f"a pasta de destino {destino} não está vazia: restaure numa pasta nova")
    manifesto, selo, dados = _ler_backup(arquivo)
    chave, estados = _ler_chaves(chaves, manifesto["origem"]) if chaves else _chaves_locais(manifesto)
    if not hmac.compare_digest(str(selo), hmac.new(chave, _canonico(manifesto), hashlib.sha256).hexdigest()):
        raise BackupRecusado("selo do manifesto não confere: backup alterado ou chave de outro backup")
    esperado = {i["caminho"]: i for i in manifesto["arquivos"]}
    if set(dados) != set(esperado):
        sobra, falta = sorted(set(dados) - set(esperado)), sorted(set(esperado) - set(dados))
        raise BackupRecusado(f"conteúdo diferente do manifesto (a mais: {sobra[:3]}; faltando: {falta[:3]})")
    for rel, bruto in dados.items():
        if hashlib.sha256(bruto).hexdigest() != esperado[rel]["sha256"] or len(bruto) != esperado[rel]["tamanho"]:
            raise BackupRecusado(f"{rel}: conteúdo não confere com o hash do manifesto (arquivo alterado)")
        if sorted(estados.get(rel, {})) != esperado[rel]["estado"]:
            raise BackupRecusado(f"{rel}: chaves ausentes ou diferentes das registradas no backup")
    with tempfile.TemporaryDirectory(prefix="fin-mas-restaurar-") as tmp:
        ensaio, chaves_ensaio = Path(tmp) / "dados", Path(tmp) / "chaves"
        for rel, bruto in dados.items():
            (ensaio / rel).parent.mkdir(parents=True, exist_ok=True)
            (ensaio / rel).write_bytes(bruto)
        _gravar_estados(ensaio, chaves_ensaio, estados)
        with _pasta_de_chaves_temporaria(chaves_ensaio):
            conferidos = conferir_selados(ensaio, estados)
        # tudo conferiu: grava no destino e religa as chaves ao caminho novo
        gravados = _gravar_estados(destino, pasta_de_chaves(), estados)  # recusa se o destino já tiver estado
        try:
            destino.mkdir(parents=True, exist_ok=True)
            for rel, bruto in dados.items():
                (destino / rel).parent.mkdir(parents=True, exist_ok=True)
                (destino / rel).write_bytes(bruto)
            conferir_selados(destino, estados)  # mesma leitura, agora com as chaves reais
        except Exception:
            for g in gravados:
                with contextlib.suppress(OSError):
                    g.unlink()
            shutil.rmtree(destino, ignore_errors=True)
            raise
    return {"pasta": str(destino), "origem": manifesto["origem"], "arquivos": len(dados), "conferidos": conferidos,
            "criado_em": manifesto["criado_em"], "versao_sistema": manifesto["versao_sistema"]}


# --------------------------------------------------------------------------------------------- migração
def _versoes_atuais() -> dict:
    from fin_mas.services import iam
    return {"acesso-contas": iam.VERSAO, "acesso-sessoes": iam.VERSAO, **VERSOES_ATUAIS}


def migrar(pasta, simular=False) -> list[dict]:
    pasta, atuais, relatorio = Path(pasta).resolve(), _versoes_atuais(), []
    for arquivo in _arquivos(pasta):
        if arquivo.suffix != ".json":
            continue
        try:
            bruto = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not (isinstance(bruto, dict) and {"versao", "contador", "selo"} <= set(bruto)):
            continue
        rel = arquivo.relative_to(pasta).as_posix()
        rotulos = sorted({n.rpartition(".")[0] for n in _estados(arquivo)})
        rotulo = rotulos[0] if rotulos else None
        de = bruto["versao"]
        item = {"arquivo": rel, "rotulo": rotulo, "de": de, "para": atuais.get(rotulo, de)}
        if "dados" not in bruto or rotulo not in atuais:
            relatorio.append({**item, "situacao": "sem migração (formato sem migrador; ver docstring)"})
            continue
        alvo = atuais[rotulo]
        if de == alvo:
            relatorio.append({**item, "situacao": "na versão atual"})
            continue
        if de > alvo:
            relatorio.append({**item, "situacao": f"ERRO: versão {de} é mais nova que a deste sistema ({alvo})"})
            continue
        faltando = [v for v in range(de, alvo) if (rotulo, v) not in MIGRACOES]
        if faltando:
            relatorio.append({**item, "situacao": f"ERRO: não há migração de {rotulo} v{faltando[0]}"})
            continue
        if simular:
            relatorio.append({**item, "situacao": f"migraria v{de} -> v{alvo}"})
            continue
        with trava(arquivo):
            antigo = ArquivoSelado(arquivo, rotulo, de, {})
            try:
                dados = antigo.ler()  # selo e contador conferidos na versão de origem
            except ArquivoComprometido as erro:
                relatorio.append({**item, "situacao": f"ERRO: {erro}"})
                continue
            for v in range(de, alvo):
                dados = MIGRACOES[(rotulo, v)](dados)
            novo = ArquivoSelado(arquivo, rotulo, alvo, {})
            contador = max(antigo._contador, novo._ultimo_contador()) + 1
            temporario = arquivo.with_suffix(arquivo.suffix + ".tmp")
            temporario.write_text(json.dumps({"versao": alvo, "contador": contador, "dados": dados,
                                              "selo": novo._selo(contador, dados)},
                                             ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
            os.replace(temporario, arquivo)
            from fin_mas.services.selado import _estado
            _estado(rotulo, arquivo, "contador").write_text(str(contador), encoding="utf-8")
        relatorio.append({**item, "situacao": f"migrado v{de} -> v{alvo}"})
    return relatorio


# ------------------------------------------------------------------------------------------------- CLI
def configurar(sub) -> None:
    b = sub.add_parser("backup", help="copia a pasta de dados para um .zip com manifesto selado")
    b.add_argument("--pasta", default="dados", help="pasta de dados (padrão: dados)")
    b.add_argument("--para", required=True, metavar="ARQ.zip")
    b.add_argument("--chaves-para", default=None, metavar="ARQ.chaves.zip",
                   help="também exporta as chaves, num arquivo separado (guarde em outro lugar)")
    r = sub.add_parser("restaurar", help="confere e restaura um backup numa pasta nova")
    r.add_argument("arquivo", metavar="ARQ.zip")
    r.add_argument("--pasta", required=True, help="pasta nova (vazia ou inexistente)")
    r.add_argument("--chaves", default=None, metavar="ARQ.chaves.zip", help="chaves exportadas no backup")
    m = sub.add_parser("migrar", help="migra os arquivos selados para a versão de formato deste sistema")
    m.add_argument("--pasta", default="dados")
    m.add_argument("--simular", action="store_true", help="só mostra o que seria migrado")


def executar(args) -> int:
    if args.comando == "backup":
        try:
            r = backup(args.pasta, args.para, args.chaves_para)
        except (FileNotFoundError, ArquivoComprometido) as erro:
            print(f"backup não feito: {erro}", file=sys.stderr)
            return 2
        print(f"backup: {r['arquivo']} ({r['arquivos']} arquivo(s), {r['selados']} com chave de integridade)")
        print(f"origem: {r['origem']}; manifesto selado com a chave de backup (fora da pasta de dados)")
        if r["chaves"]:
            print(f"chaves: {r['chaves']} (guarde separado do backup; quem tem as duas coisas tem tudo)")
        return 0
    if args.comando == "restaurar":
        try:
            r = restaurar(args.arquivo, args.pasta, args.chaves)
        except (BackupRecusado, FileNotFoundError) as erro:
            print(f"BACKUP RECUSADO: {erro}", file=sys.stderr)
            return 3
        print(f"restaurado em {r['pasta']}: {r['arquivos']} arquivo(s) de {r['origem']} ({r['criado_em']}, "
              f"versão {r['versao_sistema']})")
        for c in r["conferidos"]:
            print(f"  conferido: {c}")
        print(f"suba com: fin-mas serve --instalacao {r['pasta']}   (diagnóstico: fin-mas doctor --pasta {r['pasta']})")
        return 0
    relatorio = migrar(args.pasta, args.simular)
    for i in relatorio:
        print(f"{i['arquivo']:<28} {str(i['rotulo']):<16} v{i['de']} -> v{i['para']}: {i['situacao']}")
    erros = sum(i["situacao"].startswith("ERRO") for i in relatorio)
    print(f"{len(relatorio)} arquivo(s) selado(s); {erros} erro(s)" + (" (simulação)" if args.simular else ""))
    return 1 if erros else 0

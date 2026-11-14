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
1. o zip só pode ter o manifesto e `dados/<relativo>`: sem absoluto, `//`, `.`, `..`, barra invertida ou
   unidade; o manifesto inteiro tem a estrutura conferida (torto é recusado) e declara o tamanho
   descompactado (limite de 1 GiB), conferido em fluxo na extração; nenhuma entrada é descompactada
   antes de o selo conferir, e a extração só grava dentro da pasta de ensaio;
2. o selo do manifesto confere com a chave de backup (do `--chaves` ou, na mesma máquina, da
   pasta de chaves) e cada arquivo confere com o hash e o tamanho do manifesto;
3. numa pasta temporária, com uma pasta de chaves temporária, os arquivos selados são lidos pelas
   classes de sempre: `ArquivoSelado` (selo e versão), `TrilhaAcesso.verificar()` (cadeia e cabeça)
   e `Memoria` (selo e assinaturas). Arquivo selado sem chave é recusado;
4. só então os dados vão para a pasta nova e as chaves são religadas a ela (os nomes de estado do pacote
   de chaves são só `<rótulo>.<sufixo>`, gravados com `O_EXCL` dentro da pasta de chaves).

**Cofres.** Os cofres selados ligados a pastas da instalação (o do cadastro de acesso, com os segredos
do segundo fator e as chaves de LLM, e os das fontes, com as credenciais de conector) ficam na pasta
de chaves; o manifesto lista quais existem e o pacote de chaves os leva, com o estado deles. Na
restauração cada cofre é conferido (selo e contador) e religado à pasta nova, com o mesmo cuidado de
rollback; um cofre declarado e ausente recusa o backup. O backup não segue link simbólico para fora
da pasta de dados.

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
import re
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


def _dentro(base: Path, alvo: Path) -> bool:
    base, alvo = Path(base).resolve(), Path(alvo).resolve()
    return alvo == base or base in alvo.parents


def _arquivos(pasta: Path) -> list[Path]:
    """Arquivos da pasta de dados. Link simbólico para fora da pasta não entra (o backup não segue o link)."""
    chaves = pasta_de_chaves().resolve()
    return [a for a in sorted(pasta.rglob("*")) if a.is_file() and not a.name.endswith(IGNORAR)
            and chaves not in a.resolve().parents and _dentro(pasta, a)]


def _pastas(pasta: Path) -> list[Path]:
    """A pasta de dados e as subpastas (sem seguir link): onde um cofre selado pode estar vinculado."""
    return [pasta] + [d for d in sorted(pasta.rglob("*")) if d.is_dir() and not d.is_symlink() and _dentro(pasta, d)]


def _cofres(pasta: Path) -> dict[str, Path]:
    """Cofres selados ligados a pastas da instalação (`services/cofre.py::caminho_padrao`): o do cadastro de acesso
    (chaves de LLM, segredos do segundo fator) e os das fontes (credenciais de conector). Ficam na pasta de chaves."""
    from fin_mas.services.cofre import caminho_padrao
    achados = {}
    for d in _pastas(pasta):
        cofre = caminho_padrao(d)
        if cofre.is_file():
            achados["." if d == pasta else d.relative_to(pasta).as_posix()] = cofre
    return achados


# ---------------------------------------------------------------------------------------------- backup
def backup(pasta, destino, chaves_para=None) -> dict:
    pasta = Path(pasta).resolve()
    if not pasta.is_dir():
        raise FileNotFoundError(f"pasta de dados não existe: {pasta}")
    itens, estados = [], {}
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cofres = _cofres(pasta)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for arquivo in _arquivos(pasta):
            rel = arquivo.relative_to(pasta).as_posix()
            if arquivo.suffix in (".json", ".jsonl"):  # selado: lê dentro da trava, sem gravação no meio
                with trava(arquivo):
                    bruto = arquivo.read_bytes()
            else:
                bruto = arquivo.read_bytes()
            z.writestr(f"dados/{rel}", bruto)
            estados[rel] = _estados(arquivo)
            itens.append({"caminho": rel, "sha256": hashlib.sha256(bruto).hexdigest(), "tamanho": len(bruto),
                          "estado": sorted(estados[rel])})
        manifesto = {"formato": FORMATO, "versao_formato": VERSAO_FORMATO, "versao_sistema": __version__,
                     "criado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"), "origem": str(pasta),
                     "arquivos": itens, "total": sum(i["tamanho"] for i in itens), "cofres": sorted(cofres)}
        chave = chave_de(ROTULO_BACKUP, pasta)
        selo = hmac.new(chave, _canonico(manifesto), hashlib.sha256).hexdigest()
        z.writestr(MANIFESTO, json.dumps({"manifesto": manifesto, "selo": selo}, ensure_ascii=False, indent=1))
    resumo = {"arquivo": str(destino), "arquivos": len(itens), "selados": sum(1 for i in itens if i["estado"]),
              "origem": str(pasta), "chaves": None, "cofres": len(cofres)}
    if chaves_para:
        alvo = Path(chaves_para)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        pacote_cofres = {}
        for rel_dir, cofre in cofres.items():  # o cofre só viaja no pacote de chaves, nunca no zip de dados
            with trava(cofre):
                conteudo = cofre.read_bytes()
            pacote_cofres[rel_dir] = {"arquivo": base64.b64encode(conteudo).decode("ascii"),
                                      "estados": {n: base64.b64encode(b).decode("ascii")
                                                  for n, b in _estados(cofre).items()}}
        corpo = {"formato": FORMATO + "-chaves", "versao_formato": VERSAO_FORMATO, "origem": str(pasta),
                 "backup": base64.b64encode(chave).decode("ascii"),
                 "estados": {rel: {nome: base64.b64encode(b).decode("ascii") for nome, b in e.items()}
                             for rel, e in estados.items() if e},
                 "cofres": pacote_cofres}
        with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(MANIFESTO_CHAVES, json.dumps(corpo, ensure_ascii=False))
        with contextlib.suppress(OSError):
            os.chmod(alvo, 0o600)
        resumo["chaves"] = str(alvo)
    return resumo


# ----------------------------------------------------------------------------------------- restauração
LIMITE_DESCOMPACTADO = 1 << 30  # soma dos tamanhos declarada no manifesto e conferida na leitura (em fluxo)
LIMITE_MANIFESTO = 16 << 20
MAX_ENTRADAS = 100_000
SUFIXOS_ESTADO = ("chave", "contador", "cabeca")
ROTULO = re.compile(r"^[a-z][a-z0-9_-]{0,47}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _rel_seguro(rel) -> bool:
    """Caminho relativo normalizado: sem absoluto, sem vazio (`//`), sem `.`/`..`, sem barra invertida, unidade
    ou NUL."""
    if not isinstance(rel, str) or not rel or len(rel) > 1024 or "\\" in rel or "\0" in rel:
        return False
    partes = rel.split("/")
    return not (rel.startswith("/") or any(p in ("", ".", "..") for p in partes) or ":" in partes[0]
                or PurePosixPath(rel).is_absolute())


def _nome_seguro(nome: str) -> bool:
    """Entrada `dados/<relativo seguro>` do zip (pasta: com `/` no fim)."""
    return isinstance(nome, str) and nome.startswith("dados/") and _rel_seguro(nome[len("dados/"):].rstrip("/") or "")


def _estado_seguro(nome) -> bool:
    """Nome de um arquivo de estado no pacote de chaves: `<rótulo>.<sufixo>` e nada mais (sem caminho)."""
    if not isinstance(nome, str):
        return False
    rotulo, _, sufixo = nome.rpartition(".")
    return bool(ROTULO.match(rotulo)) and sufixo in SUFIXOS_ESTADO


def _validar_manifesto(corpo) -> tuple[dict, str]:
    """Estrutura do manifesto inteira conferida antes de qualquer uso: manifesto torto vira BACKUP RECUSADO."""
    if not isinstance(corpo, dict) or not isinstance(corpo.get("manifesto"), dict) or not isinstance(corpo.get("selo"), str):
        raise BackupRecusado("manifesto ilegível (esperado {manifesto: {...}, selo: texto})")
    manifesto, selo = corpo["manifesto"], corpo["selo"]
    if manifesto.get("formato") != FORMATO or manifesto.get("versao_formato") != VERSAO_FORMATO:
        raise BackupRecusado(f"formato de backup não reconhecido: {str(manifesto.get('formato'))[:40]} "
                             f"v{str(manifesto.get('versao_formato'))[:10]}")
    if not HEX64.match(selo):
        raise BackupRecusado("selo do manifesto não confere: fora do formato")
    for campo in ("origem", "criado_em", "versao_sistema"):
        if not isinstance(manifesto.get(campo), str):
            raise BackupRecusado(f"manifesto sem {campo}")
    arquivos = manifesto.get("arquivos")
    if not isinstance(arquivos, list) or len(arquivos) > MAX_ENTRADAS:
        raise BackupRecusado("manifesto: arquivos precisa ser uma lista")
    vistos, total = set(), 0
    for i in arquivos:
        if not (isinstance(i, dict) and _rel_seguro(i.get("caminho")) and isinstance(i.get("sha256"), str)
                and HEX64.match(i["sha256"]) and type(i.get("tamanho")) is int and i["tamanho"] >= 0
                and isinstance(i.get("estado"), list) and all(_estado_seguro(n) for n in i["estado"])):
            raise BackupRecusado(f"manifesto: item fora do formato ({str(i)[:80]})")
        if i["caminho"] in vistos:
            raise BackupRecusado(f"manifesto: caminho repetido ({i['caminho']})")
        vistos.add(i["caminho"])
        total += i["tamanho"]
    declarado = manifesto.get("total", total)
    if type(declarado) is not int or max(total, declarado) > LIMITE_DESCOMPACTADO:
        raise BackupRecusado(f"manifesto: {max(total, declarado) if type(declarado) is int else declarado!r} bytes "
                             f"descompactados (limite {LIMITE_DESCOMPACTADO})")
    cofres = manifesto.get("cofres", [])
    if not isinstance(cofres, list) or not all(c == "." or _rel_seguro(c) for c in cofres):
        raise BackupRecusado("manifesto: cofres fora do formato")
    return manifesto, selo


def _ler_limitado(z, nome, limite: int) -> bytes:
    with z.open(nome) as f:
        bruto = f.read(limite + 1)
    if len(bruto) > limite:
        raise BackupRecusado(f"{nome}: maior que o limite ({limite} bytes)")
    return bruto


def _ler_backup(z) -> tuple[dict, str, dict[str, str]]:
    """Manifesto conferido e as entradas de dados (relativo -> nome no zip); nenhum dado é descompactado aqui."""
    nomes = z.namelist()
    if len(nomes) > MAX_ENTRADAS + 1 or len(set(nomes)) != len(nomes):
        raise BackupRecusado("backup com entradas repetidas ou em excesso")
    if MANIFESTO not in nomes:
        raise BackupRecusado("backup sem manifesto.json")
    estranhos = [n for n in nomes if n != MANIFESTO and not _nome_seguro(n)]
    if estranhos:
        raise BackupRecusado(f"backup com entradas fora do formato: {', '.join(estranhos[:3])}")
    try:
        corpo = json.loads(_ler_limitado(z, MANIFESTO, LIMITE_MANIFESTO))
    except (ValueError, RecursionError, UnicodeDecodeError, zipfile.BadZipFile):
        raise BackupRecusado("manifesto ilegível") from None
    manifesto, selo = _validar_manifesto(corpo)
    return manifesto, selo, {n[len("dados/"):]: n for n in nomes if n.startswith("dados/") and not n.endswith("/")}


def _estados_validos(e) -> dict[str, bytes]:
    if not isinstance(e, dict) or not all(_estado_seguro(n) and isinstance(b, str) for n, b in e.items()):
        raise BackupRecusado("pacote de chaves: nome de estado fora do formato (<rótulo>.<sufixo>)")
    return {n: base64.b64decode(b, validate=True) for n, b in e.items()}


def _ler_chaves(arquivo, origem: str) -> tuple[bytes, dict, dict]:
    try:
        with zipfile.ZipFile(arquivo) as z:
            corpo = json.loads(_ler_limitado(z, MANIFESTO_CHAVES, LIMITE_MANIFESTO))
        if not isinstance(corpo, dict):
            raise BackupRecusado("arquivo de chaves fora do formato")
        if corpo.get("origem") != origem:
            raise BackupRecusado(f"o arquivo de chaves é de outra pasta ({str(corpo.get('origem'))[:200]}), não de {origem}")
        if not isinstance(corpo.get("estados"), dict) or not isinstance(corpo.get("cofres", {}), dict):
            raise BackupRecusado("arquivo de chaves fora do formato")
        estados = {}
        for rel, e in corpo["estados"].items():
            if not _rel_seguro(rel):
                raise BackupRecusado(f"pacote de chaves: caminho fora do formato ({str(rel)[:80]})")
            estados[rel] = _estados_validos(e)
        cofres = {}
        for rel_dir, c in corpo.get("cofres", {}).items():
            if not (rel_dir == "." or _rel_seguro(rel_dir)) or not isinstance(c, dict) or not isinstance(c.get("arquivo"), str):
                raise BackupRecusado(f"pacote de chaves: cofre fora do formato ({str(rel_dir)[:80]})")
            cofres[rel_dir] = (base64.b64decode(c["arquivo"], validate=True), _estados_validos(c.get("estados")))
        return base64.b64decode(corpo["backup"], validate=True), estados, cofres
    except BackupRecusado:
        raise
    except (OSError, zipfile.BadZipFile, ValueError, KeyError, TypeError, AttributeError, RecursionError) as erro:
        raise BackupRecusado(f"arquivo de chaves ilegível: {erro}") from None


def _chaves_locais(manifesto) -> tuple[bytes, dict, dict]:
    """Mesma máquina: as chaves e os cofres da pasta de origem ainda estão na pasta de chaves."""
    from fin_mas.services.cofre import caminho_padrao
    origem = Path(manifesto["origem"])
    arquivo = pasta_de_chaves() / f"{ROTULO_BACKUP}-{_marca(origem)}.chave"
    if not arquivo.exists():
        raise BackupRecusado("a chave deste backup não está nesta máquina: informe o arquivo de chaves (--chaves)")
    cofres = {}
    for rel_dir in manifesto.get("cofres", []):
        cofre = caminho_padrao(origem if rel_dir == "." else origem / rel_dir)
        if cofre.is_file():
            cofres[rel_dir] = (cofre.read_bytes(), _estados(cofre))
    return arquivo.read_bytes(), {i["caminho"]: _estados(origem / i["caminho"]) for i in manifesto["arquivos"]}, cofres


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


def _alvos_de_estado(base: Path, chaves: Path, estados: dict, cofres: dict) -> list[tuple[Path, bytes]]:
    """Arquivos a gravar na pasta de chaves para religar os dados de `base`: o estado de cada arquivo (nome derivado
    do caminho novo) e cada cofre (nome derivado da pasta nova) com o seu estado. Todos confinados a `chaves`."""
    alvos = []
    for rel, e in estados.items():
        marca = _marca(base / rel)
        for nome, conteudo in e.items():
            rotulo, _, sufixo = nome.rpartition(".")
            alvos.append((chaves / f"{rotulo}-{marca}.{sufixo}", conteudo))
    for rel_dir, (conteudo, e) in cofres.items():
        cofre = chaves / f"cofre-{_marca(base if rel_dir == '.' else base / rel_dir)}.json"
        alvos.append((cofre, conteudo))
        for nome, b in e.items():
            rotulo, _, sufixo = nome.rpartition(".")
            alvos.append((chaves / f"{rotulo}-{_marca(cofre)}.{sufixo}", b))
    for alvo, _ in alvos:
        if alvo.parent != chaves:
            raise BackupRecusado(f"estado fora da pasta de chaves: {alvo.name}")
    return alvos


def _gravar_estados(alvos: list[tuple[Path, bytes]], chaves: Path) -> list[Path]:
    ocupados = [a for a, _ in alvos if a.exists() or a.is_symlink()]
    if ocupados:
        raise BackupRecusado(f"já existe estado de integridade para a pasta de destino ({ocupados[0].name}): "
                             "restaurar por cima de uma instalação seria um rollback; use uma pasta nova")
    chaves.mkdir(parents=True, exist_ok=True)
    gravados = []
    try:
        for alvo, conteudo in alvos:
            fd = os.open(alvo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # nunca segue link nem sobrescreve
            with os.fdopen(fd, "wb") as f:
                f.write(conteudo)
            gravados.append(alvo)
    except OSError as erro:
        for g in gravados:
            with contextlib.suppress(OSError):
                g.unlink()
        raise BackupRecusado(f"não foi possível religar as chaves: {erro}") from None
    return gravados


def conferir_cofres(base: Path, cofres: dict) -> list[str]:
    """Cada cofre restaurado é lido pelo `Cofre` de sempre (selo e contador), com a pasta de chaves já apontada."""
    from fin_mas.services.cofre import Cofre
    conferidos = []
    for rel_dir in sorted(cofres):
        cofre = Cofre.do_cadastro(base if rel_dir == "." else base / rel_dir)
        try:
            n = len(cofre.nomes())
        except ArquivoComprometido as erro:
            raise BackupRecusado(f"cofre de {rel_dir}: {erro}") from None
        conferidos.append(f"cofre de {rel_dir} (selo, {n} segredo(s))")
    return conferidos


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
        except (ValueError, RecursionError):
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


def _extrair(z, entradas: dict, esperado: dict, ensaio: Path) -> None:
    """Descompacta em fluxo para a pasta de ensaio, conferindo o tamanho (nunca além do declarado) e o hash."""
    for rel, nome in sorted(entradas.items()):
        alvo = ensaio / rel
        if not _dentro(ensaio, alvo.parent):
            raise BackupRecusado(f"{rel}: caminho fora da pasta de destino")
        alvo.parent.mkdir(parents=True, exist_ok=True)
        h, lido, limite = hashlib.sha256(), 0, esperado[rel]["tamanho"]
        try:
            with z.open(nome) as origem, open(alvo, "xb") as f:
                while bloco := origem.read(1 << 20):
                    lido += len(bloco)
                    if lido > limite:
                        raise BackupRecusado(f"{rel}: maior que o tamanho declarado no manifesto ({limite} bytes)")
                    h.update(bloco)
                    f.write(bloco)
        except (zipfile.BadZipFile, OSError, EOFError) as erro:  # inclusive CRC que não confere
            raise BackupRecusado(f"{rel}: entrada ilegível no zip ({erro})") from None
        if lido != limite or h.hexdigest() != esperado[rel]["sha256"]:
            raise BackupRecusado(f"{rel}: conteúdo não confere com o hash do manifesto (arquivo alterado)")


def restaurar(arquivo, pasta_nova, chaves=None) -> dict:
    """Confere o backup inteiro (manifesto, selo, nomes, chaves e cofres) antes de descompactar qualquer coisa; só
    então extrai, em fluxo e com limite, numa pasta de ensaio; e só depois de tudo conferir grava no destino."""
    destino = Path(pasta_nova).resolve()
    if destino.exists() and not destino.is_dir():
        raise BackupRecusado(f"o destino {destino} existe e não é uma pasta: restaure numa pasta nova")
    if destino.exists() and any(destino.iterdir()):
        raise BackupRecusado(f"a pasta de destino {destino} não está vazia: restaure numa pasta nova")
    try:
        z = zipfile.ZipFile(arquivo)
    except (OSError, zipfile.BadZipFile) as erro:
        raise BackupRecusado(f"{arquivo}: não é um backup legível ({erro})") from None
    with z:
        manifesto, selo, entradas = _ler_backup(z)
        chave, estados, cofres = _ler_chaves(chaves, manifesto["origem"]) if chaves else _chaves_locais(manifesto)
        calculado = hmac.new(chave, _canonico(manifesto), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(selo.encode("ascii"), calculado.encode("ascii")):
            raise BackupRecusado("selo do manifesto não confere: backup alterado ou chave de outro backup")
        esperado = {i["caminho"]: i for i in manifesto["arquivos"]}
        if set(entradas) != set(esperado):
            sobra, falta = sorted(set(entradas) - set(esperado)), sorted(set(esperado) - set(entradas))
            raise BackupRecusado(f"conteúdo diferente do manifesto (a mais: {sobra[:3]}; faltando: {falta[:3]})")
        for rel in esperado:
            if sorted(estados.get(rel, {})) != esperado[rel]["estado"]:
                raise BackupRecusado(f"{rel}: chaves ausentes ou diferentes das registradas no backup")
        declarados = set(manifesto.get("cofres", []))
        if set(cofres) != declarados:
            raise BackupRecusado(f"cofre ausente ou a mais no pacote de chaves ({sorted(declarados ^ set(cofres))[:3]}): "
                                 "sem ele, segredos do segundo fator, chaves de LLM e credenciais se perderiam")
        with tempfile.TemporaryDirectory(prefix="fin-mas-restaurar-") as tmp:
            ensaio, chaves_ensaio = Path(tmp) / "dados", Path(tmp) / "chaves"
            ensaio.mkdir()
            _extrair(z, entradas, esperado, ensaio)  # tudo validado: só agora algo é descompactado (no ensaio)
            _gravar_estados(_alvos_de_estado(ensaio, chaves_ensaio, estados, cofres), chaves_ensaio)
            with _pasta_de_chaves_temporaria(chaves_ensaio):
                conferidos = conferir_selados(ensaio, estados) + conferir_cofres(ensaio, cofres)
            # tudo conferiu: grava no destino e religa as chaves e os cofres ao caminho novo
            chaves_reais = pasta_de_chaves()
            gravados = _gravar_estados(_alvos_de_estado(destino, chaves_reais, estados, cofres), chaves_reais)
            criada = not destino.exists()
            try:
                destino.mkdir(parents=True, exist_ok=True)
                for rel in sorted(esperado):
                    alvo = destino / rel
                    if not _dentro(destino, alvo.parent):
                        raise BackupRecusado(f"{rel}: caminho fora da pasta de destino")
                    alvo.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ensaio / rel, alvo)
                conferir_selados(destino, estados)  # mesma leitura, agora com as chaves reais
                conferir_cofres(destino, cofres)
            except Exception:
                for g in gravados:
                    with contextlib.suppress(OSError):
                        g.unlink()
                if criada:
                    shutil.rmtree(destino, ignore_errors=True)
                else:
                    for filho in list(destino.iterdir()):
                        shutil.rmtree(filho, ignore_errors=True) if filho.is_dir() else filho.unlink()
                raise
    return {"pasta": str(destino), "origem": manifesto["origem"], "arquivos": len(esperado), "conferidos": conferidos,
            "criado_em": manifesto["criado_em"], "versao_sistema": manifesto["versao_sistema"], "cofres": len(cofres)}


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
        print(f"backup: {r['arquivo']} ({r['arquivos']} arquivo(s), {r['selados']} com chave de integridade, "
              f"{r['cofres']} cofre(s) no pacote de chaves)")
        print(f"origem: {r['origem']}; manifesto selado com a chave de backup (fora da pasta de dados)")
        if r["chaves"]:
            print(f"chaves: {r['chaves']} (guarde separado do backup; quem tem as duas coisas tem tudo)")
        return 0
    if args.comando == "restaurar":
        try:
            r = restaurar(args.arquivo, args.pasta, args.chaves)
        except (BackupRecusado, OSError) as erro:
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

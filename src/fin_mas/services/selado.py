"""Arquivo selado: JSON versionado, íntegro e seguro para dois processos (ADR-009).

É o formato dos cadastros do SVC-IAM (contas e sessões), que a TUI de administração e o
servidor do dashboard leem e gravam ao mesmo tempo. Mesmo desenho do arquivo do SVC-MEM:

- **selo**: HMAC-SHA256 sobre (versão, contador, dados), com chave guardada **fora da pasta de
  dados** (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`, modo 0600);
- **contador**: sobe a cada gravação e também fica fora da pasta; um arquivo com contador menor
  que o último gravado é uma versão antiga recolocada no lugar (rollback) e é recusado;
- **gravação atômica**: arquivo temporário e `os.replace`;
- **trava entre processos**: arquivo `<dados>.lock` ao lado do arquivo de dados, travado pelo sistema operacional (Windows, Linux e
  macOS); toda alteração relê o arquivo dentro da trava, então duas escritas concorrentes
  nunca se sobrescrevem;
- **falha fechada**: arquivo ausente depois de já ter sido gravado, ilegível, de outra versão,
  com selo que não confere ou com contador antigo levanta `ArquivoComprometido`. Quem chama
  decide o que negar; o SVC-IAM nega toda entrada.

Sem `caminho`, os dados ficam só em memória (acesso simulado dos cenários em lote).
"""
import contextlib
import copy
import errno
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ESPERA_TRAVA = 5.0  # segundos tentando obter a trava antes de desistir


def _sem_conflito_de_acesso(operacao):
    """No Windows, abrir ou consultar o arquivo no instante em que outro processo o troca (`os.replace`) dá
    `PermissionError` por um momento: repete por até cerca de 2 s em vez de tomar o arquivo por ilegível
    (o cadastro ficava "comprometido" por uma colisão de milissegundos). Fora do Windows não acontece."""
    for tentativa in range(40):
        try:
            return operacao()
        except PermissionError:
            if tentativa == 39:
                raise
            time.sleep(0.05)


class ArquivoComprometido(RuntimeError):
    """A integridade do arquivo não pôde ser garantida."""


class TravaOcupada(RuntimeError):
    pass


def pasta_de_chaves() -> Path:
    return Path(os.environ.get("FIN_MAS_DIR_CHAVES") or Path.home() / ".fin_mas" / "chaves")


def chave_de(rotulo: str, caminho: Path) -> bytes:
    """Chave de 32 bytes do arquivo, criada no primeiro uso, fora da pasta de dados."""
    arquivo = _estado(rotulo, caminho, "chave")
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    # Criação atômica: dois processos no primeiro uso não podem gerar chaves diferentes para o mesmo arquivo
    # (um selaria com a sua e o outro acusaria "selo não confere"). Quem perde a corrida lê a chave do vencedor.
    try:
        fd = os.open(arquivo, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        for _ in range(200):  # o vencedor pode ainda estar gravando os 32 bytes
            chave = arquivo.read_bytes()
            if len(chave) >= 32:
                return chave
            time.sleep(0.01)
        raise ArquivoComprometido(f"chave de {Path(caminho).name} incompleta em {arquivo.name}") from None
    chave = secrets.token_bytes(32)
    with os.fdopen(fd, "wb") as f:
        f.write(chave)
    return chave


def marca(caminho) -> str:
    """Nome curto do arquivo de dados nos arquivos de estado (chave, contador): hash do caminho absoluto com
    `os.path.normcase`. No Windows, `MEMORIA.JSON` e `memoria.json` são o mesmo arquivo e passam a ter a mesma marca
    (antes, a grafia do caminho mudava a marca e a memória ficava "comprometida"; correção simulada da DSM4). No
    Linux e no macOS o `normcase` não muda nada."""
    return hashlib.sha256(os.path.normcase(str(Path(caminho).resolve())).encode("utf-8")).hexdigest()[:16]


def marca_legada(caminho) -> str:
    """A marca até a versão 1.1.0, sem `normcase` (lida para migrar instalações existentes)."""
    return hashlib.sha256(str(Path(caminho).resolve()).encode("utf-8")).hexdigest()[:16]


def _estado(rotulo: str, caminho: Path, sufixo: str) -> Path:
    pasta = pasta_de_chaves()
    novo = pasta / f"{rotulo}-{marca(caminho)}.{sufixo}"
    antigo = pasta / f"{rotulo}-{marca_legada(caminho)}.{sufixo}"
    if antigo != novo and not novo.exists() and antigo.exists():
        try:  # migração do nome antigo: a mesma chave e o mesmo contador, com o nome novo
            os.replace(antigo, novo)
        except OSError:
            if not novo.exists():  # outro processo migrou ao mesmo tempo, ou o arquivo está em uso: usa o antigo
                return antigo
    return novo


@contextlib.contextmanager
def trava(caminho: Path):
    """A trava pertence ao descritor aberto. O SO a libera mesmo se o processo terminar.

    O arquivo da trava fica ao lado do arquivo de dados (`memoria.json.lock`), não na pasta de chaves: dois
    processos com pastas de chaves diferentes sobre o mesmo arquivo de dados disputam a mesma trava (antes, cada um
    travava o seu arquivo e as gravações se perdiam; achado da correção simulada da DSM4). O backup ignora `.lock`."""
    caminho = Path(caminho)
    alvo = caminho.with_name(caminho.name + ".lock")
    alvo.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(alvo, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fim = time.monotonic() + ESPERA_TRAVA
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as erro:
                if erro.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= fim:
                    raise TravaOcupada(f"{caminho.name}: outro processo mantém a trava") from None
                time.sleep(0.02)
        yield
    finally:
        if os.name == "nt":  # libera já: no Windows, o desbloqueio no fechamento pode demorar (doc. da Microsoft)
            import msvcrt
            with contextlib.suppress(OSError):
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        os.close(fd)


class ArquivoSelado:
    """`modo`: permissão do arquivo gravado (ex.: 0o600 no cofre); `chave`: chave do selo vinda de fora
    (ex.: `FIN_MAS_CHAVE_MEMORIA`) em vez da chave guardada na pasta de chaves (DSM4, aditivos)."""

    def __init__(self, caminho, rotulo: str, versao: int, vazio: dict, *, modo: int | None = None,
                 chave: bytes | None = None):
        self.caminho = Path(caminho) if caminho else None
        self.rotulo, self.versao = rotulo, versao
        self.modo = modo
        self._vazio = vazio
        self._dados = copy.deepcopy(vazio)
        self._contador = 0
        self._marca = None  # (mtime_ns, tamanho) do que está em memória
        self._chave = chave or (chave_de(rotulo, self.caminho) if self.caminho else secrets.token_bytes(32))

    # ---- formato em disco (subclasses com outro formato sobrescrevem só estes dois) ----------
    def _decodificar(self, bruto: dict) -> tuple:
        """(versão, contador, dados, selo) do JSON lido."""
        return bruto["versao"], bruto["contador"], bruto["dados"], bruto["selo"]

    def _codificar(self, contador: int, dados: dict, selo: str) -> dict:
        return {"versao": self.versao, "contador": contador, "dados": dados, "selo": selo}

    # ---- leitura ---------------------------------------------------------------
    def ler(self) -> dict:
        """Dados atuais (cópia). Relê do disco quando outro processo gravou."""
        if self.caminho is not None:
            self._recarregar()
        return copy.deepcopy(self._dados)

    def ver(self) -> dict:
        """Dados atuais **sem cópia**, só para leitura (caminho quente: uma consulta por requisição)."""
        if self.caminho is not None:
            self._recarregar()
        return self._dados

    def _selo(self, contador: int, dados: dict) -> str:
        corpo = json.dumps({"versao": self.versao, "contador": contador, "dados": dados}, sort_keys=True,
                           ensure_ascii=False)
        return hmac.new(self._chave, corpo.encode("utf-8"), hashlib.sha256).hexdigest()

    def _ultimo_contador(self) -> int:
        try:
            return int(_estado(self.rotulo, self.caminho, "contador").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0

    def _recarregar(self) -> None:
        ultimo = self._ultimo_contador()
        try:
            st = _sem_conflito_de_acesso(self.caminho.stat)
        except FileNotFoundError:
            if ultimo:
                raise ArquivoComprometido(f"{self.caminho.name}: arquivo ausente, mas já houve {ultimo} gravação(ões)") \
                    from None
            self._dados, self._contador, self._marca = copy.deepcopy(self._vazio), 0, None
            return
        marca = (st.st_mtime_ns, st.st_size)
        if marca == self._marca and self._contador == ultimo:
            return
        try:
            bruto = json.loads(_sem_conflito_de_acesso(lambda: self.caminho.read_text(encoding="utf-8")))
            if not isinstance(bruto, dict):
                raise ValueError("objeto esperado")
            versao, contador, dados, selo = self._decodificar(bruto)
        except (OSError, ValueError, KeyError, TypeError):
            raise ArquivoComprometido(f"{self.caminho.name}: arquivo ilegível ou fora do formato") from None
        if versao != self.versao:
            raise ArquivoComprometido(f"{self.caminho.name}: versão {versao} do formato (esperada {self.versao})")
        if not isinstance(selo, str) or not hmac.compare_digest(selo, self._selo(contador, dados)):
            raise ArquivoComprometido(f"{self.caminho.name}: selo não confere (arquivo alterado fora do sistema)")
        if contador < ultimo:
            raise ArquivoComprometido(f"{self.caminho.name}: contador {contador} menor que o último gravado "
                                      f"({ultimo}): versão antiga recolocada")
        self._dados, self._contador, self._marca = dados, contador, marca

    # ---- escrita ---------------------------------------------------------------
    @contextlib.contextmanager
    def transacao(self):
        """`with arquivo.transacao() as dados:` relê dentro da trava, entrega os dados para alterar
        e grava ao sair. Uma exceção dentro do bloco descarta a alteração."""
        if self.caminho is None:
            rascunho = copy.deepcopy(self._dados)
            yield rascunho
            self._dados, self._contador = rascunho, self._contador + 1
            return
        with trava(self.caminho):
            self._recarregar()
            rascunho = copy.deepcopy(self._dados)
            yield rascunho
            contador = max(self._contador, self._ultimo_contador()) + 1
            self._gravar(rascunho, contador)

    def _gravar(self, rascunho, contador):
        """Persiste sob a trava já adquirida pelo chamador."""
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.caminho.with_suffix(self.caminho.suffix + ".tmp")
        texto = json.dumps(self._codificar(contador, rascunho, self._selo(contador, rascunho)),
                           ensure_ascii=False, indent=1, sort_keys=True)
        fd = os.open(temporario, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, self.modo if self.modo is not None else 0o666)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(texto)
        if self.modo is not None:
            with contextlib.suppress(OSError):
                os.chmod(temporario, self.modo)
        for tentativa in range(40):  # no Windows o destino pode estar aberto por um leitor (até cerca de 2 s)
            try:
                os.replace(temporario, self.caminho)
                break
            except PermissionError:
                if tentativa == 39:
                    raise
                time.sleep(0.05)
        estado = _estado(self.rotulo, self.caminho, "contador")
        estado.parent.mkdir(parents=True, exist_ok=True)
        estado.write_text(str(contador), encoding="utf-8")
        st = self.caminho.stat()
        self._dados, self._contador, self._marca = rascunho, contador, (st.st_mtime_ns, st.st_size)

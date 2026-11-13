"""Arquivo selado: JSON versionado, íntegro e seguro para dois processos (ADR-009).

É o formato dos cadastros do SVC-IAM (contas e sessões), que a TUI de administração e o
servidor do dashboard leem e gravam ao mesmo tempo. Mesmo desenho do arquivo do SVC-MEM:

- **selo**: HMAC-SHA256 sobre (versão, contador, dados), com chave guardada **fora da pasta de
  dados** (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`, modo 0600);
- **contador**: sobe a cada gravação e também fica fora da pasta; um arquivo com contador menor
  que o último gravado é uma versão antiga recolocada no lugar (rollback) e é recusado;
- **gravação atômica**: arquivo temporário e `os.replace`;
- **trava entre processos**: arquivo `.lock` criado com `O_EXCL` (funciona em Windows, Linux e
  macOS); toda alteração relê o arquivo dentro da trava, então duas escritas concorrentes
  nunca se sobrescrevem;
- **falha fechada**: arquivo ausente depois de já ter sido gravado, ilegível, de outra versão,
  com selo que não confere ou com contador antigo levanta `ArquivoComprometido`. Quem chama
  decide o que negar; o SVC-IAM nega toda entrada.

Sem `caminho`, os dados ficam só em memória (acesso simulado dos cenários em lote).
"""
import contextlib
import copy
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

ESPERA_TRAVA = 5.0  # segundos tentando obter a trava antes de desistir
TRAVA_VELHA = 30.0  # trava mais antiga que isso é de um processo que morreu: pode ser quebrada


class ArquivoComprometido(RuntimeError):
    """A integridade do arquivo não pôde ser garantida."""


class TravaOcupada(RuntimeError):
    pass


def pasta_de_chaves() -> Path:
    return Path(os.environ.get("FIN_MAS_DIR_CHAVES") or Path.home() / ".fin_mas" / "chaves")


def chave_de(rotulo: str, caminho: Path) -> bytes:
    """Chave de 32 bytes do arquivo, criada no primeiro uso, fora da pasta de dados."""
    arquivo = _estado(rotulo, caminho, "chave")
    if arquivo.exists():
        return arquivo.read_bytes()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    chave = secrets.token_bytes(32)
    arquivo.write_bytes(chave)
    with contextlib.suppress(OSError):
        os.chmod(arquivo, 0o600)
    return chave


def _estado(rotulo: str, caminho: Path, sufixo: str) -> Path:
    nome = hashlib.sha256(str(Path(caminho).resolve()).encode("utf-8")).hexdigest()[:16]
    return pasta_de_chaves() / f"{rotulo}-{nome}.{sufixo}"


@contextlib.contextmanager
def trava(caminho: Path):
    """Exclusão mútua entre processos sobre `caminho` (arquivo `<caminho>.lock`)."""
    alvo = Path(str(caminho) + ".lock")
    alvo.parent.mkdir(parents=True, exist_ok=True)
    fim = time.monotonic() + ESPERA_TRAVA
    while True:
        try:
            fd = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - alvo.stat().st_mtime > TRAVA_VELHA:
                    alvo.unlink()
                    continue
            if time.monotonic() > fim:
                raise TravaOcupada(f"{alvo.name}: outro processo está gravando há mais de {ESPERA_TRAVA:.0f} s") from None
            time.sleep(0.02)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            alvo.unlink()


class ArquivoSelado:
    def __init__(self, caminho, rotulo: str, versao: int, vazio: dict):
        self.caminho = Path(caminho) if caminho else None
        self.rotulo, self.versao = rotulo, versao
        self._vazio = vazio
        self._dados = copy.deepcopy(vazio)
        self._contador = 0
        self._marca = None  # (mtime_ns, tamanho) do que está em memória
        self._chave = chave_de(rotulo, self.caminho) if self.caminho else secrets.token_bytes(32)

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
            st = self.caminho.stat()
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
            bruto = json.loads(self.caminho.read_text(encoding="utf-8"))
            versao, contador, dados, selo = bruto["versao"], bruto["contador"], bruto["dados"], bruto["selo"]
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
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.caminho.with_suffix(self.caminho.suffix + ".tmp")
            temporario.write_text(json.dumps({"versao": self.versao, "contador": contador, "dados": rascunho,
                                              "selo": self._selo(contador, rascunho)},
                                             ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
            for tentativa in range(5):  # no Windows o destino pode estar aberto por um leitor por um instante
                try:
                    os.replace(temporario, self.caminho)
                    break
                except PermissionError:
                    if tentativa == 4:
                        raise
                    time.sleep(0.05)
            estado = _estado(self.rotulo, self.caminho, "contador")
            estado.parent.mkdir(parents=True, exist_ok=True)
            estado.write_text(str(contador), encoding="utf-8")
            st = self.caminho.stat()
            self._dados, self._contador, self._marca = rascunho, contador, (st.st_mtime_ns, st.st_size)

"""Cofre de segredos selado (DSM4, IAM-10, ADR-012): segredos nomeados da plataforma.

Guarda o que a plataforma precisa usar mas ninguém precisa ver de novo: o segredo TOTP de cada
conta (`totp:<usuario>`), as chaves dos provedores de LLM (`llm:<VARIAVEL>`) e credenciais de
conectores (`conector:<nome>`).

O que o cofre **garante**:

- **integridade**: é um `ArquivoSelado` (selo HMAC-SHA256 com chave fora da pasta de dados,
  contador contra volta de versão, gravação atômica, trava entre processos). Segredo trocado,
  removido ou recolocado de uma versão antiga fora do sistema deixa o cofre comprometido e a
  leitura falha fechada (`ArquivoComprometido`);
- **controle de acesso**: o arquivo é gravado com permissão 0600 (só o dono do processo lê) e
  fica, por padrão, na pasta de chaves (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`), fora da
  pasta de dados que se copia, se compartilha ou se envia junto com as planilhas;
- **a interface nunca recebe o valor**: o SVC-IAM só devolve se o segredo existe (`existe`,
  `nomes`). `ler` é para o código que usa o segredo (verificar um código TOTP, chamar o
  provedor), nunca para uma rota, comando ou tela;
- **auditoria**: quem grava e quem remove fica no próprio cofre (sem o valor) e na trilha de
  acesso (o SVC-IAM registra).

O que o cofre **não garante**: **confidencialidade contra quem lê o disco** com o usuário do
processo (ou como administrador da máquina). A biblioteca padrão do Python não tem cifra
autenticada, e o projeto não inventa criptografia: os valores ficam em claro dentro do arquivo
selado. Contra esse atacante a proteção é a do sistema operacional (permissão do arquivo,
disco cifrado, conta separada para o serviço). Para confidencialidade em repouso, troque este
módulo por um cofre do sistema (Keychain, DPAPI, libsecret) ou por um gerenciador de segredos
mantendo a mesma API: `guardar(nome, valor, ator)`, `ler(nome)`, `existe(nome)`,
`remover(nome, ator)`.

Sem caminho (acesso simulado dos cenários em lote) o cofre fica só em memória.
"""
import hashlib
import re
import time
from pathlib import Path

from fin_mas.services.selado import ArquivoSelado, pasta_de_chaves

VERSAO = 1
NOME = re.compile(r"^[a-z][a-z0-9_-]{0,31}:[A-Za-z0-9_.@-]{1,96}$")
MAX_VALOR = 8 * 1024


class SegredoInvalido(ValueError):
    pass


def caminho_padrao(pasta_dados) -> Path:
    """Cofre de um cadastro: na pasta de chaves, com o nome derivado do caminho do cadastro."""
    nome = hashlib.sha256(str(Path(pasta_dados).resolve()).encode("utf-8")).hexdigest()[:16]
    return pasta_de_chaves() / f"cofre-{nome}.json"


class Cofre:
    def __init__(self, caminho=None, *, relogio=time.time):
        self.caminho = Path(caminho) if caminho else None
        self.relogio = relogio
        self._arquivo = ArquivoSelado(self.caminho, "cofre", VERSAO, {"segredos": {}}, modo=0o600)

    @classmethod
    def do_cadastro(cls, pasta_dados, relogio=time.time) -> "Cofre":
        return cls(caminho_padrao(pasta_dados) if pasta_dados else None, relogio=relogio)

    @staticmethod
    def _validar_nome(nome) -> str:
        if not isinstance(nome, str) or not NOME.match(nome):
            raise SegredoInvalido("nome de segredo: prefixo:nome (ex.: llm:ANTHROPIC_API_KEY, totp:carla)")
        return nome

    def guardar(self, nome: str, valor: str, ator: str) -> None:
        self._validar_nome(nome)
        if not isinstance(valor, str) or not valor or len(valor) > MAX_VALOR or "\n" in valor:
            raise SegredoInvalido(f"valor do segredo: texto de uma linha, de 1 a {MAX_VALOR} caracteres")
        with self._arquivo.transacao() as dados:
            dados["segredos"][nome] = {"valor": valor, "por": str(ator), "em": round(self.relogio(), 3)}

    def ler(self, nome: str) -> str | None:
        """Valor do segredo, para o código que o usa. Nunca vai para uma interface."""
        item = self._arquivo.ver()["segredos"].get(nome)
        return None if item is None else item["valor"]

    def existe(self, nome: str) -> bool:
        return nome in self._arquivo.ver()["segredos"]

    def remover(self, nome: str, ator: str) -> bool:
        with self._arquivo.transacao() as dados:
            return dados["segredos"].pop(nome, None) is not None

    def nomes(self, prefixo: str = "") -> list[dict]:
        """Nomes, autor e data de cada segredo: o que a interface pode ver (sem o valor)."""
        return [{"nome": n, "por": s["por"], "em": s["em"]} for n, s in sorted(self._arquivo.ver()["segredos"].items())
                if n.startswith(prefixo)]

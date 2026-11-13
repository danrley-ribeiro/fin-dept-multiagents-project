"""Cofre selado de credenciais (tokens e chaves de API dos conectores), ADR-011.

API mínima: `guardar(nome, valor, ator)`, `ler(nome)`, `existe(nome)`, `remover(nome, ator)` e
`nomes()`. O valor:

- fica cifrado no disco (fluxo HMAC-SHA256 em modo contador, nonce aleatório por segredo, e
  etiqueta HMAC própria: cifra e autentica com a biblioteca padrão, sem dependência nova);
- dentro de um `ArquivoSelado` (selo HMAC, contador contra rollback, trava entre processos), com
  as chaves **fora da pasta de dados** (`FIN_MAS_DIR_CHAVES`), como os cadastros do SVC-IAM;
- nunca volta pela API nem entra em trace ou trilha: só o conector o lê, na hora da chamada; a
  trilha registra quem guardou ou removeu qual nome, sem o valor.

Arquivo adulterado, de outra versão ou com contador antigo: `ArquivoComprometido` (falha fechada).
Sem `caminho`, o cofre fica só em memória.
"""
import base64
import hashlib
import hmac
import re
import secrets

from fin_mas.services.selado import ArquivoSelado, chave_de

VERSAO = 1
NOME = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,63}$")


class SegredoAdulterado(RuntimeError):
    pass


class Cofre:
    def __init__(self, caminho=None, registrar=None):
        """`registrar(evento, ator, **campos)`: trilha de acesso (ex.: `Acesso.registrar`)."""
        self._arquivo = ArquivoSelado(caminho, "cofre", VERSAO, {"segredos": {}})
        mestra = chave_de("cofre-cifra", self._arquivo.caminho) if self._arquivo.caminho else secrets.token_bytes(32)
        self._k_cifra = hmac.new(mestra, b"cifra", hashlib.sha256).digest()
        self._k_etiqueta = hmac.new(mestra, b"etiqueta", hashlib.sha256).digest()
        self._registrar = registrar

    # ---- cifra ---------------------------------------------------------------------------------
    def _fluxo(self, nonce: bytes, tamanho: int) -> bytes:
        blocos = (hmac.new(self._k_cifra, nonce + i.to_bytes(8, "big"), hashlib.sha256).digest()
                  for i in range((tamanho + 31) // 32))
        return b"".join(blocos)[:tamanho]

    def _cifrar(self, nome: str, valor: str) -> dict:
        nonce = secrets.token_bytes(16)
        claro = valor.encode("utf-8")
        cifrado = bytes(a ^ b for a, b in zip(claro, self._fluxo(nonce, len(claro))))
        etiqueta = hmac.new(self._k_etiqueta, nome.encode() + nonce + cifrado, hashlib.sha256).hexdigest()
        return {"nonce": base64.b64encode(nonce).decode(), "valor": base64.b64encode(cifrado).decode(),
                "etiqueta": etiqueta}

    def _decifrar(self, nome: str, guardado: dict) -> str:
        nonce, cifrado = base64.b64decode(guardado["nonce"]), base64.b64decode(guardado["valor"])
        esperado = hmac.new(self._k_etiqueta, nome.encode() + nonce + cifrado, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(esperado, guardado.get("etiqueta", "")):
            raise SegredoAdulterado(f"credencial {nome}: etiqueta não confere")
        return bytes(a ^ b for a, b in zip(cifrado, self._fluxo(nonce, len(cifrado)))).decode("utf-8")

    def _auditar(self, evento, ator, **campos):
        if self._registrar is not None:
            self._registrar(evento, ator, **campos)

    # ---- API -------------------------------------------------------------------------------------
    def guardar(self, nome: str, valor: str, ator: str | None) -> None:
        if not isinstance(nome, str) or not NOME.match(nome):
            raise ValueError("nome de credencial: minúsculas, números, ponto, dois-pontos, hífen ou sublinhado")
        if not isinstance(valor, str) or not valor or len(valor) > 4096:
            raise ValueError("credencial vazia ou grande demais (até 4096 caracteres)")
        with self._arquivo.transacao() as dados:
            dados["segredos"][nome] = self._cifrar(nome, valor)
        self._auditar("credencial_guardada", ator, credencial=nome)

    def ler(self, nome: str) -> str | None:
        """Só para o conector, na hora da chamada. Nunca devolva isto por uma API."""
        guardado = self._arquivo.ver()["segredos"].get(nome)
        return None if guardado is None else self._decifrar(nome, guardado)

    def existe(self, nome: str) -> bool:
        return nome in self._arquivo.ver()["segredos"]

    def remover(self, nome: str, ator: str | None) -> bool:
        with self._arquivo.transacao() as dados:
            existia = dados["segredos"].pop(nome, None) is not None
        if existia:
            self._auditar("credencial_removida", ator, credencial=nome)
        return existia

    def nomes(self) -> list[str]:
        return sorted(self._arquivo.ver()["segredos"])

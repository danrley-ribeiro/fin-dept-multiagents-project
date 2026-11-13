"""Segundo fator por TOTP (RFC 6238 sobre o HOTP da RFC 4226), só com a biblioteca padrão (DSM4, IAM-08).

- segredo de 160 bits, mostrado em base32 (o formato que os aplicativos autenticadores leem);
- código de 6 dígitos, HMAC-SHA1, passo de 30 s;
- janela de ±1 passo (relógios desencontrados em até 30 s);
- anti-replay: quem verifica guarda o último passo aceito e só aceita passo maior. O mesmo
  código, ou um código mais antigo ainda dentro da janela, é recusado;
- códigos de recuperação: dez, de uso único, no formato `xxxx-xxxx`; quem guarda guarda só o
  SHA-256 deles.

O relógio é sempre passado por quem chama (o `relogio` do SVC-IAM), então os testes geram
códigos válidos de forma determinística.
"""
import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote

PASSO_S = 30
DIGITOS = 6
JANELA = 1
CODIGOS_RECUPERACAO = 10


def novo_segredo() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _chave(segredo: str) -> bytes:
    texto = segredo.strip().replace(" ", "").upper()
    return base64.b32decode(texto + "=" * (-len(texto) % 8))


def hotp(chave: bytes, contador: int, digitos: int = DIGITOS) -> str:
    """RFC 4226, seção 5.3: truncamento dinâmico do HMAC-SHA1."""
    mac = hmac.new(chave, struct.pack(">Q", contador), hashlib.sha1).digest()
    deslocamento = mac[-1] & 0x0F
    numero = struct.unpack(">I", mac[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF
    return str(numero % 10 ** digitos).zfill(digitos)


def passo(t: float) -> int:
    return int(t // PASSO_S)


def codigo(segredo: str, t: float) -> str:
    return hotp(_chave(segredo), passo(t))


def verificar(segredo: str, recebido, t: float, ultimo_passo: int = -1, janela: int = JANELA) -> int | None:
    """Passo aceito (para guardar como o último usado), ou None.

    Aceita só passos dentro de ±`janela` de `t` **e** maiores que `ultimo_passo` (anti-replay).
    """
    if not isinstance(recebido, str):
        return None
    recebido = recebido.strip().replace(" ", "")
    if len(recebido) != DIGITOS or not recebido.isdigit():
        return None
    chave, atual = _chave(segredo), passo(t)
    for p in range(atual - janela, atual + janela + 1):
        if p > ultimo_passo and hmac.compare_digest(hotp(chave, p), recebido):
            return p
    return None


def uri(segredo: str, conta: str, emissor: str = "SMA Controladoria") -> str:
    """URI `otpauth://` para cadastrar no aplicativo autenticador (pode virar QR code)."""
    return (f"otpauth://totp/{quote(emissor)}:{quote(conta)}?secret={segredo}&issuer={quote(emissor)}"
            f"&algorithm=SHA1&digits={DIGITOS}&period={PASSO_S}")


def codigos_recuperacao(n: int = CODIGOS_RECUPERACAO) -> list[str]:
    return [f"{secrets.token_hex(2)}{secrets.token_hex(2)}-{secrets.token_hex(2)}{secrets.token_hex(2)}" for _ in range(n)]


def hash_recuperacao(codigo_: str) -> str:
    return hashlib.sha256(("recuperacao:" + codigo_.strip().lower()).encode("utf-8")).hexdigest()

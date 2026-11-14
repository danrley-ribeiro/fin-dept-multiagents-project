"""Redaction fail-closed de traces e memória (NORM-06, REQ-P01), DSM3.

`redigir` percorre o valor (dict, lista, texto, número) e devolve uma cópia com:

- campos cujo nome indica segredo (senha, token, api_key, credencial…) substituídos;
- CPF e CNPJ (com ou sem máscara), telefone, e-mail, chaves de API e tokens Bearer dentro de
  textos substituídos.

Nomes próprios em texto livre não são reconhecidos (não há NER); por isso a memória de longo
prazo não guarda texto livre.

Tipos que não sabe sanitizar (objetos arbitrários) ou estruturas profundas demais levantam
`FalhaRedacao`: quem grava (auditoria, memória) recusa a gravação em vez de arriscar
vazar o conteúdo. Nomes de usuário do ERP (ex.: `ana`) não são removidos do trace porque
são a evidência de alçada e SoD (finalidade de auditoria); na memória de longo prazo eles
são pseudonimizados (`services/memoria.py`).
"""
import re

SEGREDO = "[SEGREDO REDIGIDO]"
# nome do campo é (ou termina em) um destes: o valor inteiro é removido, qualquer que seja o tipo
CHAVES_SECRETAS = re.compile(r"(^|[_\-.])(senha|password|passwd|token|api[_-]?key|secret|segredo|credencial|"
                             r"authorization|cpf|cnpj|rg|telefone|celular)$", re.IGNORECASE)
PADROES = [
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "[CPF REDIGIDO]"),
    (re.compile(r"\bCPF[:\s]*\d{11}\b", re.IGNORECASE), "[CPF REDIGIDO]"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "[CNPJ REDIGIDO]"),
    # CPF (11 dígitos) ou CNPJ (14) sem máscara em texto livre: números longos assim não aparecem no domínio.
    # A fronteira exclui letras e dígitos (não só dígitos): 11 ou 14 dígitos seguidos dentro de um hash
    # hexadecimal (ex.: o digest do veto) não são documento e não podem ser alterados.
    (re.compile(r"(?<![0-9A-Za-z])(?<!\d[.,])(\d{11}|\d{14})(?![0-9A-Za-z])(?![.,]\d)"), "[DOCUMENTO REDIGIDO]"),
    (re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-\d{4}\b"), "[TELEFONE REDIGIDO]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b"), "[EMAIL REDIGIDO]"),
    (re.compile(r"\b(sk|pk|rk|ghp|gho|xox[abprs])[-_][A-Za-z0-9_-]{12,}\b"), SEGREDO),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{12,}=*", re.IGNORECASE), "Bearer " + SEGREDO),
]
PROFUNDIDADE_MAX = 40


class FalhaRedacao(ValueError):
    """A sanitização não pôde ser garantida: a gravação deve ser recusada."""


def redigir(valor, _nivel: int = 0):
    if _nivel > PROFUNDIDADE_MAX:
        raise FalhaRedacao("estrutura profunda demais para sanitizar")
    if valor is None or isinstance(valor, (bool, int, float)):
        return valor
    if isinstance(valor, str):
        return redigir_texto(valor)
    if isinstance(valor, dict):
        saida = {}
        for chave, item in valor.items():
            if not isinstance(chave, str):
                chave = str(chave)
            segredo = CHAVES_SECRETAS.search(chave) and item not in (None, "")
            saida[chave] = SEGREDO if segredo else redigir(item, _nivel + 1)
        return saida
    if isinstance(valor, (list, tuple)):
        return [redigir(item, _nivel + 1) for item in valor]
    raise FalhaRedacao(f"tipo não sanitizável: {type(valor).__name__}")


def redigir_texto(texto: str) -> str:
    for padrao, substituto in PADROES:
        texto = padrao.sub(substituto, texto)
    return texto

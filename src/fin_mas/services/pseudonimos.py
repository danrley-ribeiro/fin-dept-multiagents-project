"""Pseudônimos para o que sai da máquina rumo a um provedor de LLM externo (NORM-06, ADR-008).

Antes do envio, identificadores de fornecedor, documento e lançamento e os nomes das pessoas
do ERP são trocados por rótulos neutros (`FORNECEDOR-A`, `PESSOA-B`…). A tabela fica só em
memória, neste processo, e serve para desfazer a troca no texto que volta. Os rótulos não
têm dígitos, de modo que continuam válidos sob a regra "texto de proposta sem números".

Não é anonimização: valores e contas seguem no contexto, porque são o que o modelo precisa
para a tarefa. Por isso o envio a um provedor externo também exige consentimento explícito.
"""
import re

PADROES = (("FORNECEDOR", re.compile(r"\bF-\d+\b")), ("DOCUMENTO", re.compile(r"\bNF-\d+\b")),
           ("LANCAMENTO", re.compile(r"\bL-\d+\b")))
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _rotulo(categoria: str, n: int) -> str:
    sufixo = ""
    while True:
        sufixo = LETRAS[n % 26] + sufixo
        n = n // 26 - 1
        if n < 0:
            return f"{categoria}-{sufixo}"


class Pseudonimizador:
    def __init__(self, pessoas=()):
        nomes = sorted({p for p in pessoas if p}, key=lambda p: (-len(p), p))
        self._pessoas = re.compile(r"\b(" + "|".join(re.escape(p) for p in nomes) + r")\b", re.IGNORECASE) \
            if nomes else None
        self.mapa: dict[str, str] = {}  # rótulo -> valor real
        self._inverso: dict[str, str] = {}

    def _trocar(self, categoria: str, real: str) -> str:
        chave = real.lower() if categoria == "PESSOA" else real
        if chave not in self._inverso:
            n = sum(1 for r in self.mapa if r.startswith(categoria + "-"))
            self._inverso[chave] = _rotulo(categoria, n)
            self.mapa[self._inverso[chave]] = real
        return self._inverso[chave]

    def aplicar(self, texto: str) -> str:
        for categoria, padrao in PADROES:
            texto = padrao.sub(lambda m, c=categoria: self._trocar(c, m.group(0)), texto)
        if self._pessoas is not None:
            texto = self._pessoas.sub(lambda m: self._trocar("PESSOA", m.group(0)), texto)
        return texto

    def reverter(self, texto: str) -> str:
        for rotulo in sorted(self.mapa, key=len, reverse=True):
            texto = texto.replace(rotulo, self.mapa[rotulo])
        return texto

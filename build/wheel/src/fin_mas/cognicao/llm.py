"""Proponente de hipóteses por LLM opcional (ADR-008): só encaminha ao SVC-MOD.

Quem decide se a chamada acontece é o Registro de Modelos (flag do agente, uso `hipoteses`,
cota, consentimento para provedor externo). Com a flag desligada devolve lista vazia e nada
é registrado. O que volta são propostas, que o agente valida como as de qualquer proponente.
"""


class ProponenteLLM:
    ID = "llm"

    def __init__(self, modelos):
        self.modelos = modelos
        self.pseudonimos: dict = {}  # rótulo -> valor real, das propostas da última chamada

    def propor(self, agente, cid, tarefa, contexto, esquema) -> list:
        propostas, self.pseudonimos = self.modelos.propor(agente, cid, tarefa, contexto=contexto, esquema=esquema)
        return propostas

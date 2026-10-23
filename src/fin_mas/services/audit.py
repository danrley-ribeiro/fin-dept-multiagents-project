"""Auditoria: registro central de eventos (SVC-AUD), em memória.

Cada registro é um dict com t (relógio lógico) e seq; o bus e os agentes gravam
por aqui, nunca cada agente por conta própria (REQ-O01).
"""
import hashlib
import json


class AuditLog:
    def __init__(self):
        self.records: list[dict] = []

    def record(self, t: int, kind: str, **campos) -> dict:
        registro = {"seq": len(self.records) + 1, "t": t, "kind": kind, **campos}
        self.records.append(registro)
        return registro

    def by_conversation(self, conversation_id: str) -> list[dict]:
        return [r for r in self.records if r.get("conversation_id") == conversation_id]

    def digest(self) -> str:
        canonico = json.dumps(self.records, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()

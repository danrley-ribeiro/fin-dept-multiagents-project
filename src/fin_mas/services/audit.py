"""Auditoria: registro central de eventos (SVC-AUD), em memória.

Cada registro é um dict com t (relógio lógico) e seq; o bus e os agentes gravam
por aqui, nunca cada agente por conta própria (REQ-O01).
"""
import hashlib
import json
from pathlib import Path


class AuditLog:
    def __init__(self):
        self.records: list[dict] = []

    def record(self, t: int, kind: str, **campos) -> dict:
        registro = {"seq": len(self.records) + 1, "t": t, "kind": kind, **campos}
        self.records.append(registro)
        return registro

    def by_conversation(self, conversation_id: str) -> list[dict]:
        return [r for r in self.records if r.get("conversation_id") == conversation_id]

    def write_jsonl(self, path) -> None:
        """Grava um registro por linha (JSONL), na ordem de seq."""
        linhas = (json.dumps(r, sort_keys=True, ensure_ascii=False) for r in self.records)
        Path(path).write_text("\n".join(linhas) + "\n", encoding="utf-8")

    @classmethod
    def read_jsonl(cls, path) -> "AuditLog":
        log = cls()
        for linha in Path(path).read_text(encoding="utf-8").splitlines():
            if linha.strip():
                log.records.append(json.loads(linha))
        return log

    def digest(self) -> str:
        canonico = json.dumps(self.records, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()

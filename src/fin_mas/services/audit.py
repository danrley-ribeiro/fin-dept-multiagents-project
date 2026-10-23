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

    def familia(self, conversation_id: str) -> list[str]:
        """A conversa e as filhas ligadas por registros `link` (subtarefas, consultas), em ordem de abertura."""
        filhas = {}
        for r in self.records:
            if r["kind"] == "link":
                filhas.setdefault(r["conversation_id"], []).append(r["filha"])
        ordem, pendentes = [], [conversation_id]
        while pendentes:
            atual = pendentes.pop(0)
            ordem.append(atual)
            pendentes += filhas.get(atual, [])
        return ordem

    def trilha(self, conversation_id: str, verbose: bool = False) -> list[str]:
        """Sequência causal da solicitação reconstruída só pelo trace (REQ-O01)."""
        familia = set(self.familia(conversation_id))
        ocultos = set() if verbose else {"deliver"}
        return [formatar(r) for r in self.records
                if r.get("conversation_id") in familia and r["kind"] not in ocultos]

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


def formatar(r: dict) -> str:
    """Uma linha legível por registro do trace."""
    cab = f"t={r['t']:03d} #{r['seq']:03d} {r.get('conversation_id', '-'):<8}"
    k = r["kind"]
    if k in ("open", "send", "deliver", "ui"):
        estados = f"  [{r['de']} -> {r['para']}]" if "de" in r else ""
        return f"{cab} {r['sender']} -> {r['receiver']} {r['performative']}{estados}"
    if k == "drop":
        return f"{cab} PERDIDA {r['sender']} -> {r['receiver']} {r['performative']} ({r['motivo']})"
    if k == "discard":
        return f"{cab} DESCARTADA {r['sender']} -> {r['receiver']} {r['performative']} ({r['motivo']})"
    if k == "timeout":
        return f"{cab} TIMEOUT contra {r['content'].get('contraparte')}  [{r['de']} -> {r['para']}]"
    if k == "advance":
        return f"{cab} {r['agente']} aplica '{r['evento']}'  [{r['de']} -> {r['para']}]"
    if k == "decision":
        resultado = json.dumps(r["resultado"], sort_keys=True, ensure_ascii=False)
        return f"{cab} DECISAO {r['agente']}: {r['regra']} => {resultado}"
    if k == "mcp_call":
        return f"{cab} MCP {r['agente']} chama {r['tool']}"
    if k == "mcp_denied":
        return f"{cab} MCP NEGADO {r['agente']} em {r['tool']}"
    if k == "link":
        return f"{cab} subconversa {r['filha']} ({r['subtarefa']})"
    return f"{cab} {k}"

"""Envelope A2A: m = <s, r, p, c, o, k> da DSM1, mais reply_by (relógio lógico)."""
from dataclasses import dataclass, field

ONTOLOGIA = "ctrl-fin-v1"


@dataclass(frozen=True)
class Message:
    sender: str
    receiver: str
    performative: str  # performativo FIPA ou evento da FSM do protocolo
    conversation_id: str
    protocol: str | None  # None = canal de interface humana (ENV-UI), fora do A2A
    content: dict = field(default_factory=dict)
    ontology: str = ONTOLOGIA
    reply_by: int | None = None

"""FSMs dos protocolos, carregadas de models/protocols.yaml (fonte única da DSM1).

`transicoes` viram a tabela de transição; qualquer par (estado, evento) fora dela
levanta ProtocolViolation. `invalidas` só enriquecem a mensagem de erro.

DSM3: cada protocolo também declara os papéis participantes, quem pode emitir cada
performativo (`emissores`), quem pode aplicar cada transição local (`eventos_locais`) e o
esquema do conteúdo de cada performativo (`esquemas`). O barramento usa esses campos
para validar remetente, destinatário, papel e conteúdo antes de mudar o estado.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ProtocolViolation(Exception):
    """Mensagem ou evento não permitido pela FSM do protocolo."""


def models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "models"


@dataclass(frozen=True)
class Protocol:
    id: str
    initial: str
    finals: frozenset
    transitions: dict  # (estado, evento) -> estado
    invalid: dict  # (estado, evento) -> motivo
    opening: str  # primeiro performativo: abre a conversa
    performatives: tuple = ()
    participants: frozenset = frozenset()  # papéis (ROLE-*, SVC-*) que podem participar
    emitters: dict = field(default_factory=dict)  # performativo -> papéis que podem emitir
    local_events: dict = field(default_factory=dict)  # evento local -> papéis que podem aplicar
    schemas: dict = field(default_factory=dict)  # performativo -> {campo: tipo}

    def next_state(self, state: str, event: str) -> str:
        key = (state, event)
        if key in self.transitions:
            return self.transitions[key]
        motivo = self.invalid.get(key, "transição inexistente")
        raise ProtocolViolation(f"{self.id}: '{event}' em {state} não é permitido ({motivo})")


def load_protocols(path: Path | None = None) -> dict[str, Protocol]:
    path = path or models_dir() / "protocols.yaml"
    itens = yaml.safe_load(path.read_text(encoding="utf-8"))["items"]
    protocolos = {}
    for p in itens:
        protocolos[p["id"]] = Protocol(
            id=p["id"],
            initial=p["estado_inicial"],
            finals=frozenset(p["estados_finais"]),
            transitions={(a, e): b for a, e, b in p["transicoes"]},
            invalid={(a, e): motivo for a, e, motivo in p.get("invalidas", [])},
            opening=p["performativos"][0],
            performatives=tuple(p["performativos"]),
            participants=frozenset(p.get("participantes", [])),
            emitters={k: frozenset(v) for k, v in (p.get("emissores") or {}).items()},
            local_events={k: frozenset(v) for k, v in (p.get("eventos_locais") or {}).items()},
            schemas=dict(p.get("esquemas") or {}),
        )
    return protocolos


@dataclass
class Conversation:
    protocol: Protocol
    conversation_id: str
    initiator: str
    counterpart: str
    state: str = ""
    history: list = field(default_factory=list)

    def __post_init__(self):
        self.state = self.protocol.initial

    @property
    def is_final(self) -> bool:
        return self.state in self.protocol.finals

    def can(self, event: str) -> bool:
        return (self.state, event) in self.protocol.transitions

    def step(self, event: str) -> tuple[str, str]:
        antes = self.state
        self.state = self.protocol.next_state(antes, event)
        self.history.append((antes, event, self.state))
        return antes, self.state

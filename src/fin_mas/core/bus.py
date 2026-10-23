"""Bus A2A em processo com relógio lógico (ADR-003 e ADR-004).

Single-thread e determinístico: a fila é ordenada por (tempo lógico, sequência).
Toda mensagem A2A passa pela FSM do protocolo e é auditada; `reply_by` vira um
temporizador que expira a conversa (evento `timeout`) no tempo lógico.
"""
import heapq
from dataclasses import dataclass

from fin_mas.core.fsm import Conversation, ProtocolViolation, load_protocols
from fin_mas.core.message import Message
from fin_mas.services.audit import AuditLog

SISTEMA = "SVC-A2A"


@dataclass
class Fault:
    """Perda deliberada de mensagens na entrega (injeção de falha do ambiente)."""

    receiver: str
    performative: str
    times: int
    protocol: str | None = None

    def matches(self, msg: Message) -> bool:
        return (
            self.times > 0
            and msg.receiver == self.receiver
            and msg.performative == self.performative
            and (self.protocol is None or msg.protocol == self.protocol)
        )


class Bus:
    def __init__(self, audit: AuditLog | None = None, faults: list[Fault] | None = None):
        self.audit = audit if audit is not None else AuditLog()
        self.protocols = load_protocols()
        self.faults = faults or []
        self.now = 0
        self.agents: dict = {}
        self.conversations: dict[str, Conversation] = {}
        self._queue: list = []
        self._seq = 0
        self._ids: dict[str, int] = {}

    def register(self, agent) -> None:
        self.agents[agent.id] = agent

    def new_conversation_id(self, prefix: str) -> str:
        self._ids[prefix] = self._ids.get(prefix, 0) + 1
        return f"{prefix}-{self._ids[prefix]:03d}"

    def _push(self, when: int, kind: str, payload) -> None:
        self._seq += 1
        heapq.heappush(self._queue, (when, self._seq, kind, payload))

    def send(self, msg: Message, delay: int = 1) -> None:
        """Valida a mensagem na FSM e a agenda para entrega em now + delay."""
        if msg.protocol is None:
            self.audit.record(self.now, "ui", **_campos(msg))
            self._push(self.now + delay, "msg", msg)
            return
        conv = self.conversations.get(msg.conversation_id)
        if conv is None:
            self._open(msg)
        else:
            if conv.protocol.id != msg.protocol:
                raise ProtocolViolation(f"{msg.conversation_id} pertence a {conv.protocol.id}")
            if conv.state == "EXPIRADA":
                self.audit.record(self.now, "discard", motivo="resposta após reply_by", **_campos(msg))
                return
            if msg.sender not in (conv.initiator, conv.counterpart):
                raise ProtocolViolation(f"{msg.sender} não participa de {msg.conversation_id}")
            antes, depois = conv.step(msg.performative)
            self.audit.record(self.now, "send", de=antes, para=depois, **_campos(msg))
        self._push(self.now + delay, "msg", msg)

    def _open(self, msg: Message) -> Conversation:
        proto = self.protocols[msg.protocol]
        if msg.performative != proto.opening:
            raise ProtocolViolation(
                f"{proto.id}: '{msg.performative}' sem conversa aberta "
                f"(conversation_id desconhecido: {msg.conversation_id})"
            )
        conv = Conversation(proto, msg.conversation_id, msg.sender, msg.receiver)
        self.conversations[msg.conversation_id] = conv
        antes = conv.state
        if conv.can(msg.performative):
            conv.step(msg.performative)
        self.audit.record(self.now, "open", de=antes, para=conv.state, **_campos(msg))
        if msg.reply_by is not None:
            self._push(msg.reply_by, "timer", msg.conversation_id)
        return conv

    def advance(self, conversation_id: str, event: str, actor: str) -> str:
        """Transição local da FSM (decisão do próprio participante, sem mensagem)."""
        conv = self.conversations[conversation_id]
        antes, depois = conv.step(event)
        self.audit.record(
            self.now, "advance", conversation_id=conversation_id, protocol=conv.protocol.id,
            agente=actor, evento=event, de=antes, para=depois,
        )
        return depois

    def run(self, max_steps: int = 10_000) -> int:
        passos = 0
        while self._queue:
            passos += 1
            if passos > max_steps:
                raise RuntimeError("limite de passos excedido (possível laço de mensagens)")
            when, _, kind, payload = heapq.heappop(self._queue)
            self.now = max(self.now, when)
            if kind == "msg":
                self._deliver(payload)
            else:
                self._timer(payload)
        return passos

    def _deliver(self, msg: Message) -> None:
        for falha in self.faults:
            if falha.matches(msg):
                falha.times -= 1
                self.audit.record(self.now, "drop", motivo="falha injetada", **_campos(msg))
                return
        self.audit.record(self.now, "deliver", **_campos(msg))
        self.agents[msg.receiver].on_message(msg)

    def _timer(self, conversation_id: str) -> None:
        conv = self.conversations[conversation_id]
        if conv.can("timeout"):
            antes, depois = conv.step("timeout")
        elif len(conv.history) == 1 and not conv.is_final:
            # protocolo sem transição de timeout (PROT-CMP) e contraparte ainda sem resposta:
            # avisa o iniciador sem mexer na FSM
            antes = depois = conv.state
        else:
            return
        aviso = Message(
            SISTEMA, conv.initiator, "timeout", conversation_id, conv.protocol.id,
            {"contraparte": conv.counterpart},
        )
        self.audit.record(self.now, "timeout", de=antes, para=depois, **_campos(aviso))
        self.agents[conv.initiator].on_message(aviso)


def _campos(msg: Message) -> dict:
    return {
        "conversation_id": msg.conversation_id,
        "protocol": msg.protocol,
        "sender": msg.sender,
        "receiver": msg.receiver,
        "performative": msg.performative,
        "content": msg.content,
    }

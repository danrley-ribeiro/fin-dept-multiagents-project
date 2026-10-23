"""Agente base: estado, conhecimento e memória são atributos distintos (DSM1)."""
from fin_mas.core.bus import Bus
from fin_mas.core.message import Message


class Agent:
    def __init__(self, agent_id: str, bus: Bus):
        self.id = agent_id
        self.bus = bus
        self.estado: dict = {}  # muda a cada conversa
        self.conhecimento: dict = {}  # regras e parâmetros fixos
        self.memoria: dict = {}  # reservada ao SVC-MEM (DSM3)
        bus.register(self)

    def on_message(self, msg: Message) -> None:
        raise NotImplementedError

    def send(self, receiver, performative, protocol, conversation_id, content=None,
             delay=1, reply_by=None) -> None:
        self.bus.send(
            Message(self.id, receiver, performative, conversation_id, protocol,
                    content or {}, reply_by=reply_by),
            delay=delay,
        )

    def decide(self, conversation_id: str, regra: str, entradas: dict, resultado) -> None:
        """Registra uma decisão com a regra aplicada (REQ-O01)."""
        self.bus.audit.record(
            self.bus.now, "decision", conversation_id=conversation_id, agente=self.id,
            regra=regra, entradas=entradas, resultado=resultado,
        )

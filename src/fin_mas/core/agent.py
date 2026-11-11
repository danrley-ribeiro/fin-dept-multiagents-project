"""Agente base: estado, conhecimento e memória são atributos distintos (DSM1).

DSM3: cada agente declara o seu papel (`PAPEL`) e recebe do barramento uma credencial
no registro. Só `send` e `avancar` a usam; mensagens montadas fora do próprio agente,
com o identificador dele, são rejeitadas por falta de credencial.
"""
from fin_mas.core.bus import Bus
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message


class Agent:
    PAPEL: str | None = None

    def __init__(self, agent_id: str, bus: Bus, papel: str | None = None):
        self.id = agent_id
        self.bus = bus
        self.papel = papel or self.PAPEL
        self.estado: dict = {}  # muda a cada conversa
        self.conhecimento: dict = {}  # regras e parâmetros fixos
        self.memoria = None  # visão do SVC-MEM (services/memoria.py), quando o agente usa memória
        self.__credencial = bus.register(self, self.papel)

    def on_message(self, msg: Message) -> None:
        raise NotImplementedError

    def send(self, receiver, performative, protocol, conversation_id, content=None,
             delay=1, reply_by=None) -> None:
        self.bus.send(
            Message(self.id, receiver, performative, conversation_id, protocol,
                    content or {}, reply_by=reply_by),
            delay=delay, credencial=self.__credencial,
        )

    def ferramenta(self, tool: str, conversation_id: str, **args):
        """Chamada autenticada ao gateway MCP: a identidade vai com a credencial do próprio agente."""
        return self.gw.call(self.id, tool, conversation_id, credencial=self.__credencial, **args)

    def avancar(self, conversation_id: str, evento: str) -> str:
        """Transição local autenticada (ex.: publicar no PROT-CMP)."""
        return self.bus.advance(conversation_id, evento, self.id, credencial=self.__credencial)

    def on_error(self, msg: Message, erro: Exception) -> None:
        """Erro ao tratar `msg`: responde com recusa ou falha explícita, se a FSM permitir."""
        conv = self.bus.conversations.get(msg.conversation_id)
        if conv is None or conv.is_final or msg.receiver != self.id:
            return
        motivo = f"erro ao processar {msg.performative}: {type(erro).__name__}: {erro}"
        for performativo in ("not-understood", "refuse", "failure"):
            if performativo in conv.protocol.performatives and conv.can(performativo):
                try:
                    self.send(msg.sender, performativo, conv.protocol.id, msg.conversation_id,
                              {"motivo": motivo, "publicado": False})
                    return
                except ProtocolViolation:
                    continue

    def mente(self) -> dict:
        """Snapshot observável do agente (dashboard e depuração): estado e conhecimento."""
        return {"id": self.id, "papel": self.papel, "estado": self.estado, "conhecimento": self.conhecimento}

    def decide(self, conversation_id: str, regra: str, entradas: dict, resultado) -> None:
        """Registra uma decisão com a regra aplicada (REQ-O01)."""
        self.bus.audit.record(
            self.bus.now, "decision", conversation_id=conversation_id, agente=self.id,
            regra=regra, entradas=entradas, resultado=resultado,
        )

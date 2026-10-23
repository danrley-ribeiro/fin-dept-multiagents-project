"""Base dos agentes especialistas: responde a PROT-DEL (request) e PROT-QRY (query-ref)."""
from fin_mas.core.agent import Agent
from fin_mas.core.message import Message


class Specialist(Agent):
    latencia = 2  # ticks lógicos entre o agree e o inform

    def __init__(self, agent_id, bus, gateway):
        super().__init__(agent_id, bus)
        self.gw = gateway

    def on_message(self, msg: Message) -> None:
        if msg.performative == "request" and msg.protocol == "PROT-DEL":
            self._delegacao(msg)
        elif msg.performative == "query-ref" and msg.protocol == "PROT-QRY":
            self._consulta(msg)
        elif msg.performative == "timeout":
            self.on_timeout(msg)

    def _delegacao(self, msg: Message) -> None:
        cid, tarefa = msg.conversation_id, msg.content["tarefa"]
        self.send(msg.sender, "agree", "PROT-DEL", cid)
        try:
            resultado = self.executar(tarefa, msg.content, cid)
        except Exception as erro:  # falha explícita ao solicitante, nunca silêncio
            self.send(msg.sender, "failure", "PROT-DEL", cid, {"motivo": str(erro)}, delay=1 + self.latencia)
            return
        self.send(msg.sender, "inform", "PROT-DEL", cid, resultado, delay=1 + self.latencia)

    def _consulta(self, msg: Message) -> None:
        cid, assunto = msg.conversation_id, msg.content["assunto"]
        try:
            resposta = self.consultar(assunto, msg.content, cid)
        except KeyError:
            self.send(msg.sender, "refuse", "PROT-QRY", cid, {"motivo": f"assunto desconhecido: {assunto}"})
            return
        except Exception as erro:
            self.send(msg.sender, "failure", "PROT-QRY", cid, {"motivo": str(erro)})
            return
        self.send(msg.sender, "inform", "PROT-QRY", cid, resposta)

    def executar(self, tarefa: str, content: dict, conversation_id: str) -> dict:
        raise NotImplementedError

    def consultar(self, assunto: str, content: dict, conversation_id: str) -> dict:
        raise KeyError(assunto)

    def on_timeout(self, msg: Message) -> None:
        """Hook para agentes que iniciam conversas e precisam reagir à expiração."""

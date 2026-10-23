"""Auxiliares dos testes: agente cliente que registra o que recebe."""
from fin_mas.core.agent import Agent


class Cliente(Agent):
    """Faz o papel do solicitante (ROLE-SOL) ou de um consumidor de especialista."""

    def __init__(self, agent_id, bus):
        super().__init__(agent_id, bus)
        self.recebidas = []

    def on_message(self, msg):
        self.recebidas.append(msg)

    def por_performativo(self, performativo, cid=None):
        return [m for m in self.recebidas
                if m.performative == performativo and (cid is None or m.conversation_id == cid)]


def seq(audit, cid, performativo, kinds=("open", "send")):
    """seq do primeiro registro de envio do performativo na conversa (ordem causal no trace)."""
    return next(r["seq"] for r in audit.by_conversation(cid)
                if r["kind"] in kinds and r["performative"] == performativo)

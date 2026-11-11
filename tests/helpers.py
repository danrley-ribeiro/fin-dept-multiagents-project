"""Auxiliares dos testes: agente cliente que registra o que recebe."""
from fin_mas.core.agent import Agent


class Cliente(Agent):
    """Faz o papel do solicitante de um especialista (por padrão, o do Orquestrador).

    Desde a DSM3 o barramento confere o papel: para delegar (PROT-DEL, PROT-CMP) o cliente
    é ROLE-ORQ; para consultar (PROT-QRY), ROLE-RES ou ROLE-ORC.
    """

    def __init__(self, agent_id, bus, papel="ROLE-ORQ"):
        super().__init__(agent_id, bus, papel)
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


def aguardando_humano(bus) -> bool:
    """O próximo evento da fila é o prazo de uma aprovação humana (PROT-APR) ainda pendente."""
    if not bus._queue:
        return True
    _, _, kind, payload = bus._queue[0]
    conv = bus.conversations.get(payload) if kind == "timer" else None
    return conv is not None and conv.protocol.id == "PROT-APR" and conv.state == "PENDENTE"


def rodar_ate_humano(bus, limite=10_000):
    """Processa eventos até a fila esvaziar ou o próximo evento ser o prazo de uma aprovação pendente."""
    for _ in range(limite):
        if aguardando_humano(bus):
            return
        bus.step()
    raise AssertionError("a fila não chegou à espera humana")

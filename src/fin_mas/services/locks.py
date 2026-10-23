"""Reserva de período contábil (SVC-LCK): exclusão mútua por (entidade, competência).

Cada chave tem uma FSM do PROT-LCK. A reserva expira por TTL no relógio lógico.
"""
from fin_mas.core.fsm import Conversation, ProtocolViolation, load_protocols

TTL_PADRAO = 50


class LockService:
    def __init__(self, audit, clock, ttl: int = TTL_PADRAO):
        self.audit = audit
        self.clock = clock  # callable que devolve o tempo lógico atual
        self.ttl = ttl
        self._protocolo = load_protocols()["PROT-LCK"]
        self._reservas: dict[tuple, dict] = {}

    def _conv(self, chave) -> Conversation:
        if chave not in self._reservas:
            self._reservas[chave] = {
                "fsm": Conversation(self._protocolo, f"LCK-{chave[0]}-{chave[1]}", "SVC-LCK", "SVC-LCK"),
                "dono": None, "expira_em": None,
            }
        return self._reservas[chave]["fsm"]

    def _expirar(self, chave) -> None:
        reserva = self._reservas.get(chave)
        if reserva and reserva["fsm"].state == "RESERVADO" and self.clock() >= reserva["expira_em"]:
            reserva["fsm"].step("ttl_expirado")
            self.audit.record(self.clock(), "lock", chave=list(chave), evento="ttl_expirado", dono=reserva["dono"])
            reserva["dono"] = None

    def reserve(self, entidade: str, competencia: str, dono: str) -> dict:
        chave = (entidade, competencia)
        fsm = self._conv(chave)
        self._expirar(chave)
        reserva = self._reservas[chave]
        agora = self.clock()
        if fsm.state == "LIVRE":
            fsm.step("reserve")
            reserva["dono"], reserva["expira_em"] = dono, agora + self.ttl
            resposta = {"performative": "reserve-accept", "dono": dono, "expira_em": reserva["expira_em"]}
        elif reserva["dono"] == dono:
            resposta = {"performative": "reserve-accept", "dono": dono, "expira_em": reserva["expira_em"]}
        else:
            fsm.step("reserve_outro_dono")
            resposta = {"performative": "reserve-failure", "dono_atual": reserva["dono"],
                        "expira_em": reserva["expira_em"]}
        self.audit.record(agora, "lock", chave=list(chave), evento="reserve", solicitante=dono, **resposta)
        return resposta

    def release(self, entidade: str, competencia: str, dono: str) -> None:
        chave = (entidade, competencia)
        fsm = self._conv(chave)
        self._expirar(chave)
        reserva = self._reservas[chave]
        if fsm.state == "RESERVADO" and reserva["dono"] != dono:
            raise ProtocolViolation(f"PROT-LCK: {dono} não é o dono da reserva ({reserva['dono']})")
        fsm.step("release")  # em LIVRE levanta ProtocolViolation: liberar reserva inexistente
        reserva["dono"] = None
        self.audit.record(self.clock(), "lock", chave=list(chave), evento="release", dono=dono)

    def dono(self, entidade: str, competencia: str):
        chave = (entidade, competencia)
        self._expirar(chave)
        reserva = self._reservas.get(chave)
        return reserva["dono"] if reserva else None

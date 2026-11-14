"""Reserva de período contábil (SVC-LCK): exclusão mútua por (entidade, competência).

Cada chave tem uma FSM do PROT-LCK. A reserva expira por TTL no relógio lógico.
"""
from fin_mas.core.fsm import Conversation, ProtocolViolation, load_protocols

TTL_PADRAO = 50


class LockService:
    OPERADORES = frozenset({"AG-ORQ"})  # só o Orquestrador reserva, renova e libera períodos

    def __init__(self, audit, clock, ttl: int = TTL_PADRAO, autenticar=None):
        self.audit = audit
        self.clock = clock  # callable que devolve o tempo lógico atual
        self.ttl = ttl
        # f(identidade, credencial) -> bool, do barramento. None = serviço isolado (testes do próprio PROT-LCK).
        # Com ele, dizer o nome do dono não basta: a transição exige a credencial do Orquestrador (correção M6).
        self.autenticar = autenticar
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

    def _autorizar(self, evento: str, chave, agente, credencial) -> None:
        if self.autenticar is None:
            return
        if agente not in self.OPERADORES or not self.autenticar(agente, credencial):
            motivo = f"PROT-LCK: '{evento}' sem credencial válida do Orquestrador (agente={agente!r})"
            self.audit.record(self.clock(), "rejected", protocol="PROT-LCK", agente=str(agente)[:64], evento=evento,
                              chave=list(chave), motivo=motivo, etapa="autenticacao")
            raise ProtocolViolation(motivo)

    def reserve(self, entidade: str, competencia: str, dono: str, *, agente=None, credencial=None) -> dict:
        chave = (entidade, competencia)
        self._autorizar("reserve", chave, agente, credencial)
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

    def release(self, entidade: str, competencia: str, dono: str, *, agente=None, credencial=None) -> None:
        chave = (entidade, competencia)
        self._autorizar("release", chave, agente, credencial)
        fsm = self._conv(chave)
        self._expirar(chave)
        reserva = self._reservas[chave]
        if fsm.state == "RESERVADO" and reserva["dono"] != dono:
            raise ProtocolViolation(f"PROT-LCK: {dono} não é o dono da reserva ({reserva['dono']})")
        fsm.step("release")  # em LIVRE levanta ProtocolViolation: liberar reserva inexistente
        reserva["dono"] = None
        self.audit.record(self.clock(), "lock", chave=list(chave), evento="release", dono=dono)

    def renovar(self, entidade: str, competencia: str, dono: str, ate: int, *, agente=None, credencial=None) -> bool:
        """Estende o TTL da reserva do próprio dono (ex.: enquanto espera o aprovador). False se já a perdeu."""
        chave = (entidade, competencia)
        self._autorizar("renovar", chave, agente, credencial)
        self._expirar(chave)
        reserva = self._reservas.get(chave)
        if reserva is None or reserva["fsm"].state != "RESERVADO" or reserva["dono"] != dono:
            return False
        if ate > reserva["expira_em"]:
            reserva["expira_em"] = ate
            self.audit.record(self.clock(), "lock", chave=list(chave), evento="renovar", dono=dono, expira_em=ate)
        return True

    def dono(self, entidade: str, competencia: str):
        chave = (entidade, competencia)
        self._expirar(chave)
        reserva = self._reservas.get(chave)
        return reserva["dono"] if reserva else None

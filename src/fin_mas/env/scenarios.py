"""Montagem do sistema e cenários nomeados (seed, plantios, falhas, decisão humana).

`build_system` liga bus, dataset, MCP, reserva de período e os seis agentes;
`run_scenario` executa um cenário e devolve a resposta final e o trace.
"""
from dataclasses import dataclass, field

from fin_mas.agents.cin import AgenteControlesInternos
from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.agents.orq import Orquestrador
from fin_mas.agents.rel import AgenteRelatorios
from fin_mas.agents.res import AgenteResultados
from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import COMPETENCIA, ENTIDADE, Dataset
from fin_mas.mcp.gateway import MCPGateway
from fin_mas.services.locks import LockService


class Solicitante(Agent):
    """ROLE-SOL simulado: pede e guarda o que o Orquestrador responde."""

    def __init__(self, bus, agent_id="SOL"):
        super().__init__(agent_id, bus)
        self.recebidas = []

    def solicitar(self, intencao, entidade=ENTIDADE, competencia=COMPETENCIA):
        sid = self.bus.new_conversation_id("SOL")
        self.send("AG-ORQ", "request", "PROT-SOL", sid,
                  {"intencao": intencao, "entidade": entidade, "competencia": competencia})
        return sid

    def on_message(self, msg):
        self.recebidas.append(msg)

    def resposta(self, sid):
        """Última mensagem terminal recebida para a solicitação (inform, failure, refuse, not-understood)."""
        terminais = [m for m in self.recebidas
                     if m.conversation_id == sid and m.performative != "agree"]
        return terminais[-1] if terminais else None


class Aprovador(Agent):
    """ROLE-APR simulado: responde ao aviso de veto conforme o roteiro do cenário."""

    def __init__(self, bus, decisao="nenhuma"):
        super().__init__("APR", bus)
        self.decisao = decisao  # "waiver" libera com ressalva; "nenhuma" deixa o prazo esgotar
        self.avisos = []

    def on_message(self, msg):
        if msg.performative != "veto_notice":
            return
        self.avisos.append(msg)
        self.send("AG-ORQ", "decisao_humana", None, msg.conversation_id,
                  {"solicitacao": msg.content["solicitacao"], "decisao": self.decisao,
                   "justificativa": "aceito o risco: lançamento será corrigido no próximo ciclo"})


@dataclass
class System:
    bus: Bus
    dataset: Dataset
    gateway: MCPGateway
    locks: LockService
    orq: Orquestrador
    usuario: Solicitante
    aprovador: Aprovador
    agentes: dict = field(default_factory=dict)


def build_system(seed=42, plantar=(), faults=(), decisao_aprovador="nenhuma", ttl=200) -> System:
    bus = Bus(faults=[Fault(**f) if isinstance(f, dict) else f for f in faults])
    ds = Dataset(seed=seed, plantar=tuple(plantar))
    gw = MCPGateway(ds, bus.audit, bus)
    locks = LockService(bus.audit, lambda: bus.now, ttl=ttl)
    agentes = {"AG-CUS": AgenteCustos(bus, gw), "AG-ORC": AgenteOrcamento(bus, gw),
               "AG-RES": AgenteResultados(bus, gw), "AG-CIN": AgenteControlesInternos(bus, gw),
               "AG-REL": AgenteRelatorios(bus, gw)}
    orq = Orquestrador(bus, locks)
    return System(bus, ds, gw, locks, orq, Solicitante(bus), Aprovador(bus, decisao_aprovador), agentes)


@dataclass(frozen=True)
class Scenario:
    nome: str
    descricao: str
    intencao: str
    seed: int = 42
    plantar: tuple = ()
    faults: tuple = ()
    decisao_aprovador: str = "nenhuma"


CENARIOS = {c.nome: c for c in [
    Scenario("fechar_mes", "Fechamento do mês sem inconformidades: caminho feliz", "fechar_mes"),
    Scenario("avaliar_orcamento", "Avaliação orçamentária com dois desvios plantados", "avaliar_orcamento",
             plantar=("desvio_orcamentario",)),
    Scenario("veto_waiver", "Alçada violada: veto do AG-CIN e waiver humano libera com ressalva", "fechar_mes",
             plantar=("alcada",), decisao_aprovador="waiver"),
    Scenario("veto_bloqueio", "Alçada violada sem waiver: publicação bloqueada", "fechar_mes",
             plantar=("alcada",), decisao_aprovador="nenhuma"),
    Scenario("falha_especialista", "AG-CUS expira duas vezes: um reenvio e depois failure", "fechar_mes",
             faults=({"receiver": "AG-CUS", "performative": "request", "times": 2},)),
    Scenario("depuracao", "Cenário controlado de depuração: seed 1337, SoD plantado e uma perda de mensagem",
             "fechar_mes", seed=1337, plantar=("sod", "competencia"), decisao_aprovador="waiver",
             faults=({"receiver": "AG-ORC", "performative": "request", "times": 1},)),
]}


@dataclass
class Execucao:
    scenario: Scenario
    system: System
    sid: str
    resposta: object  # última Message terminal para o solicitante

    @property
    def audit(self):
        return self.system.bus.audit

    @property
    def hash(self) -> str:
        return self.audit.digest()


def run_scenario(cenario, seed=None) -> Execucao:
    sc = CENARIOS[cenario] if isinstance(cenario, str) else cenario
    sistema = build_system(seed if seed is not None else sc.seed, sc.plantar, sc.faults, sc.decisao_aprovador)
    sid = sistema.usuario.solicitar(sc.intencao)
    sistema.bus.run()
    return Execucao(sc, sistema, sid, sistema.usuario.resposta(sid))

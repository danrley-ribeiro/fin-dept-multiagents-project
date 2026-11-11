"""Montagem do sistema e cenários nomeados (seed, plantios, falhas, decisão humana).

`build_system` liga bus, dataset, MCP, reserva de período e os seis agentes;
`run_scenario` executa um cenário e devolve a resposta final e o trace.
"""
from dataclasses import dataclass, field

from fin_mas import __version__
from fin_mas.agents.cin import AgenteControlesInternos
from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.agents.orq import Orquestrador
from fin_mas.agents.rel import VERSAO_TEMPLATE, AgenteRelatorios
from fin_mas.agents.res import AgenteResultados
from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import COMPETENCIA, ENTIDADE, VERSAO_RATEIO, Ambiente, Dataset
from fin_mas.env.empresa import EMPRESA
from fin_mas.env.portes import PORTE_PADRAO
from fin_mas.mcp.gateway import MCPGateway
from fin_mas.services.locks import LockService
from fin_mas.services.memoria import Memoria
from fin_mas.services.modelos import VERSAO_PROMPT, RegistroModelos
from fin_mas.services.politica import PRAZO_APROVACAO, PoliticaAprovacao


class Solicitante(Agent):
    """ROLE-SOL simulado: pede e guarda o que o Orquestrador responde."""

    PAPEL = "ROLE-SOL"

    def __init__(self, bus, agent_id="SOL"):
        super().__init__(agent_id, bus)
        self.recebidas = []

    def solicitar(self, intencao, entidade=ENTIDADE, competencia=COMPETENCIA, atraso=1):
        sid = self.bus.new_conversation_id("SOL")
        self.send("AG-ORQ", "request", "PROT-SOL", sid,
                  {"intencao": intencao, "entidade": entidade, "competencia": competencia}, delay=atraso)
        return sid

    def on_message(self, msg):
        self.recebidas.append(msg)

    def resposta(self, sid):
        """Última mensagem terminal recebida para a solicitação (inform, failure, refuse, not-understood)."""
        terminais = [m for m in self.recebidas
                     if m.conversation_id == sid and m.performative != "agree"]
        return terminais[-1] if terminais else None


class Aprovador(Agent):
    """ROLE-APR simulado: decide no Approval Gate (PROT-APR) conforme o roteiro do cenário.

    Recebe `propose-action` do Orquestrador com o ticket do SVC-POL e responde `approve`
    ou `reject` citando o ticket, a solicitação e o hash do veto que viu. Decisões:
    "waiver" libera com ressalva; "corrigir" aprova as correções sugeridas pelo AG-CIN
    (o gateway as executa no ERP); "corrigir_parcial" aprova só a primeira; "bloquear"
    rejeita; "nenhuma" não responde e o prazo do ticket esgota. Opção que a política não
    abriu vira silêncio (corrigir) ou rejeição (waiver). Uma sequência é consumida aviso a
    aviso (a última se repete). No modo interativo a decisão vem do dashboard (`decidir`).
    """

    PAPEL = "ROLE-APR"
    JUSTIFICATIVA = "aceito o risco: lançamento será corrigido no próximo ciclo"

    def __init__(self, bus, decisao="nenhuma", ambiente: Ambiente | None = None, interativo=False,
                 agent_id="APR"):
        super().__init__(agent_id, bus)
        self.decisoes = [decisao] if isinstance(decisao, str) else list(decisao)
        self.decisao = self.decisoes[0]
        self.ambiente = ambiente
        self.interativo = interativo
        self.avisos = []
        self.pendentes: dict[str, object] = {}  # solicitação -> proposta aguardando decisão humana

    def on_message(self, msg):
        if msg.protocol != "PROT-APR" or msg.performative != "propose-action":
            return
        self.avisos.append(msg)
        if self.bus.conversations[msg.conversation_id].is_final:
            return  # negada pela política (POL-07): só ciência, não há o que decidir
        if self.interativo:
            self.pendentes[msg.content["solicitacao"]] = msg
            return
        decisao = self.decisoes.pop(0) if len(self.decisoes) > 1 else self.decisoes[0]
        self._responder(msg, decisao, self.JUSTIFICATIVA)

    def decidir(self, solicitacao, decisao, justificativa=None) -> bool:
        msg = self.pendentes.pop(solicitacao, None)
        if msg is None:
            return False
        if decisao == "nenhuma":
            decisao = "bloquear"  # no dashboard, "não liberar" é uma rejeição explícita
        self._responder(msg, decisao, (justificativa or "").strip() or self.JUSTIFICATIVA)
        return True

    def _responder(self, msg, decisao, justificativa):
        c = msg.content
        base = {"aprovacao": msg.conversation_id, "solicitacao": c["solicitacao"], "veto": c["veto"],
                "justificativa": justificativa}
        if decisao in ("corrigir", "corrigir_parcial"):
            if "corrigir" not in c["opcoes"]:
                return  # correção não oferecida: o prazo do ticket esgota
            sugeridas = c["correcoes_sugeridas"]
            escolhidas = sugeridas[:1] if decisao == "corrigir_parcial" else sugeridas
            self.send("AG-ORQ", "approve", "PROT-APR", msg.conversation_id,
                      {**base, "decisao": "corrigir", "correcoes": escolhidas})
        elif decisao == "waiver" and "waiver" in c["opcoes"]:
            self.send("AG-ORQ", "approve", "PROT-APR", msg.conversation_id, {**base, "decisao": "waiver"})
        elif decisao in ("waiver", "bloquear"):
            if decisao == "waiver":
                base["justificativa"] = "waiver não admitido pela política; publicação permanece bloqueada"
            self.send("AG-ORQ", "reject", "PROT-APR", msg.conversation_id, base)
        # "nenhuma": silêncio deliberado; o reply_by do ticket expira a conversa


@dataclass
class System:
    bus: Bus
    dataset: Dataset  # dataset da competência principal (gabarito dos testes)
    gateway: MCPGateway
    locks: LockService
    orq: Orquestrador
    usuario: Solicitante
    aprovador: Aprovador
    agentes: dict = field(default_factory=dict)
    ambiente: Ambiente | None = None
    politica: PoliticaAprovacao | None = None
    memoria: Memoria | None = None
    modelos: RegistroModelos | None = None


PRAZO_APROVACAO_INTERATIVO = 1800  # ticks: ~10 min de parede no ritmo padrão do dashboard


def build_system(seed=42, plantar=(), faults=(), decisao_aprovador="nenhuma", ttl=200, agenda=None,
                 interativo=False, porte=PORTE_PADRAO, pasta=None, memoria=None, aprovadores=None,
                 prazo_aprovacao=None, llm=None) -> System:
    """`pasta`: planilha preenchida de uma empresa real sem ERP (substitui os dados sintéticos).

    `memoria`: caminho do arquivo do SVC-MEM (persistente entre execuções); None = só em memória.
    `aprovadores`: cadastro do SVC-POL (quem decide o quê); None = controller com todas as decisões.
    """
    bus = Bus(faults=[Fault(**f) if isinstance(f, dict) else f for f in faults])
    amb = Ambiente.de_pasta(pasta) if pasta else Ambiente(seed, plantar=plantar, agenda=agenda, porte=porte)
    ds = amb.dataset()
    prazo = prazo_aprovacao or (PRAZO_APROVACAO_INTERATIVO if interativo else PRAZO_APROVACAO)
    politica = PoliticaAprovacao(bus, aprovadores=aprovadores, prazo=prazo)
    mem = Memoria(bus.audit, lambda: bus.now, politica=politica, caminho=memoria)
    gw = MCPGateway(amb, bus.audit, bus, politica=politica)
    locks = LockService(bus.audit, lambda: bus.now, ttl=ttl)
    agentes = {"AG-CUS": AgenteCustos(bus, gw), "AG-ORC": AgenteOrcamento(bus, gw),
               "AG-RES": AgenteResultados(bus, gw), "AG-CIN": AgenteControlesInternos(bus, gw),
               "AG-REL": AgenteRelatorios(bus, gw)}
    agentes["AG-CIN"].memoria = mem.visao("AG-CIN")
    modelos = RegistroModelos(bus.audit, lambda: bus.now)
    agentes["AG-REL"].modelos = modelos
    if llm:  # flag do LLM opcional no AG-REL (ADR-002); desligada por padrão
        modelos.configurar("AG-REL", llm=True, modelo=llm)
    orq = Orquestrador(bus, locks, politica=politica, gateway=gw)
    return System(bus, ds, gw, locks, orq, Solicitante(bus), Aprovador(bus, decisao_aprovador, amb, interativo),
                  agentes, amb, politica, mem, modelos)


@dataclass(frozen=True)
class Scenario:
    nome: str
    descricao: str
    intencao: str
    seed: int = 42
    plantar: tuple = ()
    faults: tuple = ()
    decisao_aprovador: str | tuple = "nenhuma"
    agenda: tuple = ()  # ((competência, plantios), ...) para cenários com vários meses
    pedidos: tuple = ()  # ((intenção, competência, atraso), ...); vazio = um pedido de `intencao`
    porte: str = PORTE_PADRAO
    aprovadores: dict | None = None  # cadastro do SVC-POL; None = padrão (controller)
    ataques: bool = False  # dispara env/ataques.py enquanto o veto aguarda o aprovador


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
    Scenario("veto_correcao", "Alçada violada: AG-CIN veta e sugere reaprovação; humano corrige e AG-CIN reavalia",
             "fechar_mes", plantar=("alcada",), decisao_aprovador="corrigir"),
    Scenario("correcao_parcial", "Alçada e SoD: humano corrige só uma, AG-CIN mantém o veto e o prazo esgota",
             "fechar_mes", plantar=("alcada", "sod"), decisao_aprovador=("corrigir_parcial", "nenhuma")),
    Scenario("divergencia_fonte", "Planilha diverge do ERP: AG-ORC revisa a crença e adota o ERP", "avaliar_orcamento",
             plantar=("divergencia_fonte",)),
    Scenario("desvio_irregular", "Desvio inflado por NF duplicada: AG-ORC consulta o AG-CIN e reclassifica; "
             "estorno sugerido pelo AG-CIN destrava o fechamento", "fechar_mes",
             plantar=("desvio_irregular",), decisao_aprovador="corrigir"),
    Scenario("orc_sem_cin", "Consulta do AG-ORC ao AG-CIN se perde: timeout e replanejamento", "avaliar_orcamento",
             plantar=("desvio_irregular",),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},)),
    Scenario("expediente_sma", "Expediente da SMA: três competências, pedidos concorrentes, vetos, correções e "
             "divergências", "fechar_mes", decisao_aprovador=("corrigir", "waiver", "corrigir"),
             agenda=(("2026-07", ("divergencia_fonte", "competencia")), ("2026-08", ("desvio_irregular",)),
                     ("2026-09", ("alcada", "desvio_orcamentario"))),
             pedidos=(("avaliar_orcamento", "2026-07", 1), ("fechar_mes", "2026-07", 4),
                      ("fechar_mes", "2026-08", 30), ("fechar_mes", "2026-08", 34),
                      ("avaliar_orcamento", "2026-09", 70), ("fechar_mes", "2026-09", 90))),
    Scenario("fechamento_micro", "Microempresa sem ERP: planilhas, SoD inevitável tratada por controle compensatório "
             "e alçada do assistente violada", "fechar_mes", porte="micro", plantar=("alcada", "competencia"),
             decisao_aprovador="corrigir"),
    Scenario("fechamento_pequena", "EPP com sistema simples: duplicidade de NF vetada e estornada", "fechar_mes",
             porte="pequena", plantar=("duplicidade",), decisao_aprovador="corrigir"),
    Scenario("fechamento_grande", "Grande empresa: materialidade menor, competência errada já é crítica (corte)",
             "fechar_mes", porte="grande", plantar=("competencia", "desvio_orcamentario"), decisao_aprovador="corrigir"),
    Scenario("ataque_decisao_forjada", "Veto pendente sob ataque: decisão forjada, identidade falsa, transição local "
             "não autorizada, destinatário fora da conversa e pedido malformado são rejeitados; o prazo esgota e "
             "nada é publicado", "fechar_mes", plantar=("alcada",), decisao_aprovador="nenhuma", ataques=True),
    Scenario("reincidencia_waiver", "Mesma violação de alçada em dois meses: o waiver de agosto vira memória; em "
             "setembro o AG-CIN cita a memória, a política nega novo waiver e o humano corrige", "fechar_mes",
             decisao_aprovador=("waiver", "corrigir"),
             agenda=(("2026-08", ("alcada",)), ("2026-09", ("alcada",))),
             pedidos=(("fechar_mes", "2026-08", 1), ("fechar_mes", "2026-09", 60))),
]}

PEDIDOS_PLANILHA = (("avaliar_orcamento", None, 1), ("fechar_mes", None, 4))


@dataclass
class Execucao:
    scenario: Scenario
    system: System
    sid: str
    resposta: object  # última Message terminal para o solicitante
    sids: list = field(default_factory=list)  # todas as solicitações do cenário, em ordem

    @property
    def audit(self):
        return self.system.bus.audit

    @property
    def hash(self) -> str:
        return self.audit.digest()

    @property
    def respostas(self) -> dict:
        return {sid: self.system.usuario.resposta(sid) for sid in self.sids}


def montar(sc: Scenario, seed=None, interativo=False, porte=None, pasta=None, memoria=None,
           llm=None) -> tuple[System, list]:
    """Monta o sistema do cenário e agenda os pedidos (sem executar).

    `porte` troca o porte do cenário; `pasta` usa a planilha de uma empresa real (os pedidos viram
    avaliar orçamento + fechar o mês da competência da planilha).
    """
    sistema = build_system(seed if seed is not None else sc.seed, () if pasta else sc.plantar, sc.faults,
                           sc.decisao_aprovador, agenda=None if pasta else dict(sc.agenda) or None,
                           interativo=interativo, porte=porte or sc.porte, pasta=pasta, memoria=memoria,
                           aprovadores=sc.aprovadores, llm=llm)
    ds = sistema.dataset
    sistema.bus.audit.record(0, "meta", empresa={**EMPRESA, "razao_social": getattr(ds, "razao_social", None)
                                                 or EMPRESA["razao_social"], "sigla": ds.entidade},
                             cenario=sc.nome, seed=sistema.ambiente.seed, porte=ds.porte,
                             porte_titulo=ds.perfil["titulo"], tem_erp=ds.perfil["tem_erp"],
                             fonte="planilha" if pasta else "sintetico",
                             arquivo=str(getattr(ds, "arquivo", "")) or None,
                             versoes={"pacote": __version__, "normas": ds.perfil["versao"], "template": VERSAO_TEMPLATE,
                                      "rateio": VERSAO_RATEIO, "prompt": VERSAO_PROMPT},
                             llm=dict(sistema.modelos.config("AG-REL"), agente="AG-REL"),
                             identidades=dict(sistema.bus.papeis),
                             aprovadores={k: {"titulo": v["titulo"], "decisoes": v["decisoes"]}
                                          for k, v in sistema.politica.aprovadores.items()},
                             prazo_aprovacao=sistema.politica.prazo)
    if sc.ataques:
        from fin_mas.env import ataques
        ataques.preparar(sistema)
    pedidos = PEDIDOS_PLANILHA if pasta else (sc.pedidos or ((sc.intencao, None, 1),))
    sids = [sistema.usuario.solicitar(intencao, competencia=c or sistema.ambiente.principal, atraso=atraso)
            for intencao, c, atraso in pedidos]
    return sistema, sids


def run_scenario(cenario, seed=None, porte=None, pasta=None, memoria=None, llm=None) -> Execucao:
    sc = CENARIOS[cenario] if isinstance(cenario, str) else cenario
    sistema, sids = montar(sc, seed, porte=porte, pasta=pasta, memoria=memoria, llm=llm)
    sistema.bus.run()
    return Execucao(sc, sistema, sids[0], sistema.usuario.resposta(sids[0]), sids)

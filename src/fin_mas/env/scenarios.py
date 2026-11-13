"""Montagem do sistema e cenários nomeados (seed, plantios, falhas, decisão humana).

`build_system` liga bus, dataset, MCP, reserva de período e os seis agentes;
`run_scenario` executa um cenário e devolve a resposta final e o trace.
"""
from dataclasses import dataclass, field

from fin_mas import __version__
from fin_mas.agents.cin import AgenteControlesInternos
from fin_mas.agents.cus import AgenteCustos
from fin_mas.agents.cus_bdi import AgenteCustosBDI
from fin_mas.agents.orc import AgenteOrcamento
from fin_mas.agents.orq import Orquestrador
from fin_mas.agents.rel import VERSAO_TEMPLATE, AgenteRelatorios
from fin_mas.agents.rel_bdi import AgenteRelatoriosBDI
from fin_mas.agents.res import AgenteResultados
from fin_mas.agents.res_bdi import AgenteResultadosBDI
from fin_mas.cognicao import NIVEIS
from fin_mas.cognicao.llm import ProponenteLLM
from fin_mas.cognicao.perfis import COMPROMISSOS, compromisso_de, limiares
from fin_mas.cognicao.regras import REGRAS_RES, ProponenteLocal
from fin_mas.core.bdi import AgenteBDI
from fin_mas.services.aprendizado import Aprendizado
from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import COMPETENCIA, ENTIDADE, VERSAO_RATEIO, Ambiente, Dataset
from fin_mas.env.empresa import EMPRESA, PESSOAS
from fin_mas.env.portes import PORTE_PADRAO
from fin_mas.env.segmentos import SEGMENTO_PADRAO
from fin_mas.mcp.gateway import MCPGateway
from fin_mas.services.iam import CONTAS_DEMO, Acesso
from fin_mas.services.locks import LockService
from fin_mas.services.memoria import Memoria
from fin_mas.services.modelos import VERSAO_PROMPT, RegistroModelos
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.services.politica import PRAZO_APROVACAO, PoliticaAprovacao, digest_decisao


class Solicitante(Agent):
    """ROLE-SOL simulado: pede e guarda o que o Orquestrador responde."""

    PAPEL = "ROLE-SOL"

    def __init__(self, bus, agent_id="SOL"):
        super().__init__(agent_id, bus)
        self.recebidas = []

    def solicitar(self, intencao, entidade=ENTIDADE, competencia=COMPETENCIA, atraso=1, solicitado_por=None):
        """`solicitado_por`: usuário autenticado que fez o pedido (só com o SVC-IAM ligado)."""
        sid = self.bus.new_conversation_id("SOL")
        conteudo = {"intencao": intencao, "entidade": entidade, "competencia": competencia}
        if solicitado_por:
            conteudo["solicitado_por"] = solicitado_por
        self.send("AG-ORQ", "request", "PROT-SOL", sid, conteudo, delay=atraso)
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
                 agent_id="APR", acesso=None, persona="controller"):
        super().__init__(agent_id, bus)
        self.acesso = acesso  # SVC-IAM: com ele, toda decisão leva o atestado de uma pessoa (POL-09)
        self.persona = persona  # conta que decide nos cenários em lote com acesso simulado
        self.decisoes = [decisao] if isinstance(decisao, str) else list(decisao)
        self.decisao = self.decisoes[0]
        self.ambiente = ambiente
        self.interativo = interativo
        self.avisos = []
        self.pendentes: dict[str, object] = {}  # solicitação -> proposta aguardando decisão humana
        self.avalizados: set = set()  # tickets com dupla aprovação em que o aval (endorse) já foi aceito (POL-12)
        self._propostas: dict[str, object] = {}  # ticket -> proposta, para decidir de novo quando ele escala (POL-14)
        self.ultimo_performativo = None

    def on_message(self, msg):
        if msg.protocol != "PROT-APR" or msg.performative != "propose-action":
            return
        self.avisos.append(msg)
        if self.bus.conversations[msg.conversation_id].is_final:
            return  # negada pela política (POL-07): só ciência, não há o que decidir
        if self.interativo:
            self.pendentes[msg.content["solicitacao"]] = msg
            return
        if self.acesso is not None:
            self._propostas[msg.conversation_id] = msg
            self._decidir_em_lote(msg)
            return
        decisao = self.decisoes.pop(0) if len(self.decisoes) > 1 else self.decisoes[0]
        self._responder(msg, decisao, self.JUSTIFICATIVA)

    def _decidir_em_lote(self, msg) -> None:
        """Roteiro com pessoas (`"carla:corrigir"`): se a política recusa uma, a próxima do roteiro tenta.

        DSM4: `"ana@DLG-001:waiver"` decide pela delegação DLG-001 (POL-11); num ticket com dupla aprovação
        a primeira decisão aceita é o aval (endorse) e o roteiro segue até a segunda pessoa aprovar (POL-12).
        """
        while True:
            item = self.decisoes.pop(0) if len(self.decisoes) > 1 else self.decisoes[0]
            persona, _, decisao = item.rpartition(":")
            persona, _, delegacao = persona.partition("@")
            sessao = self.acesso.sessao_simulada(persona or self.persona)
            try:
                self._responder(msg, decisao, self.JUSTIFICATIVA, sessao, delegacao or None)
                if self.ultimo_performativo != "endorse":
                    return
            except (ProtocolViolation, PermissionError):
                if len(self.decisoes) <= 1 and item == self.decisoes[0]:
                    return  # roteiro esgotado: o prazo do ticket decide

    def reconsiderar(self, tid: str) -> None:
        """O ticket escalou (POL-14): o roteiro do cenário tenta de novo com o nível de cargo acima."""
        msg = self._propostas.get(tid)
        if msg is not None and not self.interativo and self.acesso is not None:
            self._decidir_em_lote(msg)

    def decidir(self, solicitacao, decisao, justificativa=None, sessao=None) -> bool:
        """Decisão humana vinda do dashboard. A pendência só sai da lista depois que a decisão
        foi aceita pelo barramento e pelo SVC-POL: se for recusada (ex.: POL-04), a exceção
        sobe e o aprovador pode decidir de novo. Devolve False se nada foi enviado.

        O waiver usa a justificativa como veio, sem texto padrão: sem justificativa humana, a
        POL-04 (ou o esquema) recusa. Bloquear e corrigir sem justificativa recebem um texto
        factual que diz que nenhuma foi informada, nunca um texto atribuído ao aprovador.
        """
        msg = self.pendentes.get(solicitacao)
        if msg is None:
            return False
        if decisao == "nenhuma":
            decisao = "bloquear"  # no dashboard, "não liberar" é uma rejeição explícita
        texto = justificativa.strip() if isinstance(justificativa, str) else ""
        if not texto and decisao != "waiver":
            texto = self.SEM_JUSTIFICATIVA.get(decisao, "")
        if not self._responder(msg, decisao, texto, sessao):
            return False
        if self.ultimo_performativo != "endorse":  # com o aval (POL-12) o ticket segue à espera da segunda pessoa
            self.pendentes.pop(solicitacao, None)
        return True

    SEM_JUSTIFICATIVA = {
        "bloquear": "publicação bloqueada pelo aprovador (sem justificativa informada)",
        "corrigir": "correções sugeridas aprovadas pelo aprovador (sem justificativa informada)",
        "corrigir_parcial": "primeira correção sugerida aprovada pelo aprovador (sem justificativa informada)",
    }

    def _responder(self, msg, decisao, justificativa, sessao=None, delegacao=None) -> bool:
        """Envia a decisão; devolve False quando não envia nada (opção não oferecida ou "nenhuma")."""
        c = msg.content
        self.ultimo_performativo = None
        base = {"aprovacao": msg.conversation_id, "solicitacao": c["solicitacao"], "veto": c["veto"],
                "justificativa": justificativa, **({"delegacao": delegacao} if delegacao else {})}
        if decisao in ("corrigir", "corrigir_parcial"):
            if "corrigir" not in c["opcoes"]:
                return False  # correção não oferecida: o prazo do ticket esgota
            sugeridas = c["correcoes_sugeridas"]
            escolhidas = sugeridas[:1] if decisao == "corrigir_parcial" else sugeridas
            self._enviar(msg, "approve", {**base, "decisao": "corrigir", "correcoes": escolhidas}, "corrigir", sessao)
        elif decisao == "waiver" and "waiver" in c["opcoes"]:
            self._enviar(msg, "approve", {**base, "decisao": "waiver"}, "waiver", sessao)
        elif decisao in ("waiver", "bloquear"):
            if decisao == "waiver":
                base["justificativa"] = "waiver não admitido pela política; publicação permanece bloqueada"
            self._enviar(msg, "reject", base, "bloquear", sessao)
        else:
            return False  # "nenhuma": silêncio deliberado; o reply_by do ticket expira a conversa
        return True

    def _enviar(self, msg, performativo, conteudo, decisao, sessao) -> None:
        """Com o SVC-IAM ligado e uma sessão, a decisão sai com o atestado da pessoa (POL-09).

        Ticket com dupla aprovação (POL-12): a primeira liberação sai como aval (`endorse`)."""
        tid = msg.conversation_id
        if performativo == "approve" and msg.content.get("dupla") and tid not in self.avalizados:
            performativo = "endorse"
        if self.acesso is not None and sessao is not None:
            conteudo = {**conteudo, "atestado": self.acesso.atestar(
                sessao, ticket=tid, veto=msg.content["veto"], decisao=decisao,
                corpo=digest_decisao(conteudo))}
        self.send("AG-ORQ", performativo, "PROT-APR", tid, conteudo)
        if performativo == "endorse":
            self.avalizados.add(tid)
        self.ultimo_performativo = performativo


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
    acesso: object | None = None  # SVC-IAM (services/iam.py), quando ligado
    aprendizado: object | None = None  # registro de aprendizado das regras locais (ADR-010), quando ligado


PRAZO_APROVACAO_INTERATIVO = 1800  # ticks: ~10 min de parede no ritmo padrão do dashboard


def build_system(seed=42, plantar=(), faults=(), decisao_aprovador="nenhuma", ttl=200, agenda=None,
                 interativo=False, porte=PORTE_PADRAO, pasta=None, memoria=None, aprovadores=None,
                 prazo_aprovacao=None, llm=None, cognicao="basico", acesso=None, compromisso=None,
                 aprendizado=None, parametros=None, caos=None, segmento=SEGMENTO_PADRAO) -> System:
    """`pasta`: planilha preenchida de uma empresa real sem ERP (substitui os dados sintéticos).

    DSM4 (ADR-010): fora do nível `basico`, AG-RES, AG-CUS e AG-REL são as variantes BDI; em `basico` são as
    classes reativas de sempre. `compromisso`: estratégia de compromisso dos agentes BDI, um texto (vale para
    todos) ou `{agente: estratégia}`; None = a do porte em models/cognicao.yaml (`aberto`). `aprendizado`:
    None = registro em memória (só nos níveis cognitivos); False = desligado; caminho = arquivo selado
    persistente entre execuções.

    `memoria`: caminho do arquivo do SVC-MEM (persistente entre execuções); None = só em memória.
    `aprovadores`: cadastro do SVC-POL (quem decide o quê); None = controller com todas as decisões.
    `cognicao`: `basico` (ciclo BDI de sempre), `local` (regras locais propõem hipóteses, offline) ou
    `llm` (regras locais e o LLM do agente, se a flag dele estiver ligada no SVC-MOD). Ver ADR-008.
    `acesso`: SVC-IAM (`services/iam.py`); `"simulado"` cria as contas de demonstração em memória, com
    o relógio lógico (cenários em lote); None = sem contas (lote da primeira versão da DSM3). Ver ADR-009.
    `parametros`: `fin_mas.parametros.Parametros` (prazos, tentativas, correções, TTL da reserva, limiares de
    desvio); None = os valores de sempre. `caos`: `fin_mas.caos.ModeloFalhas` (falhas sorteadas por seed);
    None = nenhuma. Os dois existem para o experimento da DSM4 e não mudam nada por padrão.
    `segmento`: comércio, serviços ou indústria (models/segmentos.yaml); o padrão é a SMA de sempre (DSM4).
    """
    if cognicao not in NIVEIS:
        raise ValueError(f"nível de cognição desconhecido: {cognicao} (use {', '.join(NIVEIS)})")
    bus = Bus(faults=[Fault(**f) if isinstance(f, dict) else f for f in faults], caos=caos)
    amb = Ambiente.de_pasta(pasta) if pasta else Ambiente(seed, plantar=plantar, agenda=agenda, porte=porte,
                                                           segmento=segmento)
    ds = amb.dataset()
    if parametros is not None:
        ttl, prazo_aprovacao = parametros.ttl_reserva, parametros.prazo_aprovacao or prazo_aprovacao
        parametros.aplicar_limiares(ds)
    prazo = prazo_aprovacao or (PRAZO_APROVACAO_INTERATIVO if interativo else PRAZO_APROVACAO)
    if acesso == "simulado":
        acesso = Acesso.simulado_com({u: {"nome": n, "papeis": p, "pessoa_erp": e, "cargo": c}
                                      for u, n, p, e, c in CONTAS_DEMO}, relogio=lambda: bus.now)
    compensatorio = "; ".join(f"{k}: {v}" for k, v in sorted(ds.perfil["controle_compensatorio"].items())) or None
    politica = PoliticaAprovacao(bus, aprovadores=aprovadores, prazo=prazo, acesso=acesso,
                                 controle_compensatorio=compensatorio, perfil=ds.perfil)
    mem = Memoria(bus.audit, lambda: bus.now, politica=politica, caminho=memoria)
    gw = MCPGateway(amb, bus.audit, bus, politica=politica)
    locks = LockService(bus.audit, lambda: bus.now, ttl=ttl, autenticar=bus.autenticar)
    cognitivo = cognicao != "basico"  # ADR-010: as classes reativas são o braço `basico` do experimento
    agentes = {"AG-CUS": (AgenteCustosBDI if cognitivo else AgenteCustos)(bus, gw), "AG-ORC": AgenteOrcamento(bus, gw),
               "AG-RES": (AgenteResultadosBDI if cognitivo else AgenteResultados)(bus, gw),
               "AG-CIN": AgenteControlesInternos(bus, gw),
               "AG-REL": (AgenteRelatoriosBDI if cognitivo else AgenteRelatorios)(bus, gw)}
    agentes["AG-CIN"].memoria = mem.visao("AG-CIN")
    if getattr(ds, "segmento", SEGMENTO_PADRAO) != SEGMENTO_PADRAO:  # DSM4: direcionador de rateio do segmento
        agentes["AG-CUS"].conhecimento.update(rateio=dict(ds.rateio), versao_rateio=ds.versao_rateio)
    agentes["AG-CIN"].informar_exposicao = acesso is not None  # DSM4: exposição no veto só com o SVC-IAM (POL-10)
    pessoas = [*ds.perfil["pessoas"], *(nome for nome, _ in PESSOAS.values())]
    modelos = RegistroModelos(bus.audit, lambda: bus.now, pessoas=pessoas)
    for agente in ("AG-REL", "AG-RES", "AG-ORC"):  # os três em que a NORM-07 permite LLM
        agentes[agente].modelos = modelos
    # flag do LLM opcional (ADR-002), desligada por padrão. Texto = apelido de modelo só para a síntese do AG-REL
    # (forma da primeira versão da DSM3); dicionário = configuração por agente (ADR-008).
    for agente, campos in ({"AG-REL": {"modelo": llm}} if isinstance(llm, str) else dict(llm or {})).items():
        modelos.configurar(agente, llm=True, **campos)
    registro = None
    if cognitivo:  # ADR-008: hipóteses propostas por regras locais (e por LLM, no nível `llm`)
        agentes["AG-ORC"].proponentes.append(ProponenteLocal())
        agentes["AG-RES"].proponentes.append(ProponenteLocal(REGRAS_RES))  # causa da variação de indicador (ADR-010)
        agentes["AG-CIN"].base_normativa = True  # CP8: achados citam a base normativa (tool normas.buscar)
        for agente in ("AG-ORC", "AG-RES", "AG-REL"):  # leitura da memória aprovada, por tipo (SVC-MEM)
            agentes[agente].memoria = mem.visao(agente)
        if aprendizado is not False:
            registro = Aprendizado(bus.audit, lambda: bus.now, caminho=aprendizado if isinstance(aprendizado, str) else None,
                                   peso_do_prior=limiares()["peso_do_prior"])
            for agente in ("AG-ORC", "AG-RES"):
                agentes[agente].aprendizado = registro
    if cognicao == "llm":
        agentes["AG-ORC"].proponentes.append(ProponenteLLM(modelos))
    for nome, agente in agentes.items():  # estratégia de compromisso por agente e porte (ADR-010)
        if not isinstance(agente, AgenteBDI):
            continue
        estrategia = (compromisso if isinstance(compromisso, str) else (compromisso or {}).get(nome)) \
            or compromisso_de(ds.porte, nome)
        if estrategia not in COMPROMISSOS:
            raise ValueError(f"estratégia de compromisso desconhecida: {estrategia} (use {', '.join(COMPROMISSOS)})")
        if estrategia != agente.compromisso:
            agente.compromisso = estrategia
    orq = Orquestrador(bus, locks, politica=politica, gateway=gw, parametros=parametros)
    sistema = System(bus, ds, gw, locks, orq, Solicitante(bus),
                     Aprovador(bus, decisao_aprovador, amb, interativo, acesso=acesso),
                     agentes, amb, politica, mem, modelos, acesso, registro)
    if caos is not None:  # modelo de falhas do experimento (DSM4): instala antes de fechar o registro
        caos.instalar(sistema)
    bus.fechar_registro()  # ninguém fora do diretório entra depois de o sistema estar montado
    return sistema


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
    cognicao: str = "basico"  # basico | local | llm (ADR-008); os cenários revisados ficam em `basico`
    llm: tuple = ()  # ((agente, ((campo, valor), ...)), ...): configuração de LLM por agente (mocks, nos cenários)
    acesso: bool = False  # liga o SVC-IAM com as contas de demonstração em memória (ADR-009)
    solicitante: str | None = None  # conta que faz os pedidos, nos cenários com acesso
    ataques_acesso: bool = False  # dispara env/ataques_acesso.py enquanto o veto aguarda o aprovador
    # DSM4 (ADR-012), só com `acesso`: delegações ((de, para, ate, teto, competência), ...), política do cadastro
    # ((campo, valor), ...) e os ataques de env/ataques_acesso_avancado.py
    delegacoes: tuple = ()
    politica_acesso: tuple = ()
    ataques_acesso_avancado: bool = False
    esperado: str = ""  # o que observar ao rodar o cenário (catálogo de cenários de teste)
    compromisso: tuple = ()  # ((agente, estratégia), ...): cego | obstinado | aberto (ADR-010); vazio = a do porte
    segmento: str = SEGMENTO_PADRAO  # DSM4: comércio, serviços, indústria (models/segmentos.yaml)


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
    # ---- DSM3: cognição local (ADR-008). Os cenários acima ficam em `basico`. ----
    Scenario("orc_hipotese_local", "Mesma perda de `orc_sem_cin`, com cognição local: a observação da planilha gera "
             "a hipótese de causa de controle, o AG-ORC consulta de novo o AG-CIN e o desvio é reclassificado",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             esperado="hipótese confirmada pelo AG-CIN (QRY-002); conta atribuída a controle, sem falso desvio"),
    Scenario("hipotese_refutada", "Desvio orçamentário legítimo com um alarme falso na planilha: a hipótese de "
             "controle é conferida com a resposta que o AG-CIN já deu e refutada; o desvio segue sinalizado",
             "avaliar_orcamento", plantar=("desvio_orcamentario", "observacao_alarme_falso"), cognicao="local",
             esperado="hipótese refutada sem mensagem extra (P-CONFERIR-EVIDENCIA); os dois desvios sinalizados"),
    Scenario("hipotese_arquivada", "AG-CIN não responde a nenhuma das duas consultas: a hipótese fica sem evidência, "
             "é arquivada e a avaliação sai igual à da cognição básica",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 3},),
             esperado="três consultas perdidas (uma delas com prazo negociado); hipótese arquivada; ressalva de AG-CIN indisponível"),
    Scenario("negociacao_prazo", "Duas consultas ao AG-CIN se perdem e a terceira não cabe no prazo: o AG-ORC negocia "
             "mais prazo com o Orquestrador, que aceita; a hipótese é confirmada e o desvio reclassificado",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 2},),
             esperado="propose e accept-proposal no PROT-DEL; QRY-003 respondida; sem falso desvio; nenhum timeout da subtarefa"),
    Scenario("negociacao_recusada", "No fechamento com período reservado o Orquestrador recusa a extensão de prazo: o "
             "AG-ORC arquiva a hipótese e entrega no prazo; o AG-CIN veta a NF duplicada depois e o estorno é aprovado",
             "fechar_mes", plantar=("desvio_irregular",), cognicao="local", decisao_aprovador="corrigir",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 2},),
             esperado="propose e reject-proposal (período reservado); hipótese arquivada; fechamento publicado após a correção"),
    Scenario("historico_calendario", "Gasto concentrado no início do trimestre: a hipótese de efeito de calendário "
             "é conferida em todos os trimestres do histórico e entra no relatório como insight",
             "avaliar_orcamento", cognicao="local", agenda=(("2026-07", ("desvio_sazonal",)),),
             pedidos=(("avaliar_orcamento", "2026-07", 1),),
             esperado="hipótese efeito_temporal confirmada pelo histórico; desvio sinalizado com ressalva de calendário"),
    Scenario("fechamento_hipotese_local", "Fechamento do mês com a consulta ao AG-CIN perdida: a hipótese leva o "
             "AG-ORC a consultar de novo, o AG-CIN veta a NF duplicada e o estorno aprovado destrava o fechamento",
             "fechar_mes", plantar=("desvio_irregular",), cognicao="local", decisao_aprovador="corrigir",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             esperado="hipótese confirmada; veto com estorno aprovado; relatório publicado com o insight"),
    # ---- DSM3: decisão por pessoa autenticada (SVC-IAM com contas em memória, ADR-009) ----
    Scenario("decisao_por_pessoa", "SoD plantado por uma gerente: ela tenta decidir sobre o próprio lançamento e a "
             "política recusa (POL-03); outro gerente decide e o fechamento é publicado",
             "fechar_mes", plantar=("sod",), acesso=True, solicitante="elisa",
             decisao_aprovador=("carla:corrigir", "diego:corrigir"),
             esperado="decisão de carla rejeitada (POL-03); ticket aprovado por diego; relatório publicado"),
    Scenario("solicitante_nao_aprova", "A diretora que pediu o fechamento tenta aprovar a correção do veto: recusada "
             "(POL-13); o controller decide",
             "fechar_mes", plantar=("alcada",), acesso=True, solicitante="elisa",
             decisao_aprovador=("elisa:corrigir", "controller:corrigir"),
             esperado="decisão de elisa rejeitada (POL-13); ticket aprovado pelo controller"),
    Scenario("waiver_exige_cargo", "Uma analista com papel de aprovadora tenta conceder waiver: o cargo dela só "
             "corrige ou bloqueia (POL-02); a gerente concede",
             "fechar_mes", plantar=("sod",), acesso=True, solicitante="elisa",
             decisao_aprovador=("ana:waiver", "diego:waiver"),
             esperado="waiver de ana rejeitado (POL-02); waiver de diego aceito; publicado com ressalva"),
    Scenario("micro_controle_compensatorio", "Microempresa: a mesma pessoa pede e decide. A POL-13 cede ao controle "
             "compensatório do porte, que fica anotado na decisão",
             "fechar_mes", porte="micro", plantar=("alcada", "competencia"), acesso=True, solicitante="controller",
             decisao_aprovador="controller:corrigir",
             esperado="decisão aceita com controle_compensatorio registrado; fechamento publicado"),
    Scenario("ataque_acesso", "Veto pendente sob ataque de quem controla a caixa APR mas não é a pessoa certa: sem "
             "atestado, atestado forjado, de outra decisão, de sessão revogada, replay, cargo sem alçada, aprovador "
             "envolvido, solicitante decidindo e escalada de privilégio. Tudo recusado; nada é publicado",
             "fechar_mes", plantar=("alcada",), acesso=True, solicitante="elisa", decisao_aprovador="nenhuma",
             ataques_acesso=True,
             esperado="15 ataques rejeitados (POL-02, 03, 09, 13 e IAM-05, 06); prazo esgota; nada publicado"),
    # ---- DSM4: acesso avançado (ADR-012): alçada, delegação, dupla aprovação e escalonamento ----
    Scenario("aprovador_sem_alcada", "Microempresa: uma gerente com papel de aprovadora tenta liberar a correção, mas "
             "as normas do porte só dão alçada ao assistente e ao sócio (POL-10); o controller corrige",
             "fechar_mes", porte="micro", plantar=("alcada", "competencia"), acesso=True, solicitante="controller",
             decisao_aprovador=("carla:corrigir", "controller:corrigir"),
             esperado="correção de carla recusada (POL-10, gerente sem alçada no porte); o controller corrige; publicado"),
    Scenario("delegacao_valida", "O gerente delega à analista a sua alçada para a competência, com teto de R$ 10 mil; "
             "ela concede o waiver que o cargo dela sozinho não permitiria, e a decisão registra a delegação",
             "fechar_mes", plantar=("sod",), acesso=True, solicitante="elisa",
             delegacoes=(("diego", "ana", 10_000, 1_000_000, None),), decisao_aprovador="ana@DLG-001:waiver",
             esperado="waiver de ana por delegação de diego (DLG-001) aceito; publicado com ressalva"),
    Scenario("delegacao_expirada", "Mesma delegação, mas com prazo que termina antes do veto: a analista não decide "
             "mais por ela (POL-11) e o próprio gerente concede o waiver",
             "fechar_mes", plantar=("sod",), acesso=True, solicitante="elisa",
             delegacoes=(("diego", "ana", 5, 1_000_000, None),), decisao_aprovador=("ana@DLG-001:waiver", "diego:waiver"),
             esperado="waiver de ana recusado (POL-11, delegação expirada); waiver de diego aceito"),
    Scenario("dupla_aprovacao", "Grande empresa: a correção de R$ 30 mil passa do limite de quatro olhos (R$ 25 mil); "
             "uma gerente dá o aval e o outro gerente aprova",
             "fechar_mes", porte="grande", plantar=("alcada",), acesso=True, solicitante="elisa",
             decisao_aprovador=("carla:corrigir", "diego:corrigir"),
             esperado="endorse de carla (PENDENTE->PENDENTE), approve de diego; aprovado_por com o aval; publicado"),
    Scenario("dupla_mesma_pessoa_recusada", "Grande empresa: a gerente que deu o aval tenta também aprovar; a política "
             "recusa (POL-12) e a segunda aprovação vem de outra pessoa",
             "fechar_mes", porte="grande", plantar=("alcada",), acesso=True, solicitante="elisa",
             decisao_aprovador=("carla:corrigir", "carla:corrigir", "diego:corrigir"),
             esperado="aprovação de carla depois do próprio aval recusada (POL-12); diego aprova; publicado"),
    Scenario("escalonamento", "Ticket no nível de gerente: a diretora tenta decidir antes e é recusada (POL-14); sem "
             "decisão na metade do prazo o ticket escala para diretor e a decisão dela vale",
             "fechar_mes", plantar=("sod",), acesso=True, solicitante="ana", decisao_aprovador="elisa:corrigir",
             politica_acesso=(("escalonamento_percentual", 50),),
             esperado="elisa recusada (POL-14) antes; ticket escalado de gerente para diretor; elisa aprova depois"),
    Scenario("ataque_acesso_avancado", "Veto pendente sob ataques ao acesso avançado: código TOTP repetido e fora da "
             "janela, código de recuperação reutilizado, pré-sessão usada como sessão, delegação forjada, expirada e "
             "subdelegada, a mesma pessoa nos dois passos, decisão acima da alçada e sessão de outra empresa. Tudo "
             "recusado; nada é publicado",
             "fechar_mes", porte="grande", plantar=("alcada",), acesso=True, solicitante="elisa",
             decisao_aprovador="nenhuma", ataques_acesso_avancado=True,
             esperado="ataques rejeitados (IAM-04, 08, 09, POL-10, 11, 12); prazo esgota; nada publicado"),
    # ---- DSM3: LLM opcional como proponente e redator, sempre com mocks offline (ADR-008) ----
    Scenario("orc_hipotese_llm", "A planilha descreve o lançamento repetido com outras palavras: as regras locais "
             "não propõem nada, o LLM (mock) propõe, o AG-CIN confirma e o desvio é reclassificado",
             "avaliar_orcamento", plantar=("desvio_irregular", "observacao_parafraseada"), cognicao="llm",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-analista"), ("usos", ("hipoteses",)))),),
             esperado="hipótese de origem llm confirmada pelo AG-CIN; sem falso desvio"),
    Scenario("llm_hipotese_rejeitada", "O LLM (mock) devolve propostas com número inventado, alvo inexistente, tipo "
             "fora da lista, ação e evidência que o agente não tem: todas rejeitadas, nada muda",
             "avaliar_orcamento", plantar=("desvio_irregular", "observacao_parafraseada"), cognicao="llm",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-analista-ruim"), ("usos", ("hipoteses",)))),),
             esperado="cinco propostas rejeitadas (NORM-11); resposta igual à da cognição básica"),
    Scenario("llm_nota_injetada", "A observação da planilha traz uma instrução para o modelo; o LLM (mock) obedece e "
             "a proposta é rejeitada: texto livre é dado, não instrução",
             "avaliar_orcamento", plantar=("desvio_orcamentario", "nota_injetada"), cognicao="llm",
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-injetado"), ("usos", ("hipoteses",)))),),
             esperado="proposta 'dentro_do_limiar' rejeitada; os dois desvios seguem sinalizados"),
    Scenario("llm_json_invalido", "O LLM (mock) responde fora do formato: fallback registrado e avaliação determinística",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="llm",
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-json-invalido"), ("usos", ("hipoteses",)))),),
             esperado="llm_fallback 'resposta fora do formato'; a hipótese local segue o caminho normal"),
    Scenario("llm_provedor_fora", "Provedor de LLM fora do ar em dois meses seguidos: cada chamada cai no fallback, "
             "o disjuntor abre na terceira e as avaliações saem pelo caminho determinístico",
             "avaliar_orcamento", cognicao="llm",
             agenda=(("2026-08", ("desvio_orcamentario",)), ("2026-09", ("desvio_orcamentario",))),
             pedidos=(("avaliar_orcamento", "2026-08", 1), ("avaliar_orcamento", "2026-09", 40)),
             llm=(("AG-ORC", (("provedor", "openai-compat"), ("modelo", "modelo-local"),
                              ("base_url", "http://127.0.0.1:9/v1"), ("usos", ("hipoteses", "narrativa")))),),
             esperado="duas falhas do provedor, depois disjuntor aberto; as duas avaliações publicadas"),
    Scenario("llm_sem_consentimento", "Provedor externo configurado sem consentimento para enviar dados: nada sai "
             "da máquina e o agente segue no caminho determinístico",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="llm",
             llm=(("AG-ORC", (("provedor", "openai"), ("modelo", "modelo-externo"), ("usos", ("hipoteses",)))),),
             esperado="llm_fallback NORM-06 'sem consentimento'; nenhum llm_prompt registrado"),
    Scenario("llm_pseudonimos", "Envio com pseudônimos: o prompt registrado troca fornecedor e documento por rótulos "
             "e o insight volta com os nomes reais",
             "avaliar_orcamento", plantar=("desvio_irregular", "observacao_parafraseada"), cognicao="llm",
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-analista"), ("usos", ("hipoteses",)),
                              ("pseudonimizar", True))),),
             esperado="prompt com FORNECEDOR-A e sem F-77; insight com F-77; hipótese confirmada"),
    Scenario("llm_textos_validados", "Fechamento com os três textos opcionais: narrativa do AG-ORC, comentário do "
             "AG-RES e síntese do AG-REL (mocks), cada um conferido contra os números do seu agente",
             "fechar_mes", plantar=("desvio_orcamentario",),
             llm=(("AG-ORC", (("provedor", "mock"), ("modelo", "mock-narrador"), ("usos", ("narrativa",)))),
                  ("AG-RES", (("provedor", "mock"), ("modelo", "mock-narrador"), ("usos", ("comentario",)))),
                  ("AG-REL", (("provedor", "mock"), ("modelo", "mock-narrador"), ("usos", ("sintese",))))),
             esperado="três chamadas de LLM registradas, uma por agente; nenhum número fora do texto-base"),
    # ---- DSM4: todos os especialistas BDI, aprendizado, compromisso, memória lida e base normativa (ADR-010) ----
    Scenario("res_explica_variacao", "Um centro de custo salta no mês e o EBITDA% cai contra o histórico: o AG-RES "
             "recebe a hipótese de custo fixo, pede o detalhe ao AG-CUS e explica a variação com o centro responsável",
             "fechar_mes", plantar=("variacao_custo_fixo",), cognicao="local",
             esperado="hipótese causa_custo_fixo confirmada por cálculo sobre AG-CUS e histórico; explicação aponta CC-OPS; insight no relatório"),
    Scenario("res_insumo_faltante", "O AG-ORC não responde a duas consultas do AG-RES: o plano de consulta falha, o "
             "agente consulta de novo, dá o orçamento por indisponível e decide, pelo porte e pela criticidade, "
             "consolidar a DRE com ressalva (na grande empresa a mesma situação termina em falha explícita)",
             "fechar_mes", cognicao="local",
             faults=({"receiver": "AG-ORC", "performative": "query-ref", "times": 2},),
             esperado="P-CONSULTAR-ESPECIALISTA falha, P-CONSULTAR-DE-NOVO falha, P-DAR-POR-INDISPONIVEL; P-CONSOLIDAR-COM-RESSALVA; publicado com ressalva, sem reenvio do Orquestrador"),
    Scenario("cus_rateio_alternativo", "O direcionador de rateio do período está inconsistente (soma 110): o plano "
             "padrão do AG-CUS falha ao ler o dado e o agente escolhe outro critério conforme o porte, registrando "
             "o critério e o motivo",
             "fechar_mes", plantar=("direcionador_inconsistente",), cognicao="local",
             esperado="P-RATEIO-PADRAO falha; P-RATEIO-PROPORCIONAL-RECEITA escolhido (média); resultado por UN igual ao gabarito do critério; ressalva no relatório"),
    Scenario("rel_relatorio_de_excecao", "Veto de alçada corrigido por decisão humana: o AG-REL escolhe o relatório de "
             "exceção, que abre pela correção aprovada e cita a base normativa; sem exceção ele escolhe o sumário",
             "fechar_mes", plantar=("alcada",), decisao_aprovador="corrigir", cognicao="local",
             esperado="P-RELATORIO-DE-EXCECAO escolhido; exceção antes dos indicadores; base normativa COSO-ALCADA; texto por template"),
    Scenario("aprendizado_regra", "A regra da observação de duplicidade dá alarme falso em julho e em agosto: as duas "
             "refutações baixam a confiança dela de 0,80 para 0,40; em setembro, com o AG-CIN sem responder, a "
             "hipótese não justifica mais uma consulta nova e é arquivada",
             "avaliar_orcamento", cognicao="local",
             agenda=tuple((c, ("desvio_orcamentario", "observacao_alarme_falso")) for c in ("2026-07", "2026-08", "2026-09")),
             pedidos=(("avaliar_orcamento", "2026-07", 1), ("avaliar_orcamento", "2026-08", 50),
                      ("avaliar_orcamento", "2026-09", 100)),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 2, "competencia": "2026-09"},),
             esperado="duas observações 'refutada' de local:R-OBS-REPETICAO; hipótese de setembro com confiança 0,40; P-VERIFICAR-COM-CIN não aplicável; uma consulta a menos que sem aprendizado"),
    Scenario("compromisso_aberto", "Consulta ao AG-CIN perdida e, depois, resposta que derruba o motivo do alerta: com "
             "compromisso aberto o AG-ORC replaneja na falha e abandona o alerta quando o motivo cai",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local", compromisso=(("AG-ORC", "aberto"),),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             esperado="P-CONSULTAR-CIN falha e é replanejado; P-SINALIZAR abandonada por reconsideração; conta atribuída a controle (igual ao gabarito)"),
    Scenario("compromisso_obstinado", "Mesma situação com compromisso obstinado: o AG-ORC replaneja na falha, mas não "
             "larga o alerta quando o motivo cai (a intenção ainda é possível) e sinaliza um falso desvio",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local", compromisso=(("AG-ORC", "obstinado"),),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             esperado="P-SINALIZAR 'mantida' e concluída; conta sinalizada como desvio orçamentário (diferente do gabarito)"),
    Scenario("compromisso_cego", "Mesma situação com compromisso cego: o AG-ORC insiste na mesma consulta em vez de "
             "replanejar e também não larga o alerta: falso desvio, por outro caminho",
             "avaliar_orcamento", plantar=("desvio_irregular",), cognicao="local", compromisso=(("AG-ORC", "cego"),),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},),
             esperado="P-CONSULTAR-CIN 'insistida' (sem replanejar); P-SINALIZAR mantida; falso desvio"),
    Scenario("memoria_reincidencia_orc", "Em agosto um estorno de NF duplicada em Marketing é aprovado e vira memória. "
             "Em setembro a planilha não fala em duplicidade e a consulta ao AG-CIN se perde: o AG-ORC lê a memória "
             "aprovada, levanta a hipótese de reincidência, consulta de novo e reclassifica o desvio",
             "fechar_mes", cognicao="local", decisao_aprovador="corrigir",
             agenda=(("2026-08", ("desvio_irregular",)), ("2026-09", ("desvio_irregular", "observacao_parafraseada"))),
             pedidos=(("fechar_mes", "2026-08", 1), ("avaliar_orcamento", "2026-09", 100)),
             faults=({"receiver": "AG-CIN", "performative": "query-ref", "times": 1, "competencia": "2026-09"},),
             esperado="memória 'correcao' consultada pelo AG-ORC; hipótese de origem local:R-MEM-REINCIDENCIA confirmada pelo AG-CIN; sem falso desvio em setembro"),
    Scenario("normas_fundamentam_achado", "SoD crítica vetada e liberada por waiver: o AG-CIN busca na base normativa o "
             "trecho que fundamenta o achado e o cita com documento, trecho e versão",
             "fechar_mes", plantar=("sod",), decisao_aprovador="waiver", cognicao="local",
             esperado="achado de sod com fundamento COSO-2013, trecho COSO-SEGREGACAO (corpus-v1) no veto; o relatório de exceção cita a mesma base"),
    Scenario("normas_sem_evidencia", "NF duplicada vetada e estornada: a base normativa não tem trecho sobre "
             "duplicidade, a busca devolve vazio e o AG-CIN declara 'sem evidência' em vez de citar algo aproximado",
             "fechar_mes", plantar=("duplicidade",), decisao_aprovador="corrigir", cognicao="local",
             esperado="normas.buscar devolve zero trechos para duplicidade; achado marcado 'sem evidência'; o veto vale pela regra interna"),
    # ---- DSM4: portes novos (MEI e Média empresa II) e segmentos (models/segmentos.yaml). Ficam em `basico`,
    # como fechamento_micro/pequena/grande: o que muda é a regra do porte e a forma do segmento, não a cognição.
    Scenario("fechamento_mei", "MEI: uma pessoa só, sem ERP; toda a segregação é impossível e vira controle "
             "compensatório; a NF duplicada é vetada e estornada, a competência errada fica como ressalva",
             "fechar_mes", porte="mei", plantar=("duplicidade", "competencia"), decisao_aprovador="corrigir",
             esperado="veto só da duplicidade (crítica); estorno aprovado; SoD e competência viram ressalvas; "
                      "realizado da planilha"),
    Scenario("fechamento_media_ii", "Média empresa II (BNDES, R$ 90 a 300 milhões): alçadas e materialidade da "
             "faixa de cima; alçada violada é reaprovada e os desvios orçamentários entram no relatório",
             "fechar_mes", porte="media_ii", plantar=("alcada", "desvio_orcamentario"), decisao_aprovador="corrigir",
             esperado="veto da alçada com reaprovação; dois desvios acima de 7% e de R$ 20 mil; publicado"),
    Scenario("fechamento_comercio", "Comércio: CMV pelo estoque, lojas física e virtual e rateio por área ocupada; "
             "NF duplicada de fornecedor vetada e estornada", "fechar_mes", segmento="comercio",
             plantar=("duplicidade",), decisao_aprovador="corrigir",
             esperado="AG-CUS rateia por m² (80/20); estorno aprovado; relatório publicado"),
    Scenario("fechamento_servicos", "Serviços profissionais: mão de obra direta como custo variável e rateio por "
             "horas trabalhadas; a gerente aprova o próprio lançamento (SoD) e outro aprovador reaprova",
             "fechar_mes", segmento="servicos", plantar=("sod",), decisao_aprovador="corrigir",
             esperado="AG-CUS rateia por horas (65/35); SoD vetado e reaprovado; relatório publicado"),
    Scenario("fechamento_industria", "Indústria: custo de produção e rateio dos custos fixos por horas-máquina; NF "
             "lançada duas vezes na conta de marketing infla o desvio; o AG-CIN veta e o estorno destrava",
             "fechar_mes", segmento="industria", plantar=("desvio_irregular",), decisao_aprovador="corrigir",
             esperado="AG-CUS rateia por horas-máquina (70/30); desvio atribuído a controle; estorno aprovado"),
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
           llm=None, cognicao=None, acesso=None, compromisso=None, aprendizado=None, parametros=None,
           caos=None, segmento=None) -> tuple[System, list]:
    """Monta o sistema do cenário e agenda os pedidos (sem executar).

    `porte` troca o porte do cenário; `pasta` usa a planilha de uma empresa real (os pedidos viram
    avaliar orçamento + fechar o mês da competência da planilha).
    """
    sistema = build_system(seed if seed is not None else sc.seed, () if pasta else sc.plantar, sc.faults,
                           sc.decisao_aprovador, agenda=None if pasta else dict(sc.agenda) or None,
                           interativo=interativo, porte=porte or sc.porte, pasta=pasta, memoria=memoria,
                           aprovadores=sc.aprovadores, llm=llm or {a: dict(campos) for a, campos in sc.llm} or None,
                           cognicao=cognicao or sc.cognicao, acesso=acesso or ("simulado" if sc.acesso else None),
                           compromisso=compromisso or dict(sc.compromisso) or None, aprendizado=aprendizado,
                           parametros=parametros, caos=caos, segmento=segmento or sc.segmento)
    ds = sistema.dataset
    extras = {} if (cognicao or sc.cognicao) == "basico" else {"cognicao": cognicao or sc.cognicao}
    estrategias = {a: ag.compromisso for a, ag in sistema.agentes.items() if getattr(ag, "compromisso", "aberto") != "aberto"}
    if estrategias:  # só aparece quando algum agente sai do compromisso aberto (ADR-010)
        extras["compromisso"] = estrategias
    if aprendizado is False and extras:
        extras["aprendizado"] = "desligado"
    if getattr(ds, "segmento", SEGMENTO_PADRAO) != SEGMENTO_PADRAO:  # só fora do padrão: traces antigos intactos
        extras["segmento"] = {"segmento": ds.segmento, "titulo": ds.perfil_segmento["titulo"] if hasattr(
            ds, "perfil_segmento") else ds.segmento, "versao_rateio": getattr(ds, "versao_rateio", None)}
    outros = {a: sistema.modelos.situacao(a) for a in ("AG-ORC", "AG-RES") if sistema.modelos.config(a)["llm"]}
    if outros:
        extras["llm_agentes"] = outros
    if sistema.acesso is not None:
        extras["acesso"] = {"modo": "simulado" if sistema.acesso.simulado else "contas", "solicitante": sc.solicitante}
    if parametros is not None and parametros.diferencas():  # só no experimento da DSM4
        extras["parametros"] = parametros.diferencas()
    if caos is not None:
        extras["caos"] = caos.descricao()
    sistema.bus.audit.record(0, "meta", **extras, empresa={**EMPRESA, "razao_social": getattr(ds, "razao_social", None)
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
    if sc.ataques_acesso:
        from fin_mas.env import ataques_acesso
        ataques_acesso.preparar(sistema)
    if sistema.acesso is not None and sistema.acesso.simulado:
        _preparar_acesso_avancado(sistema, sc)
    pedidos = PEDIDOS_PLANILHA if pasta else (sc.pedidos or ((sc.intencao, None, 1),))
    sids = [sistema.usuario.solicitar(intencao, competencia=c or sistema.ambiente.principal, atraso=atraso,
                                      solicitado_por=sc.solicitante if sistema.acesso is not None else None)
            for intencao, c, atraso in pedidos]
    return sistema, sids


def _preparar_acesso_avancado(sistema, sc) -> None:
    """DSM4: política do cadastro, delegações e ataques avançados de um cenário com acesso simulado."""
    acesso = sistema.acesso
    sistema.politica.ao_escalar.append(sistema.aprovador.reconsiderar)
    if sc.politica_acesso:
        acesso.definir_politica(acesso.sessao_simulada("admin"), **dict(sc.politica_acesso))
    for de, para, ate, teto, competencia in sc.delegacoes:
        acesso.delegar(acesso.sessao_simulada(de), para, ate=ate, teto=teto,
                       competencia=competencia or sistema.ambiente.principal)
    if sc.ataques_acesso_avancado:
        from fin_mas.env import ataques_acesso_avancado
        ataques_acesso_avancado.preparar(sistema)


def run_scenario(cenario, seed=None, porte=None, pasta=None, memoria=None, llm=None, cognicao=None,
                 compromisso=None, aprendizado=None, parametros=None, caos=None, segmento=None) -> Execucao:
    sc = CENARIOS[cenario] if isinstance(cenario, str) else cenario
    sistema, sids = montar(sc, seed, porte=porte, pasta=pasta, memoria=memoria, llm=llm, cognicao=cognicao,
                           compromisso=compromisso, aprendizado=aprendizado, parametros=parametros, caos=caos,
                           segmento=segmento)
    sistema.bus.run()
    return Execucao(sc, sistema, sids[0], sistema.usuario.resposta(sids[0]), sids)

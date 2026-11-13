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
from fin_mas.cognicao import NIVEIS
from fin_mas.cognicao.llm import ProponenteLLM
from fin_mas.cognicao.regras import ProponenteLocal
from fin_mas.core.agent import Agent
from fin_mas.core.bus import Bus, Fault
from fin_mas.env.dataset import COMPETENCIA, ENTIDADE, VERSAO_RATEIO, Ambiente, Dataset
from fin_mas.env.empresa import EMPRESA, PESSOAS
from fin_mas.env.portes import PORTE_PADRAO
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
            self._decidir_em_lote(msg)
            return
        decisao = self.decisoes.pop(0) if len(self.decisoes) > 1 else self.decisoes[0]
        self._responder(msg, decisao, self.JUSTIFICATIVA)

    def _decidir_em_lote(self, msg) -> None:
        """Roteiro com pessoas (`"carla:corrigir"`): se a política recusa uma, a próxima do roteiro tenta."""
        while True:
            item = self.decisoes.pop(0) if len(self.decisoes) > 1 else self.decisoes[0]
            persona, _, decisao = item.rpartition(":")
            sessao = self.acesso.sessao_simulada(persona or self.persona)
            try:
                self._responder(msg, decisao, self.JUSTIFICATIVA, sessao)
                return
            except (ProtocolViolation, PermissionError):
                if len(self.decisoes) <= 1 and item == self.decisoes[0]:
                    return  # roteiro esgotado: o prazo do ticket decide

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
        self.pendentes.pop(solicitacao, None)
        return True

    SEM_JUSTIFICATIVA = {
        "bloquear": "publicação bloqueada pelo aprovador (sem justificativa informada)",
        "corrigir": "correções sugeridas aprovadas pelo aprovador (sem justificativa informada)",
        "corrigir_parcial": "primeira correção sugerida aprovada pelo aprovador (sem justificativa informada)",
    }

    def _responder(self, msg, decisao, justificativa, sessao=None) -> bool:
        """Envia a decisão; devolve False quando não envia nada (opção não oferecida ou "nenhuma")."""
        c = msg.content
        base = {"aprovacao": msg.conversation_id, "solicitacao": c["solicitacao"], "veto": c["veto"],
                "justificativa": justificativa}
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
        """Com o SVC-IAM ligado e uma sessão, a decisão sai com o atestado da pessoa (POL-09)."""
        if self.acesso is not None and sessao is not None:
            conteudo = {**conteudo, "atestado": self.acesso.atestar(
                sessao, ticket=msg.conversation_id, veto=msg.content["veto"], decisao=decisao,
                corpo=digest_decisao(conteudo))}
        self.send("AG-ORQ", performativo, "PROT-APR", msg.conversation_id, conteudo)


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


PRAZO_APROVACAO_INTERATIVO = 1800  # ticks: ~10 min de parede no ritmo padrão do dashboard


def build_system(seed=42, plantar=(), faults=(), decisao_aprovador="nenhuma", ttl=200, agenda=None,
                 interativo=False, porte=PORTE_PADRAO, pasta=None, memoria=None, aprovadores=None,
                 prazo_aprovacao=None, llm=None, cognicao="basico", acesso=None, ambiente=None) -> System:
    """`pasta`: planilha preenchida de uma empresa real sem ERP (substitui os dados sintéticos).

    `memoria`: caminho do arquivo do SVC-MEM (persistente entre execuções); None = só em memória.
    `aprovadores`: cadastro do SVC-POL (quem decide o quê); None = controller com todas as decisões.
    `cognicao`: `basico` (ciclo BDI de sempre), `local` (regras locais propõem hipóteses, offline) ou
    `llm` (regras locais e o LLM do agente, se a flag dele estiver ligada no SVC-MOD). Ver ADR-008.
    `acesso`: SVC-IAM (`services/iam.py`); `"simulado"` cria as contas de demonstração em memória, com
    o relógio lógico (cenários em lote); None = sem contas (lote da primeira versão da DSM3). Ver ADR-009.
    """
    if cognicao not in NIVEIS:
        raise ValueError(f"nível de cognição desconhecido: {cognicao} (use {', '.join(NIVEIS)})")
    bus = Bus(faults=[Fault(**f) if isinstance(f, dict) else f for f in faults])
    # `ambiente`: fonte por conector (Ambiente.de_conector, ADR-011); substitui `pasta` e os dados sintéticos
    amb = ambiente if ambiente is not None else \
        Ambiente.de_pasta(pasta) if pasta else Ambiente(seed, plantar=plantar, agenda=agenda, porte=porte)
    ds = amb.dataset()
    prazo = prazo_aprovacao or (PRAZO_APROVACAO_INTERATIVO if interativo else PRAZO_APROVACAO)
    if acesso == "simulado":
        acesso = Acesso.simulado_com({u: {"nome": n, "papeis": p, "pessoa_erp": e, "cargo": c}
                                      for u, n, p, e, c in CONTAS_DEMO}, relogio=lambda: bus.now)
    compensatorio = "; ".join(f"{k}: {v}" for k, v in sorted(ds.perfil["controle_compensatorio"].items())) or None
    politica = PoliticaAprovacao(bus, aprovadores=aprovadores, prazo=prazo, acesso=acesso,
                                 controle_compensatorio=compensatorio)
    mem = Memoria(bus.audit, lambda: bus.now, politica=politica, caminho=memoria)
    gw = MCPGateway(amb, bus.audit, bus, politica=politica)
    locks = LockService(bus.audit, lambda: bus.now, ttl=ttl)
    agentes = {"AG-CUS": AgenteCustos(bus, gw), "AG-ORC": AgenteOrcamento(bus, gw),
               "AG-RES": AgenteResultados(bus, gw), "AG-CIN": AgenteControlesInternos(bus, gw),
               "AG-REL": AgenteRelatorios(bus, gw)}
    agentes["AG-CIN"].memoria = mem.visao("AG-CIN")
    pessoas = [*ds.perfil["pessoas"], *(nome for nome, _ in PESSOAS.values())]
    modelos = RegistroModelos(bus.audit, lambda: bus.now, pessoas=pessoas)
    for agente in ("AG-REL", "AG-RES", "AG-ORC"):  # os três em que a NORM-07 permite LLM
        agentes[agente].modelos = modelos
    # flag do LLM opcional (ADR-002), desligada por padrão. Texto = apelido de modelo só para a síntese do AG-REL
    # (forma da primeira versão da DSM3); dicionário = configuração por agente (ADR-008).
    for agente, campos in ({"AG-REL": {"modelo": llm}} if isinstance(llm, str) else dict(llm or {})).items():
        modelos.configurar(agente, llm=True, **campos)
    if cognicao != "basico":  # ADR-008: hipóteses propostas por regras locais (e por LLM, no nível `llm`)
        agentes["AG-ORC"].proponentes.append(ProponenteLocal())
    if cognicao == "llm":
        agentes["AG-ORC"].proponentes.append(ProponenteLLM(modelos))
    orq = Orquestrador(bus, locks, politica=politica, gateway=gw)
    return System(bus, ds, gw, locks, orq, Solicitante(bus),
                  Aprovador(bus, decisao_aprovador, amb, interativo, acesso=acesso),
                  agentes, amb, politica, mem, modelos, acesso)


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
    esperado: str = ""  # o que observar ao rodar o cenário (catálogo de cenários de teste)
    conector: str | None = None  # fonte por conector (conectores/cenarios.py), ADR-011; None = dados sintéticos


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
    # ---- DSM4 (ADR-011): conectores e entendimento automático de fontes, sem LLM ----
    Scenario("conector_rest_demo", "ERP de demonstração em loopback: o conector REST genérico lê o contrato OpenAPI, "
             "entende a fonte sem LLM e o mapeamento é confirmado; alçada violada, correção aprovada escrita no ERP "
             "pela API", "fechar_mes", decisao_aprovador="corrigir", conector="erp_demo:alcada",
             esperado="mesmo resultado do veto_correcao sobre o ERP simulado; a correção só chega ao ERP com o ticket "
                      "aprovado"),
    Scenario("conector_fora_do_ar", "ERP fora do ar (nada escuta na porta): toda leitura falha com o motivo e o "
             "fechamento termina em falha explícita, sem travar", "fechar_mes", conector="erp_fora_do_ar",
             esperado="failure com 'fonte indisponível'; leituras negadas auditadas; nada publicado"),
    Scenario("planilha_fora_do_modelo", "Planilha da casa (abas e colunas renomeadas e reordenadas, título acima do "
             "cabeçalho, R$ em texto, datas, linha de total): entendimento sugere o mapeamento, confirmação e "
             "fechamento", "fechar_mes", seed=7, porte="pequena", conector="planilha_fora_do_modelo",
             esperado="mesmo resultado da mesma empresa no modelo canônico; linha de total excluída e conferida"),
    Scenario("mcp_tools_entendidas", "Servidor MCP de Excel por stdio: tools listadas, ler_aba reconhecida como uma "
             "tool por aba canônica, amostras, mapeamento confirmado e fechamento pelo cliente MCP", "fechar_mes",
             seed=11, porte="micro", conector="mcp_excel",
             esperado="mesmo resultado da planilha lida pela pasta; proveniência mcp://mcp-excel/ler_aba#Aba"),
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
           llm=None, cognicao=None, acesso=None, ambiente=None) -> tuple[System, list]:
    """Monta o sistema do cenário e agenda os pedidos (sem executar).

    `porte` troca o porte do cenário; `pasta` usa a planilha de uma empresa real (os pedidos viram
    avaliar orçamento + fechar o mês da competência da planilha). `ambiente` (ou `sc.conector`) usa
    a fonte de um conector (ADR-011).
    """
    if ambiente is None and sc.conector:
        from fin_mas.conectores.cenarios import ambiente_do_cenario
        ambiente = ambiente_do_cenario(sc.conector, seed if seed is not None else sc.seed, porte or sc.porte)
    sistema = build_system(seed if seed is not None else sc.seed, () if pasta else sc.plantar, sc.faults,
                           sc.decisao_aprovador, agenda=None if pasta else dict(sc.agenda) or None,
                           interativo=interativo, porte=porte or sc.porte, pasta=pasta, memoria=memoria,
                           aprovadores=sc.aprovadores, llm=llm or {a: dict(campos) for a, campos in sc.llm} or None,
                           cognicao=cognicao or sc.cognicao, acesso=acesso or ("simulado" if sc.acesso else None),
                           ambiente=ambiente)
    ds = sistema.dataset
    extras = {} if (cognicao or sc.cognicao) == "basico" else {"cognicao": cognicao or sc.cognicao}
    outros = {a: sistema.modelos.situacao(a) for a in ("AG-ORC", "AG-RES") if sistema.modelos.config(a)["llm"]}
    if outros:
        extras["llm_agentes"] = outros
    if sistema.acesso is not None:
        extras["acesso"] = {"modo": "simulado" if sistema.acesso.simulado else "contas", "solicitante": sc.solicitante}
    if ambiente is not None and hasattr(ambiente, "descricao_fonte"):  # ADR-011: qual conector alimenta os agentes
        extras["conector"] = ambiente.descricao_fonte()
    sistema.bus.audit.record(0, "meta", **extras, empresa={**EMPRESA, "razao_social": getattr(ds, "razao_social", None)
                                                 or EMPRESA["razao_social"], "sigla": ds.entidade},
                             cenario=sc.nome, seed=sistema.ambiente.seed, porte=ds.porte,
                             porte_titulo=ds.perfil["titulo"], tem_erp=ds.perfil["tem_erp"],
                             fonte=getattr(ambiente, "fonte", None) or ("planilha" if pasta else "sintetico"),
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
    pedidos = PEDIDOS_PLANILHA if pasta else (sc.pedidos or ((sc.intencao, None, 1),))
    sids = [sistema.usuario.solicitar(intencao, competencia=c or sistema.ambiente.principal, atraso=atraso,
                                      solicitado_por=sc.solicitante if sistema.acesso is not None else None)
            for intencao, c, atraso in pedidos]
    return sistema, sids


def run_scenario(cenario, seed=None, porte=None, pasta=None, memoria=None, llm=None, cognicao=None,
                 ambiente=None) -> Execucao:
    sc = CENARIOS[cenario] if isinstance(cenario, str) else cenario
    sistema, sids = montar(sc, seed, porte=porte, pasta=pasta, memoria=memoria, llm=llm, cognicao=cognicao,
                           ambiente=ambiente)
    try:
        sistema.bus.run()
    finally:
        fechar = getattr(sistema.ambiente, "fechar", None)  # conector: encerra o que o cenário subiu (ADR-011)
        if fechar is not None:
            fechar()
    return Execucao(sc, sistema, sids[0], sistema.usuario.resposta(sids[0]), sids)

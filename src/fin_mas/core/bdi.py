"""Núcleo BDI dos agentes cognitivos (AG-ORC e AG-CIN).

Ciclo executado a cada percepção (mensagem, resposta MCP ou timeout):

    perceber -> revisar crenças -> reconsiderar intenções -> gerar opções (desejos)
    -> deliberar (plano aplicável de maior utilidade) -> executar -> ...

Política de compromisso: aberta (Rao & Georgeff). Uma intenção é mantida enquanto o
desejo continua ativo e o contexto do plano continua verdadeiro; a reconsideração só
é disparada por eventos relevantes (crença revisada, falha ou timeout do plano,
desejo satisfeito), nunca a cada tick (equilíbrio cauteloso x ousado de Kinny & Georgeff).

Tudo vai para a auditoria: `belief`, `desire`, `deliberation` e `intention`.

DSM3 (ADR-008): com um ou mais **proponentes** ligados (regras locais ou LLM opcional), o
ciclo começa por `_inferir`, que recolhe propostas, valida cada uma (`core/inferencia.py`) e
guarda as aceitas em `self.hipoteses`, um repositório separado das crenças. Hipótese não é
crença: os planos de domínio não a leem; ela só pode gerar um desejo epistêmico (buscar a
evidência que a confirma ou refuta), e é a evidência que revisa a crença. Sem proponentes
(nível `basico`) `_inferir` não faz nada e nenhum registro novo aparece no trace.
"""
from dataclasses import dataclass, field
from typing import Callable

from fin_mas.agents.base import Specialist
from fin_mas.core.inferencia import FINAIS, Hipotese, validar_proposta

TERMINAIS = {"concluida", "abandonada", "falhou"}


class Crencas:
    """Base de crenças com revisão auditada: só grava quando o valor muda."""

    def __init__(self, agente):
        self.agente = agente
        self._b: dict = {}
        self._fonte: dict = {}  # chave -> fonte da última revisão (quem ou o quê sustentou a crença)

    def get(self, chave, padrao=None):
        return self._b.get(chave, padrao)

    def __contains__(self, chave):
        return chave in self._b

    def fonte(self, chave) -> str | None:
        return self._fonte.get(chave)

    def revisar(self, chave: str, valor, fonte: str, cid: str | None = None) -> bool:
        antes = self._b.get(chave)
        if chave in self._b and antes == valor:
            return False
        self._b[chave] = valor
        self._fonte[chave] = fonte
        self.agente.bus.audit.record(
            self.agente.bus.now, "belief", conversation_id=cid, agente=self.agente.id,
            chave=chave, antes=antes, depois=valor, fonte=fonte,
        )
        self.agente._crencas_mudaram = True
        return True

    def snapshot(self) -> dict:
        return dict(self._b)


@dataclass
class Desejo:
    id: str  # tipo:parâmetros, único por agente
    tipo: str
    prioridade: int  # 1 = mais importante
    params: dict
    cid: str | None  # conversa que originou o desejo (ligação causal no trace)
    estado: str = "ativo"  # ativo | satisfeito | descartado


@dataclass
class Plano:
    """Receita para um tipo de desejo. `contexto` devolve (aplicável, motivo)."""

    id: str
    desejo: str
    descricao: str
    atende: tuple  # desejos permanentes do agente que o plano também serve
    contexto: Callable
    corpo: Callable  # corpo(agente, intencao) -> None
    continuar: Callable | None = None  # continuar(agente, intencao, msg) ao chegar a resposta aguardada
    preferencia: int = 0  # desempate entre planos de mesma utilidade


@dataclass
class Intencao:
    id: str
    desejo: Desejo
    plano: Plano
    estado: str = "ativa"  # ativa | suspensa | concluida | abandonada | falhou
    aguardando: str | None = None  # conversation_id ou "desejo:<id>"
    tentados: list = field(default_factory=list)
    resultado: object = None


class AgenteBDI(Specialist):
    """Especialista com base de crenças, desejos, biblioteca de planos e intenções."""

    PLANOS: list = []  # biblioteca de planos (por classe)
    DESEJOS_PERMANENTES: dict = {}  # nome -> peso; usados na utilidade dos planos

    def __init__(self, agent_id, bus, gateway):
        super().__init__(agent_id, bus, gateway)
        self.crencas = Crencas(self)
        self.desejos: dict[str, Desejo] = {}
        self.intencoes: list[Intencao] = []
        self._seq_intencao = 0
        self._crencas_mudaram = False
        self._em_ciclo = False
        self.proponentes: list = []  # vazio = cognição básica (sem hipóteses)
        self.hipoteses: dict[str, Hipotese] = {}
        self._gatilhos_usados: set = set()

    # ---- hipóteses (ADR-008) -------------------------------------------------
    def gatilhos_inferencia(self) -> list[dict]:
        """Momentos em que vale pedir hipóteses: [{"chave", "cid", "tarefa", "competencia", "contexto", "esquema"}].

        Cada gatilho é usado uma única vez (a chave o identifica), o que limita custo e garante
        que o ciclo termine.
        """
        return []

    def _inferir(self) -> None:
        if not self.proponentes:
            return
        for g in self.gatilhos_inferencia():
            if g["chave"] in self._gatilhos_usados:
                continue
            self._gatilhos_usados.add(g["chave"])
            for proponente in self.proponentes:
                propostas = proponente.propor(self.id, g["cid"], g["tarefa"], g["contexto"], g["esquema"])
                pseudonimos = dict(getattr(proponente, "pseudonimos", None) or {})
                for p in propostas[: g["esquema"].max_propostas]:
                    self._receber_proposta(p, g, pseudonimos)

    def _receber_proposta(self, p, g, pseudonimos=None) -> None:
        motivo = validar_proposta(p, g["esquema"])
        if motivo:
            self._registrar("hipotese", g["cid"], evento="rejeitada", tipo=p.tipo, alvo=p.alvo, origem=p.origem,
                            motivo=motivo, regra="NORM-11")
            return
        existente = self.hipotese_de(p.tipo, p.alvo, g["competencia"])
        if existente is not None:
            if p.origem not in existente.origens:
                existente.origens.append(p.origem)
                self._registrar("hipotese", g["cid"], hipotese=existente.id, evento="corroborada", tipo=p.tipo,
                                alvo=p.alvo, origem=p.origem, regra="NORM-11")
            return
        h = Hipotese(f"{self.id}-H{len(self.hipoteses) + 1:03d}", p.tipo, p.alvo, g["competencia"], [p.origem],
                     p.justificativa, p.evidencias, p.confianca, g["cid"], pseudonimos=dict(pseudonimos or {}))
        self.hipoteses[h.id] = h
        self._registrar("hipotese", g["cid"], hipotese=h.id, evento="aceita", tipo=h.tipo, alvo=h.alvo,
                        origem=p.origem, justificativa=h.justificativa, evidencias=list(h.evidencias),
                        confianca=h.confianca, regra="NORM-11")
        self._crencas_mudaram = True

    def hipotese_de(self, tipo, alvo, competencia) -> Hipotese | None:
        return next((h for h in self.hipoteses.values()
                     if (h.tipo, h.alvo, h.competencia) == (tipo, alvo, competencia)), None)

    def marcar_hipotese(self, h: Hipotese, estado: str, motivo: str, fonte: str | None = None) -> None:
        """Muda o estado da hipótese; `fonte` é a evidência determinística que a confirmou ou refutou."""
        if h.estado in FINAIS or h.estado == estado:
            return
        h.estado, h.verificacao = estado, fonte or h.verificacao
        self._registrar("hipotese", h.cid, hipotese=h.id, evento=estado, tipo=h.tipo, alvo=h.alvo, motivo=motivo,
                        fonte=fonte, regra="NORM-11")
        self._crencas_mudaram = True

    # ---- desejos ---------------------------------------------------------
    def opcoes(self) -> list[tuple]:
        """Gera opções a partir das crenças: [(tipo, params, prioridade, motivo, cid)]."""
        return []

    def desejo_ativo(self, desejo: Desejo) -> tuple[bool, str]:
        """Se o desejo ainda faz sentido diante das crenças atuais (para a reconsideração)."""
        return True, ""

    def _adotar_desejo(self, tipo, params, prioridade, motivo, cid) -> Desejo | None:
        did = tipo + ":" + "|".join(f"{v}" for _, v in sorted(params.items()))
        if did in self.desejos:
            return None  # já adotado (ativo, satisfeito ou descartado): não regenera
        d = Desejo(did, tipo, prioridade, dict(params), cid)
        self.desejos[did] = d
        self._registrar("desire", d.cid, desejo=did, evento="gerado", prioridade=prioridade, motivo=motivo)
        return d

    def _encerrar_desejo(self, d: Desejo, estado: str, motivo: str) -> None:
        if d.estado != "ativo":
            return
        d.estado = estado
        self._registrar("desire", d.cid, desejo=d.id, evento=estado, prioridade=d.prioridade, motivo=motivo)

    # ---- ciclo -------------------------------------------------------------
    def ciclo(self) -> None:
        """Reconsidera, gera opções e delibera até não haver mais mudança (ponto fixo)."""
        if self._em_ciclo:
            self._crencas_mudaram = True  # o ciclo em andamento fará outra volta
            return
        self._em_ciclo = True
        try:
            for _ in range(50):
                self._crencas_mudaram = False
                self._inferir()
                self._reconsiderar()
                for tipo, params, prioridade, motivo, cid in self.opcoes():
                    self._adotar_desejo(tipo, params, prioridade, motivo, cid)
                self._deliberar()
                self._retomar_internas()
                if not self._crencas_mudaram:
                    break
            self.apos_ciclo()
        finally:
            self._em_ciclo = False

    def apos_ciclo(self) -> None:
        """Gancho do agente concreto (ex.: responder quando todas as intenções terminarem)."""

    def _reconsiderar(self) -> None:
        for i in self.intencoes:
            if i.estado in TERMINAIS:
                continue
            ativo, motivo = self.desejo_ativo(i.desejo)
            if not ativo:
                self._encerrar_intencao(i, "abandonada", f"reconsiderada: {motivo}")
                self._encerrar_desejo(i.desejo, "descartado", motivo)
                continue
            if i.estado == "ativa" or (i.aguardando or "").startswith("desejo:"):
                ok, motivo_ctx = i.plano.contexto(self, i.desejo)
                if not ok:
                    self._falhar(i, f"contexto do plano deixou de valer: {motivo_ctx}")

    def _deliberar(self) -> None:
        pendentes = [d for d in self.desejos.values() if d.estado == "ativo" and not self._intencao_de(d)]
        for d in sorted(pendentes, key=lambda d: (d.prioridade, d.id)):
            if d.estado == "ativo" and not self._intencao_de(d):
                self._selecionar_e_executar(d, tentados=[])

    def _utilidade(self, plano: Plano) -> int:
        return sum(self.DESEJOS_PERMANENTES.get(a, 0) for a in plano.atende) * 10 + plano.preferencia

    def _selecionar_e_executar(self, d: Desejo, tentados: list) -> None:
        opcoes = []
        for p in (p for p in self.PLANOS if p.desejo == d.tipo):
            if p.id in tentados:
                opcoes.append({"plano": p.id, "aplicavel": False, "motivo": "já tentado sem sucesso",
                               "utilidade": self._utilidade(p)})
                continue
            ok, motivo = p.contexto(self, d)
            opcoes.append({"plano": p.id, "aplicavel": ok, "motivo": motivo, "utilidade": self._utilidade(p),
                           "atende": list(p.atende)})
        aplicaveis = [o for o in opcoes if o["aplicavel"]]
        escolhido = max(aplicaveis, key=lambda o: o["utilidade"])["plano"] if aplicaveis else None
        self._registrar("deliberation", d.cid, desejo=d.id, opcoes=opcoes, escolhido=escolhido)
        if escolhido is None:
            self._encerrar_desejo(d, "descartado", "nenhum plano aplicável")
            return
        self._seq_intencao += 1
        plano = next(p for p in self.PLANOS if p.id == escolhido)
        i = Intencao(f"{self.id}-I{self._seq_intencao:03d}", d, plano, tentados=list(tentados) + [plano.id])
        self.intencoes.append(i)
        self._registrar("intention", d.cid, intencao=i.id, desejo=d.id, plano=plano.id, evento="adotada",
                        motivo=plano.descricao)
        plano.corpo(self, i)

    def _retomar_internas(self) -> None:
        for i in list(self.intencoes):
            if i.estado == "suspensa" and (i.aguardando or "").startswith("desejo:"):
                dep = self.desejos.get(i.aguardando[len("desejo:"):])
                if dep is None or dep.estado != "ativo":
                    i.estado, i.aguardando = "ativa", None
                    self._registrar("intention", i.desejo.cid, intencao=i.id, desejo=i.desejo.id,
                                    plano=i.plano.id, evento="retomada", motivo="dependência resolvida")
                    i.plano.corpo(self, i)

    # ---- operações usadas pelos corpos dos planos ---------------------------
    def suspender(self, i: Intencao, aguardando: str, motivo: str) -> None:
        if i.estado == "suspensa" and i.aguardando == aguardando:
            return
        i.estado, i.aguardando = "suspensa", aguardando
        self._registrar("intention", i.desejo.cid, intencao=i.id, desejo=i.desejo.id, plano=i.plano.id,
                        evento="suspensa", motivo=motivo, aguardando=aguardando)

    def concluir(self, i: Intencao, resultado=None, motivo="objetivo atingido") -> None:
        i.resultado = resultado
        self._encerrar_intencao(i, "concluida", motivo)
        self._encerrar_desejo(i.desejo, "satisfeito", motivo)
        self._crencas_mudaram = True

    def _falhar(self, i: Intencao, motivo: str) -> None:
        """Falha do plano: tenta o próximo plano aplicável para o mesmo desejo (replanejamento)."""
        self._encerrar_intencao(i, "falhou", motivo)
        if i.desejo.estado == "ativo":
            self._registrar("intention", i.desejo.cid, intencao=i.id, desejo=i.desejo.id, plano=i.plano.id,
                            evento="reconsiderada", motivo=f"replanejar após falha: {motivo}")
            self._selecionar_e_executar(i.desejo, tentados=i.tentados)
        self._crencas_mudaram = True

    def falhar(self, i: Intencao, motivo: str) -> None:
        self._falhar(i, motivo)

    def _encerrar_intencao(self, i: Intencao, estado: str, motivo: str) -> None:
        if i.estado in TERMINAIS:
            return
        i.estado, i.aguardando = estado, None
        self._registrar("intention", i.desejo.cid, intencao=i.id, desejo=i.desejo.id, plano=i.plano.id,
                        evento=estado, motivo=motivo)

    def intencao_aguardando(self, cid: str) -> Intencao | None:
        return next((i for i in self.intencoes if i.estado == "suspensa" and i.aguardando == cid), None)

    def entregar_resposta(self, msg) -> bool:
        """Retoma a intenção que aguardava esta conversa; devolve False se nenhuma aguardava."""
        i = self.intencao_aguardando(msg.conversation_id)
        if i is None:
            return False
        i.estado, i.aguardando = "ativa", None
        self._registrar("intention", i.desejo.cid, intencao=i.id, desejo=i.desejo.id, plano=i.plano.id,
                        evento="retomada", motivo=f"{msg.performative} em {msg.conversation_id}")
        if msg.performative in ("inform",) and i.plano.continuar:
            i.plano.continuar(self, i, msg)
        else:
            self._falhar(i, f"{msg.performative} de {msg.sender if msg.sender != 'SVC-A2A' else msg.content.get('contraparte')}")
        self.ciclo()
        return True

    def _intencao_de(self, d: Desejo) -> Intencao | None:
        return next((i for i in self.intencoes if i.desejo is d and i.estado not in TERMINAIS), None)

    def pendentes(self, filtro: Callable | None = None) -> list[Intencao]:
        return [i for i in self.intencoes if i.estado not in TERMINAIS and (filtro is None or filtro(i))]

    def _registrar(self, kind, cid, **campos) -> None:
        self.bus.audit.record(self.bus.now, kind, conversation_id=cid, agente=self.id, **campos)

    # ---- observabilidade -----------------------------------------------------
    def mente(self) -> dict:
        m = super().mente()
        m["bdi"] = {
            "crencas": self.crencas.snapshot(),
            "desejos": [{"id": d.id, "tipo": d.tipo, "prioridade": d.prioridade, "estado": d.estado}
                        for d in self.desejos.values()],
            "intencoes": [{"id": i.id, "desejo": i.desejo.id, "plano": i.plano.id, "estado": i.estado,
                           "aguardando": i.aguardando} for i in self.intencoes],
            "planos": [{"id": p.id, "desejo": p.desejo, "descricao": p.descricao, "atende": list(p.atende),
                        "utilidade": self._utilidade(p)} for p in self.PLANOS],
            "desejos_permanentes": dict(self.DESEJOS_PERMANENTES),
        }
        if self.proponentes:
            m["bdi"]["hipoteses"] = [h.resumo() for h in self.hipoteses.values()]
        return m

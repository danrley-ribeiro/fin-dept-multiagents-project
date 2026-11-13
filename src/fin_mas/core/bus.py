"""Bus A2A em processo com relógio lógico (ADR-003, ADR-004 e ADR-007).

Single-thread e determinístico: a fila é ordenada por (tempo lógico, sequência).
`reply_by` vira um temporizador que expira a conversa (evento `timeout`) no tempo lógico.

DSM3 — autenticidade e integridade das interações. Antes de mudar o estado de qualquer
conversa, `send` verifica, nesta ordem, e rejeita (fail-closed, com registro `rejected`
na auditoria e `MensagemRejeitada`) o que falhar:

1. autenticação: o remetente está registrado e apresentou a sua credencial;
2. envelope: campos obrigatórios, ontologia e `reply_by` no futuro;
3. destinatário registrado e diferente do remetente; protocolo e performativo conhecidos;
4. papel: o papel do remetente pode emitir o performativo e o do destinatário participa;
5. esquema do conteúdo do performativo;
6. conversa: abertura só pelo performativo inicial; resposta só entre iniciador e
   contraparte, e endereçada à outra ponta; transição permitida pela FSM;
7. validadores do domínio registrados para o protocolo (ex.: SVC-POL no PROT-APR).

`advance` (transição local, sem mensagem) exige credencial, participação na conversa e
um papel autorizado para o evento em `eventos_locais`. O conteúdo é copiado no envio e
tem o hash conferido na entrega; o destinatário recebe a sua própria cópia. Exceção de
um agente ao tratar uma mensagem é registrada (`erro_agente`) e não interrompe a simulação.
"""
import copy
import hashlib
import heapq
import hmac
import json
import secrets
from dataclasses import dataclass, replace

from fin_mas.core.diretorio import carregar_diretorio, papeis_validos
from fin_mas.core.fsm import Conversation, ProtocolViolation, load_protocols
from fin_mas.core.message import Message
from fin_mas.core.schema import erros_conteudo, erros_envelope
from fin_mas.services.audit import AuditLog

SISTEMA = "SVC-A2A"


class MensagemRejeitada(ProtocolViolation):
    """Mensagem ou transição local recusada pelo barramento (registrada como `rejected`)."""

    def __init__(self, motivo: str, etapa: str):
        super().__init__(motivo)
        self.motivo = motivo
        self.etapa = etapa


@dataclass
class Fault:
    """Perda deliberada de mensagens na entrega (injeção de falha do ambiente)."""

    receiver: str
    performative: str
    times: int
    protocol: str | None = None

    def matches(self, msg: Message) -> bool:
        return (
            self.times > 0
            and msg.receiver == self.receiver
            and msg.performative == self.performative
            and (self.protocol is None or msg.protocol == self.protocol)
        )


def _hash_credencial(credencial: str) -> str:
    return hashlib.sha256(credencial.encode("utf-8")).hexdigest()


def digest_conteudo(content) -> str:
    """SHA-256 do JSON canônico; levanta TypeError para chaves não-texto ou valores não JSON."""
    _so_chaves_texto(content)
    canonico = json.dumps(content, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class Bus:
    def __init__(self, audit: AuditLog | None = None, faults: list[Fault] | None = None,
                 diretorio: dict | None = None, isolar_erros: bool = True, caos=None):
        self.audit = audit if audit is not None else AuditLog()
        self.protocols = load_protocols()
        self.faults = faults or []
        self.caos = caos  # DSM4: modelo de falhas aleatórias por seed (`fin_mas.caos`); None = nenhum efeito
        self.now = 0
        self.agents: dict = {}
        self.papeis: dict[str, str] = {}  # identidade -> papel (agentes e serviços registrados)
        self.conversations: dict[str, Conversation] = {}
        self.validadores: dict[str, list] = {}  # protocolo -> [f(msg, conv) -> motivo | None]
        self.diretorio = carregar_diretorio() if diretorio is None else diretorio
        self.isolar_erros = isolar_erros
        self._credenciais: dict[str, str] = {}
        self._queue: list = []
        self._seq = 0
        self._ids: dict[str, int] = {}
        self.offline: set[str] = set()  # agentes fora de operação: o que chega a eles se perde
        self.prazos: dict[str, int] = {}  # conversa -> prazo vigente (uma resposta com novo reply_by o estende)

    # ---- identidades ------------------------------------------------------------
    def register(self, agent, papel: str | None = None) -> str:
        """Registra um agente e devolve a sua credencial (só ele a recebe)."""
        credencial = self._registrar(agent.id, papel or getattr(agent, "papel", None))
        self.agents[agent.id] = agent
        return credencial

    def register_service(self, servico_id: str, papel: str) -> str:
        """Serviço que aplica transições locais (ex.: SVC-POL), sem caixa de entrada."""
        return self._registrar(servico_id, papel)

    def _registrar(self, ident: str, papel: str | None) -> str:
        if not isinstance(ident, str) or not ident or ident == SISTEMA:
            raise ProtocolViolation(f"identidade inválida: {ident!r}")
        if ident in self.papeis:
            raise ProtocolViolation(f"identidade já registrada: {ident} (personificação recusada)")
        if papel not in papeis_validos():
            raise ProtocolViolation(f"{ident}: papel desconhecido {papel!r}")
        if ident in self.diretorio and papel not in self.diretorio[ident]:
            raise ProtocolViolation(f"{ident}: papel {papel} não consta no diretório ({sorted(self.diretorio[ident])})")
        self.papeis[ident] = papel
        credencial = secrets.token_hex(16)
        self._credenciais[ident] = _hash_credencial(credencial)  # só o hash fica no barramento
        return credencial

    def _autentico(self, ident: str, credencial) -> bool:
        esperado = self._credenciais.get(ident)
        return (esperado is not None and isinstance(credencial, str)
                and hmac.compare_digest(esperado, _hash_credencial(credencial)))

    def autenticar(self, ident: str, credencial) -> bool:
        """Para serviços fora do barramento (gateway MCP, memória) conferirem a identidade de quem chama."""
        return isinstance(ident, str) and self._autentico(ident, credencial)

    def new_conversation_id(self, prefix: str) -> str:
        self._ids[prefix] = self._ids.get(prefix, 0) + 1
        return f"{prefix}-{self._ids[prefix]:03d}"

    def add_validator(self, protocolo: str, validador) -> None:
        self.validadores.setdefault(protocolo, []).append(validador)

    def _push(self, when: int, kind: str, payload) -> None:
        self._seq += 1
        heapq.heappush(self._queue, (when, self._seq, kind, payload))

    # ---- envio ---------------------------------------------------------------------
    def send(self, msg: Message, delay: int = 1, credencial: str | None = None) -> None:
        """Valida a mensagem (ver docstring do módulo) e a agenda para entrega em now + delay."""
        if isinstance(msg.content, dict):
            msg = replace(msg, content=copy.deepcopy(msg.content))  # o remetente não altera o que já enviou
        if not isinstance(msg.sender, str) or msg.sender not in self._credenciais:
            self._rejeitar(msg, f"remetente desconhecido: {msg.sender!r}", "autenticacao")
        if not self._autentico(msg.sender, credencial):
            self._rejeitar(msg, f"remetente não autenticado: credencial ausente ou inválida para {msg.sender}",
                           "autenticacao")
        erros = erros_envelope(msg, self.now)
        if erros:
            self._rejeitar(msg, "envelope inválido: " + "; ".join(erros), "esquema")
        if msg.receiver not in self.agents:
            self._rejeitar(msg, f"destinatário desconhecido: {msg.receiver}", "destinatario")
        if msg.receiver == msg.sender:
            self._rejeitar(msg, "remetente e destinatário iguais", "destinatario")
        if msg.protocol is None:
            self._rejeitar(msg, "mensagem sem protocolo: decisões e avisos passam por um protocolo (DSM3)", "protocolo")
        proto = self.protocols.get(msg.protocol)
        if proto is None:
            self._rejeitar(msg, f"protocolo desconhecido: {msg.protocol}", "protocolo")
        if msg.performative not in proto.performatives:
            self._rejeitar(msg, f"{proto.id}: performativo '{msg.performative}' não pertence ao protocolo", "protocolo")
        papel_rem, papel_dest = self.papeis[msg.sender], self.papeis.get(msg.receiver)
        emissores = proto.emitters.get(msg.performative)
        if proto.emitters and emissores is None:
            self._rejeitar(msg, f"{proto.id}: '{msg.performative}' não é enviado como mensagem "
                                f"(só como transição local do participante autorizado)", "papel")
        if emissores is not None and papel_rem not in emissores:
            self._rejeitar(msg, f"{proto.id}: papel {papel_rem} de {msg.sender} não pode emitir '{msg.performative}'",
                           "papel")
        if proto.participants and papel_dest not in proto.participants:
            self._rejeitar(msg, f"{proto.id}: papel {papel_dest} de {msg.receiver} não participa do protocolo", "papel")
        erros = erros_conteudo(proto.schemas.get(msg.performative), msg.content)
        if erros:
            self._rejeitar(msg, f"{proto.id}/{msg.performative}: conteúdo inválido: " + "; ".join(erros), "esquema")
        try:  # calculado antes de qualquer efeito: falhar aqui não pode deixar ticket ou FSM alterados
            digest = digest_conteudo(msg.content)
        except (TypeError, ValueError) as erro:
            self._rejeitar(msg, f"conteúdo não serializável (chaves e valores JSON): {erro}", "esquema")

        conv = self.conversations.get(msg.conversation_id)
        if conv is None:
            if msg.performative != proto.opening:
                self._rejeitar(msg, f"{proto.id}: '{msg.performative}' sem conversa aberta "
                                    f"(conversation_id desconhecido: {msg.conversation_id})", "conversa")
            self._validar_dominio(msg, None)
            self._open(msg)
        else:
            if conv.protocol.id != msg.protocol:
                self._rejeitar(msg, f"{msg.conversation_id} pertence a {conv.protocol.id}", "conversa")
            if msg.sender not in (conv.initiator, conv.counterpart):
                self._rejeitar(msg, f"{msg.sender} não participa de {msg.conversation_id}", "conversa")
            outra_ponta = conv.counterpart if msg.sender == conv.initiator else conv.initiator
            if msg.receiver != outra_ponta:
                self._rejeitar(msg, f"{msg.receiver} não é a contraparte de {msg.sender} em {msg.conversation_id} "
                                    f"(esperado {outra_ponta})", "destinatario")
            if conv.state == "EXPIRADA":
                self.audit.record(self.now, "discard", motivo="resposta após reply_by", **_campos(msg))
                return
            if not conv.can(msg.performative):
                try:
                    conv.protocol.next_state(conv.state, msg.performative)
                except ProtocolViolation as erro:
                    self._rejeitar(msg, str(erro), "fsm")
            self._validar_dominio(msg, conv)
            antes, depois = conv.step(msg.performative)
            self.audit.record(self.now, "send", de=antes, para=depois, **_campos(msg))
            if msg.reply_by is not None:  # prazo renegociado (PROT-DEL, accept-proposal): o temporizador antigo perde efeito
                self.prazos[msg.conversation_id] = msg.reply_by
                self._push(msg.reply_by, "timer", msg.conversation_id)
        if self.caos is not None:  # atraso de entrega sorteado (jitter); os prazos (reply_by) não mudam
            delay += self.caos.atraso(msg)
        self._push(self.now + delay, "msg", (msg, digest))

    def _validar_dominio(self, msg: Message, conv) -> None:
        for validador in self.validadores.get(msg.protocol, []):
            motivo = validador(msg, conv)
            if motivo:
                self._rejeitar(msg, motivo, "politica")

    def _rejeitar(self, msg: Message, motivo: str, etapa: str):
        self.audit.record(self.now, "rejected", motivo=motivo, etapa=etapa, **_campos(msg, seguro=True))
        raise MensagemRejeitada(motivo, etapa)

    def _open(self, msg: Message) -> Conversation:
        proto = self.protocols[msg.protocol]
        conv = Conversation(proto, msg.conversation_id, msg.sender, msg.receiver)
        self.conversations[msg.conversation_id] = conv
        antes = conv.state
        if conv.can(msg.performative):
            conv.step(msg.performative)
        self.audit.record(self.now, "open", de=antes, para=conv.state, **_campos(msg))
        if msg.reply_by is not None:
            self.prazos[msg.conversation_id] = msg.reply_by
            self._push(msg.reply_by, "timer", msg.conversation_id)
        return conv

    def advance(self, conversation_id: str, event: str, actor: str, credencial: str | None = None) -> str:
        """Transição local da FSM (decisão do próprio participante, sem mensagem).

        Só o participante autenticado cujo papel consta em `eventos_locais` do protocolo
        pode aplicar o evento; qualquer outra tentativa é rejeitada e auditada.
        """
        conv = self.conversations.get(conversation_id)

        def rejeitar(motivo, etapa):
            self.audit.record(self.now, "rejected", conversation_id=conversation_id, agente=actor, evento=event,
                              protocol=conv.protocol.id if conv else None, motivo=motivo, etapa=etapa)
            raise MensagemRejeitada(motivo, etapa)

        if not isinstance(actor, str) or actor not in self._credenciais:
            rejeitar(f"transição local por identidade desconhecida: {actor!r}", "autenticacao")
        if not self._autentico(actor, credencial):
            rejeitar(f"transição local sem credencial válida de {actor}", "autenticacao")
        if conv is None:
            rejeitar(f"conversa inexistente: {conversation_id}", "conversa")
        papel = self.papeis[actor]
        autorizados = conv.protocol.local_events.get(event)
        if autorizados is None:
            rejeitar(f"{conv.protocol.id}: '{event}' não é um evento local do protocolo", "protocolo")
        if papel not in autorizados:
            rejeitar(f"{conv.protocol.id}: papel {papel} de {actor} não pode aplicar '{event}'", "papel")
        servico = papel.startswith("SVC-") and papel in conv.protocol.participants
        if actor not in (conv.initiator, conv.counterpart) and not servico:
            rejeitar(f"{actor} não participa de {conversation_id}", "conversa")
        try:
            antes, depois = conv.step(event)
        except ProtocolViolation as erro:
            rejeitar(str(erro), "fsm")
        self.audit.record(
            self.now, "advance", conversation_id=conversation_id, protocol=conv.protocol.id,
            agente=actor, evento=event, de=antes, para=depois,
        )
        return depois

    # ---- execução --------------------------------------------------------------------
    def run(self, max_steps: int = 10_000) -> int:
        passos = 0
        while self._queue:
            passos += 1
            if passos > max_steps:
                raise RuntimeError("limite de passos excedido (possível laço de mensagens)")
            self.step()
        return passos

    def proximo_tempo(self) -> int | None:
        """Tempo lógico do próximo evento agendado (None com a fila vazia)."""
        return self._queue[0][0] if self._queue else None

    def step(self) -> bool:
        """Processa um único evento (entrega ou temporizador); usado pela execução ao vivo."""
        if not self._queue:
            return False
        when, _, kind, payload = heapq.heappop(self._queue)
        self.now = max(self.now, when)
        if kind == "msg":
            self._deliver(*payload)
        elif kind == "acao":
            self._acao(*payload)
        else:
            self._timer(payload)
        return True

    def agendar(self, when: int, acao, rotulo: str) -> None:
        """Evento do ambiente no tempo lógico `when` (ex.: ataques de um cenário adversarial)."""
        self._push(max(when, self.now), "acao", (acao, rotulo))

    def _acao(self, acao, rotulo: str) -> None:
        self.audit.record(self.now, "ambiente", evento=rotulo)
        try:
            acao()
        except Exception as erro:
            self.audit.record(self.now, "erro_agente", agente="ambiente", erro=f"{type(erro).__name__}: {erro}")

    def set_online(self, agente: str, online: bool) -> None:
        """Liga ou desliga um agente (injeção de falha do ambiente, comandada pelo operador)."""
        if online:
            self.offline.discard(agente)
        else:
            self.offline.add(agente)
        self.audit.record(self.now, "agente", agente=agente, evento="ligado" if online else "desligado")

    def _deliver(self, msg: Message, digest: str) -> None:
        for falha in self.faults:
            if falha.matches(msg):
                falha.times -= 1
                self.audit.record(self.now, "drop", motivo="falha injetada", **_campos(msg))
                return
        if self.caos is not None and self.caos.perder(msg):
            self.audit.record(self.now, "drop", motivo="perda aleatória (caos)", **_campos(msg))
            return
        if msg.receiver in self.offline:
            self.audit.record(self.now, "drop", motivo="agente fora de operação", **_campos(msg))
            return
        try:
            integro = digest_conteudo(msg.content) == digest
        except (TypeError, ValueError):
            integro = False
        if not integro:
            self.audit.record(self.now, "drop", motivo="integridade: conteúdo alterado após o envio",
                              **_campos(msg, seguro=True))
            return
        self.audit.record(self.now, "deliver", **_campos(msg))
        self._entregar(self.agents[msg.receiver], replace(msg, content=copy.deepcopy(msg.content)))

    def _entregar(self, agente, msg: Message) -> None:
        if not self.isolar_erros:
            agente.on_message(msg)
            return
        try:
            agente.on_message(msg)
        except Exception as erro:  # um agente com defeito não derruba a simulação
            self.audit.record(self.now, "erro_agente", conversation_id=msg.conversation_id, agente=agente.id,
                              protocol=msg.protocol, performative=msg.performative,
                              erro=f"{type(erro).__name__}: {erro}")
            tratar = getattr(agente, "on_error", None)
            if tratar is not None:
                try:
                    tratar(msg, erro)
                except Exception as erro2:
                    self.audit.record(self.now, "erro_agente", conversation_id=msg.conversation_id,
                                      agente=agente.id, erro=f"on_error: {type(erro2).__name__}: {erro2}")

    def _timer(self, conversation_id: str) -> None:
        conv = self.conversations[conversation_id]
        if self.prazos.get(conversation_id, self.now) > self.now:
            return  # o prazo foi estendido depois deste temporizador: vale o novo
        if conv.can("timeout"):
            antes, depois = conv.step("timeout")
        elif len(conv.history) == 1 and not conv.is_final:
            # protocolo sem transição de timeout (PROT-CMP) e contraparte ainda sem resposta:
            # avisa o iniciador sem mexer na FSM
            antes = depois = conv.state
        else:
            return
        aviso = Message(
            SISTEMA, conv.initiator, "timeout", conversation_id, conv.protocol.id,
            {"contraparte": conv.counterpart},
        )
        self.audit.record(self.now, "timeout", de=antes, para=depois, **_campos(aviso))
        if conv.initiator not in self.offline:
            self._entregar(self.agents[conv.initiator], aviso)


def _so_chaves_texto(valor, nivel=0) -> None:
    if nivel > 50:
        raise ValueError("estrutura profunda demais")
    if isinstance(valor, dict):
        for k, v in valor.items():
            if not isinstance(k, str):
                raise TypeError(f"chave não-texto: {k!r}")
            _so_chaves_texto(v, nivel + 1)
    elif isinstance(valor, (list, tuple)):
        for v in valor:
            _so_chaves_texto(v, nivel + 1)


def _campos(msg: Message, seguro: bool = False) -> dict:
    """Campos auditados da mensagem; `seguro` tolera envelopes malformados (rejeições)."""
    campos = {
        "conversation_id": msg.conversation_id,
        "protocol": msg.protocol,
        "sender": msg.sender,
        "receiver": msg.receiver,
        "performative": msg.performative,
        "content": msg.content,
    }
    if seguro:
        campos = {k: v if isinstance(v, (str, int, dict, list, type(None))) else repr(v) for k, v in campos.items()}
    return campos

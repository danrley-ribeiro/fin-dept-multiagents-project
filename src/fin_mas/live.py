"""Execução ao vivo do SMA para o dashboard: o mesmo bus determinístico, ritmado no tempo real.

Uma thread avança o bus evento a evento; cada tick lógico vale `ms_por_tick`
milissegundos de parede. O operador comanda pela fila (thread-safe):

    pausar, retomar, passo, velocidade, agente (ligar/desligar), solicitar,
    decidir (decisão humana do aprovador), reiniciar (cenário, seed)

Desligar um agente não é simulado à parte: o bus perde o que chega a ele, e os
prazos (`reply_by`) disparam timeouts, reenvios e replanejamentos dos agentes BDI.
"""
import queue
import re
import threading
import time

from fin_mas.core.fsm import ProtocolViolation
from fin_mas.env.portes import PORTES
from fin_mas.env.scenarios import CENARIOS, montar

AGENTES_HUMANOS = ("SOL", "APR")


class Simulacao:
    def __init__(self, cenario="expediente_sma", seed=None, interativo=True, ms_por_tick=350, pausado=False,
                 pasta_dados=None):
        self.pasta_dados = pasta_dados  # onde o dashboard grava as planilhas enviadas
        self.lock = threading.RLock()
        self.comandos: queue.Queue = queue.Queue()
        self.ouvintes: list = []  # callbacks(evento: dict) para os clientes SSE
        self.ms_por_tick = ms_por_tick
        self.pausado = pausado
        self._passos_pendentes = 0
        self._parar = threading.Event()
        self._thread = None
        self.geracao = 0
        self._montar(cenario, seed, interativo)

    # ---- montagem ---------------------------------------------------------
    def _montar(self, cenario, seed, interativo, porte=None, fonte="sintetico") -> None:
        sc = CENARIOS[cenario]
        pasta = self.pasta_dados if fonte == "planilha" else None
        sistema, sids = montar(sc, seed if seed is not None else sc.seed, interativo=interativo, porte=porte,
                               pasta=pasta)  # se a planilha for inválida, levanta antes de trocar o estado
        self.cenario, self.interativo = sc, interativo
        self.seed = seed if seed is not None else sc.seed
        self.sistema, self.sids = sistema, sids
        self.porte, self.fonte = sistema.dataset.porte, fonte
        self.geracao += 1
        self._emitir({"tipo": "reset", "geracao": self.geracao, "cenario": sc.nome, "seed": self.seed})
        for registro in self.sistema.bus.audit.records:  # meta e pedidos iniciais, gravados antes da assinatura
            self._emitir_registro(registro)
        self.sistema.bus.audit.subscribe(self._emitir_registro)

    def _emitir_registro(self, registro) -> None:
        self._emitir({"tipo": "registro", "geracao": self.geracao, "registro": registro})

    def _emitir(self, evento) -> None:
        for ouvinte in list(self.ouvintes):
            ouvinte(evento)

    @property
    def registros(self) -> list:
        return self.sistema.bus.audit.records

    # ---- comandos -----------------------------------------------------------
    def comando(self, cmd: dict) -> None:
        """Enfileira um comando (chamado pelas threads HTTP)."""
        validar(cmd)
        self.comandos.put(cmd)

    def _aplicar(self, cmd: dict) -> None:
        tipo, bus = cmd["tipo"], self.sistema.bus
        if tipo == "pausar":
            self.pausado = True
        elif tipo == "retomar":
            self.pausado = False
        elif tipo == "passo":
            self._passos_pendentes += int(cmd.get("n", 1))
        elif tipo == "velocidade":
            self.ms_por_tick = max(0, int(cmd["ms_por_tick"]))
        elif tipo == "agente":
            bus.set_online(cmd["agente"], bool(cmd["online"]))
        elif tipo == "solicitar":
            sid = self.sistema.usuario.solicitar(cmd["intencao"],
                                                 competencia=cmd.get("competencia") or self.sistema.ambiente.principal)
            self.sids.append(sid)
        elif tipo == "decidir":
            try:
                self.sistema.aprovador.decidir(cmd["solicitacao"], cmd["decisao"], cmd.get("justificativa"))
            except ProtocolViolation as erro:  # a política ou o barramento recusou: avisa, não derruba
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"decisão recusada: {erro}"})
                return
        elif tipo == "reiniciar":
            try:
                self._montar(cmd.get("cenario", self.cenario.nome), cmd.get("seed"),
                             cmd.get("interativo", self.interativo), cmd.get("porte"), cmd.get("fonte", "sintetico"))
            except (ValueError, LookupError) as erro:  # planilha inválida: mantém a simulação atual
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"não foi possível carregar os dados: {erro}"})
                return
        self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle()})

    def processar_comandos(self) -> None:
        while True:
            try:
                cmd = self.comandos.get_nowait()
            except queue.Empty:
                return
            with self.lock:
                try:
                    self._aplicar(cmd)
                except Exception as erro:  # nenhum comando derruba a thread da simulação
                    self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                                  "erro": f"comando {cmd.get('tipo')} recusado: {type(erro).__name__}: {erro}"})

    # ---- avanço ---------------------------------------------------------------
    def passo(self) -> bool:
        """Processa os comandos pendentes e um evento do bus, sem ritmo (testes e depuração)."""
        self.processar_comandos()
        with self.lock:
            return self.sistema.bus.step()

    def _laco(self) -> None:
        while not self._parar.is_set():
            self.processar_comandos()
            if self.pausado and self._passos_pendentes == 0:
                time.sleep(0.03)
                continue
            with self.lock:
                bus = self.sistema.bus
                proximo = bus.proximo_tempo()
            if proximo is None:
                self._passos_pendentes = 0
                time.sleep(0.05)
                continue
            espera = (proximo - bus.now) * self.ms_por_tick / 1000
            if espera > 0 and self._passos_pendentes == 0 and not self._dormir(espera):
                continue  # um comando chegou durante a espera: reavaliar
            try:
                with self.lock:
                    self.sistema.bus.step()
            except Exception as erro:  # erro de agente não derruba o servidor: pausa e avisa o operador
                self.pausado = True
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"{type(erro).__name__}: {erro}"})
            if self._passos_pendentes:
                self._passos_pendentes -= 1

    def _dormir(self, segundos) -> bool:
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            if not self.comandos.empty() or self._parar.is_set():
                return False
            time.sleep(max(0.0, min(0.03, fim - time.monotonic())))
        return True

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._laco, name="simulacao-sma", daemon=True)
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=2)

    # ---- observação ---------------------------------------------------------------
    def controle(self) -> dict:
        bus = self.sistema.bus
        return {"cenario": self.cenario.nome, "seed": self.seed, "t": bus.now, "pausado": self.pausado,
                "ms_por_tick": self.ms_por_tick, "offline": sorted(bus.offline), "interativo": self.interativo,
                "fila": len(bus._queue), "geracao": self.geracao, "porte": self.porte, "fonte": self.fonte}

    def snapshot(self) -> dict:
        with self.lock:
            s = self.sistema
            return {
                "controle": self.controle(),
                "agentes": {aid: a.mente() for aid, a in s.bus.agents.items() if aid not in AGENTES_HUMANOS},
                "conversas": {cid: {"protocolo": c.protocol.id, "estado": c.state, "iniciador": c.initiator,
                                    "contraparte": c.counterpart, "final": c.is_final}
                              for cid, c in s.bus.conversations.items()},
                "pendentes_humanos": [{"solicitacao": sid, "conversation_id": m.conversation_id, **m.content}
                                      for sid, m in s.aprovador.pendentes.items()],
                "solicitacoes": {sid: (lambda r: None if r is None else {"performative": r.performative,
                                                                         "content": r.content})(
                    s.usuario.resposta(sid)) for sid in self.sids},
            }


TIPOS = {"pausar": (), "retomar": (), "passo": (), "velocidade": ("ms_por_tick",), "agente": ("agente", "online"),
         "solicitar": ("intencao",), "decidir": ("solicitacao", "decisao"), "reiniciar": ()}


class ComandoInvalido(ValueError):
    pass


CAMPOS = {  # campo -> (validador, descrição) para os comandos que vêm do navegador
    "n": (lambda v: _inteiro(v) and 1 <= v <= 1000, "inteiro entre 1 e 1000"),
    "ms_por_tick": (lambda v: _inteiro(v) and 0 <= v <= 10_000, "inteiro entre 0 e 10000"),
    "agente": (lambda v: isinstance(v, str) and v.startswith("AG-"), "id de agente (AG-...)"),
    "online": (lambda v: isinstance(v, bool), "booleano"),
    "intencao": (lambda v: isinstance(v, str) and 0 < len(v) <= 64, "texto"),
    "competencia": (lambda v: v is None or (isinstance(v, str) and COMPETENCIA.fullmatch(v) is not None),
                    "competência AAAA-MM"),
    "solicitacao": (lambda v: isinstance(v, str) and 0 < len(v) <= 64, "texto"),
    "justificativa": (lambda v: v is None or (isinstance(v, str) and len(v) <= 2000), "texto de até 2000 caracteres"),
    "seed": (lambda v: v is None or (_inteiro(v) and 0 <= v <= 2**31), "inteiro não negativo"),
    "interativo": (lambda v: isinstance(v, bool), "booleano"),
    "cenario": (lambda v: isinstance(v, str), "texto"),
    "porte": (lambda v: v is None or isinstance(v, str), "texto"),
    "fonte": (lambda v: isinstance(v, str), "texto"),
    "decisao": (lambda v: isinstance(v, str), "texto"),
}
COMPETENCIA = re.compile(r"20\d{2}-(0[1-9]|1[0-2])")


def _inteiro(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def validar(cmd) -> None:
    if not isinstance(cmd, dict) or cmd.get("tipo") not in TIPOS:
        raise ComandoInvalido(f"tipo de comando desconhecido: {cmd.get('tipo') if isinstance(cmd, dict) else cmd}")
    faltando = [c for c in TIPOS[cmd["tipo"]] if c not in cmd]
    if faltando:
        raise ComandoInvalido(f"comando {cmd['tipo']} sem {', '.join(faltando)}")
    for campo, valor in cmd.items():
        if campo in CAMPOS and not CAMPOS[campo][0](valor):
            raise ComandoInvalido(f"comando {cmd['tipo']}: campo {campo}={valor!r} deveria ser {CAMPOS[campo][1]}")
    if cmd["tipo"] == "agente" and cmd["agente"] in ("AG-ORQ",) + AGENTES_HUMANOS:
        raise ComandoInvalido(f"{cmd['agente']} não pode ser desligado (fronteira com o usuário)")
    if cmd["tipo"] == "reiniciar" and cmd.get("cenario", "expediente_sma") not in CENARIOS:
        raise ComandoInvalido(f"cenário desconhecido: {cmd.get('cenario')}")
    if cmd["tipo"] == "reiniciar" and cmd.get("porte") not in (None, *PORTES):
        raise ComandoInvalido(f"porte desconhecido: {cmd.get('porte')}")
    if cmd["tipo"] == "reiniciar" and cmd.get("fonte", "sintetico") not in ("sintetico", "planilha"):
        raise ComandoInvalido(f"fonte desconhecida: {cmd.get('fonte')}")
    if cmd["tipo"] == "decidir" and cmd["decisao"] not in ("waiver", "corrigir", "corrigir_parcial", "bloquear", "nenhuma"):
        raise ComandoInvalido(f"decisão desconhecida: {cmd['decisao']}")

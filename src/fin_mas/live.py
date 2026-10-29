"""Execução ao vivo do SMA para o dashboard: o mesmo bus determinístico, ritmado no tempo real.

Uma thread avança o bus evento a evento; cada tick lógico vale `ms_por_tick`
milissegundos de parede. O operador comanda pela fila (thread-safe):

    pausar, retomar, passo, velocidade, agente (ligar/desligar), solicitar,
    decidir (decisão humana do aprovador), reiniciar (cenário, seed)

Desligar um agente não é simulado à parte: o bus perde o que chega a ele, e os
prazos (`reply_by`) disparam timeouts, reenvios e replanejamentos dos agentes BDI.
"""
import queue
import threading
import time

from fin_mas.env.scenarios import CENARIOS, montar

AGENTES_HUMANOS = ("SOL", "APR")


class Simulacao:
    def __init__(self, cenario="expediente_sma", seed=None, interativo=True, ms_por_tick=350, pausado=False):
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
    def _montar(self, cenario, seed, interativo) -> None:
        sc = CENARIOS[cenario]
        self.cenario, self.interativo = sc, interativo
        self.seed = seed if seed is not None else sc.seed
        self.sistema, self.sids = montar(sc, self.seed, interativo=interativo)
        self.geracao += 1
        self.sistema.bus.audit.subscribe(self._emitir_registro)
        self._emitir({"tipo": "reset", "geracao": self.geracao, "cenario": sc.nome, "seed": self.seed})

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
            self.sistema.aprovador.decidir(cmd["solicitacao"], cmd["decisao"], cmd.get("justificativa"))
        elif tipo == "reiniciar":
            self._montar(cmd.get("cenario", self.cenario.nome), cmd.get("seed"),
                         cmd.get("interativo", self.interativo))
        self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle()})

    def processar_comandos(self) -> None:
        while True:
            try:
                cmd = self.comandos.get_nowait()
            except queue.Empty:
                return
            with self.lock:
                self._aplicar(cmd)

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
            with self.lock:
                self.sistema.bus.step()
            if self._passos_pendentes:
                self._passos_pendentes -= 1

    def _dormir(self, segundos) -> bool:
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            if not self.comandos.empty() or self._parar.is_set():
                return False
            time.sleep(min(0.03, fim - time.monotonic()))
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
                "fila": len(bus._queue), "geracao": self.geracao}

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


def validar(cmd) -> None:
    if not isinstance(cmd, dict) or cmd.get("tipo") not in TIPOS:
        raise ComandoInvalido(f"tipo de comando desconhecido: {cmd.get('tipo') if isinstance(cmd, dict) else cmd}")
    faltando = [c for c in TIPOS[cmd["tipo"]] if c not in cmd]
    if faltando:
        raise ComandoInvalido(f"comando {cmd['tipo']} sem {', '.join(faltando)}")
    if cmd["tipo"] == "agente" and cmd["agente"] in ("AG-ORQ",) + AGENTES_HUMANOS:
        raise ComandoInvalido(f"{cmd['agente']} não pode ser desligado (fronteira com o usuário)")
    if cmd["tipo"] == "reiniciar" and cmd.get("cenario", "expediente_sma") not in CENARIOS:
        raise ComandoInvalido(f"cenário desconhecido: {cmd.get('cenario')}")
    if cmd["tipo"] == "decidir" and cmd["decisao"] not in ("waiver", "corrigir", "corrigir_parcial", "nenhuma"):
        raise ComandoInvalido(f"decisão desconhecida: {cmd['decisao']}")

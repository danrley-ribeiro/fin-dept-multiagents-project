"""Execução ao vivo do SMA para o dashboard: o mesmo bus determinístico, ritmado no tempo real.

Uma thread avança o bus evento a evento; cada tick lógico vale `ms_por_tick`
milissegundos de parede. O operador comanda pela fila (thread-safe):

    pausar, retomar, passo, velocidade, agente (ligar/desligar), solicitar,
    decidir (decisão humana do aprovador), reiniciar (cenário, seed)

Desligar um agente não é simulado à parte: o bus perde o que chega a ele, e os
prazos (`reply_by`) disparam timeouts, reenvios e replanejamentos dos agentes BDI.

DSM3 (ADR-009): com o SVC-IAM ligado (`acesso`), todo comando chega com o **ator** (a sessão
da pessoa). A camada confere a permissão do comando (`PERMISSAO_COMANDO`, negado por padrão),
grava um registro `operador` com quem agiu, liga o pedido à pessoa (`solicitado_por`) e
entrega a decisão humana com a sessão dela, que vira o atestado exigido pela política.
Comandos novos: `modelo` (LLM de um agente) e, em `reiniciar`, o nível de cognição.
"""
import math
import queue
import re
import threading
import time

from fin_mas.cognicao import NIVEIS
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.schema import FORMATOS, _tipo_ok
from fin_mas.env.portes import PORTES
from fin_mas.env.segmentos import SEGMENTOS
from fin_mas.env.scenarios import CENARIOS, montar
from fin_mas.services.modelos import ConfiguracaoInvalida

AGENTES_HUMANOS = ("SOL", "APR")
PERMISSAO_COMANDO = {  # comando -> permissão exigida (models/permissions.yaml)
    "pausar": "PERM-SIM-OPERAR", "retomar": "PERM-SIM-OPERAR", "passo": "PERM-SIM-OPERAR",
    "velocidade": "PERM-SIM-OPERAR", "reiniciar": "PERM-SIM-OPERAR", "agente": "PERM-AGT-ENERGIA",
    "solicitar": "PERM-SOL-CRIAR", "decidir": "PERM-APR-DECIDIR", "modelo": "PERM-MOD-CONFIG",
}
CAMPOS_MODELO = ("llm", "provedor", "modelo", "base_url", "usos", "consentimento_externo", "pseudonimizar",
                 "max_tokens", "cota_tokens", "preco_entrada", "preco_saida")


class Simulacao:
    def __init__(self, cenario="expediente_sma", seed=None, interativo=True, ms_por_tick=350, pausado=False,
                 pasta_dados=None, acesso=None, cognicao=None, empresa=None, memoria=None):
        self.empresa = empresa  # DSM4 (IAM-09): empresa desta simulação; decisões só de sessões ativas nela
        self.memoria = memoria  # DSM4: arquivo do SVC-MEM desta empresa (dados/<empresa>/memoria.json)
        self.pasta_dados = pasta_dados  # onde o dashboard grava as planilhas enviadas
        self.acesso = acesso  # SVC-IAM: com ele, comando sem pessoa autorizada é negado
        self.cognicao = cognicao  # None = a do cenário
        self.config_llm: dict[str, dict] = {}  # LLM por agente, reaplicado a cada reinício
        self.fabrica_fonte = None  # fonte "conector": devolve um Ambiente novo a cada reinício (ADR-011)
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
    def cadastro_da_empresa(self) -> dict:
        """Porte e segmento da empresa desta simulação no cadastro (IAM-09); vazio sem empresa cadastrada."""
        if not self.empresa or self.acesso is None:
            return {}
        e = self.acesso.empresas().get(self.empresa) or {}
        return {k: e[k] for k in ("porte", "segmento") if e.get(k)}

    def _montar(self, cenario, seed, interativo, porte=None, fonte="sintetico", segmento=None) -> None:
        sc = CENARIOS[cenario]
        cadastro = self.cadastro_da_empresa()  # empresa cadastrada: o porte (alçadas, dupla aprovação) é o do cadastro
        porte, segmento = porte or cadastro.get("porte"), segmento or cadastro.get("segmento")
        pasta = self.pasta_dados if fonte == "planilha" else None
        llm = {a: {k: v for k, v in c.items() if k != "llm"} for a, c in self.config_llm.items() if c.get("llm")}
        if fonte == "conector" and self.fabrica_fonte is None:
            raise LookupError("nenhuma fonte de conector ativada (aba Fontes de dados)")
        ambiente = self.fabrica_fonte() if fonte == "conector" else None
        sistema, sids = montar(sc, seed if seed is not None else sc.seed, interativo=interativo, porte=porte,
                               pasta=pasta, acesso=self.acesso, cognicao=self.cognicao,
                               llm=llm or None, segmento=segmento, memoria=self.memoria,
                               ambiente=ambiente)  # dados inválidos levantam antes de trocar o estado
        sistema.politica.empresa = self.empresa
        anterior = getattr(getattr(self, "sistema", None), "ambiente", None)
        if anterior is not None and hasattr(anterior, "fechar"):
            anterior.fechar()
        self.cenario, self.interativo = sc, interativo
        self.seed = seed if seed is not None else sc.seed
        self.sistema, self.sids = sistema, sids
        self.porte, self.fonte = sistema.dataset.porte, fonte
        self.segmento = getattr(sistema.dataset, "segmento", None)
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
    def comando(self, cmd: dict, ator=None) -> None:
        """Enfileira um comando (chamado pelas threads HTTP). `ator` é a sessão de quem pediu."""
        validar(cmd)
        if self.acesso is not None:  # negado por padrão: sem sessão ou sem a permissão do comando, não entra na fila
            self.acesso.exigir(ator, PERMISSAO_COMANDO[cmd["tipo"]])
            if cmd["tipo"] == "reiniciar" and cmd.get("cognicao") not in (None, self.cognicao or self.cenario.cognicao):
                self.acesso.exigir(ator, "PERM-MOD-CONFIG")  # mudar o nível de cognição é ajuste de modelo
            cadastro = self.cadastro_da_empresa()
            if cmd["tipo"] == "reiniciar" and any(cmd.get(k) not in (None, cadastro[k]) for k in cadastro):
                # porte e segmento da empresa cadastrada definem alçadas e dupla aprovação: trocá-los é administrar
                # a empresa, não operar a simulação (IAM-09)
                self.acesso.exigir(ator, "PERM-IAM-EMPRESAS")
        if cmd["tipo"] == "agente" and cmd.get("agente") not in self.sistema.bus.agents:
            raise ComandoInvalido(f"agente desconhecido: {cmd.get('agente')!r}")
        self.comandos.put((cmd, ator))

    def _aplicar(self, cmd: dict, ator=None) -> None:
        tipo, bus = cmd["tipo"], self.sistema.bus
        if ator is not None and tipo != "reiniciar":  # quem agiu fica no trace (o reinício registra depois de montar)
            bus.audit.record(bus.now, "operador", ator=ator.usuario, comando=tipo,
                             detalhe={k: v for k, v in cmd.items() if k not in ("tipo", "justificativa")})
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
                                                 competencia=cmd.get("competencia") or self.sistema.ambiente.principal,
                                                 solicitado_por=ator.usuario if ator is not None else None)
            self.sids.append(sid)
        elif tipo == "modelo":
            campos = {k: (tuple(v) if k == "usos" else v) for k, v in cmd.items() if k in CAMPOS_MODELO}
            try:
                self.sistema.modelos.configurar(cmd["agente"], **campos)
            except ConfiguracaoInvalida as erro:
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"configuração de LLM recusada: {erro}"})
                return
            self.config_llm[cmd["agente"]] = {**self.config_llm.get(cmd["agente"], {}), **campos}
        elif tipo == "decidir":
            try:
                enviada = self.sistema.aprovador.decidir(cmd["solicitacao"], cmd["decisao"],
                                                         cmd.get("justificativa"), ator, cmd.get("delegacao"))
            except (ProtocolViolation, PermissionError) as erro:  # a política, o barramento ou o acesso recusou
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"decisão recusada: {erro} (a pendência continua aberta)"})
                return
            if not enviada:
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": "decisão não enviada: não há pendência para essa solicitação "
                                      "ou a opção não foi oferecida pela política"})
                return
        elif tipo == "reiniciar":
            anterior = self.cognicao
            if "cognicao" in cmd:
                self.cognicao = cmd["cognicao"]
            try:
                self._montar(cmd.get("cenario", self.cenario.nome), cmd.get("seed"),
                             cmd.get("interativo", self.interativo), cmd.get("porte"), cmd.get("fonte", "sintetico"),
                             cmd.get("segmento"))
            except (ValueError, LookupError) as erro:  # planilha inválida: mantém a simulação atual
                self.cognicao = anterior
                self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle(),
                              "erro": f"não foi possível carregar os dados: {erro}"})
                return
            if ator is not None:
                self.sistema.bus.audit.record(self.sistema.bus.now, "operador", ator=ator.usuario, comando="reiniciar",
                                              detalhe={k: v for k, v in cmd.items() if k != "tipo"})
        self._emitir({"tipo": "controle", "geracao": self.geracao, "estado": self.controle()})

    def processar_comandos(self) -> None:
        while True:
            try:
                item = self.comandos.get_nowait()
            except queue.Empty:
                return
            cmd, ator = item if isinstance(item, tuple) else (item, None)
            with self.lock:
                try:
                    self._aplicar(cmd, ator) if ator is not None else self._aplicar(cmd)
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
                "fila": len(bus._queue), "geracao": self.geracao, "porte": self.porte, "fonte": self.fonte,
                "segmento": self.segmento,
                "cognicao": self.cognicao or self.cenario.cognicao}

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
         "solicitar": ("intencao",), "decidir": ("solicitacao", "decisao"), "reiniciar": (), "modelo": ("agente",)}


class ComandoInvalido(ValueError):
    pass


DELEGACAO = re.compile(r"DLG-\d{3,6}")
PRECO_MAXIMO = 1_000_000  # preço por milhão de tokens: 1e999 vira inf e deixaria o JSON das respostas inválido
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
    "segmento": (lambda v: v is None or isinstance(v, str), "texto"),
    "fonte": (lambda v: isinstance(v, str), "texto"),
    "decisao": (lambda v: isinstance(v, str), "texto"),
    "cognicao": (lambda v: v in NIVEIS, f"um de {', '.join(NIVEIS)}"),
    "llm": (lambda v: isinstance(v, bool), "booleano"),
    "provedor": (lambda v: v is None or (isinstance(v, str) and len(v) <= 32), "texto"),
    "modelo": (lambda v: isinstance(v, str) and 0 < len(v) <= 128, "texto"),
    "base_url": (lambda v: v is None or (isinstance(v, str) and len(v) <= 300 and v.startswith(("http://", "https://"))),
                 "URL http(s)"),
    "usos": (lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v), "lista de textos"),
    "consentimento_externo": (lambda v: isinstance(v, bool), "booleano"),
    "pseudonimizar": (lambda v: v is None or isinstance(v, bool), "booleano"),
    "max_tokens": (lambda v: _inteiro(v) and 1 <= v <= 200_000, "inteiro entre 1 e 200000"),
    "cota_tokens": (lambda v: _inteiro(v) and 1 <= v <= 100_000_000, "inteiro positivo"),
    "preco_entrada": (lambda v: v is None or _preco(v), f"número finito entre 0 e {PRECO_MAXIMO}"),
    "preco_saida": (lambda v: v is None or _preco(v), f"número finito entre 0 e {PRECO_MAXIMO}"),
    "delegacao": (lambda v: v is None or (isinstance(v, str) and DELEGACAO.fullmatch(v) is not None),
                  "id de delegação (DLG-001) ou nada (POL-11)"),
}
COMPETENCIA = FORMATOS["aaaa-mm"][0]  # mesma regra do barramento (core/schema.py)


def _preco(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= PRECO_MAXIMO


def _inteiro(v) -> bool:
    return _tipo_ok(v, int)


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
    if cmd["tipo"] == "reiniciar" and cmd.get("segmento") not in (None, *SEGMENTOS):
        raise ComandoInvalido(f"segmento desconhecido: {cmd.get('segmento')}")
    if cmd["tipo"] == "reiniciar" and cmd.get("fonte", "sintetico") not in ("sintetico", "planilha", "conector"):
        raise ComandoInvalido(f"fonte desconhecida: {cmd.get('fonte')}")
    if cmd["tipo"] == "decidir" and cmd["decisao"] not in ("waiver", "corrigir", "corrigir_parcial", "bloquear", "nenhuma"):
        raise ComandoInvalido(f"decisão desconhecida: {cmd['decisao']}")

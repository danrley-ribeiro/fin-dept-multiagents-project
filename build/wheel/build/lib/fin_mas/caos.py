"""Modelo de falhas aleatórias, controlado e reproduzível por seed (DSM4, experimento).

    modelo = ModeloFalhas(seed=7, perda=0.15, indisponibilidades=1, aprovador="lento")
    sistema = build_system(seed=7, plantar=modelo.plantios(), caos=modelo)

Os cenários da DSM3 injetam falhas fixas (`Fault`: "perca as duas primeiras mensagens para o
AG-CUS"). Aqui cada falha é **sorteada**, e o sorteio depende só da seed e do fator:

    random.Random(f"{seed}:{fator}")

Cada fator tem o seu fluxo, independente dos outros e do gerador dos dados da empresa
(`env/dataset.py` usa `random.Random(seed)`): ligar a perda de mensagens não muda os plantios,
nem o perfil do aprovador, nem um centavo do dataset.

Fatores:

- `plantios`            quais inconformidades e desvios existem nos dados (carga da execução);
- `aprovador:perfil`    como o humano decide: diligente, cauteloso ou rigoroso;
- `aprovador:atraso`    quanto ele demora, ou se não aparece (`aprovador="lento"`);
- `perda:<mensagem>:<n>`  se a n-ésima ocorrência de uma mensagem entre agentes se perde;
- `jitter:<mensagem>:<n>` quantos ticks a mais ela leva para chegar;
- `indisponibilidade`   qual especialista sai do ar, quando e por quanto tempo;
- ataques               `env/ataques.py` e `env/ataques_acesso.py`, disparados enquanto um veto
                        aguarda o aprovador (não têm sorteio: são sempre os mesmos).

A perda e o atraso são sorteados por mensagem com chave própria (remetente, destinatário,
protocolo, performativo e ordem de ocorrência). Assim a mesma mensagem tem o mesmo destino em
braços e variantes diferentes da mesma seed, e o que se perde com probabilidade 0,05 também se
perde com 0,15 (números aleatórios comuns). Só as mensagens entre agentes (PROT-DEL, PROT-CMP,
PROT-QRY) se perdem ou atrasam; a conversa com as pessoas (PROT-SOL, PROT-APR) é a interface
local do sistema.

`Bus(caos=None)` é o padrão: sem modelo instalado, o barramento não faz nada disto.
"""
import random
from dataclasses import asdict, dataclass

from fin_mas.core.fsm import ProtocolViolation

ESPECIALISTAS = ("AG-CUS", "AG-ORC", "AG-RES", "AG-CIN", "AG-REL")
ENTRE_AGENTES = ("PROT-DEL", "PROT-CMP", "PROT-QRY")
PLANTIOS_BASE = ("alcada", "sod", "duplicidade", "competencia", "desvio_orcamentario", "divergencia_fonte",
                 "desvio_irregular")
PERFIS = (("diligente", 0.75), ("cauteloso", 0.15), ("rigoroso", 0.10))
P_VARIANTE_OBSERVACAO = 0.3  # observação parafraseada (desvio_irregular) ou alarme falso (desvio_orcamentario)
ATRASO_HUMANO = (0.3, 1.3)  # fração do prazo de aprovação que o aprovador lento demora
SEGUNDA_PESSOA = "avaliador"  # segunda conta com cargo para a dupla aprovação no bloco com acesso
P_AUSENTE = 0.15
INICIO_INDISPONIBILIDADE = (1, 30)  # tick em que o especialista sai do ar
DURACAO_INDISPONIBILIDADE = (8, 30)  # ticks fora do ar


def escolher_decisao(perfil: str, opcoes) -> str:
    """Decisão do aprovador simulado diante das opções que a política deixou abertas."""
    if perfil == "rigoroso":
        return "bloquear"
    if "corrigir" in opcoes:
        return "corrigir"
    return "waiver" if perfil == "diligente" and "waiver" in opcoes else "bloquear"


@dataclass
class ModeloFalhas:
    seed: int
    perda: float = 0.0  # probabilidade de perda de cada mensagem entre agentes
    perda_enlaces: tuple = ()  # ((destinatário, performativo, probabilidade), ...): perda só nesses enlaces
    jitter: int = 0  # atraso extra de entrega, uniforme em 0..jitter ticks
    indisponibilidades: int = 0  # quantos especialistas saem do ar (um sorteio cada)
    aprovador: str = "pontual"  # pontual | lento (demora uma fração do prazo ou não aparece)
    ataque: bool = False  # env/ataques.py enquanto o veto aguarda
    ataque_acesso: bool = False  # env/ataques_acesso.py (só com o SVC-IAM ligado)
    p_plantio: float = 0.35
    plantios_forcados: tuple = ()
    persona: str | None = None  # conta que decide, com o SVC-IAM ligado (ex.: "controller")

    def __post_init__(self):
        if self.aprovador not in ("pontual", "lento"):
            raise ValueError(f"aprovador desconhecido: {self.aprovador} (use pontual ou lento)")
        self._ocorrencias: dict[str, int] = {}

    # ---- fluxos ---------------------------------------------------------------------
    def _rng(self, fator: str) -> random.Random:
        return random.Random(f"{self.seed}:{fator}")

    def _proxima(self, fator: str, msg) -> random.Random:
        chave = f"{fator}:{msg.sender}>{msg.receiver}:{msg.protocol}:{msg.performative}"
        self._ocorrencias[chave] = self._ocorrencias.get(chave, 0) + 1
        return self._rng(f"{chave}:{self._ocorrencias[chave]}")

    def descricao(self) -> dict:
        """Configuração que difere do padrão (vai para o `meta` do trace e para o manifesto)."""
        padrao = asdict(ModeloFalhas(self.seed))
        atual = asdict(self)
        return {"seed": self.seed, **{k: (list(v) if isinstance(v, tuple) else v) for k, v in atual.items()
                                      if v != padrao[k]}}

    # ---- carga: plantios e perfil do aprovador --------------------------------------------
    def plantios(self) -> tuple:
        """Inconformidades e desvios da execução, sorteados; os mesmos para todo braço e condição da seed."""
        rng = self._rng("plantios")
        sorteados = [p for p in PLANTIOS_BASE if rng.random() < self.p_plantio]
        parafraseada, alarme_falso = rng.random() < P_VARIANTE_OBSERVACAO, rng.random() < P_VARIANTE_OBSERVACAO
        escolhidos = [p for p in PLANTIOS_BASE if p in sorteados or p in self.plantios_forcados]
        if "desvio_irregular" in escolhidos and parafraseada:
            escolhidos.append("observacao_parafraseada")
        if "desvio_orcamentario" in escolhidos and alarme_falso:
            escolhidos.append("observacao_alarme_falso")
        return tuple(escolhidos)

    def perfil_aprovador(self) -> str:
        u, acumulado = self._rng("aprovador:perfil").random(), 0.0
        for perfil, p in PERFIS:
            acumulado += p
            if u < acumulado:
                return perfil
        return PERFIS[-1][0]

    # ---- ganchos do barramento ------------------------------------------------------------
    def _probabilidade_de_perda(self, msg) -> float:
        if msg.protocol not in ENTRE_AGENTES:
            return 0.0
        p = self.perda
        for destinatario, performativo, p_enlace in self.perda_enlaces:
            if msg.receiver == destinatario and msg.performative == performativo:
                p = max(p, p_enlace)
        return p

    def perder(self, msg) -> bool:
        """Chamado pelo barramento na entrega: True = a mensagem se perde."""
        p = self._probabilidade_de_perda(msg)
        return p > 0 and self._proxima("perda", msg).random() < p

    def atraso(self, msg) -> int:
        """Chamado pelo barramento no envio: ticks a mais até a entrega."""
        if self.jitter <= 0 or msg.protocol not in ENTRE_AGENTES:
            return 0
        return self._proxima("jitter", msg).randint(0, self.jitter)

    # ---- instalação num sistema montado ---------------------------------------------------
    def instalar(self, sistema) -> None:
        """Agenda as indisponibilidades, troca o comportamento do aprovador e arma os ataques."""
        bus = sistema.bus
        bus.caos = self
        rng = self._rng("indisponibilidade")
        for _ in range(self.indisponibilidades):
            agente = rng.choice(ESPECIALISTAS)
            inicio, duracao = rng.randint(*INICIO_INDISPONIBILIDADE), rng.randint(*DURACAO_INDISPONIBILIDADE)
            bus.agendar(inicio, lambda a=agente: bus.set_online(a, False),
                        f"caos: {agente} fora do ar por {duracao} ticks")
            bus.agendar(inicio + duracao, lambda a=agente: bus.set_online(a, True), f"caos: {agente} de volta")
        self.instalar_aprovador(sistema.aprovador, bus, sistema.politica.prazo)
        if self.ataque:
            from fin_mas.env import ataques
            ataques.preparar(sistema)
        if self.ataque_acesso and sistema.acesso is not None:
            from fin_mas.env import ataques_acesso
            ataques_acesso.preparar(sistema)

    def instalar_aprovador(self, aprovador, bus, prazo: int) -> None:
        """O aprovador simulado passa a decidir pelo perfil sorteado e, se `lento`, com atraso.

        É o mesmo `Aprovador` de `env/scenarios.py` (mesma mensagem, mesmo atestado, mesma política):
        só a escolha da decisão e o momento em que ela sai vêm daqui. Serve ao SMA e ao workflow.
        """
        perfil, rng, original = self.perfil_aprovador(), self._rng("aprovador:atraso"), aprovador.on_message
        prefixo = f"{self.persona}:" if self.persona else ""

        def decidir(msg) -> None:
            if not bus.conversations[msg.conversation_id].is_final:
                escolha = escolher_decisao(perfil, msg.content["opcoes"])
                decisao = prefixo + escolha
                aprovador.decisoes, aprovador.decisao = [decisao], decisao
                if self.persona and escolha not in ("bloquear", "nenhuma"):
                    # com o SVC-IAM, a liberação acima do limite do porte exige duas pessoas (POL-12): o roteiro
                    # tem uma segunda pessoa com cargo para aprovar depois do aval da primeira. Com uma só, o
                    # ticket expirava e o bloco D media a falta da segunda pessoa, não o custo do acesso (M2).
                    aprovador.decisoes = [decisao, f"{SEGUNDA_PESSOA}:{escolha}"]
            original(msg)

        def decidir_depois(msg) -> None:
            if bus.conversations[msg.conversation_id].is_final or bus.now + 1 >= msg.content["prazo"]:
                return  # chegou depois do prazo do ticket: não há mais o que decidir
            try:
                decidir(msg)
            except ProtocolViolation:
                pass  # a política recusou por prazo (já auditado como `rejected`): o ticket expira sozinho

        def on_message(msg) -> None:
            if msg.protocol != "PROT-APR" or msg.performative != "propose-action" or self.aprovador == "pontual":
                decidir(msg) if msg.protocol == "PROT-APR" and msg.performative == "propose-action" else original(msg)
                return
            ausente, fracao = rng.random() < P_AUSENTE, rng.uniform(*ATRASO_HUMANO)
            if ausente:
                aprovador.avisos.append(msg)
                bus.audit.record(bus.now, "ambiente", evento="caos: aprovador ausente (não vai decidir)")
                return
            atraso = max(1, round(fracao * prazo))
            bus.agendar(bus.now + atraso, lambda: decidir_depois(msg), f"caos: aprovador chega {atraso} ticks depois")

        aprovador.on_message = on_message

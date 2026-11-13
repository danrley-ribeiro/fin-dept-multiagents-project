"""Parâmetros de coordenação injetáveis em `build_system(parametros=...)` (DSM4, experimento).

Os padrões são os valores que o sistema já usava (constantes de `agents/orq.py`, `services/politica.py`
e o `ttl` de `build_system`): `Parametros()` não muda nenhum trace. O experimento
(`fin_mas.estudo`) varia um de cada vez (varredura) e desliga um mecanismo de cada vez (ablação).

Mecanismos e como cada um é desligado:

- reenvio do Orquestrador ....... `max_tentativas=1`
- veto com correção ............. `max_correcoes=0` (o veto continua; a correção deixa de ser oferecida)
- negociação de prazo ........... `max_extensao=0` (toda proposta de prazo é recusada)
- reserva de período ............ `reserva_periodo=False`
- cognição local ................ `build_system(cognicao="basico")`
"""
from dataclasses import asdict, dataclass

from fin_mas.agents.orq import MAX_CORRECOES, MAX_EXTENSAO, MAX_TENTATIVAS, PRAZO_SUBTAREFA

TTL_RESERVA = 200  # o `ttl` padrão de `build_system`


@dataclass(frozen=True)
class Parametros:
    prazo_subtarefa: int = PRAZO_SUBTAREFA  # ticks de reply_by por delegação
    max_tentativas: int = MAX_TENTATIVAS  # envio original + reenvios
    max_correcoes: int = MAX_CORRECOES  # ciclos de correção que o Orquestrador ainda oferece ao aprovador
    max_extensao: int = MAX_EXTENSAO  # ticks a mais que uma subtarefa pode negociar
    ttl_reserva: int = TTL_RESERVA  # validade da reserva do período
    prazo_aprovacao: int | None = None  # None = o do modo (20 em lote, 1.800 no dashboard)
    limiar_percentual: int | None = None  # None = o do porte (models/portes.yaml)
    limiar_absoluto: int | None = None  # idem, em centavos
    reserva_periodo: bool = True  # o fechamento reserva o mês (PROT-LCK)

    def diferencas(self) -> dict:
        """Só o que difere do padrão (vai para o `meta` do trace e para o manifesto do experimento)."""
        padrao = asdict(Parametros())
        return {k: v for k, v in asdict(self).items() if v != padrao[k]}


PADRAO = Parametros()

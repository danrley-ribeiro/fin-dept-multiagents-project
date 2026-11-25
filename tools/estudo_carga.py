"""Ensaio exploratório pareado de volume e frequência de irregularidades da DSM4."""
import argparse
import csv
import random
from pathlib import Path

from fin_mas import baseline_eq
from fin_mas.env.dataset import Ambiente, Dataset
from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.estudo import medir_sma, medir_workflow, protocolos_em_cache


def linhas():
    for seed in range(1, 31):
        sorteio = random.Random(seed).random()
        for porte in ("pequena", "media"):
            for volume in (12, 96):
                for frequencia in (0.2, 0.8):
                    plantar = ("alcada",) if sorteio < frequencia else ()
                    for braco in ("sma_basico", "wf_equivalente"):
                        ds = Dataset(seed, porte=porte, plantar=plantar, volume_base=volume)
                        ambiente = Ambiente.de_dataset(ds)
                        total = len(ds.lancamentos)
                        if braco == "sma_basico":
                            sc = Scenario("carga", "fechamento sob carga", "fechar_mes", decisao_aprovador="corrigir")
                            medidas = medir_sma(run_scenario(sc, seed=seed, ambiente=ambiente))
                        else:
                            medidas = medir_workflow(baseline_eq.executar(ambiente=ambiente, decisao_aprovador="corrigir"))
                        yield dict(seed=seed, porte=porte, volume_base=volume, frequencia=frequencia,
                                   lancamentos=total, alcada_plantada=int(bool(plantar)), braco=braco,
                                   **{k: medidas[k] for k in ("status", "conformidade_correta", "criticas_corrigidas",
                                      "criticas_publicadas_sem_tratamento", "intervencoes_humanas", "mensagens",
                                      "latencia_ticks")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saida", type=Path)
    destino = parser.parse_args().saida
    with protocolos_em_cache(), destino.open("w", newline="", encoding="utf-8") as arquivo:
        registros = iter(linhas())
        primeira = next(registros)
        writer = csv.DictWriter(arquivo, fieldnames=primeira, lineterminator="\n")
        writer.writeheader()
        writer.writerow(primeira)
        writer.writerows(registros)

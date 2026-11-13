# DSM4 — Experimentação, documentação e entrega final

Páginas da DSM4 disponíveis até aqui: o experimento redesenhado.

| Página | Conteúdo |
|---|---|
| {doc}`experimento` | Pré-registro: perguntas, hipóteses, braços, fatores, métricas, plano de análise e ameaças previstas. Versionado antes de existir qualquer resultado. |
| {doc}`resultados` | O que foi medido: resposta a cada pergunta, comportamento coletivo, o que não se confirmou, defeitos encontrados, desvios do pré-registro e ameaças à validade. |
| {doc}`tabelas` | Todas as tabelas e todos os testes de hipótese, gerados pelo comando do experimento. |

```bash
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # ou: make experimento (cerca de 3 minutos)
python -m fin_mas experimento --rapido --out /tmp/experimento            # 3 seeds, alguns segundos
```

```{toctree}
:maxdepth: 1

experimento
resultados
tabelas
```

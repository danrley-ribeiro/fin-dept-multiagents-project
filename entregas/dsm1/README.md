# DSM1 — Cenário, requisitos e modelagem

**Sistema Multiagente de Controladoria** — INE5628 Sistemas Multiagentes (UFSC/CTC/INE),
Prof. Rafael Luiz Cancian.

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Enunciado: [`enunciados/DSM1.txt`](../../enunciados/DSM1.txt).

## Conteúdo da entrega

| Exigido pelo enunciado | Arquivo |
|---|---|
| PDF (~4–6 páginas) | [`documentacao/main.pdf`](documentacao/main.pdf) — 6 páginas com referências |
| Diagramas/modelos editáveis | [`modelos-editaveis/`](modelos-editaveis/) (Mermaid `.mmd`) |
| Imagens dos diagramas | [`diagramas/`](diagramas/) (`.png`, uma por `.mmd`) |
| `README.md` | este arquivo |
| `USO_DE_IA.md` | [`USO_DE_IA.md`](USO_DE_IA.md) |

O PDF cobre: cenário-problema, motivação e objetivos; fronteira e ambiente; requisitos com
evidência de aceite; agentes, papéis e responsabilidades; objetivos, percepções, ações e
estado/conhecimento; interações e coordenação (protocolos como máquinas de estados e normas);
métricas e matriz de rastreabilidade.

## Diagramas

| Diagrama | Editável | Imagem |
|---|---|---|
| Fronteira do sistema | `ambiente_fronteira.mmd` | `ambiente_fronteira.png` |
| Organização do SMA (Figura 1) | `roles_organizacao.mmd` | `roles_organizacao.png` |
| Máquinas de estados dos protocolos (Figura 2: DEL e APR) | `protocols_fsm_PROT-{SOL,DEL,QRY,CMP,LCK,APR}.mmd` | `protocols_fsm_PROT-*.png` |
| Sequência: fechar o resultado do mês (Figura 3) | `protocols_sequencia_fechar_mes.mmd` | `protocols_sequencia_fechar_mes.png` |
| Sequência: avaliar o orçamento do trimestre | `protocols_sequencia_avaliar_orcamento.mmd` | `protocols_sequencia_avaliar_orcamento.png` |
| Sequência: veto e waiver | `protocols_sequencia_veto_waiver.mmd` | `protocols_sequencia_veto_waiver.png` |

As máquinas de estados são geradas por `tools/trace.py` a partir de `models/protocols.yaml`.
As figuras do PDF são desenhadas em TikZ dentro do próprio `main.tex`.

## Como compilar o PDF

```bash
cd entregas/dsm1/documentacao
latexmk -pdf main.tex
```

O `main.tex` é um arquivo único: figuras, tabelas e referências estão nele.

Documentação navegável e rastreável: <https://fin-dept-multiagents-project.readthedocs.io>.

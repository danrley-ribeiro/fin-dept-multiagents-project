# DSM1 — Cenário, requisitos e modelagem

**Sistema Multiagente de Controladoria** — INE5628 Sistemas Multiagentes (UFSC/CTC/INE),
Prof. Rafael Luiz Cancian.

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

## Versão 2 (revisão pós-feedback)

[`documentacao/main-v2.pdf`](documentacao/main-v2.pdf) (fonte: [`main-v2.tex`](documentacao/main-v2.tex)) incorpora
o feedback do professor: AG-ORC e AG-CIN como agentes **BDI** (crenças, desejos, planos com utilidade, seleção e
reconsideração de intenções), tabela de **decisões distribuídas** (consulta direta ORC→CIN, veto com correção),
**MET-01 corrigida** e as novas MET-13 e MET-14, **regras por porte** de empresa (micro a grande, com base legal),
empresas sem ERP (planilhas) e o mapa dos **checkpoints CP1–CP13**. A primeira página traz o quadro "Alterações após
o feedback". A versão 1 entregue (`main.pdf`) foi preservada sem alterações. Os diagramas novos (ciclo BDI,
ORC↔CIN, veto→correção) estão em [`../dsm2/modelos-editaveis/`](../dsm2/modelos-editaveis/).

## Conteúdo da entrega

| Exigido pelo enunciado | Arquivo |
|---|---|
| PDF (~4–6 páginas) | [`documentacao/main.pdf`](documentacao/main.pdf) — 6 páginas de conteúdo + 1 de referências; fonte em [`documentacao/main.tex`](documentacao/main.tex) |
| Diagramas/modelos editáveis | [`modelos-editaveis/`](modelos-editaveis/) (Mermaid `.mmd`) |
| Imagens dos diagramas | [`diagramas/`](diagramas/) (`.png`, uma por `.mmd`) |
| `README.md` | este arquivo |
| `USO_DE_IA.md` | [`USO_DE_IA.md`](USO_DE_IA.md) |

## Conteúdo do PDF

| Seção do PDF | Item do enunciado | Critério de avaliação |
|---|---|---|
| 1. Cenário-problema, motivação e objetivos | cenário-problema, motivação e objetivo | Problema e objetivos (20%) |
| 2. Fronteira do sistema e caracterização do ambiente | fronteira e ambiente | Agentes e ambiente (25%) |
| 3. Requisitos e critérios de aceite | requisitos | Rastreabilidade (20%) |
| 4. Agentes, papéis e responsabilidades | agentes, papéis e responsabilidades | Agentes e ambiente (25%) |
| 5. Objetivos, percepções, ações e estado/conhecimento | objetivos, percepções, ações e estado/conhecimento | Agentes e ambiente (25%) |
| 6. Interações e coordenação | interações e coordenação previstas (protocolos como máquinas de estados, sequências e normas) | Interações e coordenação (25%) |
| 7. Métricas de sucesso e rastreabilidade | métricas/evidências de sucesso | Rastreabilidade (20%) |
| Referências | — | Documentação e autoria (10%) |

## Estrutura da pasta

```
entregas/dsm1/
  README.md            este arquivo
  USO_DE_IA.md         uso de IA no desenvolvimento da entrega
  documentacao/        main.tex e main.pdf (v1 entregue); main-v2.tex e main-v2.pdf (revisão pós-feedback)
  modelos-editaveis/   11 diagramas Mermaid (.mmd)
  diagramas/           11 imagens (.png), uma por .mmd
```

## Rastreabilidade

Os requisitos, papéis, protocolos, normas, testes e métricas do PDF vêm de `models/*.yaml`, com
ID estável. `tools/trace.py --check` valida a cadeia Problema → Requisito → Objetivo →
Papel/Agente → Protocolo/Norma → Componente → Teste → Métrica: 18/18 requisitos com cadeia
completa. Na v1 os 26 testes estavam apenas **especificados**; na v2 são 45, dos quais 33 executados pela suíte da DSM2.

## Diagramas

11 diagramas, cada um com fonte editável e imagem.

| # | Diagrama | Editável | Imagem |
|---|---|---|---|
| 1 | Fronteira do sistema | [`ambiente_fronteira.mmd`](modelos-editaveis/ambiente_fronteira.mmd) | [`ambiente_fronteira.png`](diagramas/ambiente_fronteira.png) |
| 2 | Organização do SMA (Figura 1) | [`roles_organizacao.mmd`](modelos-editaveis/roles_organizacao.mmd) | [`roles_organizacao.png`](diagramas/roles_organizacao.png) |
| 3 | Máquina de estados — Solicitação do usuário (PROT-SOL) | [`protocols_fsm_PROT-SOL.mmd`](modelos-editaveis/protocols_fsm_PROT-SOL.mmd) | [`protocols_fsm_PROT-SOL.png`](diagramas/protocols_fsm_PROT-SOL.png) |
| 4 | Máquina de estados — Delegação de subtarefa (PROT-DEL, Figura 2) | [`protocols_fsm_PROT-DEL.mmd`](modelos-editaveis/protocols_fsm_PROT-DEL.mmd) | [`protocols_fsm_PROT-DEL.png`](diagramas/protocols_fsm_PROT-DEL.png) |
| 5 | Máquina de estados — Consulta entre especialistas (PROT-QRY) | [`protocols_fsm_PROT-QRY.mmd`](modelos-editaveis/protocols_fsm_PROT-QRY.mmd) | [`protocols_fsm_PROT-QRY.png`](diagramas/protocols_fsm_PROT-QRY.png) |
| 6 | Máquina de estados — Verificação de conformidade com veto (PROT-CMP) | [`protocols_fsm_PROT-CMP.mmd`](modelos-editaveis/protocols_fsm_PROT-CMP.mmd) | [`protocols_fsm_PROT-CMP.png`](diagramas/protocols_fsm_PROT-CMP.png) |
| 7 | Máquina de estados — Reserva de período contábil (PROT-LCK) | [`protocols_fsm_PROT-LCK.mmd`](modelos-editaveis/protocols_fsm_PROT-LCK.mmd) | [`protocols_fsm_PROT-LCK.png`](diagramas/protocols_fsm_PROT-LCK.png) |
| 8 | Máquina de estados — Approval Gate (PROT-APR, Figura 2) | [`protocols_fsm_PROT-APR.mmd`](modelos-editaveis/protocols_fsm_PROT-APR.mmd) | [`protocols_fsm_PROT-APR.png`](diagramas/protocols_fsm_PROT-APR.png) |
| 9 | Sequência: fechar o resultado do mês (Figura 3) | [`protocols_sequencia_fechar_mes.mmd`](modelos-editaveis/protocols_sequencia_fechar_mes.mmd) | [`protocols_sequencia_fechar_mes.png`](diagramas/protocols_sequencia_fechar_mes.png) |
| 10 | Sequência: avaliar o orçamento do trimestre | [`protocols_sequencia_avaliar_orcamento.mmd`](modelos-editaveis/protocols_sequencia_avaliar_orcamento.mmd) | [`protocols_sequencia_avaliar_orcamento.png`](diagramas/protocols_sequencia_avaliar_orcamento.png) |
| 11 | Sequência: veto e waiver | [`protocols_sequencia_veto_waiver.mmd`](modelos-editaveis/protocols_sequencia_veto_waiver.mmd) | [`protocols_sequencia_veto_waiver.png`](diagramas/protocols_sequencia_veto_waiver.png) |

## Uso de IA

O desenvolvimento foi apoiado por IA generativa (Claude Opus 5.5) na organização dos arquivos e
da documentação; escopo, decisões de projeto e revisão ficaram com os autores. Detalhes em
[`USO_DE_IA.md`](USO_DE_IA.md).

Documentação navegável e rastreável: <https://fin-dept-multiagents-project.readthedocs.io>.

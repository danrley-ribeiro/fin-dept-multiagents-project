# Sistema Multiagente de Controladoria — Documentação

Sistema Multiagente para a **Controladoria** da **SMA S.A.** (empresa fictícia, de
qualquer porte, com ou sem ERP): o Orquestrador e cinco
agentes especializados (Agente de Custos, Agente de Orçamento, Agente de Resultados,
Agente de Controles Internos e Agente de Relatórios) sobre camadas de comunicação
(A2A/MCP), governança e auditoria, registro de modelos e memória.

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE,
Prof. Rafael Luiz Cancian), modelado segundo AOSE (Gaia, Tropos e Prometheus).

## Linha do tempo das entregas

| Entrega | Conteúdo | Situação |
|---|---|---|
| [DSM1](dsm1/index.md) | Cenário, requisitos e modelagem | <span class="badge-ok">concluída</span> |
| [DSM2](dsm2/index.md) | Arquitetura e protótipo, revisados após o feedback ([o que mudou](dsm2/revisao.md)) | <span class="badge-ok">concluída</span> |
| [DSM3](dsm3/index.md) | Comunicação, coordenação e protótipo funcional (até 18/11) | <span class="badge-pend">em andamento</span> |
| DSM4 | Experimentação, documentação e entrega final (até 02/12) | <span class="badge-pend">pendente</span> |

A documentação cresce **uma entrega por vez**. O que pertence a entregas futuras aparece
somente como *stub* rastreável (`status: pendente`), para que a cadeia fique fechada sem
antecipar decisões de implementação; na DSM2 os itens implementados passam a
`implementado` ou `executado`.

## Como a rastreabilidade funciona

Todo objeto (problema, objetivo, requisito, papel, agente, protocolo, norma, teste,
métrica) tem um **ID estável** definido em `models/*.yaml`. O script `tools/trace.py`
valida a cadeia e gera, a partir da mesma fonte, os objetos desta documentação e as
tabelas do PDF da entrega. Veja [Rastreabilidade](plataforma/rastreabilidade.md).

```{include} _generated/cobertura.md
```

Os treze checkpoints do DSMA e onde está a evidência de cada um: [Checkpoints CP1–CP13](checkpoints.md).

```{toctree}
:caption: Plataforma
:maxdepth: 1

plataforma/rastreabilidade
plataforma/como-contribuir
checkpoints
```

```{toctree}
:caption: DSM1 — Cenário, requisitos e modelagem
:maxdepth: 2

dsm1/index
```

```{toctree}
:caption: DSM2 — Arquitetura e protótipo (revisada)
:maxdepth: 2

dsm2/index
```

```{toctree}
:caption: DSM3 — Comunicação e coordenação (em andamento)
:maxdepth: 2

dsm3/index
```

# SMA de Controladoria — Documentação

Sistema Multiagente para **terceirização (BPO) da Controladoria** de uma empresa:
orquestrador + cinco agentes especializados (Custos e Rentabilidade, Orçamento,
Resultados e Indicadores, Controles Internos e Relatórios Gerenciais) sobre camadas
de comunicação (A2A/MCP), governança e auditoria, configuração de modelos e memória.

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE,
Prof. Rafael Luiz Cancian), modelado segundo AOSE (Gaia, Tropos e Prometheus).

## Linha do tempo das entregas

| Entrega | Conteúdo | Prazo | Situação |
|---|---|---|---|
| [DSM1](dsm1/index.md) | Cenário, requisitos e modelagem | 10/10/2026 | <span class="badge-ok">concluída</span> |
| [DSM2](dsm2/index.md) | Arquitetura e protótipo inicial | 31/10/2026 | <span class="badge-pend">pendente</span> |
| Próximas | Definidas pelo plano da disciplina | — | <span class="badge-pend">a anotar</span> |

A documentação cresce **uma entrega por vez**. O que pertence a entregas futuras aparece
somente como *stub* rastreável (`entrega: DSM2`, `status: pendente`), para que a cadeia
fique fechada desde a DSM1 sem antecipar decisões de implementação.

## Como a rastreabilidade funciona

Todo objeto (problema, objetivo, requisito, papel, agente, protocolo, norma, teste,
métrica) tem um **ID estável** definido em `models/*.yaml`. O script `tools/trace.py`
valida a cadeia e gera, a partir da mesma fonte, os objetos desta documentação e as
tabelas do PDF da entrega. Veja [Rastreabilidade](plataforma/rastreabilidade.md).

```{include} _generated/cobertura.md
```

```{toctree}
:caption: Plataforma
:maxdepth: 1

plataforma/rastreabilidade
plataforma/como-contribuir
plataforma/ADR-001-plataforma-docs
```

```{toctree}
:caption: DSM1 — Cenário, requisitos e modelagem
:maxdepth: 2

dsm1/index
```

```{toctree}
:caption: DSM2 — Arquitetura e protótipo (pendente)
:maxdepth: 2

dsm2/index
```

# Interações, coordenação e normas

## Mecanismos de coordenação

| Dependência (Cap. 3) | Onde aparece | Mecanismo | Protocolo |
|---|---|---|---|
| Tarefa | Orquestrador precisa que especialistas executem subtarefas do DAG | delegação supervisionada (*supervisor/especialistas*) | {need}`PROT-DEL` |
| Informação | Resultados precisa de custos e orçamento consolidados | consulta A2A sem acesso às regras alheias | {need}`PROT-QRY` |
| Autoridade / norma | Publicação depende do parecer de Controles Internos | verificação com **veto** | {need}`PROT-CMP` |
| Recurso exclusivo | Um fechamento por (entidade, competência) | reserva com TTL | {need}`PROT-LCK` |
| Autorização humana | Efeitos externos (ERP, orçamento, publicação) | Approval Gate (HITL) | {need}`PROT-APR` |
| Fronteira com o usuário | Pedido e resposta final | FIPA-Request externo | {need}`PROT-SOL` |

**Por que não Contract Net como mecanismo principal?** Os especialistas são
heterogêneos: para cada subtarefa existe um único papel competente, então não há
disputa a leiloar. O Contract Net fica registrado como evolução possível (DSM2+) para o
caso de **várias instâncias do mesmo papel** (por exemplo, um agente de Custos por
unidade de negócio).

## Cenário âncora — "feche o resultado do mês"

```{mermaid} ../../diagrams/dsm1/sequencia_fechar_mes.mmd
```

## Protocolos (FSMs)

Cada protocolo é especificado como máquina de estados. Transições válidas originam
testes nominais; as **transições inválidas** originam testes negativos (DSM2). Os
diagramas abaixo são gerados de `models/protocols.yaml`.

```{include} ../_generated/protocols.md
```

## Normas e guardrails

O princípio **capacidade ≠ autorização** (Cancian, 2026): nenhuma proposta de agente,
e menos ainda de um LLM, dispara efeito externo sem passar pela `SafetyPolicy`
determinística, que classifica cada ação:

- `ALLOW`: leitura e cálculo internos;
- `REQUIRE_APPROVAL`: lançar ajuste no ERP, alterar orçamento, publicar relatório;
  a ação fica retida no Approval Gate até decisão humana;
- `DENY`: fora da allowlist do papel; bloqueio fail-closed, sem opção de aprovação.

```{include} ../_generated/norms.md
```

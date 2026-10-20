# Interações, coordenação e normas

## Mecanismos de coordenação

| Dependência (Cap. 3) | Onde aparece | Mecanismo | Protocolo |
|---|---|---|---|
| Tarefa | Orquestrador precisa que especialistas executem subtarefas do DAG | delegação supervisionada (*supervisor/especialistas*) | {need}`PROT-DEL` |
| Informação | O Agente de Resultados precisa de custos e orçamento consolidados | consulta A2A sem acesso às regras alheias | {need}`PROT-QRY` |
| Autoridade / norma | A publicação depende do parecer do Agente de Controles Internos | verificação com **veto** | {need}`PROT-CMP` |
| Recurso exclusivo | Um fechamento por (entidade, competência) | reserva com TTL | {need}`PROT-LCK` |
| Autorização humana | Efeitos externos (ERP, orçamento, publicação) | Approval Gate (HITL) | {need}`PROT-APR` |
| Fronteira com o usuário | Pedido e resposta final | FIPA-Request externo | {need}`PROT-SOL` |

**Por que não Contract Net como mecanismo principal?** Os especialistas são
heterogêneos: para cada subtarefa existe um único papel competente, então não há
disputa a leiloar. O Contract Net fica registrado como evolução possível (DSM2+) para o
caso de **várias instâncias do mesmo papel** (por exemplo, um agente de Custos por
unidade de negócio).

## Cenários âncora

### Sequência: fechar o resultado do mês

Figura 3 do PDF (`entregas/dsm1/modelos-editaveis/protocols_sequencia_fechar_mes.mmd`). O Orquestrador
reserva o período, delega em paralelo aos Agentes de Custos e de Orçamento, o Agente de
Resultados consulta os dois, o Agente de Controles Internos verifica (e pode vetar) e o
relatório só é publicado com aprovação humana.

```{mermaid} ../../entregas/dsm1/modelos-editaveis/protocols_sequencia_fechar_mes.mmd
```

### Sequência: veto e waiver

Continuação do bloco de veto acima (`entregas/dsm1/modelos-editaveis/protocols_sequencia_veto_waiver.mmd`),
seguindo a máquina de estados de {need}`PROT-CMP`. Com o resultado vetado, nada é publicado
e a reserva de período continua ativa. Há três saídas: a contabilidade corrige o lançamento e
o Agente de Controles Internos reavalia; o aprovador concede um waiver justificado e o
relatório sai com ressalva; ou o prazo se esgota, a solicitação termina em `failure` e a
reserva é liberada ({need}`REQ-F05`, {need}`NORM-04`, {need}`TEST-08`).

```{mermaid} ../../entregas/dsm1/modelos-editaveis/protocols_sequencia_veto_waiver.mmd
```

### Sequência: avaliar o orçamento do trimestre

Diagrama `entregas/dsm1/modelos-editaveis/protocols_sequencia_avaliar_orcamento.mmd` (citado no texto do PDF). A avaliação
só lê dados, por isso dispensa a reserva de período. Se um desvio passar do limiar, o
Agente de Orçamento pode propor uma correção, que fica retida até o aprovador decidir.

```{mermaid} ../../entregas/dsm1/modelos-editaveis/protocols_sequencia_avaliar_orcamento.mmd
```

## Tratamento de falhas

Se um especialista não responde até o `reply_by` (`EXPIRADA`) ou responde `failure`, o
Orquestrador reenvia a subtarefa uma vez, em nova conversa. Se falhar de novo, ele
interrompe a solicitação: libera a reserva de período, não publica nada e responde
`failure` ao solicitante indicando qual subtarefa falhou ({need}`REQ-F01`, {need}`TEST-26`).

## Máquinas de estados dos protocolos

Cada protocolo é especificado como máquina de estados. Transições válidas originam
testes nominais; as **transições inválidas** originam testes negativos (DSM2). Os
diagramas abaixo são gerados de `models/protocols.yaml` e também ficam salvos em
`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-*.mmd`. A Figura 2 do PDF mostra `PROT-DEL` e `PROT-APR`.

```{include} ../_generated/protocols.md
```

## Normas e guardrails

O princípio **capacidade ≠ autorização** (Cancian, 2026): nenhuma proposta de agente,
e menos ainda de um LLM, dispara efeito externo sem passar pela Política de Segurança
(`SVC-POL`) determinística, que classifica cada ação:

- `ALLOW`: leitura e cálculo internos;
- `REQUIRE_APPROVAL`: lançar ajuste no ERP, alterar orçamento, publicar relatório;
  a ação fica retida no Approval Gate até decisão humana;
- `DENY`: fora da allowlist do papel; bloqueio fail-closed, sem opção de aprovação.

```{include} ../_generated/norms.md
```

# Arquitetura

<span class="badge-pend">em implementação</span>

A arquitetura traduz o modelo da DSM1 (6 agentes, 7 serviços, 6 protocolos) em camadas e
componentes `COMP-*`. Na DSM2 entram apenas os componentes necessários ao protótipo; os
demais serviços ficam para as próximas entregas.

```{mermaid} ../../entregas/dsm2/modelos-editaveis/arquitetura_camadas.mmd
```

## Camadas e justificativas

| Camada | Componentes | Decisão | Requisitos |
|---|---|---|---|
| Orquestração | {need}`COMP-ORQ` | Única fronteira com o usuário; traduz a intenção em DAG e cuida de prazos, reenvio e falha explícita | {need}`REQ-F01` |
| Agentes especialistas | {need}`COMP-CUS`, {need}`COMP-ORC`, {need}`COMP-RES`, {need}`COMP-CIN`, {need}`COMP-REL` | Cada papel decide sob regras próprias; Resultados depende de Custos e Orçamento por query-ref; Controles Internos tem autonomia de veto | {need}`REQ-F02`, {need}`REQ-F03`, {need}`REQ-F04`, {need}`REQ-F05`, {need}`REQ-F06` |
| Comunicação social | {need}`COMP-A2A` | Bus em processo com relógio lógico; as FSMs vêm de `models/protocols.yaml` ({doc}`ADR-003-runtime-python-deterministico`, {doc}`ADR-004-a2a-bus-e-mcp-mock`) | {need}`REQ-F01`, {need}`REQ-NF01` |
| Instrumental | {need}`COMP-MCP` | Mocks de leitura sobre dataset sintético com gabarito | {need}`REQ-F02`, {need}`REQ-NF01` |
| Governança e coordenação | {need}`COMP-AUD`, {need}`COMP-LCK` | Auditoria JSONL central (não por agente) e exclusão mútua do período | {need}`REQ-O01`, {need}`REQ-S02` |

## Estado, conhecimento e memória

Cada agente separa três atributos, conforme `models/agents.yaml`:

- **estado**: o que muda a cada conversa (DAG e prazos no Orquestrador; custos apurados em Custos);
- **conhecimento**: regras e parâmetros fixos (catálogo de intenções, rateio, limiares, regras de alçada e SoD);
- **memória**: reservada; o serviço de memória de longo prazo ({need}`SVC-MEM`) fica para a DSM3.

## Fluxo de dados

1. A solicitação entra por `PROT-SOL`; o Orquestrador responde `agree` ou `not-understood`.
2. O Orquestrador reserva o período (`PROT-LCK`) e delega as subtarefas (`PROT-DEL`) pelo bus.
3. Resultados consulta Custos e Orçamento por `PROT-QRY`; Custos, Orçamento e Controles Internos leem dados pelas tools MCP mock.
4. Controles Internos emite parecer ou veto (`PROT-CMP`); o resultado final é `inform` ou `failure`.
5. Toda mensagem é gravada em JSONL e pode ser reconstruída pelo `conversation_id`.

## Componentes rastreáveis

```{include} ../_generated/components.md
```

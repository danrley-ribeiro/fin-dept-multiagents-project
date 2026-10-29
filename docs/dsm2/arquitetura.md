# Arquitetura

<span class="badge-ok">revisada</span>

A arquitetura traduz o modelo da DSM1 (6 agentes, 7 serviços, 6 protocolos) em camadas e
componentes `COMP-*`. A revisão pós-feedback acrescenta o núcleo BDI comum a AG-ORC e AG-CIN,
a consulta direta entre especialistas, a base normativa por porte, as planilhas de empresas
sem ERP (com servidor MCP de Excel) e a execução ao vivo com dashboard.

```{mermaid} ../../entregas/dsm2/modelos-editaveis/arquitetura_camadas.mmd
```

## Camadas e justificativas

| Camada | Componentes | Decisão | Requisitos |
|---|---|---|---|
| Orquestração | {need}`COMP-ORQ` | Única fronteira com o usuário; traduz a intenção em DAG e cuida de prazos, reenvio e falha explícita | {need}`REQ-F01` |
| Agentes especialistas | {need}`COMP-CUS`, {need}`COMP-ORC`, {need}`COMP-RES`, {need}`COMP-CIN`, {need}`COMP-REL` | Cada papel decide sob regras próprias; Resultados depende de Custos e Orçamento por query-ref; Controles Internos tem autonomia de veto | {need}`REQ-F02`, {need}`REQ-F03`, {need}`REQ-F04`, {need}`REQ-F05`, {need}`REQ-F06` |
| Comunicação social | {need}`COMP-A2A` | Bus em processo com relógio lógico; as FSMs vêm de `models/protocols.yaml` ({doc}`ADR-003-runtime-python-deterministico`, {doc}`ADR-004-a2a-bus-e-mcp-mock`) | {need}`REQ-F01`, {need}`REQ-NF01` |
| Cognição | {need}`COMP-BDI` | Núcleo BDI único para AG-ORC e AG-CIN: crenças auditadas, desejos, planos com utilidade, intenções e reconsideração ({doc}`cognicao`) | {need}`REQ-F03`, {need}`REQ-F05`, {need}`REQ-O01` |
| Instrumental | {need}`COMP-MCP`, {need}`COMP-XLS` | Gateway MCP com allowlist sobre a empresa simulada (por porte) ou a planilha real; servidor MCP de Excel ({doc}`ADR-006-regras-por-porte-e-planilhas`) | {need}`REQ-F02`, {need}`REQ-NF01`, {need}`REQ-S01` |
| Governança e coordenação | {need}`COMP-AUD`, {need}`COMP-LCK` | Auditoria JSONL central (não por agente) e exclusão mútua do período | {need}`REQ-O01`, {need}`REQ-S02` |
| Observabilidade | {need}`COMP-OBS` | Execução ao vivo ritmada + servidor SSE + dashboard do escritório, tudo a partir do trace ({doc}`ADR-005-execucao-ao-vivo-e-dashboard`) | {need}`REQ-O04`, {need}`REQ-O01` |

## Estado, conhecimento e memória

Cada agente separa três atributos, conforme `models/agents.yaml`:

- **estado**: o que muda a cada conversa (DAG e prazos no Orquestrador; custos apurados em Custos);
- **conhecimento**: regras e parâmetros (catálogo de intenções, rateio e, nos agentes BDI, os do porte percebidos por `normas.perfil`);
- **crenças** (AG-ORC e AG-CIN): o que o agente acredita sobre o mundo, revisado por percepção e registrado no trace;
- **memória**: reservada; o serviço de memória de longo prazo ({need}`SVC-MEM`) fica para a DSM3.

## Fluxo de dados

1. A solicitação entra por `PROT-SOL`; o Orquestrador responde `agree` ou `not-understood`.
2. O Orquestrador reserva o período (`PROT-LCK`) e delega as subtarefas (`PROT-DEL`) pelo bus.
3. Resultados consulta Custos e Orçamento por `PROT-QRY`; o AG-ORC consulta o AG-CIN quando precisa explicar um desvio; todos leem dados pelas tools MCP (ERP, planilhas, normas do porte).
4. Controles Internos delibera e emite parecer ou veto (`PROT-CMP`) com correções sugeridas; o humano decide e o AG-CIN reavalia; o resultado final é `inform` ou `failure`.
5. Toda mensagem é gravada em JSONL e pode ser reconstruída pelo `conversation_id`.

## Componentes rastreáveis

```{include} ../_generated/components.md
```

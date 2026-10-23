# ADR-004 — Transporte A2A em processo e servidores MCP mock

- **Status:** aceita (DSM2, 23/10/2026)
- **Requisitos:** {need}`REQ-NF01`, {need}`REQ-F02`, {need}`REQ-F04`, {need}`REQ-O01`
- **Serviços:** {need}`SVC-A2A`, {need}`SVC-MCP`, {need}`SVC-AUD`

## Contexto

A DSM1 separa a comunicação **social** (A2A, agente a agente) da **instrumental** (MCP,
agente a fonte de dados). Na DSM2 não há ERP real nem rede; é preciso demonstrar as
interações e depurá-las com dados controlados.

## Decisão

1. **A2A como bus local em processo** ({need}`COMP-A2A`). O envelope segue o modelo
   `m = ⟨s, r, p, c, o, k⟩` da DSM1 (remetente, destinatário, performativo, conteúdo,
   ontologia `ctrl-fin-v1`, `conversation_id`) mais `reply_by`. Toda mensagem passa pela
   FSM do protocolo correspondente e é gravada pelo serviço de auditoria.
2. **A interface do bus é mínima** (`send`, `register`, `run`) para permitir, em entrega futura, um adaptador do protocolo A2A real sem mudar os agentes.
3. **MCP como mocks in-process** ({need}`COMP-MCP`): funções tipadas de **leitura**
   (balancete, orçado x realizado, lançamentos e aprovadores) sobre um dataset gerado por
   `seed`, com **gabarito** para comparação (tolerância R$ 0,01). Não há ferramenta de escrita nesta entrega.
4. **Dataset sintético em memória** (estruturas Python geradas por `random.Random(seed)`), com anomalias plantadas (alçada, segregação de funções, duplicidade, desvio orçamentário) para os cenários de veto e de depuração.
5. **Auditoria JSONL** ({need}`COMP-AUD`) registra cada mensagem com `conversation_id`,
   permitindo reconstruir a sequência causal depois (`replay`).

## Consequências

- (+) Execução offline, rápida e reprodutível; falhas e anomalias são plantadas deliberadamente.
- (+) Os agentes não conhecem o transporte nem a fonte, então a troca futura é localizada.
- (−) O bus em processo não prova interoperabilidade A2A/MCP reais; é uma limitação declarada.
- (−) Sem escrita no ERP, o fluxo de Approval Gate fica para a DSM3.

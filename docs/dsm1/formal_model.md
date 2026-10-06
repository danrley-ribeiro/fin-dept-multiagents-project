# Modelo formal — objetivos, percepções, ações e estado/conhecimento

## Estado ≠ conhecimento ≠ memória

Seguindo Cancian (2026), três camadas de informação são mantidas separadas:

| Camada | O que é | Exemplo | Onde vive |
|---|---|---|---|
| **Estado interno (crenças)** | situação corrente do agente, muda a cada ciclo | DAG em execução, crenças de conformidade de cada lançamento | dentro do agente |
| **Conhecimento** | regras e referências usadas para decidir, não mudam por ciclo | critérios de rateio, regras de alçada, fórmulas de KPI | configuração versionada / base normativa (RAG) |
| **Memória** | saídas **aprovadas** de ciclos anteriores, reutilizáveis | justificativa aprovada de um desvio de setembro | `SVC-MEM` (embeddings + grafo) |

## Ciclo de cada agente (PEAS / BDI)

Para cada agente $i$: percepção $see_i: S \to P_i$, atualização de estado
$upd_i: B_i \times P_i \to B_i$ e decisão $act_i: B_i \times K_i \to A_i$, em que $K_i$ é o
conhecimento. Em `AG-CIN` o ciclo é BDI explícito: crenças sobre lançamentos →
desejo de conformidade → intenção de **aprovar, apontar ou vetar**.

| Agente | Objetivo | Percepções | Estado (B) | Conhecimento (K) | Ações (A) |
|---|---|---|---|---|---|
| {need}`AG-ORQ` | {need}`G-01` | solicitação, respostas dos especialistas, veto, decisão de aprovação | DAG e status por conversation_id; reserva ativa; prazos | catálogo de intenções e planos; diretório de papéis | delegar, reservar/liberar, pedir conformidade, propor publicação, responder |
| {need}`AG-CUS` | {need}`G-02` | request, query-ref, balancete via MCP | custos do período, versão do rateio, pendências | critérios de rateio, classificação fixo/variável, memória | calcular margens, informar com proveniência, informar falha |
| {need}`AG-ORC` | {need}`G-03` | request, query-ref, orçado e realizado via MCP | desvios, forecast e premissas | limiares, método de forecast, memória | sinalizar desvio, projetar forecast, propor alteração (restrita) |
| {need}`AG-RES` | {need}`G-04` | request, inform de CUS/ORC, índices de mercado | DRE/KPIs em construção, pendências | estrutura da DRE, fórmulas de KPI, memória | query-ref, consolidar, informar |
| {need}`AG-CIN` | {need}`G-05` | request, lançamentos/aprovadores/conciliações, waiver | crenças de conformidade; intenções ativas | regras de alçada, SoD, duplicidade, competência | parecer, **veto**, reavaliar |
| {need}`AG-REL` | {need}`G-06` | request com resultados e parecer; memória | rascunho e versão do template | templates; memória aprovada | gerar por template, narrativa LLM (flag) + validação, propor publicação |

Os detalhes completos de cada agente estão em [Papéis e agentes](roles.md).

## Mensagem e conversação

Toda comunicação entre agentes usa a tupla imutável
$m = \langle s, r, p, c, o, k \rangle$: remetente, destinatário, **performativo**
(FIPA-ACL: `request`, `agree`, `refuse`, `inform`, `failure`, `query-ref`,
`not-understood`), conteúdo, ontologia (`ctrl-fin-v1`) e `conversation_id`. O campo
`reply_by` (relógio lógico) define o prazo da conversa; respostas tardias são
descartadas deterministicamente.

**A2A vs MCP:** A2A é **social** (agente ↔ agente, com semântica de protocolo);
MCP é **instrumental** (agente → fonte de dados, como *tool*). Um agente nunca usa MCP
para "conversar" com outro agente.

## Árvore de objetivos e responsabilidades

```{needflow}
:types: goal, agent
:link_types: refines, pursues
:show_link_names:
:scale: 70
```

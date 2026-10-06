# Fronteira do sistema e caracterização do ambiente

## Fronteira

Pertencem ao **software modelado**: os seis agentes (Orquestrador e cinco especialistas)
e os sete serviços de plataforma (A2A, MCP, Auditoria, Registro de modelos, Memória,
SafetyPolicy/Approval Gate e Reserva de período).

Permanecem no **ambiente**, mesmo quando representados por adapters: usuários humanos
(solicitante, aprovador, auditor), ERP, planilhas de orçamento, base histórica, APIs de
mercado, base normativa e o relógio/calendário de fechamento.

```{mermaid} ../../diagrams/dsm1/fronteira.mmd
```

## Propriedades do ambiente

| Propriedade | Justificativa |
|---|---|
| **Parcialmente observável** | Cada agente só percebe o que seus conectores MCP e mensagens A2A entregam: Custos não enxerga a base normativa; Controles Internos não enxerga as regras de rateio; ninguém tem o estado global instantâneo. |
| **Dinâmico** | Lançamentos, estornos e conciliações continuam chegando durante o fechamento. |
| **Discreto** | Contas, centros de custo, competências e lançamentos têm identificadores e valores bem definidos; tempo por relógio lógico. |
| **Estocástico / com incerteza** | APIs de mercado podem falhar ou atrasar; dados podem chegar incompletos; o tempo de resposta humano é incerto. |
| **Sequencial por ciclo** | Ajustes aprovados e memória de um fechamento afetam o próximo. |
| **Recursos compartilhados** | Período contábil (exclusivo durante o fechamento) e orçamento de tokens (consumível). |

Formalmente (Cancian, 2026): estados do ambiente $S$, percepção $see: S \to P$ distinta
por agente, ações $A$ e transição $next: S \times A \to S$ que também muda por eventos
externos (novos lançamentos), não só pelas ações dos agentes.

## Recursos do ambiente

Classificação por **observabilidade, acionabilidade, exclusividade e autoridade**.
Escrita em qualquer fonte externa é **ação restrita** (ver {need}`NORM-01`).

```{include} ../_generated/environment.md
```

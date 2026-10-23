# Limitações

O que o protótipo da DSM2 **não** garante e por quê.

## Escopo adiado para as próximas entregas

- **LLM**: só existe o modo template (determinístico); a flag, o mock de LLM, a validação numérica do texto, a cota e o log de prompt e de custo não foram implementados (ADR-002).
- **Registro de modelos, memória de longo prazo e Approval Gate** ({need}`COMP-MOD`, {need}`COMP-MEM`, {need}`COMP-POL`): são stubs. A publicação do relatório não passa por aprovação humana; o relatório é entregue na resposta final.
- **Redaction**, versionamento de prompts e regras e dashboard de observabilidade.
- **Métricas** MET-01 a MET-12 e a comparação com a linha de base sequencial não foram medidas; o trace JSONL já registra o necessário para calculá-las.
- **Testes**: 12 dos 26 testes seguem `planejado` (ver {doc}`testes`).

## Simplificações do protótipo

- **Bus em processo**: um único fio e relógio lógico; não há concorrência real, latência de rede nem interoperabilidade com o protocolo A2A real.
- **MCP mock**: somente leitura, sobre dados gerados; não há servidor MCP real nem escrita no ERP.
- **Dados sintéticos**: o gabarito vem do que foi plantado; a linha de base da DSM1 é premissa, não medição.
- **Humanos simulados**: solicitante e aprovador são agentes com roteiro; o aprovador só decide `waiver` ou deixa o prazo esgotar.
- **Correção de lançamento** (`PROT-CMP` `correcao` → reavaliação) não foi implementada; só waiver e prazo esgotado.
- **`avaliar_orcamento`** não passa por AG-RES (o diagrama de sequência da DSM1 inclui o passo); o fluxo é Orçamento → Relatórios.
- **Falhas**: a injeção é por perda de mensagem na entrega; falhas de dado de origem (MCP indisponível) só aparecem como `failure` do especialista.
- **Reenvio** segue a regra da DSM1 (uma vez, em nova conversa); `refuse` de um especialista aborta sem reenvio.
- **`PROT-CMP` não tem `timeout`** no modelo da DSM1: o bus avisa o iniciador quando a contraparte não respondeu, sem alterar a FSM.
- **Competência** e entidade são parâmetros do pedido, mas o dataset é gerado para uma única entidade e competência por execução.

# ADR-002 — IA generativa opcional, por flag, em três agentes

- **Status:** aceita (DSM1, 06/10/2026)
- **Requisitos:** {need}`REQ-F06`, {need}`REQ-S03`, {need}`REQ-C01`, {need}`REQ-O02`, {need}`REQ-O03`, {need}`REQ-NF01`
- **Normas:** {need}`NORM-05`, {need}`NORM-07`

## Contexto

A controladoria exige números exatos, decisões auditáveis e custo previsível. Modelos de
linguagem ajudam a **comunicar** (síntese executiva, narrativa de desvios, comentário
analítico), mas são probabilísticos, custam por token e não podem ser fonte de números
nem de autorização. A disciplina também exige um núcleo executável **offline e sem API
paga**.

## Decisão

| Agente | LLM | Uso permitido |
|---|---|---|
| Relatórios Gerenciais (`AG-REL`) | **flag** (desligada por padrão) | síntese executiva e insights |
| Resultados e Indicadores (`AG-RES`) | **flag** (desligada por padrão) | comentário analítico dos indicadores |
| Orçamento (`AG-ORC`) | **flag** (desligada por padrão) | narrativa explicativa dos desvios |
| Orquestrador, Custos, Controles Internos | **não permitido** | — |

1. Todo agente tem um **modo determinístico completo** (template); a flag apenas acrescenta texto.
2. Números vêm sempre do núcleo determinístico; o texto gerado é validado e, havendo
   divergência, é descartado em favor do template ({need}`NORM-05`).
3. Flag, modelo, limite de tokens e orçamento ficam no **registro central de modelos**
   (`SVC-MOD`), alteráveis em runtime sem redeploy; habilitar LLM em agente não permitido
   é rejeitado na validação ({need}`NORM-07`).
4. Com a flag ligada, cada chamada gera log de prompt e de custo; com ela desligada, o
   custo é zero e não há registro de prompt.

## Consequências

- (+) Reprodutibilidade e custo zero no modo padrão; avaliação independe de fornecedor.
- (+) A IA fica onde agrega valor (comunicação) e longe de onde introduz risco (cálculo, conformidade, orquestração).
- (−) A validação numérica do texto precisa de um extrator robusto (a especificar na DSM2).
- (−) A qualidade da narrativa com a flag ligada depende do modelo escolhido e será medida, não presumida.

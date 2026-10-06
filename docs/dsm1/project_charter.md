# Project charter — cenário, motivação e objetivos

## Cenário-problema

Uma empresa de médio porte terceiriza (BPO) a sua **Controladoria**. Todo mês a equipe
precisa fechar o resultado (balancete → rateios → DRE → indicadores → relatório à
diretoria) e, a cada trimestre, avaliar o orçamento. Hoje esse ciclo:

- leva dias de consolidação manual em planilhas e e-mails;
- não dá visibilidade de margem por produto ou unidade de negócio;
- detecta desvios orçamentários tarde demais;
- deixa passar riscos de conformidade (alçada, segregação de funções, duplicidades);
- produz relatórios inconsistentes com a DRE;
- e, quando usa IA, não deixa trilha de critério, prompt, fontes nem custo.

**Cenários âncora (MVP):** *"feche o resultado do mês"* e *"avalie o orçamento do
trimestre"*, executados sobre uma **empresa sintética** com dados e gabarito
controlados, acessados por **MCP servers mock offline**.

## Motivação

Terceirizar a controladoria exige **escala** (vários clientes e ciclos), **confiança**
(números iguais ao gabarito, conformidade verificada antes de publicar) e
**auditabilidade** (toda decisão reconstruível). Um único script ou um único LLM não
atende às três ao mesmo tempo: o problema tem unidades de decisão distintas, com
informação distribuída, que precisam negociar dependências e respeitar vetos.

## Stakeholders e problemas

```{include} ../_generated/stakeholders.md
```

```{include} ../_generated/problems.md
```

## Objetivos

**Objetivo geral (G-00):** executar as rotinas de controladoria da empresa cliente de
forma terceirizada e coordenada, entregando à liderança o resultado do período e
análises confiáveis, respeitando alçadas, sigilo e aprovação humana, com evidência
reconstruível de cada decisão.

```{needflow}
:types: goal, prob
:show_link_names:
:scale: 70
```

```{include} ../_generated/goals.md
```

## Por que um Sistema Multiagente? (hipótese MAS)

Checklist de adequação (Cancian, 2026, Tab. 5.1), aplicado ao domínio:

| Critério | Evidência no domínio | Favorável? |
|---|---|---|
| Autonomia | Controles Internos decide sozinho **vetar** a publicação; Orçamento decide o que é desvio relevante pelos seus limiares | sim |
| Distribuição | Dados vivem em fontes heterogêneas (ERP, planilhas, base histórica, APIs, normas); nenhum agente vê tudo | sim |
| Interdependência | Resultados **depende** de Custos e Orçamento (dependência de informação); o veto de CI altera as opções do Orquestrador e de Relatórios; o período é recurso exclusivo | sim |
| Heterogeneidade | Cálculo determinístico (CUS), regras BDI (CIN), síntese com LLM opcional (REL) — ciclos cognitivos distintos | sim |
| Recursos | Período contábil (exclusão mútua) e orçamento de tokens (cota consumível) | sim |
| Evidência | Comportamento testável por cenários com gabarito e protocolos com transições inválidas | sim |

**Condição explícita de rejeição do MAS.** Se a demanda se reduzir a gerar um único
relatório por uma sequência fixa de etapas, **sem veto, sem dependência entre unidades
de decisão e sem recurso disputado**, um *workflow* determinístico basta. Esse workflow
sequencial único é adotado como **baseline** para as comparações das entregas seguintes.

**Hipóteses verificáveis (para a experimentação futura):**

- **H1.** Com o veto de Controles Internos, 100% das inconformidades críticas plantadas
  são barradas antes da publicação, contra a baseline sem veto.
- **H2.** A decomposição em agentes mantém acurácia numérica de 100% contra o gabarito,
  com overhead de mensagens mensurável e justificável.
- **H3.** Com a flag LLM desligada, o sistema entrega todos os relatórios sem rede e a
  custo zero; com ela ligada, a consistência numérica do texto permanece em 100%.

## Escopo mínimo viável e riscos

Fora do escopo da DSM1/MVP: integração com ERP real, contabilização fiscal, múltiplas
moedas, dashboard implementado (apenas especificado).

| Risco | Controle previsto | Requisito |
|---|---|---|
| Ação com efeito externo indevida | Approval Gate, DENY fail-closed | {need}`REQ-S01` |
| Fechamentos concorrentes | Reserva de período com TTL | {need}`REQ-S02` |
| LLM inventa número ou "autoriza" ação | Validação numérica + fallback ao template | {need}`REQ-S03` |
| Vazamento de dado sensível em log | Redaction fail-closed | {need}`REQ-P01` |
| Custo de IA descontrolado | Flag desligada por padrão + cota por agente | {need}`REQ-C01` |
| Resultados não reproduzíveis | Offline, seed fixo, versões nos logs | {need}`REQ-NF01` |

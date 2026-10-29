# Arquitetura cognitiva (BDI) de AG-ORC e AG-CIN

Resposta ao feedback da DSM2: o projeto passa a ter **dois agentes cognitivos** com um ciclo
BDI explícito e observável: {need}`AG-ORC` (Orçamento) e {need}`AG-CIN` (Controles Internos).
Os demais seguem com outra natureza, declarada: o Orquestrador é **reativo a protocolos**
(roteia, não decide conformidade nem desvio); Custos, Resultados e Relatórios são
**deliberativos determinísticos** (regras fixas, sem desejos concorrentes).

O núcleo está em `src/fin_mas/core/bdi.py` ({need}`COMP-BDI`) e é o mesmo para os dois agentes.

## Ciclo

```{mermaid} ../../entregas/dsm2/modelos-editaveis/ciclo_bdi.mmd
```

| Etapa | No código | Registro no trace |
|---|---|---|
| Percepção | mensagens do bus, respostas MCP, timeouts, `normas.perfil` | `mcp_call`, `deliver`, `timeout` |
| Revisão de crenças | `Crencas.revisar(chave, valor, fonte)`: grava só quando o valor muda | `belief` (antes, depois, fonte) |
| Reconsideração | `_reconsiderar()`: o desejo ainda vale? o contexto do plano ainda vale? | `intention` (abandonada / falhou / reconsiderada + motivo) |
| Geração de opções | `opcoes()`: desejos derivados das crenças, com prioridade | `desire` (gerado / satisfeito / descartado + motivo) |
| Deliberação e seleção de plano | `_selecionar_e_executar()`: plano aplicável de maior utilidade | `deliberation` (todas as opções, aplicabilidade, motivo e utilidade) |
| Execução | corpo do plano; pode suspender aguardando uma conversa ou outro desejo | `intention` (adotada, suspensa, retomada, concluída) |

**Utilidade de um plano** = 10 × soma dos pesos dos desejos permanentes que ele atende + preferência.
Os pesos vêm do **porte da empresa** ({doc}`portes`): uma micro valoriza mais o prazo; uma grande, a conformidade.

**Política de compromisso.** Compromisso aberto (Rao & Georgeff): a intenção é mantida enquanto o desejo
continuar desejável e o contexto do plano continuar verdadeiro. A reconsideração é **disparada por eventos
relevantes** (crença revisada, falha ou timeout do plano, desejo satisfeito) e não a cada tick. É o
equilíbrio entre agente cauteloso e ousado descrito por Kinny & Georgeff: reconsiderar sempre custa
deliberação; nunca reconsiderar insiste em planos sem sentido.

## AG-ORC — Orçamento

| Elemento | Conteúdo |
|---|---|
| Crenças | orçado e realizado por conta em duas fontes (planilha e ERP), fonte adotada, desvio bruto e ajustado, valores contestados pelo AG-CIN, classificação; porte e se a empresa tem ERP |
| Desejos permanentes | `precisao`, `tempestividade` (pesos por porte) |
| Desejos gerados | `fonte_confiavel(conta)` p1 · `explicar_desvio(conta)` p2 · `alertar_desvio(conta)` p3 · `encaminhar_controle(conta)` p3 · `projetar_forecast` p4 · `avaliar_execucao` p5 |
| Planos | `P-ADOTAR-ERP` / `P-MANTER-PLANILHA` · `P-CONSULTAR-CIN` / `P-SEM-EXPLICACAO` · `P-SINALIZAR` · `P-ENCAMINHAR-CONTROLE` · `P-FORECAST-AJUSTADO` / `P-RUN-RATE` · `P-CONSOLIDAR` |
| Reconsideração | a resposta do AG-CIN revisa `contestado[conta]`; se o desvio ajustado ficar abaixo do limiar, `alertar_desvio` deixa de valer, a intenção `P-SINALIZAR` é **abandonada** e nasce `encaminhar_controle` |
| Replanejamento | timeout ou refuse da consulta → `P-CONSULTAR-CIN` falha → `P-SEM-EXPLICACAO` (marcado "já tentado sem sucesso" na deliberação) |
| Empresa sem ERP | `erp.realizado_por_conta` é indisponível: a crença do realizado vem só da planilha e o desejo `fonte_confiavel` nunca nasce |

Trecho real do trace (`python -m fin_mas run --scenario desvio_irregular`):

```text
DELIBERA AG-ORC: explicar_desvio:2026-09|C-3002 Marketing -> P-CONSULTAR-CIN [P-CONSULTAR-CIN u=30; P-SEM-EXPLICACAO u=10]
INTENCAO AG-ORC: AG-ORC-I002 P-SINALIZAR suspensa (só sinaliza depois de tentar explicar o desvio)
CRENCA AG-ORC: contestado[C-3002 Marketing]@2026-09 = ... (fonte: AG-CIN (QRY-001))
INTENCAO AG-ORC: AG-ORC-I002 P-SINALIZAR abandonada (reconsiderada: desvio ajustado ... abaixo do limiar ...)
DESEJO AG-ORC: encaminhar_controle:2026-09|C-3002 Marketing gerado
```

## AG-CIN — Controles Internos

| Elemento | Conteúdo |
|---|---|
| Crenças | por lançamento: conta, valor, criador, violações e evidências; correções percebidas, waivers, ciclos de correção; porte e versão das normas |
| Desejos permanentes concorrentes | `conformidade` e `prazo` (pesos por porte; conformidade sempre maior) |
| Desejo gerado | `parecer(CMP)` ao receber a verificação |
| Planos e seleção | `P-APROVAR` e `P-APONTAR` (conformidade + prazo), `P-VETAR-COM-CORRECAO` (conformidade + prazo; só se todas as críticas forem corrigíveis e houver ciclo de correção disponível), `P-VETAR` (só conformidade). Com críticas corrigíveis, os dois vetos se aplicam e o que preserva o prazo vence por utilidade |
| Reconsideração | `correcao` → nova percepção via MCP → a intenção de vetar é reconsiderada: sem críticas, troca por aprovar/apontar; com críticas restantes, mantém o compromisso de vetar (agora `P-VETAR`); `waiver_humano` → intenção abandonada, crença de violação mantida; `prazo_esgotado` → intenção concluída com bloqueio |
| Corrigibilidade | alçada e SoD → reaprovar por quem tem alçada (na micro, o próprio sócio, sob controle compensatório); duplicidade → estornar; competência → reclassificar |

## Observar a mente dos agentes

- CLI: `python -m fin_mas run --scenario veto_correcao` imprime `CRENCA`, `DESEJO`, `DELIBERA` e `INTENCAO` na trilha.
- Dashboard: clique no agente; as abas *Intenções*, *Deliberações*, *Crenças*, *Desejos*, *Decisões* e *Planos*
  mostram o mesmo trace com badges de novidade ({doc}`dashboard`).
- Testes: TEST-27 a TEST-31 e TEST-36 verificam o comportamento pelo trace de cenários completos.

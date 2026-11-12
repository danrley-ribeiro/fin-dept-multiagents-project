# Uso de IA — DSM3

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de IA generativa na produção da DSM3. O uso de IA **no produto** (LLM opcional
do AG-REL, desligado por padrão) está em [`docs/dsm3/llm.md`](../../docs/dsm3/llm.md) e segue a
[ADR-002](../../docs/dsm1/ADR-002-llm-opcional-por-flag.md). Os testes usam apenas provedores
mock e offline.

## Ferramentas e período

| Fase | Modelo | Ferramenta | Período |
|---|---|---|---|
| Correções do feedback da DSM2 e funcionalidades da DSM3 | Claude Opus 5.5 | Claude Code (extensão VS Code) | 10/11/2026 |

## O que a IA produziu

A partir do enunciado da DSM3 e do feedback do professor, colados pelos autores:

| Atividade | Artefatos |
|---|---|
| Diagnóstico das falhas relatadas no código (canal livre, `advance` sem autorização, destinatário não conferido, conteúdo sem esquema) | — |
| Barramento com autenticação, papéis, contraparte, esquemas, integridade e isolamento de erros | `core/bus.py`, `core/schema.py`, `core/diretorio.py`, `core/agent.py`, `models/protocols.yaml` |
| Approval Gate (PROT-APR) e política SVC-POL; correção no ERP protegida | `services/politica.py`, `agents/orq.py`, `mcp/gateway.py`, `env/scenarios.py` |
| Memória persistente, redaction, trace com hash encadeado | `services/memoria.py`, `services/redacao.py`, `services/audit.py`, `agents/cin.py` |
| LLM opcional (SVC-MOD) com mocks offline | `services/modelos.py`, `agents/rel.py` |
| Cenários `ataque_decisao_forjada` e `reincidencia_waiver`; CLI `verificar`, `--memoria`, `--llm` | `env/ataques.py`, `cli.py` |
| Testes adversariais e de memória, LLM e Approval Gate; ajuste dos testes antigos que injetavam mensagens sem credencial | `tests/` |
| Modelos de rastreabilidade (REQ-S04, NORM-09/10, MET-15/16, TEST-46..71, componentes) | `models/` |
| Dashboard adaptado ao PROT-APR | `web/src/state/reducer.ts`, `web/src/App.tsx`, `web/src/components/DecisaoHumana.tsx` |
| Documentação da DSM3 e desta entrega | `docs/dsm3/`, `entregas/dsm3/` |
| Correção dos 7 achados da revisão do PR feita pelo Danrley, seguindo as sugestões dele, e 15 testes de regressão | `env/scenarios.py`, `live.py`, `cli.py`, `services/redacao.py`, `services/modelos.py`, `services/memoria.py`, `agents/cin.py`, `tests/e2e/test_revisao_pr.py` |

## Decisões que ficaram com os autores

- Priorizar as falhas de autorização e validação, como recomendou o feedback, e concluir os
  itens previstos (memória, Approval Gate, proteção de informações, LLM opcional).
- Manter o núcleo determinístico e offline. O provedor real de LLM fica opcional e fora dos testes.
- Não adotar o Contract Net nesta entrega (um especialista por capacidade) e deixar a
  comparação com um workflow funcionalmente equivalente para a DSM4.
- Domínio, agentes, protocolos e normas de base: definidos pelos autores na DSM1 e na DSM2.

## Verificação

- `python -m pytest`: 247 testes passam, offline (157 na DSM2).
- `python tools/trace.py --check`: 0 erros; 89 de 90 testes modelados executados (TEST-19 é de
  entrega futura).
- `python -m fin_mas run --scenario ataque_decisao_forjada`: 14 ataques, nenhum aceito.
- `python -m fin_mas comparar --seeds 10`: a qualidade é idêntica à da DSM2; o custo do Approval
  Gate aparece em `docs/dsm3/coordenacao.md`.
- Dashboard, executado pelos autores (o ambiente da IA não tinha Node nem bun): `bun run test`
  com 3 de 3 testes do reducer passando, e `npx playwright test` com 14 de 14 testes de uso real
  passando (com `PW_CHANNEL=chromium`, porque a máquina não tem o Google Chrome instalado).
- Todo código e texto gerado foi revisado pelos autores antes da entrega.

## Correção simulada por avaliador independente

Antes do envio, pedimos a um segundo agente de IA (Claude Opus 5.5, sem acesso ao nosso
raciocínio) que corrigisse a entrega como o professor corrigiu a DSM2. Ele executou a suíte e
os cenários, reproduziu o experimento e escreveu ataques próprios. A nota é só uma estimativa
dessa simulação, não uma avaliação oficial.

| Rodada | Comunicação (25%) | Coordenação (25%) | Robustez (25%) | Testes (15%) | Documentação (10%) | Final |
|---|---|---|---|---|---|---|
| 1ª (antes das correções) | 8,0 | 7,5 | 6,0 | 7,5 | 8,0 | **7,3** |
| 2ª (após a primeira leva de correções) | 8,5 | 8,0 | 7,5 | 8,0 | 8,5 | **8,1** |
| 3ª (versão entregue) | 8,5 | 8,0 | 8,0 | 8,0 | 8,5 | **8,2** |

- **Corrigido entre as rodadas** (detalhes em [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md)):
  - gateway MCP sem autenticação;
  - pedidos que ficavam sem resposta;
  - dois fechamentos do mesmo mês durante a espera pelo aprovador;
  - memória com identidade declarada e nomes de pessoas no arquivo;
  - trace sem detecção de corte ou de cadeia recalculada;
  - comandos que derrubavam o dashboard;
  - teste instável.
- **O que o avaliador apontou na 2ª rodada, e foi corrigido depois dela**
  (detalhes em [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md)):
  - **Memória persistente:** a assinatura é por entrada e a chave fica ao lado do arquivo. Por isso, apagar uma entrada ou corromper o arquivo libera um novo waiver sem aviso, e quem lê a chave consegue forjar uma reincidência. Os ids podem se repetir depois que uma entrada é descartada.
  - **Aprovação no último tick:** uma aprovação enviada no último tick do prazo pode expirar antes de ser entregue.
  - **Servidor do dashboard:** o corpo do POST é lido antes da autenticação, e um token com caractere não-ASCII gera exceção.
  - **Redaction:** não reconhece CPF ou CNPJ sem máscara em texto livre.
  - **Verificação do trace:** em outra máquina, sem a mesma chave, o trace acusa adulteração que não houve.
- **3ª rodada:** o avaliador reexecutou todos os ataques e confirmou os itens acima corrigidos, sem
  regressão nos 17 cenários. Ele também reproduziu a âncora do trace em outra configuração de chave.
  Apontou novos pontos, ainda não corrigidos na versão entregue:
  - **Moderado:** uma cópia íntegra da memória em outra pasta ou máquina é tratada como comprometida e
    suspende o waiver até para violações novas, sem comando de restauração.
  - **Menor:** duas execuções simultâneas sobre o mesmo arquivo de memória perdem entradas sem detecção.
  - **Menor:** a checagem do prazo da aprovação supõe entrega em um tick.
  - **Menor:** o padrão de CPF/CNPJ sem máscara também redige números legítimos de 11 ou 14 dígitos.
  - **Menor:** `verificar --ancora` sobre um trace sem cadeia devolve código 1, não 3.
- **Depois da 3ª rodada:** a correção da redação feita na revisão do PR (abaixo) também resolve a parte
  do ponto menor sobre CPF/CNPJ que atingia hashes; números legítimos soltos de 11 ou 14 dígitos
  continuam sendo redigidos.
- **Ainda não corrigido:** a variância zero entre as seeds e o baseline sem as mesmas funções. Isso
  exige redesenhar o experimento, trabalho da DSM4, e está registrado em
  [`docs/dsm3/limitacoes.md`](../../docs/dsm3/limitacoes.md). Segundo o avaliador, é o que mais
  impede uma nota maior.

## Revisão humana do PR pelo coautor

O Danrley revisou o pull request da DSM3: reproduziu cada problema com um script sobre o
código e sugeriu a correção. Ele apontou 7 pontos e descartou outros 3 depois
de verificá-los. A IA aplicou as correções seguindo as sugestões dele e escreveu um teste de
regressão por achado (detalhes em [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md)):

| Achado | Gravidade | Correção |
|---|---|---|
| Decisão humana recusada pela política tirava a pendência e impedia nova decisão | bug | a pendência só sai depois de a decisão ser aceita |
| Waiver sem justificativa passava com um texto padrão atribuído ao aprovador | bug sério | no dashboard, o waiver exige o texto do humano |
| `replay` não lia trace de outra máquina | bug | `replay --ancora` |
| Redação de CPF/CNPJ alterava cerca de 5,5% dos hashes no trace | bug | fronteira sem letras nem dígitos |
| NORM-05 aceitava número com a escala errada | bug | comparação pelo valor (pt-BR) |
| Pseudônimo da memória reversível por dicionário | segurança | HMAC com a chave da memória |
| Regra de competência duplicada e divergente | detalhe | uma regra só, em `core/schema.py` |

Verificação depois das correções: 247 testes passando; `trace.py --check` sem erros; cenário
adversarial com 14 de 14 ataques rejeitados e a mesma âncora; comparação em 10 seeds com as
mesmas métricas (só os hashes de cada execução mudaram, porque o trace não guarda mais o
pseudônimo). Os testes do dashboard (`bun run test` e Playwright) não rodaram no ambiente da IA,
que não tem Node; o código do dashboard (`web/`) não foi alterado nesta rodada.

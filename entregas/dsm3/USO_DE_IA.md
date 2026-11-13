# Uso de IA — DSM3

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de IA generativa na produção da DSM3. O uso de IA **no produto** (LLM opcional
no AG-REL, AG-ORC e AG-RES, desligado por padrão) está em [`docs/dsm3/llm.md`](../../docs/dsm3/llm.md)
e segue a [ADR-002](../../docs/dsm1/ADR-002-llm-opcional-por-flag.md) e a
[ADR-008](../../docs/dsm3/ADR-008-cognicao-local-e-llm.md). Os testes usam apenas provedores mock e
servidores falsos em loopback, offline.

## Ferramentas e período

| Fase | Modelo | Ferramenta | Período |
|---|---|---|---|
| Correções do feedback da DSM2 e funcionalidades da DSM3 | Claude Opus 5.5 | Claude Code (extensão VS Code) | 10/11/2026 |
| Versão 0.5.0 (cognição, acesso, negociação, dashboard, TUI, implantação) | Claude Opus 5.5 | Claude Code, com agentes em paralelo | 12/11/2026 |

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
| Botão de waiver com a regra da POL-04 | `web/src/state/justificativa.ts`, `web/src/components/DecisaoHumana.tsx`, `web/e2e/escritorio.spec.ts` |

## Decisões que ficaram com os autores

- Priorizar as falhas de autorização e validação, como recomendou o feedback, e concluir os
  itens previstos (memória, Approval Gate, proteção de informações, LLM opcional).
- Manter o núcleo determinístico e offline. O provedor real de LLM fica opcional e fora dos testes.
- Não adotar o Contract Net nesta entrega (um especialista por capacidade) e deixar a
  comparação com um workflow funcionalmente equivalente para a DSM4.
- Domínio, agentes, protocolos e normas de base: definidos pelos autores na DSM1 e na DSM2.

## Verificação (entrega inicial, 10/11/2026; números atuais na seção da v0.5.0)

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
- **Na v0.5.0:** dois desses pontos menores foram corrigidos: a checagem do prazo da aprovação usa
  o instante previsto de entrega (`test_deadline_check_uses_the_real_delivery_time_of_the_decision`)
  e `verificar --ancora` sobre trace sem cadeia devolve 3
  (`test_verify_with_anchor_on_unchained_trace_returns_three`). Os números soltos de 11 ou 14 dígitos
  continuam redigidos por decisão (falha fechada); a cópia da memória em outra pasta e as duas
  execuções simultâneas sobre o mesmo arquivo de memória ficam para a DSM4.
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
pseudônimo).

Depois da revisão, também a pedido dos autores, o botão de waiver do dashboard passou a usar a
mesma regra da POL-04 (10 caracteres e duas palavras diferentes): `aaaaaaaaaa` não habilita mais o
botão. Desta vez o ambiente tinha Node e bun, e a IA rodou os testes do dashboard: `bun run test`
com 12 de 12 (3 do reducer e 9 da regra da justificativa) e `bun run test:e2e` com 14 de 14 testes
de uso real no Chromium, incluindo o caso `aaaaaaaaaa`.

## Etapa v0.5.0 (12/11/2026)

Depois da tag `dsm3-base`, os autores planejaram com a IA o que faltava para concluir a DSM3 e a
IA implementou, em commits locais.

### O que a IA fez

| Atividade | Artefatos |
|---|---|
| Planejamento com os autores: divisão da etapa em partes independentes (cognição, LLM, negociação, acesso, servidor e dashboard, CLI, TUI, implantação, documentação) e ordem dos commits | — |
| Cognição assistida: proposta, validação, hipótese, ação epistêmica; motor local; proponente LLM; planos do AG-ORC; bancada | `core/inferencia.py`, `core/bdi.py`, `cognicao/`, `agents/orc.py`, `env/scenarios.py` |
| LLM multiprovedor, usos por agente, consentimento, pseudônimos, disjuntor, conferência por rótulo | `services/modelos.py`, `services/provedores.py`, `services/pseudonimos.py`, `agents/res.py`, `agents/rel.py`, `.env.example` |
| Negociação de prazo no PROT-DEL | `models/protocols.yaml`, `core/bus.py`, `agents/orq.py` |
| Identidade e acesso: SVC-IAM, arquivo selado, trilha, permissões, POL-09 e POL-13, ataques de acesso | `services/iam.py`, `services/selado.py`, `services/trilha.py`, `core/permissoes.py`, `models/permissions.yaml`, `services/politica.py`, `env/ataques_acesso.py` |
| Servidor e dashboard com login, CSRF, permissões, áreas de trabalho e hipóteses na mente do agente | `server.py`, `live.py`, `web/src/` |
| CLI de acesso, auditoria, explicação, sequência, invariantes, catálogo de cenários, implantação | `cli.py`, `cli_acesso.py`, `invariantes.py`, `services/consulta.py`, `services/explicacao.py`, `implantacao.py` |
| Console de administração no terminal, feito por um agente em paralelo | `tui/` |
| Testes: e2e, integração (servidor real, CLI em subprocesso, servidor falso de LLM), TUI pelo Pilot do Textual e roteiros Playwright; nenhum unitário novo | `tests/e2e/`, `tests/integration/`, `tests/tui/`, `tests/fakes/`, `web/e2e/` |
| Modelos de rastreabilidade (REQ-S05, REQ-F08, NORM-11..13, SVC-IAM, componentes, MET-17/18, TEST-19 e TEST-91..140) | `models/` |
| Diagramas da etapa, feitos por um agente em paralelo | `entregas/dsm3/modelos-editaveis/`, `entregas/dsm3/diagramas/`, `tools/diagramas.mjs` |
| Documentação desta etapa, feita por um agente em paralelo | `docs/dsm3/`, `README.md`, `CHANGELOG.md`, esta pasta |
| Revisão: números da documentação conferidos rodando os comandos | — |

### Decisões que ficaram com os autores

- Dividir as entregas: o que fecha a DSM3 (acesso por pessoa, cognição, negociação, implantação)
  entra agora; experimento redesenhado, 2FA, delegação, dupla aprovação e cofre ficam para a DSM4.
- TUI para administração (contas, papéis, sessões, trilha) e web para uso (operar, pedir, decidir,
  auditar).
- LLM como **proponente**, nunca fonte de crença: a saída do modelo passa por validação e precisa
  de evidência determinística; AG-ORQ, AG-CUS e AG-CIN continuam sem LLM.
- Só commits locais, revisados antes de publicar.
- Sem testes unitários novos: cobertura por e2e, integração e interface.

### Correção simulada desta etapa (4ª rodada, 12 e 13/11/2026)

- **Quem avaliou:** um agente de IA sem acesso ao plano nem à conversa de desenvolvimento, só com
  leitura do repositório, o enunciado e a rubrica; escreveu e rodou testes adversariais próprios.
- **Nota dada ao estado avaliado:** 7,2 (comunicação 7,5; coordenação 7,5; corretude 6,5; testes
  7,0; documentação 7,5, esta com baixa confiança porque os documentos estavam em reescrita).
- **Achados:** 2 críticos, 10 moderados e 8 menores. Foram corrigidos os 2 críticos, 7 moderados
  e 2 menores, cada um com teste novo (TEST-141 a 153); a tabela está em
  [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md).
- **Não corrigido:** o que está em "Achados da correção simulada da v0.5.0 que continuam", em
  [`docs/dsm3/limitacoes.md`](../../docs/dsm3/limitacoes.md).
- **Sem reavaliação:** o avaliador não reexaminou o sistema depois das correções; a nota acima é
  a do estado anterior a elas.
- **O que não foi coberto pelo avaliador:** Playwright, TUI, provedores reais de LLM, upload de
  planilha maliciosa, Windows e a auditoria da qualidade dos testes, que ele delegou e não recebeu.

### Verificação (13/11/2026)

- `python -m pytest`: 431 testes passam, offline (249 na tag `dsm3-base`).
- `python tools/trace.py --check`: 312 objetos, 21 requisitos, 153 de 153 testes modelados executados, 0 erros.
- `python -m fin_mas cenarios --verificar`: 37 de 37 cenários em ordem.
- `python -m fin_mas run --scenario ataque_acesso`: 15 de 15 ataques recusados;
  `ataque_decisao_forjada`: 14 de 14, âncora `2586f2c81fc2cc1c1739c12be744fce07eb2619044a5c337d2c6e1666becc76e`.
- Os 17 cenários revisados, no nível básico, mantêm as métricas da tag `dsm3-base` em 10 seeds.
- Dashboard: 12 testes vitest e 29 roteiros Playwright no Chrome (14 do escritório, 9 de acesso, 6 das áreas de trabalho).

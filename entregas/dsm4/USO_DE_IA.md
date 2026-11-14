# Uso de IA — DSM4

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de IA generativa na produção da DSM4. O uso de IA **no produto** (LLM opcional, desligado
por padrão, só como proponente de hipóteses e redator de textos rotulados, e nunca no Orquestrador, no AG-CUS
nem no AG-CIN) está em [`docs/dsm3/llm.md`](../../docs/dsm3/llm.md), no
[ADR-008](../../docs/dsm3/ADR-008-cognicao-local-e-llm.md), no
[ADR-010](../../docs/dsm4/ADR-010-especialistas-bdi.md) e, para o entendimento de fontes, no ADR-011. O
experimento não usa LLM em nenhum braço. Os testes usam só provedores mock e servidores falsos em loopback,
offline.

## Ferramentas e período

| Fase | Modelo | Ferramenta | Período |
|---|---|---|---|
| Planejamento da DSM4 com os autores | Claude Opus 5.5 | Claude Code | novembro de 2026 |
| Implementação dos lotes, em paralelo, por agentes de IA em cópias isoladas do repositório | Claude Opus 5.5 | Claude Code, agentes em *worktrees* do git | novembro de 2026 |
| Integração, verificação e documentação de fechamento | Claude Opus 5.5 | Claude Code | novembro de 2026 |

## O que a IA fez

| Atividade | Artefatos |
|---|---|
| Planejamento com os autores: divisão da DSM4 em lotes independentes, ordem de integração e o que cada lote não podia tocar | — |
| **Especialistas BDI** (um agente): variantes BDI de AG-RES, AG-CUS e AG-REL, aprendizado local auditável, estratégias de compromisso, leitura da memória por tipo, base normativa com busca lexical, ADR-010 e cenários | `agents/*_bdi.py`, `services/aprendizado.py`, `conhecimento/`, `models/cognicao.yaml`, `models/conhecimento.yaml`, `docs/dsm4/cognicao.md`, `docs/dsm4/ADR-010-especialistas-bdi.md` |
| **Experimento** (um agente): pré-registro escrito antes do código, modelo de falhas por seed, workflow funcionalmente equivalente, biblioteca estatística só com a biblioteca padrão, estudo em quatro blocos, comando `fin-mas experimento`, análise das três rodadas | `docs/dsm4/experimento.md`, `caos.py`, `baseline_eq.py`, `estatistica.py`, `estudo.py`, `estudo_relato.py`, `docs/dsm4/resultados/`, `docs/dsm4/resultados.md` |
| **Implantação e portes** (um agente): pacote instalável, contêiner, backup, restauração e migração; MEI, Média empresa II e segmentos, com as fontes legais consultadas | `implantacao.py`, `manutencao.py`, `Dockerfile`, `compose.yaml`, `docker/`, `tools/empacotar_wheel.py`, `models/portes.yaml`, `models/segmentos.yaml`, `docs/dsm4/implantacao.md`, `docs/dsm4/portes-e-segmentos.md` |
| **Conectores** (um agente): interface `Conector`, REST genérico, cliente MCP, ERP de demonstração, entendimento determinístico de fontes, cofre de credenciais da fonte, aba Fontes | `conectores/`, `fontes/entendimento.py`, `docs/dsm4/ADR-011-conectores-e-entendimento.md` |
| **Acesso avançado** (um agente): segundo fator, alçada por pessoa, delegação, dupla aprovação, escalonamento, cofre, memória sobre o arquivo selado, várias empresas, TUI | `services/acesso_avancado.py`, `services/cofre.py`, `docs/dsm4/acesso-avancado.md`, `docs/dsm4/ADR-012-acesso-avancado.md` |
| **Este relatório e o fechamento** (um agente): gerador dos números do relatório a partir das fontes, relatório técnico em LaTeX, diagramas da entrega, páginas de arquitetura final, limitações, demonstração, reprodução e catálogo de cenários, apresentação, empacotador | `tools/relatorio_numeros.py`, `tools/empacotar_dsm4.py`, `entregas/dsm4/`, `docs/dsm4/{arquitetura-final,limitacoes,demonstracao,reproducao,cenarios-de-teste}.md`, `docs/checkpoints.md` |
| Testes de todos os lotes: e2e, integração e interface (TUI pelo Pilot); nenhum unitário novo | `tests/e2e/`, `tests/integration/`, `tests/tui/` |
| Integração dos lotes numa versão e verificação: suíte, rastreabilidade, cenários, experimento regenerado sobre o código integrado, documentação | merges na branch da DSM4 |
| Correção simulada da DSM4 (um agente avaliador, sem o plano) e correção dos achados (agentes), com um teste por achado; terceira rodada do experimento na versão 1.0.0 e esta análise atualizada | `core/bus.py`, `caos.py`, `estudo.py`, serviços de acesso, fontes e manutenção, TEST-420 a TEST-449, `docs/dsm4/resultados.md`, `docs/dsm4/limitacoes.md` |

## Decisões que ficaram com os autores

- **Divisão das entregas**: o que entra na DSM4 e em que ordem; o que fica como limitação declarada.
- **TUI para administração e web para uso**, mantida da DSM3 para as funções novas de acesso.
- **LLM só como proponente**: a saída de modelo é proposta validada por regras determinísticas e precisa de
  evidência; nunca fonte de crença, nunca decisão; fora do experimento.
- **Conectores genéricos, sem fornecedor** (nenhum conector SAP, TOTVS etc.).
- **Entendimento de fontes sem IA generativa**: determinístico, com confirmação humana do mapeamento; o LLM
  só sugere, se ligado.
- **Sem testes unitários novos**: cobertura por e2e, integração e interface.
- **Só commits locais**, revisados antes de publicar.
- **Demonstração guiada como opção** (roteiro com comandos exatos e plano B), além do dashboard ao vivo.
- Domínio, agentes, protocolos, normas de base e as perguntas que o experimento devia responder: definidos
  pelos autores nas entregas anteriores e no planejamento desta.

## Correção simulada e verificação

### Correção simulada da v0.5.0 (registrada na DSM3)

- **Quem avaliou:** um agente de IA sem acesso ao plano nem à conversa de desenvolvimento, só com o
  repositório, o enunciado e a rubrica.
- **Nota dada ao estado avaliado:** 7,2, **antes das correções**; **sem reavaliação** depois delas.
- Os achados corrigidos e os que continuam estão em [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md) e
  [`docs/dsm3/limitacoes.md`](../../docs/dsm3/limitacoes.md); os que seguem valendo na versão final estão em
  [`docs/dsm4/limitacoes.md`](../../docs/dsm4/limitacoes.md).

### Defeito achado pelo próprio experimento

A primeira rodada do experimento, sobre a v0.5.0 como estava, mostrou execuções sem resposta explícita sob
perda de mensagens (violação do INV-07): a resposta final de um especialista, perdida na entrega, não
avisava ninguém. O defeito tinha sido previsto pela leitura do código no pré-registro só para o PROT-CMP;
estava também no PROT-DEL. Foi corrigido e o experimento rodou de novo; depois da correção simulada da DSM4
rodou uma terceira vez. As três rodadas estão relatadas lado a lado e nenhuma posterior à primeira é tratada
como confirmatória ([`docs/dsm4/resultados.md`](../../docs/dsm4/resultados.md), "Três rodadas" e "Desvios do
pré-registro").

### Correção simulada da DSM4

- **Quem avaliou:** um agente de IA independente, sem acesso ao plano nem à conversa de desenvolvimento, só
  com o repositório, o enunciado e a rubrica, como na correção simulada da DSM3.
- **Nota dada ao estado avaliado: 7,2**, dada ao estado **anterior às correções**. Por critério: sistema
  6,5; arquitetura 7,5; experimentação 8,0; testes 7,5; documentação 7,5; demonstração e autoria 6,5.
- **Não houve reavaliação** depois das correções. A nota vale para o que foi avaliado, não para a versão
  entregue, e não se sabe qual seria a nota desta.
- **Achados:** 5 críticos, 10 moderados e 7 menores. Todos os críticos e quase todos os demais foram
  corrigidos, cada um com teste (TEST-420 a TEST-449 em `models/tests.yaml`).

| Achado | O que era | O que foi feito | Testes |
|---|---|---|---|
| C1 (crítico) | Resposta perdida voltava a virar silêncio com atraso de entrega de 3 ticks ou mais: uma mensagem anterior entregue atrasada apagava a marca da perda | perda marcada pela posição da mensagem na conversa (`core/bus.py`) | TEST-420 |
| C2 (crítico) | `waiver_humano` perdido contornava a POL-06 ou gerava um segundo ticket para o mesmo veto | avisos de decisão humana ao AG-CIN com reentrega pelo transporte, até 5 tentativas (`ENTREGA_GARANTIDA`) | TEST-421 |
| C3 (crítico) | Segundo fator derrubável por força bruta: o limite de códigos errados era por pré-sessão e `desativar` não contava erros | contador por conta, bloqueio de 15 minutos, senha atual exigida para desativar e trocar os códigos | TEST-430 a 432 |
| C4 (crítico) | Registro de fontes, planilhas e credenciais compartilhado entre empresas | registro por empresa | TEST-433 |
| C5 (crítico) | `restaurar` gravava fora da pasta de destino com um backup forjado | backup inteiro validado antes de gravar; o cofre viaja no pacote de chaves | TEST-434, 435 |
| M1 | Texto: "nenhum ataque mudou o desfecho" era falso para o bloco D, onde H6b não foi testada | análise corrigida: H6b restrita ao bloco A e o que não foi testado declarado (`docs/dsm4/resultados.md`) | — (texto) |
| M2 | Bloco D com uma pessoa só no roteiro de aprovação media a falta da segunda pessoa, e "execução correta em 100% dos dois lados" era tautológico | segunda pessoa no roteiro (`caos.py`); comparação real do acesso relatada | experimento regenerado |
| M3 a M8 | Cofre fora do backup (M3); mapeamento confirmado continuava valendo depois de a fonte mudar (M4); fluxo de eventos mantinha viva a sessão e não reconferia permissão e empresa (M5); porte da simulação trocável por quem só opera (M6); simulação duplicada por requisições simultâneas (M7); delegação não usada ao vivo, troca de senha sem derrubar as outras sessões e rajada de entradas segurando o cadastro (M8) | cada um corrigido no código | TEST-435 a 441, 445, 446 |
| M9 | Estatística: pseudo-replicação na RQ4; latência dependente da premissa de 3 ticks por etapa; Holm sem as comparações idênticas; falta de poder lida como ausência de efeito; resultados por construção | RQ4 com a seed como unidade (`estudo.py`); o resto declarado na análise, com os números | experimento regenerado |
| Menores | Opções de cenário que terminavam em traceback (m1); aprendizado que aceitava evidência citando um proponente (m2); manifesto de backup torto com traceback (m5); servidor MCP de Excel que morria com requisição malformada (m6); duas contas da mesma pessoa cumprindo a dupla aprovação, veto sem exposição, delegação de outra empresa, preço infinito e cofre adulterado (m7); INV-04 sem cobrir o aval (`endorse`) | corrigidos | TEST-422, 423, 434, 442 a 444, 447, 448 |
| Verificação do avaliador | Escrita aceita pelo ERP com releitura inválida era registrada como "não executada" | registrada como "aplicado, confirmação inválida" e nunca repetida | TEST-449 |

A numeração completa do relatório do avaliador não está no repositório; a tabela agrupa os achados pelo
que foi corrigido, com o identificador quando ele aparece no código ou nos testes.

- **O que não foi corrigido** (em [`docs/dsm4/limitacoes.md`](../../docs/dsm4/limitacoes.md), "Em aberto
  depois da correção simulada da DSM4"): o bloqueio de 15 minutos do segundo fator ou da troca de senha
  pode ser provocado de propósito por quem já tem a senha ou uma sessão roubada (troca consciente contra
  a força bruta); a resposta final ao solicitante não menciona "aplicado, confirmação inválida" (fica no
  trace e no ticket); AG-CIN e AG-ORC ficam com intenção BDI aberta em parte das execuções com falha (não
  afeta a resposta); nenhum invariante cobre "uma liberação humana por veto"; a reentrega garantida vai
  só até 5 tentativas; a TUI não tem campo de segmento no cadastro de empresa.
- **O que o avaliador não verificou:** planilha maliciosa, redirecionamento 30x, respostas lentas do ERP,
  o wheel instalado, o Docker Compose, provedores reais de LLM e os roteiros Playwright.
- **Efeito no experimento:** as correções C1, C2, M2 e M9 mudaram o sistema ou a análise depois de ver os
  resultados; o experimento foi executado de novo na versão 1.0.0 (terceira rodada) e a análise trata as
  três rodadas lado a lado, sem tratar nenhuma posterior à primeira como confirmatória
  ([`docs/dsm4/resultados.md`](../../docs/dsm4/resultados.md), "Três rodadas").

### Revisão e teste exploratório do coautor (PR #4)

O Jiliard abriu o PR #4 ("DSM3: ajustes finais") depois de rodar o projeto como usuário, no Windows PowerShell
5.1 e no dashboard em navegador real: o `iniciar.ps1` parava em máquinas sem Python 3.13; as dependências da
documentação eram instaladas em todo modo e falhavam com Python 3.11; na reincidência, o waiver negado pela
política aparecia no diálogo e, se escolhido, bloqueava o fechamento sem o aprovador saber; e duas atribuições
de feedback (DSM1 × DSM2) estavam trocadas. O PR foi integrado à v0.5.0 e à versão final com os commits dele
preservados, e mesclado na `main`. Na mesma revisão ele registrou uma limitação que ficou para a DSM4 (a POL-06
só era conferida na emissão do ticket); ela foi fechada nesta versão, com a conferência também na decisão do
waiver (TEST-424). O detalhe do teste exploratório está em `entregas/dsm3/USO_DE_IA.md`.

### Autoria

O avaliador escreveu que a autoria fica **"difícil de defender oralmente"**, porque os lotes da DSM4 foram
implementados por agentes de IA, em paralelo, em cerca de um dia. É um registro correto do que aconteceu:
os autores planejaram, dividiram os lotes, decidiram o que está em "Decisões que ficaram com os autores",
revisaram e integraram, mas não escreveram à mão a maior parte do código nem do texto desta entrega. A
nota de demonstração e autoria (6,5) reflete isso, e nenhuma correção posterior muda esse fato.

Para a apresentação, os autores precisam dominar, sem apoio do texto:

1. **A conclusão do experimento e por que ela é desfavorável**: o workflow funcionalmente equivalente, o
   empate de qualidade (em boa parte por construção), a perda em mensagens e em robustez sob perda, e por
   que a robustez favorece o workflow por construção.
2. **O desenho e a estatística**: blocos A a D, seed como unidade, números aleatórios comuns e o
   aninhamento das perdas, a definição de execução correta (e por que ela é 100% por definição sem
   falhas), Wilcoxon, Mann-Whitney, delta de Cliff, Holm por família e por que poucas seeds diferentes
   não dão poder (2/2^k).
3. **As três rodadas**: o que cada correção mudou, por que nenhuma rodada posterior é confirmatória e o
   que continua igual nas três.
4. **O transporte**: estado da conversa mudado no envio, aviso de prazo ao iniciador, marca da perda pela
   posição (C1), reentrega garantida dos avisos de decisão humana (C2) e seu limite de 5 tentativas.
5. **O Approval Gate e a política**: ticket com hash do veto, uso único e prazo, atestado da pessoa, alçada,
   delegação, dupla aprovação, POL-06; os ataques e o que é um "aceito sem a premissa", e por que H6b não
   foi testada no bloco D.
6. **BDI e cognição**: o ciclo BDI dos especialistas, proposta não é crença, por que o LLM fica fora do
   Orquestrador, do AG-CUS e do AG-CIN, e por que a cognição local não mostrou ganho.
7. **Segurança e acesso**: segundo fator com contador por conta (e a negação de serviço aceita), fontes
   por empresa, backup validado antes de gravar, raiz de confiança no processo e no disco.
8. **Rastreabilidade e reprodução**: `models/*.yaml`, `tools/trace.py --check`, como os números do
   relatório saem de `tools/relatorio_numeros.py` e como reproduzir o `execucoes.csv` byte a byte.
9. **A demonstração**: rodar os comandos de [`docs/dsm4/demonstracao.md`](../../docs/dsm4/demonstracao.md) ao
   vivo e explicar o trace que aparece.
10. **O que ficou em aberto e o que não foi testado**, sem suavizar.

### Verificação

Os números da versão entregue (testes coletados e executados, cenários conferidos, objetos rastreados,
resultados do experimento) são gerados por `python tools/relatorio_numeros.py --suite` e aparecem no
relatório técnico; nenhum foi escrito à mão. Os 41 roteiros Playwright foram executados à parte sobre a versão
entregue (41 de 41, em 14/11/2026), fora do gerador. A leitura e a revisão de todo o código e texto gerado pelos
autores, antes da submissão, é o passo que falta e é deles: os pontos a dominar estão na seção "Autoria".

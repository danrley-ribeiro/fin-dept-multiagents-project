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
| Revisão final pós-feedback da DSM3 (POL-06 na mesma trava da memória, pacote, ensaio exploratório de carga) | GPT Astra 6.2 | Codex | 25/11/2026 |
| Revisão do commit anterior, correções do feedback da DSM3 (permissões, suíte do ZIP), bloco E do experimento e roteiro do vídeo | Claude Opus 5.5 | Claude Code | 25 e 26/11/2026 |

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
relatório técnico; nenhum foi escrito à mão. Os 41 roteiros Playwright foram executados à parte, fora do gerador:
41 de 41 em 14/11/2026 e de novo depois das revisões de 25 e 26/11/2026. Cada mudança desta etapa passou por
pull request revisado por um dos autores, e o trabalho de uma IA foi revisado pela outra (o commit do Codex de
25/11 foi revisado pelo Claude em 26/11, seção abaixo). Responder pelo código e pelo texto, inclusive o gerado
por IA, é dos autores: os pontos a dominar estão na seção "Autoria".

## Revisão final de 25/11/2026

O Codex consultou a conversa compartilhada e o feedback do professor, modificou a política de reincidência e a persistência, atualizou os testes do pacote e executou o ensaio exploratório pareado de carga. Também revisou os materiais de reprodução e demonstração. As afirmações sobre aprovação entre processos podem ser verificadas em TEST-459. Os dados do ensaio estão em `docs/dsm4/resultados/carga.csv`.

## Revisão de 26/11/2026 (Claude Code)

O Claude Code (Claude Opus 5.5) revisou o commit do Codex em modo de planejamento. Três agentes só
leram o código e apontaram os problemas. Os autores escolheram o que fazer: corrigir de verdade as
permissões e fazer um reforço focado do experimento, sem refazer o principal. A revisão achou:

- **Regras diferentes no waiver.** A oferta, na emissão do ticket, olhava só meses anteriores. A
  decisão olhava também o mesmo mês e os posteriores. O waiver era oferecido e depois recusado. Isso
  quebrava o caso sequencial documentado e, no lote, deixava o ticket expirar com `erro_agente`.
- **Ticket recusado ainda oferecia o waiver.** O segundo ticket concorrente não era reavaliado.
- **Entrada fantasma na memória** quando a gravação falhava.
- **Permissões.** Quem reiniciava pelo dashboard podia aprovar o próprio pedido. O porte micro
  escolhido no reinício dispensava a POL-13.
- **Suíte do ZIP.** Falhava sem `setuptools`/`wheel`, e havia um teste intermitente no login.
- **Documentos inconsistentes.** A âncora do trace na demonstração estava desatualizada, assim como
  o número de invariantes. A medida do tempo de parede do bloco E, antes da análise, incluía o
  cálculo das métricas.

Cada correção tem teste (TEST-453, 460 a 469), e o bloco E está declarado como desvio do
pré-registro (desvio 14 em `docs/dsm4/resultados.md`). O roteiro passou a ser de vídeo, com as
evidências pedidas no feedback e os dois autores em arquitetura e segurança. A verificação foi feita em sequência, em Windows, na versão 1.1.0:

- **pytest:** 733 passaram, 0 falharam e 1 pulado (o teste que só roda dentro do ZIP extraído), em 18,2 minutos (12,5 numa rodada anterior, com a máquina livre);
- **rastreabilidade:** 552 objetos, 0 erros;
- **vitest:** 12 de 12;
- **Playwright:** 41 de 41, com o Chromium do Playwright;
- **experimento inteiro:** rodado duas vezes, com o mesmo `execucoes.csv`; as métricas são iguais
  às da terceira rodada em todas as linhas;
- **bloco E:** duas execuções com o mesmo CSV;
- **suíte a partir do ZIP:** extraído fora do repositório (sem Git), num venv só com o projeto e o
  pytest (Python 3.11, versão com a replicação do bloco E). Rodada três vezes: nas três, 708 passaram, nenhum
  falhou e 5 foram pulados, cada um com motivo (os 2 módulos da TUI, sem `textual`; um de LLM, sem `anthropic`;
  o que monta o pacote pelo Git; o do wheel, sem o pacote `wheel`). Numa rodada anterior, com `setuptools` e
  `wheel` instalados, o teste do wheel também passou. Os links dos Markdown e a build do dashboard são conferidos
  dentro do próprio pacote. A revisão humana desta etapa é a do pull request `dsm4-revisao` → `main`,
feita pelo coautor.

### Correção simulada da entrega final (26/11/2026)

Os autores pediram duas correções simuladas no formato do professor. Cada uma foi feita por um agente
independente (Claude Opus 5.5), que recebeu só o ZIP extraído, o enunciado, o feedback da DSM3 e, na
segunda, o aviso do professor sobre o vídeo. Nenhum dos dois agentes viu as conclusões da revisão.

- **Primeira rodada: nota 8,9.** O avaliador tentou burlar a POL-06 por vários caminhos e achou dois que
  funcionavam:
  - dois processos com pastas de chaves diferentes sobre o mesmo arquivo de memória liberavam os dois
    waivers, porque a trava ficava na pasta de chaves;
  - no dashboard de demonstração, reiniciar o cenário esquecia o waiver anterior, porque a memória
    vivia só no processo.

  Os dois foram corrigidos com teste: TEST-470 falha nas três tentativas com a trava antiga, e há ainda
  TEST-471 e TEST-472. Também foram corrigidos:
  - o filtro de um comando da demonstração;
  - caminhos que não existiam no ZIP;
  - o tempo do experimento;
  - a prova do pré-registro sem o Git (nota com os commits).

  As tabelas do experimento principal passaram a mostrar o desvio-padrão. Os autores decidiram manter
  a conta `avaliador` com todos os papéis, para facilitar os testes do professor, e isso ficou
  declarado nas limitações. O roteiro foi refeito para o vídeo de 15 a 30 minutos com foco no código
  e nos testes, como o professor pediu.
- **Segunda rodada: nota 9,2.** Nenhuma tentativa liberou dois waivers: 12 rodadas com dois processos,
  quatro reinícios pelo dashboard e a CLI concorrente. O avaliador achou uma brecha nova: a POL-13
  comparava só o nome da conta, e duas contas da mesma pessoa do ERP pediam e aprovavam. Ela foi
  corrigida com teste (TEST-473, que falha sem a correção). Ficaram declarados como limitação:
  - o caminho de memória sem normalização (falha fechada);
  - o workflow equivalente, que valia para um pedido: depois desta rodada ele ganhou a mesma memória da POL-06 e a
    recusa de mês já atendido, com teste (TEST-474 a 476), e o bloco E ganhou o fator porte e o aprovador sorteado;
  - o bloco E, que é exploratório.
- **Terceira rodada: nota 9,1, depois de os autores pedirem as correções que a segunda apontou.** O workflow
  equivalente ganhou a mesma memória da POL-06 e a recusa de mês já atendido; o bloco E ganhou porte e aprovador
  sorteado. O avaliador não conseguiu liberar dois waivers em 26 rodadas concorrentes. Achou:
  - a POL-13 comparando a pessoa do ERP como texto exato ("Elisa" e "elisa " contornavam a regra);
  - o painel sem o aviso do impedimento pela pessoa;
  - `/api/estado` com as opções desatualizadas;
  - o teste de empacotamento pulado no ZIP;
  - o SHA antigo no README e o diagrama da arquitetura desatualizado;
  - no roteiro: o fechamento bloqueado só por prazo, a conta "14 de 14" sem explicação e pouco tempo para o
    experimento.

  Tudo foi corrigido, com teste (TEST-473 com as grafias, TEST-477), e o bloco E ganhou a concorrência sob perda
  de mensagens (TEST-478; 1.020 execuções).
- **Quarta rodada: nota 9,1.** Nenhuma tentativa liberou dois waivers (20 rodadas com dois processos,
  dashboard com reinícios do cenário e do servidor, CLI concorrente). O avaliador achou:
  - a pessoa do ERP ainda contornável por acento ou caracteres de largura total ("Élisa" na POL-13, "Cárla"
    na POL-03);
  - a suíte do ZIP falhando numa segunda execução, por causa do `build/` deixado pelo teste do wheel;
  - duas referências de linha erradas no roteiro e números antigos neste arquivo;
  - o diagrama da arquitetura sem a ligação SVC-POL → SVC-MEM;
  - a memória "comprometida" quando dois processos criam o mesmo arquivo com grafias diferentes do caminho
    (limitação que estava declarada).

  Tudo foi corrigido, com teste (TEST-473 e TEST-479 com as grafias Unicode, TEST-480 e TEST-481 para o nome dos
  arquivos de estado e a migração). Um teste novo confere toda referência de linha do roteiro, e a suíte do ZIP
  foi rodada duas vezes seguidas sem falha.
- **Quinta rodada: nota 9,3.** Nenhum caminho liberou dois waivers (12 corridas entre processos, sete grafias do
  caminho, dois servidores sobre a mesma pasta, arquivo apagado e versão antiga recolocada). O avaliador achou:
  - a pessoa do ERP ainda contornável por homóglifo ("е" cirílico) ou caractere invisível;
  - o `operador` disparando pedidos sem ter a permissão de pedir;
  - um aprovador sem cargo no porte derrubando o AG-CIN (KeyError) em vez de virar achado;
  - a demo 7 que, na velocidade padrão, mostra o caso sequencial e não o simultâneo;
  - tempos declarados abaixo do medido.

  Tudo foi corrigido, com teste (TEST-482 a 485). A correção da pessoa do ERP mudou de natureza: em vez de só
  normalizar texto livre, o vínculo passou a ser validado como identificador do ERP. O bloco E ganhou a
  concorrência com um especialista fora do ar.

### Replicação confirmatória do bloco E (27/11/2026)

Depois da quinta correção simulada restavam limitações declaradas. A pedido dos autores, o Claude avaliou quais
dava para corrigir e foi feita a que dependia só de método: o bloco E deixou de ser apenas exploratório. A ordem
foi esta:

1. As oito conclusões do bloco E viraram hipóteses com critério de decisão (H-E1 a H-E8), escritas em
   `docs/dsm4/experimento-bloco-e.md` e publicadas no PR (commit `95e7923`) **antes** de rodar qualquer seed nova
   e antes de mudar o código.
2. O código ganhou só a opção `--primeira-seed`; a replicação rodou com as seeds 31 a 60, duas vezes, com o mesmo
   `execucoes.csv`.
3. O verificador `tools/confirmar_bloco_e.py` foi escrito enquanto a replicação rodava e conferido primeiro nas
   seeds 1 a 30. Resultado na replicação: 8 de 8 confirmadas. Os testes TEST-486 e TEST-487 conferem as seeds
   novas e que um dado adulterado refuta a hipótese.

O Orquestrador como ponto único de falha e o workflow distribuído continuam como limitações declaradas: corrigi-los
mudaria a arquitetura na véspera da entrega.

Na mesma rodada, a pedido dos autores, a conta de demonstração `avaliador` deixou de aprovar (opera, pede e audita) e o
ajuste de modelos e cotas passou do aprovador para a operação. Duas limitações declaradas saíram da lista ("a conta
`avaliador` opera e aprova" e "quem decide vetos também liga o LLM"). Os testes Python e de navegador que decidiam com
a `avaliador` passaram a decidir com o `controller`; os que conferiam a POL-13 para quem opera e aprova usam uma conta
criada pelo administrador com os dois papéis.

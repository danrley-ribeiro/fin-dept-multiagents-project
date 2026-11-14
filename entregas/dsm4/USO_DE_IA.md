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
| **Experimento** (um agente): pré-registro escrito antes do código, modelo de falhas por seed, workflow funcionalmente equivalente, biblioteca estatística só com a biblioteca padrão, estudo em quatro blocos, comando `fin-mas experimento`, análise das duas rodadas | `docs/dsm4/experimento.md`, `caos.py`, `baseline_eq.py`, `estatistica.py`, `estudo.py`, `estudo_relato.py`, `docs/dsm4/resultados/`, `docs/dsm4/resultados.md` |
| **Implantação e portes** (um agente): pacote instalável, contêiner, backup, restauração e migração; MEI, Média empresa II e segmentos, com as fontes legais consultadas | `implantacao.py`, `manutencao.py`, `Dockerfile`, `compose.yaml`, `docker/`, `tools/empacotar_wheel.py`, `models/portes.yaml`, `models/segmentos.yaml`, `docs/dsm4/implantacao.md`, `docs/dsm4/portes-e-segmentos.md` |
| **Conectores** (um agente): interface `Conector`, REST genérico, cliente MCP, ERP de demonstração, entendimento determinístico de fontes, cofre de credenciais da fonte, aba Fontes | `conectores/`, `fontes/entendimento.py`, `docs/dsm4/ADR-011-conectores-e-entendimento.md` |
| **Acesso avançado** (um agente): segundo fator, alçada por pessoa, delegação, dupla aprovação, escalonamento, cofre, memória sobre o arquivo selado, várias empresas, TUI | `services/acesso_avancado.py`, `services/cofre.py`, `docs/dsm4/acesso-avancado.md`, `docs/dsm4/ADR-012-acesso-avancado.md` |
| **Este relatório e o fechamento** (um agente): gerador dos números do relatório a partir das fontes, relatório técnico em LaTeX, diagramas da entrega, páginas de arquitetura final, limitações, demonstração, reprodução e catálogo de cenários, apresentação, empacotador | `tools/relatorio_numeros.py`, `tools/empacotar_dsm4.py`, `entregas/dsm4/`, `docs/dsm4/{arquitetura-final,limitacoes,demonstracao,reproducao,cenarios-de-teste}.md`, `docs/checkpoints.md` |
| Testes de todos os lotes: e2e, integração e interface (TUI pelo Pilot); nenhum unitário novo | `tests/e2e/`, `tests/integration/`, `tests/tui/` |
| Integração dos lotes numa versão e verificação: suíte, rastreabilidade, cenários, experimento regenerado sobre o código integrado, documentação | merges na branch da DSM4 |

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
estava também no PROT-DEL. Foi corrigido e o experimento rodou de novo; as duas rodadas estão relatadas lado
a lado e a segunda é declarada não confirmatória ([`docs/dsm4/resultados.md`](../../docs/dsm4/resultados.md),
"Duas rodadas" e "Desvios do pré-registro").

### Correção simulada da DSM4

*A preencher depois da correção simulada da DSM4*: quem avaliou, nota do estado avaliado, achados,
o que foi corrigido e se houve reavaliação.

### Verificação

Os números da versão entregue (testes coletados e executados, cenários conferidos, objetos rastreados,
resultados do experimento) são gerados por `python tools/relatorio_numeros.py --suite` e aparecem no
relatório técnico; nenhum foi escrito à mão. Os roteiros Playwright não foram executados na geração do
relatório. Todo código e texto gerado foi revisado pelos autores antes da entrega.

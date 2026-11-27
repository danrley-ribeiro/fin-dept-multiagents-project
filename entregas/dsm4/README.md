# DSM4 — Experimentação, documentação e entrega final

**Projeto:** Sistema Multiagente de Controladoria da **SMA** (empresa fictícia) — INE5628 Sistemas Multiagentes, UFSC.
**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).
**Prazo:** 02/12/2026 às 18h30. Enunciado: [`enunciados/`](../../enunciados/).

Pacote final do sistema: um Orquestrador e cinco agentes especialistas (Custos, Orçamento, Resultados,
Controles Internos e Relatórios) que fecham o mês e avaliam o orçamento de empresas de seis portes e quatro
segmentos, comunicando-se por protocolos em máquina de estados num barramento que valida identidade, papel,
contraparte, esquema e transição, com decisão humana atestada no Approval Gate e toda decisão num trace
encadeado.

**O resultado do experimento, em uma frase:** com as mesmas funções, o SMA empata com um workflow
centralizado em qualidade e perde em custo e em robustez quando mensagens se perdem; a cognição local não
mostrou ganho significativo; nenhuma crítica foi publicada sem tratamento e nenhum ataque foi aceito
indevidamente, em nenhuma condição. O experimento rodou três vezes; as correções entre as rodadas foram
feitas depois de ver resultados, e nenhuma rodada posterior à primeira é confirmatória. Os números
(versão 1.0.0, terceira rodada; a 1.0.1 só traz as correções da DSM3 v0.5.1 e a 1.1.0, as da revisão final; nenhuma das duas muda as métricas, ver a conferência em resultados)
estão no relatório e em
[`docs/dsm4/resultados.md`](../../docs/dsm4/resultados.md).

**Vídeo da apresentação:** _link a preencher depois da gravação_ (roteiro em
[`apresentacao/roteiro.md`](apresentacao/roteiro.md)).

**Revisão final (25 e 26/11), em resposta ao feedback da DSM3:**

- **POL-06.** A POL-06 é conferida na aprovação e o waiver é gravado na mesma transação, sob trava do
  sistema operacional, ao lado do arquivo de memória. O segundo ticket concorrente perde a opção de
  waiver (TEST-424, nas duas ordens; TEST-459, com dois processos no mesmo arquivo; TEST-470, com
  pastas de chaves diferentes).
- **Memória.** A oferta e a decisão usam a mesma regra. Rodar de novo com a mesma memória dá o mesmo
  resultado (TEST-460 a 464). No dashboard, reiniciar o cenário não apaga a memória; só o
  administrador a limpa (TEST-471, TEST-472).
- **Permissões.** Quem reinicia um cenário pelo dashboard é o solicitante e não aprova (POL-13), nem
  por outra conta da mesma pessoa (TEST-473). O porte micro escolhido no reinício não dispensa essa
  regra (TEST-453, TEST-465).
- **Suíte do ZIP.** Roda sem Git e sem as dependências opcionais; os testes que precisam delas são
  pulados. Sem `textual`, os 23 testes da TUI viram 2 pulos de módulo, então a contagem coletada é
  menor que a do relatório, que é a do ambiente com as dependências de desenvolvimento.
- **Bloco E.** Um bloco E exploratório varia pedidos concorrentes, frequência de irregularidades e
  volume, com desvio-padrão e testes por seed ([resultados](../../docs/dsm4/resultados.md), seção
  "Bloco E"). Para repeti-lo: `python -m fin_mas.estudo_e --replicas 30 --out saidas/bloco_e`.

## Conteúdo do pacote

`make entrega-dsm4` (ou `python tools/empacotar_dsm4.py`) gera `entregas/dsm4/DSM4-entrega.zip`:

| Pasta ou arquivo | O que é |
|---|---|
| `README.md` | este arquivo: como executar do zero, critério → evidência, o que mudou, limitações |
| `USO_DE_IA.md` | uso de IA no desenvolvimento desta etapa |
| `documentacao/relatorio.pdf` | **relatório técnico** (fontes: `relatorio.tex`, `referencias.bib`, `numeros.tex` e `rastreabilidade.tex` gerados, `figuras/`) |
| `diagramas/`, `modelos-editaveis/` | diagramas em PNG e as fontes Mermaid (`.mmd`): arquitetura final, desenho do experimento, ciclo BDI dos especialistas, correção da mensagem perdida, as seis FSMs, Approval Gate, waiver concorrente, decisão atestada, login, hipóteses, validação do barramento |
| `apresentacao/` | `slides.md`, `roteiro.md` (falas, tempos e comandos da demonstração) e `DSM4-apresentacao.pptx` |
| `codigo/` | código-fonte e configurações (`src/`, `models/`, `web/`, `tools/`, `docker/`, `Dockerfile`, `compose.yaml`, `pyproject.toml`, `requirements*`, `.env.example`, `Makefile`, `iniciar.*`), testes (`tests/`, `web/e2e/`), documentação (`docs/`, incluindo os dados e resultados do experimento em `docs/dsm4/resultados/`), `README.md` e `CHANGELOG.md` da raiz |

## Como executar do zero

Requer Python 3.11+. O ZIP já traz o dashboard construído (`codigo/web/dist/`): `serve --demo` abre no
navegador sem bun nem Node. bun e o Chrome só são necessários para reconstruir a interface e para os testes de
navegador (Playwright); para o PDF, TeX Live com `latexmk` e `rsvg-convert`; para o `.pptx`, pandoc. Passo a passo completo, com tempos: [`docs/dsm4/reproducao.md`](../../docs/dsm4/reproducao.md).

```bash
cd codigo                                                   # dentro do zip; no repositório, a raiz
python3 -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt
source .venv/bin/activate && export PYTHONPATH=src
python -m pytest                                            # suíte inteira, offline (de 5 a 15 minutos, conforme a máquina)
python tools/trace.py --check                               # rastreabilidade: 0 erros
python -m fin_mas cenarios --verificar                      # cada cenário duas vezes: resposta, invariantes, mesmo hash
python -m fin_mas experimento --rapido --out /tmp/exp       # aparato do experimento em 3 seeds (segundos)
python -m fin_mas experimento --replicas 30 --out saidas/reproducao      # experimento completo (de 5 a 10 minutos)
python -m fin_mas serve --demo                              # dashboard em http://127.0.0.1:8765 (avaliador / Demonstracao-SMA-2026)
```

No Windows (PowerShell; não há `make`, e o ambiente fica em `.venv\Scripts`):

```powershell
cd codigo                                                   # dentro do zip; no repositório, a raiz
py -3 -m venv .venv; .\.venv\Scripts\pip install -e . -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1; $env:PYTHONPATH = "src"
python -m pytest                                            # suíte inteira, offline
python tools\trace.py --check                               # rastreabilidade: 0 erros
python -m fin_mas cenarios --verificar                      # cada cenário duas vezes: resposta, invariantes, mesmo hash
python -m fin_mas experimento --rapido --out $env:TEMP\exp  # aparato do experimento em 3 seeds
python -m fin_mas.estudo_e --replicas 30 --out saidas\bloco_e   # bloco E: concorrência, frequência e volume
python -m fin_mas serve --demo                              # dashboard em http://127.0.0.1:8765 (avaliador / Demonstracao-SMA-2026)
cd web; bun run test; $env:PW_CHANNEL = "chromium"; bun run test:e2e   # sem o Chrome do sistema: Chromium do Playwright
```

A tela de entrada do dashboard mostra a conta de demonstração quando o servidor sobe com `--demo`. Quem
reinicia um cenário dispara os pedidos dele e, pela POL-13, não decide sobre eles: para decidir, entre com
outra conta (por exemplo, `controller`, com a mesma senha).

Atalho para tudo: `./iniciar.sh` (Linux/macOS) ou `.\iniciar.ps1` (Windows), com os modos `testes`,
`replay`, `cli`, `docs`. Roteiro de demonstração com as evidências pedidas no feedback da DSM3 e plano B:
[`docs/dsm4/demonstracao.md`](../../docs/dsm4/demonstracao.md).

## Critério → evidência

| Critério (peso) | Evidência |
|---|---|
| Sistema final e corretude (25%) | `codigo/src/fin_mas/`; cenários do catálogo, todos com resposta explícita, invariantes e repetibilidade conferidos por `cenarios --verificar` ([catálogo da DSM4](../../docs/dsm4/cenarios-de-teste.md), [da DSM3](../../docs/dsm3/cenarios-de-teste.md)); invariantes de segurança sobre qualquer trace (`fin-mas invariantes`); cenários adversariais com todos os ataques recusados; relatório §3 a §8 |
| Arquitetura e SMA (20%) | [arquitetura final](../../docs/dsm4/arquitetura-final.md) e ADR-002 a ADR-012; quem é BDI, quem é reativo e por quê ([ADR-010](../../docs/dsm4/ADR-010-especialistas-bdi.md), incluindo onde a cognição não se justificou); protocolos com transições inválidas testadas ([protocolos](../../docs/dsm3/protocolos.md)); coordenação e comportamento coletivo (relatório §5 e §10.5); proposta de modelo ≠ crença ([ADR-008](../../docs/dsm3/ADR-008-cognicao-local-e-llm.md)) |
| Experimentação e análise (20%) | [pré-registro](../../docs/dsm4/experimento.md) versionado antes do código; [resultados](../../docs/dsm4/resultados.md) por pergunta, com as três rodadas, o que não se confirmou, o que não foi testado, desvios e ameaças; [tabelas e testes gerados](../../docs/dsm4/tabelas.md); dado bruto `docs/dsm4/resultados/execucoes.csv` (terceira rodada, versão 1.0.0); na versão 1.1.0 entregue, `experimento --replicas 30` reproduz byte a byte o `docs/dsm4/resultados/revisao-final/execucoes.csv` (SHA-256 `b324fc61…` no `manifesto.json` dessa pasta), com as mesmas métricas: só a coluna de hash muda, porque a versão entra no trace; relatório §10 |
| Testes e reprodutibilidade (15%) | `codigo/tests/` (unit, e2e, integração, TUI), `codigo/web/e2e/` (Playwright), vitest; `tools/trace.py --check`; mesmo hash por seed; [reprodução do zero](../../docs/dsm4/reproducao.md); números do relatório gerados por `tools/relatorio_numeros.py` |
| Documentação (10%) | relatório técnico (`documentacao/relatorio.pdf`); documentação navegável (`docs/`, Sphinx, <https://fin-dept-multiagents-project.readthedocs.io>); [limitações](../../docs/dsm4/limitacoes.md); diagramas editáveis; este README |
| Demonstração e autoria (10%) | vídeo (link acima) com os dois autores; [roteiro do vídeo](apresentacao/roteiro.md); [roteiro de demonstração](../../docs/dsm4/demonstracao.md), `apresentacao/`; [`USO_DE_IA.md`](USO_DE_IA.md); [checkpoints CP1–CP13](../../docs/checkpoints.md) |

## O que mudou desde a DSM3 (v0.5.0)

- **Experimento redesenhado** em resposta ao feedback (baseline desequilibrado e variância zero):
  workflow centralizado funcionalmente equivalente, com a equivalência por teste; plantios, falhas, perfil
  do aprovador e ataques sorteados por seed; 30 seeds, quatro blocos (principal, varredura, ablação,
  acesso); estatística por seed com bootstrap, Wilcoxon, delta de Cliff e Holm; pré-registro antes do código.
- **Defeito encontrado pelo experimento e corrigido:** a resposta de um especialista perdida na entrega
  deixava a solicitação sem resposta (a conversa já constava concluída). Agora a perda avisa o iniciador,
  que reenvia uma vez ou falha de forma explícita.
- **Correção simulada independente da DSM4** (nota 7,2 ao estado anterior às correções, sem reavaliação):
  5 achados críticos, 10 moderados e 7 menores; os críticos e quase todos os demais corrigidos, cada um com
  teste (TEST-420 a TEST-449). No transporte, a marca da perda não é mais apagada por entrega atrasada e os
  avisos de decisão humana têm reentrega; segundo fator com contador por conta; fontes por empresa;
  restauração validada antes de gravar. No experimento, bloco D com duas pessoas no roteiro de aprovação e
  RQ4 com a seed como unidade. O experimento rodou uma terceira vez na versão 1.0.0; as três rodadas estão
  relatadas lado a lado. O que ficou em aberto está em [`USO_DE_IA.md`](USO_DE_IA.md) e nas limitações.
- **Especialistas BDI** (AG-RES, AG-CUS, AG-REL) como variantes nos níveis `local` e `llm`, com as classes
  reativas preservadas no `basico`; aprendizado local auditável; estratégias de compromisso; base normativa
  com proveniência e "sem evidência" (ADR-010).
- **Implantação:** pacote instalável com os dados embutidos, contêiner com porta só em loopback, backup
  selado e restauração com falha fechada, migração versionada.
- **Portes e segmentos:** MEI e Média empresa II, com as fontes legais; comércio, serviços e indústria.
- **Conectores e entendimento de fontes** (ADR-011): interface `Conector` (ERP simulado, planilhas, REST
  JSON genérico, cliente MCP), entendimento determinístico de uma fonte nova com confirmação humana do
  mapeamento, LLM só como sugestão opcional, rede externa só por permissão, credenciais no cofre.
- **Acesso avançado** (ADR-012): segundo fator TOTP, alçada por pessoa, delegação, dupla aprovação,
  escalonamento, cofre selado, memória segura entre processos, várias empresas por cadastro.
- **Fechamento:** relatório técnico com números gerados, arquitetura final, limitações, roteiro de
  demonstração, reprodução do zero, catálogo de cenários da DSM4, apresentação e este pacote.

## Limitações (resumo)

A lista completa está em [`docs/dsm4/limitacoes.md`](../../docs/dsm4/limitacoes.md).

- Com funções iguais, o SMA não ganha do workflow em nenhuma métrica de resultado; perde em custo e em
  robustez sob perda de mensagens. A recuperação é um reenvio por subtarefa; o Orquestrador é ponto único de
  falha e não foi exercitado como tal.
- A cognição local não mostrou ganho na medida registrada; o AG-REL BDI não acrescenta capacidade; nenhum
  LLM real foi avaliado.
- A robustez favorece o workflow por construção; um workflow distribuído não foi construído. Dados
  sintéticos com plantio. Nenhuma rodada depois da primeira é confirmatória. A latência entre os braços é
  modelada (3 ticks por etapa no workflow, premissa que decide o sinal sem falhas); com 5 seeds diferentes ou
  menos os testes não têm poder; H6b não foi testada com o controle de acesso ligado.
- Raiz de confiança no processo e na pasta de chaves; o cofre garante integridade, não confidencialidade
  contra quem lê o disco; pedido sem atestado no PROT-SOL.
- Uma máquina, só loopback; nenhum conector de fornecedor nem ERP real; algumas funções de acesso só pela
  API, CLI e TUI (sem tela no dashboard).
- Os roteiros Playwright (41, no Chrome headless) rodam por `make web-test` e passaram na versão entregue
  em 25/11/2026. A tabela de testes do relatório reúne essa execução do navegador com os resultados do pytest e do vitest.

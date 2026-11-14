# DSM4 — Experimentação, documentação e entrega final

**Projeto:** Sistema Multiagente de Controladoria da **SMA** (empresa fictícia) — INE5628 Sistemas Multiagentes, UFSC.
**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).
**Prazo:** 02/12/2026. Enunciado: [`enunciados/`](../../enunciados/).

Pacote final do sistema: um Orquestrador e cinco agentes especialistas (Custos, Orçamento, Resultados,
Controles Internos e Relatórios) que fecham o mês e avaliam o orçamento de empresas de seis portes e quatro
segmentos, comunicando-se por protocolos em máquina de estados num barramento que valida identidade, papel,
contraparte, esquema e transição, com decisão humana atestada no Approval Gate e toda decisão num trace
encadeado.

**O resultado do experimento, em uma frase:** com as mesmas funções, o SMA empata com um workflow
centralizado em qualidade e perde em custo e em robustez quando mensagens se perdem; a cognição local não
mostrou ganho significativo; nenhuma crítica foi publicada sem tratamento e nenhum ataque foi aceito
indevidamente, em nenhuma condição. Os números estão no relatório e em
[`docs/dsm4/resultados.md`](../../docs/dsm4/resultados.md).

## Conteúdo do pacote

`make entrega-dsm4` (ou `python tools/empacotar_dsm4.py`) gera `entregas/dsm4/DSM4-entrega.zip`:

| Pasta ou arquivo | O que é |
|---|---|
| `README.md` | este arquivo: como executar do zero, critério → evidência, o que mudou, limitações |
| `USO_DE_IA.md` | uso de IA no desenvolvimento desta etapa |
| `documentacao/relatorio.pdf` | **relatório técnico** (fontes: `relatorio.tex`, `referencias.bib`, `numeros.tex` e `rastreabilidade.tex` gerados, `figuras/`) |
| `diagramas/`, `modelos-editaveis/` | diagramas em PNG e as fontes Mermaid (`.mmd`): arquitetura final, desenho do experimento, ciclo BDI dos especialistas, correção da mensagem perdida, as seis FSMs, Approval Gate, decisão atestada, login, hipóteses, validação do barramento |
| `apresentacao/` | `slides.md`, `roteiro.md` (falas, tempos e comandos da demonstração) e `DSM4-apresentacao.pptx` |
| `codigo/` | código-fonte e configurações (`src/`, `models/`, `web/`, `tools/`, `docker/`, `Dockerfile`, `compose.yaml`, `pyproject.toml`, `requirements*`, `.env.example`, `Makefile`, `iniciar.*`), testes (`tests/`, `web/e2e/`), documentação (`docs/`, incluindo os dados e resultados do experimento em `docs/dsm4/resultados/`), `README.md` e `CHANGELOG.md` da raiz |

## Como executar do zero

Requer Python 3.11+. Para o dashboard, bun e o Chrome; para o PDF, TeX Live com `latexmk` e `rsvg-convert`;
para o `.pptx`, pandoc. Passo a passo completo, com tempos: [`docs/dsm4/reproducao.md`](../../docs/dsm4/reproducao.md).

```bash
cd codigo                                                   # dentro do zip; no repositório, a raiz
python3 -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt
source .venv/bin/activate && export PYTHONPATH=src
python -m pytest                                            # suíte inteira, offline (cerca de 4 minutos)
python tools/trace.py --check                               # rastreabilidade: 0 erros
python -m fin_mas cenarios --verificar                      # cada cenário duas vezes: resposta, invariantes, mesmo hash
python -m fin_mas experimento --rapido --out /tmp/exp       # aparato do experimento em 3 seeds (segundos)
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # experimento completo (cerca de 3 minutos)
python -m fin_mas serve --demo                              # dashboard em http://127.0.0.1:8765 (avaliador / Demonstracao-SMA-2026)
```

Atalho para tudo: `./iniciar.sh` (Linux/macOS) ou `.\iniciar.ps1` (Windows), com os modos `testes`,
`replay`, `cli`, `docs`. Roteiro de demonstração de 10 minutos, com plano B:
[`docs/dsm4/demonstracao.md`](../../docs/dsm4/demonstracao.md).

## Critério → evidência

| Critério (peso) | Evidência |
|---|---|
| Sistema final e corretude (25%) | `codigo/src/fin_mas/`; cenários do catálogo, todos com resposta explícita, invariantes e repetibilidade conferidos por `cenarios --verificar` ([catálogo da DSM4](../../docs/dsm4/cenarios-de-teste.md), [da DSM3](../../docs/dsm3/cenarios-de-teste.md)); invariantes de segurança sobre qualquer trace (`fin-mas invariantes`); cenários adversariais com todos os ataques recusados; relatório §3 a §8 |
| Arquitetura e SMA (20%) | [arquitetura final](../../docs/dsm4/arquitetura-final.md) e ADR-002 a ADR-012; quem é BDI, quem é reativo e por quê ([ADR-010](../../docs/dsm4/ADR-010-especialistas-bdi.md), incluindo onde a cognição não se justificou); protocolos com transições inválidas testadas ([protocolos](../../docs/dsm3/protocolos.md)); coordenação e comportamento coletivo (relatório §5 e §10.5); proposta de modelo ≠ crença ([ADR-008](../../docs/dsm3/ADR-008-cognicao-local-e-llm.md)) |
| Experimentação e análise (20%) | [pré-registro](../../docs/dsm4/experimento.md) versionado antes do código; [resultados](../../docs/dsm4/resultados.md) por pergunta, com as duas rodadas, o que não se confirmou, desvios e ameaças; [tabelas e testes gerados](../../docs/dsm4/tabelas.md); dado bruto `docs/dsm4/resultados/execucoes.csv` (reproduzível byte a byte, SHA-256 em `manifesto.json`); relatório §10 |
| Testes e reprodutibilidade (15%) | `codigo/tests/` (unit, e2e, integração, TUI), `codigo/web/e2e/` (Playwright), vitest; `tools/trace.py --check`; mesmo hash por seed; [reprodução do zero](../../docs/dsm4/reproducao.md); números do relatório gerados por `tools/relatorio_numeros.py` |
| Documentação (10%) | relatório técnico (`documentacao/relatorio.pdf`); documentação navegável (`docs/`, Sphinx, <https://fin-dept-multiagents-project.readthedocs.io>); [limitações](../../docs/dsm4/limitacoes.md); diagramas editáveis; este README |
| Demonstração e autoria (10%) | [roteiro de demonstração](../../docs/dsm4/demonstracao.md), `apresentacao/`; [`USO_DE_IA.md`](USO_DE_IA.md); [checkpoints CP1–CP13](../../docs/checkpoints.md) |

## O que mudou desde a DSM3 (v0.5.0)

- **Experimento redesenhado** em resposta ao feedback (baseline desequilibrado e variância zero):
  workflow centralizado funcionalmente equivalente, com a equivalência por teste; plantios, falhas, perfil
  do aprovador e ataques sorteados por seed; 30 seeds, quatro blocos (principal, varredura, ablação,
  acesso); estatística por seed com bootstrap, Wilcoxon, delta de Cliff e Holm; pré-registro antes do código.
- **Defeito encontrado pelo experimento e corrigido:** a resposta de um especialista perdida na entrega
  deixava a solicitação sem resposta (a conversa já constava concluída). Agora a perda avisa o iniciador,
  que reenvia uma vez ou falha de forma explícita. As duas rodadas estão relatadas lado a lado.
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
  sintéticos com plantio. A segunda rodada não é confirmatória.
- Raiz de confiança no processo e na pasta de chaves; o cofre garante integridade, não confidencialidade
  contra quem lê o disco; pedido sem atestado no PROT-SOL.
- Uma máquina, só loopback; nenhum conector de fornecedor nem ERP real; algumas funções de acesso só pela
  API, CLI e TUI (sem tela no dashboard).
- Os roteiros Playwright rodam no CI e por `make web-test`; não foram executados na geração do relatório.

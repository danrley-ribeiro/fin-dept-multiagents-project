# Sistema Multiagente de Controladoria · SMA

<img src="assets/sma-logo.svg" alt="SMA" width="56">

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE, Prof. Rafael Luiz Cancian).

O Orquestrador e cinco agentes especializados (Agente de Custos, Agente de Orçamento, Agente de
Resultados, Agente de Controles Internos e Agente de Relatórios) executam as rotinas de
controladoria da **SMA** (empresa fictícia) de forma coordenada e auditável. Orçamento e
Controles Internos são **agentes cognitivos BDI**; as regras valem para empresas de **qualquer
porte** (micro, pequena, média e grande), com ou sem ERP (modelos Excel e servidor MCP de Excel). Um
**dashboard** mostra os agentes trabalhando num escritório, ao vivo ou em replay. Desde a DSM3, o barramento
valida identidade, papel, destinatário, conversa e esquema de toda mensagem, e as decisões humanas passam
por um **Approval Gate** com política explícita e uso único. Na versão 0.5.0, quem usa a plataforma é uma
**pessoa com conta** (login, papéis, decisão atestada pela pessoa autenticada, trilha de acesso), o Agente de
Orçamento trabalha com **hipóteses verificáveis** (propostas por regras locais ou por um LLM, que só viram
crença com evidência) e pode **negociar prazo** com o Orquestrador. A IA generativa continua **opcional e
desligada por padrão** (Orçamento, Resultados e Relatórios; nunca Orquestrador, Custos ou Controles
Internos), com cinco provedores, consentimento para envio externo e números conferidos contra o núcleo.

Na **versão final (1.0.0, DSM4)**: Resultados, Custos e Relatórios ganham variantes BDI (as reativas seguem como
nível `basico` e braço de comparação), com aprendizado local auditável, estratégias de compromisso e base normativa
com proveniência; acesso avançado (segundo fator, alçada por pessoa, delegação, dupla aprovação, cofre, várias
empresas); conectores genéricos e entendimento automático de fontes, sem IA generativa; portes MEI e Média empresa II
e segmentos (comércio, serviços, indústria); instalação por wheel e Docker, backup e restauração. O **experimento**
foi refeito com pré-registro, falhas sorteadas e um workflow centralizado funcionalmente equivalente: com as mesmas
funções, o SMA **empata em qualidade e perde em custo e em robustez sob perda de mensagens**
([análise](docs/dsm4/resultados.md), [relatório técnico](entregas/dsm4/documentacao/relatorio.pdf)).

```bash
.\iniciar.ps1          # Windows: prepara tudo (Python, .venv, bun, dashboard) e abre o escritório ao vivo
./iniciar.sh           # Linux/macOS
```

Modos e o que é preparado: veja [Um comando](#um-comando) abaixo.

📘 **Documentação navegável:** <https://fin-dept-multiagents-project.readthedocs.io>

## Um comando

Na raiz do repositório:

| Sistema | Comando |
|---|---|
| Windows (PowerShell) | `.\iniciar.ps1` |
| Linux / macOS | `./iniciar.sh` |
| Qualquer um, com Python 3.11+ já instalado | `python tools/iniciar.py` |

Sem argumento, abre o **escritório ao vivo** no navegador (`http://127.0.0.1:8765`) com as **contas de
demonstração** (abaixo). Para outro modo, passe o nome dele: `.\iniciar.ps1 testes`, `./iniciar.sh replay` etc.

| Modo | O que faz |
|---|---|
| `ao-vivo` (padrão) | servidor Python (`serve --demo`) + dashboard com login: agentes executando agora; pausar, desligar agentes, pedir, decidir vetos, logs, LLM, trocar porte, enviar planilha, conforme os papéis da conta |
| `replay` | dashboard sem servidor Python, reproduzindo os traces exportados (offline, sem login), em `http://127.0.0.1:4173` |
| `dev` | servidor Python (8765) + Vite com recarga automática (`http://127.0.0.1:5173`), para desenvolver o dashboard |
| `testes` | pytest (437: unit, e2e, integração e TUI), `tools/trace.py --check`, vitest (12) e os 30 roteiros de uso real no Chrome |
| `docs` | gera a documentação Sphinx em `docs/_build/html` |
| `cli` | roda um cenário no terminal: `--cenario veto_correcao --porte micro` |
| `instalar` | só prepara o ambiente |

Opções: `--porta N`, `--cenario NOME` (ao-vivo e cli), `--porte micro|pequena|media|grande` (cli) e
`--sem-navegador`.

**O que o comando prepara** (só o que falta ou mudou, então as próximas execuções são rápidas):

1. **Python 3.11+**: o `iniciar.ps1` procura `py -3.13`, `py -3.12`, `py -3.11`, `python` e, se não houver, instala o
   Python 3.12 pelo `winget`; o `iniciar.sh` procura `python3.13`/`python3.12`/`python3.11`/`python3` e, se faltar,
   mostra o comando de instalação (`apt` ou `brew`).
2. **Ambiente virtual `.venv`** com o projeto e as dependências de testes (`pyproject.toml`,
   `requirements-dev.txt`); reinstala só se esses arquivos mudarem. As dependências da documentação
   (`docs/requirements.txt`, Sphinx 9, que exige Python 3.12+) só entram no modo `docs`.
3. **bun**: usa o que estiver no `PATH` ou em `~/.bun/bin`; se não houver, roda o instalador oficial
   (`bun.sh/install`).
4. **Dependências do dashboard** (`bun install`, conforme `web/bun.lock`) e **build** (`bun run build`) quando o
   código em `web/src` for mais novo que o build.
5. **Traces do replay e comparação com o baseline** (`fin_mas comparar` e `fin_mas export`), se ainda não existirem.

Os testes de uso real usam o **Chrome instalado** (Playwright com `channel: chrome`, sem baixar navegador).
Depois da preparação, nada usa a internet.

## Autoria

| Nome | Matrícula |
|---|---|
| Danrley Moreira Ribeiro | 23102664 |
| Jiliard Mai Peifer | 23103129 |

## Entregas

Cada entrega tem uma pasta própria com tudo o que é submetido.

| Entrega | Pasta | Situação |
|---|---|---|
| **DSM1** — Cenário, requisitos e modelagem | [`entregas/dsm1/`](entregas/dsm1/README.md) | ✅ concluída |
| **DSM1 v2** — revisão pós-feedback | [`entregas/dsm1/documentacao/main-v2.pdf`](entregas/dsm1/documentacao/main-v2.pdf) | ✅ concluída |
| **DSM2** — Arquitetura e protótipo (revisados após o feedback) | [`entregas/dsm2/`](entregas/dsm2/README.md) | ✅ concluída (prazo 31/10) |
| **DSM3** — Comunicação, coordenação e protótipo funcional (v0.5.0) | [`entregas/dsm3/`](entregas/dsm3/README.md) | ✅ concluída (prazo 18/11) |
| **DSM4** — Experimentação, documentação e entrega final (v1.0.0) | [`entregas/dsm4/`](entregas/dsm4/README.md) | ✅ concluída (prazo 02/12) |

Enunciados e o exemplo de formato estão em [`enunciados/`](enunciados/).

## Estrutura

```
entregas/
  dsm1/
    README.md            descrição da entrega
    USO_DE_IA.md         uso de IA na entrega
    documentacao/        main.tex (arquivo único) e main.pdf
    modelos-editaveis/   diagramas Mermaid (.mmd)
    diagramas/           imagens dos diagramas (.png)
  dsm2/                  README, USO_DE_IA, diagramas e modelos-editaveis do protótipo
  dsm3/                  README, USO_DE_IA, diagramas e modelos-editaveis (validação, PROT-APR, login, decisão atestada, hipóteses, PROT-DEL)
src/fin_mas/             protótipo em Python (agentes, bus A2A, MCP mock, cenários, CLI, SVC-IAM, TUI)
tests/                   testes unit, e2e, integration e tui (pytest)
web/                     dashboard (Vite/React) e roteiros Playwright (web/e2e)
enunciados/              enunciados da disciplina e exemplo de formato
models/                  modelos AOSE em YAML (fonte única da rastreabilidade)
tools/trace.py           valida a cadeia de rastreabilidade e gera a documentação
docs/                    site de documentação (Sphinx + sphinx-needs, Read the Docs)
```

## Rastreabilidade

Todos os objetos (problemas, stakeholders, objetivos, requisitos, papéis, agentes, protocolos,
normas, recursos, serviços, componentes, testes e métricas) têm **ID estável** em `models/*.yaml`.
O `tools/trace.py` valida a cadeia **Problema → Requisito → Objetivo → Papel/Agente →
Protocolo/Norma → Componente → Teste → Métrica** (falha com ID órfão, link quebrado ou requisito
incompleto) e gera os objetos da documentação (`docs/_generated/`) e as máquinas de estados dos
protocolos (`entregas/dsm1/modelos-editaveis/protocols_fsm_*.mmd`).

Situação atual (DSM4, v1.0.0): **26/26 requisitos (100%) com cadeia completa**, 513 objetos rastreados,
292 testes modelados (292 **executados**), 29 métricas, 0 erros.

## Como executar

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt   # Python 3.11+ (versões exatas: requirements-lock.txt)
python -m fin_mas run --scenario fechar_mes --seed 42             # make demo
python -m fin_mas cenarios --verificar                            # 64 cenários: resposta, 10 invariantes, repetível (make cenarios)
python -m fin_mas run --scenario ataque_decisao_forjada           # 14 ataques ao barramento rejeitados (make ataque)
python -m fin_mas run --scenario ataque_acesso                    # 15 ataques ao controle de acesso rejeitados
python -m fin_mas run --scenario orc_hipotese_local               # hipótese verificada com o AG-CIN
python -m fin_mas run --scenario negociacao_prazo                 # negociação de prazo no PROT-DEL
python -m fin_mas serve --demo                                    # dashboard com login em http://127.0.0.1:8765
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # o experimento da DSM4 (make experimento, ~3 min)
python -m pytest                                                  # 669 testes: unit 95, e2e 428, integração 123, TUI 23 (make test)
```

Reprodução completa, do zero, com o tempo de cada passo: [docs/dsm4/reproducao.md](docs/dsm4/reproducao.md).
Roteiro de demonstração de 10 minutos: [docs/dsm4/demonstracao.md](docs/dsm4/demonstracao.md).

**Contas de demonstração** (`serve --demo`, `instalar --demo`, `acesso demo` e o modo ao vivo do comando único),
todas com a senha pública `Demonstracao-SMA-2026`: `avaliador` (vê e faz tudo, menos administrar acesso), `admin`,
`operador`, `auditor`, `controller`, `elisa`, `carla`, `diego`, `ana` e `bruno`. Papéis e para que serve cada uma:
[docs/dsm3/acesso.md](docs/dsm3/acesso.md), seção "Contas de demonstração".

**Comandos novos da v0.5.0:**

| Comando | Para quê |
|---|---|
| `fin-mas instalar [--demo]`, `fin-mas doctor`, `fin-mas serve --instalacao dados` | implantação local e diagnóstico |
| `fin-mas acesso iniciar \| demo \| usuario \| sessao \| trilha \| papeis \| tui` | contas, papéis, sessões, trilha de acesso; console de administração (`pip install "fin-mas[tui]"`) |
| `fin-mas auditoria TRACE [--agente --tipo --tarefa --q ...]`, `explicar TRACE SEQ`, `sequencia TRACE CONVERSA`, `invariantes TRACE` | auditoria de um trace gravado |
| `fin-mas cenarios [--verificar] [--filtro]` | catálogo de cenários com conferência |
| `fin-mas llm provedores \| avaliar` | provedores de LLM e bancada de avaliação de hipóteses |
| `fin-mas run ... --cognicao basico\|local\|llm`, `--llm PROVEDOR:MODELO --llm-agentes --llm-usos --llm-consentimento` | nível de cognição e LLM opcional |

**Comandos novos da v1.0.0:**

| Comando | Para quê |
|---|---|
| `fin-mas experimento [--replicas N] [--rapido] --out PASTA` | experimento pré-registrado: braços, falhas sorteadas, estatística, tabelas e figuras |
| `fin-mas run ... --segmento`, `--compromisso`, `--aprendizado ARQUIVO`; `fin-mas normas CONSULTA` | segmento da empresa, estratégia de compromisso, aprendizado persistente e busca na base normativa |
| `fin-mas fontes entender \| testar`, `fin-mas erp-demo` | entendimento automático de uma fonte (OpenAPI, amostra JSON, tools MCP, planilha) e ERP de demonstração em loopback |
| `fin-mas acesso 2fa \| politica \| delegacao \| alcadas \| empresa \| segredo`, `fin-mas memoria adotar` | acesso avançado e adoção de um arquivo de memória íntegro |
| `fin-mas backup`, `restaurar`, `migrar`; `make wheel`, `make docker` | cópia de segurança conferida, pacote instalável e contêiner |

`fin-mas` é o mesmo que `python -m fin_mas` (instalado pelo `pip install -e .`). Alvos do `make`: `cenarios`,
`diagramas`, `cobertura`, `experimento`, `pdf-dsm4`, `entrega-dsm4` e `verificar-tudo`
(rastreabilidade, pytest, cenários, vitest, Playwright e documentação, parando no primeiro erro).

Roteiro de demonstração e mapa feedback → correção: [entregas/dsm3/README.md](entregas/dsm3/README.md);
catálogo de cenários de teste: [docs/dsm3/cenarios-de-teste.md](docs/dsm3/cenarios-de-teste.md);
protótipo e cenário de depuração: [entregas/dsm2/README.md](entregas/dsm2/README.md).

## Como compilar

Pré-requisitos: Python 3.12+ (Sphinx 9), Graphviz e TeX Live (com `latexmk`).

```bash
python -m venv .venv && .venv/bin/pip install -r docs/requirements.txt
make trace   # valida a cadeia e regenera os arquivos gerados
make docs    # documentação HTML em docs/_build/html
make pdf     # entregas/dsm1/documentacao/main.pdf
```

O CI (`.github/workflows/docs.yml`) repete essas etapas a cada push e PR. Fluxo de trabalho em
dupla e publicação no Read the Docs: [docs/plataforma/como-contribuir.md](docs/plataforma/como-contribuir.md).

## Materiais da disciplina

A apostila é de uso exclusivo em sala de aula e **não é versionada** (`.gitignore`); ela é apenas
citada (Cancian, 2026) e parafraseada nos artefatos.

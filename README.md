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
por um **Approval Gate** com política explícita e uso único. A IA generativa é **opcional e desligada por
padrão**, restrita à síntese do Agente de Relatórios e validada contra os números do template.

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

Sem argumento, abre o **escritório ao vivo** no navegador (`http://127.0.0.1:8765`). Para outro modo,
passe o nome dele: `.\iniciar.ps1 testes`, `./iniciar.sh replay` etc.

| Modo | O que faz |
|---|---|
| `ao-vivo` (padrão) | servidor Python + dashboard: agentes executando agora; pausar, desligar agentes, decidir vetos, trocar porte, enviar planilha |
| `replay` | dashboard sem servidor Python, reproduzindo os traces exportados (offline), em `http://127.0.0.1:4173` |
| `dev` | servidor Python (8765) + Vite com recarga automática (`http://127.0.0.1:5173`), para desenvolver o dashboard |
| `testes` | pytest (e2e e integração), `tools/trace.py --check`, testes do reducer e os 14 testes de uso real no Chrome |
| `docs` | gera a documentação Sphinx em `docs/_build/html` |
| `cli` | roda um cenário no terminal: `--cenario veto_correcao --porte micro` |
| `instalar` | só prepara o ambiente |

Opções: `--porta N`, `--cenario NOME` (ao-vivo e cli), `--porte micro|pequena|media|grande` (cli) e
`--sem-navegador`.

**O que o comando prepara** (só o que falta ou mudou, então as próximas execuções são rápidas):

1. **Python 3.11+**: o `iniciar.ps1` procura `py -3.13`, `py -3.12`, `py -3.11`, `python` e, se não houver, instala o
   Python 3.12 pelo `winget`; o `iniciar.sh` procura `python3.13`/`python3.12`/`python3.11`/`python3` e, se faltar,
   mostra o comando de instalação (`apt` ou `brew`).
2. **Ambiente virtual `.venv`** com o projeto e as dependências de testes e de documentação
   (`pyproject.toml`, `requirements-dev.txt`, `docs/requirements.txt`); reinstala só se esses arquivos mudarem.
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
| **DSM3** — Comunicação, coordenação e protótipo funcional | [`entregas/dsm3/`](entregas/dsm3/README.md) | ✅ concluída (prazo 18/11) |

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
  dsm3/                  README, USO_DE_IA e modelos-editaveis (validação, PROT-APR)
src/fin_mas/             protótipo em Python (agentes, bus A2A, MCP mock, cenários, CLI)
tests/                   testes unitários e e2e (pytest)
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

Situação atual (DSM3): **19/19 requisitos (100%) com cadeia completa**, 194 objetos rastreados,
90 testes modelados (89 **executados**; TEST-19 é de entrega futura).

## Como executar o protótipo (DSM3)

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt   # Python 3.11+
python -m fin_mas run --scenario fechar_mes --seed 42             # make demo
python -m fin_mas run --scenario ataque_decisao_forjada           # 14 ataques rejeitados (make ataque)
python -m fin_mas run --scenario reincidencia_waiver --memoria m.json
python -m fin_mas verificar trace.jsonl                           # trace com cadeia de hashes e selo HMAC
python -m pytest                                                  # 249 testes (make test)
```

Roteiro de demonstração e mapa feedback → correção: [entregas/dsm3/README.md](entregas/dsm3/README.md);
protótipo e cenário de depuração: [entregas/dsm2/README.md](entregas/dsm2/README.md).

## Como compilar

Pré-requisitos: Python 3.11+, Graphviz e TeX Live (com `latexmk`).

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

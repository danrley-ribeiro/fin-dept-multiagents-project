# Uso de IA

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de ferramentas de IA generativa na produção dos artefatos do projeto, por entrega.
Duas coisas distintas aparecem aqui:

- **IA no processo de desenvolvimento** (ferramentas usadas pelos autores para produzir os artefatos): registrada abaixo.
- **IA no produto** (LLM opcional por flag em três agentes): decisão de projeto documentada na
  [ADR-002](docs/dsm1/ADR-002-llm-opcional-por-flag.md), não neste arquivo.

---

## DSM1 — Cenário, requisitos e modelagem

**Modelo utilizado no desenvolvimento:** **Claude Opus 5.5** (Anthropic), por meio do Claude Code
(assistente de programação em terminal).
**Período:** 06/10/2026.

### Papel da IA

A IA trabalhou **organizando os arquivos e a documentação** do projeto. A concepção do sistema
(orquestrador, cinco agentes especializados, camadas de comunicação, governança, configuração de
modelos e memória) foi definida pelos autores em `arquitetura-sistema-multiagente-controladoria.md`
e `ideias.txt`. A ferramenta partiu desse material para estruturar, padronizar e interligar os
artefatos da entrega.

| Atividade de organização | Artefatos |
|---|---|
| Leitura do enunciado da DSM1/DSM2, do PDF de referência e dos capítulos 4–5 da apostila, para alinhar a estrutura dos documentos ao que é avaliado | — |
| Organização das ideias dos autores em modelos AOSE com IDs estáveis (problemas, objetivos, requisitos, papéis, agentes, protocolos, normas, ambiente, métricas, testes) | `models/*.yaml` |
| Organização da estrutura de pastas por entrega (DSM1 completa, DSM2 pré-estruturada) | `docs/`, `entregas/`, `diagrams/` |
| Script que verifica a ligação entre os documentos e gera tabelas e páginas a partir dos modelos | `tools/trace.py` |
| Formatação da documentação navegável, dos diagramas Mermaid e das figuras TikZ | `docs/`, `diagrams/dsm1/`, `entregas/dsm1/figures/` |
| Formatação do documento da entrega em LaTeX | `entregas/dsm1/main.tex`, `entregas/dsm1/referencias.bib` |
| README, Makefile, CI | raiz, `.github/` |

### Decisões que permaneceram com os autores

- Escopo do sistema (orquestrador + 5 agentes + camadas transversais): definido pelos autores antes do uso da ferramenta.
- Plataforma de documentação (Sphinx-needs + Read the Docs).
- Política de IA no produto: LLM **opcional, desligado por padrão**, apenas em Relatórios, Resultados e Orçamento.
- Organização da documentação por entrega (DSM1 completa, DSM2 apenas pré-estruturada).

### Verificação

- Rastreabilidade checada automaticamente (`tools/trace.py --check`): 0 erros, 18/18 requisitos com cadeia completa.
  A ferramenta detectou e levou à correção de uma inconsistência real: o papel Aprovador participava do
  protocolo de veto sem declará-lo.
- Documentação compilada com `sphinx -W` (nenhum aviso permitido).
- PDF compilado e inspecionado visualmente página a página.
- Nenhum teste foi declarado aprovado: os 25 testes estão apenas **especificados** (execução na DSM2).
- **Revisão humana dos autores:** *(preencher: quem revisou, o que foi alterado e o que foi validado
  contra a apostila)*.

### Limites conhecidos

- O conteúdo da apostila foi apenas citado e parafraseado (material de uso restrito).
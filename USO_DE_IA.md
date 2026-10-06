# Uso de IA

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de ferramentas de IA generativa na produção dos artefatos do projeto, por entrega.
Duas coisas distintas aparecem aqui:

- **IA no processo de desenvolvimento** (ferramentas usadas pelos autores para produzir os artefatos): registrada abaixo.
- **IA no produto** (LLM opcional por flag em três agentes): decisão de projeto documentada na
  [ADR-002](docs/dsm1/ADR-002-llm-opcional-por-flag.md), não neste arquivo.

---

## DSM1 — Cenário, requisitos e modelagem

**Ferramenta:** Claude Code (modelo Claude Opus 5.5, Anthropic), assistente de programação em terminal.
**Período:** 06/10/2026.

### O que a IA fez

| Atividade | Artefatos | Natureza da contribuição |
|---|---|---|
| Análise do enunciado da DSM1/DSM2, do PDF de referência e dos capítulos 4–5 da apostila | — | leitura e síntese para orientar a modelagem |
| Proposta da plataforma de documentação (comparação Mintlify × Backstage × MkDocs × Sphinx-needs/RTD) | `docs/plataforma/ADR-001-plataforma-docs.md` | pesquisa e recomendação; **decisão tomada pelos autores** |
| Rascunho dos modelos AOSE (problemas, stakeholders, objetivos, requisitos, papéis, agentes, protocolos, normas, ambiente, métricas, testes) a partir das ideias dos autores | `models/*.yaml` | redação a partir de `arquitetura-sistema-multiagente-controladoria.md` e `ideias.txt` (autores) |
| Script de validação e geração de rastreabilidade | `tools/trace.py` | código gerado e executado |
| Páginas da documentação, diagramas Mermaid e figuras TikZ | `docs/`, `diagrams/dsm1/`, `entregas/dsm1/figures/` | redação e diagramação |
| Documento LaTeX da entrega | `entregas/dsm1/main.tex` | redação e diagramação |
| README, este arquivo, Makefile, CI e configuração do Read the Docs | raiz, `.github/` | redação |

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
- Referências bibliográficas clássicas (Gaia, Tropos, Prometheus, FIPA) foram incluídas pelo conhecimento
  da ferramenta e devem ser conferidas pelos autores.

---

## DSM2 — Arquitetura e protótipo inicial

*Pendente. Registrar aqui ferramentas, atividades, decisões humanas, verificação e limites ao
iniciar a entrega.*

# Uso de IA

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de ferramentas de IA generativa na produção dos artefatos do projeto, por entrega.
Duas coisas distintas aparecem aqui:

- **IA no processo de desenvolvimento** (ferramentas usadas pelos autores para produzir os artefatos): registrada abaixo.
- **IA no produto** (LLM opcional por flag em três agentes): decisão de projeto documentada na
  [ADR-002](../../docs/dsm1/ADR-002-llm-opcional-por-flag.md), não neste arquivo.

---

## DSM1 — Cenário, requisitos e modelagem

**Modelo utilizado no desenvolvimento:** **Claude Opus 5.5**.
**Período:** 06/10/2026 (versão inicial), 19/10/2026 e 20/10/2026 (revisões).

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
| Organização da estrutura de pastas por entrega (DSM1 completa, DSM2 pré-estruturada) | `docs/`, `entregas/` |
| Script que verifica a ligação entre os documentos e gera tabelas e páginas a partir dos modelos | `tools/trace.py` |
| Formatação da documentação navegável, dos diagramas Mermaid e das figuras TikZ | `docs/`, `entregas/dsm1/modelos-editaveis/`, `entregas/dsm1/documentacao/main.tex` |
| Formatação do documento da entrega em LaTeX | `entregas/dsm1/documentacao/main.tex` |
| README, Makefile, CI | raiz, `.github/` |
| Revisão de 19/10/2026: nomes padronizados (português + ID), remoção de "terceirização", diagramas renomeados pela página da documentação, diagramas de sequência "avaliar o orçamento" e "veto e waiver", tratamento de falhas e linha de base do problema | `models/`, `docs/dsm1/`, `diagrams/dsm1/`, `entregas/dsm1/` |
| Revisão de 20/10/2026: PDF reduzido de 15 para 6 páginas (sem capa e sumário, tabelas compactas, duas figuras substituídas por referência ao `.mmd`); imagens PNG dos diagramas Mermaid; remoção de comentários de instrução e de anotações de peso, prazo e versão; reorganização do repositório com uma pasta por entrega e `main.tex` em arquivo único | `entregas/dsm1/`, `enunciados/`, `tools/trace.py`, `README.md`, `docs/` |

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
- Nenhum teste foi declarado aprovado: os 26 testes estão apenas **especificados** (execução na DSM2).
- **Revisão humana dos autores**, dividida entre os dois:
  - **Danrley Moreira Ribeiro:** revisou os modelos AOSE (`models/*.yaml`) e a cadeia de
    rastreabilidade (`tools/trace.py`), conferindo requisitos, papéis e protocolos contra os
    capítulos 4–5 da apostila. Pediu a análise de completude que levou ao segundo cenário âncora,
    ao tratamento de falhas, à linha de base do problema e à indicação de onde estão as máquinas
    de estados.
  - **Jiliard Mai Peifer:** revisou o texto do PDF e do README. Definiu o nome do projeto
    (Sistema Multiagente de Controladoria, sem "terceirização"), pediu a padronização dos nomes
    dos agentes e a retirada do prazo do README.

### Limites conhecidos

- O conteúdo da apostila foi apenas citado e parafraseado (material de uso restrito).
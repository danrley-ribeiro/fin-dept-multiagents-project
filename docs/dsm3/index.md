# DSM3 — Comunicação, coordenação e protótipo funcional

<span class="badge-pend">em andamento</span> · prazo: 18/11/2026

## Enunciado

Comunicação com conteúdo e finalidade claros; protocolo de interação documentado;
coordenação, negociação, cooperação ou planejamento; tratamento de conflito, falha ou
alternativa; testes integrados ou cenários automatizados; evidências de comportamento
coletivo.

## Já disponível (adiantado na revisão da DSM2)

| Item | Onde |
|---|---|
| Empresa fictícia **SMA S.A.**, logo em relatórios, dashboard e documentação | `src/fin_mas/env/empresa.py`, `assets/sma-logo.svg`, `python -m fin_mas relatorio` |
| Dados mock de três competências com anomalias variadas (`expediente_sma`) | {doc}`../dsm2/prototipo` |
| Regras e BDI por porte (micro, pequena, média, grande) | {doc}`../dsm2/portes` |
| Empresas sem ERP: modelos Excel, modo manual, servidor MCP de Excel | {doc}`../dsm2/planilhas` |
| Escritório ao vivo com decisão humana, desligamento de agentes e badges | {doc}`../dsm2/dashboard` |
| Coordenação: consulta direta ORC↔CIN, veto com correção, reserva de período | {doc}`../dsm2/coordenacao` |

## Planejado para a entrega

- Avaliar **Contract Net** para alocar verificações entre mais de um verificador (CP6).
- **Approval Gate** formal (PROT-APR) para efeitos externos, como a correção no ERP (CP7).
- **Memória** aprovada com proveniência (CP9) e **redaction** (CP10).
- RAG sobre documentos normativos da empresa, além do YAML por porte (CP8).
- Ampliar os testes integrados de comportamento coletivo (TEST-11 a TEST-13, TEST-23).

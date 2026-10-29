# ADR-006 — Regras por porte como base normativa e planilhas como fonte de dados

**Status:** aceita · **Contexto:** as regras e os BDIs precisam valer para empresas de qualquer
porte, e empresas sem ERP precisam usar o sistema com planilhas.

## Decisão

1. **Base normativa em dados, não em código.** `models/portes.yaml` define, por porte, alçadas,
   severidades, controles compensatórios, materialidade, fonte primária do realizado, ciclos de
   correção e pesos dos desejos de AG-ORC e AG-CIN, com as referências legais e normativas
   (LC 123/2006, BNDES, Lei 11.638/2007, ITG 1000, NBC TG 1000, NBC TA 320, COSO 2013).
2. **Os agentes percebem o porte.** A tool MCP `normas.perfil` entrega o perfil; os agentes
   revisam a crença `porte` e ajustam conhecimento e pesos, como qualquer outra percepção. O
   baseline usa o mesmo perfil, o que mantém a comparação justa.
3. **Planilha como fonte equivalente ao ERP.** `fontes/planilha.py` gera os modelos e lê a
   planilha preenchida com validação; o resultado tem a mesma interface do dataset sintético,
   então nenhum agente muda. Sem ERP, `erp.realizado_por_conta` é indisponível, e não
   simulado: o AG-ORC registra isso e segue só com a planilha.
4. **Servidor MCP de Excel real** (stdio, JSON-RPC 2.0) sobre o mesmo leitor, restrito à pasta e
   sem sobrescrever arquivos.
5. **`openpyxl`** como única dependência nova (puro Python, sem rede).

## Consequências

- Mudar uma política (por exemplo, a alçada do gerente) é editar o YAML ou a planilha, sem
  mexer em agentes.
- Dados reais não têm gabarito: as métricas de acurácia só valem para os cenários sintéticos.
- O dataset sintético foi recalibrado por porte para a receita anual cair na faixa legal
  (verificado em 10 seeds por porte, TEST-36).

# Experimento da DSM4 — tabelas e testes

Tudo nesta página é gerado por `python -m fin_mas experimento` a partir de
`docs/dsm4/resultados/execucoes.csv` (uma linha por execução). São os números da **terceira
rodada**, sobre a versão final 1.0.0; os da primeira e da segunda estão resumidos em
{doc}`resultados` (seção "Três rodadas") e inteiros no histórico do git (commits `cfa6b6f` e
`174e7b6`). A leitura está em {doc}`resultados`; o desenho, em {doc}`experimento`. Os testes da
RQ4 usam a seed como unidade (média por seed), desvio declarado em {doc}`resultados`.

## Tabelas por pergunta de pesquisa

```{include} resultados/resumo.md
```

## Testes de hipótese

```{include} resultados/testes.md
```

## Bloco E (exploratório)

Gerado por `python -m fin_mas.estudo_e` a partir de `docs/dsm4/resultados/bloco_e/execucoes.csv`;
a leitura está em {doc}`resultados` (seção "Bloco E").

```{include} resultados/bloco_e/resumo.md
:heading-offset: 2
```

## Bloco E: replicação confirmatória (seeds 31 a 60)

Mesmo aparato, seeds novas; hipóteses e critérios em {doc}`experimento-bloco-e`.

```{include} resultados/bloco_e_confirmatorio/confirmacao.md
:heading-offset: 2
```

```{include} resultados/bloco_e_confirmatorio/resumo.md
:heading-offset: 2
```

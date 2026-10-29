# Empresas sem ERP: modelos Excel e servidor MCP de Excel

Micro e pequenas empresas costumam controlar o mês em planilhas. Para elas o sistema traz
**modelos Excel embutidos** e funciona em **modo manual**: a empresa preenche a planilha, o
sistema a valida e os agentes a leem por MCP, com a mesma proveniência e as mesmas regras do
porte. As correções que o aprovador aceita são gravadas de volta na planilha, que continua
sendo a fonte da verdade.

## Modelos

```bash
python -m fin_mas modelos --out modelos
#   modelo_controladoria_em_branco.xlsx  exemplo_micro.xlsx  exemplo_pequena.xlsx
#   exemplo_media.xlsx  exemplo_grande.xlsx
```

Também dá para baixar pelo dashboard: **Dados da empresa → Minha empresa sem ERP**.

| Aba | Conteúdo | Validações |
|---|---|---|
| LEIA-ME | instruções de preenchimento | — |
| Empresa | razão social, sigla, porte, competência (AAAA-MM), se possui ERP | porte em micro/pequena/media/grande; competência válida |
| Pessoas | usuário, nome, cargo | cargo existente no porte |
| Produtos | código, nome, unidade de negócio, quantidade, preço e custo variável unitário | UN-A/UN-B; números |
| CustosFixos | centro de custo, descrição, valor do mês | número |
| Orcamento | conta, orçado no trimestre, orçado e realizado acumulados | números |
| Lancamentos | código, competência, conta, fornecedor, NF, valor, criado por, aprovado por, situação | pessoas e contas existentes; situação ativo/estornado |

Valores ficam em reais na planilha (formato `R$`) e viram centavos inteiros no sistema.
Erros são listados por aba, coluna e linha (por exemplo
`Lancamentos!Valor (R$) linha 4: valor inválido 'mil reais'`), e uma planilha inválida
**nunca substitui** a que já está na pasta.

## Rodar sobre a planilha

```bash
python -m fin_mas run --scenario fechar_mes --pasta dados/empresa   # pasta com um único .xlsx
python -m fin_mas serve --pasta-dados dados/empresa                 # dashboard: enviar e executar
```

Com a pasta configurada, o sistema faz os pedidos *avaliar orçamento* e *fechar o mês* da
competência da planilha. A proveniência de cada leitura aparece como
`mcp://excel/<arquivo>#<aba>`. Ao aceitar uma correção sugerida pelo AG-CIN, a planilha é
alterada: *estornar* marca a situação, *reaprovar* troca o aprovador e *reclassificar*
ajusta a competência.

## Servidor MCP de Excel

O mesmo leitor validado é exposto como **servidor MCP real** (JSON-RPC 2.0 por stdio,
protocolo `2024-11-05`), para que outro cliente MCP acesse as planilhas da pasta com
segurança:

```bash
python -m fin_mas mcp-excel --pasta dados/empresa
```

```json
{"mcpServers": {"sma-excel": {"command": "python",
  "args": ["-m", "fin_mas", "mcp-excel", "--pasta", "C:/dados/empresa"]}}}
```

| Ferramenta | O que faz |
|---|---|
| `listar_planilhas` | lista os `.xlsx` da pasta e se cada um é um modelo válido |
| `ler_aba` | linhas de uma aba, com proveniência |
| `validar_planilha` | erros de abas, colunas, tipos e referências |
| `resumo_empresa` | porte, norma contábil, alçadas, materialidade e totais do mês |
| `criar_modelo_em_branco` | cria um modelo novo (nunca sobrescreve) |

O servidor só lê arquivos **dentro da pasta** (caminhos com `..` são negados) e nunca
sobrescreve planilhas; a escrita das correções é feita pelo sistema, a partir da decisão
humana. O teste TEST-41 conversa com ele por stdio.

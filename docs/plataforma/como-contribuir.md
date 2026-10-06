# Como contribuir

A documentação segue o modelo *docs-as-code*: tudo vive no repositório GitHub e é
publicado automaticamente no Read the Docs a cada push em `main`.

## Fluxo de trabalho

1. Crie uma branch por tarefa: `git switch -c dsm2/protocolo-delegacao`.
2. **Para alterar modelagem**, edite `models/*.yaml` (nunca os arquivos em `_generated/`).
3. Rode localmente:
   ```bash
   make trace   # valida a cadeia e regenera docs/_generated e entregas/dsm1/generated
   make docs    # sphinx -W (falha com qualquer aviso)
   make pdf     # compila entregas/dsm1/main.tex
   ```
4. Abra um Pull Request. O CI (`.github/workflows/docs.yml`) repete as três etapas e
   confere se os arquivos gerados foram commitados atualizados.
5. A outra pessoa revisa. O Read the Docs pode gerar *preview* do PR (opção
   "Build pull requests" no painel do projeto).

## Convenções

- IDs são estáveis: **nunca reutilize** um ID removido; marque o objeto como obsoleto.
- Cada novo requisito precisa nascer com evidência observável, teste derivado e métrica.
- Itens de entregas futuras entram como stub (`entrega: DSM2`, `status: pendente`).
- Uso de IA em qualquer artefato é registrado em `USO_DE_IA.md`, na seção da entrega.

## Configuração única (feita uma vez)

1. Em readthedocs.org → *Import a Project* → selecionar este repositório GitHub.
2. O arquivo `.readthedocs.yaml` já define Python, Graphviz e as dependências.
3. Em *Settings → Maintainers*, adicionar a segunda pessoa (e no GitHub, como colaboradora).

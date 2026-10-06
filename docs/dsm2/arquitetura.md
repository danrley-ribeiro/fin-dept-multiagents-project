# Arquitetura (pendente)

```{admonition} Pendente — DSM2
:class: warning
Preencher com o diagrama de arquitetura e a justificativa. Ponto de partida: o
[modelo organizacional da DSM1](../dsm1/roles.md).
```

## A preencher

- [ ] Diagrama de arquitetura (camadas: orquestração, agentes, comunicação, governança, configuração, memória)
- [ ] Mapeamento agente/serviço → componente (atualizar `models/components.yaml`)
- [ ] Fluxo de dados MCP e A2A no runtime escolhido
- [ ] Justificativa de cada decisão, ligada a `REQ-*`

## Componentes rastreáveis (stubs)

Estes objetos existem desde a DSM1 apenas para fechar a cadeia Agente/Serviço →
Componente. Na DSM2, cada um ganha caminho real e muda de status.

```{include} ../_generated/components.md
```

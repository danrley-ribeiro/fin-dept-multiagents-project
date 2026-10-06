# Agentes, papéis e responsabilidades

## Organização

O modelo organizacional (Gaia) separa **papéis** (o que precisa ser feito, com quais
direitos e deveres) de **agentes** (entidades operacionais que os assumem) e de
**serviços de plataforma** (capacidades transversais que não precisam de autonomia).

```{mermaid} ../../diagrams/dsm1/organizacao.mmd
```

Cada papel é a tupla didática **role = ⟨Resp, Perm, Obl, Prot⟩**
(responsabilidades, permissões, obrigações e protocolos; Cancian, 2026, §4.3).

## Matriz agente × papel

```{needtable}
:types: agent
:columns: id, title as "Agente", realizes as "Papel", llm as "LLM", pursues as "Objetivos", uses_resource as "Recursos"
:style: table
```

**Política de IA generativa** (ver [ADR-002](ADR-002-llm-opcional-por-flag.md)): `flag` =
opcional e **desligada por padrão**, só para narrativa; `nao_permitido` = o registro
de modelos rejeita qualquer configuração que habilite LLM.

## Papéis

Papéis humanos (`ROLE-SOL`, `ROLE-APR`) ficam fora da fronteira do software, mas
participam de protocolos.

```{include} ../_generated/roles.md
```

## Agentes

```{include} ../_generated/agents.md
```

## Serviços de plataforma (por que não são agentes)

Auditoria, configuração de modelos e memória são **serviços compartilhados**, e não
responsabilidade de cada agente. Isso permite auditar o sistema como um todo e trocar
peças (modelos, agentes, fontes) sem afetar as demais camadas. Também evita a
*agentificação excessiva*: nenhum deles tem objetivo local, iniciativa ou identidade
social própria.

```{include} ../_generated/services.md
```

# Runtime e plataforma

Escolha registrada em duas ADRs, aplicando os critérios de Cancian (2026, §4.6):

- {doc}`ADR-003-runtime-python-deterministico`: Python 3.12 puro, execução em um único fio com relógio lógico, FSMs carregadas de `models/protocols.yaml`.
- {doc}`ADR-004-a2a-bus-e-mcp-mock`: bus A2A em processo, MCP mock de leitura, dataset sintético com seed e gabarito, auditoria JSONL.
- {doc}`ADR-005-execucao-ao-vivo-e-dashboard`: o mesmo bus ritmado em tempo real, servidor local com SSE e dashboard Vite + React.
- {doc}`ADR-006-regras-por-porte-e-planilhas`: base normativa por porte e planilhas como fonte de dados (com servidor MCP de Excel).

| Critério | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.12 | já usada em `tools/trace.py`; stdlib, `pyyaml` e `openpyxl` (planilhas) |
| Concorrência | um fio, relógio lógico | determinismo e testes sem tempo real |
| Comunicação | bus em processo, envelope FIPA-ACL | offline; adaptador A2A real fica para depois |
| Dados | MCP mock + dataset com seed | reprodutibilidade e gabarito |
| Testabilidade | pytest, rede bloqueada | cenários plantados e e2e rápidos |
| Interface | Vite + React + MUI, servida pelo próprio Python | offline; replay sem servidor |
| Custo | zero | sem API paga; LLM adiado (ADR-002) |

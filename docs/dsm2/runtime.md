# Runtime e plataforma

Escolha registrada em duas ADRs, aplicando os critérios de Cancian (2026, §4.6):

- {doc}`ADR-003-runtime-python-deterministico`: Python 3.12 puro, execução em um único fio com relógio lógico, FSMs carregadas de `models/protocols.yaml`.
- {doc}`ADR-004-a2a-bus-e-mcp-mock`: bus A2A em processo, MCP mock de leitura, dataset sintético com seed e gabarito, auditoria JSONL.

| Critério | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.12 | já usada em `tools/trace.py`; stdlib e `pyyaml` bastam |
| Concorrência | um fio, relógio lógico | determinismo e testes sem tempo real |
| Comunicação | bus em processo, envelope FIPA-ACL | offline; adaptador A2A real fica para depois |
| Dados | MCP mock + dataset com seed | reprodutibilidade e gabarito |
| Testabilidade | pytest, rede bloqueada | cenários plantados e e2e rápidos |
| Custo | zero | sem API paga; LLM adiado (ADR-002) |

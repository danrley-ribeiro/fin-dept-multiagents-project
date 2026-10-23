# ADR-003 — Runtime: Python puro com scheduler determinístico

- **Status:** aceita (DSM2, 23/10/2026)
- **Requisitos:** {need}`REQ-NF01`, {need}`REQ-F01`, {need}`REQ-S02`, {need}`REQ-O01`
- **Protocolos:** {need}`PROT-DEL`, {need}`PROT-QRY`, {need}`PROT-LCK`

## Contexto

O ambiente da DSM1 é discreto, com relógio lógico, e o núcleo deve rodar offline, sem API
paga e com resultado reprodutível por seed ({need}`REQ-NF01`). Prazos (`reply_by`), TTL de
reserva e falhas de especialista precisam ser testáveis sem esperar tempo real. Os
critérios de escolha seguem Cancian (2026, §4.6): linguagem, concorrência, semântica de
comunicação, suporte BDI, testabilidade offline, maturidade e custo.

## Alternativas

| Critério | Python puro + scheduler próprio | SPADE (XMPP) | Frameworks de orquestração de LLM |
|---|---|---|---|
| Determinismo e relógio lógico | **total** (fila ordenada por tempo lógico e sequência) | baixo (I/O e servidor XMPP) | baixo |
| Offline e sem serviço externo | **sim** | exige servidor XMPP | depende do provedor |
| Semântica de mensagens (FIPA-ACL, `conversation_id`) | **implementada sobre o YAML dos protocolos** | nativa | ad hoc |
| Testabilidade (pytest, falhas plantadas) | **alta** | média | média |
| Custo e dependências | **stdlib + pyyaml** | maior | maior |

## Decisão

1. **Python 3.12**, biblioteca padrão e `pyyaml` (já usada por `tools/trace.py`); `pytest` apenas em desenvolvimento.
2. **Execução em um único fio** com **relógio lógico**: o bus entrega mensagens em ordem
   (tempo lógico, sequência) e dispara `timeout` quando `reply_by` é ultrapassado. Não há
   `sleep` nem threads, então o mesmo seed produz a mesma sequência de mensagens.
3. Cada agente é um objeto com **estado**, **conhecimento** e **memória** em atributos
   separados ({need}`AG-ORQ`, {need}`AG-CUS`, {need}`AG-ORC`, {need}`AG-RES`, {need}`AG-CIN`, {need}`AG-REL`), reagindo a mensagens (`on_message`).
4. As máquinas de estado dos protocolos **não são codificadas à mão**: são carregadas de
   `models/protocols.yaml`, que continua a fonte única (transição inválida → `ProtocolViolation`).

## Consequências

- (+) Reprodutibilidade por construção; testes e2e rápidos e sem rede.
- (+) O código reflete os modelos da DSM1, sem duplicar as FSMs.
- (−) Sem concorrência real nem distribuição entre processos: a escala e a latência de rede não são avaliadas.
- (−) Semântica FIPA-ACL parcial (apenas os performativos usados pelos protocolos).
- Evolução: se a DSM3/DSM4 exigir processos distintos, o bus pode ganhar outro transporte sem alterar os agentes ({doc}`ADR-004-a2a-bus-e-mcp-mock`).

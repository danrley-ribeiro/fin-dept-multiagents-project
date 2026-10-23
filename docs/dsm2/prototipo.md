# Protótipo inicial

Protótipo executável em Python 3.12 (`src/fin_mas/`), offline e determinístico
({doc}`ADR-003-runtime-python-deterministico`).

## Como executar

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt   # Windows: .venv\Scripts\
python -m fin_mas list
python -m fin_mas run --scenario fechar_mes --seed 42
python -m fin_mas run --scenario depuracao --trace trace.jsonl
python -m fin_mas replay trace.jsonl SOL-001
python -m pytest
```

Sem instalar o pacote, use `PYTHONPATH=src` antes dos comandos `python -m fin_mas`.

## Interação demonstrada

"Fechar o mês" (`fechar_mes`, seed 42) percorre os seis protocolos da DSM1 sobre o bus:

1. `PROT-SOL`: o solicitante pede; o Orquestrador responde `agree`.
2. `PROT-LCK`: o Orquestrador reserva (entidade, competência).
3. `PROT-DEL`: Custos e Orçamento recebem `request` em paralelo e respondem `agree` e `inform`.
4. `PROT-DEL` + `PROT-QRY`: Resultados recebe a delegação e faz `query-ref` a Custos e a Orçamento antes do seu `inform`.
5. `PROT-CMP`: Controles Internos emite `conforme`, `nao_conforme_nao_critico` ou `veto`.
6. `PROT-DEL`: Relatórios gera o relatório por template; o Orquestrador responde `inform` e libera a reserva.

## Cenários

| Cenário | O que mostra |
|---|---|
| `fechar_mes` | caminho feliz; resultado igual ao gabarito |
| `avaliar_orcamento` | dois desvios plantados sinalizados; o chamariz (+12% em base pequena) não |
| `veto_waiver` | alçada violada, veto, waiver humano e publicação com ressalva |
| `veto_bloqueio` | alçada violada sem waiver: `BLOQUEADO`, nada publicado, reserva liberada |
| `falha_especialista` | AG-CUS expira duas vezes: um reenvio e depois `failure` |
| `depuracao` | seed 1337 com perda de mensagem, SoD, competência errada e waiver |

## Cenário controlado de depuração

O cenário `depuracao` é montado para ser investigado a partir do trace, sem ler o código:

- **seed 1337**: o mesmo dataset sempre; o gabarito vem do que foi plantado;
- **perda** do primeiro `request` ao AG-ORC (`DEL-002`): expira em `t=031`, o Orquestrador reenvia (`DEL-003`);
- **SoD** crítico (L-013) e **competência** fora do período (L-014): o AG-CIN emite `veto`;
- **waiver humano**: `CMP-001` vai `VETADO -> LIBERADO_COM_RESSALVA -> LIBERADO` e o relatório sai com duas ressalvas.

`python -m fin_mas run --scenario depuracao --trace t.jsonl` grava o trace; `replay t.jsonl SOL-001`
reconstrói a sequência causal pelo `conversation_id`, com as subconversas ligadas por registros `link`.

## Estado, conhecimento e memória no código

| Agente | `estado` (muda) | `conhecimento` (regras) | `memoria` |
|---|---|---|---|
| {need}`AG-ORQ` | solicitações, DAG, tentativas, reservas | catálogo de intenções, prazo, máximo de tentativas | reservada (DSM3) |
| {need}`AG-CUS` | custos apurados, pendências | critério e versão do rateio | reservada |
| {need}`AG-ORC` | avaliação do período | limiares (10% e R$ 5.000) e método de forecast | reservada |
| {need}`AG-RES` | consolidações e consultas em andamento | estrutura da DRE | reservada |
| {need}`AG-CIN` | crenças por lançamento e intenção (aprovar, apontar, vetar) | regras de alçada, SoD, duplicidade e competência | reservada |
| {need}`AG-REL` | rascunho do relatório | template e versão (`tpl-exec-v1`) | reservada |

## Mapa de componentes

| Componente | Caminho |
|---|---|
| {need}`COMP-ORQ`, {need}`COMP-CUS`, {need}`COMP-ORC`, {need}`COMP-RES`, {need}`COMP-CIN`, {need}`COMP-REL` | `src/fin_mas/agents/` |
| {need}`COMP-A2A` | `src/fin_mas/core/` (`bus.py`, `fsm.py`, `message.py`, `agent.py`) |
| {need}`COMP-MCP` | `src/fin_mas/mcp/gateway.py` sobre `src/fin_mas/env/dataset.py` |
| {need}`COMP-AUD`, {need}`COMP-LCK` | `src/fin_mas/services/` |

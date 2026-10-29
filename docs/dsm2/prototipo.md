# Protótipo

Protótipo executável em Python 3.12 (`src/fin_mas/`), offline e determinístico
({doc}`ADR-003-runtime-python-deterministico`).

## Como executar

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt   # Windows: .venv\Scripts\
python -m fin_mas list                                        # cenários
python -m fin_mas run --scenario fechar_mes --seed 42         # trilha causal + resultado
python -m fin_mas run --scenario fechar_mes --porte micro     # regras de outro porte
python -m fin_mas run --scenario depuracao --trace trace.jsonl && python -m fin_mas replay trace.jsonl SOL-001
python -m fin_mas comparar --seeds 10                         # SMA x workflow centralizado
python -m fin_mas relatorio --scenario veto_correcao          # relatório HTML com o logo da SMA
python -m fin_mas modelos --out modelos                       # planilhas modelo (empresa sem ERP)
python -m fin_mas serve                                       # escritório ao vivo (dashboard)
python -m pytest                                              # testes e2e e de integração
```

Sem instalar o pacote, use `PYTHONPATH=src` antes dos comandos `python -m fin_mas`.

## Interação demonstrada

"Fechar o mês" (`fechar_mes`) percorre os protocolos da DSM1 sobre o bus:

1. `PROT-SOL`: o solicitante pede; o Orquestrador responde `agree`.
2. `PROT-LCK`: o Orquestrador reserva (entidade, competência).
3. `PROT-DEL`: Custos e Orçamento recebem `request` em paralelo. O AG-ORC percebe o porte
   (`normas.perfil`), as duas fontes do realizado e, se precisar, consulta o AG-CIN por `PROT-QRY`.
4. `PROT-DEL` + `PROT-QRY`: Resultados consulta Custos e Orçamento antes do seu `inform`.
5. `PROT-CMP`: Controles Internos delibera entre aprovar, apontar, vetar com correção ou vetar;
   o veto vai ao aprovador humano, e correção, waiver ou prazo voltam ao AG-CIN.
6. `PROT-DEL`: Relatórios gera o relatório (cabeçalho da SMA); o Orquestrador responde
   `inform` e libera a reserva.

## Cenários

| Cenário | O que mostra |
|---|---|
| `fechar_mes` | caminho feliz; resultado igual ao gabarito |
| `avaliar_orcamento` | desvios plantados sinalizados após consulta do AG-ORC ao AG-CIN; o chamariz não é sinalizado |
| `veto_waiver` | alçada violada, veto com correção oferecida, waiver humano, publicação com ressalva |
| `veto_bloqueio` | alçada violada, ninguém decide: `BLOQUEADO`, nada publicado |
| `veto_correcao` | veto com correção sugerida; humano reaprova; AG-CIN reavalia e aprova |
| `correcao_parcial` | correção de só uma crítica; AG-CIN mantém o veto; prazo esgota |
| `divergencia_fonte` | planilha diverge do ERP; AG-ORC adota o ERP e registra ressalva |
| `desvio_irregular` | NF duplicada infla uma conta; AG-ORC reclassifica como problema de controle; AG-CIN sugere estorno |
| `orc_sem_cin` | a consulta ao AG-CIN se perde; timeout e replanejamento do AG-ORC |
| `falha_especialista` | AG-CUS expira duas vezes: um reenvio e depois `failure` |
| `depuracao` | seed 1337 com perda de mensagem, SoD, competência errada e waiver |
| `expediente_sma` | três competências, pedidos concorrentes, vetos, correções e divergências (dados mock da SMA) |
| `fechamento_micro` / `_pequena` / `_grande` | regras do porte ({doc}`portes`) |

## Cenário controlado de depuração

`depuracao` é montado para ser investigado a partir do trace, sem ler o código: seed 1337,
perda do primeiro `request` ao AG-ORC (`DEL-002`, expira em `t=031`, reenvio em `DEL-003`),
SoD crítico e competência fora do período, waiver humano. `replay trace.jsonl SOL-001`
reconstrói a sequência causal pelo `conversation_id`, agora com as linhas `CRENCA`,
`DESEJO`, `DELIBERA` e `INTENCAO` dos agentes BDI.

## Estado, conhecimento e crenças no código

| Agente | `estado` | `conhecimento` | crenças BDI |
|---|---|---|---|
| {need}`AG-ORQ` | solicitações, DAG, tentativas, reservas | catálogo de intenções, prazo, máximo de tentativas e de correções | — |
| {need}`AG-CUS` | custos apurados por competência | critério e versão do rateio | — |
| {need}`AG-ORC` | tarefas por competência e avaliação | limiares, fonte primária e norma do porte | orçado/realizado por fonte, contestado, classificação, porte |
| {need}`AG-RES` | consolidações e consultas | estrutura da DRE | — |
| {need}`AG-CIN` | pareceres, alçadas e severidades percebidas | regras, correção por regra, ciclos do porte | lançamentos e violações, waivers, ciclos de correção, porte |
| {need}`AG-REL` | rascunho | template `tpl-exec-v2` (cabeçalho da SMA) | — |

## Mapa de componentes

| Componente | Caminho |
|---|---|
| {need}`COMP-ORQ`, {need}`COMP-CUS`, {need}`COMP-ORC`, {need}`COMP-RES`, {need}`COMP-CIN`, {need}`COMP-REL` | `src/fin_mas/agents/` |
| {need}`COMP-BDI` | `src/fin_mas/core/bdi.py` |
| {need}`COMP-A2A` | `src/fin_mas/core/` (`bus.py`, `fsm.py`, `message.py`, `agent.py`) |
| {need}`COMP-MCP` | `src/fin_mas/mcp/gateway.py` sobre `env/dataset.py` (por porte) ou `fontes/planilha.py` |
| {need}`COMP-XLS` | `src/fin_mas/mcp/excel_server.py`, `src/fin_mas/fontes/planilha.py` |
| {need}`COMP-AUD`, {need}`COMP-LCK` | `src/fin_mas/services/` |
| {need}`COMP-OBS` | `src/fin_mas/live.py`, `server.py`, `web/` |
| baseline, métricas e experimento | `src/fin_mas/baseline.py`, `metricas.py`, `experimentos.py` |

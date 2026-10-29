# DSM2 — Arquitetura e protótipo inicial (revisada após o feedback)

**Projeto:** Sistema Multiagente de Controladoria da **SMA S.A.** (empresa fictícia) — INE5628 Sistemas Multiagentes.
**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).
Enunciado: [`enunciados/DSM2.txt`](../../enunciados/DSM2.txt).

Protótipo executável do Orquestrador e de cinco especialistas sobre um barramento A2A em processo, com
**dois agentes cognitivos BDI** (Orçamento e Controles Internos), **decisões distribuídas** entre eles,
**comparação com o workflow centralizado** da DSM1, regras por **porte de empresa** (micro a grande),
suporte a **empresas sem ERP** (modelos Excel e servidor MCP de Excel) e um **dashboard** em que os agentes
aparecem trabalhando num escritório. O que mudou depois do feedback está em
[`docs/dsm2/revisao.md`](../../docs/dsm2/revisao.md).

## Como executar

**Um comando** (prepara Python, `.venv`, bun, dependências, build e traces; detalhes no
[README da raiz](../../README.md#um-comando)):

```bash
.\iniciar.ps1              # Windows — escritório ao vivo em http://127.0.0.1:8765
./iniciar.sh               # Linux/macOS
.\iniciar.ps1 testes       # todos os testes; outros modos: replay, dev, docs, cli, instalar
```

Passo a passo manual (requer Python 3.12+ e [bun](https://bun.sh); npm também funciona). Nada usa a
internet em tempo de execução.

```bash
python -m venv .venv
.venv/bin/pip install -e . -r requirements-dev.txt          # Windows: .venv\Scripts\pip
.venv/bin/python -m fin_mas list                             # cenários
.venv/bin/python -m fin_mas run --scenario desvio_irregular  # trilha com crenças, desejos, deliberações e intenções
.venv/bin/python -m fin_mas run --scenario fechar_mes --porte micro
.venv/bin/python -m fin_mas comparar --seeds 10              # SMA x workflow centralizado
.venv/bin/python -m pytest                                   # testes e2e e de integração (offline)

cd web && bun install && bun run build && cd ..             # ou: npm install && npm run build
.venv/bin/python -m fin_mas serve                            # http://127.0.0.1:8765 — escritório ao vivo
cd web && bun run test:e2e                                   # testes de uso real (Chrome + servidor Python)
```

Empresa sem ERP: `python -m fin_mas modelos --out modelos`, preencha a planilha e rode
`python -m fin_mas run --scenario fechar_mes --pasta <pasta>`, ou envie-a pelo dashboard (**Dados da empresa**).

### Cenário controlado de depuração

```bash
python -m fin_mas run --scenario depuracao --trace trace.jsonl   # seed 1337
python -m fin_mas replay trace.jsonl SOL-001                     # reconstrói a causalidade pelo conversation_id
```

Perda do primeiro `request` ao AG-ORC (`DEL-002`), timeout em `t=031`, reenvio (`DEL-003`), veto do AG-CIN,
aviso ao aprovador, waiver, publicação com duas ressalvas e `inform` final. Mesmo seed, mesmo hash.

## Arquitetura

Fonte editável: [`modelos-editaveis/arquitetura_camadas.mmd`](modelos-editaveis/arquitetura_camadas.mmd); também:
[`ciclo_bdi.mmd`](modelos-editaveis/ciclo_bdi.mmd), [`sequencia_orc_cin.mmd`](modelos-editaveis/sequencia_orc_cin.mmd) e
[`sequencia_veto_correcao.mmd`](modelos-editaveis/sequencia_veto_correcao.mmd) (renderizados na documentação).
Decisões: ADR-003 (runtime), ADR-004 (A2A e MCP mock), ADR-005 (execução ao vivo e dashboard),
ADR-006 (regras por porte e planilhas), em [`docs/dsm2/`](../../docs/dsm2/).

| Camada | Código | Componente |
|---|---|---|
| Orquestração | `src/fin_mas/agents/orq.py` | `COMP-ORQ` |
| Especialistas (ORC e CIN são BDI) | `agents/cus.py`, `orc.py`, `res.py`, `cin.py`, `rel.py` | `COMP-CUS`, `COMP-ORC`, `COMP-RES`, `COMP-CIN`, `COMP-REL` |
| Cognição | `core/bdi.py` | `COMP-BDI` |
| Comunicação (A2A) | `core/bus.py`, `fsm.py`, `message.py`, `agent.py` | `COMP-A2A` |
| Instrumental (MCP, Excel, normas por porte) | `mcp/gateway.py`, `mcp/excel_server.py`, `fontes/planilha.py`, `env/` | `COMP-MCP`, `COMP-XLS` |
| Governança e coordenação | `services/audit.py`, `services/locks.py` | `COMP-AUD`, `COMP-LCK` |
| Observabilidade | `live.py`, `server.py`, `web/` | `COMP-OBS` |
| Baseline, métricas, experimento | `baseline.py`, `metricas.py`, `experimentos.py` | — |

## Testes

- `python -m pytest`: e2e (cenários sobre o bus, verificados pelo trace e pelo gabarito) e integração
  (simulação ao vivo + servidor HTTP em loopback, planilhas reais, servidor MCP de Excel por stdio, exportação).
- `cd web && bun run test:e2e`: 14 testes de uso real no Chrome sobre o servidor Python verdadeiro
  (`bun run test` roda os testes do reducer).
- `tools/trace.py --check` liga cada `TEST-*` executado ao teste homônimo (pytest ou Playwright).

Detalhes em [`docs/dsm2/testes.md`](../../docs/dsm2/testes.md).

## Checklist do enunciado

| Entregável | Onde |
|---|---|
| Código-fonte executável | `src/fin_mas/`, `web/` |
| Diagrama de arquitetura | `modelos-editaveis/arquitetura_camadas.mmd` (e a imagem da v1 em `diagramas/`) |
| README.md | este arquivo |
| Testes iniciais | `tests/`, `web/e2e/`, `docs/dsm2/testes.md` |
| USO_DE_IA.md | [`USO_DE_IA.md`](USO_DE_IA.md) |

| Requisito | Onde |
|---|---|
| Justificar arquitetura e runtime | ADR-003 a ADR-006, `docs/dsm2/arquitetura.md` |
| Agentes principais e ambiente | seis agentes (dois BDI), bus, MCP, empresa SMA simulada por porte ou planilha real |
| Estado/conhecimento e comportamento básico | estado, conhecimento e crenças por agente; `docs/dsm2/cognicao.md` |
| Ao menos uma interação | `fechar_mes` (PROT-SOL, LCK, DEL, QRY, CMP); consulta ORC→CIN; veto com correção |
| Cenário controlado para depuração | `depuracao` (seed 1337) |
| Limitações | [`docs/dsm2/limitacoes.md`](../../docs/dsm2/limitacoes.md) |

Checkpoints CP1–CP13: [`docs/checkpoints.md`](../../docs/checkpoints.md). Documentação navegável:
<https://fin-dept-multiagents-project.readthedocs.io>.

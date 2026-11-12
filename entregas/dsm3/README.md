# DSM3 — Comunicação, coordenação e protótipo funcional

**Projeto:** Sistema Multiagente de Controladoria da **SMA** (empresa fictícia) — INE5628 Sistemas Multiagentes.
**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).
Enunciado: [`enunciados/DSM3.txt`](../../enunciados/DSM3.txt).

A DSM3 corrige as falhas de autorização e validação apontadas no feedback da DSM2 e conclui as
funcionalidades previstas. Agora o barramento valida **remetente, destinatário, papel,
conversa, performativo e esquema** antes de mudar qualquer estado. As decisões humanas passam
por um **Approval Gate** formal (PROT-APR): cada uma fica vinculada à solicitação, ao veto
(hash), ao aprovador e a um prazo, é de uso único e segue uma política explícita (POL-01 a
POL-08). Há também **memória persistente** só de decisões aprovadas, **redaction** fail-closed
com trace com cadeia de hashes e selo HMAC e **LLM opcional** do AG-REL, sempre offline nos testes. A
resposta a cada ponto do feedback está em
[`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md).

## Conteúdo da entrega

| Exigido pelo enunciado | Onde |
|---|---|
| Comunicação com conteúdo e finalidade claros | [`docs/dsm3/protocolos.md`](../../docs/dsm3/protocolos.md); `models/protocols.yaml` (emissores, eventos locais, esquemas) |
| Protocolo de interação documentado | seis FSMs + [`modelos-editaveis/`](modelos-editaveis/) (validação, FSM e sequência do PROT-APR) |
| Coordenação, negociação, cooperação ou planejamento | [`docs/dsm3/coordenacao.md`](../../docs/dsm3/coordenacao.md) |
| Tratamento de conflito, falha ou alternativa | [`docs/dsm3/seguranca.md`](../../docs/dsm3/seguranca.md); reenvio, replanejamento, prazo, negação, reincidência |
| Testes integrados ou cenários automatizados | `codigo/tests/` (247 testes) e `codigo/web/e2e/`; [`docs/dsm3/testes.md`](../../docs/dsm3/testes.md) |
| Evidências de comportamento coletivo | traces dos cenários, `docs/dsm3/resultados/` (10 seeds), cenário `ataque_decisao_forjada` |
| Autoria e uso de IA | este arquivo e [`USO_DE_IA.md`](USO_DE_IA.md) |

**Pacote para envio:** `python tools/empacotar_dsm3.py` (ou `make entrega-dsm3`) gera
`entregas/dsm3/DSM3-entrega.zip`, com esta pasta e uma cópia do código em `codigo/`.

## Como executar

Requer Python 3.11+. Nada usa a internet em tempo de execução. Para o dashboard, use o
comando único descrito no [README da raiz](../../README.md#um-comando).

```bash
python -m venv .venv
.venv/bin/pip install -e . -r requirements-dev.txt            # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest                                     # 247 testes, offline
.venv/bin/python tools/trace.py --check                        # rastreabilidade: 0 erros
```

### Roteiro de demonstração (5 comandos)

```bash
python -m fin_mas run --scenario ataque_decisao_forjada --trace ataque.jsonl
#   14 ataques (os 4 do feedback e outros 10 da mesma família): 0 aceitos; trilha com REJEITADA [etapa] motivo;
#   o ticket APR-001 expira e o fechamento termina bloqueado, sem publicar
python -m fin_mas verificar ataque.jsonl --ancora 3107d1dd721e2c1517e2c476b285d5a7f072b05be3af3c981b935154b0e1d931
#   a âncora (hash final da cadeia) é reproduzível: confere em qualquer máquina, sem a chave do autor;
#   altere, remova ou corte uma linha e o comando acusa (saída 3)
python -m fin_mas run --scenario veto_correcao
#   veto -> ticket APR-001 -> approve (corrigir) -> erp.corrigir com a aprovação -> AG-CIN reavalia -> publicado
python -m fin_mas run --scenario reincidencia_waiver --memoria memoria.json
#   waiver em agosto vira memória; em setembro o AG-CIN cita MEM-0001, a política (POL-06) nega novo waiver
python -m fin_mas run --scenario fechar_mes --llm mock-narrador
#   síntese por LLM (mock offline) conferida contra os números do template; mock-alucina cai no template
```

## Feedback da DSM2 → correção

| Falha relatada | Agora | Teste |
|---|---|---|
| `decisao_humana` de remetente inexistente liberou o fechamento vetado | remetente precisa estar registrado e ter credencial; o canal livre acabou; a decisão só vale pelo PROT-APR, validada pelo SVC-POL | `test_forged_human_decision_from_unknown_sender_is_rejected` |
| transição local por identificador não autorizado | `advance` exige credencial, participação e papel autorizado em `eventos_locais` | `test_local_transition_by_unauthorized_identity_is_rejected` |
| resposta a quem não participava da conversa | destinatário tem de ser a contraparte e ter papel participante | `test_reply_to_non_participant_receiver_is_rejected` |
| `KeyError` por campo obrigatório ausente | esquema por performativo; erro de agente isolado e respondido | `test_malformed_request_does_not_crash_simulation` |
| suíte não detectava as violações | 90 testes novos (falsificação, duplicidade, atraso, reutilização, papel, SoD, adulteração) | `docs/dsm3/testes.md` |
| baseline sem veto/correção | ressalva registrada; workflow equivalente planejado para a DSM4 | `docs/dsm3/limitacoes.md` |

## Componentes novos

| Código | Componente | Papel |
|---|---|---|
| `core/bus.py`, `core/schema.py`, `core/diretorio.py`, `core/agent.py` | `COMP-A2A`, `COMP-SCH` | autenticação, papel, contraparte, esquema, integridade, isolamento de erros |
| `services/politica.py` | `COMP-POL` (SVC-POL) | tickets do Approval Gate e política POL-01..08 |
| `services/memoria.py` | `COMP-MEM` (SVC-MEM) | memória aprovada, persistente, com retenção e pseudônimos |
| `services/redacao.py`, `services/audit.py` | `COMP-RED` | redaction fail-closed e JSONL com hash encadeado |
| `services/modelos.py` | `COMP-MOD` (SVC-MOD) | LLM opcional do AG-REL com validação numérica, cota e logs |
| `env/ataques.py` | — | ataques do cenário adversarial |

Decisão de arquitetura: [ADR-007](../../docs/dsm3/ADR-007-autenticidade-e-approval-gate.md).
Limitações e plano da DSM4: [`docs/dsm3/limitacoes.md`](../../docs/dsm3/limitacoes.md).

## Estrutura da pasta

```
entregas/dsm3/
  README.md            este arquivo
  USO_DE_IA.md         uso de IA no desenvolvimento da entrega
  modelos-editaveis/   3 diagramas Mermaid (.mmd): pipeline de validação, FSM e sequência do PROT-APR
  diagramas/           3 imagens (.png), uma por .mmd
  DSM3-entrega.zip     pacote para envio (gerado por tools/empacotar_dsm3.py; não versionado)
```

| Diagrama | Imagem | Fonte editável |
|---|---|---|
| Pipeline de validação do barramento | [`diagramas/pipeline_validacao.png`](diagramas/pipeline_validacao.png) | [`pipeline_validacao.mmd`](modelos-editaveis/pipeline_validacao.mmd) |
| FSM do Approval Gate (PROT-APR) | [`diagramas/fsm_prot_apr.png`](diagramas/fsm_prot_apr.png) | [`fsm_prot_apr.mmd`](modelos-editaveis/fsm_prot_apr.mmd) |
| Sequência veto → aprovação → correção | [`diagramas/sequencia_approval_gate.png`](diagramas/sequencia_approval_gate.png) | [`sequencia_approval_gate.mmd`](modelos-editaveis/sequencia_approval_gate.mmd) |

Para regenerar uma imagem: `npx @mermaid-js/mermaid-cli -i modelos-editaveis/<arquivo>.mmd -o diagramas/<arquivo>.png -b white -s 2`.

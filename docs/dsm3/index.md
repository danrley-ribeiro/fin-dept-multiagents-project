# DSM3 — Comunicação, coordenação e protótipo funcional

<span class="badge-ok">concluída</span> · prazo: 18/11/2026

A DSM3 consolida a **segurança e a robustez das interações** apontadas no feedback da DSM2 e
conclui as funcionalidades que estavam previstas: barramento que valida remetente,
destinatário, papel, conversa, performativo e esquema; **Approval Gate** formal (PROT-APR) com
política de aprovação explícita; **memória persistente** aprovada (SVC-MEM); **proteção de
informações** (redaction fail-closed, pseudônimos, trace com hash encadeado); **LLM opcional**
do AG-REL com validação numérica, sempre offline nos testes. O que mudou em resposta ao
feedback, ponto a ponto, está em {doc}`revisao`.

## Enunciado e onde está cada critério

| Critério | Peso | Página |
|---|---|---|
| Comunicação e protocolos | 25% | {doc}`protocolos` (envelope, validação, papéis, esquemas, PROT-APR) · ADR-007 |
| Coordenação coletiva | 25% | {doc}`coordenacao` (delegação, consulta direta, veto→aprovação→correção, reserva, memória entre ciclos) |
| Corretude e robustez | 25% | {doc}`seguranca` (14 ataques rejeitados, política POL-01..08, isolamento de erros) |
| Testes e evidências | 15% | {doc}`testes` · `docs/dsm3/resultados/` · cenário `ataque_decisao_forjada` |
| Documentação e autoria | 10% | `entregas/dsm3/README.md` · `entregas/dsm3/USO_DE_IA.md` · {doc}`limitacoes` |

| Requisito do enunciado | Evidência |
|---|---|
| Comunicação com conteúdo e finalidade claros | performativos FIPA por protocolo com esquema de conteúdo validado (`models/protocols.yaml`, `core/schema.py`) |
| Protocolo de interação documentado | seis FSMs com transições válidas e inválidas, emissores e eventos locais; diagramas em `entregas/dsm3/modelos-editaveis/` |
| Coordenação, negociação, cooperação ou planejamento | DAG do Orquestrador, consulta ORC↔CIN, ciclo veto→aprovação→correção→reavaliação, exclusão mútua de período |
| Tratamento de conflito, falha ou alternativa | reenvio e falha explícita, replanejamento BDI, prazo do ticket, decisão negada pela política, reincidência |
| Testes integrados ou cenários automatizados | 232 testes pytest (75 novos) + Playwright; 17 cenários nomeados |
| Evidências de comportamento coletivo | traces JSONL com crenças, intenções, decisões, rejeições e tickets; comparação em 10 seeds |

## Como reproduzir em dois minutos

```bash
python -m fin_mas run --scenario ataque_decisao_forjada     # 14 ataques, 0 aceitos, nada publicado
python -m fin_mas run --scenario reincidencia_waiver         # memória entre meses + POL-06
python -m fin_mas run --scenario veto_correcao --trace t.jsonl && python -m fin_mas verificar t.jsonl
python -m fin_mas run --scenario fechar_mes --llm mock-narrador   # síntese por LLM validada (offline)
python -m pytest                                              # 232 testes
```

```{toctree}
:maxdepth: 1

revisao
protocolos
coordenacao
seguranca
memoria
llm
testes
limitacoes
ADR-007-autenticidade-e-approval-gate
```

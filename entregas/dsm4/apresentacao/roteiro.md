# Roteiro do vídeo — DSM4

A apresentação final é um **vídeo de 15 a 30 minutos** que substitui a apresentação presencial. O professor
pediu foco no **código-fonte e nos testes**: o vídeo passa a maior parte do tempo no editor e no terminal,
e os slides só abrem e amarram cada parte. **Duração-alvo:** cerca de 28 minutos, com 2 de folga até o limite de 30. **Quem fala:** Danrley (D) e
Jiliard (J), os dois explicando arquitetura e segurança no próprio código.
**Tom:** mostrar como o sistema funciona por dentro e dizer o que o experimento mostrou, inclusive o
que é desfavorável a nós.

**Slides:** [`DSM4-apresentacao.pptx`](DSM4-apresentacao.pptx), gerado de [`slides.md`](slides.md) por
`make apresentacao-dsm4`. As falas resumidas também estão nas notas do apresentador. A versão longa da
demonstração, com plano B, está em [`docs/dsm4/demonstracao.md`](../../../docs/dsm4/demonstracao.md).

## O que o vídeo cobre

| Pedido | Onde |
|---|---|
| Código-fonte em detalhe (aviso do professor) | Parte 2, de 3:00 a 14:00: barramento, protocolos, Approval Gate, POL-06 e trava, acesso, agentes BDI, negociação, workflow equivalente |
| Testes em detalhe (aviso do professor) | Parte 3, de 14:00 a 19:00: organização, rastreabilidade, testes da POL-06, testes negativos de protocolo, equivalência, suíte a partir do ZIP |
| Negociação de prazo | Parte 2 (código do `_negociar_prazo`) e Parte 4, demo 1 |
| Hipótese confirmada ou refutada por outro agente | Parte 2 (código do AG-ORC) e Parte 4, demos 2 e 3 |
| Fechamento bloqueado por irregularidade | Parte 4, demo 4 (prazo esgotado, POL-08) e demo 7 (o controller bloqueia setembro, com o waiver negado pela POL-06) |
| Aprovação indevida rejeitada | Parte 4, demos 5 e 6 (14 ataques recusados; a gerente envolvida no dashboard) |
| POL-06 com fechamentos simultâneos (feedback da DSM3) | Parte 2 (código), Parte 3 (TEST-424, 459, 470, 471) e Parte 4, demo 7 ao vivo no dashboard |
| Memória entre execuções, operar × aprovar, suíte do ZIP | Parte 2 (trava e memória), Parte 3 (suíte sem Git) e slide "Revisão final" |
| Experimento: baseline equivalente, fatores, seeds, variabilidade | Parte 5 |
| Os dois autores explicam arquitetura e segurança | Partes 1 e 2, divididas entre D e J |

## Preparar a gravação (fora do tempo)

- Gravar a tela em 1920×1080, com fonte de 16 pt ou mais no editor e no terminal e tema claro. Fechar
  notificações. No editor, deixar abertas as abas da Parte 2 na ordem do roteiro, com as funções já
  localizadas (Ctrl+G para a linha). Gravar parte por parte e juntar na edição. Na Parte 5, mostrar também as tabelas
  geradas (`docs/dsm4/resultados/resumo.md` e `bloco_e/resumo.md`, com média ± desvio-padrão e IC).
- Cada um se apresenta na primeira fala e fala na sua voz nas partes indicadas.
- Ensaiar com cronômetro. Se passar de 30 minutos, encurtar a Parte 5, nunca as Partes 2 e 3. Na Parte 2, cada autor explica o mecanismo com as próprias palavras antes de mostrar o código (D: trava, selo e por que o waiver é gravado antes de a decisão chegar ao Orquestrador; J: a ordem de validação do `Bus.send`), não lê o slide.
- Exportar em MP4 (H.264) e publicar como link não listado; o link vai no `README.md` da entrega.

Terminal, na raiz do repositório (Linux/macOS):

```bash
source .venv/bin/activate && export PYTHONPATH=src
export FIN_MAS_DIR_CHAVES=/tmp/sma-chaves
python -m fin_mas cenarios --verificar            # aquecimento, todos "ok" e "sim"
```

No Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"; $env:PYTHONIOENCODING = "utf-8"
$env:FIN_MAS_DIR_CHAVES = "$env:TEMP\sma-chaves"
python -m fin_mas cenarios --verificar
```

Segundo terminal, com pastas novas de dados e de acesso. A primeira começa com a memória vazia e a segunda
recebe os papéis atuais da demonstração. Cadastros existentes preservam os papéis gravados: `python -m fin_mas serve --demo --pasta-dados saidas/video/dados
--acesso saidas/video/acesso`, e o navegador em `http://127.0.0.1:8765`. Todas as contas usam a senha
`Demonstracao-SMA-2026`. Deixar abertas janelas anônimas para `operador`, `controller`, `carla` e
`diego`. Para regravar a demo 7, suba o servidor de novo com outra pasta de dados.

## Parte 1 — O problema e a arquitetura (0:00 a 3:00, slides 1 a 4)

| Slide | Quem | Tempo | O que dizer |
|---|---|---|---|
| 1. Capa | D + J | 0:30 | Cada um se apresenta. O vídeo mostra o código e os testes, depois as demonstrações e o experimento. |
| 2. O problema | D | 0:30 | Fechar o mês com fontes que divergem, regras por porte e decisão humana. A pergunta da DSM4: com as mesmas funções, agentes valem a pena? |
| 3. Arquitetura final | D | 1:00 | Camadas de cima até o barramento. Quem calcula não aprova, o AG-CIN veta sozinho e a decisão humana tem dono. BDI onde há escolha sob incerteza (ADR-010). |
| 4. Mapa do código | J | 1:00 | Onde está cada coisa em `src/fin_mas/`: `core/` (barramento, FSM, BDI), `agents/`, `services/` (política, memória, acesso, trace), `baseline_eq.py`, `estudo*.py`; `models/` como fonte da verdade (protocolos, papéis, permissões, testes); `tests/` em quatro pastas e `web/e2e/`. |

## Parte 2 — Código-fonte (3:00 a 14:00, slides 5 a 9, editor aberto)

Cada bloco: o slide dá o mapa, a tela vai para o editor e a fala percorre a função.

| Bloco | Quem | Tempo | Arquivo e função | O que mostrar e dizer |
|---|---|---|---|---|
| Protocolos como dados | J | 1:30 | `models/protocols.yaml` (PROT-APR, PROT-DEL) e `src/fin_mas/core/fsm.py` | Estados, transições e quem emite cada performativo estão no YAML. O código não tem `if` por protocolo; a FSM é carregada e conferida. |
| Barramento: a cadeia de validação | J | 2:00 | `src/fin_mas/core/bus.py`, `Bus.send` (l. 171) | Percorrer a ordem das recusas: envelope, autenticação do remetente (credencial), esquema, destinatário, papel no protocolo, conversa, FSM e, por último, a política (l. 266). Cada recusa vira registro `rejected` com a etapa. É aqui que os ataques da DSM2 morrem. |
| Approval Gate e POL-06 | D | 2:30 | `src/fin_mas/services/politica.py`, `emitir` (l. 143) e `_validar_apr` (l. 234); `src/fin_mas/services/memoria.py`, `_reincide` (l. 142) e `_decidir_waiver` (l. 260) | O ticket guarda o hash do veto, o prazo e as opções. Na decisão, `_validar_apr` confere a pessoa (`_validar_pessoa`: atestado, cargo, envolvido, solicitante) e, no waiver, chama `_decidir_waiver`: relê o histórico **sob a trava**, aplica a mesma regra da oferta (`_reincide`: waiver do padrão em outro mês, antes ou depois) e grava na mesma transação. Recusado, o ticket perde a opção de waiver (`politica.py`, l. 281). É a correção do caso dos dois fechamentos simultâneos. |
| Trava e memória entre execuções | D | 1:30 | `src/fin_mas/services/selado.py`, `trava` (l. 107); `src/fin_mas/live.py`, comando `limpar_memoria` | A trava do sistema operacional fica ao lado do arquivo (`memoria.json.lock`), então dois processos disputam a mesma trava mesmo com pastas de chaves diferentes. A memória do dashboard fica em arquivo e o reinício não a apaga; só o administrador limpa (`PERM-MEM-LIMPAR`), com registro no trace. |
| Acesso: a decisão é da pessoa | D | 1:00 | `src/fin_mas/services/iam.py`, `atestar` (l. 606) e `exigir`; `models/permissions.yaml` e `roles.yaml` | Negado por padrão (IAM-05). A decisão sai com um atestado da sessão, ligado ao ticket e ao hash do veto; a caixa do aprovador não decide sozinha. Operar e aprovar são permissões diferentes; quem reinicia o cenário é o solicitante e a POL-13 o impede de aprovar, também por outra conta da mesma pessoa do ERP (TEST-473). |
| Agentes BDI: hipótese não é crença | J | 1:30 | `src/fin_mas/agents/orc.py`, `concluir_hipotese` (l. 545); `src/fin_mas/core/inferencia.py`, `validar_proposta` (l. 165) | A hipótese nasce de uma regra local (ou do LLM, opcional), passa por regras determinísticas e vira **ação epistêmica**: consultar o AG-CIN. Só a resposta dele confirma ou refuta, e a decisão cita a NORM-11. |
| Negociação de prazo | J | 0:30 | `src/fin_mas/agents/orq.py`, `_negociar_prazo` (l. 241) | O especialista propõe (`propose`); o Orquestrador aceita ou recusa por regra (`accept-proposal`, l. 267), com limite de extensões. |
| Workflow equivalente | D | 0:30 | `src/fin_mas/baseline_eq.py`, `executar` (l. 405) e `decidir_waiver` (l. 331) | Um controlador com as mesmas regras, veto, correção e aprovação, sem agentes nem mensagens entre componentes. Usa a mesma memória da POL-06 e recusa mês já atendido na fila: a linha de base justa pedida no feedback. |

## Parte 3 — Testes (14:00 a 19:00, slides 10 e 11, editor e terminal)

| Bloco | Quem | Tempo | O que mostrar |
|---|---|---|---|
| Organização e rastreabilidade | J | 1:00 | `tests/unit`, `e2e`, `integration`, `tui` e `web/e2e` (Playwright). Em `models/tests.yaml`, cada teste tem id, o requisito que verifica e o elemento do modelo de onde vem; `python tools/trace.py --check` fecha a cadeia (0 erros). |
| Os testes da POL-06 | D | 1:30 | `tests/e2e/test_approval_gate.py`: `test_recurrence_is_checked_again_when_the_waiver_is_decided` (TEST-424, as duas ordens de decisão), `test_uma_liberacao_entre_processos` (TEST-459, dois processos com barreira) e `..._com_pastas_de_chaves_diferentes` (TEST-470). `tests/integration/test_revisao_dsm4_memoria.py` (TEST-471: reiniciar não apaga a memória; só o admin limpa). Rodar: `python -m pytest tests/e2e/test_approval_gate.py tests/integration/test_revisao_dsm4_memoria.py -q -k "recurrence or processos or memory"`. |
| Testes negativos de protocolo e ataques | J | 1:00 | `tests/e2e/test_protocolos_invalidos.py` (transições fora da FSM recusadas) e os cenários `ataque_decisao_forjada` e `ataque_acesso`; `python -m fin_mas invariantes` confere 10 propriedades só pelo trace. |
| Equivalência do workflow | D | 0:45 | `tests/e2e/test_equivalencia_workflow.py`: sem falhas, o workflow e o SMA dão o mesmo resultado nos cenários comparáveis e em cargas sorteadas. É o teste que sustenta a palavra "equivalente". |
| A suíte inteira e a partir do ZIP | J | 0:45 | Rodar na tela os testes da POL-06 (o comando do bloco anterior) e mostrar o fim de uma execução gravada da suíte inteira: no repositório em Linux, 732 passaram e 3 pulados (dois de Windows e um do ZIP); na verificação anterior do ZIP, num ambiente só com o projeto e o pytest, 708 passaram, 0 falharam e 5 pulados com motivo (TUI sem `textual`, LLM sem `anthropic`, o empacotamento que precisa do Git, o wheel sem o pacote `wheel`), igual em três execuções. `python -m fin_mas cenarios --verificar`: 64 de 64. |

## Parte 4 — Demonstrações (19:00 a 23:40, slide 12)

No PowerShell, troque `| grep -E "..."` por `| Select-String -Pattern "..."`.

1. **Jiliard: negociação de prazo** (0:40).
   `python -m fin_mas run --scenario negociacao_prazo | grep -E "P-NEGOCIAR-PRAZO adotada|propose|accept-proposal|confirmada \(|resposta final"`.
   Mostrar `propose [EM_EXECUCAO -> NEGOCIANDO]`, o `accept-proposal` do Orquestrador e a hipótese confirmada
   com o prazo novo.
2. **Jiliard: hipótese confirmada por outro agente** (0:30).
   `python -m fin_mas run --scenario orc_hipotese_local | grep -E "HIPOTESE|QRY-002  AG-ORC|NORM-11|resposta final"`.
   Mostrar "aceita", a consulta QRY-002 e "confirmada (AG-CIN contesta R$ 21.005,86)".
3. **Jiliard: hipótese refutada** (0:20).
   `python -m fin_mas run --scenario hipotese_refutada | grep -E "HIPOTESE|resposta final"`.
   Mostrar "refutada (AG-CIN não contesta…)".
4. **Danrley: fechamento bloqueado** (0:30).
   `python -m fin_mas run --scenario veto_bloqueio | grep -E "parecer veto|POLITICA|BLOQUEADO|resposta final"`.
   Mostrar o veto pela NORM-04, o ticket, o prazo esgotado (POL-08) e `[VETADO -> BLOQUEADO]`. Aqui ninguém
   decide e o fechamento não sai por omissão; na demo 7 o bloqueio é uma decisão humana.
5. **Danrley: aprovação indevida recusada no barramento** (0:40).
   `python -m fin_mas run --scenario ataque_decisao_forjada | grep -E "REJEITADA|MCP INDISPONIVEL|ATAQUES|resposta final"`.
   Ler três recusas (remetente desconhecido, papel errado, hash do veto que não confere) e
   "ATAQUES 14 de 14 rejeitados". A conta: 11 recusas do barramento na tela (`REJEITADA`), 2 do gateway
   MCP (`MCP INDISPONIVEL`: corrigir o ERP sem aprovação e ler o ERP sem credencial) e 1 pedido
   malformado, recusado pelo esquema numa conversa à parte (`SOL-900`, fora da trilha deste pedido; está no
   trace, e por isso o `verificar` conta 12 rejeições do barramento).
6. **Danrley: a gerente envolvida não decide** (0:40). No dashboard, o `operador` reinicia
   `decisao_por_pessoa`. Na janela da `carla`, aba **Aprovações**: "POL-03: você participou de um
   lançamento vetado" e **Decidir** desabilitado. Na janela do `diego`: **Decidir** e **Corrigir no ERP**;
   o histórico registra "diego (gerente)".
7. **Jiliard: POL-06 com dois fechamentos, ao vivo** (1:20). O `operador` reinicia `reincidencia_waiver`.
   Para mostrar o caso do professor na DSM3, os dois tickets abertos ao mesmo tempo, o `controller`
   **espera o ticket de setembro aparecer na aba Aprovações antes de decidir agosto** (o prazo do ticket
   no dashboard é de cerca de 10 minutos; o `operador` pode pausar a simulação enquanto isso). Com os dois
   pendentes, o controller dá waiver em agosto, com justificativa. Em setembro, o waiver ainda aparece;
   ao clicar, a política recusa com "POL-06: reincidência" e a opção some do ticket. Nos dois casos o controller clica em **Bloquear**:
   setembro fica bloqueado por decisão humana, com o waiver negado pela política. Depois, o
   `operador` reinicia o cenário de novo: setembro continua sem waiver, porque a memória sobreviveu ao
   reinício. Fechar com o teste dos dois processos já mostrado na Parte 3.

**Plano B:** sem dashboard, `./iniciar.sh replay` e os cenários `decisao_por_pessoa` e
`reincidencia_waiver` no terminal; sem ambiente, `python3 tools/iniciar.py cli --cenario veto_correcao`.

## Parte 5 — Experimento, revisão final e fechamento (23:40 a 27:20, slides 13 a 20)

| Slide | Quem | Tempo | O que dizer |
|---|---|---|---|
| 13. Experimento: desenho | J | 0:30 | Pré-registro antes do código; quatro braços; 30 seeds; falhas, plantios, aprovador e ataques sorteados por seed. |
| 14. Qualidade e robustez | D | 0:35 | Empate sem falhas (em boa parte por construção); o SMA perde a partir de 15% de perda; nenhuma crítica publicada. Desvio-padrão nas tabelas. |
| 15. Custo, cognição, ablação, ataques | D | 0:30 | Mais mensagens; cognição sem ganho significativo; reenvio, reserva e correção valem; 0 ataques aceitos indevidamente. |
| 16. Bloco E | J | 0:40 | Com a mesma memória e a recusa de mês já atendido no workflow, os resultados são iguais seed a seed, nos quatro portes; sobra o paralelismo (que um controlador com vários atendentes também teria) e o custo em mensagens. Sob 15% de perda e concorrência, o SMA publica menos, sempre com falha explícita e sem crítica sem tratamento. Com um especialista fora do ar, o reenvio recupera e o SMA publica o mesmo que o workflow. Volume mede só o tempo de parede. As oito conclusões foram pré-registradas e confirmadas com as seeds 31 a 60: mostrar `bloco_e_confirmatorio/confirmacao.md` (8 de 8). |
| 17. Três rodadas | J | 0:15 | Nenhuma rodada posterior à primeira é confirmatória. A 1.1.0 repetiu o experimento inteiro: as mesmas métricas. |
| 18. Revisão final | D | 0:30 | Um item por pedido do feedback, cada um com o seu teste. |
| 19. Limitações | J | 0:20 | As que mais pesam; a lista completa está na documentação. |
| 20. Lições | D + J | 0:20 | Com funções iguais, o SMA empata em qualidade e perde em custo e robustez; o que ele entrega é estrutural. Cada um fecha com uma frase. |

## Critérios do enunciado → vídeo

| Critério | Partes |
|---|---|
| Sistema final e corretude | 2, 3 e 4 |
| Arquitetura e SMA | 1 e 2 |
| Experimentação e análise | 5 |
| Testes e reprodutibilidade | 3 |
| Documentação | 1 (mapa do código) e 5 (limitações) |
| Demonstração, apresentação e autoria | 4; os dois autores falam em todas as partes |

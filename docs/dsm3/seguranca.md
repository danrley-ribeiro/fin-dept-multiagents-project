# Corretude e robustez: segurança das decisões

## Política de aprovação (SVC-POL)

Cada regra tem um id que aparece no motivo da rejeição e no registro `politica` do trace.

| Regra | Conteúdo | Onde é aplicada |
|---|---|---|
| POL-01 | toda liberação de veto exige aprovação humana (REQUIRE_APPROVAL); a proposta tem de ser idêntica ao ticket emitido | emissão do ticket; validador do `propose-action` |
| POL-02 | só o aprovador designado decide, e só o que o cadastro dele permite (ex.: analista corrige ou bloqueia, não concede waiver) | validador do `approve`/`reject` |
| POL-03 | quem criou ou aprovou um lançamento vetado não decide sobre ele (segregação de funções da própria aprovação) | idem, com os `envolvidos` que o AG-CIN informa no veto |
| POL-04 | waiver exige justificativa com pelo menos 10 caracteres | idem |
| POL-05 | correção aprovada só contém correções sugeridas pelo AG-CIN; o AG-CIN recebe exatamente as executadas | idem; gateway (`autorizar_efeito`); validador do `correcao` |
| POL-06 | achado crítico reincidente após waiver anterior do mesmo padrão (memória) não admite novo waiver | emissão do ticket |
| POL-07 | sem opção de liberação restante, a ação é negada (DENY) e a publicação fica bloqueada | emissão e classificação |
| POL-08 | ticket de uso único: um veto, uma vez, no prazo, com o hash dos achados apresentados | validadores do PROT-APR e do PROT-CMP |

O ticket guarda solicitação, conversa vetada e ciclo, hash do veto, opções abertas e negadas
(com a regra), aprovador designado, prazo, decisão, quem decidiu (agente, pessoa, cargo),
justificativa, correções aprovadas e executadas e se já foi consumido. A memória e o
relatório citam o id do ticket.

## Ataques testados

O cenário `ataque_decisao_forjada` (plantio de alçada, aprovador em silêncio) dispara, um tick
depois da abertura do PROT-APR, a sequência de `src/fin_mas/env/ataques.py`. Resultado
(`python -m fin_mas run --scenario ataque_decisao_forjada`):

| # | Ataque | Barrado em | Motivo registrado |
|---|---|---|---|
| 1 | `decisao_humana` sem protocolo, de remetente inexistente (feedback) | autenticação | remetente desconhecido: 'FANTASMA' |
| 2 | `approve` em nome do APR, sem a credencial dele | autenticação | credencial ausente ou inválida para APR |
| 3 | `approve` enviado pelo AG-REL | papel | ROLE-REL não pode emitir 'approve' |
| 4 | `approve` do APR com hash de veto adulterado | política | POL-08: hash do veto não confere |
| 5 | `approve` do APR citando outro ticket | política | POL-08: não corresponde ao ticket |
| 6 | `waiver_humano` ao AG-CIN sem aprovação | política | POL-08: sem aprovação emitida |
| 7 | `advance publicar` por identificador não autorizado (feedback) | autenticação | identidade desconhecida: 'HACKER' |
| 8 | `advance publicar` pelo AG-CIN | papel | ROLE-CIN não pode aplicar 'publicar' |
| 9 | `execute` antes da aprovação | FSM | execução sem aprovação humana |
| 10 | `erp.corrigir` sem aprovação, pelo próprio Orquestrador | gateway | aprovação APR-001 está pendente (`mcp_denied`) |
| 10b | gateway chamado em nome de outro agente (AG-REL se declara AG-CIN) | gateway | identidade não autenticada (`mcp_denied`) |
| 11 | resposta a quem não é a contraparte da conversa (feedback) | destinatário | AG-RES não é a contraparte de AG-CUS |
| 12 | resposta a papel que não participa do protocolo | papel | ROLE-REL não participa do PROT-CMP |
| 13 | pedido sem campos obrigatórios (feedback) | esquema | campo obrigatório ausente: entidade; competencia |

Resultado: 14 tentativas, **0 aceitas** (MET-15), 12 `rejected` + 2 `mcp_denied` no trace,
nenhum `erro_agente`; o ticket expira no prazo e o fechamento termina **bloqueado, sem
publicar**. Os testes de {doc}`testes` repetem cada ataque isoladamente e cobrem ainda
duplicidade, atraso, reutilização entre ciclos, papel do aprovador, SoD, justificativa,
correção fora das sugeridas, personificação no registro e adulteração de conteúdo e de trace.

## Proteção de informações

- **Redaction fail-closed (NORM-06):** todo registro de auditoria passa por `services/redacao.py`
  antes de ser guardado: campos com nome de segredo (senha, token, api_key, credencial…) e CPF,
  e-mail, chaves de API e tokens Bearer em texto são substituídos. Se a sanitização falhar
  (tipo desconhecido, estrutura profunda), o conteúdo é recusado e fica só um marcador
  `redacao: recusada`. Na memória, a falha recusa a gravação.
- **Credenciais:** cada identidade recebe a sua credencial no registro; o barramento guarda só o
  hash SHA-256 dela (ler o estado do barramento não permite se passar por ninguém). O gateway MCP
  e a memória também exigem prova de identidade: `Agent.ferramenta` envia a credencial ao gateway
  e a memória só aceita a visão emitida para cada agente. Um teste confere que nenhuma
  credencial aparece no JSONL gravado.
- **Minimização na memória:** pessoas viram pseudônimos estáveis (`pessoa#…`, HMAC com a chave da memória, que fica fora da pasta de dados) e nenhum texto
  livre (detalhe de correção, justificativa) é guardado; o arquivo de memória não tem nomes.
- **Memória íntegra e com falha fechada:** cada entrada é assinada com HMAC-SHA256 e o arquivo
  inteiro tem um selo HMAC sobre (contador de versão, entradas). A chave e o último contador
  ficam fora da pasta de dados (`~/.fin_mas/chaves/` ou `FIN_MAS_DIR_CHAVES`). Entrada inventada,
  alterada, removida ou malformada, arquivo corrompido ou apagado, volta a uma versão antiga e
  arquivo em outra versão do formato (ex.: v3, com pseudônimos sem chave; issue #2)
  deixam a memória **comprometida**: nada é gravado e o AG-CIN trata todo achado crítico como
  reincidente, então a política não reabre o waiver (TEST-84). A gravação exige ticket compatível: waiver aprovado para
  `waiver`, correção executada para `correcao`, rejeição para `bloqueio`, mesma competência e
  lançamento do veto.
- **Trace com cadeia de hashes e selo HMAC:** cada linha do JSONL traz `_hash` = SHA-256(hash
  anterior + registro) e a última linha é um selo com o número de registros, o hash final e um
  HMAC desses valores com a chave local do trace (`~/.fin_mas/chave_trace` ou
  `FIN_MAS_CHAVE_TRACE`, fora do repositório). `python -m fin_mas verificar trace.jsonl` acusa
  linha alterada, removida ou reordenada, corte do fim do arquivo e cadeia recalculada por quem
  não tem a chave (saída 3); o `replay` recusa trace sem cadeia, salvo com `--sem-verificar`.
  Em outra máquina, sem a chave do autor, a verificação usa a **âncora pública**: o hash final da
  cadeia, que é reproduzível (`verificar trace.jsonl --ancora <hash>`); a âncora do cenário
  adversarial está no README da entrega (TEST-88).
- **Isolamento de erros e atomicidade:** o barramento calcula o hash do conteúdo (que precisa ser
  JSON com chaves de texto) antes de qualquer efeito; uma mensagem recusada nunca deixa ticket ou
  FSM alterados. Exceção de um agente não interrompe a simulação, e todo estado de espera tem
  prazo, inclusive `APROVADA` no PROT-APR: nenhuma solicitação fica sem resposta. Comandos do
  dashboard têm os tipos validados (400) e nenhum erro derruba a thread da simulação.
- **Reserva do período durante a aprovação:** o Orquestrador renova a reserva (PROT-LCK) até o
  prazo do ticket e não publica se a perder; outro fechamento do mesmo mês é recusado.
- **Validação de domínio na entrada:** competência fora de `AAAA-MM` (ano 2000–2099, mês 01 a 12) é barrada pelo
  esquema; entidade que não é a empresa atendida, ou competência sem dados no modo planilha,
  recebe `refuse` do Orquestrador antes de qualquer delegação (TEST-72).
- **API do dashboard:** autentica antes de ler o corpo (corpo enorme sem token não é lido; leitura
  com tempo limite; token não-ASCII não gera exceção, TEST-90); só loopback; `Host` e `Origin` precisam ser `127.0.0.1`/`localhost`
  (bloqueia DNS rebinding e páginas de outros sites); todo POST — comandos, decisão humana,
  envio de planilha — exige o cabeçalho `X-SMA-Token` com o token da sessão, obtido em
  `GET /api/sessao`, que outro site não consegue ler (TEST-73).

## Modelo de ameaça e limites

O barramento é em processo e single-thread. A credencial protege contra **mensagens montadas
fora do agente dono da identidade** (injeção no barramento, personificação, replay de
decisões), que é o que o feedback demonstrou. Não protege contra código que acesse o objeto
Python de outro agente: nesse modelo, o registro no barramento é a raiz de confiança. Numa
versão distribuída, a mesma checagem passaria a usar mTLS ou assinaturas por mensagem, sem
mudar os protocolos (ADR-007).

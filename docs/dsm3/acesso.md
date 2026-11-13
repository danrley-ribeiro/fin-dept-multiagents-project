# Identidade e acesso por pessoa (SVC-IAM)

Implementa o {need}`REQ-S05`, a {need}`NORM-12` e a {need}`NORM-13` (decisão em
{doc}`ADR-009-identidade-e-acesso`). Na primeira versão da DSM3, qualquer processo local que
lesse o token da sessão do dashboard agia como o aprovador `APR`. Agora quem usa a plataforma é
uma **pessoa com conta**: entra com senha, recebe uma sessão, só faz o que os papéis dela
permitem, e cada comando e cada decisão ficam no nome dela.

Código: `src/fin_mas/services/iam.py` (contas, sessões, regras IAM, atestado),
`src/fin_mas/services/selado.py` (arquivo selado), `src/fin_mas/services/trilha.py` (trilha de
acesso), `src/fin_mas/core/permissoes.py` e `models/permissions.yaml` (papéis e permissões),
`src/fin_mas/cli_acesso.py` (linha de comando) e `src/fin_mas/tui/` (console de administração).

## Contas e sessões

| Item | Como funciona |
|---|---|
| Senha | `hashlib.scrypt` com sal por conta; o cadastro guarda só o resultado. Mínimo de 12 caracteres, diferente do usuário, fora da lista de senhas óbvias |
| Senha temporária | redefinida por um administrador, precisa ser trocada na primeira entrada (dashboard e TUI bloqueiam o resto até a troca) |
| Sessão | token aleatório; o cadastro guarda só o SHA-256. Vale 8 horas, cai após 15 minutos sem uso e pode ser revogada |
| Revogação | gravada no arquivo de sessões; servidor e TUI conferem a sessão a cada requisição ou ação, então vale na requisição seguinte; o fluxo SSE do dashboard se fecha |
| Conta bloqueada pelo administrador ou desativada | derruba as sessões dela |
| Bloqueio temporário por senhas erradas | impede só novas entradas por 15 minutos; a sessão já aberta continua (senão quem não tem conta derrubaria a sessão de outra pessoa) |
| Cadastro | dois arquivos selados (`contas.json`, `sessoes.json`) e a trilha (`trilha.jsonl`) na pasta de acesso; podem ser alterados pela TUI com o servidor rodando |

## Papéis e permissões

Papéis humanos de plataforma (DSM3) somam-se ao Solicitante e ao Aprovador da DSM1. Nenhum
deles troca mensagens com os agentes: agem pela interface autenticada. A matriz vem de
`models/roles.yaml` (campo `permissoes`) e é lida pelo SVC-IAM; nada fica no código. Negado por
padrão: só passa o que algum papel da conta concede (IAM-05).

| Permissão | ROLE-SOL | ROLE-APR | ROLE-OPE | ROLE-AUD | ROLE-ADM |
|---|:-:|:-:|:-:|:-:|:-:|
| `PERM-SIM-VER` ver a simulação | ✓ | ✓ | ✓ | ✓ | ✓ |
| `PERM-SIM-OPERAR` pausar, passo, ritmo, reiniciar, nível de cognição | | | ✓ | | |
| `PERM-AGT-ENERGIA` ligar e desligar especialistas | | | ✓ | | |
| `PERM-SOL-CRIAR` fazer solicitações | ✓ | | | | |
| `PERM-APR-DECIDIR` decidir no Approval Gate | | ✓ | | | |
| `PERM-DAD-VER` ver planilha e baixar modelos | ✓ | ✓ | ✓ | ✓ | |
| `PERM-DAD-ENVIAR` enviar planilha | | | ✓ | | |
| `PERM-MOD-VER` ver configuração de LLM | | ✓ | ✓ | ✓ | |
| `PERM-MOD-CONFIG` ajustar LLM, usos, cota, consentimento | | ✓ | | | |
| `PERM-AUD-VER` ver trace, trilha e explicações | | ✓ | ✓ | ✓ | ✓ |
| `PERM-AUD-EXPORTAR` exportar recortes | | | | ✓ | ✓ |
| `PERM-IAM-USUARIOS` criar, bloquear, desativar contas, redefinir senha | | | | | ✓ |
| `PERM-IAM-PAPEIS` atribuir papéis | | | | | ✓ |
| `PERM-IAM-SESSOES` listar e revogar sessões | | | | | ✓ |

`python -m fin_mas acesso --acesso PASTA papeis` imprime a mesma matriz lida dos modelos
(teste `test_role_matrix_comes_from_the_models`). Os papéis completos (responsabilidades,
permissões e obrigações) estão em {doc}`../dsm1/roles`.

Incompatibilidade (IAM-06): a mesma conta não acumula `ROLE-ADM` e `ROLE-APR`. Decisões por
cargo (POL-02), em `models/permissions.yaml`:

| Cargo | Decisões permitidas |
|---|---|
| assistente, analista | corrigir, bloquear |
| gerente, diretor, sócio, controller | waiver, corrigir, bloquear |

### Permissões (gerado de `models/permissions.yaml`)

```{include} ../_generated/permissions.md
```

## Regras IAM

| Regra | Conteúdo | Onde é testada |
|---|---|---|
| IAM-01 | o primeiro administrador só é criado enquanto não existe nenhuma conta (bootstrap) | `test_first_use_wizard_creates_the_first_administrator`, `test_full_account_lifecycle_from_the_terminal` |
| IAM-02 | senha com 12+ caracteres, diferente do usuário, fora da lista de óbvias; senha redefinida é trocada na primeira entrada | `test_temporary_password_must_be_changed_first` (servidor), `test_temporary_password_must_be_changed_before_using_the_console` (TUI), roteiro Playwright "senha temporária…" |
| IAM-03 | cinco senhas erradas seguidas bloqueiam novas entradas na conta por 15 minutos (a sessão aberta continua); usuário inexistente custa o mesmo tempo e recebe a mesma resposta | `test_login_lockout_and_generic_errors`, roteiro "senha errada mostra erro genérico…" |
| IAM-04 | sessão de 8 h, cai após 15 min sem uso, pode ser revogada; conta bloqueada ou desativada derruba as sessões | `test_revoked_session_stops_at_once_and_closes_the_event_stream`, `test_blocking_an_account_drops_its_session_and_its_login` (a expiração por tempo não tem teste automatizado; ver {doc}`limitacoes`) |
| IAM-05 | negado por padrão: só passa o que algum papel concede | `test_each_role_can_only_do_what_its_permissions_allow`, `test_auditor_sees_the_trail_and_cannot_administer` |
| IAM-06 | papéis incompatíveis (`ROLE-ADM` + `ROLE-APR`) e remoção, bloqueio ou rebaixamento do último administrador ativo são recusados | `test_assigning_approver_role_to_the_administrator_is_refused_with_iam06`, `test_last_administrator_cannot_be_blocked` |
| IAM-07 | cadastro com integridade comprometida não deixa ninguém entrar (falha fechada) | `test_tampered_account_store_locks_everyone_out`, `test_compromised_registry_lets_nobody_in`, `test_rolled_back_account_file_is_refused` |

Toda negação leva o id da regra: na resposta HTTP (403), na mensagem da TUI e da CLI e na
trilha de acesso.

## Decisão pela pessoa no Approval Gate

Com o SVC-IAM ligado, a decisão deixa de valer pela caixa `APR` e passa a valer pela pessoa
autenticada. O servidor (ou o acesso simulado dos cenários em lote) emite um **atestado**
`{pessoa, sessao, nonce, token}`, em que `token` é um HMAC-SHA256, com uma chave gerada no
início do processo e nunca gravada, sobre o ticket, o hash do veto, a decisão, o corpo da
decisão (justificativa e correções), a pessoa, a sessão e o nonce. O atestado viaja no campo
opcional `atestado` do `approve`/`reject` (PROT-APR); com tipo errado, a mensagem é recusada já
na etapa de esquema do barramento.

| Regra (SVC-POL) | Com o SVC-IAM ligado | Cenário |
|---|---|---|
| POL-09 | a decisão precisa de atestado que confira com ticket, veto, decisão, corpo e pessoa; sessão viva; nonce inédito; pessoa com `PERM-APR-DECIDIR` | `ataque_acesso` |
| POL-02 | o **cargo da conta** define o que a pessoa decide | `waiver_exige_cargo`: waiver de ana (analista) recusado; diego (gerente) concede |
| POL-03 | quem criou ou aprovou um lançamento vetado (vínculo da conta com a pessoa do ERP) não decide sobre ele | `decisao_por_pessoa`: carla recusada; diego decide |
| POL-13 | quem fez a solicitação não decide sobre ela; no porte com controle compensatório registrado (micro), a decisão passa e o controle fica anotado na decisão | `solicitante_nao_aprova` (elisa recusada; controller decide); `micro_controle_compensatorio` |

Sem o SVC-IAM (cenários em lote da primeira versão da DSM3), valem POL-01 a POL-08 com o
cadastro por identidade, como antes (`test_without_iam_the_reviewed_scenarios_keep_the_identity_based_rules`).
O ticket decidido guarda `aprovado_por = {agente, pessoa, titulo, sessao}`, e a decisão vai para a
trilha de acesso (evento `decisao`). O pedido feito pelo dashboard leva `solicitado_por` com o
usuário da sessão.

## Arquivo selado e trilha de acesso

| Mecanismo | Garantia | Arquivo |
|---|---|---|
| Selo | HMAC-SHA256 sobre (versão, contador, dados), com chave **fora da pasta de dados** (`FIN_MAS_DIR_CHAVES` ou `~/.fin_mas/chaves/`, modo 0600) | `services/selado.py` |
| Contador | sobe a cada gravação e também fica fora da pasta; arquivo com contador menor que o último gravado é uma versão antiga (rollback) e é recusado | idem |
| Gravação atômica e trava | arquivo temporário + `os.replace`; trava `.lock` criada com `O_EXCL`; toda alteração relê o arquivo dentro da trava | idem; `test_concurrent_writers_do_not_lose_updates` |
| Falha fechada | arquivo ausente depois de gravado, ilegível, de outra versão, com selo errado ou contador antigo levanta `ArquivoComprometido`; o SVC-IAM nega toda entrada (IAM-07) | idem |
| Trilha de acesso | JSONL só de acréscimo; cada registro traz o hash do anterior; a **cabeça** (quantidade, hash final, HMAC) fica fora da pasta; `verificar` acusa alteração, remoção e corte | `services/trilha.py`; `test_access_trail_is_listed_verified_and_tampering_is_detected` |

Eventos da trilha: `bootstrap`, `entrada`, `saida`, `senha_trocada`, `senha_redefinida`,
`conta_criada`, `conta_bloqueada`, `conta_desbloqueada`, `conta_desativada`, `papeis_alterados`,
`vinculo_alterado`, `sessao_revogada`, `sessoes_revogadas`, `permissao` (negação), `decisao`,
`planilha_enviada`, `auditoria_exportada` e `cadastro_comprometido`, cada um com `resultado`
(`ok` ou `negado`) e, na negação, a regra. Os registros
passam pela redação de segredos: senha e token nunca entram.

## Ataques do cenário `ataque_acesso`

Todos partem da posição que a primeira versão da DSM3 deixava aberta: quem controla a caixa
`APR` (a credencial do barramento, como faria uma interface comprometida) tenta fazer valer uma
decisão sem ser a pessoa certa. Disparam um tick depois da abertura do PROT-APR
(`src/fin_mas/env/ataques_acesso.py`). Resultado de
`python -m fin_mas run --scenario ataque_acesso`:

| # | Ataque | Regra que recusa |
|---|---|---|
| 1 | decisão pela caixa APR sem atestado (a lacuna da primeira versão) | POL-09: decisão sem atestado de sessão |
| 2 | atestado com token forjado | POL-09: atestado não confere |
| 3 | atestado emitido para bloquear, usado para liberar | POL-09: atestado não confere |
| 4 | atestado de outro ticket reaproveitado | POL-09: atestado não confere |
| 5 | atestado de uma justificativa enviado com outra | POL-09: atestado não confere |
| 6 | atestado de sessão revogada | POL-09: sessão expirada, revogada ou de outra pessoa |
| 7 | pessoa sem papel de aprovador (operador) pede um atestado | IAM-05: sem `PERM-APR-DECIDIR` |
| 8 | pessoa sem papel de aprovador (bruno) forja o atestado | POL-09: atestado não confere |
| 9 | cargo sem alçada (analista concede waiver) | POL-02 |
| 10 | mesmo atestado enviado duas vezes (replay) | POL-02 no primeiro envio; POL-09 "atestado já usado" no segundo |
| 11 | aprovadora que participou do lançamento vetado decide sobre ele (ana corrige) | POL-03 |
| 12 | quem fez a solicitação decide sobre ela (elisa) | POL-13 |
| 13 | operador atribui a si o papel de aprovador | IAM-05: sem `PERM-IAM-PAPEIS` |
| 14 | administrador de acesso acumula o papel de aprovador | IAM-06 |
| 15 | administrador remove o último administrador (ele mesmo) | IAM-06 |

Resultado: **15 de 15 rejeitados** (registro `ATAQUES`), 12 `rejected` na etapa de política no
trace, o ticket expira no prazo e o fechamento termina em `failure`, sem publicar.

## Linha de comando

A pasta do cadastro vem de `--acesso` (padrão `dados/acesso` ou `FIN_MAS_ACESSO`). Toda
alteração exige um administrador (`--como USUARIO`, senha pelo terminal ou `FIN_MAS_SENHA`).
Senhas novas vêm de `FIN_MAS_SENHA_NOVA` ou do terminal, nunca de argumento.

```bash
python -m fin_mas acesso --acesso dados/acesso iniciar --usuario admin --nome "Administração"
python -m fin_mas acesso --acesso dados/acesso demo                    # contas de demonstração
python -m fin_mas acesso --acesso dados/acesso --como admin usuario listar
python -m fin_mas acesso --acesso dados/acesso --como admin usuario papeis ana ROLE-SOL ROLE-APR
python -m fin_mas acesso --acesso dados/acesso --como admin usuario vinculo ana --pessoa ana --cargo analista
python -m fin_mas acesso --acesso dados/acesso papeis                  # matriz papel x permissão
python -m fin_mas acesso --acesso dados/acesso --como admin sessao listar     # e: sessao revogar ID
python -m fin_mas acesso --acesso dados/acesso trilha ver --resultado negado
python -m fin_mas acesso --acesso dados/acesso trilha verificar        # cadeia e cabeça selada
python -m fin_mas acesso --acesso dados/acesso tui                     # console (extra `tui`)
```

## Console de administração (TUI)

`python -m fin_mas acesso --acesso PASTA tui` (Textual, extra opcional:
`pip install "fin-mas[tui]"`). É para **gerenciar** (administrador de acesso e auditor); a
simulação dos agentes é usada pelo dashboard web. A TUI grava nos mesmos arquivos selados que o
servidor lê, e toda alteração é uma chamada a `services/iam.py`.

| Aba | Tecla | Quem vê | Conteúdo |
|---|---|---|---|
| Usuários | F1 | `PERM-IAM-USUARIOS` | contas com estado, papéis, cargo e pessoa do ERP |
| Papéis × permissões | F2 | `PERM-IAM-PAPEIS` | matriz dos modelos e o quadro de contas que violam IAM-06 ou que solicitam e aprovam (aviso da POL-13) |
| Sessões | F3 | `PERM-IAM-SESSOES` | sessões abertas e encerradas, com a situação |
| Trilha de acesso | F4 | `PERM-AUD-VER` | filtros por ator, evento e resultado; integridade (ÍNTEGRA ou ADULTERADA, com o motivo); exportação do recorte |
| Traces | F5 | `PERM-AUD-VER` | abre um JSONL de simulação, confere cadeia e selo, filtra, explica o registro selecionado, confere os invariantes e exporta |

| Onde | Atalhos |
|---|---|
| qualquer lugar | `Ctrl+Q` encerra a sessão e sai · `Ctrl+R` relê do disco · `F1`..`F5` abas · `F8` troca a própria senha · `/` filtros · `Esc` volta à tabela |
| Usuários | `n` nova conta · `p` papéis · `v` vínculo (pessoa do ERP, cargo) · `s` redefinir senha · `b` bloquear · `d` desbloquear · `x` desativar |
| Sessões | `r` revogar a selecionada · `t` revogar todas as vivas do usuário |
| Trilha | `i` verificar integridade · `e` exportar o recorte |
| Traces | `a` caminho do arquivo (Enter abre) · `l` ou Enter explicar · `i` conferir de novo · `e` exportar |
| formulários | Enter confirma · Esc cancela · confirmações: `s` sim, `n` ou Esc não (foco começa no "Não") |

Só entra quem tem ao menos uma de `PERM-IAM-USUARIOS`, `PERM-IAM-SESSOES` ou `PERM-AUD-VER`. A
sessão do console é conferida no cadastro antes de cada ação: revogada, expirada ou com 15
minutos sem uso, o console volta à entrada; se os papéis mudaram em outro lugar, as abas são
remontadas. A exportação nunca sobrescreve arquivo existente e fica na trilha.

## Contas de demonstração

`python -m fin_mas serve --demo`, `fin-mas instalar --demo` ou `acesso demo` criam, numa pasta
vazia, as contas abaixo, todas com a senha pública **`Demonstracao-SMA-2026`** (documentada de
propósito; não use fora de avaliação e aula). O modo ao vivo do comando único (`./iniciar.sh`,
`.\iniciar.ps1`) sobe com `--demo`.

| Usuário | Papéis | Cargo | Pessoa do ERP | Para que serve |
|---|---|---|---|---|
| `avaliador` | OPE, SOL, APR, AUD | controller | — | ver tudo numa conta só (não administra acesso) |
| `admin` | ADM | — | — | administrar contas, papéis e sessões |
| `operador` | OPE | — | — | operar a simulação; não pede nem decide |
| `auditor` | AUD | — | — | ler e exportar logs e trilha; não opera |
| `controller` | APR, SOL | controller | — | decidir qualquer opção; também pede (aviso POL-13 na TUI) |
| `elisa` | SOL, APR | diretor | elisa | solicitante dos cenários de acesso; recusada pela POL-13 ao decidir o próprio pedido |
| `carla` | APR | gerente | carla | aprovadora envolvida em lançamento (POL-03) |
| `diego` | APR | gerente | diego | aprovador que decide quando carla ou ana não podem |
| `ana` | SOL, APR | analista | ana | só corrige ou bloqueia (POL-02) |
| `bruno` | SOL | analista | bruno | pede, não decide |

## MET-17: acessos indevidos aceitos

{need}`MET-17` é calculada por `metricas.medir_acesso` sobre o trace.

| Cenário | Ataques tentados / aceitos | Decisões negadas por regra | Decisões aceitas com pessoa e sessão |
|---|---|---|---|
| `ataque_acesso` | 15 / **0** | POL-09: 8 · POL-02: 2 · POL-03: 1 · POL-13: 1 | 0 de 0 |
| `decisao_por_pessoa` | — | POL-03: 1 | 1 de 1 |
| `solicitante_nao_aprova` | — | POL-13: 1 | 1 de 1 |
| `waiver_exige_cargo` | — | POL-02: 1 | 1 de 1 |
| `micro_controle_compensatorio` | — | nenhuma | 1 de 1 (com `controle_compensatorio`) |

Os ataques 7, 13, 14 e 15 são recusados pelo SVC-IAM antes de chegar ao barramento e aparecem
no registro `ataques` e na trilha; o ataque 10 gera dois registros `rejected` (POL-02 e depois
POL-09), daí 12 rejeições no trace para 11 ataques que chegam ao barramento. O alvo da métrica é
0 aceitos; nos testes de integração do servidor e da CLI, cada recusa é conferida com a regra.

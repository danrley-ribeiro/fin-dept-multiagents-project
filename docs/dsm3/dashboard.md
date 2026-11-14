# Dashboard autenticado e áreas de trabalho

O dashboard da DSM2 ({doc}`../dsm2/dashboard`) continua: escritório com os agentes, mente BDI,
conversas, decisão humana, replay e comparação. Nesta etapa ele passa a ser usado **por
pessoas com conta** ({doc}`acesso`): login, permissões por papel, áreas de trabalho e as
hipóteses na mente do agente. Servidor: `src/fin_mas/server.py`; interface: `web/src/`
(`App.tsx`, `components/Login.tsx`, `components/AreasDeTrabalho.tsx`, `components/PainelMente.tsx`,
`api/sessao.ts`). Implementa o {need}`REQ-O04` (TEST-19, agora executado).

```bash
python -m fin_mas serve --demo                   # contas de demonstração; abra http://127.0.0.1:8765
python -m fin_mas serve --demo --cognicao local  # o mesmo, com hipóteses no AG-ORC
python -m fin_mas serve --instalacao dados       # a partir da pasta criada pelo `instalar`
```

Sem contas no cadastro, o servidor não sobe e diz como criar (`acesso iniciar`, `acesso demo`
ou `serve --demo`; teste `test_server_refuses_to_start_without_accounts`).

## Login e sessão

1. A página consulta `GET /api/saude` (pública: versão e se há contas). Sem servidor, abre o
   replay offline.
2. `POST /api/login {usuario, senha}` abre a sessão: cookie `HttpOnly; SameSite=Strict` com o
   token, e o corpo devolve o token CSRF **da sessão**. Erro de senha e usuário inexistente
   recebem a mesma mensagem; cinco erros bloqueiam a conta por 15 minutos (IAM-03).
3. Com senha temporária, a única tela é a de troca (`POST /api/senha`); as demais rotas
   respondem 403 com IAM-02 até a troca.
4. `POST /api/logout` encerra a sessão no servidor e apaga o cookie.
5. A cada requisição o servidor relê a sessão do cadastro selado: revogada pela TUI ou pela
   CLI, a próxima chamada recebe 401 e o fluxo de eventos (SSE) se fecha; o dashboard volta ao
   login.

## O que cada papel vê e pode

| Elemento | Exige | SOL | APR | OPE | AUD | ADM |
|---|---|:-:|:-:|:-:|:-:|:-:|
| Escritório, conversas, mente BDI, eventos ao vivo | `PERM-SIM-VER` | ✓ | ✓ | ✓ | ✓ | ✓ |
| Pausar, passo, ritmo, reiniciar, cenário, nível de cognição | `PERM-SIM-OPERAR` | | | ✓ | | |
| Ligar e desligar especialistas | `PERM-AGT-ENERGIA` | | | ✓ | | |
| Novo pedido (diálogo e painel do Solicitante) | `PERM-SOL-CRIAR` | ✓ | | | | |
| Decidir veto (notificação e área Aprovações) | `PERM-APR-DECIDIR` | | ✓ | | | |
| Planilha atual e modelos | `PERM-DAD-VER` | ✓ | ✓ | ✓ | ✓ | |
| Enviar planilha | `PERM-DAD-ENVIAR` | | | ✓ | | |
| Aba *Logs* (filtros, por quê, sequência) | `PERM-AUD-VER` | | ✓ | ✓ | ✓ | ✓ |
| Exportar recorte dos logs | `PERM-AUD-EXPORTAR` | | | | ✓ | ✓ |
| Aba *Agentes e LLM* (ver) | `PERM-MOD-VER` | | ✓ | ✓ | ✓ | |
| Ligar LLM, trocar provedor, usos, cota, consentimento | `PERM-MOD-CONFIG` | | ✓ | | | |

Botões sem a permissão aparecem desabilitados com a explicação; a aba que exige permissão nem
aparece. A interface só reflete a regra: quem decide é o servidor, que recusa com 403 e a regra
qualquer chamada direta à API sem a permissão (`test_each_role_can_only_do_what_its_permissions_allow`).
O administrador de acesso usa a TUI para administrar contas; no dashboard ele só lê.

## Áreas de trabalho

| Aba | Quem vê | O que tem |
|---|---|---|
| Escritório | todos | o escritório da DSM2; o chip da pessoa logada, troca de senha e saída |
| Solicitações | logados | pedidos com situação e quem pediu; relatório final para abrir e baixar em JSON, TXT ou HTML; botão de novo pedido para quem tem `PERM-SOL-CRIAR` |
| Aprovações | logados | fila de tickets pendentes com prazo e "pedido por"; decisão com justificativa (só `PERM-APR-DECIDIR`); histórico com a pessoa que decidiu |
| Logs | `PERM-AUD-VER` | trace com filtros por agente, tipo, tarefa, intervalo e texto; "por quê" de um registro (cadeia percepção → crença → hipótese → desejo → plano → decisão) e sequência da conversa; exportação em JSONL para `PERM-AUD-EXPORTAR` |
| Agentes e LLM | `PERM-MOD-VER` | por agente com LLM permitido (AG-ORC, AG-RES, AG-REL): ligado/desligado, provedor, modelo, URL, usos, cota, consentimento de envio externo, se a chave está no ambiente (nunca o valor), disjuntor e uso de tokens e custo; nível de cognição |
| Porte | logados | ficha das regras de cada porte (`models/portes.yaml`) com o porte em uso marcado ({doc}`../dsm2/portes`) |
| SMA × workflow | todos | a comparação da DSM2/DSM3 |

No painel da mente do AG-ORC, a aba **Hipóteses** lista as hipóteses com tipo, alvo, origem
(regra local ou IA, com o id da regra ou do modelo), estado e a fonte da evidência; na aba de
crenças, cada crença mostra a origem classificada pela fonte registrada: percepção (tool MCP),
comunicação (outro agente ou serviço) ou inferência (plano ou cálculo). Um proponente nunca
aparece como origem de crença.

## Rotas da API e permissão de cada uma

| Método e rota | Exige |
|---|---|
| `GET /api/saude`, `POST /api/login` | nada (públicas) |
| `GET /api/sessao`, `POST /api/logout`, `POST /api/senha` | sessão |
| `GET /api/cenarios`, `/api/estado`, `/api/eventos`, `/api/portes`, `/api/solicitacoes`, `/api/relatorios[/<SOL>]`, `/api/aprovacoes`, `/api/sequencia` | `PERM-SIM-VER` |
| `GET /api/explicar`, `/api/auditoria`, `/api/acesso/trilha` | `PERM-AUD-VER` |
| `GET /api/auditoria/exportar` | `PERM-AUD-EXPORTAR` |
| `GET /api/llm` | `PERM-MOD-VER` |
| `GET /api/modelos[/<arquivo>]`, `/api/dados` | `PERM-DAD-VER` |
| `POST /api/dados/planilha` | `PERM-DAD-ENVIAR` |
| `POST /api/comando` `pausar`, `retomar`, `passo`, `velocidade`, `reiniciar` | `PERM-SIM-OPERAR` |
| `POST /api/comando` `agente` | `PERM-AGT-ENERGIA` |
| `POST /api/comando` `solicitar` | `PERM-SOL-CRIAR` |
| `POST /api/comando` `decidir` | `PERM-APR-DECIDIR` |
| `POST /api/comando` `modelo` | `PERM-MOD-CONFIG` |

Ordem de checagem: origem (`Host`/`Origin` de loopback) → sessão (401) → senha temporária (403
IAM-02) → permissão da rota ou do comando (403 com a regra; rota fora da tabela é negada) → nos
POST, cabeçalho `X-SMA-Token` com o token CSRF da sessão. Cada comando aceito vira um registro
`operador` no trace com quem agiu; o pedido leva `solicitado_por` e a decisão leva o atestado da
pessoa ({doc}`acesso`).

## Cabeçalhos de segurança

Toda resposta leva (teste `test_security_headers_and_cookie_flags`):

| Cabeçalho | Valor |
|---|---|
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Cross-Origin-Opener-Policy` | `same-origin` |

As respostas da API vão com `Cache-Control: no-store`. O servidor escuta só em loopback e
continua autenticando antes de ler o corpo de um POST, com tempo limite de leitura
(TEST-73, TEST-90).

## Replay offline, sem login

`./iniciar.sh replay` (ou `bun run build` + servidor estático) abre o dashboard sem o servidor
Python: `GET /api/saude` falha, e a interface entra em **replay offline** dos traces exportados
em `web/public/traces/` (`python -m fin_mas export`, 37 cenários). Não há login porque não há
dado vivo nem comando: é a mesma leitura que `python -m fin_mas replay` faz no terminal. As
abas que dependem do servidor (Solicitações, Aprovações, Logs, Agentes e LLM) não aparecem.

## Testes de uso real

`web/e2e/acesso.spec.ts` (9 roteiros) e `web/e2e/areas.spec.ts` (6) sobem o servidor real com
as contas de demonstração e dirigem o Chrome pelo Playwright; `web/e2e/escritorio.spec.ts`
(14) continua cobrindo o escritório, agora autenticado. Lista completa em
{doc}`cenarios-de-teste`.

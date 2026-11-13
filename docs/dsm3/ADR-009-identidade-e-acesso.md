# ADR-009 — Identidade e acesso por pessoa

- **Status:** aceita (DSM3, 12/11/2026)
- **Requisitos:** {need}`REQ-S05`, {need}`REQ-S04`, {need}`REQ-O04`, {need}`REQ-S01`
- **Normas:** {need}`NORM-12`, {need}`NORM-13`, {need}`NORM-10`
- **Estende:** ADR-007 ({doc}`ADR-007-autenticidade-e-approval-gate`): a credencial continua
  por identidade no barramento; a decisão humana passa a valer pela **pessoa** autenticada

## Contexto

O ADR-007 fechou o barramento: só a caixa `APR`, com a credencial dela, emite `approve`. Mas a
caixa `APR` era alimentada pelo dashboard, e o dashboard tinha um único token de sessão (TEST-73
barrava outros sites, não outros processos locais). Quem lesse `/api/sessao` agia como o
aprovador. O {need}`REQ-O04` (dashboard autenticado, TEST-19) estava especificado desde a DSM1 e
não implementado. Faltavam também: quem pediu, quem operou e quem decidiu, como pessoas; o cargo
real para a POL-02; a segregação de funções contra a pessoa real (POL-03); e a regra de que quem
solicita não aprova.

## Decisão

**1. SVC-IAM: contas, sessões e papéis lidos dos modelos.** Senha com scrypt e sal; sessão com
token aleatório (o cadastro guarda só o SHA-256), 8 h de validade, 15 min de inatividade,
revogável; bloqueio após cinco senhas erradas; negado por padrão; papéis incompatíveis e último
administrador protegidos; papéis e permissões em `models/roles.yaml` e `models/permissions.yaml`.
Regras IAM-01 a IAM-07 ({doc}`acesso`).

**2. Atestado no conteúdo da decisão, não uma identidade de barramento por pessoa.** A pessoa
não vira agente. A caixa `APR` continua sendo a única identidade que emite `approve`/`reject`,
mas a mensagem leva um **atestado** `{pessoa, sessao, nonce, token}`: HMAC, com chave do
processo, sobre ticket, hash do veto, decisão, corpo da decisão, pessoa, sessão e nonce. O
SVC-POL confere o atestado (POL-09), o cargo da conta (POL-02), o vínculo com a pessoa do ERP
(POL-03) e quem pediu (POL-13), e registra a pessoa e a sessão no ticket.

**3. Cookie `HttpOnly` + token CSRF por sessão.** O navegador guarda a sessão num cookie
`HttpOnly; SameSite=Strict` (script da página não o lê); os POST exigem, além do cookie, o
cabeçalho `X-SMA-Token` com o token CSRF daquela sessão. Cada rota e cada comando têm uma
permissão; rota fora da tabela é negada. Cabeçalhos de segurança em toda resposta.

**4. Arquivo selado para o cadastro.** Contas e sessões em JSON com selo HMAC, contador contra
rollback (chave e contador fora da pasta de dados), gravação atômica e trava entre processos:
a TUI e o servidor alteram o mesmo cadastro, e a revogação vale na requisição seguinte.
Cadastro comprometido: ninguém entra (IAM-07). Trilha de acesso com cadeia de hashes e cabeça
selada fora da pasta.

**5. Administração no terminal, uso na web.** A TUI (Textual, opcional) e a CLI `acesso`
administram contas, papéis, sessões e trilha; o dashboard é para operar, pedir, decidir e
auditar.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Registrar cada pessoa como identidade no barramento (uma caixa por aprovador) | Mistura pessoas com agentes no diretório e nos papéis dos protocolos; cada conta nova exigiria registrar identidade e credencial no processo dos agentes. O atestado mantém o barramento como está (ADR-007) e leva a pessoa no conteúdo, onde a política já decide |
| Token de sessão no `localStorage` e cabeçalho `Authorization` | Qualquer script na página lê o token; com cookie `HttpOnly` + CSRF por sessão, nem script nem outro site obtêm os dois |
| Banco de dados (SQLite) para contas e sessões | Mais uma dependência e um formato sem selo; o arquivo selado repete o desenho já revisado da memória (SVC-MEM) e detecta edição e rollback |
| Assinatura do atestado com chave assimétrica e chave persistente | Permitiria verificar fora do processo, mas exige gestão de chaves; com HMAC de chave efêmera, um atestado não sobrevive a reinício, o que limita replay |
| Administração pelo dashboard web | Exporia as operações mais sensíveis na mesma superfície da operação diária; a TUI roda só para quem tem acesso à máquina e à pasta do cadastro |

## Consequências

- (+) A lacuna da primeira versão da DSM3 está fechada: o cenário `ataque_acesso` repete 15
  tentativas a partir da caixa `APR` e todas são recusadas ({need}`MET-17` = 0 aceitos).
- (+) Pedido, comando e decisão têm autor: `solicitado_por`, registro `operador`, `aprovado_por`
  com pessoa e sessão, e a trilha de acesso.
- (+) TEST-19 executado; as permissões são verificáveis rota a rota e comando a comando.
- (−) A chave do atestado só existe no processo do servidor: reiniciar invalida decisões
  pendentes já atestadas (por desenho), e a raiz de confiança continua sendo o processo.
- (−) O PROT-SOL leva `solicitado_por` sem atestado: a pessoa do pedido vem da camada de
  interface.

## Fica para a DSM4

- segundo fator de autenticação (2FA);
- delegação de alçada (férias, substituição);
- dupla aprovação (quatro olhos) acima de um valor;
- cofre de credenciais para as chaves de LLM e de integridade (hoje variável de ambiente e
  pasta local);
- atestado também no pedido (PROT-SOL).

---
orphan: true
---

# ADR-012 — Acesso avançado: segundo fator, alçada por pessoa, delegação, quatro olhos, cofre e empresas

- **Status:** aceita (DSM4)
- **Requisitos:** {need}`REQ-S06` (e {need}`REQ-S05`, que estende)
- **Normas:** {need}`NORM-14`, {need}`NORM-15`
- **Estende:** ADR-009 (SVC-IAM e decisão por pessoa autenticada)

## Contexto

Na DSM3 a decisão no Approval Gate passou a valer pela pessoa autenticada (POL-09), com o cargo
decidindo o *tipo* de decisão (POL-02), sem conflito de interesse (POL-03) e sem o solicitante
decidir o próprio pedido (POL-13). Ficaram abertos, de propósito:

1. a senha era o único fator de autenticação, inclusive para quem administra o acesso e para quem
   libera vetos;
2. o cargo dizia *o que* a pessoa decide, mas não *até quanto*: um gerente liberava um veto de
   qualquer valor;
3. sem delegação, a ausência do aprovador travava o fechamento até o prazo esgotar;
4. acima de valores materiais, uma pessoa só liberava (sem quatro olhos);
5. as chaves de LLM só existiam como variável de ambiente;
6. dois residuais da memória (SVC-MEM): uma cópia íntegra em outra pasta era tratada como
   comprometida, e duas execuções simultâneas sobre o mesmo arquivo perdiam entradas;
7. o cadastro atendia uma empresa só.

## Decisão

**Segundo fator (IAM-08).** TOTP da RFC 6238 implementado só com a biblioteca padrão (HMAC-SHA1,
passo de 30 s, 6 dígitos, janela de ±1 passo), conferido contra os vetores das RFCs 4226/6238.
Anti-replay pelo passo: guarda-se o último passo aceito e só se aceita um passo maior. Dez códigos
de recuperação de uso único, guardados como SHA-256. O segredo fica no cofre, não no `contas.json`.
Com o segundo fator ativo, a senha certa abre só uma **pré-sessão** de 5 minutos, que nenhuma rota
aceita como sessão e que só serve para `/api/login/2fa` (cookie próprio, restrito a esse caminho);
cinco códigos errados a derrubam. A política do cadastro (`exigir_2fa_para`) torna o segundo fator
obrigatório para ROLE-ADM e/ou ROLE-APR: a conta sem ele entra, mas só consegue ativá-lo.

**Alçada por pessoa (POL-10).** Com o SVC-IAM ligado, o AG-CIN informa no veto a `exposicao` (soma,
em centavos, dos lançamentos com achado crítico). A liberação (waiver ou correção) só vale se a
exposição couber em `limites_alcada` do porte para o cargo de quem decide; o cargo `controller`, que
não é cargo do ERP, usa a maior alçada do porte (`alcada_de_referencia` em `permissions.yaml`);
cargo sem linha nem referência não libera. Bloquear não libera valor e não depende de alçada.
`exposicao` é campo **opcional** novo no PROT-CMP e no PROT-APR e só aparece com o SVC-IAM: os
cenários revisados (nível básico, sem SVC-IAM) produzem exatamente os mesmos traces (guarda: 140
execuções, 0 hashes diferentes).

**Delegação (POL-11).** Um aprovador delega a outra conta aprovadora a sua alçada, com prazo, teto
e escopo (uma competência ou uma solicitação). A decisão cita a delegação; valem o cargo e a
alçada de quem delegou, limitados ao teto; POL-03 e POL-13 valem para as duas pessoas; a decisão
registra `por_delegacao_de`. Sem subdelegação, expira sozinha (relógio do SVC-IAM), revogável por
quem delegou ou pela administração de contas. A delegação entra no corpo coberto pelo atestado.

**Dupla aprovação (POL-12).** `dupla_aprovacao` por porte em `portes.yaml` (nulo em micro e
pequena; R$ 50 mil na média; R$ 25 mil na grande — acima das exposições dos cenários da DSM3).
Acima do limite, a primeira pessoa dá o aval com o performativo novo `endorse` (PENDENTE →
PENDENTE, o ticket conta o aval) e uma segunda pessoa, diferente (também por delegação), aprova a
mesma decisão. A decisão aceita leva `aval` em `aprovado_por`. INV-09 confere no trace.

**Escalonamento (POL-14).** Com `escalonamento_percentual` na política do cadastro, o ticket nasce
no menor nível de cargo do porte cuja alçada cobre a exposição; cargos acima só decidem depois que,
sem decisão em X% do prazo, o ticket escala um nível (uma vez, registrado no trace e na trilha).

**Cofre (IAM-10).** `services/cofre.py` sobre o `ArquivoSelado`, arquivo 0600 na pasta de chaves
(fora da pasta de dados). API: `guardar(nome, valor, ator)`, `ler(nome)`, `existe(nome)`,
`remover(nome, ator)`. A interface (API, CLI, TUI) só define, remove e vê nomes; o valor nunca
volta. `services/provedores.py` lê a chave do ambiente e, sem ela, do segredo `llm:<VARIAVEL>`.

**Memória (SVC-MEM) sobre o `ArquivoSelado`**, no mesmo formato em disco da v4 (selo e assinaturas
iguais; nada a migrar). Gravação e expiração acontecem na trava entre processos, relendo e juntando
o que o outro processo gravou. A cópia de outra pasta continua comprometida (falha fechada), com o
motivo "cópia íntegra de outra pasta"; `python -m fin_mas memoria adotar ARQUIVO` (sob
`PERM-MEM-ADOTAR`, registrado na trilha) confere selo e assinaturas com uma chave conhecida desta
máquina e passa a usá-la no caminho novo, com contador novo. Arquivo alterado não é adotado.

**Empresas (IAM-09).** Empresas no cadastro, escopo de empresas por conta, empresa ativa por sessão
(automática com uma só no escopo; `/api/empresa` e `--empresa` para trocar). Com empresas, toda
permissão que não é da administração do cadastro exige a empresa ativa e no escopo; o servidor
mantém uma simulação por empresa, com dados e memória em `dados/<empresa>/`, e a política recusa
decisão de sessão ativa em outra empresa.

## O que o cofre garante e o que não garante

| Garante | Não garante |
|---|---|
| integridade: selo HMAC com chave fora da pasta de dados, contador contra volta de versão; segredo alterado, removido ou recolocado fora do sistema deixa o cofre ilegível (falha fechada) | **confidencialidade contra quem lê o disco** com o usuário do processo ou como administrador da máquina: os valores ficam em claro dentro do arquivo selado |
| controle de acesso: arquivo 0600, fora da pasta de dados que se copia ou se envia | proteção se a pasta de chaves for copiada junto (ela é o segredo do selo) |
| a interface nunca recebe o valor; definir e remover exigem `PERM-MOD-SEGREDOS` e ficam na trilha | cifra em repouso: a biblioteca padrão não tem cifra autenticada e o projeto não inventa criptografia |

Para confidencialidade em repouso, troca-se o módulo por um cofre do sistema (Keychain, DPAPI,
libsecret) ou um gerenciador de segredos, mantendo a mesma API.

## Consequências

- Os cenários sem SVC-IAM são os mesmos byte a byte; os cenários da DSM3 com acesso mantêm os
  resultados (o veto deles passa a levar `exposicao`, dentro das alçadas).
- Cenários novos: `aprovador_sem_alcada`, `delegacao_valida`, `delegacao_expirada`,
  `dupla_aprovacao`, `dupla_mesma_pessoa_recusada`, `escalonamento`, `ataque_acesso_avancado`
  (12 ataques, nenhum aceito).
- No acesso simulado os ids de sessão passam a ser sequenciais (determinismo do trace quando um
  cenário abre sessões de verdade, como o de ataques).
- A trilha de acesso continua uma só por cadastro (o cadastro é global); os eventos de empresa
  levam o campo `empresa`.

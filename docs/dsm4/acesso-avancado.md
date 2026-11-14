# Acesso avançado (DSM4)

Decisão de arquitetura: [ADR-012](ADR-012-acesso-avancado.md). Requisito {need}`REQ-S06`; normas
{need}`NORM-14` e {need}`NORM-15`; métrica {need}`MET-19`.

## Regras

| Regra | O que exige | Onde |
|---|---|---|
| IAM-08 | segundo fator TOTP (±30 s, anti-replay), códigos de recuperação de uso único, pré-sessão de 5 min só para o código, obrigatoriedade pela política do cadastro | `services/totp.py`, `services/acesso_avancado.py` |
| IAM-09 | empresa ativa na sessão, dentro do escopo da conta, para toda permissão que não é do cadastro | `services/acesso_avancado.py`, `server_avancado.py` |
| IAM-10 | segredos só sob `PERM-MOD-SEGREDOS`; o valor nunca volta à interface | `services/cofre.py` |
| POL-10 | liberação só com a exposição dentro da alçada do cargo (ou do teto da delegação) | `services/politica.py` |
| POL-11 | delegação com prazo, teto e escopo, sem subdelegação, revogável | `services/acesso_avancado.py`, `services/politica.py` |
| POL-12 | acima de `dupla_aprovacao` do porte, aval (`endorse`) e aprovação de duas pessoas | `services/politica.py`, `models/protocols.yaml` |
| POL-14 | ticket nasce no nível de cargo que cobre a exposição e escala sem decisão em X% do prazo | `services/politica.py` |

Invariantes novos: INV-09 (liberação com dupla aprovação tem duas pessoas distintas) e INV-10
(exposição dentro da alçada efetiva de quem liberou).

## Permissões novas

`PERM-APR-DELEGAR` (ROLE-APR), `PERM-IAM-POLITICA`, `PERM-IAM-EMPRESAS`, `PERM-MOD-SEGREDOS` e
`PERM-MEM-ADOTAR` (ROLE-ADM).

## Como usar

Terminal (senhas, códigos e valores por variável de ambiente ou digitados, nunca por argumento):

```bash
python -m fin_mas acesso --como admin 2fa ativar          # mostra o segredo uma vez
FIN_MAS_CODIGO_2FA=123456 python -m fin_mas acesso --como admin 2fa confirmar   # códigos de recuperação
python -m fin_mas acesso --como admin politica definir --exigir-2fa ROLE-ADM,ROLE-APR --escalonamento 50
python -m fin_mas acesso --como diego delegacao criar ana --horas 8 --teto 1000000 --competencia 2026-09
python -m fin_mas acesso alcadas
python -m fin_mas acesso --como admin empresa criar alfa --nome "Alfa S.A." --porte media
python -m fin_mas acesso --como admin empresa escopo carla alfa
FIN_MAS_SEGREDO=... python -m fin_mas acesso --como admin segredo definir llm:ANTHROPIC_API_KEY
python -m fin_mas memoria --como admin adotar outra/pasta/memoria.json
```

Console (`python -m fin_mas acesso tui`): F6 segundo fator, F7 delegações, F9 alçadas, F10
política do cadastro, F11 cofre, F12 empresas; a entrada pede o código quando o segundo fator está
ativo.

API do dashboard: `POST /api/login` (com segundo fator: `{"segundo_fator": "pendente"}`, o número de
tentativas e o cookie da pré-sessão), `POST /api/login/2fa` (a recusa diz quantas tentativas restam
ou que a pré-sessão acabou), `GET /api/2fa`, `POST /api/2fa/ativar|confirmar|recuperacao|desativar`,
`GET|POST /api/empresa`, `GET|POST /api/segredos` (com a origem da chave de cada provedor de LLM:
ambiente, cofre ou nenhuma), `POST /api/segredos/remover`.

## No dashboard web

Decisão do dono do produto: o console (TUI) e a CLI são para **gerenciar** (contas, papéis, sessões,
política do cadastro, delegações, empresas e escopos); a web é para **usar** a plataforma. Por isso
o dashboard traz só o que a própria pessoa usa:

| O quê | Onde | Regra |
|---|---|---|
| Entrada em dois passos: depois da senha, o código do aplicativo ou um código de recuperação; erro genérico, tentativas e prazo vindos do servidor, volta ao início quando a pré-sessão acaba | tela de entrada (`components/Login.tsx`) | IAM-08 |
| Meu segundo fator: ativar (segredo, endereço `otpauth://` e códigos de recuperação mostrados uma vez), ver a situação, gerar novos códigos, desativar com confirmação | botão “Meu segundo fator” no cabeçalho (`components/SegundoFator.tsx`) | IAM-08 |
| Segundo fator exigido pela política: a conta sem ele cai direto na tela de ativação, inclusive quem já estava dentro quando a política mudou | antes do escritório | IAM-08 |
| Empresa ativa: escolha na entrada (conta com várias), seletor no cabeçalho só para quem tem mais de uma; a troca remonta o escritório sobre a simulação da empresa escolhida | cabeçalho (`components/Empresas.tsx`) | IAM-09 |
| Chave de LLM no cofre, por provedor: “há chave no ambiente / no cofre / não há”, definir (campo de senha, nunca reexibido) e remover | aba “Agentes e LLM”, só com `PERM-MOD-SEGREDOS` | IAM-10 |

Contas, papéis, sessões, política do cadastro, delegações e cadastro de empresas continuam só na
TUI e na CLI. Roteiros de interface: `web/e2e/avancado.spec.ts` (servidor e cadastro próprios, com o
TOTP calculado no teste pela RFC 6238).

## Cenários

| Cenário | Resultado esperado |
|---|---|
| `aprovador_sem_alcada` | gerente sem alçada no porte micro recusada (POL-10); o controller corrige |
| `delegacao_valida` | waiver de ana por delegação de diego aceito, registrado com `por_delegacao_de` |
| `delegacao_expirada` | delegação expirada recusada (POL-11); o próprio diego decide |
| `dupla_aprovacao` | carla dá o aval (`endorse`), diego aprova; `aprovado_por.aval` |
| `dupla_mesma_pessoa_recusada` | carla não aprova depois do próprio aval (POL-12); diego aprova |
| `escalonamento` | diretora recusada antes (POL-14); ticket escala para diretor na metade do prazo; ela decide |
| `ataque_acesso_avancado` | 12 ataques (TOTP repetido e fora da janela, recuperação reutilizada, pré-sessão em rota comum, delegação forjada/expirada/de outra pessoa/subdelegada, mesma pessoa nos dois passos, acima da alçada, outra empresa decide e troca de empresa), nenhum aceito |

## Memória (SVC-MEM)

O arquivo continua no formato v4 e passa a ser um `ArquivoSelado`: toda gravação e expiração
relê o arquivo dentro da trava e junta o que outro processo gravou (teste com quatro execuções
simultâneas sobre o mesmo arquivo). Uma cópia íntegra em outra pasta continua comprometida, agora
com o motivo explícito, até ser adotada com `memoria adotar` (sob permissão, na trilha). A API
pública (`Memoria`, `VisaoMemoria`, `gravar`, `consultar`, `expirar`, `pseudonimo`, `entradas`,
`comprometida`, `integra`) não mudou.

## Limites conhecidos

- O cofre garante integridade e controle de acesso, não confidencialidade contra quem lê o disco
  (ver a tabela da ADR-012).
- A trilha de acesso é uma por cadastro (o cadastro de contas é global); os eventos levam a empresa.
- O escalonamento sobe um nível, uma vez.
- Delegações, política do cadastro e gestão de contas e de empresas não têm tela no dashboard web
  (decisão de produto: ficam na TUI e na CLI).
- A ativação do segundo fator pela web mostra o segredo e o endereço `otpauth://` em texto; não há
  QR code (o dashboard não carrega bibliotecas além das que já usa).

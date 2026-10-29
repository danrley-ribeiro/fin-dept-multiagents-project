# Limitações

O que o protótipo **não** garante e por quê.

## Escopo adiado

- **LLM**: só o modo template; flag, mock de LLM, validação numérica do texto, cota e log de
  prompt ficam para a DSM3 (ADR-002), como recomendou o feedback.
- **Memória de longo prazo, registro de modelos e Approval Gate formal** ({need}`COMP-MEM`,
  {need}`COMP-MOD`, {need}`COMP-POL`): stubs. A decisão humana sobre o veto existe, mas não
  passa pelo PROT-APR.
- **Contract Net**: a coordenação é por delegação, consulta direta, veto e reserva; avaliar
  Contract Net para a alocação de verificações é tarefa da DSM3 (CP6).
- **Redaction e autenticação do dashboard**: o servidor escuta só em 127.0.0.1 e não tem
  login (TEST-19 segue planejado).
- **Experimento completo (CP12)**: a comparação com o baseline é uma prévia; perguntas,
  réplicas e sensibilidade ficam para a DSM4.

## Simplificações

- **Bus em processo**: um único fio e relógio lógico; não há concorrência real nem rede.
- **Dados sintéticos com gabarito**: plantios isolados; a escala por porte faz a receita
  anual cair na faixa legal, mas a estrutura (4 produtos, 2 UNs, 5 contas) é a mesma para
  todos os portes. Dados reais (planilha) não têm gabarito.
- **Regras por porte** são parâmetros de referência coerentes com a legislação de porte, não
  política de uma empresa real; ajuste em `models/portes.yaml` ou na planilha.
- **Humanos simulados**: no modo não interativo o aprovador segue um roteiro; no dashboard a
  decisão é do usuário.
- **Planilha**: um arquivo por competência e rateio fixo UN-A 60% / UN-B 40%.
- **Correção**: até 1 ciclo de correção (2 na micro) antes de bloquear; o AG-ORC não reavalia
  o orçamento depois de uma correção no ERP (só o AG-CIN reavalia o pacote).
- **`PROT-CMP` sem `timeout`**: o bus avisa o iniciador quando a contraparte não respondeu,
  sem alterar a FSM.
- **Baseline**: workflow mínimo da DSM1, sem laços de correção; ver ameaças à validade em
  {doc}`comparacao`.

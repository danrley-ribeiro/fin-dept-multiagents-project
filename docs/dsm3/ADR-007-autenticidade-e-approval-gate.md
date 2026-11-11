# ADR-007 — Autenticidade no barramento e Approval Gate para decisões humanas

- **Status:** aceita (DSM3, 10/11/2026)
- **Requisitos:** {need}`REQ-S04`, {need}`REQ-S01`, {need}`REQ-F05`, {need}`REQ-P01`
- **Normas:** {need}`NORM-09`, {need}`NORM-10`, {need}`NORM-01`, {need}`NORM-06`
- **Substitui em parte:** ADR-004 (o canal livre `protocol=None` deixa de existir)

## Contexto

No feedback da DSM2, o professor mostrou quatro falhas que a suíte não pegava:

1. uma mensagem `decisao_humana` vinda de um **remetente inexistente** liberou e publicou um
   fechamento vetado pelo AG-CIN;
2. uma **transição local** (`bus.advance`) atribuída a um identificador não autorizado mudou
   o estado de uma conversa;
3. uma resposta de protocolo **endereçada a quem não participava** da conversa foi aceita;
4. uma solicitação **sem campos obrigatórios** gerou `KeyError` e interrompeu a execução.

A causa comum: as FSMs controlavam *quais* transições eram válidas, mas não *quem* podia
dispará-las, *para quem* e *com qual conteúdo*. A decisão humana trafegava num canal sem
protocolo, sem vínculo com o veto e sem identidade verificada.

## Decisão

**1. O barramento valida tudo antes de mudar estado (fail-closed).** Ordem: autenticação
(identidade registrada + credencial emitida no registro), envelope, destinatário registrado,
protocolo e performativo conhecidos, papel do remetente autorizado para o performativo
(`emissores`), papel do destinatário participante, esquema do conteúdo (`esquemas`),
conversa (abertura só pelo performativo inicial, resposta só da outra ponta, transição da
FSM) e, por último, validadores do domínio (o SVC-POL no PROT-APR e no PROT-CMP). Toda
recusa vira um registro `rejected` com a etapa e o motivo e levanta `MensagemRejeitada`;
nenhuma conversa muda. Os campos ficam em `models/protocols.yaml`, a fonte única da DSM1.

**2. Transição local também é autorizada.** `advance` exige credencial e um papel listado em
`eventos_locais` (ex.: só o ROLE-ORQ aplica `publicar` no PROT-CMP; só o SVC-POL classifica
no PROT-APR). Performativo que só existe como evento local não pode ser enviado como mensagem.

**3. Decisão humana pelo Approval Gate (PROT-APR).** O veto vira um **ticket** do SVC-POL
vinculado à solicitação, à conversa vetada e ao ciclo, ao **hash SHA-256 dos achados**, ao
aprovador designado (com as decisões que o cadastro dele permite) e a um prazo. O
Orquestrador abre `propose-action`; o SVC-POL classifica (`require_approval` ou `deny`); só
o aprovador responde `approve` ou `reject`, citando ticket, solicitação e hash. A política
(POL-01 a POL-08, em {doc}`seguranca`) é aplicada no barramento; o ticket é de uso único: o
AG-CIN só aceita `waiver_humano` ou `correcao` que citem uma aprovação válida, ainda não usada,
daquele veto.

**4. Efeito externo só pelo gateway, com aprovação.** A correção no ERP (`erp.corrigir`) é a
única tool de escrita, está só na allowlist do Orquestrador e executa somente se o SVC-POL
confirmar o par (lançamento, ação) no ticket aprovado.

**5. Robustez.** O conteúdo é copiado no envio e conferido por hash na entrega; cada
destinatário recebe a sua cópia. Exceção de um agente vira `erro_agente` e, se a FSM
permitir, uma resposta explícita (`refuse`/`failure`/`not-understood`); a simulação segue.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Validar só nos agentes (cada um checa o remetente) | Repete a regra em seis lugares e deixa a FSM mudar antes da checagem; o problema da DSM2 era justamente o estado mudar no barramento |
| Assinatura criptográfica (HMAC/Ed25519) por mensagem | Num barramento em processo, a credencial por identidade dá a mesma garantia com menos código; fica como caminho para uma versão distribuída |
| Manter `decisao_humana` livre e só checar o remetente | Não resolve vínculo com o veto, reutilização, prazo, papel do aprovador nem SoD da aprovação |
| Rejeitar silenciosamente (sem exceção) | Esconde erros de programação; a exceção tipada é auditada e não interrompe a simulação, porque erros dentro de agentes são isolados |

## Consequências

- (+) Os quatro ataques do feedback e mais dez da mesma família são rejeitados e auditados
  (cenário `ataque_decisao_forjada`, MET-15 = 0 aceitos).
- (+) A decisão humana fica rastreável ponta a ponta: ticket, hash do veto, quem decidiu,
  justificativa, quando, e onde foi usada.
- (−) Custo de coordenação: +2 mensagens por decisão humana; sem decisão, o bloqueio espera o
  prazo do ticket (em `veto_bloqueio`, latência de 14 para 32 ticks). Ver {doc}`coordenacao`.
- (−) A credencial vale dentro do processo: quem tem acesso ao objeto Python do agente pode
  usá-la. É a raiz de confiança assumida (ver {doc}`limitacoes`).

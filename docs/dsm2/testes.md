# Testes

Três camadas, todas com o sistema de verdade (agentes sobre o bus, servidor, arquivos e
navegador). Não há chamadas à internet: o `tests/conftest.py` só libera o loopback
(127.0.0.1) e falha qualquer outro destino.

| Camada | Comando | Quantidade | O que roda |
|---|---|---|---|
| **e2e** (cenários) | `python -m pytest tests/e2e` | 90 | cenários completos sobre o bus, verificados pelo trace e pelo gabarito |
| **integração** | `python -m pytest tests/integration` | 10 | simulação ao vivo + servidor HTTP em loopback, exportação, relatório HTML, planilhas reais, servidor MCP de Excel por stdio |
| **uso real** (navegador) | `cd web && npm run test:e2e` | 14 | Playwright opera o Chrome instalado sobre o servidor Python verdadeiro |
| reducer do dashboard | `cd web && npm test` | 3 | estado do escritório reconstruído de traces reais exportados |

A pasta `tests/unit` guarda os 57 testes de FSM, bus, dataset e auditoria da primeira
versão da DSM2. Os testes novos desta revisão são todos e2e, de integração ou de uso real.

Um `TEST-*` só fica `executado` em `models/tests.yaml` se existir o teste com o mesmo nome
(função pytest ou `test("…")` do Playwright); o `tools/trace.py --check` verifica isso.

## Casos rastreados

```{needtable}
:types: test
:columns: id, title as "Teste", verifies as "Verifica", derived_from as "Derivado de", entrega, status
:style: table
```

## Testes de uso real (Playwright)

`web/e2e/escritorio.spec.ts`: primeira visita com o guia; pausar, avançar e retomar; veto
virando notificação e correção pelo humano, com a reconsideração visível na mente do AG-CIN;
waiver com justificativa obrigatória; desligar o AG-CIN e ver perdas, timeout,
replanejamento do AG-ORC e falha explícita; badges de novidade; novo pedido pelo diálogo e
pelo painel do Solicitante; *Períodos* e fontes de dados clicáveis; troca de porte para
micro; download do modelo e envio da planilha (válida e inválida); replay offline e
comparação; tema escuro lembrado.

## Ainda planejados

{need}`TEST-11`, {need}`TEST-12`, {need}`TEST-13`, {need}`TEST-15`, {need}`TEST-17`,
{need}`TEST-18`, {need}`TEST-19`, {need}`TEST-20`, {need}`TEST-21`, {need}`TEST-22`,
{need}`TEST-23` e {need}`TEST-25` dependem de serviços da DSM3 (memória, Approval Gate,
LLM, registro de modelos, redaction, versionamento).

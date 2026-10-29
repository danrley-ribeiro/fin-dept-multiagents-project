# Dashboard: o escritório da SMA

Interface web (Vite + React + TypeScript, Material Design com MUI) que mostra os agentes
trabalhando em um escritório: cada um na mesa do seu departamento, mensagens como envelopes
entre as mesas, chamadas às fontes de dados como traços discretos e a mente BDI de cada
agente ao lado. Fica em `web/` ({need}`COMP-OBS`).

## Como rodar

```bash
cd web && npm install && npm run build && cd ..
python -m fin_mas export                 # traces para o replay offline (web/public/traces)
python -m fin_mas serve                  # http://127.0.0.1:8765 (API + dashboard), sem internet
# desenvolvimento: python -m fin_mas serve  e, em outro terminal, cd web && npm run dev  (porta 5173)
```

## Dois modos

| Modo | Fonte | O que dá para fazer |
|---|---|---|
| **Ao vivo** | servidor Python local (`/api/eventos` por SSE + `/api/comando`) | pausar, avançar evento a evento, ritmo, reiniciar cenário, trocar porte, enviar planilha, **desligar/religar agentes**, novo pedido, **decidir vetos como humano** |
| **Replay offline** | `web/public/traces/*.json` exportados | reproduzir, voltar e avançar no tempo lógico, inspecionar mentes e chamadas, comparar com o baseline |

Os dois modos usam o mesmo reducer (`web/src/state/reducer.ts`), que reconstrói o
escritório **só a partir do trace**.

## Elementos

- **Planta**: Diretoria (Solicitante e Aprovador), Controles Internos (sala de vidro), Custos e
  Orçamento, Resultados e Relatórios, mesa central do Orquestrador, cofre de *Períodos*
  (PROT-LCK) e *Fontes de dados (MCP)* (ERP, Planilhas, Normas). Cada mesa mostra código,
  departamento e status (trabalhando, aguardando, vetando, fora de operação).
- **Badges**: número nas mesas e nos chips dos agentes = novidades ainda não vistas
  (decisões, deliberações, mudanças de intenção); nas abas da mente = itens novos; sino
  vermelho = vetos aguardando decisão humana; cofre = reservas ativas.
- **Clicáveis**: agentes (abrem a mente), *Períodos* (reservas e histórico), fontes de dados
  (chamadas MCP com proveniência e acesso aos modelos Excel), pedidos.
- **Mente do agente**: intenções (com histórico e motivos), deliberações (todas as opções,
  utilidade, aplicabilidade e motivo de descarte), crenças (com fonte e valor anterior),
  desejos, decisões e biblioteca de planos.
- **Decisão humana**: ao vivo, o veto do AG-CIN abre uma janela com achados e correções
  sugeridas: corrigir no ERP ou na planilha, waiver (com justificativa obrigatória) ou
  bloquear.
- **Dados da empresa**: escolher o porte (micro, pequena, média, grande) ou baixar os modelos
  e enviar a planilha de uma empresa sem ERP ({doc}`planilhas`).
- **SMA × workflow**: gráfico e tabela da {doc}`comparacao`.
- **Tema claro/escuro**, guia "Como usar" e navegação por teclado (mesas e fontes têm
  `role="button"`).

## Testes de uso real

`cd web && npm run test:e2e` builda o dashboard, sobe o **servidor Python verdadeiro** e
opera o **Chrome instalado** (Playwright, sem navegador baixado): guia da primeira visita,
pausa e passo, veto com correção e com waiver, desligar agentes, badges, novo pedido, troca
de porte, download do modelo e envio da planilha (válida e inválida), replay,
comparação e tema. `npm test` roda os testes do reducer sobre traces reais exportados.

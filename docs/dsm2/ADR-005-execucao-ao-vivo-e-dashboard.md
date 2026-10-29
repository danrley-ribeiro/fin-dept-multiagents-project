# ADR-005 — Execução ao vivo e dashboard sobre o mesmo trace

**Status:** aceita (DSM2 revisada) · **Contexto:** feedback pediu observabilidade de crenças,
objetivos, intenções e decisões; o grupo pediu um dashboard em que os agentes apareçam
trabalhando, que funcione offline e permita pausar e desligar agentes.

## Decisão

1. **O trace é a única fonte da interface.** O bus e os agentes já gravam tudo no `AuditLog`
   (mensagens, `belief`, `desire`, `deliberation`, `intention`, `decision`). O dashboard
   reconstrói o escritório só a partir desses registros, com o mesmo reducer no modo ao vivo
   e no replay.
2. **Execução ao vivo ritmada sobre o bus determinístico.** `Simulacao` (`src/fin_mas/live.py`)
   avança o mesmo bus evento a evento (`Bus.step()`), com `ms_por_tick` de parede por tick
   lógico. Comandos chegam por uma fila thread-safe; desligar um agente é feito pelo bus (o
   que chega a ele se perde), sem lógica especial: timeouts e replanejamentos surgem dos
   próprios protocolos.
3. **Servidor só com a biblioteca padrão** (`ThreadingHTTPServer`, SSE e JSON), em
   `127.0.0.1`. Não acrescenta dependência Python, funciona sem internet e serve o build do
   dashboard.
4. **Frontend Vite + React + MUI**, com fontes locais (Roboto via `@fontsource`): nenhuma
   chamada externa em tempo de execução.

## Alternativas descartadas

- *WebSocket*: precisaria de dependência; os comandos são raros e cabem em `POST`.
- *Simular os agentes no navegador*: duplicaria a lógica e quebraria a fonte única.
- *Polling do snapshot*: perderia a ordem causal e as animações por evento.

## Consequências

- Determinismo preservado no modo não interativo (mesmo hash por seed); no modo interativo a
  ordem depende das decisões humanas, que ficam registradas no trace como `ui`.
- O replay offline vem de `python -m fin_mas export`.
- Testes: TEST-34 (simulação + servidor HTTP em loopback) e a suíte Playwright de uso real.

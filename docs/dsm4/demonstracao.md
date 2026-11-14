# Roteiro de demonstração (10 minutos)

Uma falha controlada, um ataque recusado, um teste, um resultado experimental e o dashboard, com os
comandos exatos e o que observar. Os slides e as falas estão em `entregas/dsm4/apresentacao/`
(`slides.md` e `roteiro.md`).

## Antes de começar (fora do tempo)

```bash
cd fin-dept-multiagents-project
source .venv/bin/activate            # ou: python3 tools/iniciar.py instalar
export PYTHONPATH=src                # no checkout; com o pacote instalado, use fin-mas no lugar de python -m fin_mas
export FIN_MAS_DIR_CHAVES=/tmp/sma-chaves   # chaves de demonstração fora da sua pasta de chaves
python -m fin_mas cenarios --verificar      # aquecimento: todos "ok" e "sim" (alguns segundos)
```

Num segundo terminal, deixe o escritório no ar e o navegador aberto em `http://127.0.0.1:8765`:

```bash
python -m fin_mas serve --demo               # contas de demonstração, senha Demonstracao-SMA-2026
```

Use fonte grande no terminal e `| less -R` quando a saída for longa.

## Roteiro

| Tempo | Passo | Comando | O que observar |
|---|---|---|---|
| 0:00 | Abertura | — | O problema (fechar o mês e avaliar o orçamento com regras por porte e decisão humana) e a pergunta da DSM4: com as mesmas funções, agentes valem a pena? |
| 1:00 | Caminho com veto | `python -m fin_mas run --scenario veto_correcao` | `DECISAO AG-CIN ... P-VETAR-COM-CORRECAO`, `veto [EM_ANALISE -> VETADO]`, `POLITICA POL-01 ticket emitido`, `propose-action`, `approve`, `erp.corrigir` com a aprovação e o AG-CIN reavaliando até `conforme`. Quem calcula não aprova; quem veta é independente. |
| 2:30 | Falha controlada | `python -m fin_mas run --scenario res_insumo_faltante --porte grande \| grep -E "AG-RES\|resposta final"` | O AG-ORC não responde; o AG-RES delibera `P-CONSULTAR-DE-NOVO`, depois `P-DAR-POR-INDISPONIVEL` e, na grande, `P-FALHAR-EXPLICITAMENTE` (a completude pesa mais; na média seria `P-CONSOLIDAR-COM-RESSALVA`). O Orquestrador reenvia a subtarefa (`DEL-004`) e a resposta final é `inform`. Falha explícita, não silêncio. |
| 4:00 | Ataque recusado | `python -m fin_mas run --scenario ataque_acesso \| tail -5` | `ATAQUES 15 de 15 rejeitados`: quem controla a caixa do aprovador tenta decidir sem ser a pessoa certa (sem atestado, atestado forjado, replay, cargo sem alçada, envolvido, solicitante). O ticket expira e nada é publicado. |
| 5:00 | Trace íntegro | `python -m fin_mas run --scenario ataque_decisao_forjada --trace a.jsonl` e `python -m fin_mas verificar a.jsonl --ancora 2586f2c81fc2cc1c1739c12be744fce07eb2619044a5c337d2c6e1666becc76e` | "cadeia de hashes íntegra, âncora ... confere"; a âncora é a mesma em qualquer máquina. `python -m fin_mas invariantes a.jsonl` mostra "8 invariantes, 0 violação(ões)" (o número de invariantes cresce com o acesso avançado). |
| 6:00 | Um teste | `python -m pytest tests/e2e/test_equivalencia_workflow.py -q` | Cerca de 5 s, todos passam: o workflow equivalente e o SMA básico dão o mesmo resultado sem falhas nos cenários comparáveis e em cargas sorteadas. É o teste que sustenta a palavra "equivalente". |
| 7:00 | Resultado experimental | `python -m fin_mas experimento --rapido --out /tmp/exp` e abrir `docs/dsm4/resultados/fig_robustez.svg` | O modo rápido roda o aparato inteiro em 3 seeds em segundos (não é o resultado, é a prova de que o comando funciona). Na figura das 30 seeds: o SMA perde em robustez a partir de 15% de perda; empata sem falhas; nenhum braço publica crítica sem tratamento. Dizer em voz alta: com funções iguais, o SMA empata em qualidade e perde em custo e robustez. |
| 8:30 | Dashboard | navegador, conta `avaliador` | Escritório ao vivo; área Aprovações com o prazo; mente do AG-ORC com crenças, desejos e deliberações; Logs filtráveis por agente. |
| 9:30 | Fechamento | — | O que o SMA entrega que o workflow não entrega (separação auditável, veto independente, decisão atestada, negociação, extensibilidade) e as limitações ({doc}`limitacoes`). |

## Plano B (se algo falhar ao vivo)

| Falha | O que fazer |
|---|---|
| `.venv` ausente ou dependência faltando | `python3 tools/iniciar.py cli --cenario veto_correcao` prepara o ambiente e roda o cenário |
| Dashboard não sobe ou o navegador não conecta | `./iniciar.sh replay` (traces exportados, sem servidor Python, em `http://127.0.0.1:4173`); ou mostrar o mesmo cenário no terminal |
| Porta 8765 ocupada | `python -m fin_mas serve --demo --porta 8766` |
| `experimento --rapido` lento ou com erro | mostrar o que está versionado: `docs/dsm4/resultados/resumo.md`, as figuras SVG e `manifesto.json` (com o SHA-256 do CSV) |
| A âncora não confere | rodar `python -m fin_mas verificar a.jsonl` sem a âncora (cadeia íntegra com a chave local) e explicar que a âncora muda se o cenário mudar |
| O teste demora (máquina lenta) | `python -m pytest tests/e2e/test_protocolos_invalidos.py -q` (transições inválidas dos protocolos) |
| Projetor sem terminal legível | slides com as capturas e a página {doc}`resultados` no navegador |

## Perguntas prováveis

- **Por que o workflow ganha em robustez?** Porque o modelo de falhas só atinge mensagens entre
  componentes, e o workflow monolítico não as tem; a comparação mede o preço da distribuição. Um
  workflow distribuído, que seria a linha de base justa para robustez, não foi construído.
- **Então para que agentes?** Pelo que o experimento só mede indiretamente: separação de autoridade,
  menor privilégio por agente, veto independente, decisão humana atestada, trilha de quem decidiu.
  Isso se manteve com o sistema degradado (nenhum ataque aceito indevidamente, nenhuma crítica
  publicada sem tratamento).
- **E a cognição?** Não mostrou ganho na medida registrada. O AG-REL BDI não se justifica; o AG-RES
  sim (dependência, prazo, incerteza). Está no ADR-010.
- **O LLM decide alguma coisa?** Não. Propõe hipóteses que viram ação epistêmica só depois de cinco
  regras determinísticas; quem muda a avaliação é a evidência. Fica fora do experimento.

# Roteiro da apresentação — DSM4

**Slides:** [`DSM4-apresentacao.pptx`](DSM4-apresentacao.pptx), gerado de [`slides.md`](slides.md) por
`make apresentacao-dsm4` (pandoc, com o tema do deck da DSM2). As falas resumidas também estão nas notas do
apresentador. **Duração:** 10 minutos, mais as perguntas. **Quem fala:** Danrley (D) e Jiliard (J).
**Tom:** mostrar o sistema e dizer o que o experimento mostrou, inclusive o que é desfavorável.

## Antes de começar

Terminal 1, na raiz do repositório (fonte grande):

```bash
source .venv/bin/activate && export PYTHONPATH=src
export FIN_MAS_DIR_CHAVES=/tmp/sma-chaves
python -m fin_mas cenarios --verificar            # aquecimento, todos "ok" e "sim"
```

Terminal 2: `python -m fin_mas serve --demo` e o navegador aberto em `http://127.0.0.1:8765`, logado como
`avaliador` (senha `Demonstracao-SMA-2026`). Deixar aberta a figura `docs/dsm4/resultados/fig_robustez.svg`.

## Falas por slide

| # | Slide | Quem | Tempo | O que dizer e fazer |
|---|---|---|---|---|
| 1 | Capa | D | 0:15 | A dupla e o que vem: o sistema final, o experimento e o que ele mostrou, inclusive contra nós. |
| 2 | O problema | D | 0:40 | Fechar o mês com fontes que divergem, regras por porte e decisão humana. Por que agentes. A pergunta: com as mesmas funções, agentes valem a pena? |
| 3 | Arquitetura final | D | 0:50 | Uma frase por camada. Quem calcula não aprova; o AG-CIN veta sozinho; a decisão humana tem dono. BDI onde há escolha sob incerteza (ADR-010). |
| 4 | Approval Gate | D | 0:40 | A FSM é dado, conferida pelo barramento antes de mudar estado. Cada transição inválida é um teste negativo. |
| 5 | Coordenação | J | 0:40 | Consulta direta, veto, correção, reserva, negociação. A regra "waiver não se repete" emerge de três componentes. |
| 6 | Segurança | J | 0:40 | Ataques com o sistema em pé e invariantes conferidos só pelo trace. Fora do modelo: quem controla o processo ou a pasta de chaves. |
| 7 | Cognição | J | 0:40 | Proposta não é crença; guardrail determinístico, não outro modelo. O AG-REL BDI não se justificou e está escrito. |
| 8 | Experimento: desenho | J | 0:45 | Pré-registro antes do código; workflow com as mesmas funções; falhas sorteadas por seed; 30 seeds. Responde às duas críticas da DSM3. |
| 9 | Qualidade e robustez | J | 0:45 | Empate sem falhas; o SMA perde a partir de 15% de perda; empate com humano lento; nenhuma crítica publicada. O workflow ganha por construção. |
| 10 | Custo, cognição, ablação, rodadas | D | 0:45 | Mais mensagens e ticks; cognição sem ganho significativo; reenvio, reserva e correção valem; a primeira rodada achou um defeito; a segunda não é confirmatória. **Passa para a demonstração.** |
| 11 | Demonstração | D + J | 2:00 | Comandos abaixo. |
| 12 | Limitações | J | 0:30 | As que mais pesam; a lista completa está na documentação. |
| 13 | Lições | D | 0:30 | Linha de base justa mudou a conclusão; falhas sorteadas acharam defeito; o que o SMA entrega é estrutural. |

## Demonstração (slide 11, 2 minutos)

O roteiro longo, com o que observar e o plano B, está em
[`docs/dsm4/demonstracao.md`](../../../docs/dsm4/demonstracao.md). Na apresentação, a versão curta:

1. **Falha controlada** (J):
   `python -m fin_mas run --scenario res_insumo_faltante --porte grande | grep -E "AG-RES|resposta final"`.
   Apontar `P-FALHAR-EXPLICITAMENTE` (na grande a completude pesa mais), o reenvio do Orquestrador e a
   resposta final `inform`.
2. **Ataque recusado** (J): `python -m fin_mas run --scenario ataque_acesso | tail -5` →
   `ATAQUES 15 de 15 rejeitados`; nada publicado.
3. **Um teste** (D): `python -m pytest tests/e2e/test_equivalencia_workflow.py -q` (cerca de 5 s):
   é o teste que sustenta a palavra "equivalente".
4. **Resultado experimental** (D): `python -m fin_mas experimento --rapido --out /tmp/exp` (segundos; prova
   que o aparato roda) e a figura `fig_robustez.svg` das 30 seeds.
5. Se sobrar tempo: o dashboard, área Aprovações e a mente do AG-ORC.

**Plano B:** sem ambiente, `python3 tools/iniciar.py cli --cenario veto_correcao`; sem dashboard,
`./iniciar.sh replay`; sem experimento, `docs/dsm4/resultados/resumo.md` e as figuras versionadas.

## Perguntas prováveis

- **Por que o workflow é mais robusto?** O modelo de falhas só atinge mensagens entre componentes; o
  experimento mede o preço da distribuição. Um workflow distribuído não foi construído (limitação).
- **Então para que agentes?** Separação auditável de responsabilidades, veto independente, decisão humana
  atestada, negociação, extensibilidade. Nenhum ataque aceito e nenhuma crítica publicada com o sistema
  degradado. Não é vitória numérica, e não dizemos que é.
- **A cognição ajudou?** Na medida registrada, não. Há um sinal exploratório, não significativo.
- **O LLM decide algo?** Não. Propõe; regras determinísticas validam; a evidência decide. Fora do experimento.
- **A segunda rodada não é ajuste aos dados?** É, e por isso não é confirmatória. Vale o que as duas rodadas
  têm em comum.

## Critérios do enunciado → slides

| Critério | Slides |
|---|---|
| Sistema final e corretude | 3, 4, 6, 11 |
| Arquitetura e SMA | 3, 4, 5, 7 |
| Experimentação e análise | 8, 9, 10 |
| Testes e reprodutibilidade | 8, 11 |
| Documentação | 12, 13 |
| Demonstração e autoria | 11 |

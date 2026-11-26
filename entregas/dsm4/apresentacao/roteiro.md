# Roteiro do vídeo — DSM4

A apresentação da DSM4 é um **vídeo gravado**, sem perguntas ao vivo. Por isso o vídeo responde, na
própria narração, ao que o professor pediu no feedback da DSM3. **Duração-alvo:** cerca de 15 minutos.
**Quem fala:** Danrley (D) e Jiliard (J), os dois explicando a arquitetura e a segurança.
**Tom:** mostrar o sistema e dizer o que o experimento mostrou, inclusive o que nos é desfavorável.

**Slides:** [`DSM4-apresentacao.pptx`](DSM4-apresentacao.pptx), gerado de [`slides.md`](slides.md) por
`make apresentacao-dsm4` (pandoc, com o tema do deck da DSM2). As falas resumidas estão nas notas do
apresentador. O roteiro longo da demonstração, com plano B, está em
[`docs/dsm4/demonstracao.md`](../../../docs/dsm4/demonstracao.md).

## O que o vídeo precisa mostrar (feedback da DSM3)

| Pedido | Onde, no vídeo |
|---|---|
| Uma negociação de prazo | Demonstração 1 (`negociacao_prazo`) |
| Uma hipótese confirmada ou refutada por outro agente | Demonstrações 2 e 3 (`orc_hipotese_local`, `hipotese_refutada`) |
| Um fechamento bloqueado | Demonstração 4 (`veto_bloqueio`) |
| Uma aprovação indevida rejeitada | Demonstração 5 (`ataque_decisao_forjada`) e cena 6 no dashboard (`decisao_por_pessoa`) |
| Os dois autores explicando arquitetura e segurança | Slides 3 a 5 e 7, divididos entre D e J |
| POL-06 sob concorrência, memória, permissões, ZIP, experimento | Slides 13 e 14 e cena 7 (teste dos dois processos) |

## Preparar a gravação (fora do tempo)

- Gravar a tela em 1920×1080, com o terminal em fonte de 16 pt ou mais e tema claro. Fechar
  notificações. Gravar cada bloco separado e juntar na edição: um erro custa um bloco, não o vídeo.
- Câmera opcional; a voz de quem fala deve combinar com a coluna "Quem" abaixo. Cada um se apresenta
  na primeira fala.
- Ensaiar uma vez com cronômetro. Se passar de 17 minutos, cortar falas dos slides 9 a 12, nunca as
  demonstrações.
- Exportar em MP4 (H.264) e publicar como link não listado; o link vai no `README.md` da entrega.

Terminal 1, na raiz do repositório:

```bash
source .venv/bin/activate && export PYTHONPATH=src
export FIN_MAS_DIR_CHAVES=/tmp/sma-chaves
python -m fin_mas cenarios --verificar            # aquecimento, todos "ok" e "sim"
```

No Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "src"; $env:PYTHONIOENCODING = "utf-8"
$env:FIN_MAS_DIR_CHAVES = "$env:TEMP\sma-chaves"
python -m fin_mas cenarios --verificar
```

Terminal 2: `python -m fin_mas serve --demo` e o navegador em `http://127.0.0.1:8765`. A tela de
entrada mostra a conta de demonstração; todas usam a senha `Demonstracao-SMA-2026`. Deixar abertas
duas janelas anônimas (uma para `carla`, outra para `diego`) e a figura
`docs/dsm4/resultados/fig_robustez.svg`.

## Falas por slide

| # | Slide | Quem | Tempo | O que dizer e fazer |
|---|---|---|---|---|
| 1 | Capa | D + J | 0:20 | Cada um se apresenta. O que vem: o sistema final, o experimento, o que ele mostrou (inclusive contra nós) e as respostas ao feedback da DSM3. |
| 2 | O problema | D | 0:40 | Fechar o mês com fontes que divergem, regras por porte e decisão humana. Por que agentes. A pergunta: com as mesmas funções, agentes valem a pena? |
| 3 | Arquitetura final | D | 0:50 | Camadas de cima para baixo até o barramento: interfaces, fronteira (loopback e SVC-IAM), Orquestrador, especialistas. Quem calcula não aprova; o AG-CIN veta sozinho; BDI onde há escolha sob incerteza (ADR-010). |
| 3 | Arquitetura final | J | 0:30 | O resto das camadas: barramento que confere remetente, papel, contraparte, esquema, FSM e política; serviços (Approval Gate, reserva, memória, trace encadeado); fontes atrás do gateway MCP com allowlist. |
| 4 | Approval Gate (FSM) | J | 0:25 | A FSM é dado (`models/protocols.yaml`), conferida pelo barramento antes de mudar o estado. |
| 5 | O que o Approval Gate confere | D | 0:35 | Ticket com hash do veto; a decisão vale pela pessoa (atestado, cargo, alçada, envolvido, solicitante). Cada transição inválida é um teste negativo. |
| 6 | Coordenação | J | 0:40 | Consulta direta, veto, correção, reserva, negociação. "Waiver não se repete" emerge de memória, crença do AG-CIN e política. |
| 7 | Segurança | D | 0:35 | O barramento recusa remetente sem credencial, papel errado, contraparte fora da conversa e transição fora da FSM: 14 ataques ao barramento e 15 à decisão por pessoa, todos recusados. |
| 7 | Segurança | J | 0:35 | Acesso avançado (segundo fator, alçada por pessoa, delegação, dupla aprovação) e invariantes conferidos só pelo trace, com cadeia de hashes e âncora. Fora do modelo: quem controla o processo ou a pasta de chaves. |
| 8 | Cognição | J | 0:30 | Proposta não é crença; guardrail determinístico, não outro modelo. O AG-REL BDI não se justificou e está escrito. |
| 9 | Experimento: desenho | J | 0:40 | Pré-registro antes do código; workflow com as mesmas funções; falhas sorteadas por seed; 30 seeds. Responde às duas críticas da DSM3. |
| 10 | Qualidade e robustez | D | 0:40 | Empate sem falhas (em boa parte por construção); o SMA perde a partir de 15% de perda (64,2% contra 100%); nenhuma crítica publicada. O workflow ganha por construção. |
| 11 | Custo, cognição, ablação, ataques | D | 0:40 | Mais mensagens (firme); cognição sem ganho significativo; reenvio, reserva e correção valem; no bloco D, 4 ataques aceitos sem a premissa e H6b não testada. |
| 12 | Três rodadas | J | 0:25 | A primeira achou o silêncio, a segunda mediu a correção, a terceira a versão 1.0.0. Nenhuma posterior é confirmatória. |
| 13 | Bloco E | J | 0:50 | Pedidos concorrentes: a reserva impede publicar o mesmo mês duas vezes; meses diferentes em paralelo. Frequência muda o custo, não a qualidade. Volume: ticks iguais, tempo de parede cresce. Exploratório; as métricas agora variam entre seeds (desvio-padrão nas tabelas). |
| 14 | Revisão final | D | 0:45 | Um item por pedido do professor, cada um com o seu teste. **Passa para a demonstração.** |
| 15 | Demonstração | D + J | 5:00 | Blocos abaixo. |
| 16 | Limitações | J | 0:30 | As que mais pesam, inclusive o waiver gravado antes da entrega da decisão; a lista completa está na documentação. |
| 17 | Lições | D | 0:30 | A linha de base justa mudou a conclusão; falhas sorteadas e uma correção independente acharam defeitos; o que o SMA entrega é estrutural. |

## Demonstração (slide 15, cerca de 5 minutos)

Cada comando vai com um filtro, para a tela mostrar só as linhas que importam. No PowerShell, troque
`| grep -E "..."` por `| Select-String -Pattern "..."`.

1. **Jiliard: negociação de prazo** (0:50).

   ```bash
   python -m fin_mas run --scenario negociacao_prazo | grep -E "P-NEGOCIAR-PRAZO adotada|propose|accept-proposal|confirmada \(|resposta final"
   ```

   Narrar: duas consultas ao AG-CIN se perdem. O AG-ORC delibera `P-NEGOCIAR-PRAZO`. Ele envia
   `propose` e o estado vai para `[EM_EXECUCAO -> NEGOCIANDO]`. O Orquestrador responde
   `accept-proposal` por regra, sem LLM. Com o prazo novo, a hipótese é confirmada.

2. **Jiliard: hipótese confirmada por outro agente** (0:40).

   ```bash
   python -m fin_mas run --scenario orc_hipotese_local | grep -E "HIPOTESE|QRY-002  AG-ORC|NORM-11|resposta final"
   ```

   Narrar: a hipótese `AG-ORC-H001` nasce de uma regra local, sobre um lançamento que parece duplicado.
   Ela não muda a avaliação. O AG-ORC pergunta ao AG-CIN (`QRY-002`), e só a resposta dele a confirma:
   "AG-CIN contesta R$ 21.005,86". A NORM-11 aparece no trace.

3. **Jiliard: hipótese refutada** (0:25).

   ```bash
   python -m fin_mas run --scenario hipotese_refutada | grep -E "HIPOTESE|resposta final"
   ```

   Narrar: a mesma regra dispara num alarme falso. Ela é refutada porque o AG-CIN não contesta os
   lançamentos, e o desvio segue sinalizado como orçamentário.

4. **Danrley: fechamento bloqueado** (0:40).

   ```bash
   python -m fin_mas run --scenario veto_bloqueio | grep -E "parecer veto|POLITICA|BLOQUEADO|resposta final"
   ```

   Narrar: a alçada foi violada e o AG-CIN veta (NORM-04). A política emite o ticket com as opções
   abertas. Ninguém decide, o prazo esgota (POL-08) e o fechamento fica `BLOQUEADO`. Não há
   publicação por omissão.

5. **Danrley: aprovação indevida recusada** (0:50).

   ```bash
   python -m fin_mas run --scenario ataque_decisao_forjada | grep -E "REJEITADA|ATAQUES|resposta final"
   ```

   Narrar algumas linhas: remetente desconhecido, credencial ausente e papel que não pode emitir
   `approve`. Um hash do veto que não confere também é recusado, assim como um `execute` em PENDENTE.
   Resultado: `ATAQUES 14 de 14 rejeitados`, e a resposta final é `failure`, não publicação.

6. **Danrley: a decisão é da pessoa, no dashboard** (1:00). Na conta `avaliador`, reinicie o cenário
   `decisao_por_pessoa`. Na janela da `carla`, abra a aba **Aprovações**. O ticket mostra
   "POL-03: você participou de um lançamento vetado", com **Decidir** desabilitado. Na janela do
   `diego`, clique em **Decidir** e depois em **Corrigir no ERP**. O histórico registra "diego
   (gerente)" e a solicitação fica `publicado`. Narrar: uma conta opera e outra aprova, e quem
   reiniciou o cenário também não aprovaria (POL-13).

7. **Jiliard: POL-06 com dois fechamentos simultâneos** (0:35).

   ```bash
   python -m pytest tests/e2e/test_approval_gate.py tests/e2e/test_revisao_dsm4.py -q -k "recurrence or processos or memory or waiver"
   ```

   Narrar: agosto e setembro têm a mesma violação, cada um com o seu ticket. Só o primeiro waiver
   passa; o segundo é recusado pela POL-06 e perde a opção. No TEST-459 isso vale com dois processos
   sobre o mesmo arquivo de memória.

**Plano B:** sem ambiente, `python3 tools/iniciar.py cli --cenario veto_correcao`; sem dashboard,
`./iniciar.sh replay` e a cena 6 vira o cenário `decisao_por_pessoa` no terminal; sem experimento,
`docs/dsm4/resultados/resumo.md` e as figuras versionadas.

## Critérios do enunciado → vídeo

| Critério | Slides e cenas |
|---|---|
| Sistema final e corretude | 3, 4, 5, 7, 14; demonstrações 1 a 7 |
| Arquitetura e SMA | 3, 4, 5, 6, 8; demonstrações 1 a 3 |
| Experimentação e análise | 9 a 13 |
| Testes e reprodutibilidade | 9, 14; demonstração 7 |
| Documentação | 16, 17 |
| Demonstração, apresentação e autoria | 15; os dois autores falam em todos os blocos |

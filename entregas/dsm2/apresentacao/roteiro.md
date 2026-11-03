# Roteiro da apresentação — DSM2

**Slides:** [`DSM2-apresentacao.pptx`](DSM2-apresentacao.pptx). As falas também estão nas notas do apresentador.
**Duração:** cerca de 14 minutos, mais as perguntas. **Quem fala:** Danrley (D) e Jiliard (J).
**Foco:** a aplicação, a solução e as escolhas de projeto. Não é um pitch.

## A aplicação até agora (para os dois estudarem antes)

- **DSM1:** modelamos a controladoria da empresa fictícia **SMA**. Ali definimos os requisitos, seis agentes com
  papéis, os protocolos (como máquinas de estados), as normas e as métricas. Tudo fica em `models/*.yaml` e é
  rastreável pelo `tools/trace.py --check`.
- **DSM2:** o protótipo executável dessa modelagem, em Python 3.12, sem rede e determinístico.
  - **Seis agentes** conversam por um **barramento A2A**. AG-ORC (Orçamento) e AG-CIN (Controles Internos) são **BDI**.
  - **Ambiente:** a SMA simulada (seed + gabarito), regras por **porte** (micro a grande) ou **planilha** de
    empresa sem ERP. Os agentes só acessam os dados por ferramentas **MCP**.
  - **Interações:** fechar o mês, avaliar o orçamento, consultar direto ORC→CIN e vetar com correção ou waiver humano.
  - **Observabilidade:** trace JSONL, replay por `conversation_id` e um **dashboard** em que os agentes aparecem
    trabalhando num escritório.
  - **Verificação:** testes e2e, de integração e de uso real no Chrome, e a comparação com o workflow centralizado da DSM1.
- **Como rodar:** `.\iniciar.ps1` abre o escritório ao vivo e `.\iniciar.ps1 testes` roda todos os testes.

## Falas por slide

| # | Slide | Quem | Tempo | O que dizer (resumo) |
|---|---|---|---|---|
| 1 | Capa | D | 0:20 | Apresenta a dupla. A DSM2 é o protótipo executável da DSM1. Vamos mostrar como a aplicação funciona e por que foi construída assim. |
| 2 | O que a aplicação faz | D | 1:00 | O fluxo de ponta a ponta: pedido → Orquestrador → especialistas → Controles (com humano no veto) → relatório. Os dados vêm de um ERP simulado ou de planilhas, e as regras mudam com o porte. |
| 3 | Arquitetura em camadas | D | 1:00 | Uma frase por camada: onde o usuário pede, quem distribui, quem entrega as mensagens, quem trabalha, de onde vêm os dados e o que fica registrado. |
| 4 | Onde os agentes rodam | D | 1:15 | É um programa Python comum: cada agente é um objeto e um relógio próprio ordena as mensagens (mostrar a fila). Por isso roda sem internet, sempre dá o mesmo resultado e dá para provocar falhas. SPADE/JADE e LLM foram descartados (ADR-003). |
| 5 | Outras escolhas | D | 1:00 | As conversas seguem os protocolos da DSM1. Os agentes não tocam nos dados direto. Só dois agentes "pensam" (BDI). Serve para qualquer porte. |
| 6 | Agentes e ambiente | D | 0:50 | Cada agente tem uma natureza declarada. Ambiente simulado com gabarito, ou planilha real. **Passa para o Jiliard.** |
| 7 | Ciclo BDI | J | 1:15 | Nos BDI: percepção → crenças → desejos → deliberação → intenção. Ler o trecho do trace: o AG-ORC escolhe consultar o AG-CIN antes de sinalizar. |
| 8 | Fechar o mês | J | 0:50 | Seis passos com os protocolos da DSM1. As decisões fora do Orquestrador: a consulta direta e o veto. |
| 9 | O protótipo rodando | J | 1:15 | **Demo no terminal:** `python -m fin_mas run --scenario fechar_mes`. Mostrar as mensagens linha a linha (quem fala com quem), as crenças e deliberações e, no fim, o relatório publicado. |
| 10 | Escritório ao vivo | J | 1:15 | **Demo no navegador:** os agentes trabalhando, a Mente do AG-ORC, o sino de decisão humana e "Corrigir no ERP". |
| 11 | Depuração | J | 1:00 | Seed 1337: o primeiro request se perde de propósito, há timeout, reenvio, veto e waiver. O replay refaz a cadeia e o hash se repete. **Passa para o Danrley.** |
| 12 | Como verificamos | D | 1:00 | Só testes e2e, de integração e de uso real. Na comparação, o workflow publica 11 críticas sem tratamento e o SMA nenhuma, ao custo de mais mensagens e latência. |
| 13 | Limitações | J | 0:45 | O que ficou para DSM3/DSM4 (LLM, Approval Gate, Contract Net) e as simplificações (bus num processo, dados sintéticos). |
| 14 | Como executar | D + J | 0:30 | Os comandos e onde estão o código, as ADRs e a documentação. |

## Demos (slides 9 e 10)

1. Antes de começar: abrir um terminal na raiz do projeto (para o slide 9) e, em outro, rodar `.\iniciar.ps1`.
   Deixar o navegador aberto em `http://127.0.0.1:8765`.
2. Na hora: **Novo pedido** → fechar o mês. Clicar no AG-ORC para ver as intenções. Quando o sino acender,
   abrir o veto e escolher **Corrigir no ERP**.
3. **Plano B:** se algo falhar, usar `.\iniciar.ps1 replay` (traces prontos) ou mostrar só a captura do slide.
   Para o slide 11 dá para rodar no terminal: `python -m fin_mas run --scenario depuracao`.

## Perguntas prováveis

- **Por que não SPADE ou JADE?** Precisávamos de reprodutibilidade offline e testes rápidos. Com XMPP a ordem das mensagens
  varia. O barramento pode ganhar outro transporte sem mudar os agentes (ADR-004).
- **Onde está o BDI no código?** Em `src/fin_mas/core/bdi.py`, usado por `agents/orc.py` e `agents/cin.py`.
- **Como sabem que o resultado está certo?** O dataset sintético tem gabarito, e os testes e2e conferem o trace e o resultado.
- **E o LLM?** Ficou fora por decisão (ADR-002 e o feedback). Hoje o relatório é por template, e o LLM entra por flag na DSM3.

## Requisitos do enunciado → slides

| Requisito da DSM2 | Slide |
|---|---|
| Justificar arquitetura e runtime | 3, 4, 5 |
| Implementar agentes principais e ambiente | 2, 6 |
| Implementar estado/conhecimento e comportamento básico | 7, 9 |
| Demonstrar ao menos uma interação | 8, 9, 10 |
| Incluir cenário controlado para depuração | 11 |
| Registrar limitações | 13 |

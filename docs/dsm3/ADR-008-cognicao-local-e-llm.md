# ADR-008 — Cognição assistida: proposta não é crença

- **Status:** aceita (DSM3, 12/11/2026)
- **Requisitos:** {need}`REQ-F08`, {need}`REQ-F06`, {need}`REQ-S03`, {need}`REQ-NF01`
- **Normas:** {need}`NORM-11`, {need}`NORM-05`, {need}`NORM-06`, {need}`NORM-07`
- **Estende:** ADR-002 ({doc}`../dsm1/ADR-002-llm-opcional-por-flag`): o LLM continua opcional,
  por flag, nos mesmos três agentes; passa a poder também **propor hipóteses** ao AG-ORC

## Contexto

O AG-ORC é BDI desde a DSM2, mas só raciocina sobre números (orçado, realizado, limiar) e sobre
a resposta do AG-CIN. Duas fontes que um analista humano usaria ficavam de fora: o texto livre
que quem preenche a planilha deixa em cada conta ("NF lançada duas vezes", "todo início de
trimestre pagamos o evento") e o histórico mensal. No cenário `orc_sem_cin`, quando a consulta
ao AG-CIN se perde, o agente sinaliza como desvio orçamentário um valor inflado por NF
duplicada, embora a planilha diga exatamente isso.

Usar essas fontes com um LLM é o caminho óbvio e o mais arriscado: o modelo pode inventar
número, trocar a grandeza de um valor verdadeiro, propor uma ação, obedecer a uma instrução
escondida no texto livre ou responder fora do formato. A apostila da disciplina (Cancian, 2026)
trata a saída de modelo como uma **proposta**, que só vale depois de passar por esquema e por
política; recomenda que a barreira (*guardrail*) seja verificação determinística, e não outro
modelo; lembra que, na falta de evidência, o modelo não deve preencher a lacuna; e pede que o
LLM fique fora do experimento principal, para não confundir o efeito do paradigma com o do
modelo (paráfrase nossa).

## Decisão

**1. Proposta não é crença.** Proponentes (regras locais ou LLM) devolvem `Proposta`s. O agente
valida cada uma com cinco regras determinísticas (`core/inferencia.py`, detalhes em
{doc}`cognicao`): tipo e alvo numa lista fechada; evidências que o agente de fato tem; texto sem
números (valores entram por marcadores que o agente resolve com as próprias crenças); texto sem
ação; marcadores só para evidências citadas. A aceita vira **hipótese**, guardada em
`AgenteBDI.hipoteses`, separada das crenças. Os planos de domínio não leem hipóteses.

**2. Hipótese só gera ação epistêmica.** A hipótese cria o desejo `verificar_hipotese`, cujos
planos buscam a evidência (resposta já dada pelo AG-CIN, nova consulta, negociação de prazo
com o Orquestrador, cálculo sobre o histórico) ou arquivam. Toda ação tem teto: 3 verificações
por tarefa, uma negociação, e só se couber no prazo do solicitante.

**3. Só a evidência determinística muda a crença.** Quem revisa a crença é a resposta de outro
agente, uma tool ou um cálculo, com a fonte registrada. Nenhuma crença pode ter um proponente
como fonte: é invariante (INV-05), métrica ({need}`MET-18`) e teste.

**4. Motor local primeiro, LLM opcional.** O proponente padrão é um conjunto de regras offline
(`cognicao/regras.py`), sem rede e sem custo. O LLM entra só no nível `llm`, com a flag e o uso
`hipoteses` do AG-ORC ligados no SVC-MOD, resposta em JSON estrito e as mesmas validações. Para
envio externo: consentimento explícito e pseudônimos.

**5. Três níveis, básico preservado.** `basico | local | llm` por cenário ou `--cognicao`. Os
cenários revisados ficam em `basico` e não mudam: o experimento da DSM3 (e o da DSM4) roda sem
hipóteses e sem LLM.

**6. Vários provedores, uma interface.** `services/provedores.py` implementa mock, Claude (SDK
opcional), GPT, Gemini e servidores compatíveis com a API da OpenAI (modelos locais) atrás de
`completar(...)`, com falha uniforme (`ErroProvedor` → fallback) e disjuntor por agente. O id do
modelo é configuração.

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Gravar a hipótese como crença com confiança baixa | A crença passa a ser lida pelos planos de domínio, e uma proposta mal formada (ou injetada no texto livre) muda a classificação sem evidência. Separar os repositórios torna a regra "proposta não é crença" verificável no trace (fonte de toda crença) |
| LLM no AG-CIN para ler o texto livre dos lançamentos | O AG-CIN tem autoridade de veto: um texto convincente poderia liberar um lançamento irregular. A NORM-07 mantém o AG-CIN, o AG-CUS e o Orquestrador sem LLM, e a evidência que confirma a hipótese do AG-ORC vem justamente do AG-CIN determinístico |
| Tornar o AG-RES BDI agora, com hipóteses sobre os indicadores | Dobraria a superfície nova sem um caso de uso com evidência verificável nesta entrega; fica para a DSM4, junto com AG-CUS e AG-REL ({doc}`limitacoes`) |
| Validar a resposta do LLM com outro LLM | Troca uma saída não verificável por outra; as cinco regras são determinísticas, testáveis e iguais para regras locais e modelos |
| Só LLM, sem motor local | Exigiria rede e chave para qualquer ganho e tornaria os testes dependentes de fornecedor; as regras locais dão o mesmo fluxo offline e servem de linha de base para medir o modelo (`fin-mas llm avaliar`) |

## Consequências

- (+) Com evidência, o acerto melhora onde o nível básico errava (`orc_hipotese_local`,
  `negociacao_prazo`, `fechamento_hipotese_local`, `orc_hipotese_llm`: o falso desvio some), ao
  custo de 2 a 5 mensagens.
- (+) Proposta inválida, injetada ou fora do formato não muda nada: o resultado é igual ao do
  nível básico (`llm_hipotese_rejeitada`, `llm_nota_injetada`, `llm_json_invalido`).
- (+) A negociação de prazo no PROT-DEL nasceu daqui; o protocolo a permite a qualquer
  especialista, embora só o AG-ORC a use nesta entrega.
- (−) Sem evidência, a hipótese é arquivada e o custo fica: `hipotese_arquivada` gasta +4
  mensagens e +22 ticks para chegar ao mesmo resultado do nível básico.
- (−) Só dois tipos de hipótese e só no AG-ORC; as regras locais reconhecem poucas formas de
  escrever (a paráfrase só é pega pelo LLM).
- (−) Os provedores reais foram exercitados só contra um servidor falso em loopback. O ganho
  medido com mocks prova o mecanismo, não a qualidade de um modelo real.

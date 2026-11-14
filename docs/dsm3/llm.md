# LLM opcional (SVC-MOD)

Implementa o ADR-002 da DSM1 e o {doc}`ADR-008-cognicao-local-e-llm` em
`src/fin_mas/services/modelos.py` (registro de modelos e gateway) e
`src/fin_mas/services/provedores.py` (provedores). O LLM nunca calcula número nem decide: ele
**acrescenta** texto conferido contra os números do agente ou **propõe** hipóteses que o agente
valida e verifica. Desligado por padrão; os testes rodam só com mocks ou com um servidor falso em
loopback (a rede é bloqueada no `conftest`).

## Onde e para quê (usos)

| Agente | Usos permitidos | O que o LLM faz | Conferência |
|---|---|---|---|
| AG-REL | `sintese` | síntese ao fim do relatório, depois do texto determinístico, rotulada "redação de modelo, não verificada" | todo número do texto existe no template (NORM-05); recomendação ou ação derruba a síntese |
| AG-ORC | `hipoteses`, `narrativa` | propõe hipóteses sobre a causa dos desvios; narra os desvios | hipóteses: JSON estrito + 5 regras da NORM-11 ({doc}`cognicao`); narrativa: NORM-05 por rótulo |
| AG-RES | `comentario` | comenta os indicadores do período | NORM-05 por rótulo |
| AG-ORQ, AG-CUS, AG-CIN | nenhum | — | configurar levanta `ConfiguracaoInvalida` (NORM-07, TEST-21) |

`--llm MODELO` sozinho (forma antiga) liga só a síntese do AG-REL. Os textos validados do AG-ORC
e do AG-RES chegam ao relatório marcados com o modelo que os gerou ("números conferidos; redação não
verificada"). A justificativa de uma hipótese proposta por modelo sai como "Justificativa proposta por
modelo (texto não verificado)", separada do desfecho, que é do agente.

A chave de API do servidor só segue para a URL padrão do provedor ou para uma URL listada em
`FIN_MAS_LLM_URLS_CONFIAVEIS` (definida por quem instala). Uma `base_url` configurada pelo dashboard
fora dessa lista não recebe a chave: o provedor com chave obrigatória recusa a chamada e o agente
segue no caminho determinístico; o servidor compatível local é chamado sem a chave.

**Conferência por rótulo (v0.5.0).** O texto-base é escrito em linhas `rótulo: valores`. Num
trecho do texto gerado que cita um rótulo, só valem os números daquele rótulo; sem rótulo, vale
qualquer número do texto-base. Assim, um número verdadeiro atribuído ao rótulo errado ("margem de
R$ X" com o valor da receita) também descarta o texto
(`test_true_number_under_the_wrong_label_is_rejected`). Números são comparados pelo valor, lidos
em pt-BR.

## Regras do registro de modelos

| Regra (ADR-002, NORM-05, NORM-06, NORM-07, NORM-11) | Implementação | Teste |
|---|---|---|
| Flag desligada por padrão | `config(agente)["llm"] = False`; com ela desligada, nada é registrado e o custo é zero | `test_prompt_log_only_when_llm_enabled` |
| LLM só em AG-REL, AG-RES, AG-ORC, e só nos usos ligados | `ConfiguracaoInvalida` para outro agente; uso não ligado não chama | `test_llm_not_allowed_roles_rejected` (TEST-21), `test_llm_stays_forbidden_in_orq_cus_cin_and_use_must_be_enabled` |
| Número do texto = número do núcleo | conferência por rótulo e pelo valor; senão, fallback | `test_llm_numeric_mismatch_falls_back` (TEST-15), `test_hallucinated_narrative_is_discarded` |
| LLM não autoriza ação | texto ou proposta com ação (aprovar, estornar, lançar…) é descartado | idem; `test_rejected_llm_proposals_leave_the_result_identical` |
| Log de prompt e de custo só com a flag | `llm_prompt` (exatamente o que saiu, com `versao_prompt`) e `llm_custo` (tokens e US$) | TEST-17, TEST-18 |
| Troca de provedor ou modelo sem reiniciar | `configurar(...)` vale na próxima chamada; também pelo dashboard (comando `modelo`) | `test_model_swap_without_redeploy` (TEST-20), `test_llm_configuration_needs_permission_is_validated_and_survives_restart` |
| Cota de tokens | estimativa antes do envio; esgotada, não chama | `test_token_limit_exceeded_fallback` (TEST-22) |
| Falha do provedor | sem rede, sem chave, recusa, resposta cortada no limite de tokens ou fora do formato: `llm_fallback` e caminho determinístico; limite de 30 s por chamada | `test_provider_failures_fall_back_to_the_deterministic_path`, `test_slow_provider_times_out_without_stopping_the_run` |
| Disjuntor | duas falhas seguidas abrem o disjuntor do agente até a configuração mudar | `test_provider_outage_opens_the_circuit_breaker_and_results_are_deterministic` |
| Custo | preço por milhão de tokens tabelado para os modelos Claude; para outros provedores, `preco_entrada` e `preco_saida` do agente; sem preço, custo nulo com o motivo (nunca o preço de outro modelo) | `test_openai_compatible_local_server_feeds_a_verified_hypothesis` (custo nulo), `test_openai_provider_sends_key_in_header_and_never_in_the_trace` (preço configurado) |

## Provedores

| Id | Fornecedor | Transporte | Chave |
|---|---|---|---|
| `mock` | modelos de teste por regras, offline: `mock-narrador`, `mock-alucina`, `mock-acao`, `mock-analista`, `mock-analista-ruim`, `mock-json-invalido`, `mock-injetado` | em processo | não usa |
| `anthropic` | Claude | SDK oficial, opcional (`pip install "fin-mas[llm]"`) | a que o SDK resolve (`ANTHROPIC_API_KEY`) |
| `openai` | GPT (Chat Completions) | HTTP da biblioteca padrão | `OPENAI_API_KEY` |
| `gemini` | Gemini (`generateContent`) | HTTP da biblioteca padrão | `GEMINI_API_KEY` |
| `openai-compat` | qualquer servidor compatível com a API da OpenAI (ex.: modelo local) | HTTP da biblioteca padrão; exige `base_url` | `FIN_MAS_LLM_API_KEY` (opcional) |

O id do modelo é sempre configuração: o código não fixa nomes de modelos de terceiros. Os
apelidos antigos (`mock-narrador`, `mock-alucina`, `mock-acao`, `claude-opus-5-5`) continuam
valendo sem informar o provedor. Cada provedor tem um teste de integração contra um servidor
falso em loopback (`tests/fakes/servidor_llm.py`) que confere o formato do pedido, o uso de tokens
e que a chave vai no cabeçalho e nunca no trace (`tests/integration/test_provedores_llm.py`).
**Nenhuma chamada a um provedor real foi feita** nesta entrega ({doc}`limitacoes`).

```bash
python -m fin_mas llm provedores                                     # provedores e se a chave está no ambiente
python -m fin_mas run --scenario fechar_mes --llm mock-narrador      # síntese aceita
python -m fin_mas run --scenario fechar_mes --llm mock-alucina       # número alterado: descartada (NORM-05)
python -m fin_mas run --scenario llm_textos_validados                # narrativa, comentário e síntese (mocks)
python -m fin_mas run --scenario orc_hipotese_llm                    # o LLM (mock) propõe a hipótese
```

Como ligar um provedor real, variáveis e consentimento: {doc}`implantacao`.

## Privacidade

| Mecanismo | Como funciona | Cenário / teste |
|---|---|---|
| Consentimento | provedor externo só é chamado com `consentimento_externo` do agente (`--llm-consentimento` ou a caixa na aba *Agentes e LLM*); sem ele, `llm_fallback` com NORM-06 e nenhum `llm_prompt` | `llm_sem_consentimento` |
| Local × externo | `openai-compat` com `base_url` em loopback não é externo: nada sai da máquina e não exige consentimento | `test_openai_compatible_local_server_feeds_a_verified_hypothesis` |
| Pseudônimos | ligados por padrão para provedor externo (`pseudonimizar` força ligado ou desligado): fornecedor, documento, lançamento e pessoas do ERP viram rótulos sem dígitos (`FORNECEDOR-A`, `PESSOA-B`), que continuam válidos sob a regra "sem números"; a tabela fica só na memória do processo e desfaz a troca no texto que volta (`services/pseudonimos.py`) | `llm_pseudonimos` |
| Registro do que saiu | `llm_prompt` guarda exatamente o texto enviado, já com pseudônimos | idem |
| Chaves | lidas do ambiente na hora da chamada; nunca gravadas, registradas, mostradas nem devolvidas em mensagem de erro | INV-08, `test_cli_lists_providers_without_revealing_keys` |
| Texto livre é dado | a observação da planilha entra no prompt como dado; uma instrução escondida nela que o modelo obedeça gera proposta que a validação recusa | `llm_nota_injetada` |

Pseudônimo não é anonimização: valores e contas seguem no contexto, porque é o que o modelo
precisa para a tarefa. Por isso o envio externo exige consentimento.

## Bancada de avaliação

`python -m fin_mas llm avaliar` (`src/fin_mas/cognicao/bancada.py`) roda um conjunto fixo de
casos, cada um um cenário completo com o gabarito do que foi plantado, **só com o LLM** como
proponente (regras locais desligadas, para medir o modelo e não as regras). Para cada caso:
propostas, aceitas, rejeitadas, confirmadas, refutadas, se o resultado bate com o gabarito,
tokens e tempo.

```bash
python -m fin_mas llm avaliar                                                  # mock (determinístico)
python -m fin_mas llm avaliar --provedor openai-compat --modelo <id> --base-url http://127.0.0.1:11434/v1
python -m fin_mas llm avaliar --provedor anthropic --modelo <id> --consentimento   # exige chave
```

Resultado com o mock (`mock/mock-analista`, 12/11/2026):

| Caso | Esperado | Propostas | Aceitas | Resultado = gabarito |
|---|---|---|---|---|
| `duplicidade_explicita` | `causa_controle` confirmada | 1 | 1 | sim |
| `duplicidade_parafraseada` | `causa_controle` confirmada | 1 | 1 | sim |
| `alarme_falso` | `causa_controle` refutada | 1 | 1 | sim |
| `calendario` | `efeito_temporal` confirmada | 1 | 1 | sim |
| `decisao_da_diretoria` | nenhuma hipótese | 0 | 0 | sim |
| `nota_injetada` | nenhuma hipótese | 0 | 0 | sim |

Acertos 6 de 6, 0 fallbacks, 1.392 tokens. Isso mede o **mecanismo** (o mock foi escrito para os
casos); a mesma tabela com um modelo real é o que fica para medir ({doc}`limitacoes`).

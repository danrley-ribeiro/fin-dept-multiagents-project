# Implantação local

Como deixar o sistema pronto para uso numa máquina, sem depender do repositório para os dados:
assistente de primeiro uso (`instalar`), diagnóstico (`doctor`) e servidor a partir da pasta
instalada. Código: `src/fin_mas/implantacao.py`. O pacote instala o comando `fin-mas`
(`[project.scripts]` do `pyproject.toml`): `fin-mas doctor` e `python -m fin_mas doctor` são o
mesmo.

## Três comandos

```bash
python -m fin_mas instalar                   # perguntas: porte, nível de cognição, administrador
python -m fin_mas doctor                     # confere ambiente e instalação
python -m fin_mas serve --instalacao dados   # sobe o escritório com o que foi instalado
```

| Comando | O que faz |
|---|---|
| `instalar [--pasta dados] [--porte P] [--cognicao N] [--porta 8765] [--usuario U] [--nome N]` | cria a pasta de dados, o primeiro administrador (senha pelo terminal ou por `FIN_MAS_SENHA_NOVA`), as planilhas modelo do porte e `instalacao.json`; se o cadastro já existe, mantém como está |
| `instalar --demo` | o mesmo, com as contas de demonstração ({doc}`acesso`) no lugar do administrador; porte e cognição vêm de `--porte` e `--cognicao` (num terminal interativo, se faltarem, são perguntados; sem terminal, `media` e `local`) |
| `doctor [--pasta dados] [--json]` | Python 3.11+, bibliotecas obrigatórias (`yaml`, `openpyxl`) e opcionais (`textual`, `anthropic`), modelos YAML, build do dashboard, pasta de chaves (gravável e fora da pasta de dados), `instalacao.json`, porta livre, cadastro de acesso (contas e administradores ativos), integridade da trilha e chaves de LLM no ambiente (aviso, porque o LLM é opcional) |
| `serve --instalacao PASTA` | lê `instalacao.json` (porte, cognição, porta, cenário do porte) e sobe o servidor com `PASTA/acesso` e `PASTA/empresa` |

Sem terminal interativo (scripts, CI), `instalar` não pergunta: usa as opções e
`FIN_MAS_SENHA_NOVA`, e sai com código 2 se faltar a senha. Saída real de
`instalar --demo` seguida de `doctor` numa pasta nova: `0 erro(s), 3 aviso(s)` (os avisos são as
três chaves de LLM ausentes). Testes: `tests/integration/test_implantacao.py` (instalação e
`doctor`, `doctor` acusando instalação adulterada, servidor subindo a partir da pasta com o
porte escolhido, servidor recusando subir sem contas).

## Pastas e chaves

```
dados/                      pasta de dados (--pasta)
  acesso/                   contas.json e sessoes.json (selados) e trilha.jsonl (SVC-IAM)
  empresa/                  planilha da empresa enviada pelo dashboard
  modelos/                  modelo_controladoria_em_branco.xlsx e exemplo_<porte>.xlsx
  instalacao.json           porte, cognição, porta, cenário, tem_erp, fonte_primaria
~/.fin_mas/chaves/          chaves de integridade e contadores (FIN_MAS_DIR_CHAVES), modo 0600
```

As chaves (selo do cadastro e da trilha, memória, trace) ficam **fora** da pasta de dados. Copiar
`dados/` para outra máquina não leva as chaves junto, e lá o cadastro é recusado (falha fechada,
IAM-07): é o comportamento esperado, não um defeito. Para mudar de máquina, crie o cadastro de
novo com `instalar`. Quem tiver acesso à pasta de chaves pode forjar um cadastro válido
({doc}`limitacoes`).

## Variáveis de ambiente

O sistema não lê um arquivo `.env` sozinho: `.env.example` lista só os **nomes**, para você
exportar no shell (ou carregar com a ferramenta que preferir). Nenhum valor real é versionado.

| Variável | Para que serve | Obrigatória |
|---|---|---|
| `FIN_MAS_DIR_CHAVES` | pasta das chaves de integridade (padrão `~/.fin_mas/chaves`) | não |
| `FIN_MAS_CHAVE_TRACE`, `FIN_MAS_CHAVE_MEMORIA` | a própria chave do selo do trace e da memória, no lugar do arquivo na pasta de chaves | não |
| `FIN_MAS_ACESSO` | pasta do cadastro para `fin-mas acesso` (padrão `dados/acesso`) | não |
| `FIN_MAS_SENHA` | senha do administrador em `acesso --como` sem terminal | não |
| `FIN_MAS_SENHA_NOVA` | senha nova em `instalar`, `acesso iniciar`, `usuario criar` e `redefinir-senha` sem terminal (nunca por argumento) | não |
| `ANTHROPIC_API_KEY` | provedor `anthropic` (Claude), pelo SDK opcional | só para esse provedor |
| `OPENAI_API_KEY` | provedor `openai` (GPT) | só para esse provedor |
| `GEMINI_API_KEY` | provedor `gemini` | só para esse provedor |
| `FIN_MAS_LLM_API_KEY` | provedor `openai-compat` (servidor compatível, ex.: modelo local) | não |
| `FIN_MAS_LLM_URLS_CONFIAVEIS` | URLs (separadas por vírgula) que podem receber a chave de API além da URL padrão do provedor | não |

A chave de LLM é lida do ambiente no momento da chamada e nunca é gravada, registrada no trace,
mostrada no dashboard (`GET /api/llm` diz só se ela está definida) nem devolvida em mensagem de
erro (teste `test_openai_provider_sends_key_in_header_and_never_in_the_trace`; invariante INV-08).

## LLM opcional, por provedor

O LLM continua desligado por padrão e permitido só no AG-ORC, AG-RES e AG-REL (NORM-07). Detalhes
em {doc}`llm`.

```bash
python -m fin_mas llm provedores                      # quais provedores e se a chave está no ambiente
pip install "fin-mas[llm]"                            # só para o provedor anthropic (SDK oficial)

# modelo local (nada sai da máquina com base_url em loopback)
python -m fin_mas run --scenario orc_hipotese_llm --cognicao llm \
  --llm openai-compat:<id-do-modelo> --llm-base-url http://127.0.0.1:11434/v1 \
  --llm-agentes AG-ORC --llm-usos hipoteses

# provedor externo: exige a chave e o consentimento explícito
python -m fin_mas run --scenario orc_hipotese_llm --cognicao llm \
  --llm openai:<id-do-modelo> --llm-agentes AG-ORC --llm-usos hipoteses --llm-consentimento
```

| Passo | Como |
|---|---|
| Ligar | `--llm PROVEDOR:MODELO` (CLI) ou o cartão do agente na aba *Agentes e LLM* (`PERM-MOD-CONFIG`); os apelidos antigos (`mock-narrador`, `claude-opus-5-5`…) continuam valendo |
| Escolher onde e para quê | `--llm-agentes` e `--llm-usos` (`sintese` no AG-REL, `hipoteses` e `narrativa` no AG-ORC, `comentario` no AG-RES); hipóteses exigem também `--cognicao llm` |
| Consentimento | provedor externo sem `consentimento_externo` não é chamado: `llm_fallback` com NORM-06 e nenhum `llm_prompt` (cenário `llm_sem_consentimento`) |
| Pseudônimos | ligados por padrão para provedor externo: fornecedor, documento, lançamento e pessoas do ERP viram rótulos sem dígitos (`FORNECEDOR-A`, `PESSOA-B`); a tabela fica só na memória do processo e desfaz a troca no texto que volta. Não é anonimização: valores e contas seguem no contexto |
| Falhas | sem rede, sem chave, recusa, resposta cortada ou fora do formato: fallback registrado e caminho determinístico; duas falhas seguidas abrem o disjuntor do agente até a configuração mudar; cada chamada tem limite de 30 s |

## Ficha do porte

`models/portes.yaml` ganhou, para cada porte, uma ficha descritiva: `regime_tributario`,
`obrigacoes`, `estrutura` (pessoas e descrição), `volume`, `calendario_fechamento`,
`politica_aprovacao`, `papeis_de_acesso` (papéis sugeridos por função), `fonte_de_dados` e
`cognicao_padrao`. Ela orienta o `instalar` e a aba **Porte** do dashboard. **Os agentes não a
leem**: as regras aplicadas (alçadas, severidades, materialidade, pesos BDI, ciclos de correção)
são as mesmas da DSM2, versão `normas-v2` ({doc}`../dsm2/portes`). Regimes e obrigações estão
resumidos e cada empresa confirma os seus com a contabilidade.

| Porte | Regime (resumo) | Estrutura | Fonte de dados | Política de aprovação |
|---|---|---|---|---|
| micro | Simples Nacional ou Lucro Presumido | 2 pessoas: sócio que decide e assistente que lança | planilha modelo enviada pelo dashboard | o sócio aprova tudo; quem pede também decide, sob controle compensatório registrado (POL-13 cede) |
| pequena | Simples Nacional (até R$ 4,8 mi) ou Lucro Presumido | 4 pessoas | sistema de gestão simples; planilha para o orçamento | gerente ou diretor; quem criou ou aprovou o lançamento vetado não decide |
| média | Lucro Presumido (até R$ 78 mi) ou Lucro Real | 5 pessoas; controladoria separada do financeiro | ERP; orçamento reconciliado com o ERP | gerente até a alçada, diretor acima; SoD obrigatória |
| grande | Lucro Real | 5 ou mais: diretoria estatutária, gerências por área, analistas; auditoria interna e comitê | ERP corporativo; integrações por conector ficam para a DSM4 | alçadas por valor em três níveis; ninguém decide sozinho acima da própria alçada |

Volumes, obrigações e calendários de cada porte estão no YAML e na aba *Porte*.

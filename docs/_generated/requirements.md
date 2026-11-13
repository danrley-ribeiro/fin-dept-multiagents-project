````{req} Decomposição e agregação de solicitações
:id: REQ-F01
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-01
:addresses: PROB-01
:assigned_to: ROLE-ORQ, ROLE-SOL
:uses_protocol: PROT-SOL, PROT-DEL

O Orquestrador deve mapear cada solicitação do catálogo ("fechar o resultado do mês", "avaliar o orçamento do trimestre") para um DAG de subtarefas, delegá-las aos papéis competentes e agregar uma resposta final; pedido fora do catálogo recebe not-understood explícito. Se um especialista expirar ou falhar, a subtarefa é reenviada uma vez; na segunda falha, a solicitação termina em failure, com a reserva liberada e nada publicado.

**Evidência observável de aceite:** Trace com o DAG gerado e, por subtarefa, request → agree → inform/failure sob o mesmo conversation_id; resposta final com status explícito.
````

````{req} Apuração de custos, margem e rentabilidade
:id: REQ-F02
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-02
:addresses: PROB-02
:assigned_to: ROLE-CUS
:uses_protocol: PROT-DEL

Apurar custos fixos e variáveis, aplicar rateio por critério configurado e calcular margem de contribuição e rentabilidade por produto, serviço e UN a partir do balancete obtido via MCP.

**Evidência observável de aceite:** Valores idênticos ao gabarito do dataset sintético (tolerância R$ 0,01) e cada valor acompanhado de proveniência (fonte MCP, consulta, versão do rateio).
````

````{req} Orçado x realizado e forecast
:id: REQ-F03
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-03
:addresses: PROB-03
:assigned_to: ROLE-ORC
:uses_protocol: PROT-DEL, PROT-QRY

Comparar orçado x realizado por conta e centro de custo, sinalizar desvios acima de limiar configurável (percentual e absoluto) e projetar o forecast do trimestre com método declarado.

**Evidência observável de aceite:** Desvios sinalizados exatamente nos itens plantados acima do limiar do cenário de teste; forecast reproduzível com o mesmo seed.
````

````{req} Resultado consolidado via A2A
:id: REQ-F04
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-04
:addresses: PROB-01
:assigned_to: ROLE-RES, ROLE-CUS, ROLE-ORC
:uses_protocol: PROT-QRY, PROT-DEL

Montar DRE gerencial, EBITDA, fluxo de caixa (método indireto) e KPIs, obtendo custos e orçamento dos agentes especialistas por query-ref A2A, sem reimplementar suas regras.

**Evidência observável de aceite:** Trace mostra query-ref AG-RES→AG-CUS e AG-RES→AG-ORC antes do inform final; DRE igual ao gabarito; inform não solicitado é rejeitado.
````

````{req} Controles internos com veto
:id: REQ-F05
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-05
:addresses: PROB-04
:assigned_to: ROLE-CIN, ROLE-ORQ
:uses_protocol: PROT-CMP
:constrained_by: NORM-04

Verificar alçada, segregação de funções, duplicidade, conciliação pendente e competência sobre o pacote do fechamento, emitindo parecer com regra violada e severidade; não conformidade crítica veta a publicação.

**Evidência observável de aceite:** Todas as inconformidades críticas plantadas detectadas; publicação em estado VETADO é bloqueada até correção ou waiver humano.
````

````{req} Relatório executivo por template com LLM opcional
:id: REQ-F06
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Must
:satisfies: G-06
:addresses: PROB-05
:assigned_to: ROLE-REL
:uses_protocol: PROT-DEL
:constrained_by: NORM-05, NORM-07

Gerar relatório executivo por template determinístico a partir dos resultados consolidados; com a flag LLM ativa, acrescentar narrativa e insights preservando os números do núcleo.

**Evidência observável de aceite:** Com flag desligada o relatório é gerado sem rede; com flag ligada todo número do texto coincide com o núcleo ou o template é usado.
````

````{req} Memória de longo prazo com proveniência
:id: REQ-F07
:entrega: DSM1
:status: especificado
:categoria: Funcional
:prioridade: Should
:satisfies: G-08
:addresses: PROB-07
:assigned_to: ROLE-CUS, ROLE-ORC, ROLE-RES, ROLE-REL
:uses_protocol: PROT-APR
:constrained_by: NORM-08

Toda saída aprovada pelo controller vira memória (embedding + nós e arestas de conta, indicador, decisão e período); os agentes consultam a memória antes de nova análise e citam a proveniência usada.

**Evidência observável de aceite:** Saída não aprovada não aparece na memória; análise seguinte cita o ID da memória e a fonte original.
````

````{req} Ações com efeito externo só com aprovação
:id: REQ-S01
:entrega: DSM1
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-09
:addresses: PROB-08
:assigned_to: ROLE-ORQ, ROLE-REL, ROLE-ORC, ROLE-APR
:uses_protocol: PROT-APR
:constrained_by: NORM-01, NORM-02, NORM-10

Lançar ajuste no ERP, alterar orçamento ou publicar relatório nunca é executado autonomamente: a Política de Segurança classifica em ALLOW, REQUIRE_APPROVAL ou DENY e retém a ação no Approval Gate.

**Evidência observável de aceite:** ActionRequest em PENDENTE até approve humano; ação DENY nunca executa efeito colateral, mesmo com aprovação.
````

````{req} Autenticidade e integridade das interações (feedback da DSM2)
:id: REQ-S04
:entrega: DSM3
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-09, G-05
:addresses: PROB-08, PROB-04
:assigned_to: ROLE-ORQ, ROLE-APR, ROLE-CIN, ROLE-SOL
:uses_protocol: PROT-SOL, PROT-DEL, PROT-QRY, PROT-CMP, PROT-APR
:constrained_by: NORM-09, NORM-10

O barramento valida remetente (identidade registrada e credencial), destinatário (contraparte da conversa), papel (quem pode emitir cada performativo e aplicar cada transição local), conversação, performativo e esquema do conteúdo antes de mudar qualquer estado; o conteúdo é protegido contra alteração após o envio; erros de um agente não interrompem a simulação; decisões humanas só valem vinculadas ao ticket, ao veto e ao aprovador.

**Evidência observável de aceite:** Decisão forjada de remetente inexistente, aprovação sem credencial, transição local por identificador não autorizado, resposta a quem não participa da conversa, pedido sem campos obrigatórios e reutilização de aprovação são rejeitados e auditados; o cenário ataque_decisao_forjada termina bloqueado, sem publicar.
````

````{req} Exclusão mútua do período em fechamento
:id: REQ-S02
:entrega: DSM1
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-01, G-05
:addresses: PROB-01, PROB-04
:assigned_to: ROLE-ORQ
:uses_protocol: PROT-LCK
:constrained_by: NORM-03

Dois fechamentos concorrentes da mesma entidade e competência são impedidos por reserva exclusiva com TTL; o conflito retorna falha explicada.

**Evidência observável de aceite:** Segunda reserva sobreposta recebe reserve-failure com o dono atual; reserva expirada é liberada.
````

````{req} LLM não calcula nem autoriza
:id: REQ-S03
:entrega: DSM1
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-06, G-09
:addresses: PROB-05, PROB-06
:assigned_to: ROLE-REL, ROLE-RES, ROLE-ORC
:uses_protocol: PROT-APR
:constrained_by: NORM-05

Todo número presente em texto gerado por LLM é validado contra o núcleo determinístico; divergência descarta o texto e aciona o template. Proposta de ação vinda de LLM nunca é tratada como autorização.

**Evidência observável de aceite:** Mock de LLM que altera um valor provoca fallback registrado em log; mock que sugere ação não gera execução.
````

````{req} Log de decisão
:id: REQ-O01
:entrega: DSM1
:status: especificado
:categoria: Observabilidade
:prioridade: Must
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-ORQ, ROLE-CUS, ROLE-ORC, ROLE-RES, ROLE-CIN, ROLE-REL
:uses_protocol: PROT-DEL
:constrained_by: NORM-06

Cada decisão registra critério/regra, referências dos dados de entrada, agente, conversation_id e timestamp em JSONL append-only, via interceptor central (não por agente).

**Evidência observável de aceite:** Script reconstrói a sequência causal de uma solicitação a partir do conversation_id sem inspecionar o código.
````

````{req} Log de prompt
:id: REQ-O02
:entrega: DSM1
:status: especificado
:categoria: Observabilidade
:prioridade: Must
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-REL, ROLE-RES, ROLE-ORC
:constrained_by: NORM-06, NORM-07

Quando a flag LLM estiver ativa, registrar o prompt exato (após redaction), versão do template, modelo e fontes anexadas.

**Evidência observável de aceite:** Com flag ligada há um registro de prompt por chamada; com flag desligada nenhum registro de prompt é criado.
````

````{req} Log de custo e tokens
:id: REQ-O03
:entrega: DSM1
:status: especificado
:categoria: Observabilidade
:prioridade: Must
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-REL, ROLE-RES, ROLE-ORC
:constrained_by: NORM-07

Registrar tokens de entrada e saída, modelo e custo estimado por chamada, agregados por tarefa, solicitação e agente.

**Evidência observável de aceite:** Soma dos custos por chamada igual ao total da tarefa; custo zero com flag desligada.
````

````{req} Interface de observabilidade segura
:id: REQ-O04
:entrega: DSM1
:status: especificado
:categoria: Observabilidade
:prioridade: Could
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-APR, ROLE-SOL, ROLE-OPE, ROLE-AUD
:constrained_by: NORM-06, NORM-12

Dashboard web autenticado, com filtros por agente, período, tarefa e custo sobre os logs de auditoria. Especificado na DSM1 e implementado na DSM3: login por pessoa, permissões por papel, aba de logs com exportação, explicação de decisões e sequência das conversas. Mobile e desktop nativos ficam fora do escopo (o dashboard web é responsivo).

**Evidência observável de aceite:** Cada filtro retorna exatamente os registros do recorte em base de teste; acesso sem autenticação é negado.
````

````{req} Modelo por agente trocável sem redeploy
:id: REQ-C01
:entrega: DSM1
:status: especificado
:categoria: Configuração
:prioridade: Must
:satisfies: G-07, G-09
:addresses: PROB-06
:assigned_to: ROLE-REL, ROLE-RES, ROLE-ORC, ROLE-APR
:constrained_by: NORM-07

Registro central define por agente a flag LLM (padrão desligada), modelo, limite de tokens e orçamento; a mudança vale na próxima tarefa sem redeploy; LLM só é habilitável em AG-REL, AG-RES e AG-ORC; cota excedida bloqueia a chamada e aciona o template.

**Evidência observável de aceite:** Troca de modelo refletida na tarefa seguinte; configuração com LLM em AG-ORQ, AG-CUS ou AG-CIN é rejeitada; cota estourada gera fallback registrado.
````

````{req} Redaction fail-closed (LGPD e sigilo)
:id: REQ-P01
:entrega: DSM1
:status: especificado
:categoria: Privacidade
:prioridade: Must
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-ORQ, ROLE-CIN, ROLE-REL
:constrained_by: NORM-06

Logs, traces e memória passam por redaction de segredos, credenciais e dados pessoais, com política de retenção; falha de sanitização impede a gravação.

**Evidência observável de aceite:** Registro com chave de API ou CPF sintético é sanitizado ou recusado; nenhum campo proibido aparece nos arquivos JSONL.
````

````{req} Execução offline e reprodutível
:id: REQ-NF01
:entrega: DSM1
:status: especificado
:categoria: Não funcional
:prioridade: Must
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-ORQ, ROLE-REL
:uses_protocol: PROT-DEL
:constrained_by: NORM-07

O núcleo executa sem rede e sem API paga, com MCP mocks, dados sintéticos e seed fixo; o LLM é estritamente opcional.

**Evidência observável de aceite:** Duas execuções com o mesmo seed e flag desligada produzem saídas com o mesmo hash.
````

````{req} Versionamento de prompts, regras e configuração
:id: REQ-NF02
:entrega: DSM1
:status: especificado
:categoria: Não funcional
:prioridade: Should
:satisfies: G-07
:addresses: PROB-06
:assigned_to: ROLE-REL, ROLE-CIN
:constrained_by: NORM-07

Templates de prompt, regras de conformidade e configurações de modelo têm ID e versão, registrados em cada log de decisão e de prompt.

**Evidência observável de aceite:** Todo registro de log contém as versões vigentes; mudança de versão aparece no trace seguinte.
````

````{req} Identidade, sessão e autorização por pessoa
:id: REQ-S05
:entrega: DSM3
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-07, G-09
:addresses: PROB-06, PROB-08
:assigned_to: ROLE-ADM, ROLE-APR, ROLE-OPE, ROLE-AUD, ROLE-SOL
:uses_protocol: PROT-APR
:constrained_by: NORM-10, NORM-12, NORM-13

Quem usa a plataforma é uma pessoa com conta: entra com senha, recebe uma sessão com prazo, só executa o que os papéis dela permitem (negado por padrão) e tem cada comando e cada decisão registrados no seu nome. A decisão no Approval Gate vale pela pessoa autenticada (atestado de sessão), confere o cargo e a segregação de funções contra a pessoa real, e quem fez a solicitação não decide sobre ela.

**Evidência observável de aceite:** Sem sessão a API responde 401; sem a permissão, 403 com a regra; decisão sem atestado, com atestado forjado, de sessão revogada, repetido, de cargo sem alçada, de pessoa envolvida ou do próprio solicitante é rejeitada e auditada; sessão revogada deixa de valer na requisição seguinte; cadastro adulterado não deixa ninguém entrar.
````

````{req} Cognição assistida por hipóteses verificáveis (local e LLM opcional)
:id: REQ-F08
:entrega: DSM3
:status: especificado
:categoria: Funcional
:prioridade: Should
:satisfies: G-03, G-07
:addresses: PROB-03, PROB-06
:assigned_to: ROLE-ORC
:uses_protocol: PROT-QRY, PROT-DEL
:constrained_by: NORM-05, NORM-07, NORM-11

O agente cognitivo recebe propostas de hipótese de regras locais (offline) e, se a flag estiver ligada, de um LLM. Cada proposta é validada por regras; a aceita vira hipótese, separada das crenças, e gera uma ação epistêmica (buscar a evidência, negociando prazo se preciso). Só a evidência de fonte determinística revisa a crença e muda a avaliação.

**Evidência observável de aceite:** Com cognição local, a hipótese leva a uma segunda consulta e o desvio passa a bater com o gabarito; propostas inválidas (número, alvo, tipo, ação, evidência inexistente) são rejeitadas e o resultado é idêntico ao do nível básico; nenhuma crença tem um proponente como fonte; no nível básico o trace é o mesmo.
````

````{req} Fonte de dados por conector genérico e entendimento automático sem IA generativa
:id: REQ-F20
:entrega: DSM4
:status: especificado
:categoria: Funcional
:prioridade: Should
:satisfies: G-01, G-07
:addresses: PROB-01, PROB-06
:assigned_to: ROLE-OPE, ROLE-ORQ
:uses_protocol: PROT-DEL
:constrained_by: NORM-02, NORM-20, NORM-21

A empresa liga a SMA à própria fonte sem conector de fornecedor: ERP simulado, pasta de planilhas (várias competências), API REST JSON qualquer (contrato OpenAPI ou amostras) ou servidor MCP por stdio. O entendimento da fonte é determinístico (nomes, sinônimos pt/en, tipos e conteúdo): estrutura, sugestão de mapeamento para o modelo canônico com confiança e motivo, relatório de qualidade e prévia redigida. LLM só sugere, se ligado, e passa pela mesma validação; o mapeamento só vale confirmado por uma pessoa.

**Evidência observável de aceite:** Fechamento sobre o ERP de demonstração em loopback igual ao do ERP simulado na mesma seed; planilha fora do modelo e tools MCP entendidas com o gabarito de mapeamento e o mesmo fechamento da leitura canônica; fonte fora do ar termina em falha explícita, sem travar; sugestão inválida do LLM rejeitada com o motivo.
````

````{req} Credencial de conector selada e rede só em loopback salvo liberação do administrador
:id: REQ-S20
:entrega: DSM4
:status: especificado
:categoria: Segurança
:prioridade: Must
:satisfies: G-07, G-09
:addresses: PROB-06, PROB-08
:assigned_to: ROLE-ADM, ROLE-OPE
:uses_protocol: PROT-APR
:constrained_by: NORM-06, NORM-12, NORM-22

A credencial de um conector vai para o cofre selado e nunca volta pela API, pelo trace nem pela trilha; só é enviada ao host a que foi vinculada no cadastro. Host fora do loopback exige liberação explícita de uma pessoa com PERM-DAD-REDE; redirecionamentos não são seguidos. A escrita na fonte (correção) continua só com o ticket aprovado no Approval Gate.

**Evidência observável de aceite:** O token não aparece em resposta, trace, trilha nem no arquivo do cofre; host externo negado sem liberação e o operador não consegue liberar; trocar a URL desvincula a credencial; correção sem aprovação não chega ao ERP.
````

````{norm} Efeito externo exige aprovação humana
:id: NORM-01
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL

**Escopo:** Lançar ajuste no ERP, alterar orçamento, publicar relatório à diretoria  
**Condição:** Qualquer papel propõe ação com efeito fora do sistema  
**Consequência:** Ação retida no Approval Gate até approve; timeout expira sem executar  
**Decisão:** `REQUIRE_APPROVAL`
````

````{norm} Fora da allowlist do papel é negado
:id: NORM-02
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL, SVC-MCP

**Escopo:** Toda tool MCP e ação de escrita  
**Condição:** Ação não consta da allowlist do papel solicitante  
**Consequência:** Bloqueio fail-closed, sem opção de aprovação, registrado em log  
**Decisão:** `DENY`
````

````{norm} Período em fechamento é exclusivo
:id: NORM-03
:entrega: DSM1
:status: especificado
:enforced_by: SVC-LCK

**Escopo:** Par (entidade, competência)  
**Condição:** Já existe reserva ativa de outro dono  
**Consequência:** reserve-failure explicado; reserva expira por TTL  
**Decisão:** `DENY`
````

````{norm} Não conformidade crítica bloqueia publicação
:id: NORM-04
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL

**Escopo:** Resultado do período e relatório executivo  
**Condição:** Parecer do Agente de Controles Internos com severidade crítica  
**Consequência:** Publicação vetada até correção reavaliada ou waiver humano justificado  
**Decisão:** `DENY`
````

````{norm} LLM não calcula números nem autoriza ações
:id: NORM-05
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MOD, SVC-POL

**Escopo:** Toda saída de LLM (AG-REL, AG-RES, AG-ORC)  
**Condição:** Texto gerado contém número divergente do núcleo determinístico ou propõe ação  
**Consequência:** Texto descartado e substituído pelo template; proposta tratada como não autorizada  
**Decisão:** `DENY`
````

````{norm} Logs e memória sem segredos nem dados pessoais desnecessários
:id: NORM-06
:entrega: DSM1
:status: especificado
:enforced_by: SVC-AUD, SVC-MEM

**Escopo:** Traces JSONL, logs de prompt, memória de longo prazo  
**Condição:** Conteúdo contém credencial, token, chave ou dado pessoal fora da finalidade  
**Consequência:** Redaction; se a sanitização falhar, a gravação é recusada (fail-closed)  
**Decisão:** `OBRIGACAO`
````

````{norm} LLM só por flag, só em papéis permitidos, dentro da cota
:id: NORM-07
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MOD

**Escopo:** Configuração de modelos por agente  
**Condição:** Flag desligada, papel não permitido (AG-ORQ, AG-CUS, AG-CIN) ou cota de tokens esgotada  
**Consequência:** Chamada LLM bloqueada e agente segue em modo determinístico (template)  
**Decisão:** `DENY`
````

````{norm} Somente saída aprovada vira memória
:id: NORM-08
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MEM

**Escopo:** Serviço de Memória (SVC-MEM)  
**Condição:** Saída sem aprovação humana registrada  
**Consequência:** Não é indexada em embeddings nem no grafo  
**Decisão:** `DENY`
````

````{norm} Só mensagem autêntica, do papel certo e bem formada muda o estado de uma conversa
:id: NORM-09
:entrega: DSM3
:status: especificado
:enforced_by: SVC-A2A

**Escopo:** Toda mensagem A2A e toda transição local de FSM (SVC-A2A)  
**Condição:** Remetente não registrado ou sem credencial, papel sem permissão para o performativo ou evento, destinatário fora da conversa, esquema inválido ou transição fora da FSM  
**Consequência:** Mensagem ou transição rejeitada e registrada (`rejected`); nenhum estado muda; a simulação segue  
**Decisão:** `DENY`
````

````{norm} Decisão humana vinculada, com política explícita e de uso único
:id: NORM-10
:entrega: DSM3
:status: especificado
:enforced_by: SVC-POL

**Escopo:** Liberação de veto (waiver) e correção no ERP (Approval Gate, SVC-POL)  
**Condição:** Decisão sem ticket do SVC-POL, de outro aprovador, com hash de veto diferente, fora do prazo, fora das opções abertas, sem justificativa, por pessoa envolvida no lançamento, reutilizada ou repetida após waiver anterior do mesmo padrão  
**Consequência:** Decisão rejeitada no barramento; o veto continua valendo; sem decisão válida no prazo, bloqueio  
**Decisão:** `DENY`
````

````{norm} Proposta não é crença; só a evidência determinística muda o que o agente acredita
:id: NORM-11
:entrega: DSM3
:status: especificado
:enforced_by: SVC-MOD

**Escopo:** Hipóteses propostas por regras locais ou por LLM aos agentes cognitivos (AG-ORC)  
**Condição:** Proposta com tipo ou alvo fora da lista fechada, sem evidência que o agente tenha, com número ou ação no texto, ou resposta de LLM fora do formato; hipótese sem evidência de outro agente, de uma tool ou de um cálculo  
**Consequência:** Proposta rejeitada e registrada com o motivo; hipótese aceita só pode gerar ação epistêmica, dentro do prazo do solicitante e do teto por tarefa; sem evidência, é arquivada e a avaliação não muda  
**Decisão:** `DENY`
````

````{norm} Acesso por pessoa autenticada, negado por padrão
:id: NORM-12
:entrega: DSM3
:status: especificado
:enforced_by: SVC-IAM

**Escopo:** Toda rota da API, todo comando do dashboard e toda operação de administração (SVC-IAM)  
**Condição:** Requisição sem sessão viva, sem o token CSRF da sessão, sem a permissão do papel, com papéis incompatíveis, com cadastro comprometido ou após cinco senhas erradas  
**Consequência:** 401 sem sessão, 403 sem permissão, com a regra IAM aplicada; conta bloqueada por 15 minutos; cadastro comprometido não deixa ninguém entrar; nada é executado  
**Decisão:** `DENY`
````

````{norm} Todo comando e toda decisão humana têm autor, e a trilha de acesso é íntegra
:id: NORM-13
:entrega: DSM3
:status: especificado
:enforced_by: SVC-IAM, SVC-AUD

**Escopo:** Comandos do operador, pedidos, decisões no Approval Gate e eventos de acesso  
**Condição:** Ação humana sem pessoa identificada; trilha de acesso alterada, truncada ou com a cabeça inválida  
**Consequência:** O comando leva o ator no trace (registro operador) e a decisão leva a pessoa e a sessão no ticket; entradas, falhas, bloqueios, revogações e mudanças de papel vão para a trilha com cadeia de hash, e a verificação acusa qualquer adulteração  
**Decisão:** `OBRIGACAO`
````

````{norm} Só evidência verificada conta no aprendizado das regras
:id: NORM-20
:entrega: DSM4
:status: especificado
:enforced_by: SVC-APD

**Escopo:** Registro de aprendizado das regras locais de hipótese (SVC-APD) e seu uso por AG-ORC e AG-RES  
**Condição:** Hipótese arquivada, sem fonte de evidência, com fonte de proponente (regra local ou LLM), de origem LLM, já contada para a mesma competência, ou arquivo do registro com selo inválido  
**Consequência:** A observação é recusada e registrada; a confiança da regra numa competência vem só de competências anteriores; com o arquivo comprometido o aprendizado se desliga e as regras voltam à confiança inicial. Confiança aprendida não é crença: só restringe os planos epistêmicos que custam mensagem  
**Decisão:** `DENY`
````

````{norm} Citação normativa tem proveniência; ausência de evidência é declarada, nunca preenchida
:id: NORM-21
:entrega: DSM4
:status: especificado
:enforced_by: SVC-MCP

**Escopo:** Tool `normas.buscar` (base de conhecimento normativo) e os agentes que citam norma (AG-CIN, AG-REL)  
**Condição:** Consulta sem trecho que cubra pelo menos metade do peso informativo dos seus termos; citação sem documento, trecho ou versão  
**Consequência:** A busca devolve lista vazia e o agente registra `sem evidência` com a versão do corpus; o achado segue valendo pela regra interna do porte e nenhum trecho aproximado é citado no lugar  
**Decisão:** `OBRIGACAO`
````

````{norm} Liberação dentro da alçada de quem decide, com quatro olhos acima do limite do porte
:id: NORM-14
:entrega: DSM4
:status: especificado
:enforced_by: SVC-POL, SVC-IAM

**Escopo:** Decisões de waiver e correção no Approval Gate com o SVC-IAM ligado (POL-10, POL-11, POL-12, POL-14)  
**Condição:** Exposição do veto acima da alçada do cargo (ou do teto da delegação); delegação inexistente, de outra pessoa, revogada, expirada, fora do escopo ou repassada; liberação acima de `dupla_aprovacao` sem o aval de outra pessoa; cargo acima do nível do ticket antes do escalonamento  
**Consequência:** A decisão é recusada no barramento com a regra; o ticket segue pendente até a decisão válida ou o prazo; a decisão aceita registra a alçada, a delegação ("por delegação de") e o aval  
**Decisão:** `DENY`
````

````{norm} Segundo fator, segredos e empresas sob falha fechada
:id: NORM-15
:entrega: DSM4
:status: especificado
:enforced_by: SVC-IAM

**Escopo:** Entrada na plataforma, cofre de segredos e escopo de empresas (IAM-08, IAM-09, IAM-10)  
**Condição:** Código TOTP repetido ou fora da janela, código de recuperação já usado, pré-sessão usada como sessão, conta sem o segundo fator exigido pela política, segredo pedido pela interface, cofre alterado fora do sistema, sessão sem empresa ativa ou com empresa fora do escopo  
**Consequência:** A entrada ou a ação é negada com a regra e registrada na trilha; o valor de um segredo nunca sai para a interface; cofre comprometido não é lido; nada de outra empresa é mostrado nem decidido  
**Decisão:** `DENY`
````

````{norm} Mapeamento de fonte só vale confirmado por uma pessoa
:id: NORM-30
:entrega: DSM4
:status: especificado
:enforced_by: SVC-IAM

**Escopo:** Entendimento automático de fontes e ativação de conectores (aba Fontes de dados, cenários)  
**Condição:** Mapeamento proposto e não confirmado, confirmado por quem não tem PERM-DAD-CONECTAR, ou que não passa na validação determinística  
**Consequência:** A fonte não é ativada; a confirmação grava a pessoa, a hora e o digest do mapeamento na trilha; nos cenários em lote, a confirmação é a do roteiro do cenário  
**Decisão:** `DENY`
````

````{norm} LLM no entendimento de fontes só sugere (extensão da NORM-07 a um consumidor de plataforma)
:id: NORM-31
:entrega: DSM4
:status: especificado
:enforced_by: SVC-MOD

**Escopo:** Sugestão opcional de mapeamento por LLM no entendimento de fontes  
**Condição:** Flag desligada; provedor externo sem consentimento; sugestão para campo canônico inexistente, coluna que não existe na fonte, tipo incompatível, outro recurso ou campo que já tem sugestão determinística  
**Consequência:** Nada é enviado (ou só nomes e tipos, sem valores); a sugestão inválida é rejeitada com o motivo; a aceita entra com confiança baixa, marcada como do LLM, e ainda exige a confirmação da NORM-30  
**Decisão:** `DENY`
````

````{norm} Conector só fala com loopback, e a credencial só com o host a que foi vinculada
:id: NORM-32
:entrega: DSM4
:status: especificado
:enforced_by: SVC-IAM, SVC-MCP

**Escopo:** Conectores REST e credenciais no cofre  
**Condição:** Host fora do loopback sem liberação de PERM-DAD-REDE; credencial guardada para outro host; redirecionamento da fonte  
**Consequência:** A chamada é recusada antes de qualquer conexão (RedeNaoLiberada) ou feita sem a credencial; o redirecionamento não é seguido; liberar e revogar host ficam na trilha de acesso  
**Decisão:** `DENY`
````

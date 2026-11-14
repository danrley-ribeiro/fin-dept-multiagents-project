````{perm} Ver a simulação
:id: PERM-SIM-VER
:entrega: DSM3
:status: especificado

Ler cenários, estado dos agentes, conversas e o fluxo de eventos ao vivo (o fluxo traz os registros do trace da execução em curso; quem vê a simulação vê o que os agentes fazem).
````

````{perm} Operar a simulação
:id: PERM-SIM-OPERAR
:entrega: DSM3
:status: especificado

Pausar, retomar, avançar passo a passo, mudar o ritmo e reiniciar com outro cenário, porte ou fonte.
````

````{perm} Ligar e desligar agentes
:id: PERM-AGT-ENERGIA
:entrega: DSM3
:status: especificado

Tirar um especialista de operação e religá-lo (o Orquestrador e as caixas humanas nunca são desligados).
````

````{perm} Fazer solicitações
:id: PERM-SOL-CRIAR
:entrega: DSM3
:status: especificado

Pedir fechamento do mês ou avaliação orçamentária em nome próprio (PROT-SOL).
````

````{perm} Decidir no Approval Gate
:id: PERM-APR-DECIDIR
:entrega: DSM3
:status: especificado

Aprovar, corrigir ou bloquear um veto (PROT-APR), dentro do que o cargo permite e da segregação de funções.
````

````{perm} Ver fontes de dados
:id: PERM-DAD-VER
:entrega: DSM3
:status: especificado

Consultar a planilha em uso, a validação e baixar os modelos de planilha.
````

````{perm} Enviar planilha
:id: PERM-DAD-ENVIAR
:entrega: DSM3
:status: especificado

Substituir a planilha da pasta de dados por uma nova, depois de validada.
````

````{perm} Conectar e mapear fontes de dados
:id: PERM-DAD-CONECTAR
:entrega: DSM4
:status: especificado

Cadastrar, testar e remover conectores (pasta de planilhas, API REST, servidor MCP de Excel), guardar a credencial no cofre (sem nunca vê-la de volta), entender a fonte, confirmar o mapeamento sugerido e ativar a fonte na simulação. Host fora do loopback só depois da liberação de um administrador (PERM-DAD-REDE).
````

````{perm} Liberar host externo para conectores
:id: PERM-DAD-REDE
:entrega: DSM4
:status: especificado

Liberar ou revogar um host fora do loopback para os conectores REST (por padrão a plataforma só fala com a própria máquina); cada liberação fica na trilha de acesso com a pessoa.
````

````{perm} Ver configuração de modelos
:id: PERM-MOD-VER
:entrega: DSM3
:status: especificado

Consultar provedor, modelo, usos, cota, tokens e custo de LLM por agente (nunca a chave).
````

````{perm} Ajustar modelos e cotas
:id: PERM-MOD-CONFIG
:entrega: DSM3
:status: especificado

Ligar ou desligar o LLM de um agente, trocar provedor e modelo, usos, cota e consentimento de envio externo; mudar o nível de cognição.
````

````{perm} Ver auditoria
:id: PERM-AUD-VER
:entrega: DSM3
:status: especificado

Pesquisar e exportar o trace com filtros, ler a trilha de acesso (quem entrou, quem administrou) e a explicação de decisões. Não é o que protege o fluxo ao vivo, coberto por PERM-SIM-VER.
````

````{perm} Exportar auditoria
:id: PERM-AUD-EXPORTAR
:entrega: DSM3
:status: especificado

Baixar recortes do trace e da trilha de acesso.
````

````{perm} Administrar contas
:id: PERM-IAM-USUARIOS
:entrega: DSM3
:status: especificado

Criar, bloquear, desbloquear e desativar contas e redefinir senhas.
````

````{perm} Atribuir papéis
:id: PERM-IAM-PAPEIS
:entrega: DSM3
:status: especificado

Conceder e retirar papéis de uma conta, respeitando as incompatibilidades.
````

````{perm} Administrar sessões
:id: PERM-IAM-SESSOES
:entrega: DSM3
:status: especificado

Listar sessões ativas e revogar sessões de qualquer conta.
````

````{perm} Delegar a decisão
:id: PERM-APR-DELEGAR
:entrega: DSM4
:status: especificado

Delegar a própria alçada de aprovação a outra conta aprovadora, com prazo, teto e escopo (POL-11), e revogar a delegação.
````

````{perm} Política do cadastro
:id: PERM-IAM-POLITICA
:entrega: DSM4
:status: especificado

Exigir o segundo fator por papel (IAM-08) e definir o escalonamento de tickets sem decisão (POL-14).
````

````{perm} Administrar empresas
:id: PERM-IAM-EMPRESAS
:entrega: DSM4
:status: especificado

Cadastrar empresas clientes e definir o escopo de empresas de cada conta (IAM-09).
````

````{perm} Definir segredos
:id: PERM-MOD-SEGREDOS
:entrega: DSM4
:status: especificado

Definir e remover chaves de LLM e credenciais de conector no cofre selado, sem nunca vê-las (IAM-10).
````

````{perm} Adotar memória
:id: PERM-MEM-ADOTAR
:entrega: DSM4
:status: especificado

Adotar no lugar um arquivo íntegro do SVC-MEM vindo de outra pasta ou de um backup (memoria adotar).
````

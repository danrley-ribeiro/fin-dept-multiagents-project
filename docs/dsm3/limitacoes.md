# Limitações e plano para a DSM4

Situação em 12/11/2026 (v0.5.0). Saíram desta lista, porque foram resolvidos nesta etapa: o
dashboard de usuário único sem login por pessoa (TEST-19 executado, {doc}`acesso`), o LLM restrito
a um provedor (cinco provedores, {doc}`llm`), a checagem do prazo da aprovação que supunha
entrega em um tick e o código de saída de `verificar --ancora` sobre trace sem cadeia
({doc}`revisao`).

## Confiança e chaves

- **Raiz de confiança em processo.** A credencial por identidade impede mensagens e chamadas de
  tools montadas fora do agente dono, e o barramento guarda só hashes; mas código com acesso ao
  objeto Python de outro agente ainda pode usar a credencial dele. Numa versão distribuída: mTLS
  ou assinatura por mensagem.
- **Atestado de decisão só vale no processo que o emitiu.** A chave do HMAC do atestado é gerada
  no início do processo do servidor e nunca gravada. Reiniciar o servidor invalida atestados de
  decisões pendentes (por desenho: limita replay); a raiz de confiança continua sendo o processo:
  quem lê a memória do processo pode atestar.
- **Pedido sem atestado.** O PROT-SOL leva `solicitado_por` sem atestado: a pessoa do pedido vem
  da camada de interface (a sessão do dashboard), e a POL-13 confia nesse campo. Atestado no
  pedido fica para a DSM4.
- **Chaves locais.** O selo do trace, da memória, do cadastro de acesso e da trilha usam chaves
  simétricas na pasta de chaves (`~/.fin_mas/chaves` ou `FIN_MAS_DIR_CHAVES`), fora da pasta de
  dados; quem tiver acesso a essa pasta pode forjar um trace, uma memória ou um cadastro válidos.
  Para terceiros, a verificação do trace usa a âncora pública (hash final).
- **Sem 2FA, delegação, dupla aprovação nem cofre de credenciais.** Um aprovador por ticket, sem
  quatro olhos nem substituição; chaves de LLM só por variável de ambiente (DSM4).

## Dados e privacidade

- **Nomes próprios em texto livre** não são reconhecidos pela redaction (não há reconhecimento
  de entidades); por isso a memória não guarda texto livre, e o trace guarda os usuários do ERP
  porque são a evidência de alçada e SoD.
- **Números soltos de 11 ou 14 dígitos são redigidos** como CPF/CNPJ mesmo quando são outra
  coisa (ex.: "chave pix 98765432100"). Mantido por decisão: falha fechada.
- **Memória entre pastas e entre processos.** Uma cópia íntegra do arquivo de memória em outra
  pasta ou máquina é tratada como comprometida e suspende o waiver até para violações novas, sem
  comando de restauração; duas execuções simultâneas sobre o mesmo arquivo de memória perdem
  entradas sem detecção (o arquivo selado do cadastro de acesso tem trava; a memória ainda não).
- **Pseudônimos não são anonimização.** Valores e contas vão ao provedor externo; por isso o
  envio exige consentimento.
- **Reincidência conferida só na emissão do ticket (POL-06).** A política decide se o waiver é
  oferecido quando o veto é emitido, com o que a memória tem naquele momento, e não confere de
  novo quando a decisão chega. Se dois vetos do mesmo padrão ficam pendentes ao mesmo tempo (ex.:
  agosto e setembro no dashboard, com o aprovador ainda sem decidir agosto), o de setembro é
  emitido antes de o waiver de agosto existir; o aprovador pode então conceder waiver nos dois, e
  a POL-06 não age. Em sequência (agosto decidido antes do veto de setembro), a POL-06 nega o
  novo waiver, como no cenário `reincidencia_waiver`. A correção é conferir a reincidência também
  no `approve` do waiver (o SVC-POL consultando o AG-CIN ou a memória), o que muda o PROT-APR e
  fica para a DSM4, junto com as falhas combinadas.

## Cognição e LLM

- **Provedores reais não exercitados.** Claude, GPT e Gemini foram exercitados só contra um
  servidor falso em loopback; nenhuma chamada real foi feita e a qualidade de um modelo real não
  foi medida. O ganho medido com mocks prova o mecanismo, não o modelo (a bancada
  `fin-mas llm avaliar` está pronta para essa medição).
- **Hipóteses só no AG-ORC e só dois tipos** (`causa_controle`, `efeito_temporal`). AG-RES,
  AG-CUS e AG-REL continuam reativos; as regras locais reconhecem poucas formas de escrever.
- **O AG-ORC não lê a memória aprovada** (SVC-MEM): só o AG-CIN a usa.
- **Negociação sem resposta.** Se o solicitante (o Orquestrador) nunca respondesse a uma proposta
  de prazo, a subtarefa expiraria no prazo original. O Orquestrador sempre responde, por
  obrigação do papel; não há teste com um Orquestrador que se cale.
- **Custo da ação epistêmica sem evidência.** Arquivar uma hipótese depois de esperar o AG-CIN
  custa mensagens e ticks sem mudar o resultado (`hipotese_arquivada`: +4 mensagens, +22 ticks).
- **Memória por padrão, não semântica.** O SVC-MEM indexa por tipo e chave, sem embeddings nem
  grafo. RAG sobre documentos normativos (CP8) continua não implementado: a base normativa é o
  YAML por porte, com proveniência `mcp://normas/...`.

## Interfaces

- **TUI** não verificada em Windows nem em terminais com menos de 80 colunas; o bloqueio por
  cinco senhas e a expiração por inatividade não têm teste pela TUI. O bloqueio tem teste pelo
  servidor e pelo Playwright; a expiração da sessão por tempo (8 horas ou 15 minutos sem uso)
  não tem teste automatizado em nenhuma interface: as revogações testadas são explícitas.
- **Dashboard** só web (responsivo): sem aplicativo móvel ou desktop. A sequência de mensagens de
  uma conversa aparece como lista; o diagrama Mermaid sai pela CLI (`fin-mas sequencia`).
- **Prazos em tempo lógico.** O prazo do ticket é de 20 ticks em lote e 1.800 no dashboard
  (~10 min no ritmo padrão); não há calendário real nem escalonamento a outro aprovador.

## Experimento e método

- **Experimento sem variância entre seeds.** As 10 seeds geram dados diferentes, mas as métricas
  da comparação dependem dos plantios, não dos valores: os grupos têm variância zero. As réplicas
  confirmam o determinismo, não acrescentam estatística.
- **Comparação desequilibrada** (feedback): o baseline não tem veto, correção nem aprovação; a
  diferença mede a arquitetura completa contra um workflow mínimo.
- **Contract Net não adotado** (justificativa em {doc}`coordenacao`): há um especialista por
  capacidade.
- **Fonte da disciplina.** A apostila disponível localmente só tem os capítulos 3 a 5; o que ela
  diz em outros capítulos não foi consultado.

## Achados da correção simulada da v0.5.0 que continuam

A 4ª rodada da correção simulada ({doc}`revisao`) deixou estes pontos sem correção:

- **Prazo compartilhado no AG-ORC.** Quando dois solicitantes legítimos pedem a mesma avaliação,
  vale o prazo mais apertado. Com o registro do barramento fechado, só identidades do diretório
  pedem; ainda assim um segundo pedido encurta o prazo do primeiro.
- **Texto de modelo é filtrado por lista de proibições.** O filtro reduz e não esgota: por isso o
  texto sai rotulado como não verificado. Montar a frase só por template do agente fica para a DSM4.
- **Pedido sem atestado.** A decisão é atestada pela sessão; o pedido leva `solicitado_por`
  declarado pela camada de interface. Pela API o campo vem da sessão; dentro do processo, não é conferido.
- **Fluxo ao vivo.** Quem tem `PERM-SIM-VER` recebe os registros do trace da execução em curso;
  `PERM-AUD-VER` protege a pesquisa, a exportação e a trilha de acesso, não o fluxo.
- **Bloqueio por tentativas.** Quem conhece um nome de usuário bloqueia novas entradas dessa conta
  por 15 minutos (a sessão aberta continua), e a mensagem de bloqueio revela que a conta existe.
- **Esquemas de conteúdo rasos.** O protocolo confere o primeiro nível do conteúdo; o aninhado é
  tratado pelo agente (o Orquestrador converte o erro em falha explícita).
- **Raiz de confiança no disco.** Quem escreve na pasta de chaves refaz o primeiro uso, volta um
  cadastro antigo ou zera a trilha; apagada a chave da trilha, o login segue e a verificação acusa depois.
- **POL-04 é léxica.** Uma justificativa de waiver sem sentido, mas com palavras diferentes, é aceita.
- **Redação.** Não reconhece chave no formato `AIza…`, `senha=…` em texto livre nem token de sessão
  em texto; o token CSRF fica em claro em `sessoes.json`; respostas 501 saem sem os cabeçalhos de segurança.
- **Resposta final ao solicitante.** Se a resposta do Orquestrador ao solicitante (PROT-SOL) se perde
  na entrega, ninguém é avisado: quem pediu precisa consultar de novo. Nos protocolos entre agentes a
  perda é avisada ao iniciador.
- **AG-CUS e AG-REL** continuam reativos, e o `tools/trace.py` confere a existência do teste pelo
  nome, não o que ele verifica.

## Plano para a DSM4

1. **Workflow centralizado funcionalmente equivalente:** um controlador único que aplica as
   mesmas regras de conformidade, correção e aprovação em sequência, para isolar o efeito do
   paradigma do efeito das funções.
2. **Falhas combinadas, portes e parâmetros:** perda de mensagens + agente fora do ar + ataque +
   aprovação expirada + vetos do mesmo padrão pendentes ao mesmo tempo (reincidência conferida também na
   decisão) no mesmo expediente; micro a grande; limiares, prazos, TTL da reserva,
   máximo de correções e teto de extensão variando, para que as seeds tenham variância.
3. **Métricas além da qualidade:** latência, custo de coordenação, robustez e recuperação; MET-17
   e MET-18 por condição.
4. **Cognição:** hipóteses nos demais agentes (AG-RES BDI, AG-CUS e AG-REL), mais tipos, leitura
   da memória aprovada pelo AG-ORC; avaliação de um modelo real na bancada, fora do experimento
   principal.
5. **Acesso:** 2FA, delegação, dupla aprovação, cofre de credenciais, atestado no pedido
   (PROT-SOL).
6. **Memória:** restauração de cópia íntegra e trava entre processos.
7. Perguntas de pesquisa, réplicas, análise e ameaças à validade (CP12), e roteiro de
   demonstração (CP13).

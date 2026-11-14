# Limitações da versão final

O que continua limitado na versão entregue, sem suavizar. Reúne o que segue valendo de
{doc}`../dsm3/limitacoes`, o que o experimento mostrou ({doc}`resultados`) e o que cada lote da DSM4
deixou de fora. Itens resolvidos na DSM4 estão no fim, para que fique claro o que saiu da lista e por quê.

<!-- PENDENTE-INTEGRACAO: os lotes de conectores e de acesso avançado ainda não estão integrados nesta
branch. Quando entrarem: (1) tirar desta página o que eles resolverem (segundo fator, delegação, dupla
aprovação, cofre de credenciais, memória entre processos e cópia íntegra da memória, isolamento entre
empresas); (2) acrescentar as limitações próprias de cada lote (fornecedores de ERP não testados, rede
liberada por permissão, entendimento de fontes por regra). -->

## O resultado do experimento

- **Com as mesmas funções, o SMA não ganha do workflow centralizado em nenhuma métrica de resultado.**
  Empata em qualidade e perde em custo (mensagens e ticks) e em robustez quando mensagens se perdem; a
  partir de 15% de perda por mensagem a diferença é grande. O que a arquitetura compra (separação de
  autoridade, menor privilégio, trilha de quem decidiu) não aparece em métrica de resultado.
- **Recuperação fraca.** O Orquestrador reenvia uma subtarefa uma vez; com perda alta, a maior parte
  das execuções atingidas termina em falha explícita. A distância para o workflow sob perda alta
  depende dessa escolha (três tentativas melhoram a robustez e pioram a latência).
- **Cognição local sem ganho mensurável** na medida registrada (classificação correta), e sem a
  diferença de custo prevista. O sinal na execução correta é exploratório e não significativo.
- **Negociação de prazo sem efeito** na medida designada da ablação.
- **A segunda rodada não é confirmatória**: o defeito foi corrigido depois de ver a primeira, e três
  coisas mudaram entre as rodadas (correção, lugar do sorteio do atraso, conteúdo do braço local).

## Validade do experimento

- **A robustez favorece o workflow por construção**: o modelo de falhas só atinge mensagens entre
  agentes. Um workflow distribuído (controlador com serviços remotos), que seria a linha de base justa
  para robustez, não foi construído.
- **Modelo de falhas simples**: perda independente por mensagem, sem rajadas nem partição de rede;
  nenhuma falha de dados; **o Orquestrador nunca cai** (ponto único de falha conhecido, não exercitado,
  sem substituto).
- **Mensagens com pessoas não se perdem** no experimento (PROT-SOL e PROT-APR); a demora humana é
  modelada à parte.
- **Equivalência testada só sem falhas**, e o workflow equivalente foi escrito pelos mesmos autores
  depois do SMA, lendo os agentes.
- **Dados sintéticos com plantio**; o gabarito é o que foi plantado e tem teto abaixo de 100% em três
  situações de rótulo único.
- **Pouco poder para efeitos raros**: os efeitos aparecem em blocos de seed; comparações de cognição e
  negociação têm de 1 a 6 seeds diferentes em 30. Holm controla o erro por família, não no experimento.
- **A amostra não teve aprovador rigoroso** (probabilidade 0,10, não saiu nas 30 seeds).
- **MEI e Média empresa II fora do experimento** (o workflow equivalente não implementa as regras deles).
- **O bloco de fuzz** (invariantes em milhares de seeds) não foi feito.
- **A trilha de acesso não foi medida** (a previsão de mais auditoria com o SVC-IAM não pôde ser
  conferida no trace).
- **Tempo de parede** de uma máquina, uma rodada: ordem de grandeza, nada mais.

## Confiança, chaves e acesso

- **Raiz de confiança no processo.** Código com acesso ao objeto Python de outro agente pode usar a
  credencial dele; o atestado de decisão só vale no processo que o emitiu (reiniciar invalida
  atestados pendentes). Numa versão distribuída: mTLS ou assinatura por mensagem.
- **Raiz de confiança no disco.** Selos de trace, memória, cadastro e trilha usam chaves simétricas na
  pasta de chaves; quem escreve nela forja um trace, uma memória ou um cadastro válidos, refaz o
  primeiro uso, volta um cadastro antigo ou zera a trilha. Para terceiros, o trace se verifica pela
  âncora pública.
- **Pedido sem atestado.** O PROT-SOL leva `solicitado_por` declarado pela camada de interface; dentro
  do processo, não é conferido.
- **Resposta final ao solicitante perdida não é avisada**: quem pediu precisa consultar de novo (nos
  protocolos entre agentes, a perda é avisada ao iniciador desde a correção da DSM4).
- **Sem segundo fator, delegação, dupla aprovação nem cofre de credenciais** nesta branch; chaves de
  LLM só por variável de ambiente. <!-- PENDENTE-INTEGRACAO: acesso avançado -->
- **Prazo compartilhado no AG-ORC**: um segundo pedido legítimo da mesma avaliação encurta o prazo do
  primeiro.
- **Fluxo ao vivo**: quem tem `PERM-SIM-VER` recebe os registros do trace da execução em curso.
- **Bloqueio por tentativas**: quem conhece um nome de usuário bloqueia novas entradas da conta por
  15 minutos, e a mensagem revela que a conta existe.
- **POL-04 é léxica**: justificativa de waiver sem sentido, com palavras diferentes, é aceita.
- **Esquemas de conteúdo rasos**: o protocolo confere o primeiro nível; o aninhado é tratado pelo agente.

## Dados e privacidade

- **Nomes próprios em texto livre** não são reconhecidos pela redaction; por isso a memória não guarda
  texto livre.
- **Números soltos de 11 ou 14 dígitos são redigidos** como CPF/CNPJ mesmo quando são outra coisa
  (falha fechada, por decisão).
- **Redação incompleta**: não reconhece chave no formato `AIza…`, `senha=…` em texto livre nem token de
  sessão em texto; o token CSRF fica em claro em `sessoes.json`; respostas 501 saem sem os cabeçalhos
  de segurança.
- **Memória entre pastas e entre processos**: cópia íntegra em outra pasta é tratada como comprometida;
  duas execuções simultâneas sobre o mesmo arquivo de memória perdem entradas sem detecção.
  <!-- PENDENTE-INTEGRACAO: o lote de acesso avançado põe o SVC-MEM sobre o ArquivoSelado e acrescenta
  `memoria adotar`; tirar este item quando entrar. -->
- **Pseudônimos não são anonimização**: valores e contas vão ao provedor externo; por isso o envio exige
  consentimento.
- **A memória do SVC-MEM não tem migração possível** (os pseudônimos são HMAC sem volta).

## Cognição e LLM

- **Nenhum provedor real de LLM foi exercitado**; só mocks e servidor falso em loopback. O ganho medido
  com mocks prova o mecanismo, não o modelo. A bancada `fin-mas llm avaliar` está pronta e não foi usada
  com modelo real.
- **AG-REL BDI não acrescenta capacidade** (uma tabela de decisão faria o mesmo); **AG-CUS BDI** é uma
  cadeia curta e síncrona, e o ganho é transparência.
- **Regras locais reconhecem poucas formas de escrever**: observação parafraseada não gera hipótese
  (o experimento sorteia paráfrases para medir isso).
- **AG-RES** só trata piora do EBITDA% (melhora relevante não gera hipótese), não tem hipóteses por LLM
  e não negocia prazo: replaneja dentro do prazo que recebeu.
- **Compromisso por porte** é `aberto` em todos; as outras estratégias existem só como fator. O
  compromisso cego tem teto de duas insistências (desvio declarado da definição pura, para que toda
  solicitação tenha resposta).
- **Aprendizado**: uma regra que errou duas vezes pode estar certa na terceira; o efeito medido é de
  custo (uma consulta a menos), e o AG-CIN ainda vetaria o lançamento no fechamento.
- **Base normativa** (CP8): busca lexical (BM25) sobre trechos curtos em paráfrase das normas citadas,
  não sobre o texto oficial; não há recuperação semântica nem documentos externos. A regra de duplicidade
  fica "sem evidência" por não ter norma externa citada pelo projeto.
- **Texto de modelo é filtrado por lista de proibições**: o filtro reduz e não esgota; por isso o texto
  sai rotulado como não verificado, depois do conteúdo determinístico.
- **Custo da ação epistêmica sem evidência**: arquivar uma hipótese depois de esperar o AG-CIN custa
  mensagens e ticks sem mudar o resultado.
- **Negociação sem resposta**: se o Orquestrador nunca respondesse a uma proposta de prazo, a subtarefa
  expiraria no prazo original; não há teste com um Orquestrador que se cale.

## Implantação, portes e segmentos

- **Uma máquina, só loopback**: exposição em rede ou nuvem está fora do escopo por decisão do dono do
  produto. Proxy na frente ou porta em outra interface é exposição em rede.
- **Docker Compose não executado** nesta máquina (o plugin estava quebrado); a imagem foi construída e
  executada com as mesmas opções, e o `compose.yaml` é conferido por teste de leitura.
- **Migração sem migrações reais**: o mecanismo existe e é exercido por uma migração de exemplo só no
  teste; hoje não há o que migrar.
- **MEI**: obrigações acessórias e data de publicação da LC 238/2026 no DOU **a confirmar**; o plantio de
  alçada é recusado (não há alçada menor para violar). Os números de regra dos portes e dos segmentos
  (alçadas, materialidade, pesos, direcionadores) são **parâmetros da simulação**, não lei.
- **Integração com ERP real** fora do escopo. <!-- PENDENTE-INTEGRACAO: conectores genéricos -->

## Interfaces e testes

- **TUI** não verificada em Windows nem em terminais com menos de 80 colunas; bloqueio por senhas e
  expiração por inatividade sem teste pela TUI; expiração da sessão por tempo sem teste automatizado em
  nenhuma interface.
- **Dashboard só web**; a sequência de uma conversa aparece como lista (o diagrama sai pela CLI).
- **Prazos em tempo lógico**: sem calendário real nem escalonamento a outro aprovador.
- **Os roteiros Playwright** rodam no CI e por `make web-test`; não foram executados na geração do
  relatório final.
- **`tools/trace.py` confere a existência do teste pelo nome**, não o que ele verifica.
- **Sem testes unitários novos** desde a DSM2, por decisão dos autores: a cobertura nova é por e2e,
  integração e interface.

## Método e fontes

- **Contract Net não adotado**: há um especialista por capacidade. Faria sentido com verificadores
  concorrentes, que não existem.
- **A apostila disponível localmente só tem os capítulos 3 a 5**; o que ela diz em outros capítulos
  não foi consultado.

## Saíram da lista na DSM4

| Limitação da DSM3 | O que mudou |
|---|---|
| Experimento sem variância entre seeds | plantios, falhas, aprovador e ataques sorteados por seed ({doc}`experimento`) |
| Comparação desequilibrada (baseline sem veto, correção nem aprovação) | workflow funcionalmente equivalente, com a equivalência garantida por teste |
| AG-RES, AG-CUS e AG-REL só reativos | variantes BDI nos níveis `local` e `llm` ({doc}`ADR-010-especialistas-bdi`) |
| O AG-ORC não lê a memória aprovada | lê correções aprovadas por tipo (cenário `memoria_reincidencia_orc`) |
| CP8 sem conhecimento com proveniência | base normativa versionada com busca lexical e "sem evidência" ({doc}`cognicao`) |
| Resposta perdida entre agentes podia deixar a solicitação sem resposta | aviso de prazo ao iniciador; 0 execuções sem resposta na segunda rodada |

# Limitações e plano para a DSM4

## Limitações conhecidas

- **Raiz de confiança em processo.** A credencial por identidade impede mensagens e chamadas de
  tools montadas fora do agente dono, e o barramento guarda só hashes; mas código com acesso ao
  objeto Python de outro agente ainda pode usar a credencial dele. Numa versão distribuída: mTLS
  ou assinatura por mensagem.
- **Chaves locais.** O selo do trace e a assinatura da memória usam chaves simétricas no
  diretório do usuário (`~/.fin_mas/`), fora da pasta de dados; quem tiver acesso a esse
  diretório pode forjar um trace ou uma memória válidos. Para terceiros, a verificação do trace
  usa a âncora pública (hash final). Em produção: cofre de segredos e assinatura assimétrica.
- **Nomes próprios em texto livre** não são reconhecidos pela redaction (não há reconhecimento
  de entidades); por isso a memória não guarda texto livre, e o trace guarda os usuários do ERP
  porque são a evidência de alçada e SoD.
- **Experimento sem variância entre seeds.** As 10 seeds geram dados diferentes, mas as métricas
  da comparação (acerto, mensagens, latência) dependem dos plantios, não dos valores: os 28 grupos
  têm variância zero. As réplicas confirmam o determinismo, não acrescentam estatística; a DSM4
  precisa variar plantios, parâmetros e falhas.
- **Memória por padrão, não semântica.** O SVC-MEM indexa por tipo e chave (regra + pessoa ou
  fornecedor), sem embeddings nem grafo; serve à reincidência, não a perguntas abertas. RAG
  sobre documentos normativos (CP8) continua não implementado: a base normativa é o YAML por
  porte, com proveniência `mcp://normas/...`.
- **Contract Net não adotado** (justificativa em {doc}`coordenacao`): há um especialista por
  capacidade.
- **Prazos em tempo lógico.** O prazo do ticket é de 20 ticks em lote e 1.800 no dashboard
  (~10 min no ritmo padrão); não há calendário real nem escalonamento a outro aprovador.
- **Aprovador único por ticket.** A política suporta cadastro por papel e SoD, mas não aprovação
  em dupla (quatro olhos) nem delegação.
- **LLM real não exercitado nos testes.** O provedor `claude-opus-5-5` só roda com o SDK e
  credencial; a suíte usa mocks determinísticos, e a qualidade da síntese real não foi medida.
- **Dashboard de usuário único:** o servidor escuta só em loopback, recusa `Host`/`Origin` de
  fora e exige token de sessão nos POST (TEST-73), o que barra outros sites (CSRF) e DNS
  rebinding. Um processo local que leia `/api/sessao` ainda pode agir como o aprovador `APR`;
  login por pessoa e filtros do dashboard seguem como TEST-19 (entrega futura).
- **Comparação experimental desequilibrada** (feedback): o baseline não tem veto, correção nem
  aprovação.

## Plano para a DSM4

1. **Workflow centralizado funcionalmente equivalente:** um controlador único que aplica as
   mesmas regras de conformidade, correção e aprovação em sequência, para isolar o efeito do
   paradigma (distribuição, autonomia, reconsideração) do efeito das funções.
2. **Falhas combinadas:** perda de mensagens + agente fora do ar + ataque + aprovação expirada
   no mesmo expediente.
3. **Portes e parâmetros:** micro a grande; limiares, prazos de subtarefa e de aprovação, TTL da
   reserva e máximo de correções variando.
4. **Métricas além da qualidade:** latência (lógica e de parede), custo de coordenação
   (mensagens por solicitação e por decisão), robustez (fração de ataques e falhas absorvidos) e
   recuperação (tempo e caminho até resposta explícita).
5. Perguntas de pesquisa, réplicas por seed, análise e ameaças à validade (CP12), e roteiro de
   demonstração (CP13).

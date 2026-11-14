// Roteiro da demonstração guiada (opcional, desligada por padrão). Só dados: cada passo diz o que observar e qual
// comando o botão dispara no servidor (`/api/comando`, os mesmos comandos da barra de controles). Quem executa é a
// pessoa logada, com as permissões dela: o servidor confere de novo cada comando. Para mudar a demonstração, edite
// esta lista; o componente `GuiaDemo` não conhece nenhum passo em particular.

export type AbaDemo = "escritorio" | "logs" | "comparacao";

export interface AcaoDemo {
  /** Texto do botão. */
  rotulo: string;
  /** Permissões que os comandos exigem (models/permissions.yaml); sem elas o botão fica desligado, com o motivo. */
  permissoes: string[];
  /** Comandos enviados em ordem. Em `reiniciar`, o nível de cognição entra pelo campo `cognicao` abaixo. */
  comandos: Record<string, unknown>[];
  /** Nível de cognição do passo. Mudar o nível exige PERM-MOD-CONFIG: se a conta não tem e o nível atual é outro,
   *  o passo roda no nível atual, a não ser que `obrigatoria` (aí o botão fica desligado, com o motivo). */
  cognicao?: { nivel: "basico" | "local"; obrigatoria?: boolean };
}

export interface PassoDemo {
  id: string;
  titulo: string;
  /** Uma frase: o que este passo mostra. */
  resumo: string;
  /** O que olhar na tela, na ordem em que acontece. */
  observar: string[];
  acao?: AcaoDemo;
  /** Aba que o botão do passo abre (se a conta a enxerga) e agente que fica selecionado no escritório. */
  aba?: AbaDemo;
  agente?: string;
  /** Filtro aplicado na aba Logs quando o passo a abre. */
  filtroLogs?: Record<string, string>;
  /** Leitura complementar fora do dashboard. */
  link?: { rotulo: string; href: string };
}

const DOCUMENTACAO = "https://fin-dept-multiagents-project.readthedocs.io";

export const ROTEIRO: PassoDemo[] = [
  {
    id: "fechamento",
    titulo: "Fechamento normal",
    resumo: "O pedido de fechar o mês percorre o escritório sem nenhuma inconformidade.",
    observar: [
      "O Orquestrador (AG-ORQ) recebe SOL-001 e delega aos especialistas: envelopes azuis na planta.",
      "Custos, Orçamento e Resultado respondem; o AG-CIN confere e não veta.",
      "Em “Pedidos da liderança”, SOL-001 termina como publicado.",
    ],
    acao: { rotulo: "Rodar o fechamento", permissoes: ["PERM-SIM-OPERAR"], cognicao: { nivel: "basico" },
      comandos: [{ tipo: "retomar" }, { tipo: "reiniciar", cenario: "fechar_mes" }] },
    aba: "escritorio",
    agente: "AG-ORQ",
  },
  {
    id: "veto",
    titulo: "Veto e decisão humana",
    resumo: "Um lançamento acima da alçada: o AG-CIN veta a publicação e a decisão é de uma pessoa.",
    observar: [
      "O carimbo VETO aparece no AG-CIN e o sino do cabeçalho fica vermelho.",
      "Clique no sino: o veto mostra o achado, o prazo e as opções (corrigir no ERP, waiver com justificativa, bloquear).",
      "Decida com a sua conta (papel de aprovador): a decisão fica registrada com o seu nome e o pedido segue.",
    ],
    acao: { rotulo: "Rodar o cenário do veto", permissoes: ["PERM-SIM-OPERAR"], cognicao: { nivel: "basico" },
      comandos: [{ tipo: "retomar" }, { tipo: "reiniciar", cenario: "veto_waiver" }] },
    aba: "escritorio",
    agente: "AG-CIN",
  },
  {
    id: "agente-fora",
    titulo: "Agente desligado: reenvio e falha explícita",
    resumo: "O AG-CUS sai de operação antes do fechamento começar; ninguém finge que deu certo.",
    observar: [
      "O chip do AG-CUS fica “fora” e a mensagem para ele cai (✕ na planta).",
      "O Orquestrador espera o prazo, reenvia a delegação uma vez e espera de novo.",
      "Sem resposta, SOL-001 termina como “falhou”, com o motivo; nada é publicado pela metade.",
      "O botão ⏻ no chip religa o agente; o passo seguinte reinicia o cenário com todos ligados.",
    ],
    acao: { rotulo: "Desligar o AG-CUS e fechar o mês", permissoes: ["PERM-SIM-OPERAR", "PERM-AGT-ENERGIA"],
      cognicao: { nivel: "basico" },
      comandos: [{ tipo: "pausar" }, { tipo: "reiniciar", cenario: "fechar_mes" },
        { tipo: "agente", agente: "AG-CUS", online: false }, { tipo: "retomar" }] },
    aba: "escritorio",
    agente: "AG-ORQ",
  },
  {
    id: "ataque",
    titulo: "Ataque recusado no trace",
    resumo: "Com um veto pendente, chegam decisões forjadas; o barramento e a política recusam todas.",
    observar: [
      "Na aba Logs, o filtro “rejected” mostra cada tentativa recusada (remetente desconhecido, credencial falsa, papel sem direito, ticket trocado), com o motivo.",
      "O botão “?” de um registro explica a cadeia que levou até ele.",
      "O veto continua pendente (sino vermelho): nenhuma decisão forjada mudou o estado do pedido.",
    ],
    acao: { rotulo: "Rodar o cenário de ataque", permissoes: ["PERM-SIM-OPERAR"], cognicao: { nivel: "basico" },
      comandos: [{ tipo: "retomar" }, { tipo: "reiniciar", cenario: "ataque_decisao_forjada" }] },
    aba: "logs",
    filtroLogs: { tipo: "rejected" },
    agente: "AG-CIN",
  },
  {
    id: "hipotese",
    titulo: "Hipótese confirmada na mente do agente",
    resumo: "No nível de cognição local, o AG-ORC levanta uma hipótese, pede evidência e só então conclui.",
    observar: [
      "No painel à direita (Mente de AG-ORC), abra a aba Hipóteses.",
      "A hipótese nasce de uma regra local e o AG-ORC consulta o AG-CIN (envelope verde-água); a primeira consulta se perde de propósito e ele pergunta de novo.",
      "Com a resposta, ela passa a “confirmada”, com a evidência (QRY-002); a conta é atribuída a controle, sem falso desvio.",
    ],
    acao: { rotulo: "Rodar com cognição local", permissoes: ["PERM-SIM-OPERAR"], cognicao: { nivel: "local", obrigatoria: true },
      comandos: [{ tipo: "retomar" }, { tipo: "reiniciar", cenario: "orc_hipotese_local" }] },
    aba: "escritorio",
    agente: "AG-ORC",
  },
  {
    id: "experimento",
    titulo: "Resultado do experimento",
    resumo: "As mesmas seeds no sistema multiagente e no workflow centralizado, lado a lado.",
    observar: [
      "A aba “SMA × workflow” compara os dois por cenário: desvios classificados como no gabarito, mensagens e falhas.",
      "“Ver como tabela” mostra os números de cada cenário.",
      "O desenho do experimento, as métricas e as limitações estão na documentação (DSM4, Experimento).",
    ],
    acao: { rotulo: "Abrir SMA × workflow", permissoes: [], comandos: [] },
    aba: "comparacao",
    link: { rotulo: "Documentação do projeto (DSM4 › Experimento)", href: DOCUMENTACAO },
  },
];

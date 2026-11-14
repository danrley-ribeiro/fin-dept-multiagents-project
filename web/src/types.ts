// Registro do trace (SVC-AUD) exatamente como o Python grava: os campos variam por `kind`.
export interface Registro {
  seq: number;
  t: number;
  kind: string;
  conversation_id?: string | null;
  protocol?: string | null;
  sender?: string;
  receiver?: string;
  performative?: string;
  content?: Record<string, unknown>;
  de?: string;
  para?: string;
  agente?: string;
  [campo: string]: unknown;
}

export interface FichaAgente {
  id: string;
  titulo: string;
  departamento?: string;
  cognicao: string;
  papeis: string[];
}

export interface Empresa {
  sigla: string;
  razao_social: string;
  descricao: string;
}

export interface Cenario {
  nome: string;
  descricao: string;
  cognicao?: string;
  esperado?: string;
}

export interface Controle {
  cenario: string;
  seed: number;
  t: number;
  pausado: boolean;
  ms_por_tick: number;
  offline: string[];
  interativo: boolean;
  fila: number;
  geracao: number;
  porte?: string;
  fonte?: string;
  cognicao?: string;
}

/** Hipótese de um agente cognitivo (ADR-008): proposta validada, à espera de evidência, ou já decidida. */
export interface Hipotese {
  id: string;
  tipo: string;
  alvo: string;
  estado: string; // aceita (proposta) | em_verificacao | confirmada | refutada | arquivada
  origens: string[];
  justificativa?: string;
  fonte?: string; // evidência que confirmou ou refutou
  motivo?: string;
  seq: number;
  t: number;
}

export interface Crenca {
  valor: unknown;
  antes: unknown;
  fonte: string;
  seq: number;
  t: number;
}

export interface Desejo {
  id: string;
  prioridade: number;
  estado: string;
  motivo: string;
  seq: number;
}

export interface Intencao {
  id: string;
  desejo: string;
  plano: string;
  estado: string;
  motivo: string;
  aguardando?: string;
  seq: number;
  historico: { evento: string; motivo: string; t: number }[];
}

export interface Opcao {
  plano: string;
  aplicavel: boolean;
  motivo: string;
  utilidade: number;
  atende?: string[];
}

export interface Deliberacao {
  desejo: string;
  escolhido: string | null;
  opcoes: Opcao[];
  t: number;
  seq: number;
}

export interface Decisao {
  regra: string;
  entradas: unknown;
  resultado: unknown;
  t: number;
  seq: number;
  conversa: string;
}

export interface Mente {
  crencas: Record<string, Crenca>;
  desejos: Record<string, Desejo>;
  intencoes: Record<string, Intencao>;
  deliberacoes: Deliberacao[];
  decisoes: Decisao[];
  hipoteses: Record<string, Hipotese>;
  propostasRejeitadas: { tipo: string; alvo: string; origem: string; motivo: string; seq: number; t: number }[];
}

export interface EstadoAgente {
  id: string;
  ultimaAtividade: number; // t do último registro produzido pelo agente
  bolha: { texto: string; tipo: string; t: number } | null;
  mente: Mente;
  vetando: boolean;
}

export interface Conversa {
  id: string;
  protocolo: string;
  estado: string;
  iniciador: string;
  contraparte: string;
}

export type FonteDados = "ERP" | "Planilhas" | "Normas";

export interface Voo {
  id: number; // seq do registro que originou o voo
  de: string;
  para: string;
  rotulo: string;
  protocolo: string;
  tipo: "mensagem" | "mcp" | "perdida" | "humano";
}

export interface PendenciaHumana {
  solicitacao: string;
  conversation_id: string;
  competencia?: string;
  achados: { regra: string; lancamento: string; severidade: string; evidencia?: string }[];
  correcoes_sugeridas: { lancamento: string; regras: string[]; acao: string }[];
  opcoes: string[];
}

export interface Solicitacao {
  sid: string;
  intencao: string;
  competencia: string;
  status: string; // aguardando | em_execucao | publicado | ... | failure | refuse
  detalhe?: string;
}

export interface ViewState {
  t: number;
  seq: number;
  agentes: Record<string, EstadoAgente>;
  conversas: Record<string, Conversa>;
  voos: Voo[]; // voos disparados pelos registros mais recentes
  offline: string[];
  pendentes: Record<string, PendenciaHumana>;
  solicitacoes: Record<string, Solicitacao>;
  reservas: Record<string, string>; // "SMA/2026-09" -> solicitação dona
  historicoReservas: { t: number; evento: string; chave: string; quem: string; resultado: string }[];
  fontes: Record<FonteDados, { chamadas: number; ultimaT: number; indisponivel?: string }>;
  chamadasMcp: { seq: number; t: number; agente: string; tool: string; fonte: string; negada?: string }[];
  registros: Registro[];
  meta: Registro | null;
}

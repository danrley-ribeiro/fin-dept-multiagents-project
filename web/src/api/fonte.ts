// Fontes de dados: servidor Python ao vivo (/api) ou traces exportados (replay offline).
import type { Cenario, Controle, Empresa, FichaAgente, Registro } from "../types";
import { acessoNegado, AUTOMATICO, postar as postarComSessao, sessaoEncerrada } from "./sessao";

export interface Catalogo {
  cenarios: Cenario[];
  agentes: Record<string, FichaAgente>;
  empresa: Empresa;
  portes?: { porte: string; titulo: string; tem_erp: boolean; norma_contabil: string }[];
}

export type EventoAoVivo =
  | { tipo: "reset"; geracao: number; cenario: string; seed: number }
  | { tipo: "registro"; geracao: number; registro: Registro }
  | { tipo: "controle"; geracao: number; estado: Controle; erro?: string }
  | { tipo: "sessao_encerrada" }
  | { tipo: "fluxo_encerrado"; regra: string; motivo: string };

export interface TraceExportado {
  cenario: { nome: string; descricao: string; seed: number; intencao: string };
  registros: Registro[];
  mentes_finais: Record<string, MenteSnapshot>;
  hash: string;
}

export interface PlanoInfo {
  id: string;
  desejo: string;
  descricao: string;
  atende: string[];
  utilidade: number;
}

export interface MenteSnapshot {
  id: string;
  estado: unknown;
  conhecimento: Record<string, unknown>;
  bdi?: { planos: PlanoInfo[]; desejos_permanentes: Record<string, number> };
}

/** Tenta o servidor local; devolve null se não houver backend (modo replay). */
export async function catalogoAoVivo(): Promise<Catalogo | null> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch("/api/cenarios", { signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok || !(r.headers.get("content-type") ?? "").includes("json")) return null;
    return (await r.json()) as Catalogo;
  } catch {
    return null;
  }
}

export function conectarAoVivo(aoEvento: (e: EventoAoVivo) => void, aoErro: () => void): () => void {
  const fonte = new EventSource("/api/eventos");
  fonte.onmessage = (m) => {
    const evento = JSON.parse(m.data) as EventoAoVivo;
    if (evento.tipo === "sessao_encerrada") {  // sessão revogada ou expirada: o servidor fecha o fluxo
      fonte.close();
      sessaoEncerrada();
      return;
    }
    if (evento.tipo === "fluxo_encerrado") {  // permissão retirada ou empresa fora do escopo: o servidor fecha o fluxo
      fonte.close();
      acessoNegado(`${evento.regra}: ${evento.motivo}`);
      aoErro();
      return;
    }
    aoEvento(evento);
  };
  fonte.onerror = () => aoErro();
  return () => fonte.close();
}

/** POST JSON autenticado (sessão da pessoa + token CSRF) para a API do servidor local. */
export const postar = postarComSessao;

export async function enviarComando(cmd: Record<string, unknown>): Promise<string | null> {
  const r = await postar("/api/comando", cmd);
  if (r.ok) return null;
  const corpo = (await r.json().catch(() => ({}))) as { erro?: string };
  return corpo.erro ?? `erro ${r.status}`;
}

export async function estadoAoVivo(): Promise<{ agentes: Record<string, MenteSnapshot> } | null> {
  try {
    const r = await fetch("/api/estado", { headers: AUTOMATICO });
    if (r.status === 401) sessaoEncerrada();
    // 403 por segundo fator exigido ou por empresa: a aplicação leva a pessoa à tela certa
    else if (r.status === 403) acessoNegado(((await r.json().catch(() => ({}))) as { erro?: string }).erro);
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  }
}

export async function catalogoReplay(): Promise<Catalogo> {
  const r = await fetch("/traces/index.json");
  if (!r.ok) throw new Error("traces não encontrados: rode `python -m fin_mas export`");
  return (await r.json()) as Catalogo;
}

export async function carregarTrace(nome: string): Promise<TraceExportado> {
  const r = await fetch(`/traces/${nome}.json`);
  if (!r.ok) throw new Error(`trace ${nome} não encontrado`);
  return (await r.json()) as TraceExportado;
}

export interface ResumoComparacao {
  [cenario: string]: Record<string, Record<string, number | string | null>>;
}

export async function carregarComparacao(): Promise<ResumoComparacao | null> {
  try {
    const r = await fetch("/traces/comparacao.json");
    return r.ok ? ((await r.json()) as ResumoComparacao) : null;
  } catch {
    return null;
  }
}

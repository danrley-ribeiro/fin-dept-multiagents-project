// Acesso avançado (ADR-012) no que a própria pessoa usa pela web: o seu segundo fator, a empresa ativa da sessão e,
// para quem tem a permissão, as chaves de LLM do cofre. Contas, política e delegações continuam na TUI e na CLI.
import { ler, postar, type Sessao } from "./sessao";

async function resposta<T>(rota: string, corpo: unknown): Promise<{ dados?: T; erro?: string }> {
  try {
    const r = await postar(rota, corpo);
    const d = await r.json().catch(() => ({}));
    return r.ok ? { dados: d as T } : { erro: (d as { erro?: string }).erro ?? `erro ${r.status}` };
  } catch (e) {
    return { erro: String(e) };
  }
}

// ---------------------------------------------------------------- segundo fator (IAM-08)
export interface SituacaoSegundoFator {
  ativo: boolean;
  desde: number | null;
  codigos_restantes: number;
  /** A política do cadastro exige o segundo fator para um papel desta conta. */
  exigido: boolean;
}

export const situacaoSegundoFator = () => ler<SituacaoSegundoFator>("/api/2fa");

/** Segredo e endereço `otpauth://`: o servidor só os entrega aqui, uma vez. */
export const iniciarSegundoFator = () => resposta<{ segredo: string; uri: string }>("/api/2fa/ativar", {});

/** Confere o primeiro código e ativa; devolve os códigos de recuperação, que também só aparecem uma vez. */
export const confirmarSegundoFator = (codigo: string) =>
  resposta<{ codigos_recuperacao: string[] }>("/api/2fa/confirmar", { codigo });

/** Troca os códigos de recuperação: exige a senha atual e um código válido (IAM-08). */
export const renovarCodigosDeRecuperacao = (codigo: string, senha: string) =>
  resposta<{ codigos_recuperacao: string[] }>("/api/2fa/recuperacao", { codigo, senha });

/** Desativa o segundo fator: exige a senha atual e um código válido (IAM-08). */
export const desativarSegundoFator = (codigo: string, senha: string) =>
  resposta<{ ativo: boolean }>("/api/2fa/desativar", { codigo, senha });

// ---------------------------------------------------------------- empresa ativa (IAM-09)
export interface EmpresaDaConta { id: string; nome: string; porte: string }
export interface EmpresasDaConta {
  /** O cadastro tem empresas: toda permissão que não é da administração exige uma empresa ativa. */
  multiempresa: boolean;
  ativa: string | null;
  empresas: EmpresaDaConta[];
}

export async function empresasDaConta(): Promise<EmpresasDaConta | null> {
  return (await ler<EmpresasDaConta>("/api/empresa")).dados ?? null;
}

/** Troca a empresa ativa da sessão; a sessão devolvida já fala com a simulação da empresa escolhida. */
export const escolherEmpresa = (empresa: string) => resposta<{ ativa: string; sessao: Sessao }>("/api/empresa", { empresa });

// ---------------------------------------------------------------- chaves de LLM no cofre (IAM-10)
export interface ChaveProvedor {
  id: string;
  variavel: string;
  /** Nome do segredo no cofre (`llm:<VARIAVEL>`). */
  segredo: string;
  ambiente: boolean;
  cofre: boolean;
  opcional: boolean;
}
export interface Segredos {
  segredos: { nome: string; por: string; em: number }[];
  provedores: ChaveProvedor[];
}

/** O valor entra aqui e segue direto para o servidor: não é guardado, devolvido nem escrito em log. */
export const definirSegredo = (nome: string, valor: string) => resposta<{ existe: boolean }>("/api/segredos", { nome, valor });

export const removerSegredo = (nome: string) => resposta<{ removido: boolean }>("/api/segredos/remover", { nome });

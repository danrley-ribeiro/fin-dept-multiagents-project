// Sessão da pessoa no servidor local (ADR-009): login por usuário e senha, cookie HttpOnly e token CSRF.
// O token CSRF vive só na memória desta página; o cookie da sessão o navegador guarda e o JavaScript não lê.

export interface Sessao {
  usuario: string;
  nome: string;
  papeis: string[];
  permissoes: string[];
  pessoa_erp: string | null;
  cargo: string | null;
  expira_em: number;
  trocar_senha: boolean;
  /** A política do cadastro exige o segundo fator e a conta ainda não o ativou (IAM-08): só dá para ativá-lo. */
  pendente_2fa?: boolean;
  /** Empresa ativa da sessão e empresas do escopo da conta (IAM-09); vazio quando o cadastro tem uma empresa só. */
  empresa?: string | null;
  empresas?: string[];
}

/** Senha certa e segundo fator ativo: falta o código. A pré-sessão vive poucos minutos e aceita poucas tentativas. */
export interface SegundoFatorPendente {
  expiraEm: number; // epoch em segundos, do relógio do servidor (que roda nesta máquina)
  tentativas: number;
}

export interface Saude {
  ok: boolean;
  versao: string;
  acesso: { sem_contas: boolean; integro: boolean; cabecalho: string };
}

let csrf = "";
let cabecalho = "X-SMA-Token";
const ouvintes = new Set<() => void>();

const ouvintesAcesso = new Set<() => void>();

/** Avisa a aplicação quando o servidor passa a negar por segundo fator exigido (IAM-08) ou por empresa (IAM-09). */
export function aoMudarAcesso(f: () => void): () => void {
  ouvintesAcesso.add(f);
  return () => { ouvintesAcesso.delete(f); };
}

/** Chamado com o motivo de um 403: só as regras que mudam a tela da pessoa disparam o aviso. */
export function acessoNegado(erro: string | undefined): void {
  if (erro && /^(IAM-08: a política|IAM-09:)/.test(erro)) ouvintesAcesso.forEach((f) => f());
}

/** Avisa a aplicação quando o servidor diz que a sessão acabou (expirou, foi revogada, conta bloqueada). */
export function aoEncerrarSessao(f: () => void): () => void {
  ouvintes.add(f);
  return () => { ouvintes.delete(f); };
}

export function sessaoEncerrada(): void {
  csrf = "";
  ouvintes.forEach((f) => f());
}

/** Há servidor local? `null` = sem backend (o dashboard abre em replay offline, sem login). */
export async function saude(): Promise<Saude | null> {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch("/api/saude", { signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok || !(r.headers.get("content-type") ?? "").includes("json")) return null;
    return (await r.json()) as Saude;
  } catch {
    return null;
  }
}

function guardar(d: { csrf: string; cabecalho: string }) {
  csrf = d.csrf;
  cabecalho = d.cabecalho;
}

export async function sessaoAtual(): Promise<Sessao | null> {
  const r = await fetch("/api/sessao");
  if (!r.ok) return null;
  const d = (await r.json()) as { sessao: Sessao; csrf: string; cabecalho: string };
  guardar(d);
  return d.sessao;
}

interface RespostaLogin { sessao?: Sessao; csrf?: string; cabecalho?: string; erro?: string; segundo_fator?: string;
  expira_em?: number; tentativas?: number; pre_sessao?: { expira_em: number; tentativas_restantes: number } | null }

/** Primeiro passo: usuário e senha. Com o segundo fator ativo o servidor não abre a sessão: devolve `segundoFator`
 *  e guarda a pré-sessão num cookie que o JavaScript não lê e que só vale para `confirmarCodigo`. */
export async function entrar(usuario: string, senha: string): Promise<{ sessao?: Sessao; erro?: string;
  segundoFator?: SegundoFatorPendente }> {
  const r = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, senha }) });
  const d = (await r.json().catch(() => ({}))) as RespostaLogin;
  if (r.ok && d.segundo_fator === "pendente") {
    return { segundoFator: { expiraEm: d.expira_em ?? Date.now() / 1000 + 300, tentativas: d.tentativas ?? 5 } };
  }
  if (!r.ok || !d.sessao) return { erro: d.erro ?? `erro ${r.status}` };
  guardar({ csrf: d.csrf ?? "", cabecalho: d.cabecalho ?? cabecalho });
  return { sessao: d.sessao };
}

/** Segundo passo: código do aplicativo (6 dígitos) ou código de recuperação. O motivo exato da recusa fica na trilha
 *  do servidor; a tela só sabe se ainda dá para tentar (`tentativasRestantes`) ou se a pré-sessão acabou. */
export async function confirmarCodigo(codigo: string): Promise<{ sessao?: Sessao; recusado?: boolean; encerrada?: boolean;
  tentativasRestantes?: number }> {
  let r: Response;
  try {
    r = await fetch("/api/login/2fa", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codigo }) });
  } catch {
    return { recusado: true };
  }
  const d = (await r.json().catch(() => ({}))) as RespostaLogin;
  if (r.ok && d.sessao) {
    guardar({ csrf: d.csrf ?? "", cabecalho: d.cabecalho ?? cabecalho });
    return { sessao: d.sessao };
  }
  const acabou = d.pre_sessao === null || (d.pre_sessao === undefined && /pré-sessão/.test(d.erro ?? ""));
  return acabou ? { encerrada: true } : { recusado: true, tentativasRestantes: d.pre_sessao?.tentativas_restantes };
}

/** POST JSON com o token CSRF da sessão; 401 encerra a sessão na interface. */
export async function postar(rota: string, corpo: unknown): Promise<Response> {
  const r = await fetch(rota, { method: "POST", headers: { "Content-Type": "application/json", [cabecalho]: csrf },
    body: JSON.stringify(corpo) });
  if (r.status === 401) sessaoEncerrada();
  else if (r.status === 403) acessoNegado(((await r.clone().json().catch(() => ({}))) as { erro?: string }).erro);
  return r;
}

/** GET JSON de uma rota protegida; devolve o erro do servidor em texto quando não passa. */
export async function ler<T>(rota: string): Promise<{ dados?: T; erro?: string; status: number }> {
  try {
    const r = await fetch(rota);
    if (r.status === 401) { sessaoEncerrada(); return { erro: "sessão encerrada", status: 401 }; }
    const d = await r.json().catch(() => ({}));
    if (r.status === 403) acessoNegado((d as { erro?: string }).erro);
    return r.ok ? { dados: d as T, status: r.status } : { erro: (d as { erro?: string }).erro ?? `erro ${r.status}`, status: r.status };
  } catch (e) {
    return { erro: String(e), status: 0 };
  }
}

export async function sair(): Promise<void> {
  await postar("/api/logout", {}).catch(() => undefined);
  csrf = "";
}

export async function trocarSenha(atual: string, nova: string): Promise<string | null> {
  const r = await postar("/api/senha", { atual, nova });
  if (r.ok) return null;
  return ((await r.json().catch(() => ({}))) as { erro?: string }).erro ?? `erro ${r.status}`;
}

export const pode = (s: Sessao | null | undefined, permissao: string): boolean => !!s && s.permissoes.includes(permissao);

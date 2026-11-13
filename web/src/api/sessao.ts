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
}

export interface Saude {
  ok: boolean;
  versao: string;
  acesso: { sem_contas: boolean; integro: boolean; cabecalho: string };
}

let csrf = "";
let cabecalho = "X-SMA-Token";
const ouvintes = new Set<() => void>();

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

export async function entrar(usuario: string, senha: string): Promise<{ sessao?: Sessao; erro?: string }> {
  const r = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ usuario, senha }) });
  const d = (await r.json().catch(() => ({}))) as { sessao?: Sessao; csrf?: string; cabecalho?: string; erro?: string };
  if (!r.ok || !d.sessao) return { erro: d.erro ?? `erro ${r.status}` };
  guardar({ csrf: d.csrf ?? "", cabecalho: d.cabecalho ?? cabecalho });
  return { sessao: d.sessao };
}

/** POST JSON com o token CSRF da sessão; 401 encerra a sessão na interface. */
export async function postar(rota: string, corpo: unknown): Promise<Response> {
  const r = await fetch(rota, { method: "POST", headers: { "Content-Type": "application/json", [cabecalho]: csrf },
    body: JSON.stringify(corpo) });
  if (r.status === 401) sessaoEncerrada();
  return r;
}

/** GET JSON de uma rota protegida; devolve o erro do servidor em texto quando não passa. */
export async function ler<T>(rota: string): Promise<{ dados?: T; erro?: string; status: number }> {
  try {
    const r = await fetch(rota);
    if (r.status === 401) { sessaoEncerrada(); return { erro: "sessão encerrada", status: 401 }; }
    const d = await r.json().catch(() => ({}));
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

// Apoio dos testes de interface: contas de demonstração, comandos pela API e a linha de comando de acesso.
import { expect, request as playwrightRequest, type APIRequestContext, type Browser, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { join } from "node:path";

export const SENHA = "Demonstracao-SMA-2026";
export const SEM_SESSAO = { cookies: [], origins: [] };

/** Envia um comando como a conta do contexto (cookie da sessão + token CSRF dela). */
export async function comando(request: APIRequestContext, data: Record<string, unknown>, esperado = 202) {
  const { csrf } = await (await request.get("/api/sessao")).json();
  const r = await request.post("/api/comando", { data, headers: { "X-SMA-Token": csrf } });
  expect(r.status()).toBe(esperado);
  return r;
}

export async function estado(request: APIRequestContext) {
  return (await request.get("/api/estado")).json();
}

const contas: Record<string, APIRequestContext> = {};

/** Sessão de uma conta de demonstração pela API (o `operador` reinicia; o `admin` limpa a memória). */
async function contaApi(usuario: string): Promise<APIRequestContext> {
  if (!contas[usuario]) {
    contas[usuario] = await playwrightRequest.newContext({ baseURL: `http://127.0.0.1:${process.env.SMA_E2E_PORTA ?? 8777}` });
    const r = await contas[usuario].post("/api/login", { data: { usuario, senha: SENHA } });
    expect(r.ok()).toBeTruthy();
  }
  return contas[usuario];
}

/** Apaga o histórico do SVC-MEM, como o administrador (PERM-MEM-LIMPAR). Reiniciar não apaga a memória: sem isto,
 * o waiver de um roteiro faria a POL-06 recusar o waiver de outro mês num roteiro seguinte. */
export async function limparMemoria() {
  await comando(await contaApi("admin"), { tipo: "limpar_memoria" });
}

/** Reinicia o cenário como `operador`. Quem reinicia dispara os pedidos do roteiro e, pela POL-13, não decide
 * sobre eles; quem decide nos roteiros é o `controller` (o `avaliador` do contexto padrão opera, pede e audita, mas
 * não aprova desde a DSM4). Trocar a cognição exige PERM-MOD-CONFIG, que é da operação: o contexto padrão ajusta a
 * cognição e o operador reinicia. */
export async function reiniciar(request: APIRequestContext, cenario: string, pausado = false, extras: Record<string, unknown> = {},
  manterMemoria = false) {
  if (!manterMemoria) await limparMemoria();  // cada roteiro começa sem histórico de outro roteiro
  await comando(request, { tipo: pausado ? "pausar" : "retomar" });
  const cognicao = (extras.cognicao as string | undefined) ?? "basico";
  if ((await estado(request)).controle.cognicao !== cognicao) {
    await comando(request, { tipo: "reiniciar", cenario, ...extras, cognicao });
    await expect.poll(async () => (await estado(request)).controle.cognicao).toBe(cognicao);
  }
  const geracao = (await estado(request)).controle.geracao;
  await comando(await contaApi("operador"), { tipo: "reiniciar", cenario, ...extras, cognicao });
  await expect.poll(async () => (await estado(request)).controle.geracao).toBeGreaterThan(geracao);
  await expect.poll(async () => (await estado(request)).controle.cenario).toBe(cenario);
}

export async function abrir(page: Page) {
  await page.addInitScript(() => localStorage.setItem("sma-ajuda-vista", "1"));
  await page.goto("/");
  await expect(page.getByText("● ao vivo")).toBeVisible();
}

/** Entra pela tela de login, como a pessoa faria. */
export async function entrar(page: Page, usuario: string, senha = SENHA) {
  await page.addInitScript(() => localStorage.setItem("sma-ajuda-vista", "1"));
  await page.goto("/");
  await tentarEntrar(page, usuario, senha);
}

/** Preenche o formulário de login já aberto e espera a resposta do servidor (aceita ou recusada). */
export async function tentarEntrar(page: Page, usuario: string, senha = SENHA) {
  const formulario = page.getByRole("form", { name: "Entrar no escritório" });
  await formulario.getByLabel("Usuário").fill(usuario);
  await formulario.getByLabel("Senha").fill(senha);
  const resposta = page.waitForResponse((r) => r.url().endsWith("/api/login"));
  await formulario.getByRole("button", { name: "Entrar" }).click();
  await resposta;
}

/** Página nova de outra pessoa (contexto próprio do navegador, sem a sessão padrão). */
export async function paginaDe(browser: Browser, usuario: string) {
  const contexto = await browser.newContext({ storageState: SEM_SESSAO });
  const page = await contexto.newPage();
  await entrar(page, usuario);
  await expect(page.getByText("● ao vivo")).toBeVisible();
  return { page, contexto };
}

/** `python -m fin_mas acesso ...` no cadastro do servidor em teste (o que o administrador faria no terminal). */
export function cliAcesso(args: string[], env: Record<string, string> = {},
  cadastro = { acesso: process.env.SMA_E2E_ACESSO!, chaves: process.env.SMA_E2E_CHAVES! }): string {
  const raiz = process.env.SMA_E2E_RAIZ!;
  return execFileSync(process.env.SMA_E2E_PYTHON!, ["-m", "fin_mas", "acesso", "--acesso", cadastro.acesso, ...args], {
    cwd: raiz, encoding: "utf-8",
    env: { ...process.env, PYTHONPATH: join(raiz, "src"), PYTHONUTF8: "1", FIN_MAS_DIR_CHAVES: cadastro.chaves,
      FIN_MAS_SENHA: SENHA, ...env },
  });
}

/** A mesma linha de comando, no cadastro do segundo servidor (o de `avancado.spec.ts`). */
export function cliAvancado(args: string[], env: Record<string, string> = {}): string {
  return cliAcesso(args, env, { acesso: process.env.SMA_E2E_ACESSO_AVANCADO!, chaves: process.env.SMA_E2E_CHAVES_AVANCADO! });
}

export function chipAgente(page: Page, id: string) {
  return page.getByRole("navigation", { name: "Agentes" }).getByRole("button", { name: new RegExp(`^${id} ·`) });
}

export function pedido(page: Page, sid: string) {  // o chip inteiro do pedido (código, intenção, competência e status)
  return page.getByRole("region", { name: "Pedidos da liderança" }).locator(".MuiChip-root").filter({ hasText: sid });
}

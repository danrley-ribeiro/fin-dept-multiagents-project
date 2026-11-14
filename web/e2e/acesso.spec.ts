// Controle de acesso no dashboard (ADR-009): cada pessoa entra com a sua conta e só faz o que os papéis dela permitem.
// Navegador de verdade, servidor de verdade, contas de demonstração num cadastro selado em pasta temporária.
import { expect, request as novaApi, test, type APIRequestContext } from "@playwright/test";
import { SESSAO_PADRAO } from "../playwright.config";
import { cliAcesso, comando, entrar, paginaDe, reiniciar, SEM_SESSAO, SENHA, tentarEntrar } from "./apoio";

test.use({ storageState: SEM_SESSAO }); // estes testes começam sem ninguém logado

let avaliador: APIRequestContext; // prepara os cenários pela API, como faria quem opera
test.beforeAll(async ({ baseURL }) => { avaliador = await novaApi.newContext({ baseURL, storageState: SESSAO_PADRAO }); });
test.afterAll(async () => { await avaliador.dispose(); });

const formulario = (page: import("@playwright/test").Page) => page.getByRole("form", { name: "Entrar no escritório" });

test("sem sessão o escritório pede login e a API não entrega nada", async ({ page, request }) => {
  await page.goto("/");
  await expect(formulario(page)).toBeVisible();
  await expect(page.getByText("● ao vivo")).toBeHidden();
  for (const rota of ["/api/estado", "/api/cenarios", "/api/auditoria", "/api/llm", "/api/sessao"]) {
    expect((await request.get(rota)).status(), rota).toBe(401);
  }
  expect((await request.post("/api/comando", { data: { tipo: "pausar" } })).status()).toBe(401);
  expect((await request.get("/api/saude")).status()).toBe(200);
});

test("senha errada mostra erro genérico e cinco erros bloqueiam a conta", async ({ page }) => {
  await entrar(page, "bruno", "senha-errada-12345");
  await expect(page.getByRole("alert")).toHaveText("usuário ou senha inválidos");
  await tentarEntrar(page, "ninguem", "senha-errada-12345"); // usuário inexistente: mesma resposta
  await expect(page.getByRole("alert")).toHaveText("usuário ou senha inválidos");
  for (let i = 0; i < 4; i++) await tentarEntrar(page, "bruno", "senha-errada-12345");
  await expect(page.getByRole("alert")).toContainText("bloqueada");
  await tentarEntrar(page, "bruno", SENHA); // senha certa, mas a conta está bloqueada
  await expect(page.getByRole("alert")).toContainText("bloqueada");
  await expect(page.getByText("● ao vivo")).toBeHidden();
});

test("operador opera a simulação, mas não pede nem decide", async ({ browser }) => {
  await reiniciar(avaliador, "veto_waiver");
  const { page, contexto } = await paginaDe(browser, "operador");
  await expect(page.getByLabel("Conta em uso")).toContainText("operador");
  await expect(page.getByRole("button", { name: "Pausar" })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Novo pedido" })).toBeDisabled();
  await expect(page.getByRole("tab", { name: "Logs" })).toBeVisible();
  const sino = page.getByRole("button", { name: "Decisões humanas pendentes" });
  await expect(sino).toBeEnabled({ timeout: 20_000 });
  await sino.click();
  const dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-001/ });
  await expect(dialogo).toContainText("Sua conta não tem o papel de aprovador");
  await expect(dialogo.getByRole("button", { name: "Corrigir no ERP" })).toHaveCount(0); // sem botões de decisão
  // mesmo forçando pela API, o servidor nega e diz por quê
  const r = await contexto.request.post("/api/comando", {
    data: { tipo: "decidir", solicitacao: "SOL-001", decisao: "bloquear" },
    headers: { "X-SMA-Token": (await (await contexto.request.get("/api/sessao")).json()).csrf } });
  expect(r.status()).toBe(403);
  expect((await r.json()).erro).toContain("PERM-APR-DECIDIR");
  await contexto.close();
});

test("auditor só lê: consulta e exporta os logs, não opera nem configura", async ({ browser }) => {
  const { page, contexto } = await paginaDe(browser, "auditor");
  await expect(page.getByRole("button", { name: /Pausar|Retomar/ })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Reiniciar cenário" })).toBeDisabled();
  await page.getByRole("tab", { name: "Logs" }).click();
  const logs = page.getByRole("region", { name: "Logs e auditoria" });
  await expect(logs.getByRole("table", { name: "Registros do trace" }).getByRole("row").nth(1)).toBeVisible();
  await expect(logs.getByRole("link", { name: "Exportar" })).toBeVisible();
  const exportado = await contexto.request.get("/api/auditoria/exportar?tipo=decision");
  expect(exportado.status()).toBe(200);
  expect((await exportado.text()).split("\n")[0]).toContain('"kind": "decision"');
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  await expect(page.getByRole("checkbox", { name: "Ligar LLM de AG-ORC" })).toBeDisabled();
  await expect(page.getByText("Só o aprovador (controller) ajusta modelos e cotas")).toBeVisible();
  await contexto.close();
});

test("a decisão é da pessoa: a gerente envolvida é impedida e outro gerente decide", async ({ browser }) => {
  await reiniciar(avaliador, "decisao_por_pessoa");
  await expect.poll(async () => (await (await avaliador.get("/api/aprovacoes")).json()).aprovacoes.length, { timeout: 20_000 }).toBe(1);
  const carla = await paginaDe(browser, "carla");
  await carla.page.getByRole("tab", { name: "Aprovações" }).click();
  const ticketCarla = carla.page.getByRole("region", { name: "Central de aprovações" }).getByLabel("Ticket APR-001");
  await expect(ticketCarla).toContainText("POL-03: você participou de um lançamento vetado");
  await expect(ticketCarla.getByRole("button", { name: "Decidir" })).toBeDisabled();
  await carla.contexto.close();

  const diego = await paginaDe(browser, "diego");
  await diego.page.getByRole("tab", { name: "Aprovações" }).click();
  const central = diego.page.getByRole("region", { name: "Central de aprovações" });
  await expect(central.getByLabel("Ticket APR-001")).toContainText("prazo:");
  await central.getByLabel("Ticket APR-001").getByRole("button", { name: "Decidir" }).click();
  const dialogo = diego.page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-001/ });
  await expect(dialogo).toContainText("Você decide como Diego Rocha (gerente)");
  await dialogo.getByRole("button", { name: "Corrigir no ERP" }).click();
  const historico = central.getByRole("table", { name: "Histórico de aprovações" });
  await expect(historico.getByRole("row").filter({ hasText: "APR-001" })).toContainText("diego (gerente)", { timeout: 20_000 });
  await diego.page.getByRole("tab", { name: "Solicitações" }).click();
  await expect(diego.page.getByRole("table", { name: "Solicitações" }).getByRole("row").filter({ hasText: "SOL-001" }))
    .toContainText("publicado", { timeout: 20_000 });
  await diego.contexto.close();
});

test("sessão revogada pelo administrador no terminal devolve o dashboard ao login", async ({ browser }) => {
  const { page, contexto } = await paginaDe(browser, "controller");
  const sessoes = JSON.parse(cliAcesso(["--json", "--como", "admin", "sessao", "listar"])) as { id: string; usuario: string; viva: boolean }[];
  const vivas = sessoes.filter((s) => s.usuario === "controller" && s.viva);
  expect(vivas.length).toBeGreaterThan(0);
  for (const s of vivas) cliAcesso(["--como", "admin", "sessao", "revogar", s.id]);
  await expect(formulario(page)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Sua sessão foi encerrada")).toBeVisible();
  expect((await contexto.request.get("/api/estado")).status()).toBe(401);
  await contexto.close();
});

test("senha temporária precisa ser trocada na primeira entrada", async ({ page }) => {
  cliAcesso(["--como", "admin", "usuario", "redefinir-senha", "ana"], { FIN_MAS_SENHA_NOVA: "Temporaria-2026-xyz" });
  await entrar(page, "ana");
  await expect(page.getByRole("alert")).toHaveText("usuário ou senha inválidos"); // a senha antiga deixou de valer
  await tentarEntrar(page, "ana", "Temporaria-2026-xyz");
  const troca = page.getByRole("form", { name: "Trocar senha" });
  await expect(troca).toContainText("A sua senha é temporária");
  const atual = troca.locator('input[autocomplete="current-password"]');
  const novas = troca.locator('input[autocomplete="new-password"]'); // senha nova e a repetição
  await atual.fill("Temporaria-2026-xyz");
  await novas.nth(0).fill("curta");
  await novas.nth(1).fill("curta");
  await troca.getByRole("button", { name: "Salvar senha" }).click();
  await expect(troca.getByRole("alert").filter({ hasText: "IAM-02" })).toBeVisible(); // senha fraca recusada
  await novas.nth(0).fill("Definitiva-2026-abc");
  await novas.nth(1).fill("Definitiva-2026-abc");
  await troca.getByRole("button", { name: "Salvar senha" }).click();
  await expect(page.getByText("● ao vivo")).toBeVisible();
  await expect(page.getByLabel("Conta em uso")).toContainText("ana");
});

test("sair encerra a sessão no servidor", async ({ browser }) => {
  const { page, contexto } = await paginaDe(browser, "elisa");
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(formulario(page)).toBeVisible();
  expect((await contexto.request.get("/api/estado")).status()).toBe(401);
  await page.reload();
  await expect(formulario(page)).toBeVisible();
  await contexto.close();
});

test("o que a pessoa pede fica no nome dela", async ({ browser }) => {
  await reiniciar(avaliador, "fechar_mes");
  const { page, contexto } = await paginaDe(browser, "elisa");
  await comando(contexto.request, { tipo: "solicitar", intencao: "avaliar_orcamento", competencia: "2026-09" });
  await page.getByRole("tab", { name: "Solicitações" }).click();
  await expect(page.getByRole("table", { name: "Solicitações" }).getByRole("row").filter({ hasText: "SOL-002" }))
    .toContainText("elisa");
  await contexto.close();
});

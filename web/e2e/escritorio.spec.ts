// Uso real do escritório da SMA: navegador de verdade, servidor Python de verdade, agentes executando ao vivo.
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

async function comando(request: APIRequestContext, data: Record<string, unknown>) {
  const { token } = await (await request.get("/api/sessao")).json();
  const r = await request.post("/api/comando", { data, headers: { "X-SMA-Token": token } });
  expect(r.status()).toBe(202);
}

async function reiniciar(request: APIRequestContext, cenario: string, pausado = false) {
  await comando(request, { tipo: pausado ? "pausar" : "retomar" });
  await comando(request, { tipo: "reiniciar", cenario });
  await expect.poll(async () => (await (await request.get("/api/estado")).json()).controle.cenario).toBe(cenario);
}

async function abrir(page: Page) {
  await page.addInitScript(() => localStorage.setItem("sma-ajuda-vista", "1"));
  await page.goto("/");
  await expect(page.getByText("● ao vivo")).toBeVisible();
}

function chipAgente(page: Page, id: string) {
  return page.getByRole("navigation", { name: "Agentes" }).getByRole("button", { name: new RegExp(`^${id} ·`) });
}

function pedido(page: Page, sid: string) {  // o chip inteiro do pedido (código, intenção, competência e status)
  return page.getByRole("region", { name: "Pedidos da liderança" }).locator(".MuiChip-root").filter({ hasText: sid });
}

test("primeira visita mostra o guia e o escritório com códigos e departamentos", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await page.goto("/");
  const guia = page.getByRole("dialog", { name: "Como usar o escritório da SMA" });
  await expect(guia).toBeVisible();
  await guia.getByRole("button", { name: "Entendi" }).click();
  await expect(guia).toBeHidden();
  await expect(page.getByRole("heading", { name: /SMA · Escritório de controladoria/ })).toBeVisible();
  for (const [id, depto] of [["AG-ORC", "Orçamento"], ["AG-CIN", "Controles Internos"], ["AG-CUS", "Custos"]]) {
    await expect(chipAgente(page, id)).toContainText(depto);
    await expect(page.getByRole("button", { name: new RegExp(`^${id} · ${depto}`) }).first()).toBeVisible();
  }
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  // recarregar não mostra o guia de novo (preferência lembrada)
  await page.reload();
  await expect(page.getByText("● ao vivo")).toBeVisible();
  await expect(page.getByRole("dialog", { name: "Como usar o escritório da SMA" })).toBeHidden();
});

test("operador pausa, avança evento a evento e retoma", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes", true);
  await abrir(page);
  await expect(page.getByRole("button", { name: "Retomar" })).toBeVisible();
  const t0 = (await (await request.get("/api/estado")).json()).controle.fila;
  await page.getByRole("button", { name: "Avançar um evento" }).click();
  await expect.poll(async () => (await (await request.get("/api/estado")).json()).controle.fila).not.toBe(t0);
  await page.getByRole("button", { name: "Retomar" }).click();
  await expect(page.getByRole("button", { name: "Pausar" })).toBeVisible();
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
});

test("veto vira notificação; o humano corrige no ERP e o AG-CIN reconsidera", async ({ page, request }) => {
  await reiniciar(request, "veto_waiver");
  await abrir(page);
  const sino = page.getByRole("button", { name: "Decisões humanas pendentes" });
  await expect(sino).toBeEnabled({ timeout: 20_000 });
  await expect(sino).toContainText("1");
  await expect(chipAgente(page, "APR").locator("xpath=..")).toContainText("1"); // badge no aprovador
  await sino.click();
  const dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-001/ });
  await expect(dialogo).toContainText("alcada");
  await expect(dialogo).toContainText("reaprovar por quem tem alçada");
  await expect(dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" })).toBeDisabled(); // exige justificativa
  await dialogo.getByRole("button", { name: "Corrigir no ERP" }).click();
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  await expect(sino).toBeDisabled();
  await chipAgente(page, "AG-CIN").click();
  const mente = page.getByRole("region", { name: "Mente de AG-CIN" });
  await mente.getByRole("tab", { name: /Deliberações/ }).click();
  await expect(mente.getByRole("table", { name: "Opções para parecer:CMP-001" }).first()).toContainText("▶ P-APROVAR");
  await expect(mente.getByRole("table", { name: "Opções para parecer:CMP-001" }).last()).toContainText("▶ P-VETAR-COM-CORRECAO");
  await mente.getByRole("tab", { name: /Intenções/ }).click();
  await expect(mente).toContainText("substituída após reavaliação das crenças");
});

test("waiver exige justificativa e libera com ressalva", async ({ page, request }) => {
  await reiniciar(request, "veto_waiver");
  await abrir(page);
  const sino = page.getByRole("button", { name: "Decisões humanas pendentes" });
  await expect(sino).toBeEnabled({ timeout: 20_000 });
  await sino.click();
  const dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN/ });
  const waiver = dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" });
  await dialogo.getByLabel("Justificativa").fill("aaaaaaaaaa"); // 10 caracteres, uma palavra: a POL-04 recusaria
  await expect(waiver).toBeDisabled();
  await dialogo.getByLabel("Justificativa").fill("risco aceito pela diretoria; ajuste no próximo ciclo");
  await dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" }).click();
  await expect(pedido(page, "SOL-001")).toContainText("publicado c/ ressalva", { timeout: 20_000 });
});

test("reincidência: a política nega o waiver e o diálogo não o oferece", async ({ page, request }) => {
  await reiniciar(request, "reincidencia_waiver");
  await abrir(page);
  const sino = page.getByRole("button", { name: "Decisões humanas pendentes" });
  await expect(sino).toBeEnabled({ timeout: 20_000 });
  await sino.click();
  let dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-001/ });
  await dialogo.getByLabel("Justificativa").fill("risco aceito pela diretoria nesta competência");
  await dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" }).click();
  await expect(sino).toBeEnabled({ timeout: 20_000 });
  await sino.click();
  dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-002/ });
  await expect(dialogo).toContainText("reincidente");
  await dialogo.getByLabel("Justificativa").fill("risco aceito pela diretoria de novo");
  await expect(dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" })).toBeDisabled();
  await expect(dialogo).toContainText("Waiver não admitido pela política");
  await dialogo.getByRole("button", { name: "Corrigir no ERP" }).click();
  await expect(pedido(page, "SOL-002")).toContainText("publicado", { timeout: 20_000 });
});

test("desligar o AG-CIN gera perdas, timeout, replanejamento do AG-ORC e falha explícita", async ({ page, request }) => {
  await reiniciar(request, "desvio_irregular", true);
  await abrir(page);
  await chipAgente(page, "AG-CIN").click();
  await page.getByRole("button", { name: "Desligar agente (simular falha)" }).click();
  await expect(chipAgente(page, "AG-CIN")).toContainText("fora");
  await page.getByRole("button", { name: "Retomar" }).click();
  await expect(pedido(page, "SOL-001")).toContainText("falhou", { timeout: 30_000 });
  await expect(page.getByRole("region", { name: "Trilha causal" })).toContainText("agente fora de operação");
  await chipAgente(page, "AG-ORC").click();
  const mente = page.getByRole("region", { name: "Mente de AG-ORC" });
  await expect(mente).toContainText("P-SEM-EXPLICACAO");
  await mente.getByRole("tab", { name: /Deliberações/ }).click();
  await expect(mente).toContainText("já tentado sem sucesso");
  await chipAgente(page, "AG-CIN").click();
  await page.getByRole("button", { name: "Religar agente" }).click();
  await expect(chipAgente(page, "AG-CIN")).not.toContainText("fora");
});

test("badges mostram novidades não vistas e somem ao abrir o agente", async ({ page, request }) => {
  await reiniciar(request, "desvio_irregular", true);
  await abrir(page);
  await chipAgente(page, "AG-CUS").click(); // olhando outro agente enquanto o AG-ORC trabalha
  await page.getByRole("button", { name: "Retomar" }).click();
  const badgeOrc = chipAgente(page, "AG-ORC").locator("xpath=..").locator(".MuiBadge-badge");
  await expect(badgeOrc).toHaveText(/^[1-9]\d*\+?$/, { timeout: 20_000 });
  await chipAgente(page, "AG-ORC").click();
  await expect(badgeOrc).toHaveClass(/MuiBadge-invisible/);
});

test("novo pedido pelo diálogo entra na fila e é atendido", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  await page.getByRole("button", { name: "Novo pedido" }).click();
  const dialogo = page.getByRole("dialog", { name: "Novo pedido da liderança" });
  await dialogo.getByLabel("Intenção").click();
  await page.getByRole("option", { name: "Avaliar orçamento" }).click();
  await dialogo.getByRole("button", { name: "Enviar pedido" }).click();
  await expect(pedido(page, "SOL-002")).toBeVisible();
  await expect(pedido(page, "SOL-002")).toContainText(/publicado/, { timeout: 20_000 });
});

test("replay offline e comparação com o workflow centralizado", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await page.getByRole("button", { name: "Ver replay" }).click();
  await expect(page.getByText("replay offline")).toBeVisible();
  await page.getByLabel("Cenário").click();
  await page.getByRole("option", { name: "desvio_irregular" }).click();
  await page.getByRole("button", { name: "Pausar" }).click();
  const tempo = page.getByRole("slider", { name: "Tempo lógico" });
  await tempo.focus();
  await page.keyboard.press("End");
  await expect(pedido(page, "SOL-001")).toContainText("publicado c/ ressalva");
  await page.getByRole("tab", { name: "SMA × workflow" }).click();
  const comparacao = page.getByRole("region", { name: "Comparação com o baseline" });
  await expect(comparacao.getByRole("img", { name: "Desvios classificados como no gabarito" })).toBeVisible();
  await comparacao.getByLabel("Ver como tabela").check();
  await expect(comparacao.getByRole("row", { name: /desvio_irregular/ })).toContainText("0%");
});

test("tema escuro alterna e é lembrado", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  const html = page.locator("html");
  const inicial = await html.getAttribute("data-theme");
  await page.getByRole("button", { name: "Alternar tema" }).click();
  await expect(html).not.toHaveAttribute("data-theme", inicial ?? "");
  const escolhido = await html.getAttribute("data-theme");
  await page.reload();
  await expect(html).toHaveAttribute("data-theme", escolhido ?? "");
});

test("Períodos e fontes de dados são clicáveis e mostram o que aconteceu", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  await page.getByRole("button", { name: /^Períodos em fechamento/ }).click();
  const periodos = page.getByRole("dialog", { name: "Períodos em fechamento (reserva PROT-LCK)" });
  await expect(periodos.getByRole("table", { name: "Histórico de reservas" })).toContainText("reserve-accept");
  await expect(periodos.getByRole("table", { name: "Histórico de reservas" })).toContainText("release");
  await periodos.getByRole("button", { name: "Fechar" }).click();
  await page.getByRole("button", { name: /^Normas: \d+ chamada/ }).click();
  const normas = page.getByRole("dialog", { name: /Fonte de dados: Normas/ });
  await expect(normas.getByRole("table", { name: "Chamadas à fonte Normas" })).toContainText("normas.perfil");
  await normas.getByRole("button", { name: "Fechar" }).click();
});

test("trocar o porte para micro muda regras, fonte (sem ERP) e chip da empresa", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await page.getByRole("button", { name: "Dados da empresa" }).click();
  const dialogo = page.getByRole("dialog", { name: "Dados da empresa" });
  await dialogo.getByRole("radio", { name: /Microempresa/ }).check();
  await dialogo.getByRole("button", { name: "Reiniciar com este porte" }).click();
  await expect(page.getByText(/Microempresa \(ME\) · sem ERP/)).toBeVisible();
  await expect(page.getByRole("button", { name: /^ERP \(não há\)/ })).toBeVisible();
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  await chipAgente(page, "AG-CIN").click();
  const mente = page.getByRole("region", { name: "Mente de AG-CIN" });
  await mente.getByRole("tab", { name: /Crenças/ }).click();
  await expect(mente.getByRole("row", { name: /^porte micro mcp:\/\/normas\/perfil/ })).toBeVisible();
  await comando(request, { tipo: "reiniciar", cenario: "fechar_mes", porte: "media" });
});

test("empresa sem ERP: baixa o modelo, envia a planilha e o escritório roda sobre ela", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes", true);
  await abrir(page);
  await page.getByRole("button", { name: "Dados da empresa" }).click();
  const dialogo = page.getByRole("dialog", { name: "Dados da empresa" });
  await dialogo.getByRole("tab", { name: "Minha empresa sem ERP (planilha)" }).click();
  const download = page.waitForEvent("download");
  await dialogo.getByRole("listitem").filter({ hasText: "exemplo_pequena.xlsx" }).getByRole("link", { name: "Baixar" }).click();
  const baixado = await download;
  const caminho = await baixado.path();
  expect(baixado.suggestedFilename()).toBe("exemplo_pequena.xlsx");
  await dialogo.getByLabel("Arquivo da planilha").setInputFiles({ name: "minha_empresa.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: (await import("node:fs")).readFileSync(caminho!) });
  await expect(dialogo.getByText(/Planilha válida: minha_empresa\.xlsx/)).toBeVisible();
  await dialogo.getByRole("button", { name: "Executar com a minha planilha" }).click();
  await expect(page.getByText(/planilha real/)).toBeVisible();
  await page.getByRole("button", { name: "Retomar" }).click();
  await expect(pedido(page, "SOL-002")).toContainText(/publicado|bloqueado/, { timeout: 30_000 });
  await page.getByRole("button", { name: /^Excel da empresa: \d+ chamada/ }).click();
  await expect(page.getByRole("dialog", { name: /Fonte de dados: Planilhas/ })).toContainText("mcp://excel/minha_empresa.xlsx");
});

test("planilha inválida é recusada com a lista de erros", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await page.getByRole("button", { name: "Dados da empresa" }).click();
  const dialogo = page.getByRole("dialog", { name: "Dados da empresa" });
  await dialogo.getByRole("tab", { name: "Minha empresa sem ERP (planilha)" }).click();
  const resposta = await request.get("/api/modelos/modelo_controladoria_em_branco.xlsx");
  await dialogo.getByLabel("Arquivo da planilha").setInputFiles({ name: "vazia.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", buffer: await resposta.body() });
  await expect(dialogo.getByRole("alert").filter({ hasText: "nada foi substituído" })).toContainText("Produtos: nenhuma linha preenchida");
});

test("liga e desliga pelo chip do agente e faz novo pedido pelo painel do Solicitante", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes", true);
  await abrir(page);
  await page.getByRole("button", { name: "Desligar AG-REL" }).click();
  await expect(chipAgente(page, "AG-REL")).toContainText("fora");
  await page.getByRole("button", { name: "Religar AG-REL" }).click();
  await expect(chipAgente(page, "AG-REL")).not.toContainText("fora");
  await expect(page.getByRole("button", { name: "Desligar AG-ORQ" })).toHaveCount(0);  // fronteira com o usuário
  await chipAgente(page, "SOL").click();
  await page.getByRole("button", { name: "Novo pedido da liderança" }).click();
  await page.getByRole("dialog", { name: "Novo pedido da liderança" }).getByRole("button", { name: "Enviar pedido" }).click();
  await page.getByRole("button", { name: "Retomar" }).click();
  await expect(pedido(page, "SOL-002")).toBeVisible();
});

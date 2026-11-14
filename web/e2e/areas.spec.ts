// Áreas de trabalho do escritório: solicitações e relatórios, aprovações, logs com explicação, porte, cognição e LLM.
// Roda com a conta `avaliador` (opera, solicita, aprova e audita), já logada pela preparação dos testes.
import { expect, test } from "@playwright/test";
import { abrir, chipAgente, comando, reiniciar } from "./apoio";

test("solicitações: pedir, acompanhar e abrir o relatório para baixar", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await page.getByRole("tab", { name: "Solicitações" }).click();
  const area = page.getByRole("region", { name: "Solicitações e relatórios" });
  await area.getByRole("button", { name: "Nova solicitação" }).click();
  const dialogo = page.getByRole("dialog", { name: "Novo pedido da liderança" });
  await dialogo.getByRole("combobox", { name: "Intenção" }).click();
  await page.getByRole("option", { name: "Avaliar orçamento" }).click();
  await dialogo.getByRole("button", { name: "Enviar pedido" }).click();
  const linha = area.getByRole("table", { name: "Solicitações" }).getByRole("row").filter({ hasText: "SOL-002" });
  await expect(linha).toContainText("avaliar orcamento");
  await expect(linha).toContainText("avaliador");
  await expect(linha).toContainText("publicado", { timeout: 20_000 });
  await linha.getByRole("button", { name: "Ver relatório" }).click();
  const relatorio = page.getByRole("dialog", { name: "Relatório de SOL-002" });
  await expect(relatorio.getByLabel("Texto do relatório")).toContainText("Relatório orçamentário");
  await expect(relatorio.getByRole("link", { name: "Baixar HTML" })).toHaveAttribute("href", "/api/relatorios/SOL-002?formato=html");
  const baixado = await request.get("/api/relatorios/SOL-002?formato=html");
  expect(baixado.headers()["content-disposition"]).toContain("attachment");
  expect(await baixado.text()).toContain("<svg");
});

test("aprovações: fila com prazo, decisão com justificativa e histórico com a pessoa", async ({ page, request }) => {
  await reiniciar(request, "veto_waiver");
  await abrir(page);
  await page.getByRole("tab", { name: "Aprovações" }).click();
  const central = page.getByRole("region", { name: "Central de aprovações" });
  const ticket = central.getByLabel("Ticket APR-001");
  await expect(ticket).toContainText("prazo:", { timeout: 20_000 });
  await expect(ticket).toContainText("alcada");
  await ticket.getByRole("button", { name: "Decidir" }).click();
  const dialogo = page.getByRole("dialog", { name: /Veto do AG-CIN · SOL-001/ });
  await expect(dialogo).toContainText("Você decide como");
  await dialogo.getByRole("textbox", { name: "Justificativa" }).fill("aceito o risco: será corrigido no próximo fechamento");
  await dialogo.getByRole("button", { name: "Waiver (aceitar o risco)" }).click();
  const linha = central.getByRole("table", { name: "Histórico de aprovações" }).getByRole("row").filter({ hasText: "APR-001" });
  await expect(linha).toContainText("waiver", { timeout: 20_000 });
  await expect(linha).toContainText("avaliador (controller)");
  await expect(linha).toContainText("aceito o risco");
  await expect(central).toContainText("Nenhum veto aguardando decisão.");
});

test("logs: filtros por agente e tipo, busca, por quê e sequência da conversa", async ({ page, request }) => {
  await reiniciar(request, "desvio_irregular");
  await expect.poll(async () => (await (await request.get("/api/aprovacoes")).json()).aprovacoes.length, { timeout: 20_000 }).toBe(1);
  await abrir(page);
  await page.getByRole("tab", { name: "Logs" }).click();
  const logs = page.getByRole("region", { name: "Logs e auditoria" });
  const linhas = logs.getByRole("table", { name: "Registros do trace" }).locator("tbody tr");
  await expect(linhas.first()).toBeVisible();
  const total = async () => Number((await logs.getByLabel("Total de registros").innerText()).split(" ")[0]);
  const todos = await total();
  await logs.getByRole("combobox", { name: "Agente" }).click();
  await page.getByRole("option", { name: "AG-ORC" }).click();
  await logs.getByRole("combobox", { name: "Tipo" }).click();
  await page.getByRole("option", { name: "belief" }).click();
  await logs.getByRole("button", { name: "Filtrar" }).click();
  await expect.poll(total).toBeLessThan(todos);
  const crencas = await total();
  expect(crencas).toBeGreaterThan(5);
  await expect(linhas).toHaveCount(crencas);
  expect(new Set(await linhas.locator("td:nth-child(3)").allInnerTexts())).toEqual(new Set(["belief"]));
  await logs.getByLabel("Buscar texto").fill("contestado");
  await logs.getByRole("button", { name: "Filtrar" }).click();
  await expect.poll(total).toBeLessThan(crencas);
  await expect(linhas.first()).toContainText("contestado");
  // por quê: a cadeia que levou a uma decisão do AG-ORC
  await logs.getByLabel("Buscar texto").fill("");
  await logs.getByRole("combobox", { name: "Tipo" }).click();
  await page.getByRole("option", { name: "decision" }).click();
  await logs.getByRole("button", { name: "Filtrar" }).click();
  await expect(linhas.first()).toContainText("DECISAO AG-ORC");
  await linhas.last().getByRole("button", { name: /Explicar o registro/ }).click();
  const porque = page.getByRole("dialog", { name: /Por quê\? Registro/ });
  const cadeia = porque.getByRole("table", { name: "Cadeia da decisão" });
  for (const papel of ["percepção (tool)", "crença", "deliberação", "intenção", "decisão"]) {
    await expect(cadeia.getByText(papel, { exact: true }).first()).toBeVisible();
  }
  await porque.getByRole("button", { name: "Fechar" }).click();
  // sequência: a conversa de consulta do AG-ORC ao AG-CIN
  await linhas.first().getByRole("button", { name: /^(DEL|QRY)-/ }).click();
  const sequencia = page.getByRole("dialog", { name: /Sequência de mensagens/ });
  await expect(sequencia.getByLabel("Diagrama de sequência").getByRole("listitem").first()).toContainText("→");
  await expect(sequencia).toContainText("python -m fin_mas sequencia");
});

test("porte: ficha com as regras de cada porte e o porte em uso", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes");
  await abrir(page);
  await page.getByRole("tab", { name: "Porte" }).click();
  const tabela = page.getByRole("region", { name: "Porte da empresa" }).getByRole("table", { name: "Regras por porte" });
  await expect(tabela).toContainText("Microempresa (ME)");
  await expect(tabela).toContainText("ITG 1000");
  await expect(tabela.getByRole("columnheader").filter({ hasText: /^Média empresa(?! II)/ })).toContainText("em uso");
  await expect(tabela.getByRole("row").filter({ hasText: /^Controle compensatório/ })).toContainText("revisão mensal dos lançamentos pelo sócio");
  await comando(request, { tipo: "reiniciar", cenario: "fechar_mes", porte: "micro" });
  await page.reload();
  await page.getByRole("tab", { name: "Porte" }).click();
  await expect(tabela.getByRole("columnheader").filter({ hasText: "Microempresa (ME)" })).toContainText("em uso");
  await comando(request, { tipo: "reiniciar", cenario: "fechar_mes", porte: "media" });
});

test("cognição local pelo dashboard: a hipótese aparece na mente do agente e é confirmada", async ({ page, request }) => {
  await reiniciar(request, "orc_sem_cin", true);
  await abrir(page);
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  await page.getByRole("combobox", { name: "Nível de cognição" }).click();
  await page.getByRole("option", { name: /^Local \(regras locais/ }).click();
  await expect.poll(async () => (await (await request.get("/api/estado")).json()).controle.cognicao).toBe("local");
  await page.getByRole("tab", { name: "Escritório" }).click();
  await page.getByRole("button", { name: "Retomar" }).click();
  await chipAgente(page, "AG-ORC").click();
  const mente = page.getByRole("region", { name: "Mente de AG-ORC" });
  await mente.getByRole("tab", { name: /Hipóteses/ }).click({ timeout: 20_000 });
  const hipotese = mente.getByLabel("Hipótese AG-ORC-H001");
  await expect(hipotese).toContainText("confirmada", { timeout: 20_000 });
  await expect(hipotese).toContainText("regra local (R-OBS-REPETICAO)");
  await expect(hipotese).toContainText("evidência: AG-CIN (QRY-002)");
  await mente.getByRole("tab", { name: /Crenças/ }).click();
  await mente.getByLabel("Filtrar crenças").fill("contestado");
  await expect(mente.getByRole("row").filter({ hasText: "contestado[" }).first()).toContainText("comunicação");
});

test("LLM opcional pelo dashboard: ligar o mock no AG-ORC, corroborar a hipótese e ver o custo", async ({ page, request }) => {
  await reiniciar(request, "orc_sem_cin", true, { cognicao: "llm" });
  await abrir(page);
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  const cartao = page.getByLabel("LLM de AG-ORC");
  await cartao.getByRole("checkbox", { name: "Ligar LLM de AG-ORC" }).check();
  await cartao.getByRole("combobox", { name: "Modelo" }).click();
  await page.getByRole("option", { name: "mock-analista", exact: true }).click();
  await cartao.getByRole("button", { name: "hipoteses" }).click();
  await cartao.getByRole("button", { name: "Aplicar" }).click();
  await expect.poll(async () => (await (await request.get("/api/llm")).json()).agentes["AG-ORC"].llm).toBe(true);
  await page.getByRole("button", { name: "Reiniciar cenário" }).click(); // a configuração sobrevive ao reinício
  await page.getByRole("tab", { name: "Escritório" }).click();
  await page.getByRole("button", { name: "Retomar" }).click();
  await chipAgente(page, "AG-ORC").click();
  const mente = page.getByRole("region", { name: "Mente de AG-ORC" });
  await mente.getByRole("tab", { name: /Hipóteses/ }).click({ timeout: 20_000 });
  const hipotese = mente.getByLabel("Hipótese AG-ORC-H001");
  await expect(hipotese).toContainText("confirmada", { timeout: 20_000 });
  await expect(hipotese).toContainText("IA (mock/mock-analista@prompt-hipoteses-v1)");
  await expect(hipotese).toContainText("regra local (R-OBS-REPETICAO)");
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  await expect(page.getByLabel("Uso de LLM de AG-ORC")).toContainText("1 chamada(s)");
  // AG-CIN nunca aparece para configuração: a NORM-07 não permite LLM nele
  await expect(page.getByLabel("LLM de AG-CIN")).toHaveCount(0);
  await comando(request, { tipo: "modelo", agente: "AG-ORC", llm: false, modelo: "mock-narrador" });
});

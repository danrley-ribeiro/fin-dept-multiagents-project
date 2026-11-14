// Aba Fontes de dados ponta a ponta (ADR-011): o ERP de demonstração sobe em loopback (processo próprio), a pessoa
// cadastra o conector com o token, testa, entende a fonte (sugestões com motivo), ajusta uma linha, confirma, ativa
// e o fechamento roda sobre o ERP. O token nunca aparece na página nem na API. Depois, planilhas: modelo e envio.
import { expect, test } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { abrir, comando, estado, paginaDe, reiniciar } from "./apoio";

const PORTA_ERP = Number(process.env.SMA_E2E_ERP_PORTA ?? 8791);
const TOKEN = "tok-e2e-NUNCA-NA-TELA-0123456789";
let erp: ChildProcess | undefined;

test.beforeAll(async () => {
  const raiz = process.env.SMA_E2E_RAIZ!;
  erp = spawn(process.env.SMA_E2E_PYTHON!, ["-m", "fin_mas", "erp-demo", "--porta", String(PORTA_ERP), "--token", TOKEN,
    "--plantar", "alcada"], { cwd: raiz, env: { ...process.env, PYTHONPATH: join(raiz, "src"), PYTHONUTF8: "1" },
    stdio: "ignore" });
  await expect.poll(async () => fetch(`http://127.0.0.1:${PORTA_ERP}/health`).then((r) => r.status).catch(() => 0),
    { timeout: 20_000 }).toBe(200);
});

test.afterAll(async () => { erp?.kill(); });

test("fontes: cadastrar o ERP, testar, entender, ajustar, confirmar, ativar e fechar o mês sobre ele", async ({ page, request }) => {
  await reiniciar(request, "fechar_mes", true);
  await abrir(page);
  await page.getByRole("tab", { name: "Fontes de dados" }).click();
  const area = page.getByRole("region", { name: "Fontes de dados" });
  const form = area.getByRole("form", { name: "Cadastrar conector" });
  await form.getByLabel("Identificador").fill("erp-demo");
  await form.getByLabel("Nome").fill("ERP de demonstração");
  await form.getByLabel("URL base").fill(`http://127.0.0.1:${PORTA_ERP}`);
  await form.getByLabel("Credencial (token)").fill(TOKEN);
  await form.getByRole("button", { name: "Cadastrar" }).click();
  await expect(area.getByLabel("Aviso das fontes")).toContainText("credencial no cofre");
  const linha = area.getByRole("row", { name: "Conector erp-demo" });
  await expect(linha).toContainText("há credencial");
  await expect(linha).toContainText("loopback");
  await linha.getByRole("button", { name: "Testar" }).click();
  await expect(area.getByRole("region", { name: "Diagnóstico da conexão" })).toContainText("em ordem");
  await expect(area.getByRole("region", { name: "Diagnóstico da conexão" })).toContainText("[ok] recurso journal-entries");
  await linha.getByRole("button", { name: "Entender" }).click();
  const tela = area.getByRole("region", { name: "Entendimento da fonte" });
  const valor = tela.getByRole("row", { name: "Mapeamento Lancamentos.valor" });
  await expect(valor).toContainText("amount");
  await expect(valor).toContainText("sinônimo de 'valor' (en)");
  await expect(tela.getByRole("row", { name: "Mapeamento Lancamentos.competencia" })).toContainText("data_competencia");
  await expect(tela).toContainText("Qualidade: sem erros");
  await expect(tela.getByLabel("Prévia da fonte")).toContainText("realizado_acumulado");
  // ajuste manual: a observação do orçamento não será usada
  await tela.getByRole("combobox", { name: "Origem de Orcamento.observacao" }).click();
  await page.getByRole("option", { name: "—" }).click();
  await expect(tela.getByRole("row", { name: "Mapeamento Orcamento.observacao" })).toContainText("ajustado pela pessoa");
  await tela.getByRole("button", { name: "Confirmar mapeamento" }).click();
  await expect(area.getByLabel("Aviso das fontes")).toContainText("confirmado por avaliador");
  await expect(linha).toContainText("confirmado por avaliador");
  await linha.getByRole("button", { name: "Ativar" }).click();
  await expect(area.getByLabel("Aviso das fontes")).toContainText("a simulação reiniciou");
  await expect.poll(async () => (await estado(request)).controle.fonte).toBe("conector");
  await expect(area.getByLabel("Fonte em uso")).toContainText("erp-demo");
  // o token nunca aparece: nem na página nem na API
  expect(await page.content()).not.toContain(TOKEN);
  expect(await (await request.get("/api/fontes")).text()).not.toContain(TOKEN);
  // o fechamento sobre o ERP chega ao veto da alçada; a decisão corrige e o relatório é publicado
  await comando(request, { tipo: "retomar" });
  await expect.poll(async () => (await (await request.get("/api/aprovacoes")).json()).aprovacoes.length, { timeout: 30_000 }).toBe(1);
  await comando(request, { tipo: "decidir", solicitacao: "SOL-001", decisao: "corrigir", justificativa: "reaprovar com alçada" });
  await expect.poll(async () => (await estado(request)).solicitacoes["SOL-001"]?.performative, { timeout: 30_000 }).toBe("inform");
  await linha.page().reload();
  await page.getByRole("tab", { name: "Fontes de dados" }).click();
  await area.getByRole("row", { name: "Conector erp-simulado" }).getByRole("button", { name: "Ativar" }).click();
  await expect.poll(async () => (await estado(request)).controle.fonte).toBe("sintetico");
});

test("fontes: modelos para baixar, envio de planilha e histórico; host externo só pelo administrador", async ({ page, request, browser }) => {
  await abrir(page);
  await page.getByRole("tab", { name: "Fontes de dados" }).click();
  const area = page.getByRole("region", { name: "Fontes de dados" });
  const planilhas = area.getByRole("region", { name: "Planilhas" });
  await expect(planilhas.getByRole("link", { name: "modelo_controladoria_em_branco.xlsx" })).toHaveAttribute("href",
    "/api/modelos/modelo_controladoria_em_branco.xlsx");
  const modelo = await request.get("/api/modelos/exemplo_micro.xlsx");
  const pasta = mkdtempSync(join(tmpdir(), "sma-fontes-"));
  const arquivo = join(pasta, "exemplo_micro.xlsx");
  writeFileSync(arquivo, await modelo.body());
  await planilhas.getByLabel("Arquivo da planilha para a fonte").setInputFiles(arquivo);
  await expect(area.getByLabel("Aviso das fontes")).toContainText("competência 2026-09 na pasta de planilhas");
  await expect(planilhas.getByRole("table", { name: "Histórico de envios" })).toContainText("exemplo_micro.xlsx");
  await expect(area.getByRole("row", { name: "Conector planilhas" })).toBeVisible();
  // o avaliador (operador) não vê a área de rede; o administrador libera um host externo
  await expect(area.getByRole("region", { name: "Rede dos conectores" })).toHaveCount(0);
  const { page: adm, contexto } = await paginaDe(browser, "admin");
  await adm.getByRole("tab", { name: "Fontes de dados" }).click();
  const rede = adm.getByRole("region", { name: "Rede dos conectores" });
  await rede.getByLabel("Host externo").fill("erp.exemplo.com.br");
  await rede.getByRole("button", { name: "Liberar host" }).click();
  await expect(rede).toContainText("erp.exemplo.com.br (por admin)");
  await contexto.close();
});

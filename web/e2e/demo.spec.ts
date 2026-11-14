// Demonstração guiada: opcional, desligada por padrão. O roteiro (web/src/demo/roteiro.ts) dispara os mesmos comandos
// da barra de controles, com as permissões de quem está logado, e o escritório funciona igual com ela fechada.
import { expect, test } from "@playwright/test";
import { abrir, chipAgente, estado, paginaDe, pedido, reiniciar } from "./apoio";

test("demonstração guiada: abre por opção, dispara os comandos de cada passo e fecha sem mudar o escritório", async ({ page, request }) => {
  await reiniciar(request, "expediente_sma", true);
  await abrir(page);
  const guia = page.getByRole("complementary", { name: "Demonstração guiada" });
  const botao = page.getByRole("button", { name: "Demonstração guiada" });
  await expect(guia).toHaveCount(0); // desligada por padrão: nada do roteiro na tela
  await expect(botao).toHaveAttribute("aria-pressed", "false");
  expect((await estado(request)).controle.cenario).toBe("expediente_sma"); // abrir a página não dispara nada

  await botao.click();
  await expect(guia.getByLabel("Passo atual")).toHaveText("Passo 1 de 6");
  await expect(guia.getByRole("heading", { level: 3 })).toHaveText("1. Fechamento normal");
  expect((await estado(request)).controle.cenario).toBe("expediente_sma"); // abrir o roteiro também não
  await guia.getByRole("button", { name: "Rodar o fechamento" }).click();
  await expect.poll(async () => (await estado(request)).controle.cenario).toBe("fechar_mes");
  await expect(guia.getByLabel("Situação do passo")).toContainText("cenário fechar_mes");
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });

  await guia.getByRole("button", { name: "Próximo" }).click();
  await expect(guia.getByRole("heading", { level: 3 })).toHaveText("2. Veto e decisão humana");
  await expect(guia.getByLabel("Situação do passo")).toHaveCount(0); // só avançar não executa nada
  expect((await estado(request)).controle.cenario).toBe("fechar_mes");
  await guia.getByRole("button", { name: "Rodar o cenário do veto" }).click();
  await expect.poll(async () => (await estado(request)).controle.cenario).toBe("veto_waiver");
  await expect(page.getByRole("button", { name: "Decisões humanas pendentes" })).toBeEnabled({ timeout: 20_000 });
  await expect(page.getByRole("region", { name: "Mente de AG-CIN" })).toBeVisible(); // o passo seleciona o agente

  await guia.getByRole("button", { name: "Próximo" }).click();
  await guia.getByRole("button", { name: "Desligar o AG-CUS e fechar o mês" }).click();
  await expect(chipAgente(page, "AG-CUS")).toContainText("fora");
  await expect(pedido(page, "SOL-001")).toContainText("falhou", { timeout: 30_000 });
  const registros = (await (await request.get("/api/auditoria?tipo=timeout")).json()).registros;
  expect(registros.length).toBe(2); // o prazo estourou, houve um reenvio e o prazo estourou de novo

  await guia.getByRole("button", { name: "Próximo" }).click();
  await guia.getByRole("button", { name: "Rodar o cenário de ataque" }).click();
  const logs = page.getByRole("region", { name: "Logs e auditoria" }); // o passo abre os logs já filtrados
  await expect(logs.getByRole("combobox", { name: "Tipo" })).toHaveText("rejected");
  await expect(logs.getByLabel("Total de registros")).toHaveText(/^1[0-9] registro\(s\)/, { timeout: 20_000 });
  await expect(logs.getByRole("table", { name: "Registros do trace" }).getByRole("row").nth(1)).toContainText("rejected");
  expect((await estado(request)).controle.offline).toEqual([]); // o reinício religou o AG-CUS

  await guia.getByRole("button", { name: "Próximo" }).click();
  await guia.getByRole("button", { name: "Próximo" }).click();
  await expect(guia.getByLabel("Passo atual")).toHaveText("Passo 6 de 6");
  await expect(guia.getByRole("button", { name: "Próximo" })).toBeDisabled();
  await expect(guia.getByRole("link", { name: /Documentação do projeto/ })).toHaveAttribute("target", "_blank");
  await guia.getByRole("button", { name: "Abrir SMA × workflow" }).click();
  await expect(page.getByRole("region", { name: "Comparação com o baseline" })).toBeVisible();
  expect((await estado(request)).controle.cenario).toBe("ataque_decisao_forjada"); // este passo só navega

  // fecha a qualquer momento; o escritório continua onde estava e os controles de sempre funcionam
  await guia.getByRole("button", { name: "Fechar a demonstração guiada" }).click();
  await expect(guia).toHaveCount(0);
  await expect(botao).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("region", { name: "Comparação com o baseline" })).toBeVisible();
  await page.getByRole("tab", { name: "Logs" }).click(); // sem o roteiro, os logs voltam sem filtro
  await expect(page.getByRole("region", { name: "Logs e auditoria" }).getByRole("combobox", { name: "Tipo" })).not.toHaveText("rejected");
  await page.getByRole("tab", { name: "Escritório" }).click();
  await page.getByRole("combobox", { name: "Cenário" }).click();
  await page.getByRole("option", { name: "fechar_mes", exact: true }).click();
  await expect.poll(async () => (await estado(request)).controle.cenario).toBe("fechar_mes");
  await expect(pedido(page, "SOL-001")).toContainText("publicado", { timeout: 20_000 });
  await page.getByRole("button", { name: "Pausar" }).click();
  await expect.poll(async () => (await estado(request)).controle.pausado).toBe(true);
  await page.reload(); // e continua desligada depois de recarregar
  await expect(page.getByText("● ao vivo")).toBeVisible();
  await expect(guia).toHaveCount(0);
  await reiniciar(request, "fechar_mes");
});

test("demonstração guiada respeita as permissões: o auditor lê o roteiro, mas não dispara comandos", async ({ browser, request }) => {
  await reiniciar(request, "fechar_mes", true);
  const { page, contexto } = await paginaDe(browser, "auditor");
  await page.getByRole("button", { name: "Demonstração guiada" }).click();
  const guia = page.getByRole("complementary", { name: "Demonstração guiada" });
  await expect(guia.getByRole("button", { name: "Rodar o fechamento" })).toBeDisabled();
  await expect(guia.getByLabel("Por que o passo está indisponível")).toContainText("Sua conta não tem o papel de operador (PERM-SIM-OPERAR)");
  await guia.getByRole("button", { name: "Próximo" }).click();
  await guia.getByRole("button", { name: "Próximo" }).click();
  await expect(guia.getByLabel("Por que o passo está indisponível")).toContainText("PERM-SIM-OPERAR, PERM-AGT-ENERGIA");
  for (let i = 0; i < 3; i++) await guia.getByRole("button", { name: "Próximo" }).click();
  await guia.getByRole("button", { name: "Abrir SMA × workflow" }).click(); // o que não é comando continua disponível
  await expect(page.getByRole("region", { name: "Comparação com o baseline" })).toBeVisible();
  const { controle } = await estado(request);
  expect(controle.cenario).toBe("fechar_mes");
  expect(controle.pausado).toBe(true);
  // mesmo forçando pela API, o servidor nega o comando do passo
  const r = await contexto.request.post("/api/comando", { data: { tipo: "reiniciar", cenario: "veto_waiver" },
    headers: { "X-SMA-Token": (await (await contexto.request.get("/api/sessao")).json()).csrf } });
  expect(r.status()).toBe(403);
  await contexto.close();
  await reiniciar(request, "fechar_mes");
});

// Acesso avançado no dashboard (ADR-012), no que a própria pessoa usa pela web: entrada em dois passos, o seu segundo
// fator, a política que o exige, a chave de LLM no cofre e a empresa ativa. Navegador de verdade contra um SEGUNDO
// servidor, com cadastro próprio (ver playwright.config.ts): o que estes roteiros ligam vale para todas as contas.
// O código TOTP é calculado aqui mesmo (RFC 6238: HMAC-SHA1, passo de 30 s, 6 dígitos), a partir do segredo que a
// tela mostra na ativação, como faria o aplicativo autenticador.
import { expect, test, type Page } from "@playwright/test";
import { createHmac } from "node:crypto";
import { cliAvancado, comando, entrar, SENHA, tentarEntrar } from "./apoio";

// ---- TOTP (RFC 4226 + RFC 6238) ----
function base32(texto: string): Buffer {
  const alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of texto.replace(/[\s=]/g, "").toUpperCase()) {
    const v = alfabeto.indexOf(c);
    if (v < 0) throw new Error(`segredo fora do base32: ${c}`);
    bits += v.toString(2).padStart(5, "0");
  }
  const bytes = bits.match(/.{8}/g) ?? [];
  return Buffer.from(bytes.map((b) => parseInt(b, 2)));
}

function totp(segredo: string, passo: number): string {
  const contador = Buffer.alloc(8);
  contador.writeBigUInt64BE(BigInt(passo));
  const mac = createHmac("sha1", base32(segredo)).update(contador).digest();
  const deslocamento = mac[mac.length - 1] & 0x0f;
  return String((mac.readUInt32BE(deslocamento) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

const pausa = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** O "aplicativo" da pessoa. O servidor aceita o passo atual ±1 e nunca um passo já usado (anti-replay): cada pedido
 *  devolve o menor passo ainda aceito e, perto da virada do passo, espera a virada para não chegar atrasado. */
class Autenticador {
  private ultimo = -1;
  private segredo: string;
  constructor(segredo: string) { this.segredo = segredo; }
  async codigo(): Promise<string> {
    for (;;) {
      const agora = Date.now() / 1000;
      const atual = Math.floor(agora / 30);
      if (30 - (agora % 30) < 4) { await pausa(4200); continue; }
      const passo = Math.max(atual - 1, this.ultimo + 1);
      if (passo > atual + 1) { await pausa(((passo - 1) * 30 - agora) * 1000 + 300); continue; }
      this.ultimo = passo;
      return totp(this.segredo, passo);
    }
  }
}

// ---- gestos comuns ----
const login = (page: Page) => page.getByRole("form", { name: "Entrar no escritório" });
const passo2 = (page: Page) => page.getByRole("form", { name: "Confirmar o segundo fator" });
const aoVivo = (page: Page) => page.getByText("● ao vivo");

async function sair(page: Page) {
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(login(page)).toBeVisible();
}

/** Usuário e senha; com o segundo fator ativo, a tela para no pedido do código. */
async function ateOCodigo(page: Page, usuario: string) {
  await tentarEntrar(page, usuario);
  await expect(passo2(page)).toBeVisible();
  await expect(passo2(page).getByLabel("Código de verificação")).toBeFocused();
}

async function informar(page: Page, codigo: string) {
  const resposta = page.waitForResponse((r) => r.url().endsWith("/api/login/2fa"));
  await passo2(page).getByLabel("Código de verificação").fill(codigo);
  await page.keyboard.press("Enter"); // o formulário envia com Enter
  await resposta;
}

/** Na tela (ou no diálogo) "Meu segundo fator": ativa, confirma com o primeiro código e devolve segredo e códigos. */
async function ativar(page: Page, painel = page.getByRole("region", { name: "Meu segundo fator" })) {
  await painel.getByRole("button", { name: "Ativar o segundo fator" }).click();
  const segredo = (await painel.getByLabel("Segredo do segundo fator").innerText()).trim();
  expect(segredo).toMatch(/^[A-Z2-7]{32}$/);
  await expect(painel.getByLabel("Endereço otpauth")).toHaveValue(new RegExp(`^otpauth://totp/.*secret=${segredo}&`));
  const app = new Autenticador(segredo);
  await painel.getByLabel("Primeiro código do aplicativo").fill(await app.codigo());
  await painel.getByRole("button", { name: "Confirmar e ativar" }).click();
  const lista = painel.getByRole("list", { name: "Códigos de recuperação" });
  await expect(lista.getByRole("listitem")).toHaveCount(10);
  const codigos = (await lista.getByRole("listitem").allInnerTexts()).map((c) => c.trim());
  for (const c of codigos) expect(c).toMatch(/^[0-9a-f]{8}-[0-9a-f]{8}$/);
  return { app, segredo, codigos };
}

test("o cálculo do TOTP deste roteiro confere com os vetores da RFC 6238", () => {
  const rfc = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"; // "12345678901234567890" em base32
  expect(totp(rfc, Math.floor(59 / 30))).toBe("287082");
  expect(totp(rfc, Math.floor(1111111109 / 30))).toBe("081804");
  expect(totp(rfc, Math.floor(1234567890 / 30))).toBe("005924");
});

test.describe.serial("segundo fator da própria pessoa", () => {
  test.describe.configure({ timeout: 150_000 }); // um código TOTP não se repete: às vezes é preciso esperar o passo seguinte
  let app: Autenticador;
  let segredo = "";
  let codigos: string[] = [];

  test("segundo fator: ativar mostra o segredo e os códigos uma vez e a entrada passa a ter dois passos", async ({ page }) => {
    await entrar(page, "carla");
    await expect(aoVivo(page)).toBeVisible();
    await page.getByRole("button", { name: "Meu segundo fator" }).click();
    const dialogo = page.getByRole("dialog", { name: /Meu segundo fator · carla/ });
    await expect(dialogo.getByLabel("Situação do segundo fator")).toHaveText("não ativado");
    await dialogo.getByRole("button", { name: "Ativar o segundo fator" }).click();
    await dialogo.getByLabel("Primeiro código do aplicativo").fill("000000"); // código errado não ativa
    await dialogo.getByRole("button", { name: "Confirmar e ativar" }).click();
    await expect(dialogo.getByRole("alert").filter({ hasText: "IAM-08" })).toContainText("código não confere");
    await dialogo.getByRole("button", { name: "Cancelar" }).click();
    ({ app, segredo, codigos } = await ativar(page, dialogo));
    await expect(dialogo.getByRole("button", { name: "Fechar" })).toBeDisabled(); // os códigos ainda estão na tela
    await dialogo.getByRole("button", { name: "Já guardei os códigos" }).click();
    await expect(dialogo.getByLabel("Situação do segundo fator")).toHaveText("ativo");
    await expect(dialogo.getByLabel("Códigos de recuperação restantes")).toHaveText("Restam 10 códigos de recuperação.");
    const html = await page.content(); // o que só aparece uma vez não fica na página
    expect(html).not.toContain(segredo);
    expect(html).not.toContain(codigos[0]);
    await dialogo.getByRole("button", { name: "Fechar" }).click();
    await sair(page);

    // a senha certa já não basta: abre só o pedido do código, e nada do escritório
    await ateOCodigo(page, "carla");
    await expect(aoVivo(page)).toBeHidden();
    expect((await page.request.get("/api/estado")).status()).toBe(401);
    expect((await page.request.get("/api/sessao")).status()).toBe(401);
    await informar(page, "000000");
    await expect(passo2(page).getByRole("alert")).toHaveText("Código inválido. Restam 4 tentativas.");
    await expect(passo2(page).getByLabel("Código de verificação")).toBeFocused();
    await informar(page, await app.codigo());
    await expect(aoVivo(page)).toBeVisible();
    await expect(page.getByLabel("Conta em uso")).toContainText("carla");
  });

  test("segundo fator: código de recuperação entra uma vez só e cinco códigos errados devolvem ao início", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("sma-ajuda-vista", "1"));
    await page.goto("/");
    await ateOCodigo(page, "carla");
    await informar(page, codigos[0]);
    await expect(aoVivo(page)).toBeVisible();
    await sair(page);
    await ateOCodigo(page, "carla");
    await informar(page, codigos[0]); // o mesmo código de recuperação não vale de novo; o motivo não vai para a tela
    await expect(passo2(page).getByRole("alert")).toHaveText("Código inválido. Restam 4 tentativas.");
    for (const restam of ["Restam 3 tentativas", "Restam 2 tentativas", "Resta 1 tentativa"]) {
      await informar(page, "000000");
      await expect(passo2(page).getByRole("alert")).toHaveText(`Código inválido. ${restam}.`);
    }
    await informar(page, "000000"); // a quinta derruba a pré-sessão no servidor: volta ao usuário e senha
    await expect(login(page)).toBeVisible();
    await expect(login(page)).toContainText("as tentativas para informar o código acabaram");
    await expect(login(page).getByLabel("Usuário")).toBeFocused();
    // o contador é da conta: outra senha certa não renova as tentativas, o segundo fator fica bloqueado (IAM-08)
    await tentarEntrar(page, "carla");
    await expect(login(page)).toContainText("segundo fator bloqueado por códigos errados");
    await expect(passo2(page)).toBeHidden();
    cliAvancado(["--como", "admin", "usuario", "desbloquear", "carla"]); // só o administrador (ou o prazo) desbloqueia
    await tentarEntrar(page, "carla");
    await informar(page, codigos[1]);
    await expect(aoVivo(page)).toBeVisible();
  });

  test("segundo fator: novos códigos de recuperação e desativação pela própria pessoa", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("sma-ajuda-vista", "1"));
    await page.goto("/");
    await ateOCodigo(page, "carla");
    await passo2(page).getByRole("button", { name: "Voltar" }).click(); // dá para desistir e recomeçar
    await expect(login(page)).toBeVisible();
    await ateOCodigo(page, "carla");
    await informar(page, await app.codigo());
    await expect(aoVivo(page)).toBeVisible();
    await page.getByRole("button", { name: "Meu segundo fator" }).click();
    const dialogo = page.getByRole("dialog", { name: /Meu segundo fator · carla/ });
    await expect(dialogo.getByLabel("Códigos de recuperação restantes")).toHaveText("Restam 8 códigos de recuperação.");
    await dialogo.getByRole("button", { name: "Gerar novos códigos de recuperação" }).click();
    await dialogo.getByLabel("Senha atual").fill(SENHA);
    await dialogo.getByLabel("Código atual").fill(codigos[0]); // já usado: não confirma nada
    await dialogo.getByRole("button", { name: "Gerar novos códigos" }).click();
    await expect(dialogo.getByRole("alert").filter({ hasText: "IAM-08" })).toBeVisible();
    await dialogo.getByLabel("Senha atual").fill("Senha-Errada-2026"); // código certo com a senha errada não serve
    await dialogo.getByLabel("Código atual").fill(await app.codigo());
    await dialogo.getByRole("button", { name: "Gerar novos códigos" }).click();
    await expect(dialogo.getByRole("alert").filter({ hasText: "senha atual não confere" })).toBeVisible();
    await dialogo.getByLabel("Senha atual").fill(SENHA);
    await dialogo.getByLabel("Código atual").fill(await app.codigo());
    await dialogo.getByRole("button", { name: "Gerar novos códigos" }).click();
    const lista = dialogo.getByRole("list", { name: "Códigos de recuperação" });
    await expect(lista.getByRole("listitem")).toHaveCount(10);
    const novos = (await lista.getByRole("listitem").allInnerTexts()).map((c) => c.trim());
    expect(novos.filter((c) => codigos.includes(c))).toEqual([]);
    await dialogo.getByRole("button", { name: "Já guardei os códigos" }).click();
    await expect(dialogo.getByLabel("Códigos de recuperação restantes")).toHaveText("Restam 10 códigos de recuperação.");
    // desativar pede confirmação com um código; um código antigo já não serve
    await dialogo.getByRole("button", { name: "Desativar" }).click();
    await dialogo.getByLabel("Senha atual").fill(SENHA);
    await dialogo.getByLabel("Código atual").fill(codigos[2]);
    await dialogo.getByRole("button", { name: "Desativar o segundo fator" }).click();
    await expect(dialogo.getByRole("alert").filter({ hasText: "IAM-08" })).toBeVisible();
    await dialogo.getByLabel("Senha atual").fill(SENHA);
    await dialogo.getByLabel("Código atual").fill(novos[0]);
    await dialogo.getByRole("button", { name: "Desativar o segundo fator" }).click();
    await expect(dialogo.getByLabel("Situação do segundo fator")).toHaveText("não ativado");
    await dialogo.getByRole("button", { name: "Fechar" }).click();
    await sair(page);
    await tentarEntrar(page, "carla"); // de volta a um passo só
    await expect(aoVivo(page)).toBeVisible();
  });
});

test("política que exige o segundo fator leva a conta sem ele à ativação e só depois libera o escritório", async ({ page, browser }) => {
  test.setTimeout(120_000);
  // elisa já estava dentro quando a política mudou; diego entra depois
  const contextoElisa = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const elisa = await contextoElisa.newPage();
  await entrar(elisa, "elisa");
  await expect(aoVivo(elisa)).toBeVisible();
  cliAvancado(["--como", "admin", "politica", "definir", "--exigir-2fa", "ROLE-APR"]);
  try {
    await entrar(page, "diego");
    const tela = page.getByRole("main", { name: "Ativar o segundo fator" });
    await expect(tela).toContainText("A política do cadastro exige o segundo fator para a conta diego");
    await expect(tela.getByText("exigido pela política do cadastro")).toBeVisible();
    await expect(aoVivo(page)).toBeHidden();
    await expect(page.getByRole("tab", { name: "Escritório" })).toHaveCount(0);
    const negado = await page.request.get("/api/estado"); // o servidor nega tudo, menos ativar
    expect(negado.status()).toBe(403);
    expect((await negado.json()).erro).toContain("IAM-08");
    await page.reload(); // recarregar não escapa da tela
    await expect(tela).toBeVisible();
    await ativar(page, tela.getByRole("region", { name: "Meu segundo fator" }));
    await expect(aoVivo(page)).toBeHidden(); // os códigos de recuperação ainda estão na tela
    await tela.getByRole("button", { name: "Já guardei os códigos" }).click();
    await expect(aoVivo(page)).toBeVisible();
    await expect(page.getByLabel("Conta em uso")).toContainText("diego");
    expect((await page.request.get("/api/estado")).status()).toBe(200);
    // quem já estava dentro é levada à mesma tela assim que o servidor passa a negar
    await expect(elisa.getByRole("main", { name: "Ativar o segundo fator" })).toBeVisible({ timeout: 20_000 });
    // operador não tem papel exigido pela política: entra direto
    const contextoOperador = await browser.newContext({ storageState: { cookies: [], origins: [] } });
    const operador = await contextoOperador.newPage();
    await entrar(operador, "operador");
    await expect(aoVivo(operador)).toBeVisible();
    await contextoOperador.close();
  } finally {
    cliAvancado(["--como", "admin", "politica", "definir", "--exigir-2fa", "nenhum"]);
    await contextoElisa.close();
  }
  await page.reload(); // sem a política, diego segue com o segundo fator que ativou
  await expect(aoVivo(page)).toBeVisible();
});

test("chave de LLM no cofre: definir, ver que há chave e remover, sem o valor aparecer em lugar nenhum", async ({ page, browser }) => {
  const VALOR = "sk-e2e-NUNCA-NA-TELA-0123456789abcdef";
  const respostas: { url: string; corpo: string }[] = [];
  const console_: string[] = [];
  page.on("response", (r) => {  // o corpo de toda resposta da API que chegou inteira (o fluxo de eventos não termina)
    if (r.url().includes("/api/")) r.text().then((corpo) => respostas.push({ url: r.url(), corpo })).catch(() => undefined);
  });
  page.on("console", (m) => console_.push(m.text()));
  await entrar(page, "admin");
  await expect(aoVivo(page)).toBeVisible();
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  const chaves = page.getByRole("region", { name: "Chaves dos provedores de LLM" });
  // o administrador de acesso define segredos, mas não consulta nem ajusta a configuração dos agentes
  await expect(page.getByRole("combobox", { name: "Nível de cognição" })).toHaveCount(0);
  const cartao = chaves.getByRole("group", { name: "Chave de openai", exact: true }); // um cartão por provedor
  const situacao = cartao.getByLabel("Situação da chave de openai", { exact: true });
  await expect(situacao).toHaveText("não há chave");
  await expect(chaves.getByLabel("Situação da chave de openai-compat")).toContainText("opcional");
  await expect(cartao.getByRole("button", { name: "Guardar no cofre" })).toBeDisabled();
  await expect(cartao.getByRole("button", { name: "Remover do cofre" })).toBeDisabled();
  const campo = cartao.getByLabel("Chave nova de openai", { exact: true });
  await expect(campo).toHaveAttribute("type", "password");
  await campo.fill(VALOR);
  await cartao.getByRole("button", { name: "Guardar no cofre" }).click();
  await expect(chaves.getByLabel("Aviso das chaves")).toContainText("Chave de openai guardada no cofre");
  await expect(situacao).toHaveText("há chave no cofre");
  await expect(campo).toHaveValue(""); // o campo é esvaziado no envio
  await expect(cartao).toContainText("no cofre por admin");

  // quem consulta os modelos vê que a chave existe (pela mesma API de antes), mas não vê a área das chaves
  const contextoAvaliador = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const avaliador = await contextoAvaliador.newPage();
  await entrar(avaliador, "avaliador");
  await avaliador.getByRole("tab", { name: "Agentes e LLM" }).click();
  await expect(avaliador.getByRole("combobox", { name: "Nível de cognição" })).toBeVisible();
  await expect(avaliador.getByRole("region", { name: "Chaves dos provedores de LLM" })).toHaveCount(0);
  const llm = await avaliador.request.get("/api/llm");
  expect((await llm.json()).provedores.find((p: { id: string }) => p.id === "openai").tem_chave).toBe(true);
  expect(await llm.text()).not.toContain(VALOR);
  expect((await avaliador.request.get("/api/segredos")).status()).toBe(403);
  const { csrf } = await (await avaliador.request.get("/api/sessao")).json();
  expect((await avaliador.request.post("/api/segredos", { data: { nome: "llm:OPENAI_API_KEY", valor: "x" },
    headers: { "X-SMA-Token": csrf } })).status()).toBe(403);
  expect(await avaliador.content()).not.toContain(VALOR);
  await contextoAvaliador.close();

  // o valor não voltou em nenhuma resposta, não está no HTML e não foi para o console
  await page.reload();
  await page.getByRole("tab", { name: "Agentes e LLM" }).click();
  await expect(situacao).toHaveText("há chave no cofre");
  expect(await page.content()).not.toContain(VALOR);
  expect(await (await page.request.get("/api/segredos")).text()).not.toContain(VALOR);
  expect(await (await page.request.get("/api/acesso/trilha")).text()).not.toContain(VALOR);
  expect(respostas.filter((r) => r.url.endsWith("/api/segredos")).length).toBeGreaterThanOrEqual(3); // lista, definição, lista
  for (const r of respostas) expect(r.corpo, r.url).not.toContain(VALOR);
  expect(console_.join("\n")).not.toContain(VALOR);

  await cartao.getByRole("button", { name: "Remover do cofre" }).click();
  const confirmar = page.getByRole("dialog", { name: "Remover a chave de openai do cofre?" });
  await confirmar.getByRole("button", { name: "Cancelar" }).click(); // sem confirmar, nada muda
  await expect(situacao).toHaveText("há chave no cofre");
  await cartao.getByRole("button", { name: "Remover do cofre" }).click();
  await confirmar.getByRole("button", { name: "Remover" }).click();
  await expect(chaves.getByLabel("Aviso das chaves")).toContainText("Chave de openai removida do cofre");
  await expect(situacao).toHaveText("não há chave");
  expect((await (await page.request.get("/api/segredos")).json()).segredos).toEqual([]);
});

test("troca de empresa: seletor só para quem tem mais de uma, empresa ativa inequívoca e dados isolados", async ({ page, browser }) => {
  test.setTimeout(120_000);
  // daqui em diante o cadastro deste servidor tem empresas: por isso este roteiro é o último do arquivo
  cliAvancado(["--como", "admin", "empresa", "criar", "alfa", "--nome", "Alfa S.A.", "--porte", "media"]);
  cliAvancado(["--como", "admin", "empresa", "criar", "beta", "--nome", "Beta Ltda", "--porte", "pequena"]);
  cliAvancado(["--como", "admin", "empresa", "escopo", "elisa", "alfa"]);
  cliAvancado(["--como", "admin", "empresa", "escopo", "avaliador", "alfa", "beta"]);
  const sem = { storageState: { cookies: [], origins: [] } };

  // uma empresa só no escopo: entra direto nela, vê qual é e não tem o que trocar
  const contextoElisa = await browser.newContext(sem);
  const elisa = await contextoElisa.newPage();
  await entrar(elisa, "elisa");
  await expect(aoVivo(elisa)).toBeVisible();
  await expect(elisa.getByRole("heading", { level: 1 })).toContainText("Alfa S.A. · Escritório de controladoria");
  await expect(elisa.getByLabel("Empresa ativa")).toHaveText("Alfa S.A.");
  await expect(elisa.getByRole("combobox", { name: "Empresa ativa" })).toHaveCount(0);
  await comando(contextoElisa.request, { tipo: "solicitar", intencao: "avaliar_orcamento", competencia: "2026-09" });
  await elisa.getByRole("tab", { name: "Solicitações" }).click();
  await expect(elisa.getByRole("table", { name: "Solicitações" }).getByRole("cell", { name: "elisa", exact: true })).toHaveCount(1);
  const fora = await contextoElisa.request.post("/api/empresa", { data: { empresa: "beta" },
    headers: { "X-SMA-Token": (await (await contextoElisa.request.get("/api/sessao")).json()).csrf } });
  expect(fora.status()).toBe(403); // fora do escopo, nem pela API

  // duas empresas: escolhe antes de qualquer coisa; nada abre sem empresa ativa
  await entrar(page, "avaliador");
  const escolha = page.getByRole("main", { name: "Escolher a empresa" });
  await expect(escolha.getByRole("list", { name: "Empresas da sua conta" }).getByRole("button")).toHaveCount(2);
  await expect(aoVivo(page)).toBeHidden();
  expect((await page.request.get("/api/estado")).status()).toBe(403);
  await escolha.getByRole("button", { name: /Beta Ltda/ }).click();
  await expect(aoVivo(page)).toBeVisible();
  const seletor = page.getByRole("combobox", { name: "Empresa ativa" });
  await expect(seletor).toHaveText("Beta Ltda");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Beta Ltda · Escritório de controladoria");
  await expect(page.getByText(/^empresa Beta Ltda · t=/)).toBeVisible();
  // em beta: o pedido de elisa (feito em alfa) não existe, e o avaliador troca o cenário só de beta
  await page.getByRole("tab", { name: "Solicitações" }).click();
  const solicitacoes = page.getByRole("table", { name: "Solicitações" });
  await expect(solicitacoes.getByRole("row").nth(1)).toBeVisible();
  await expect(solicitacoes.getByRole("cell", { name: "elisa", exact: true })).toHaveCount(0);
  await comando(page.request, { tipo: "reiniciar", cenario: "fechar_mes" });
  await expect.poll(async () => (await (await page.request.get("/api/estado")).json()).controle.cenario).toBe("fechar_mes");

  // troca para alfa pelo seletor: mesma aba, outros dados, outro fluxo de eventos
  await seletor.click();
  await page.getByRole("option", { name: /Alfa S\.A\./ }).click();
  await expect(seletor).toHaveText("Alfa S.A.");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Alfa S.A. · Escritório de controladoria");
  await expect(solicitacoes.getByRole("cell", { name: "elisa", exact: true })).toHaveCount(1);
  expect((await (await page.request.get("/api/estado")).json()).controle.cenario).toBe("expediente_sma");
  await page.getByRole("tab", { name: "Escritório" }).click();
  await expect(page.getByText(/^empresa Alfa S\.A\. · t=/)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Cenário" })).toHaveText("expediente_sma"); // veio do fluxo de alfa
  // e de volta a beta: o cenário que só beta reiniciou
  await seletor.click();
  await page.getByRole("option", { name: /Beta Ltda/ }).click();
  await expect(page.getByText(/^empresa Beta Ltda · t=/)).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Cenário" })).toHaveText("fechar_mes");
  await page.reload(); // a empresa ativa é da sessão: recarregar não a perde nem pede de novo
  await expect(aoVivo(page)).toBeVisible();
  await expect(seletor).toHaveText("Beta Ltda");

  // quem perde a empresa do escopo é levado à escolha; conta sem empresa nenhuma vê o aviso
  cliAvancado(["--como", "admin", "empresa", "escopo", "elisa"]);
  await expect(elisa.getByRole("main", { name: "Escolher a empresa" })).toContainText("não tem acesso a nenhuma empresa",
    { timeout: 20_000 });
  await contextoElisa.close();
  const contextoBruno = await browser.newContext(sem);
  const bruno = await contextoBruno.newPage();
  await entrar(bruno, "bruno", SENHA);
  await expect(bruno.getByRole("main", { name: "Escolher a empresa" })).toContainText("não tem acesso a nenhuma empresa");
  await contextoBruno.close();
});

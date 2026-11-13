// Gera os PNG dos diagramas Mermaid de uma entrega (DSM3 em diante).
//
// Lê <entrega>/modelos-editaveis/*.mmd e grava <entrega>/diagramas/<nome>.png para cada fonte
// que não tem PNG ou cujo PNG é mais antigo que a fonte. Renderiza com o mermaid e o Playwright
// instalados em web/node_modules (nada é baixado da rede): página em branco, fundo branco,
// deviceScaleFactor 2, captura do SVG renderizado.
//
// Uso (a partir de web/, para resolver as dependências):
//   node ../tools/diagramas.mjs ../entregas/dsm3            só os desatualizados
//   node ../tools/diagramas.mjs ../entregas/dsm3 --todos    regenera todos
// Navegador: PW_CHANNEL (padrão "chrome", o Chrome do sistema; "chromium" usa o do Playwright).
// Erro de sintaxe no Mermaid: mensagem com o arquivo e o erro, código de saída 1.
import { createRequire } from "node:module";
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const args = process.argv.slice(2);
const todos = args.includes("--todos");
const pasta = args.find((a) => !a.startsWith("--"));
if (!pasta) {
  console.error("uso: node ../tools/diagramas.mjs <pasta da entrega> [--todos]   (rode a partir de web/)");
  process.exit(2);
}
const entrega = resolve(pasta);
const fontes = join(entrega, "modelos-editaveis");
const destino = join(entrega, "diagramas");
if (!existsSync(fontes)) {
  console.error(`pasta não encontrada: ${fontes}`);
  process.exit(2);
}

// dependências resolvidas a partir do diretório atual (web/), não da pasta deste script
const requerer = createRequire(join(process.cwd(), "package.json"));
let caminhoMermaid, playwright;
try {
  caminhoMermaid = requerer.resolve("mermaid/dist/mermaid.min.js");
  playwright = requerer("@playwright/test"); // pacote CommonJS
} catch (erro) {
  console.error(`dependências ausentes (rode a partir de web/ depois de "bun install"): ${erro.message}`);
  process.exit(2);
}

const pendentes = readdirSync(fontes)
  .filter((n) => n.endsWith(".mmd"))
  .sort()
  .filter((n) => {
    const png = join(destino, basename(n, ".mmd") + ".png");
    // comparação em segundos inteiros: arquivos gravados juntos (checkout do git) contam como em dia
    const segundos = (arquivo) => Math.floor(statSync(arquivo).mtimeMs / 1000);
    return todos || !existsSync(png) || segundos(png) < segundos(join(fontes, n));
  });
if (pendentes.length === 0) {
  console.log(`diagramas: nada a fazer em ${destino} (todos os PNG estão em dia)`);
  process.exit(0);
}
mkdirSync(destino, { recursive: true });

const navegador = await playwright.chromium.launch({ channel: process.env.PW_CHANNEL ?? "chrome", headless: true });
const falhas = [];
try {
  const contexto = await navegador.newContext({ deviceScaleFactor: 2, viewport: { width: 2400, height: 1600 } });
  const pagina = await contexto.newPage();
  await pagina.setContent(
    '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}'
      + "#d{display:inline-block;padding:16px;background:#fff}</style></head><body><div id=\"d\"></div></body></html>",
  );
  await pagina.addScriptTag({ path: caminhoMermaid });
  await pagina.evaluate(() =>
    window.mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "strict", fontFamily: "Arial, sans-serif" }),
  );
  for (const [n, nome] of pendentes.entries()) {
    const codigo = readFileSync(join(fontes, nome), "utf8");
    const resultado = await pagina.evaluate(async ({ codigo, id }) => {
      try {
        await window.mermaid.parse(codigo); // erro de sintaxe sobe aqui, com linha e trecho
        const { svg } = await window.mermaid.render(id, codigo);
        document.getElementById("d").innerHTML = svg;
        return { ok: true };
      } catch (erro) {
        document.getElementById("d").innerHTML = "";
        return { ok: false, erro: String(erro?.message ?? erro) };
      }
    }, { codigo, id: `diagrama${n}` });
    if (!resultado.ok) {
      falhas.push(nome);
      console.error(`ERRO de sintaxe Mermaid em ${join(fontes, nome)}:\n${resultado.erro}\n`);
      continue;
    }
    const png = join(destino, basename(nome, ".mmd") + ".png");
    await pagina.locator("#d").screenshot({ path: png, omitBackground: false });
    console.log(`ok  ${nome} -> ${png} (${statSync(png).size} bytes)`);
  }
} finally {
  await navegador.close();
}
if (falhas.length) {
  console.error(`diagramas: ${falhas.length} com erro: ${falhas.join(", ")}`);
  process.exit(1);
}
console.log(`diagramas: ${pendentes.length} PNG gerados em ${destino}`);

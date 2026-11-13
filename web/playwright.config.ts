// Testes reais de uso: o Chrome instalado (headless) opera o dashboard servido pelo servidor Python verdadeiro
// (`python -m fin_mas serve --demo`), com os agentes executando ao vivo e o controle de acesso ligado.
// Nada é simulado no navegador. Cada execução usa pastas temporárias próprias (dados, contas e chaves).
import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.PYTHON ?? join(raiz, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const PORTA = 8777;
// o processo principal sorteia a execução; os workers herdam a variável e enxergam as mesmas pastas
process.env.SMA_E2E_RUN ??= String(Date.now());
const BASE = join(tmpdir(), `sma-e2e-${process.env.SMA_E2E_RUN}`);
process.env.SMA_E2E_ACESSO = join(BASE, "acesso");
process.env.SMA_E2E_CHAVES = join(BASE, "chaves");
process.env.SMA_E2E_PYTHON = python;
process.env.SMA_E2E_RAIZ = raiz;
export const SESSAO_PADRAO = join(BASE, "sessao-avaliador.json");

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1, // um único servidor com estado: os testes reiniciam o cenário e rodam em série
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  globalSetup: "./e2e/preparar.ts",
  use: {
    baseURL: `http://127.0.0.1:${PORTA}`,
    channel: process.env.PW_CHANNEL ?? "chrome",
    headless: true,
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    storageState: SESSAO_PADRAO, // conta `avaliador` (opera, solicita, aprova e audita); os testes de acesso trocam
  },
  webServer: {
    command: `"${python}" -m fin_mas serve --porta ${PORTA} --ms-por-tick 40 --pasta-dados "${join(BASE, "dados")}" `
      + `--acesso "${process.env.SMA_E2E_ACESSO}" --demo`,
    cwd: raiz,
    env: { PYTHONPATH: join(raiz, "src"), PYTHONUTF8: "1", FIN_MAS_DIR_CHAVES: process.env.SMA_E2E_CHAVES },
    url: `http://127.0.0.1:${PORTA}/api/saude`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

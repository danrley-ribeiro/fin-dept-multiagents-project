// Testes reais de uso: o Chrome instalado opera o dashboard servido pelo servidor Python verdadeiro
// (`python -m fin_mas serve`), com os agentes executando ao vivo. Nada é simulado no navegador.
import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.PYTHON ?? join(raiz, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const PORTA = 8777;
const DADOS = join(tmpdir(), `sma-e2e-dados-${process.pid}`); // planilhas enviadas nos testes: fora do repositório

export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1, // um único servidor com estado: os testes reiniciam o cenário e rodam em série
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORTA}`,
    channel: process.env.PW_CHANNEL ?? "chrome",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `"${python}" -m fin_mas serve --porta ${PORTA} --ms-por-tick 40 --pasta-dados "${DADOS}"`,
    cwd: raiz,
    env: { PYTHONPATH: join(raiz, "src"), PYTHONUTF8: "1" },
    url: `http://127.0.0.1:${PORTA}/api/cenarios`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});

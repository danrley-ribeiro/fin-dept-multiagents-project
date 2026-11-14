// Testes reais de uso: o Chrome instalado (headless) opera o dashboard servido pelo servidor Python verdadeiro
// (`python -m fin_mas serve --demo`), com os agentes executando ao vivo e o controle de acesso ligado.
// Nada é simulado no navegador. Cada execução usa pastas temporárias próprias (dados, contas e chaves).
import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.PYTHON ?? join(raiz, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const PORTA = Number(process.env.SMA_E2E_PORTA ?? 8777); // outra porta para rodar em paralelo (ex.: worktrees)
// o processo principal sorteia a execução; os workers herdam a variável e enxergam as mesmas pastas
process.env.SMA_E2E_RUN ??= String(Date.now());
const BASE = join(tmpdir(), `sma-e2e-${process.env.SMA_E2E_RUN}`);
process.env.SMA_E2E_ACESSO = join(BASE, "acesso");
process.env.SMA_E2E_CHAVES = join(BASE, "chaves");
process.env.SMA_E2E_PYTHON = python;
process.env.SMA_E2E_RAIZ = raiz;
export const SESSAO_PADRAO = join(BASE, "sessao-avaliador.json");
// Segundo servidor, com cadastro próprio, só para `avancado.spec.ts`: segundo fator, política do cadastro, cofre e
// empresas mexem em estado que vale para todas as contas (criar uma empresa tira o acesso de quem não tem escopo, e
// não há como desfazer). Assim os roteiros do servidor principal nunca veem esse estado.
const PORTA_AVANCADO = Number(process.env.SMA_E2E_PORTA_AVANCADO ?? PORTA + 1);
process.env.SMA_E2E_ACESSO_AVANCADO = join(BASE, "avancado", "acesso");
process.env.SMA_E2E_CHAVES_AVANCADO = join(BASE, "avancado", "chaves");
const ROTEIRO_AVANCADO = /avancado\.spec\.ts$/;
const servidor = (porta: number, dados: string, acesso: string, chaves: string, env: Record<string, string> = {}) => ({
  command: `"${python}" -m fin_mas serve --porta ${porta} --ms-por-tick 40 --pasta-dados "${dados}" --acesso "${acesso}" --demo`,
  cwd: raiz,
  env: { PYTHONPATH: join(raiz, "src"), PYTHONUTF8: "1", FIN_MAS_DIR_CHAVES: chaves, ...env },
  url: `http://127.0.0.1:${porta}/api/saude`,
  reuseExistingServer: false,
  timeout: 60_000,
});

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
  projects: [
    { name: "escritorio", testIgnore: ROTEIRO_AVANCADO },
    { name: "avancado", testMatch: ROTEIRO_AVANCADO,
      use: { baseURL: `http://127.0.0.1:${PORTA_AVANCADO}`, storageState: { cookies: [], origins: [] } } },
  ],
  webServer: [
    servidor(PORTA, join(BASE, "dados"), process.env.SMA_E2E_ACESSO!, process.env.SMA_E2E_CHAVES!),
    // sem chave de LLM no ambiente: o roteiro do cofre precisa ver "não há chave" antes de definir uma
    servidor(PORTA_AVANCADO, join(BASE, "avancado", "dados"), process.env.SMA_E2E_ACESSO_AVANCADO!,
      process.env.SMA_E2E_CHAVES_AVANCADO!, { OPENAI_API_KEY: "" }),
  ],
});

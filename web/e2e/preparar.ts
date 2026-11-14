// Antes dos testes: entra como `avaliador` pela API e guarda o cookie da sessão, que o navegador e o
// `request` dos testes passam a usar. Os testes de controle de acesso abrem contextos sem essa sessão.
import { request, type FullConfig } from "@playwright/test";
import { SENHA } from "./apoio";
import { SESSAO_PADRAO } from "../playwright.config";

export default async function preparar(config: FullConfig) {
  const api = await request.newContext({ baseURL: config.projects[0].use.baseURL });
  const r = await api.post("/api/login", { data: { usuario: "avaliador", senha: SENHA } });
  if (!r.ok()) throw new Error(`não foi possível entrar como avaliador: ${r.status()} ${await r.text()}`);
  await api.storageState({ path: SESSAO_PADRAO });
  await api.dispose();
}

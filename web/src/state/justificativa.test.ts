// A regra do botão de waiver é a mesma da POL-04 do servidor (revisão do PR, item 1).
import { describe, expect, it } from "vitest";
import { justificativaValida } from "./justificativa";

describe("justificativa do waiver (POL-04)", () => {
  it.each(["", "   ", "aaaaaaaaaa", "ok ok ok ok ok", "risco risco risco", "1234567890 12"])(
    "recusa %j", (texto) => expect(justificativaValida(texto)).toBe(false));

  it.each(["risco aceito pela diretoria", "aceito o risco: lançamento será corrigido no próximo ciclo",
    "ajuste de alçada aprovado"])("aceita %j", (texto) => expect(justificativaValida(texto)).toBe(true));
});

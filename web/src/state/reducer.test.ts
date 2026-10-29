// Integração do reducer com um trace real exportado pelo Python (não fixture inventada).
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { TraceExportado } from "../api/fonte";
import { aplicarTodos, estadoInicial, statusDe } from "./reducer";

function trace(nome: string): TraceExportado {
  return JSON.parse(readFileSync(new URL(`../../public/traces/${nome}.json`, import.meta.url), "utf-8"));
}

describe("escritório reconstruído do trace exportado", () => {
  it("desvio_irregular: mente do AG-ORC mostra a reconsideração e o AG-CIN corrige o veto", () => {
    const t = trace("desvio_irregular");
    const s = aplicarTodos(estadoInicial(), t.registros);
    const orc = s.agentes["AG-ORC"].mente;
    const sinalizar = Object.values(orc.intencoes).find((i) => i.plano === "P-SINALIZAR")!;
    expect(sinalizar.estado).toBe("abandonada");
    expect(sinalizar.historico.map((h) => h.evento)).toEqual(["adotada", "suspensa", "abandonada"]);
    expect(Object.keys(orc.crencas).some((k) => k.startsWith("contestado[C-3002 Marketing]"))).toBe(true);
    const cin = s.agentes["AG-CIN"].mente;
    expect(cin.deliberacoes.map((d) => d.escolhido)).toEqual(["P-VETAR-COM-CORRECAO", "P-APROVAR"]);
    expect(s.agentes["AG-CIN"].vetando).toBe(false);
    expect(s.conversas["CMP-001"].estado).toBe("LIBERADO");
    expect(s.solicitacoes["SOL-001"].status).toBe("publicado_com_ressalva");
    expect(s.pendentes).toEqual({});
  });

  it("aplicar em lotes (ao vivo) dá o mesmo estado que de uma vez (replay)", () => {
    const t = trace("expediente_sma");
    const inteiro = aplicarTodos(estadoInicial(), t.registros);
    let lotes = estadoInicial();
    for (let i = 0; i < t.registros.length; i += 7) lotes = aplicarTodos(lotes, t.registros.slice(i, i + 7));
    expect(lotes.solicitacoes).toEqual(inteiro.solicitacoes);
    expect(lotes.agentes["AG-ORC"].mente.crencas).toEqual(inteiro.agentes["AG-ORC"].mente.crencas);
    expect(Object.values(inteiro.solicitacoes).map((x) => x.status)).toContain("recusado");
    expect(inteiro.reservas).toEqual({});
  });

  it("veto pendente aparece para o aprovador até a decisão humana", () => {
    const t = trace("veto_waiver");
    const ateAviso = t.registros.filter((r) => r.seq <= t.registros.find((x) => x.performative === "veto_notice")!.seq);
    const s = aplicarTodos(estadoInicial(), ateAviso);
    expect(Object.keys(s.pendentes)).toEqual(["SOL-001"]);
    expect(s.pendentes["SOL-001"].opcoes).toContain("corrigir");
    expect(statusDe(s, "AG-CIN")).toBe("vetando");
    const fim = aplicarTodos(s, t.registros.filter((r) => r.seq > s.seq));
    expect(fim.pendentes).toEqual({});
  });
});

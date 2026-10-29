// Notificações "não vistas": o que aconteceu com cada agente (e em cada aba da mente) desde a última olhada.
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Registro, ViewState } from "../types";

const EVENTOS_INTENCAO = new Set(["adotada", "reconsiderada", "abandonada", "falhou", "concluida"]);

/** Registro relevante para o badge do agente: decisões, deliberações, mudanças de intenção e timeouts. */
export function notificavel(r: Registro): string | null {
  if (r.kind === "decision" || r.kind === "deliberation") return String(r.agente);
  if (r.kind === "intention" && EVENTOS_INTENCAO.has(String(r.evento))) return String(r.agente);
  return null;
}

/** Contagem por agente de registros notificáveis com seq maior que o visto; o agente selecionado fica em dia. */
export function useNovidadesAgentes(estado: ViewState, selecionado: string | null, chave: string | number) {
  const [visto, setVisto] = useState<Record<string, number>>({});
  useEffect(() => setVisto({}), [chave]);
  useEffect(() => {
    if (selecionado) setVisto((v) => (v[selecionado] === estado.seq ? v : { ...v, [selecionado]: estado.seq }));
  }, [selecionado, estado.seq]);
  return useMemo(() => {
    const n: Record<string, number> = {};
    for (const r of estado.registros) {
      const a = notificavel(r);
      if (a && a !== selecionado && r.seq > (visto[a] ?? 0)) n[a] = (n[a] ?? 0) + 1;
    }
    return n;
  }, [estado.registros, visto, selecionado]);
}

/** Itens novos por aba (seq > visto); a aba aberta é marcada como vista. */
export function useNovidadesAbas(seqsPorAba: Record<string, number[]>, abaAtual: string, seqAtual: number) {
  // ao abrir o painel, o que já existia conta como visto: o badge mostra só o que chegar depois
  const [visto, setVisto] = useState<Record<string, number>>(
    () => Object.fromEntries(Object.keys(seqsPorAba).map((k) => [k, seqAtual])));
  useEffect(() => {
    setVisto((v) => (v[abaAtual] === seqAtual ? v : { ...v, [abaAtual]: seqAtual }));
  }, [abaAtual, seqAtual]);
  const contar = useCallback((aba: string) => (aba === abaAtual ? 0
    : (seqsPorAba[aba] ?? []).filter((s) => s > (visto[aba] ?? 0)).length), [seqsPorAba, visto, abaAtual]);
  return contar;
}

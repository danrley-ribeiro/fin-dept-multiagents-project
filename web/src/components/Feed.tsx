// Trilha causal (o mesmo texto do `replay` da CLI), com filtros em chips e contadores por categoria.
import { Badge, Box, Chip, FormControlLabel, Paper, Stack, Switch, Typography } from "@mui/material";
import { useEffect, useMemo, useRef, useState } from "react";
import { atorDe, categoria, formatar } from "../state/reducer";
import type { Registro } from "../types";

const CATEGORIAS = [
  ["mensagem", "Mensagens"], ["mente", "BDI"], ["decisao", "Decisões"], ["falha", "Falhas"], ["ambiente", "Ambiente"],
] as const;

export function Feed({ registros, agente }: { registros: Registro[]; agente: string | null }) {
  const [ativas, setAtivas] = useState<Set<string>>(new Set(["mensagem", "mente", "decisao", "falha"]));
  const [soAgente, setSoAgente] = useState(false);
  const [seguir, setSeguir] = useState(true);
  const lista = useRef<HTMLOListElement>(null);
  const relevantes = useMemo(() => registros.filter((r) => r.kind !== "deliver"), [registros]);
  const contagem = useMemo(() => {
    const n: Record<string, number> = {};
    for (const r of relevantes) n[categoria(r)] = (n[categoria(r)] ?? 0) + 1;
    return n;
  }, [relevantes]);
  const visiveis = useMemo(() => relevantes.filter((r) => ativas.has(categoria(r))
    && (!soAgente || !agente || atorDe(r) === agente || r.receiver === agente)).slice(-400),
  [relevantes, ativas, soAgente, agente]);

  useEffect(() => {
    if (seguir && lista.current) lista.current.scrollTop = lista.current.scrollHeight;
  }, [visiveis, seguir]);

  const alternar = (c: string) => setAtivas((s) => {
    const n = new Set(s);
    if (n.has(c)) n.delete(c); else n.add(c);
    return n;
  });

  return (
    <Paper component="section" aria-label="Trilha causal" sx={{ p: 2 }}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1} sx={{ mb: 1 }}>
        <Typography variant="h2" component="h2">Trilha causal</Typography>
        <Stack direction="row" flexWrap="wrap" useFlexGap spacing={1} alignItems="center">
          {CATEGORIAS.map(([c, rotulo]) => (
            <Badge key={c} badgeContent={contagem[c] ?? 0} max={999} color={c === "falha" ? "error" : "primary"}
              invisible={ativas.has(c) || !(contagem[c] ?? 0)}>
              <Chip size="small" label={`${rotulo}${ativas.has(c) ? ` · ${contagem[c] ?? 0}` : ""}`}
                color={ativas.has(c) ? (c === "falha" ? "error" : "primary") : "default"}
                variant={ativas.has(c) ? "filled" : "outlined"} onClick={() => alternar(c)}
                aria-pressed={ativas.has(c)} />
            </Badge>
          ))}
          <FormControlLabel control={<Switch size="small" checked={soAgente} disabled={!agente}
            onChange={(e) => setSoAgente(e.target.checked)} />} label={`só ${agente ?? "o agente selecionado"}`} />
          <FormControlLabel control={<Switch size="small" checked={seguir} onChange={(e) => setSeguir(e.target.checked)} />}
            label="acompanhar" />
        </Stack>
      </Stack>
      <Box component="ol" ref={lista} className="feed-linhas" aria-live="off">
        {visiveis.map((r) => <li key={r.seq} className={`cat-${categoria(r)}`}>{formatar(r)}</li>)}
      </Box>
    </Paper>
  );
}

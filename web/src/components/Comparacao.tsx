// SMA x workflow centralizado (baseline da DSM1) nas mesmas seeds: barras agrupadas, um eixo por métrica.
import {
  Alert, Box, FormControl, FormControlLabel, InputLabel, MenuItem, Paper, Select, Stack, Switch, Table, TableBody,
  TableCell, TableHead, TableRow, Typography,
} from "@mui/material";
import { useState } from "react";
import type { ResumoComparacao } from "../api/fonte";

const METRICAS = [
  { campo: "desvios_corretos", rotulo: "Desvios classificados como no gabarito", pct: true },
  { campo: "criticas_publicadas_sem_tratamento", rotulo: "Críticas publicadas sem tratamento", pct: false },
  { campo: "criticas_corrigidas", rotulo: "Críticas corrigidas no ciclo", pct: false },
  { campo: "mensagens_a2a", rotulo: "Mensagens A2A por solicitação", pct: false },
  { campo: "latencia_ticks", rotulo: "Latência lógica (ticks)", pct: false },
  { campo: "distribuicao_decisoria", rotulo: "Decisões fora do Orquestrador", pct: true },
  { campo: "reconsideracoes", rotulo: "Reconsiderações de intenção", pct: false },
] as const;

const SERIES = [
  { chave: "SMA", rotulo: "SMA (agentes)", cor: "var(--series-1)" },
  { chave: "workflow", rotulo: "Workflow centralizado", cor: "var(--series-2)" },
];

function fmt(v: number | null, pct: boolean) {
  if (v === null || v === undefined) return "n/a";
  return pct ? `${Math.round(v * 100)}%` : v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

export function Comparacao({ resumo }: { resumo: ResumoComparacao | null }) {
  const [campo, setCampo] = useState<string>("desvios_corretos");
  const [tabela, setTabela] = useState(false);
  const [dica, setDica] = useState<{ x: number; y: number; texto: string } | null>(null);
  if (!resumo) {
    return <Alert severity="warning" sx={{ mt: 2 }}>Sem resultados: rode <code>python -m fin_mas comparar</code> e
      depois <code>python -m fin_mas export</code>.</Alert>;
  }
  const m = METRICAS.find((x) => x.campo === campo)!;
  const cenarios = Object.keys(resumo).filter((n) => !n.startsWith("_"));
  const valor = (n: string, s: string) => resumo[n][s][campo] as number | null;
  const maximo = m.pct ? 1 : Math.max(1, ...cenarios.flatMap((n) => SERIES.map((s) => valor(n, s.chave) ?? 0)));
  const g = resumo._global as unknown as Record<string, number | number[]>;
  const rotuloW = 150, larg = 520, barra = 9, folga = 2, linha = barra * 2 + folga + 12;
  const altura = cenarios.length * linha + 12;

  return (
    <Paper component="section" aria-label="Comparação com o baseline" sx={{ p: 2, mt: 2 }}>
      <Typography variant="h2" component="h2">SMA × workflow centralizado</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        Médias em {(g.seeds as number[]).length} seeds por cenário (mesmas seeds nas duas estratégias).
        {" "}MET-01 {fmt(g["MET-01_conclusao"] as number, true)} · MET-13 {fmt(g["MET-13_resposta_explicita"] as number, true)}
        {" "}· MET-14 {fmt(g["MET-14_distribuicao_decisoria"] as number, true)}.
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }} sx={{ my: 2 }}>
        <FormControl size="small" sx={{ minWidth: 300 }}>
          <InputLabel id="metrica">Métrica</InputLabel>
          <Select labelId="metrica" label="Métrica" value={campo} onChange={(e) => setCampo(e.target.value)}>
            {METRICAS.map((x) => <MenuItem key={x.campo} value={x.campo}>{x.rotulo}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControlLabel control={<Switch checked={tabela} onChange={(e) => setTabela(e.target.checked)} />}
          label="Ver como tabela" />
        <Stack direction="row" spacing={2} className="legenda">
          {SERIES.map((s) => <span key={s.chave}><i style={{ background: s.cor }} /> {s.rotulo}</span>)}
        </Stack>
      </Stack>
      {tabela ? (
        <Table size="small" aria-label={m.rotulo}>
          <TableHead><TableRow><TableCell>Cenário</TableCell>
            {SERIES.map((s) => <TableCell key={s.chave} align="right">{s.rotulo}</TableCell>)}</TableRow></TableHead>
          <TableBody>{cenarios.map((n) => (
            <TableRow key={n} hover><TableCell>{n}</TableCell>{SERIES.map((s) => <TableCell key={s.chave} align="right">
              {fmt(valor(n, s.chave), m.pct)} <Typography component="span" variant="caption" color="text.secondary">
                ({String(resumo[n][s.chave].status)})</Typography></TableCell>)}</TableRow>
          ))}</TableBody>
        </Table>
      ) : (
        <Box className="grafico" onMouseLeave={() => setDica(null)}>
          <svg viewBox={`0 0 ${rotuloW + larg + 60} ${altura}`} role="img" aria-label={m.rotulo}>
            <line x1={rotuloW} x2={rotuloW} y1={0} y2={altura - 6} className="eixo" />
            {cenarios.map((n, i) => (
              <g key={n} transform={`translate(0 ${i * linha + 6})`}>
                <text x={rotuloW - 8} y={barra + 3} textAnchor="end" className="rotulo-eixo">{n}</text>
                {SERIES.map((s, j) => {
                  const v = valor(n, s.chave);
                  const w = v === null ? 0 : (v / maximo) * larg;
                  const y = j * (barra + folga);
                  const texto = `${n} · ${s.rotulo}: ${fmt(v, m.pct)} (${resumo[n][s.chave].status})`;
                  return (
                    <g key={s.chave}
                      onMouseMove={(e) => setDica({ x: e.nativeEvent.offsetX, y: e.nativeEvent.offsetY, texto })}>
                      <rect x={rotuloW} y={y - 1} width={larg + 50} height={barra + 2} fill="transparent" />
                      {w > 0 && <rect x={rotuloW} y={y} width={Math.max(w, 2)} height={barra} rx={2} fill={s.cor} />}
                      <text x={rotuloW + w + 6} y={y + barra - 1} className="valor-barra">{fmt(v, m.pct)}</text>
                    </g>
                  );
                })}
              </g>
            ))}
          </svg>
          {dica && <div className="dica" style={{ left: dica.x + 12, top: dica.y + 12 }}>{dica.texto}</div>}
        </Box>
      )}
      <Alert severity="info" variant="outlined" sx={{ mt: 2 }}>
        O workflow não “acerta” o veto: ele publica por falta de mecanismo. Com perda de mensagens
        (<code>falha_especialista</code>), é o workflow que publica e o SMA falha explicitamente — o custo da distribuição.
        Interpretação completa em <code>docs/dsm2/comparacao.md</code>.
      </Alert>
    </Paper>
  );
}

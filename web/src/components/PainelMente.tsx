// Mente do agente selecionado: intenções, deliberações (opções e motivos), crenças, desejos, decisões e planos.
import AddIcon from "@mui/icons-material/Add";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import {
  Alert, Badge, Box, Button, Card, CardContent, Chip, Collapse, IconButton, List, ListItem, Paper, Stack, Tab,
  Table, TableBody, TableCell, TableHead, TableRow, Tabs, TextField, Tooltip, Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useMemo, useState } from "react";
import type { MenteSnapshot } from "../api/fonte";
import { useNovidadesAbas } from "../state/novidades";
import { statusDe } from "../state/reducer";
import type { FichaAgente, Intencao, ViewState } from "../types";
import { COR_AGENTE, departamentoDe } from "./Escritorio";

interface Props {
  id: string;
  estado: ViewState;
  ficha?: FichaAgente;
  snapshot?: MenteSnapshot;
  aoVivo: boolean;
  aoAlternarEnergia?: (id: string, online: boolean) => void;
  aoNovoPedido?: () => void;
}

type Aba = "intencoes" | "deliberacoes" | "crencas" | "desejos" | "decisoes" | "planos";

export function brl(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function valorCurto(v: unknown, max = 90): string {
  if (typeof v === "number") return Number.isInteger(v) && Math.abs(v) >= 10000 ? brl(v) : String(v);
  const t = typeof v === "string" ? v : JSON.stringify(v);
  return t === undefined ? "—" : t.length > max ? t.slice(0, max - 1) + "…" : t;
}

const COR_ESTADO: Record<string, "primary" | "warning" | "success" | "error" | "default"> = {
  ativa: "primary", suspensa: "warning", concluida: "success", abandonada: "error", falhou: "error",
  ativo: "primary", satisfeito: "success", descartado: "default",
};

const ROTULO_STATUS: Record<string, string> = {
  trabalhando: "trabalhando", aguardando: "aguardando", ocioso: "ocioso", vetando: "vetando", fora: "fora de operação",
};
const COR_STATUS: Record<string, "success" | "warning" | "default" | "error"> = {
  trabalhando: "success", aguardando: "warning", ocioso: "default", vetando: "error", fora: "error",
};

export function PainelMente({ id, estado, ficha, snapshot, aoVivo, aoAlternarEnergia, aoNovoPedido }: Props) {
  const a = estado.agentes[id];
  const bdi = id === "AG-ORC" || id === "AG-CIN";
  const humano = id === "SOL" || id === "APR";
  const status = statusDe(estado, id);
  const desligavel = aoVivo && !humano && id !== "AG-ORQ";
  const abas: [Aba, string][] = bdi
    ? [["intencoes", "Intenções"], ["deliberacoes", "Deliberações"], ["crencas", "Crenças"], ["desejos", "Desejos"],
      ["decisoes", "Decisões"], ["planos", "Planos"]]
    : [["decisoes", "Decisões"]];
  const [aba, setAba] = useState<Aba>(abas[0][0]);

  const seqs = useMemo(() => ({
    intencoes: Object.values(a.mente.intencoes).map((i) => i.seq),
    deliberacoes: a.mente.deliberacoes.map((d) => d.seq),
    crencas: Object.values(a.mente.crencas).map((c) => c.seq),
    desejos: Object.values(a.mente.desejos).map((d) => d.seq),
    decisoes: a.mente.decisoes.map((d) => d.seq),
    planos: [] as number[],
  }), [a]);
  const novos = useNovidadesAbas(seqs, aba, estado.seq);

  return (
    <Paper component="section" aria-label={`Mente de ${id}`} sx={{ p: 2, display: "flex", flexDirection: "column",
      gap: 1.5, position: { lg: "sticky" }, top: { lg: 132 }, maxHeight: { lg: "calc(100vh - 148px)" } }}>
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Box sx={{ width: 14, height: 14, borderRadius: 1, mt: 0.6, flexShrink: 0, bgcolor: COR_AGENTE[id] }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h2" component="h2">{id} · {departamentoDe(id, ficha)}</Typography>
          <Typography variant="body2" color="text.secondary">{ficha?.titulo ?? id}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{ficha?.cognicao}</Typography>
        </Box>
        <Chip size="small" label={ROTULO_STATUS[status]} color={COR_STATUS[status]} variant="outlined" />
      </Stack>
      {desligavel && (
        <Button variant={status === "fora" ? "contained" : "outlined"} color={status === "fora" ? "primary" : "error"}
          startIcon={<PowerSettingsNewIcon />} onClick={() => aoAlternarEnergia?.(id, status === "fora")}>
          {status === "fora" ? "Religar agente" : "Desligar agente (simular falha)"}
        </Button>
      )}
      {!aoVivo && !humano && id !== "AG-ORQ" && (
        <Tooltip title="O replay reproduz um trace gravado: para desligar agentes, rode o servidor (python -m fin_mas serve)">
          <span><Button fullWidth variant="outlined" disabled startIcon={<PowerSettingsNewIcon />}>
            Desligar agente (só no modo ao vivo)</Button></span>
        </Tooltip>
      )}
      {!bdi && !humano && (
        <Alert severity="info" variant="outlined" sx={{ py: 0 }}>
          {id === "AG-ORQ" ? "Reativo a protocolos: roteia o pedido, não decide conformidade nem desvio."
            : "Deliberativo determinístico: sem base BDI; as decisões mostram a regra aplicada."}
        </Alert>
      )}
      {id === "SOL" && (aoNovoPedido
        ? <Button variant="contained" startIcon={<AddIcon />} onClick={aoNovoPedido}>Novo pedido da liderança</Button>
        : <Alert severity="info" variant="outlined" sx={{ py: 0 }}>Novos pedidos só no modo ao vivo (botão
          “Novo pedido” na barra de controles).</Alert>)}
      {humano ? (
        <Alert severity="info" variant="outlined">
          {id === "APR" ? "Aprovador humano. No modo ao vivo a decisão sobre cada veto é sua: use o sino de pendências."
            : "Liderança da empresa: faz os pedidos do expediente (fechar o mês, avaliar o orçamento)."}
        </Alert>
      ) : (
        <>
          <Tabs value={aba} onChange={(_, v) => setAba(v)} variant="scrollable" scrollButtons="auto"
            aria-label="Partes da mente" sx={{ borderBottom: 1, borderColor: "divider", minHeight: 42 }}>
            {abas.map(([k, rotulo]) => (
              <Tab key={k} value={k} label={
                <Badge color="secondary" badgeContent={novos(k)} max={99} sx={{ pr: novos(k) ? 1.5 : 0 }}>
                  <span>{rotulo}{k !== "planos" ? ` (${seqs[k].length})` : ""}</span>
                </Badge>} />
            ))}
          </Tabs>
          <Box sx={{ overflow: "auto", minHeight: 120 }}>
            {aba === "intencoes" && <Intencoes estado={estado} id={id} />}
            {aba === "deliberacoes" && <Deliberacoes estado={estado} id={id} />}
            {aba === "crencas" && <Crencas estado={estado} id={id} />}
            {aba === "desejos" && <Desejos estado={estado} id={id} />}
            {aba === "decisoes" && <Decisoes estado={estado} id={id} />}
            {aba === "planos" && <Planos snapshot={snapshot} />}
          </Box>
        </>
      )}
    </Paper>
  );
}

function Vazio({ texto }: { texto: string }) {
  return <Typography color="text.secondary" variant="body2" sx={{ py: 1 }}>{texto}</Typography>;
}

function Intencoes({ estado, id }: { estado: ViewState; id: string }) {
  const lista = Object.values(estado.agentes[id].mente.intencoes).sort((x, y) => y.seq - x.seq);
  if (!lista.length) return <Vazio texto="Nenhuma intenção adotada ainda." />;
  return <List dense disablePadding>{lista.map((i) => <CartaoIntencao key={i.id} i={i} />)}</List>;
}

function CartaoIntencao({ i }: { i: Intencao }) {
  const [aberto, setAberto] = useState(false);
  return (
    <ListItem disableGutters sx={{ display: "block", py: 0.5 }}>
      <Card variant="outlined">
        <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
            <Typography variant="body2" fontWeight={700}>{i.plano}</Typography>
            <Chip size="small" label={i.estado} color={COR_ESTADO[i.estado] ?? "default"} variant="outlined" />
          </Stack>
          <Typography variant="caption" color="text.secondary" component="div">
            {i.id} · desejo <code>{i.desejo}</code>{i.estado === "suspensa" && i.aguardando
              ? ` · aguardando ${i.aguardando}` : ""}</Typography>
          <Stack direction="row" alignItems="center">
            <Typography variant="body2" sx={{ flex: 1 }}>{i.historico[i.historico.length - 1]?.motivo}</Typography>
            <Tooltip title={aberto ? "Ocultar histórico" : "Ver histórico da intenção"}>
              <IconButton size="small" onClick={() => setAberto(!aberto)} aria-expanded={aberto}
                aria-label="Histórico da intenção"
                sx={{ transform: aberto ? "rotate(180deg)" : "none", transition: "transform .2s" }}>
                <ExpandMoreIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <Collapse in={aberto}>
            <Box component="ol" sx={{ m: 0, pl: 2.5, typography: "caption" }}>
              {i.historico.map((h, k) => <li key={k}>t={h.t} <b>{h.evento}</b> — {h.motivo}</li>)}
            </Box>
          </Collapse>
        </CardContent>
      </Card>
    </ListItem>
  );
}

function Deliberacoes({ estado, id }: { estado: ViewState; id: string }) {
  const lista = [...estado.agentes[id].mente.deliberacoes].reverse();
  if (!lista.length) return <Vazio texto="Nenhuma deliberação ainda." />;
  return (
    <Stack spacing={1}>
      {lista.map((d) => (
        <Card key={d.seq} variant="outlined">
          <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
            <Stack direction="row" justifyContent="space-between">
              <Typography variant="body2" fontWeight={700}>{d.desejo}</Typography>
              <Typography variant="caption" color="text.secondary">t={d.t}</Typography>
            </Stack>
            <Table size="small" aria-label={`Opções para ${d.desejo}`}>
              <TableHead><TableRow><TableCell>Plano</TableCell><TableCell align="right">Utilidade</TableCell>
                <TableCell>Aplicável</TableCell><TableCell>Motivo</TableCell></TableRow></TableHead>
              <TableBody>
                {d.opcoes.map((o) => (
                  <TableRow key={o.plano} selected={o.plano === d.escolhido}>
                    <TableCell sx={{ fontWeight: o.plano === d.escolhido ? 700 : 400 }}>
                      {o.plano === d.escolhido ? "▶ " : ""}{o.plano}</TableCell>
                    <TableCell align="right">{o.utilidade}</TableCell>
                    <TableCell>{o.aplicavel ? "sim" : "não"}</TableCell>
                    <TableCell>{o.motivo}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function Crencas({ estado, id }: { estado: ViewState; id: string }) {
  const [filtro, setFiltro] = useState("");
  const lista = Object.entries(estado.agentes[id].mente.crencas)
    .filter(([k]) => k.toLowerCase().includes(filtro.toLowerCase()))
    .sort((x, y) => y[1].seq - x[1].seq);
  return (
    <Stack spacing={1}>
      <TextField size="small" label="Filtrar crenças" placeholder="ex.: Marketing, contestado" value={filtro}
        onChange={(e) => setFiltro(e.target.value)} />
      {!lista.length ? <Vazio texto="Sem crenças." /> : (
        <Table size="small" aria-label="Crenças">
          <TableHead><TableRow><TableCell>Crença</TableCell><TableCell>Valor</TableCell>
            <TableCell>Fonte</TableCell></TableRow></TableHead>
          <TableBody>
            {lista.map(([k, c]) => (
              <TableRow key={k} sx={c.t >= estado.t - 2 ? { bgcolor: "action.selected" } : undefined}>
                <TableCell><code>{k}</code></TableCell>
                <TableCell title={JSON.stringify(c.valor)}>
                  {c.antes !== null && c.antes !== undefined && (
                    <Typography component="s" variant="caption" color="text.secondary">{valorCurto(c.antes, 40)} </Typography>
                  )}{valorCurto(c.valor)}</TableCell>
                <TableCell><Typography variant="caption" color="text.secondary">{c.fonte}</Typography></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  );
}

function Desejos({ estado, id }: { estado: ViewState; id: string }) {
  const lista = Object.values(estado.agentes[id].mente.desejos)
    .sort((x, y) => x.prioridade - y.prioridade || y.seq - x.seq);
  if (!lista.length) return <Vazio texto="Sem desejos gerados." />;
  return (
    <Stack spacing={1}>
      {lista.map((d) => (
        <Card key={d.id} variant="outlined">
          <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
            <Stack direction="row" justifyContent="space-between" spacing={1}>
              <Typography variant="body2" fontWeight={700} sx={{ wordBreak: "break-word" }}>{d.id}</Typography>
              <Chip size="small" variant="outlined" color={COR_ESTADO[d.estado] ?? "default"}
                label={`p${d.prioridade} · ${d.estado}`} />
            </Stack>
            <Typography variant="body2" color="text.secondary">{d.motivo}</Typography>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function Decisoes({ estado, id }: { estado: ViewState; id: string }) {
  const lista = [...estado.agentes[id].mente.decisoes].reverse();
  if (!lista.length) return <Vazio texto="Nenhuma decisão registrada ainda." />;
  return (
    <Stack spacing={1}>
      {lista.map((d) => (
        <Card key={d.seq} variant="outlined">
          <CardContent sx={{ p: 1.25, "&:last-child": { pb: 1.25 } }}>
            <Stack direction="row" justifyContent="space-between" spacing={1}>
              <Typography variant="body2" fontWeight={700}>{d.regra}</Typography>
              <Typography variant="caption" color="text.secondary" noWrap>t={d.t} · {d.conversa}</Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary" component="div">
              entradas: <code>{valorCurto(d.entradas, 140)}</code></Typography>
            <Typography variant="body2">⇒ <code>{valorCurto(d.resultado, 140)}</code></Typography>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function Planos({ snapshot }: { snapshot?: MenteSnapshot }) {
  const bdi = snapshot?.bdi;
  if (!bdi) return <Vazio texto="Biblioteca de planos indisponível." />;
  return (
    <Stack spacing={1}>
      <Alert severity="info" variant="outlined" sx={{ py: 0 }}>
        Utilidade = 10 × soma dos pesos dos desejos permanentes atendidos (
        {Object.entries(bdi.desejos_permanentes).map(([k, v]) => `${k}: ${v}`).join(", ")}) + preferência.
      </Alert>
      <Table size="small" aria-label="Biblioteca de planos">
        <TableHead><TableRow><TableCell>Plano</TableCell><TableCell>Desejo</TableCell><TableCell>Atende</TableCell>
          <TableCell align="right">Utilidade</TableCell></TableRow></TableHead>
        <TableBody>
          {bdi.planos.map((p) => (
            <Tooltip key={p.id} title={p.descricao} placement="left">
              <TableRow hover>
                <TableCell>{p.id}</TableCell><TableCell>{p.desejo}</TableCell><TableCell>{p.atende.join(", ")}</TableCell>
                <TableCell align="right">{p.utilidade}</TableCell>
              </TableRow>
            </Tooltip>
          ))}
        </TableBody>
      </Table>
    </Stack>
  );
}

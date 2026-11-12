// Diálogos de apoio: chamadas a cada fonte de dados (MCP), períodos em fechamento (PROT-LCK) e
// "Dados da empresa" (porte, modelos Excel para empresas sem ERP e envio da planilha preenchida).
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  FormControlLabel, LinearProgress, List, ListItem, ListItemText, Radio, RadioGroup, Stack, Tab, Table, TableBody,
  TableCell, TableHead, TableRow, Tabs, Typography,
} from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { postar } from "../api/fonte";
import type { FonteDados, ViewState } from "../types";

const DESCRICAO_FONTE: Record<FonteDados, string> = {
  ERP: "Sistema de gestão da empresa: balancete (vendas e custos), lançamentos e realizado por conta. "
    + "Empresas sem ERP não têm esta fonte: os agentes usam a planilha (modo manual).",
  Planilhas: "Planilhas da controladoria: orçamento por conta e, na empresa sem ERP, todos os dados do mês "
    + "(modelo Excel). Lidas pelo servidor MCP de Excel, com proveniência arquivo#aba.",
  Normas: "Base normativa por porte (models/portes.yaml): alçadas, severidades, materialidade, controles "
    + "compensatórios e pesos dos desejos BDI.",
};

export function FonteDialog({ fonte, estado, aoFechar, aoAbrirDados }: { fonte: FonteDados; estado: ViewState;
  aoFechar: () => void; aoAbrirDados?: () => void }) {
  const chamadas = estado.chamadasMcp.filter((c) => {
    if (fonte === "Normas") return c.tool.startsWith("normas.");
    if (fonte === "Planilhas") return c.fonte.startsWith("mcp://excel") || c.tool.startsWith("planilhas.");
    return !c.tool.startsWith("normas.") && !c.tool.startsWith("planilhas.") && !c.fonte.startsWith("mcp://excel");
  }).slice().reverse();
  const info = estado.fontes[fonte];
  return (
    <Dialog open onClose={aoFechar} maxWidth="md" fullWidth aria-labelledby="titulo-fonte">
      <DialogTitle id="titulo-fonte">Fonte de dados: {fonte}
        <Chip size="small" sx={{ ml: 1 }} label={`${info.chamadas} chamada(s)`} />
        {info.indisponivel && <Chip size="small" color="warning" sx={{ ml: 1 }} label={info.indisponivel} />}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{DESCRICAO_FONTE[fonte]}</Typography>
        {!chamadas.length ? <Alert severity="info">Nenhuma chamada a esta fonte até agora.</Alert> : (
          <Table size="small" aria-label={`Chamadas à fonte ${fonte}`}>
            <TableHead><TableRow><TableCell>t</TableCell><TableCell>Agente</TableCell><TableCell>Tool</TableCell>
              <TableCell>Proveniência / resultado</TableCell></TableRow></TableHead>
            <TableBody>
              {chamadas.slice(0, 100).map((c) => (
                <TableRow key={c.seq} hover>
                  <TableCell>{c.t}</TableCell><TableCell>{c.agente}</TableCell><TableCell><code>{c.tool}</code></TableCell>
                  <TableCell>{c.negada ? <Chip size="small" color="warning" label={c.negada} /> : <code>{c.fonte}</code>}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions>
        {fonte !== "Normas" && aoAbrirDados && <Button onClick={aoAbrirDados} startIcon={<DownloadIcon />}>
          Modelos Excel e dados da empresa</Button>}
        <Button variant="contained" onClick={aoFechar}>Fechar</Button>
      </DialogActions>
    </Dialog>
  );
}

export function PeriodosDialog({ estado, aoFechar }: { estado: ViewState; aoFechar: () => void }) {
  const ativas = Object.entries(estado.reservas);
  return (
    <Dialog open onClose={aoFechar} maxWidth="sm" fullWidth aria-labelledby="titulo-periodos">
      <DialogTitle id="titulo-periodos">Períodos em fechamento (reserva PROT-LCK)</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Cada fechamento reserva (empresa, competência) com exclusão mútua: um segundo fechamento do mesmo mês é
          recusado até a reserva ser liberada (fim do fechamento, falha ou TTL).
        </Typography>
        <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Reservas ativas</Typography>
        {ativas.length ? (
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
            {ativas.map(([chave, dono]) => <Chip key={chave} color="primary" label={`${chave} · ${dono}`} />)}
          </Stack>
        ) : <Alert severity="success" sx={{ mb: 2 }}>Nenhum período reservado agora.</Alert>}
        <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Histórico</Typography>
        {!estado.historicoReservas.length ? <Typography variant="body2" color="text.secondary">Sem eventos de
          reserva ainda.</Typography> : (
          <Table size="small" aria-label="Histórico de reservas">
            <TableHead><TableRow><TableCell>t</TableCell><TableCell>Evento</TableCell><TableCell>Período</TableCell>
              <TableCell>Quem</TableCell><TableCell>Resultado</TableCell></TableRow></TableHead>
            <TableBody>
              {[...estado.historicoReservas].reverse().map((h, i) => (
                <TableRow key={i} hover>
                  <TableCell>{h.t}</TableCell><TableCell>{h.evento}</TableCell><TableCell>{h.chave}</TableCell>
                  <TableCell>{h.quem}</TableCell>
                  <TableCell>{h.resultado === "reserve-failure"
                    ? <Chip size="small" color="error" label="recusada (já reservado)" /> : h.resultado}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DialogContent>
      <DialogActions><Button variant="contained" onClick={aoFechar}>Fechar</Button></DialogActions>
    </Dialog>
  );
}

interface Porte { porte: string; titulo: string; tem_erp: boolean; norma_contabil: string }
interface Modelo { arquivo: string; porte: string | null; descricao: string }
interface SituacaoDados { planilha: string | null; erros?: string[]; porte?: string; competencia?: string;
  razao_social?: string; lancamentos?: number }

export function DadosEmpresaDialog({ aberto, aoVivo, portes, porteAtual, fonteAtual, aoFechar, aoExecutar }: {
  aberto: boolean; aoVivo: boolean; portes: Porte[]; porteAtual?: string; fonteAtual?: string; aoFechar: () => void;
  aoExecutar: (cmd: { porte?: string; fonte: "sintetico" | "planilha" }) => void;
}) {
  const [aba, setAba] = useState<"porte" | "planilha">(fonteAtual === "planilha" ? "planilha" : "porte");
  const [porte, setPorte] = useState(porteAtual ?? "media");
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [situacao, setSituacao] = useState<SituacaoDados | null>(null);
  const [envio, setEnvio] = useState<{ ok: boolean; erros: string[]; texto?: string } | null>(null);
  const [enviando, setEnviando] = useState(false);
  const arquivo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!aberto || !aoVivo) return;
    fetch("/api/modelos").then((r) => r.json()).then((d) => setModelos(d.modelos)).catch(() => setModelos([]));
    fetch("/api/dados").then((r) => r.json()).then(setSituacao).catch(() => setSituacao(null));
  }, [aberto, aoVivo]);
  useEffect(() => { if (porteAtual) setPorte(porteAtual); }, [porteAtual]);

  const enviar = async (f: File) => {
    setEnviando(true);
    setEnvio(null);
    const bytes = new Uint8Array(await f.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    const r = await postar("/api/dados/planilha", { nome: f.name, conteudo_base64: btoa(bin) });
    const d = await r.json();
    setEnviando(false);
    if (r.ok) {
      setEnvio({ ok: true, erros: [], texto: `${d.planilha}: ${d.razao_social || "empresa"} · porte ${d.porte} · `
        + `competência ${d.competencia} · ${d.lancamentos} lançamentos` });
      setSituacao({ planilha: d.planilha, porte: d.porte, competencia: d.competencia, razao_social: d.razao_social,
        lancamentos: d.lancamentos });
    } else {
      setEnvio({ ok: false, erros: d.erros ?? [d.erro ?? "erro desconhecido"] });
    }
  };

  return (
    <Dialog open={aberto} onClose={aoFechar} maxWidth="md" fullWidth aria-labelledby="titulo-dados">
      <DialogTitle id="titulo-dados">Dados da empresa</DialogTitle>
      <Tabs value={aba} onChange={(_, v) => setAba(v)} sx={{ px: 3, borderBottom: 1, borderColor: "divider" }}>
        <Tab value="porte" label="Empresa simulada (por porte)" />
        <Tab value="planilha" label="Minha empresa sem ERP (planilha)" />
      </Tabs>
      <DialogContent>
        {!aoVivo && <Alert severity="info" sx={{ mb: 2 }}>No replay offline os dados são os do trace gravado. Rode
          <code> python -m fin_mas serve</code> para trocar o porte ou usar a sua planilha.</Alert>}
        {aba === "porte" ? (
          <FormControl>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>As regras base (alçadas,
              severidades, materialidade, controles compensatórios) e os pesos dos desejos dos agentes BDI mudam com
              o porte. Fontes: LC 123/2006, BNDES, Lei 11.638/2007, ITG 1000, NBC TG 1000, NBC TA 320 e COSO 2013.</Typography>
            <RadioGroup value={porte} onChange={(e) => setPorte(e.target.value)} aria-label="Porte da empresa">
              {portes.map((p) => (
                <FormControlLabel key={p.porte} value={p.porte} control={<Radio />} label={
                  <span><b>{p.titulo}</b> — {p.norma_contabil}{p.tem_erp ? "" : " · sem ERP (planilhas)"}</span>} />
              ))}
            </RadioGroup>
          </FormControl>
        ) : (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              1) Baixe o modelo, 2) preencha no Excel (ou LibreOffice), 3) envie aqui. A planilha é validada antes
              de entrar; os agentes a leem pelo servidor MCP de Excel e as correções aprovadas são gravadas nela.
            </Typography>
            <Box>
              <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Modelos</Typography>
              <List dense disablePadding>
                {modelos.map((m) => (
                  <ListItem key={m.arquivo} disableGutters secondaryAction={
                    <Button size="small" startIcon={<DownloadIcon />} href={`/api/modelos/${m.arquivo}`}
                      download={m.arquivo}>Baixar</Button>}>
                    <ListItemText primary={m.arquivo} secondary={m.descricao} />
                  </ListItem>
                ))}
              </List>
            </Box>
            <Divider />
            <Box>
              <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Planilha atual</Typography>
              {situacao?.planilha ? (
                <Alert severity="success">{situacao.planilha} · {situacao.razao_social} · porte {situacao.porte} ·
                  competência {situacao.competencia} · {situacao.lancamentos} lançamentos</Alert>
              ) : <Alert severity="info">Nenhuma planilha válida enviada ainda.</Alert>}
            </Box>
            <input ref={arquivo} type="file" accept=".xlsx" hidden aria-label="Arquivo da planilha"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) enviar(f); e.target.value = ""; }} />
            <Button variant="outlined" startIcon={<CloudUploadIcon />} disabled={!aoVivo || enviando}
              onClick={() => arquivo.current?.click()}>Enviar planilha preenchida (.xlsx)</Button>
            {enviando && <LinearProgress />}
            {envio?.ok && <Alert severity="success">Planilha válida: {envio.texto}</Alert>}
            {envio && !envio.ok && (
              <Alert severity="error">
                A planilha tem {envio.erros.length} problema(s); nada foi substituído.
                <Box component="ul" sx={{ m: 0, pl: 2 }}>{envio.erros.slice(0, 12).map((e) => <li key={e}>{e}</li>)}</Box>
              </Alert>
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        {aba === "porte" ? (
          <Button variant="contained" disabled={!aoVivo} onClick={() => aoExecutar({ porte, fonte: "sintetico" })}>
            Reiniciar com este porte</Button>
        ) : (
          <Button variant="contained" disabled={!aoVivo || !situacao?.planilha}
            onClick={() => aoExecutar({ fonte: "planilha" })}>Executar com a minha planilha</Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

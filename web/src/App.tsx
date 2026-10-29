// Escritório da SMA (Material Design): agentes trabalhando ao vivo (servidor local) ou em replay offline.
import AddIcon from "@mui/icons-material/Add";
import BusinessIcon from "@mui/icons-material/Business";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import LightModeIcon from "@mui/icons-material/LightMode";
import NotificationsIcon from "@mui/icons-material/Notifications";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import ReplayIcon from "@mui/icons-material/Replay";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import SkipPreviousIcon from "@mui/icons-material/SkipPrevious";
import {
  Alert, AppBar, Avatar, Badge, Box, Button, Chip, CircularProgress, CssBaseline, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, IconButton, InputLabel, LinearProgress, MenuItem, Paper, Select, Slider,
  Snackbar, Stack, Tab, Tabs, ThemeProvider, Toolbar, Tooltip, Typography, useMediaQuery,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  carregarComparacao, carregarTrace, catalogoAoVivo, catalogoReplay, conectarAoVivo, enviarComando, estadoAoVivo,
  type Catalogo, type EventoAoVivo, type MenteSnapshot, type ResumoComparacao, type TraceExportado,
} from "./api/fonte";
import { Ajuda } from "./components/Ajuda";
import { Comparacao } from "./components/Comparacao";
import { DadosEmpresaDialog, FonteDialog, PeriodosDialog } from "./components/Dialogos";
import { DecisaoHumana } from "./components/DecisaoHumana";
import { COR_AGENTE, departamentoDe, Escritorio } from "./components/Escritorio";
import { Feed } from "./components/Feed";
import { PainelMente } from "./components/PainelMente";
import { useNovidadesAgentes } from "./state/novidades";
import { AGENTES, aplicarTodos, estadoInicial, statusDe } from "./state/reducer";
import type { Controle, FonteDados, Registro, Solicitacao, ViewState } from "./types";
import { criarTema, type ModoTema } from "./theme";

type Modo = "carregando" | "aovivo" | "replay";
type AbaPrincipal = "escritorio" | "comparacao";

function lerPreferencia(chave: string): string | null {
  try { return localStorage.getItem(chave); } catch { return null; }
}
function gravarPreferencia(chave: string, valor: string) {
  try { localStorage.setItem(chave, valor); } catch { /* sem armazenamento: só não lembra */ }
}

export default function App() {
  const sistemaEscuro = useMediaQuery("(prefers-color-scheme: dark)");
  const [temaEscolhido, setTemaEscolhido] = useState<ModoTema | null>(() => lerPreferencia("sma-tema") as ModoTema | null);
  const modoTema: ModoTema = temaEscolhido ?? (sistemaEscuro ? "dark" : "light");
  const tema = useMemo(() => criarTema(modoTema), [modoTema]);
  useEffect(() => { document.documentElement.dataset.theme = modoTema; }, [modoTema]);

  const [modo, setModo] = useState<Modo>("carregando");
  const [temServidor, setTemServidor] = useState(false);
  const [catalogo, setCatalogo] = useState<Catalogo | null>(null);
  const [comparacao, setComparacao] = useState<ResumoComparacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ajuda, setAjuda] = useState(() => lerPreferencia("sma-ajuda-vista") !== "1");

  useEffect(() => {
    (async () => {
      const vivo = await catalogoAoVivo();
      setComparacao(await carregarComparacao());
      if (vivo) {
        setCatalogo(vivo);
        setTemServidor(true);
        setModo("aovivo");
        return;
      }
      try {
        setCatalogo(await catalogoReplay());
        setModo("replay");
      } catch (e) {
        setErro(String(e));
      }
    })();
  }, []);

  const alternarTema = () => {
    const novo = modoTema === "dark" ? "light" : "dark";
    setTemaEscolhido(novo);
    gravarPreferencia("sma-tema", novo);
  };
  const fecharAjuda = () => { setAjuda(false); gravarPreferencia("sma-ajuda-vista", "1"); };
  const comum = { catalogo: catalogo!, comparacao, modoTema, alternarTema, abrirAjuda: () => setAjuda(true) };

  return (
    <ThemeProvider theme={tema}>
      <CssBaseline />
      {erro ? <Alert severity="error" sx={{ m: 3 }}>{erro}</Alert>
        : modo === "carregando" || !catalogo ? (
          <Stack alignItems="center" spacing={2} sx={{ mt: 10 }}><CircularProgress />
            <Typography color="text.secondary">Abrindo o escritório…</Typography></Stack>
        ) : modo === "aovivo"
          ? <AoVivo {...comum} aoTrocarModo={() => setModo("replay")} />
          : <Replay {...comum} aoTrocarModo={temServidor ? () => setModo("aovivo") : undefined} />}
      <Ajuda aberta={ajuda} aoFechar={fecharAjuda} />
    </ThemeProvider>
  );
}

interface TelaProps {
  catalogo: Catalogo;
  comparacao: ResumoComparacao | null;
  modoTema: ModoTema;
  alternarTema: () => void;
  abrirAjuda: () => void;
  aoTrocarModo?: () => void;
}

// ---------------------------------------------------------------- ao vivo
function AoVivo(p: TelaProps) {
  const [estado, setEstado] = useState<ViewState>(estadoInicial);
  const [controle, setControle] = useState<Controle | null>(null);
  const [geracao, setGeracao] = useState(0);
  const [conectado, setConectado] = useState(true);
  const [snapshots, setSnapshots] = useState<Record<string, MenteSnapshot>>({});
  const [aviso, setAviso] = useState<{ texto: string; grave?: boolean } | null>(null);
  const [aba, setAba] = useState<AbaPrincipal>("escritorio");
  const [selecionado, setSelecionado] = useState<string>("AG-ORC");
  const [decidindo, setDecidindo] = useState<string | null>(null);
  const [pedido, setPedido] = useState(false);
  const [dados, setDados] = useState(false);
  const [fonte, setFonte] = useState<FonteDados | null>(null);
  const [periodos, setPeriodos] = useState(false);
  const buffer = useRef<Registro[]>([]);
  const geracaoRef = useRef(0);

  useEffect(() => {
    const fechar = conectarAoVivo((ev: EventoAoVivo) => {
      setConectado(true);
      if (ev.tipo === "reset") {
        geracaoRef.current = ev.geracao;
        buffer.current = [];
        setEstado(estadoInicial());
        setGeracao(ev.geracao);
        setDecidindo(null);
      } else if (ev.tipo === "registro" && ev.geracao === geracaoRef.current) {
        buffer.current.push(ev.registro);
      } else if (ev.tipo === "controle") {
        setControle(ev.estado);
        if (ev.erro) setAviso({ texto: `Simulação pausada por erro: ${ev.erro}`, grave: true });
      }
    }, () => setConectado(false));
    const timer = setInterval(() => {
      if (!buffer.current.length) return;
      const lote = buffer.current;
      buffer.current = [];
      setEstado((s) => aplicarTodos(s, lote));
      const veto = lote.find((r) => r.kind === "ui" && r.performative === "veto_notice");
      if (veto) setAviso({ texto: `AG-CIN vetou ${(veto.content as { solicitacao: string }).solicitacao}: decisão humana pendente` });
    }, 80);
    return () => { fechar(); clearInterval(timer); };
  }, []);

  useEffect(() => {  // biblioteca de planos e conhecimento vêm do snapshot do servidor
    const carregar = async () => { const e = await estadoAoVivo(); if (e) setSnapshots(e.agentes); };
    carregar();
    const t = setInterval(carregar, 4000);
    return () => clearInterval(t);
  }, [geracao]);

  const cmd = useCallback(async (c: Record<string, unknown>) => {
    const e = await enviarComando(c);
    if (e) setAviso({ texto: e, grave: true });
  }, []);

  const novidades = useNovidadesAgentes(estado, selecionado, geracao);
  const pendentes = Object.values(estado.pendentes);
  const pendencia = pendentes.find((x) => x.solicitacao === decidindo);
  const velocidade = controle?.ms_por_tick ?? 350;

  return (
    <>
      <Topo {...p} modo="aovivo" aba={aba} setAba={setAba} conectado={conectado} pendentes={pendentes.length}
        aoAbrirPendencia={() => setDecidindo(pendentes[0]?.solicitacao ?? null)}>
        <FormControl size="small" sx={{ minWidth: 190 }}>
          <InputLabel id="cenario-vivo">Cenário</InputLabel>
          <Select labelId="cenario-vivo" label="Cenário" value={controle?.cenario ?? ""}
            onChange={(e) => cmd({ tipo: "reiniciar", cenario: e.target.value })}>
            {p.catalogo.cenarios.map((c) => <MenuItem key={c.nome} value={c.nome} title={c.descricao}>{c.nome}</MenuItem>)}
          </Select>
        </FormControl>
        <Tooltip title={controle?.pausado ? "Retomar a simulação" : "Pausar a simulação"}>
          <Button variant="contained" startIcon={controle?.pausado ? <PlayArrowIcon /> : <PauseIcon />}
            onClick={() => cmd({ tipo: controle?.pausado ? "retomar" : "pausar" })}>
            {controle?.pausado ? "Retomar" : "Pausar"}</Button>
        </Tooltip>
        <Tooltip title="Processa um único evento (com a simulação pausada)">
          <span><IconButton aria-label="Avançar um evento" onClick={() => cmd({ tipo: "passo" })}
            disabled={!controle?.pausado}><SkipNextIcon /></IconButton></span>
        </Tooltip>
        <Ritmo valor={1240 - velocidade} aoMudar={(v) => cmd({ tipo: "velocidade", ms_por_tick: 1240 - v })}
          min={20} max={1200} />
        <Tooltip title="Reinicia o cenário do zero (mesma seed)">
          <IconButton aria-label="Reiniciar cenário" onClick={() => cmd({ tipo: "reiniciar" })}><ReplayIcon /></IconButton>
        </Tooltip>
        <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setPedido(true)}>Novo pedido</Button>
        <Button variant="outlined" startIcon={<BusinessIcon />} onClick={() => setDados(true)}>Dados da empresa</Button>
        <EmpresaChip estado={estado} />
      </Topo>
      {aba === "escritorio" ? (
        <Corpo estado={estado} catalogo={p.catalogo} selecionado={selecionado} setSelecionado={setSelecionado}
          snapshots={snapshots} aoVivo chave={geracao} novidades={novidades}
          aoAbrirFonte={setFonte} aoAbrirPeriodos={() => setPeriodos(true)} aoNovoPedido={() => setPedido(true)}
          duracaoVoo={Math.min(1400, Math.max(350, velocidade * 1.6))}
          rodape={`t=${estado.t} · ${controle?.fila ?? 0} eventos na fila · seed ${controle?.seed ?? "?"}${
            controle?.offline.length ? ` · fora de operação: ${controle.offline.join(", ")}` : ""}`}
          aoAlternarEnergia={(id, online) => {
            cmd({ tipo: "agente", agente: id, online });
            setAviso({ texto: online ? `${id} religado` : `${id} desligado: mensagens a ele serão perdidas` });
          }} />
      ) : <Box sx={{ px: 2 }}><Comparacao resumo={p.comparacao} /></Box>}
      {pendencia && (
        <DecisaoHumana pendencia={pendencia} interativo={controle?.interativo ?? true} aoFechar={() => setDecidindo(null)}
          aoDecidir={(decisao, justificativa) => {
            cmd({ tipo: "decidir", solicitacao: pendencia.solicitacao, decisao, justificativa: justificativa || undefined });
            setDecidindo(null);
            setAviso({ texto: `Decisão "${decisao}" enviada para ${pendencia.solicitacao}` });
          }} />
      )}
      {fonte && <FonteDialog fonte={fonte} estado={estado} aoFechar={() => setFonte(null)}
        aoAbrirDados={() => { setFonte(null); setDados(true); }} />}
      {periodos && <PeriodosDialog estado={estado} aoFechar={() => setPeriodos(false)} />}
      <DadosEmpresaDialog aberto={dados} aoVivo portes={p.catalogo.portes ?? []} porteAtual={controle?.porte}
        fonteAtual={controle?.fonte} aoFechar={() => setDados(false)} aoExecutar={(c) => {
          cmd({ tipo: "reiniciar", cenario: controle?.cenario ?? "fechar_mes", ...c });
          setDados(false);
          setAviso({ texto: c.fonte === "planilha" ? "Escritório reiniciado com a planilha da empresa"
            : `Escritório reiniciado como ${c.porte}` });
        }} />
      <NovoPedido aberto={pedido} aoFechar={() => setPedido(false)} aoPedir={(intencao, competencia) => {
        cmd({ tipo: "solicitar", intencao, competencia });
        setPedido(false);
        setAviso({ texto: `Pedido enviado: ${intencao.replace("_", " ")} ${competencia}` });
      }} />
      <Snackbar open={!!aviso} autoHideDuration={aviso?.grave ? 8000 : 4000} onClose={() => setAviso(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}>
        <Alert onClose={() => setAviso(null)} severity={aviso?.grave ? "error" : "info"} variant="filled"
          action={pendentes.length && aviso?.texto.includes("pendente") ? (
            <Button color="inherit" size="small" onClick={() => { setDecidindo(pendentes[0].solicitacao); setAviso(null); }}>
              Decidir</Button>) : undefined}>
          {aviso?.texto}
        </Alert>
      </Snackbar>
    </>
  );
}

function NovoPedido({ aberto, aoFechar, aoPedir }: { aberto: boolean; aoFechar: () => void;
  aoPedir: (intencao: string, competencia: string) => void }) {
  const [intencao, setIntencao] = useState("fechar_mes");
  const [competencia, setCompetencia] = useState("2026-09");
  return (
    <Dialog open={aberto} onClose={aoFechar} aria-labelledby="titulo-pedido">
      <DialogTitle id="titulo-pedido">Novo pedido da liderança</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1, minWidth: 300 }}>
          <FormControl fullWidth>
            <InputLabel id="intencao">Intenção</InputLabel>
            <Select labelId="intencao" label="Intenção" value={intencao} onChange={(e) => setIntencao(e.target.value)}>
              <MenuItem value="fechar_mes">Fechar o mês</MenuItem>
              <MenuItem value="avaliar_orcamento">Avaliar orçamento</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel id="competencia">Competência</InputLabel>
            <Select labelId="competencia" label="Competência" value={competencia}
              onChange={(e) => setCompetencia(e.target.value)}>
              {["2026-07", "2026-08", "2026-09"].map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>
          <Typography variant="body2" color="text.secondary">Um fechamento do mesmo mês em andamento é recusado
            pela reserva de período (PROT-LCK).</Typography>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={aoFechar}>Cancelar</Button>
        <Button variant="contained" onClick={() => aoPedir(intencao, competencia)}>Enviar pedido</Button>
      </DialogActions>
    </Dialog>
  );
}

// ---------------------------------------------------------------- replay offline
function Replay(p: TelaProps) {
  const [nome, setNome] = useState("expediente_sma");
  const [trace, setTrace] = useState<TraceExportado | null>(null);
  const [tempo, setTempo] = useState(0);
  const [tocando, setTocando] = useState(true);
  const [msPorTick, setMsPorTick] = useState(450);
  const [aba, setAba] = useState<AbaPrincipal>("escritorio");
  const [selecionado, setSelecionado] = useState<string>("AG-ORC");
  const [decidindo, setDecidindo] = useState<string | null>(null);
  const [fonte, setFonte] = useState<FonteDados | null>(null);
  const [periodos, setPeriodos] = useState(false);
  const [dados, setDados] = useState(false);

  useEffect(() => {
    let vivo = true;
    carregarTrace(nome).then((t) => { if (vivo) { setTrace(t); setTempo(0); setTocando(true); } });
    return () => { vivo = false; };
  }, [nome]);

  const tMax = trace ? Math.max(...trace.registros.map((r) => r.t)) : 0;
  useEffect(() => {
    if (!tocando || !trace) return;
    const t = setInterval(() => setTempo((x) => {
      if (x >= tMax) { setTocando(false); return x; }
      return x + 1;
    }), msPorTick);
    return () => clearInterval(t);
  }, [tocando, msPorTick, tMax, trace]);

  // estado incremental: avança aplicando só os registros novos; volta reconstruindo do zero
  const cache = useRef<{ nome: string; ate: number; estado: ViewState } | null>(null);
  const estado = useMemo(() => {
    if (!trace) return estadoInicial();
    const c = cache.current;
    const base = c && c.nome === nome && c.ate <= tempo ? c : { nome, ate: -1, estado: estadoInicial() };
    const e = aplicarTodos(base.estado, trace.registros.filter((r) => r.t > base.ate && r.t <= tempo));
    cache.current = { nome, ate: tempo, estado: e };
    return e;
  }, [trace, tempo, nome]);

  const novidades = useNovidadesAgentes(estado, selecionado, nome);
  const pendentes = Object.values(estado.pendentes);
  const pendencia = pendentes.find((x) => x.solicitacao === decidindo);
  return (
    <>
      <Topo {...p} modo="replay" aba={aba} setAba={setAba} conectado pendentes={pendentes.length}
        aoAbrirPendencia={() => setDecidindo(pendentes[0]?.solicitacao ?? null)}>
        <FormControl size="small" sx={{ minWidth: 190 }}>
          <InputLabel id="cenario-replay">Cenário</InputLabel>
          <Select labelId="cenario-replay" label="Cenário" value={nome} onChange={(e) => setNome(e.target.value)}>
            {p.catalogo.cenarios.map((c) => <MenuItem key={c.nome} value={c.nome} title={c.descricao}>{c.nome}</MenuItem>)}
          </Select>
        </FormControl>
        <Button variant="contained" startIcon={tocando ? <PauseIcon /> : <PlayArrowIcon />}
          onClick={() => { if (tempo >= tMax) setTempo(0); setTocando(!tocando); }}>
          {tocando ? "Pausar" : "Reproduzir"}</Button>
        <Tooltip title="Voltar um tick"><IconButton aria-label="Voltar um tick"
          onClick={() => { setTocando(false); setTempo((x) => Math.max(0, x - 1)); }}><SkipPreviousIcon /></IconButton></Tooltip>
        <Tooltip title="Avançar um tick"><IconButton aria-label="Avançar um tick"
          onClick={() => { setTocando(false); setTempo((x) => Math.min(tMax, x + 1)); }}><SkipNextIcon /></IconButton></Tooltip>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 220 }}>
          <Typography variant="caption" sx={{ whiteSpace: "nowrap" }}>t={tempo}/{tMax}</Typography>
          <Slider size="small" min={0} max={tMax} value={tempo} aria-label="Tempo lógico"
            onChange={(_, v) => { setTocando(false); setTempo(v as number); }} />
        </Stack>
        <Ritmo valor={1260 - msPorTick} aoMudar={(v) => setMsPorTick(1260 - v)} min={60} max={1200} />
        <Button variant="outlined" startIcon={<BusinessIcon />} onClick={() => setDados(true)}>Dados da empresa</Button>
        <EmpresaChip estado={estado} />
      </Topo>
      {aba === "escritorio" ? (
        <Corpo estado={estado} catalogo={p.catalogo} selecionado={selecionado} setSelecionado={setSelecionado}
          snapshots={trace?.mentes_finais ?? {}} aoVivo={false} chave={nome} novidades={novidades}
          aoAbrirFonte={setFonte} aoAbrirPeriodos={() => setPeriodos(true)}
          duracaoVoo={Math.min(1400, Math.max(350, msPorTick * 1.6))}
          progresso={tMax ? (tempo / tMax) * 100 : 0}
          rodape={trace ? `${trace.cenario.descricao} · seed ${trace.cenario.seed} · hash ${trace.hash.slice(0, 12)}` : ""} />
      ) : <Box sx={{ px: 2 }}><Comparacao resumo={p.comparacao} /></Box>}
      {pendencia && <DecisaoHumana pendencia={pendencia} interativo={false} aoDecidir={() => undefined}
        aoFechar={() => setDecidindo(null)} />}
      {fonte && <FonteDialog fonte={fonte} estado={estado} aoFechar={() => setFonte(null)}
        aoAbrirDados={() => { setFonte(null); setDados(true); }} />}
      {periodos && <PeriodosDialog estado={estado} aoFechar={() => setPeriodos(false)} />}
      <DadosEmpresaDialog aberto={dados} aoVivo={false} portes={p.catalogo.portes ?? []}
        porteAtual={String(estado.meta?.porte ?? "media")} aoFechar={() => setDados(false)} aoExecutar={() => undefined} />
    </>
  );
}

// ---------------------------------------------------------------- partes comuns
function Ritmo({ valor, aoMudar, min, max }: { valor: number; aoMudar: (v: number) => void; min: number; max: number }) {
  return (
    <Tooltip title="Ritmo: quanto mais à direita, mais rápido passa o tempo lógico">
      <Stack direction="row" spacing={1} alignItems="center" sx={{ width: 150 }}>
        <Typography variant="caption">Ritmo</Typography>
        <Slider size="small" min={min} max={max} step={10} value={valor} aria-label="Ritmo da simulação"
          onChange={(_, v) => aoMudar(v as number)} />
      </Stack>
    </Tooltip>
  );
}

interface TopoProps extends TelaProps {
  modo: "aovivo" | "replay";
  aba: AbaPrincipal;
  setAba: (a: AbaPrincipal) => void;
  conectado: boolean;
  pendentes: number;
  aoAbrirPendencia: () => void;
  children: React.ReactNode;
}

function Topo({ catalogo, modo, aba, setAba, aoTrocarModo, conectado, pendentes, aoAbrirPendencia, modoTema,
  alternarTema, abrirAjuda, children }: TopoProps) {
  return (
    <AppBar position="sticky" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: "divider",
      bgcolor: "background.default" }}>
      <Toolbar sx={{ gap: 2, flexWrap: "wrap", py: 1 }}>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mr: "auto" }}>
          <Avatar src="/sma-logo.svg" alt="SMA" variant="rounded" sx={{ width: 40, height: 40 }} />
          <Box>
            <Typography variant="h1" component="h1">{catalogo.empresa.razao_social} · Escritório de controladoria</Typography>
            <Typography variant="caption" color="text.secondary">Sistema multiagente · empresa e dados fictícios</Typography>
          </Box>
          <Tooltip title={modo === "aovivo" ? "Agentes executando agora no servidor local"
            : "Reprodução de um trace exportado, sem servidor"}>
            <Chip size="small" color={modo === "aovivo" ? (conectado ? "success" : "warning") : "default"}
              variant="outlined" label={modo === "aovivo" ? (conectado ? "● ao vivo" : "reconectando…") : "replay offline"} />
          </Tooltip>
          {aoTrocarModo && <Button size="small" onClick={aoTrocarModo}>{modo === "aovivo" ? "Ver replay" : "Voltar ao vivo"}</Button>}
        </Stack>
        <Tabs value={aba} onChange={(_, v) => setAba(v)} aria-label="Seções">
          <Tab value="escritorio" label="Escritório" />
          <Tab value="comparacao" label="SMA × workflow" />
        </Tabs>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title={pendentes ? `${pendentes} decisão(ões) humana(s) pendente(s): clique para decidir`
            : "Nenhuma decisão humana pendente"}>
            <span>
              <IconButton aria-label="Decisões humanas pendentes" onClick={aoAbrirPendencia} disabled={!pendentes}>
                <Badge badgeContent={pendentes} color="error"><NotificationsIcon /></Badge>
              </IconButton>
            </span>
          </Tooltip>
          <Tooltip title={modoTema === "dark" ? "Tema claro" : "Tema escuro"}>
            <IconButton aria-label="Alternar tema" onClick={alternarTema}>
              {modoTema === "dark" ? <LightModeIcon /> : <DarkModeIcon />}</IconButton>
          </Tooltip>
          <Tooltip title="Como usar"><IconButton aria-label="Como usar" onClick={abrirAjuda}><HelpOutlineIcon /></IconButton></Tooltip>
        </Stack>
      </Toolbar>
      <Toolbar variant="dense" sx={{ gap: 1.5, flexWrap: "wrap", py: 1, borderTop: 1, borderColor: "divider" }}>
        {children}
      </Toolbar>
    </AppBar>
  );
}

interface CorpoProps {
  estado: ViewState;
  catalogo: Catalogo;
  selecionado: string;
  setSelecionado: (id: string) => void;
  snapshots: Record<string, MenteSnapshot>;
  aoVivo: boolean;
  chave: string | number;
  duracaoVoo: number;
  rodape: string;
  novidades: Record<string, number>;
  progresso?: number;
  aoAlternarEnergia?: (id: string, online: boolean) => void;
  aoAbrirFonte: (f: FonteDados) => void;
  aoAbrirPeriodos: () => void;
  aoNovoPedido?: () => void;
}

function Corpo({ estado, catalogo, selecionado, setSelecionado, snapshots, aoVivo, chave, duracaoVoo, rodape,
  novidades, progresso, aoAlternarEnergia, aoAbrirFonte, aoAbrirPeriodos, aoNovoPedido }: CorpoProps) {
  return (
    <Box component="main" sx={{ display: "grid", gap: 2, p: 2, maxWidth: 1720, mx: "auto",
      gridTemplateColumns: { xs: "minmax(0,1fr)", lg: "minmax(0,1fr) 460px" },
      gridTemplateAreas: { xs: '"agentes" "principal" "lateral" "feed"', lg: '"agentes agentes" "principal lateral" "feed lateral"' } }}>
      <Box sx={{ gridArea: "agentes" }}>
        <BarraAgentes estado={estado} catalogo={catalogo} selecionado={selecionado} aoSelecionar={setSelecionado}
          novidades={novidades} aoAlternarEnergia={aoAlternarEnergia} />
      </Box>
      <Stack spacing={2} sx={{ gridArea: "principal", minWidth: 0 }}>
        <Paper sx={{ p: 0.75, overflow: "hidden" }}>
          {progresso !== undefined && <LinearProgress variant="determinate" value={progresso} sx={{ mb: 0.5 }} />}
          <Escritorio key={chave} estado={estado} fichas={catalogo.agentes} selecionado={selecionado}
            aoSelecionar={setSelecionado} duracaoVoo={duracaoVoo} novidades={novidades} aoAbrirFonte={aoAbrirFonte}
            aoAbrirPeriodos={aoAbrirPeriodos} />
          <Typography variant="caption" color="text.secondary" sx={{ px: 1 }}>{rodape}</Typography>
        </Paper>
        <Pedidos lista={Object.values(estado.solicitacoes)} />
      </Stack>
      <Box sx={{ gridArea: "lateral", minWidth: 0 }}>
        <PainelMente key={selecionado} id={selecionado} estado={estado} ficha={catalogo.agentes[selecionado]}
          snapshot={snapshots[selecionado]} aoVivo={aoVivo} aoAlternarEnergia={aoAlternarEnergia}
          aoNovoPedido={aoNovoPedido} />
      </Box>
      <Box sx={{ gridArea: "feed", minWidth: 0 }}><Feed registros={estado.registros} agente={selecionado} /></Box>
    </Box>
  );
}

const ROTULO_STATUS: Record<string, string> = {
  trabalhando: "trabalhando", aguardando: "aguardando", ocioso: "ocioso", vetando: "vetando", fora: "fora",
};

function BarraAgentes({ estado, catalogo, selecionado, aoSelecionar, novidades, aoAlternarEnergia }: {
  estado: ViewState; catalogo: Catalogo; selecionado: string; aoSelecionar: (id: string) => void;
  novidades: Record<string, number>; aoAlternarEnergia?: (id: string, online: boolean) => void }) {
  return (
    <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap" component="nav" aria-label="Agentes">
      {AGENTES.map((id) => {
        const st = statusDe(estado, id);
        const n = id === "APR" ? Object.keys(estado.pendentes).length : novidades[id] ?? 0;
        const desligavel = aoAlternarEnergia && id.startsWith("AG-") && id !== "AG-ORQ";
        return (
          <Stack key={id} direction="row" alignItems="center" spacing={0.25}>
            <Tooltip describeChild title={`${catalogo.agentes[id]?.titulo ?? id} · ${ROTULO_STATUS[st]}${n ? ` · ${n} ${id === "APR"
              ? "decisão(ões) pendente(s)" : "novidade(s) não vista(s)"}` : ""}`}>
              <Badge badgeContent={n} max={99} color={id === "APR" ? "error" : "secondary"} overlap="rectangular">
                <Chip clickable onClick={() => aoSelecionar(id)} variant={selecionado === id ? "filled" : "outlined"}
                  color={selecionado === id ? "primary" : "default"}
                  avatar={<Avatar aria-hidden sx={{ bgcolor: COR_AGENTE[id], color: "#fff !important" }}>{id.replace("AG-", "")[0]}</Avatar>}
                  label={<span><b>{id}</b> · {departamentoDe(id, catalogo.agentes[id])}
                    <Box component="span" sx={{ ml: 0.75, color: st === "fora" || st === "vetando" ? "error.main"
                      : st === "trabalhando" ? "success.main" : "text.secondary" }}>● {ROTULO_STATUS[st]}</Box></span>} />
              </Badge>
            </Tooltip>
            {desligavel && (
              <Tooltip title={st === "fora" ? `Religar ${id}` : `Desligar ${id} (simular falha)`}>
                <IconButton size="small" aria-label={st === "fora" ? `Religar ${id}` : `Desligar ${id}`}
                  color={st === "fora" ? "error" : "default"} onClick={() => aoAlternarEnergia(id, st === "fora")}>
                  <PowerSettingsNewIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Stack>
        );
      })}
    </Stack>
  );
}

function EmpresaChip({ estado }: { estado: ViewState }) {
  const m = estado.meta;
  if (!m) return null;
  const planilha = m.fonte === "planilha";
  return (
    <Tooltip describeChild title={planilha ? `Dados da planilha ${String(m.arquivo ?? "")}` : "Empresa simulada (dados sintéticos com gabarito)"}>
      <Chip variant="outlined" color={planilha ? "secondary" : "default"}
        label={`${String(m.porte_titulo ?? m.porte ?? "")} · ${m.tem_erp === false ? "sem ERP" : "ERP"}${planilha ? " · planilha real" : ""}`} />
    </Tooltip>
  );
}

const ROTULO_PEDIDO: Record<string, string> = {
  aguardando: "na fila", em_execucao: "em execução", publicado: "publicado", publicado_com_ressalva: "publicado c/ ressalva",
  bloqueado: "bloqueado (veto)", falhou: "falhou", recusado: "recusado",
};
const COR_PEDIDO: Record<string, "default" | "info" | "success" | "warning" | "error"> = {
  aguardando: "default", em_execucao: "info", publicado: "success", publicado_com_ressalva: "warning",
  bloqueado: "error", falhou: "error", recusado: "error",
};

function Pedidos({ lista }: { lista: Solicitacao[] }) {
  if (!lista.length) return null;
  const andamento = lista.filter((s) => s.status === "em_execucao" || s.status === "aguardando").length;
  return (
    <Paper component="section" aria-label="Pedidos da liderança" sx={{ p: 2 }}>
      <Badge badgeContent={andamento} color="info" sx={{ mb: 1.5, pr: 1.5 }}>
        <Typography variant="h2" component="h2">Pedidos da liderança</Typography>
      </Badge>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {lista.map((s) => (
          <Tooltip describeChild key={s.sid} title={s.detalhe ?? ROTULO_PEDIDO[s.status] ?? s.status}>
            <Chip variant="outlined" color={COR_PEDIDO[s.status] ?? "default"}
              label={<span><b>{s.sid}</b> {s.intencao.replace("_", " ")} {s.competencia} · {ROTULO_PEDIDO[s.status] ?? s.status}</span>} />
          </Tooltip>
        ))}
      </Stack>
    </Paper>
  );
}

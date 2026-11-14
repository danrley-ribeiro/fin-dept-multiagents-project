// Áreas de trabalho do escritório (ADR-009): onde as pessoas usam a plataforma, cada uma com o que os papéis dela permitem.
// Solicitações e relatórios, fila de aprovações, logs com filtros e explicação de decisões, agentes e LLM, ficha do porte.
import DownloadIcon from "@mui/icons-material/Download";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControl,
  FormControlLabel, IconButton, InputLabel, MenuItem, Paper, Select, Stack, Switch, Table, TableBody, TableCell,
  TableHead, TableRow, TextField, Tooltip, Typography,
} from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";
import { definirSegredo, removerSegredo, type ChaveProvedor, type Segredos } from "../api/avancado";
import { ler, pode, type Sessao } from "../api/sessao";

type Json = Record<string, unknown>;
const NIVEIS: [string, string][] = [["basico", "Básico (ciclo BDI, sem hipóteses)"],
  ["local", "Local (regras locais propõem hipóteses, offline)"], ["llm", "Local + LLM opcional"]];

function useRota<T>(rota: string | null, intervalo = 0): { dados: T | null; erro: string | null; recarregar: () => void } {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const recarregar = useCallback(() => {
    if (!rota) return;
    ler<T>(rota).then((r) => { if (r.dados) { setDados(r.dados); setErro(null); } else if (r.status !== 401) setErro(r.erro ?? "erro"); });
  }, [rota]);
  useEffect(() => {
    recarregar();
    if (!intervalo) return;
    const t = setInterval(recarregar, intervalo);
    return () => clearInterval(t);
  }, [recarregar, intervalo]);
  return { dados, erro, recarregar };
}

function Secao({ titulo, children, acoes }: { titulo: string; children: React.ReactNode; acoes?: React.ReactNode }) {
  return (
    <Paper component="section" aria-label={titulo} sx={{ p: 2, maxWidth: 1400, mx: "auto", my: 2 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }} useFlexGap flexWrap="wrap">
        <Typography variant="h2" component="h2" sx={{ mr: "auto" }}>{titulo}</Typography>
        {acoes}
      </Stack>
      {children}
    </Paper>
  );
}

// ---------------------------------------------------------------- solicitações e relatórios
interface SolicitacaoApi { id: string; intencao: string; competencia: string; solicitado_por: string | null;
  performativo: string | null; status: string; motivo: string | null; ressalvas: string[] }
interface RelatorioApi { id: string; status: string; relatorio: string; ressalvas: string[]; notas: string[];
  insights?: string[] }

export function Solicitacoes({ sessao, aoNovoPedido }: { sessao: Sessao; aoNovoPedido: () => void }) {
  const { dados, erro } = useRota<{ solicitacoes: SolicitacaoApi[] }>("/api/solicitacoes", 1500);
  const [aberto, setAberto] = useState<string | null>(null);
  const relatorio = useRota<RelatorioApi>(aberto ? `/api/relatorios/${aberto}` : null);
  return (
    <Secao titulo="Solicitações e relatórios" acoes={
      <Tooltip title={pode(sessao, "PERM-SOL-CRIAR") ? "Pedir fechamento do mês ou avaliação orçamentária"
        : "Sua conta não tem o papel de solicitante"}>
        <span><Button variant="contained" onClick={aoNovoPedido} disabled={!pode(sessao, "PERM-SOL-CRIAR")}>
          Nova solicitação</Button></span>
      </Tooltip>}>
      {erro && <Alert severity="error">{erro}</Alert>}
      <Table size="small" aria-label="Solicitações">
        <TableHead><TableRow><TableCell>Pedido</TableCell><TableCell>O quê</TableCell><TableCell>Competência</TableCell>
          <TableCell>Pedido por</TableCell><TableCell>Situação</TableCell><TableCell>Relatório</TableCell></TableRow></TableHead>
        <TableBody>
          {(dados?.solicitacoes ?? []).map((s) => (
            <TableRow key={s.id}>
              <TableCell><b>{s.id}</b></TableCell>
              <TableCell>{s.intencao?.replace("_", " ")}</TableCell>
              <TableCell>{s.competencia}</TableCell>
              <TableCell>{s.solicitado_por ?? "roteiro do cenário"}</TableCell>
              <TableCell>
                <Chip size="small" label={s.status.replace(/_/g, " ")} color={s.performativo === "inform" ? "success"
                  : s.performativo === null ? "info" : "error"} variant="outlined" />
                {s.motivo && <Typography variant="caption" color="text.secondary" component="div">{s.motivo}</Typography>}
              </TableCell>
              <TableCell>{s.performativo === "inform"
                ? <Button size="small" onClick={() => setAberto(s.id)}>Ver relatório</Button> : "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!dados?.solicitacoes.length && <Typography color="text.secondary" sx={{ mt: 1 }}>Nenhuma solicitação ainda.</Typography>}
      <Dialog open={!!aberto} onClose={() => setAberto(null)} maxWidth="md" fullWidth aria-labelledby="titulo-relatorio">
        <DialogTitle id="titulo-relatorio">Relatório de {aberto}</DialogTitle>
        <DialogContent dividers>
          {relatorio.erro && <Alert severity="error">{relatorio.erro}</Alert>}
          {relatorio.dados && (
            <Box component="pre" aria-label="Texto do relatório" sx={{ whiteSpace: "pre-wrap", fontFamily: "inherit",
              fontSize: 14, m: 0 }}>{relatorio.dados.relatorio}</Box>)}
        </DialogContent>
        <DialogActions>
          <Button startIcon={<DownloadIcon />} component="a" href={`/api/relatorios/${aberto}?formato=html`}>Baixar HTML</Button>
          <Button startIcon={<DownloadIcon />} component="a" href={`/api/relatorios/${aberto}?formato=txt`}>Baixar texto</Button>
          <Button onClick={() => setAberto(null)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </Secao>
  );
}

// ---------------------------------------------------------------- aprovações
interface AprovacaoApi { id: string; solicitacao: string; competencia: string; estado: string; classe: string;
  opcoes: string[]; achados: { regra: string; lancamento: string; severidade: string }[]; emitido_em: number;
  expira_em: number; solicitado_por: string | null; decisao: string | null; aguardando: boolean;
  aprovado_por: { pessoa: string; titulo: string } | null; justificativa: string | null; impedimento: string | null;
  decisoes_do_cargo: string[] }

export function Aprovacoes({ sessao, aoDecidir }: { sessao: Sessao; aoDecidir: (solicitacao: string) => void }) {
  const { dados, erro } = useRota<{ t: number; aprovacoes: AprovacaoApi[] }>("/api/aprovacoes", 1500);
  const lista = dados?.aprovacoes ?? [];
  const fila = lista.filter((a) => a.estado === "pendente");
  const historico = lista.filter((a) => a.estado !== "pendente").reverse();
  return (
    <Secao titulo="Central de aprovações">
      {erro && <Alert severity="error">{erro}</Alert>}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Você entrou como <b>{sessao.usuario}</b>{sessao.cargo ? ` (${sessao.cargo})` : ""}. A decisão fica registrada com
        o seu nome; quem criou ou aprovou o lançamento vetado, ou fez o pedido, não decide sobre ele.
      </Typography>
      <Typography variant="h3" component="h3">Aguardando decisão ({fila.length})</Typography>
      {!fila.length && <Typography color="text.secondary" sx={{ my: 1 }}>Nenhum veto aguardando decisão.</Typography>}
      <Stack spacing={1} sx={{ my: 1 }}>
        {fila.map((a) => (
          <Card key={a.id} variant="outlined" aria-label={`Ticket ${a.id}`}>
            <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
                <Typography variant="body1"><b>{a.id}</b> · {a.solicitacao} · {a.competencia}</Typography>
                <Chip size="small" color="warning" label={`prazo: ${Math.max(0, a.expira_em - (dados?.t ?? 0))} ticks`} />
                {a.solicitado_por && <Chip size="small" variant="outlined" label={`pedido por ${a.solicitado_por}`} />}
                <Box sx={{ flex: 1 }} />
                <Tooltip title={a.impedimento ?? "Abrir o veto para decidir"}>
                  <span><Button variant="contained" size="small" disabled={!!a.impedimento || !a.aguardando}
                    onClick={() => aoDecidir(a.solicitacao)}>Decidir</Button></span>
                </Tooltip>
              </Stack>
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {a.achados.map((x) => `${x.regra} em ${x.lancamento} (${x.severidade})`).join("; ")}
              </Typography>
              {a.impedimento && <Alert severity="warning" sx={{ mt: 1, py: 0 }}>{a.impedimento}</Alert>}
            </CardContent>
          </Card>
        ))}
      </Stack>
      <Typography variant="h3" component="h3">Histórico</Typography>
      <Table size="small" aria-label="Histórico de aprovações">
        <TableHead><TableRow><TableCell>Ticket</TableCell><TableCell>Pedido</TableCell><TableCell>Situação</TableCell>
          <TableCell>Decisão</TableCell><TableCell>Quem decidiu</TableCell><TableCell>Justificativa</TableCell></TableRow></TableHead>
        <TableBody>
          {historico.map((a) => (
            <TableRow key={a.id}><TableCell>{a.id}</TableCell><TableCell>{a.solicitacao}</TableCell>
              <TableCell>{a.estado}</TableCell><TableCell>{a.decisao ?? "—"}</TableCell>
              <TableCell>{a.aprovado_por ? `${a.aprovado_por.pessoa} (${a.aprovado_por.titulo})` : "—"}</TableCell>
              <TableCell>{a.justificativa ?? "—"}</TableCell></TableRow>
          ))}
        </TableBody>
      </Table>
    </Secao>
  );
}

// ---------------------------------------------------------------- logs
interface Auditoria { total: number; registros: (Json & { seq: number; t: number; kind: string })[]; textos: string[];
  custos: Record<string, { chamadas: number; tokens: number; custo_usd: number; fallbacks?: number }> }
interface Explicacao { alvo: { texto: string }; agente: string; tarefa: string;
  cadeia: { seq: number; papel: string; texto: string }[] }

const TIPOS = ["", "decision", "belief", "hipotese", "deliberation", "intention", "desire", "send", "open", "rejected",
  "politica", "mcp_call", "operador", "llm_prompt", "llm_custo", "llm_fallback", "drop", "timeout", "memoria"];

const SEM_FILTRO = { agente: "", tipo: "", tarefa: "", competencia: "", de_t: "", ate_t: "", custo_min: "", q: "" };
const consultaDe = (f: Record<string, string>) => new URLSearchParams(Object.entries(f).filter(([, v]) => v !== "")).toString();

/** `filtroInicial`: a demonstração guiada abre os logs já filtrados e acompanhando o cenário (atualiza sozinho). */
export function Logs({ sessao, filtroInicial }: { sessao: Sessao; filtroInicial?: Record<string, string> }) {
  const [f, setF] = useState({ ...SEM_FILTRO, ...filtroInicial });
  const [consulta, setConsulta] = useState(() => consultaDe({ ...SEM_FILTRO, ...filtroInicial }));
  const { dados, erro, recarregar } = useRota<Auditoria>(`/api/auditoria?limite=400&${consulta}`, filtroInicial ? 2000 : 0);
  const [explicar, setExplicar] = useState<number | null>(null);
  const explicacao = useRota<Explicacao>(explicar !== null ? `/api/explicar?seq=${explicar}` : null);
  const [conversa, setConversa] = useState<string | null>(null);
  const sequencia = useRota<{ mermaid: string }>(conversa ? `/api/sequencia?conversa=${encodeURIComponent(conversa)}` : null);
  const montar = () => consultaDe(f);
  const campo = (nome: keyof typeof f, rotulo: string, largura = 130) => (
    <TextField size="small" label={rotulo} value={f[nome]} sx={{ width: largura }}
      onChange={(e) => setF({ ...f, [nome]: e.target.value })} inputProps={{ "aria-label": rotulo }} />);
  return (
    <Secao titulo="Logs e auditoria" acoes={<>
      <Tooltip title={pode(sessao, "PERM-AUD-EXPORTAR") ? "Baixa o recorte filtrado em JSONL"
        : "Exportar exige o papel de auditor ou de administrador"}>
        <span><Button startIcon={<DownloadIcon />} component="a" href={`/api/auditoria/exportar?${consulta}`}
          disabled={!pode(sessao, "PERM-AUD-EXPORTAR")}>Exportar</Button></span>
      </Tooltip>
      <IconButton aria-label="Atualizar logs" onClick={recarregar}><RefreshIcon /></IconButton></>}>
      <Stack component="form" direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 1.5 }}
        onSubmit={(e) => { e.preventDefault(); setConsulta(montar()); }}>
        <FormControl size="small" sx={{ width: 130 }}>
          <InputLabel id="log-agente">Agente</InputLabel>
          <Select labelId="log-agente" label="Agente" value={f.agente} onChange={(e) => setF({ ...f, agente: e.target.value })}>
            {["", "AG-ORQ", "AG-CUS", "AG-ORC", "AG-RES", "AG-CIN", "AG-REL", "SOL", "APR", "SVC-POL"].map((a) =>
              <MenuItem key={a} value={a}>{a || "todos"}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ width: 150 }}>
          <InputLabel id="log-tipo">Tipo</InputLabel>
          <Select labelId="log-tipo" label="Tipo" value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value })}>
            {TIPOS.map((t) => <MenuItem key={t} value={t}>{t || "todos"}</MenuItem>)}
          </Select>
        </FormControl>
        {campo("tarefa", "Tarefa (ex.: SOL-001)", 170)}{campo("competencia", "Competência", 120)}
        {campo("de_t", "De t", 80)}{campo("ate_t", "Até t", 80)}{campo("custo_min", "Custo mín. (US$)", 140)}
        {campo("q", "Buscar texto", 170)}
        <Button type="submit" variant="contained">Filtrar</Button>
      </Stack>
      {erro && <Alert severity="error" role="alert">{erro}</Alert>}
      <Typography variant="caption" color="text.secondary" aria-label="Total de registros">
        {dados ? `${dados.total} registro(s)${dados.total > dados.registros.length ? ` (mostrando os últimos ${dados.registros.length})` : ""}` : "…"}
      </Typography>
      <Box sx={{ maxHeight: 520, overflow: "auto", mt: 0.5 }}>
        <Table size="small" stickyHeader aria-label="Registros do trace">
          <TableHead><TableRow><TableCell>#</TableCell><TableCell>t</TableCell><TableCell>Tipo</TableCell>
            <TableCell>Conversa</TableCell><TableCell>Registro</TableCell><TableCell /></TableRow></TableHead>
          <TableBody>
            {(dados?.registros ?? []).map((r, i) => (
              <TableRow key={r.seq} hover>
                <TableCell>{r.seq}</TableCell><TableCell>{r.t}</TableCell><TableCell>{r.kind}</TableCell>
                <TableCell>{r.conversation_id
                  ? <Button size="small" sx={{ minWidth: 0, p: 0 }} onClick={() => setConversa(String(r.conversation_id))}>
                    {String(r.conversation_id)}</Button> : "—"}</TableCell>
                <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{(dados?.textos[i] ?? "").replace(/^t=\d+ #\d+ \S+\s+/, "")}</TableCell>
                <TableCell><Tooltip title="Por quê? Mostra o que levou a este registro">
                  <IconButton size="small" aria-label={`Explicar o registro ${r.seq}`} onClick={() => setExplicar(r.seq)}>
                    <HelpOutlineIcon fontSize="small" /></IconButton></Tooltip></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <Dialog open={explicar !== null} onClose={() => setExplicar(null)} maxWidth="md" fullWidth aria-labelledby="titulo-explicar">
        <DialogTitle id="titulo-explicar">Por quê? Registro {explicar}</DialogTitle>
        <DialogContent dividers>
          {explicacao.erro && <Alert severity="error">{explicacao.erro}</Alert>}
          {explicacao.dados && (<>
            <Typography variant="body2" sx={{ mb: 1 }}>{explicacao.dados.alvo.texto}</Typography>
            <Typography variant="caption" color="text.secondary">Agente {explicacao.dados.agente} · tarefa {explicacao.dados.tarefa}.
              A cadeia abaixo são os próprios registros do trace, na ordem em que aconteceram.</Typography>
            <Table size="small" aria-label="Cadeia da decisão">
              <TableBody>
                {explicacao.dados.cadeia.map((c) => (
                  <TableRow key={c.seq}><TableCell sx={{ whiteSpace: "nowrap" }}><Chip size="small" label={c.papel} /></TableCell>
                    <TableCell sx={{ fontFamily: "monospace", fontSize: 12 }}>{c.texto}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table></>)}
        </DialogContent>
        <DialogActions><Button onClick={() => setExplicar(null)}>Fechar</Button></DialogActions>
      </Dialog>
      <Dialog open={!!conversa} onClose={() => setConversa(null)} maxWidth="md" fullWidth aria-labelledby="titulo-sequencia">
        <DialogTitle id="titulo-sequencia">Sequência de mensagens · {conversa}</DialogTitle>
        <DialogContent dividers>
          {sequencia.erro && <Alert severity="error">{sequencia.erro}</Alert>}
          <Box component="ol" aria-label="Diagrama de sequência" sx={{ fontFamily: "monospace", fontSize: 13, pl: 3, m: 0 }}>
            {(sequencia.dados?.mermaid ?? "").split("\n").filter((l) => l.includes("->>") || l.includes("--x") || l.includes("Note over"))
              .map((l, i) => <li key={i}>{l.trim().replace("->>", " → ").replace("--x", " ✕ ").replace(/_/g, "-")}</li>)}
          </Box>
          <Typography variant="caption" color="text.secondary">Fonte do diagrama em Mermaid:
            <code> python -m fin_mas sequencia TRACE {conversa}</code></Typography>
        </DialogContent>
        <DialogActions><Button onClick={() => setConversa(null)}>Fechar</Button></DialogActions>
      </Dialog>
    </Secao>
  );
}

// ---------------------------------------------------------------- agentes e LLM
interface AgenteLLM { llm: boolean; modelo: string; provedor: string | null; base_url: string | null; usos: string[];
  cota_tokens: number; max_tokens: number; usado: number; consentimento_externo: boolean; disjuntor_aberto: boolean }
interface LLMApi { agentes: Record<string, AgenteLLM>; cognicao: string; nao_permitidos: string[];
  provedores: { id: string; variavel_chave: string | null; tem_chave: boolean; chave_opcional: boolean; externo: boolean;
    exige_base_url: boolean }[]; usos: Record<string, string[]>;
  custos: Record<string, { chamadas: number; tokens: number; custo_usd: number; fallbacks?: number; sem_preco: number }> }

const MODELOS_MOCK = ["mock-analista", "mock-narrador", "mock-analista-ruim", "mock-json-invalido", "mock-injetado",
  "mock-alucina", "mock-acao"];

export function ConfigLLM({ sessao, aoComando, cenario }: { sessao: Sessao; cenario: string;
  aoComando: (c: Record<string, unknown>) => void }) {
  // quem só define segredos (administrador de acesso) abre a área sem consultar a configuração dos agentes
  const ve = pode(sessao, "PERM-MOD-VER");
  const { dados, erro, recarregar } = useRota<LLMApi>(ve ? "/api/llm" : null, 2500);
  const edita = pode(sessao, "PERM-MOD-CONFIG");
  const opera = pode(sessao, "PERM-SIM-OPERAR");
  const segredos = pode(sessao, "PERM-MOD-SEGREDOS");
  const [rascunho, setRascunho] = useState<Record<string, Partial<AgenteLLM>>>({});
  if (erro) return <Secao titulo="Agentes e LLM"><Alert severity="error">{erro}</Alert></Secao>;
  if (ve && !dados) return null;
  return (
    <Secao titulo="Agentes e LLM">
      {dados && (<>
      <Stack direction="row" spacing={2} alignItems="center" useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 340 }}>
          <InputLabel id="nivel-cognicao">Nível de cognição</InputLabel>
          <Select labelId="nivel-cognicao" label="Nível de cognição" value={dados.cognicao} disabled={!opera}
            onChange={(e) => aoComando({ tipo: "reiniciar", cenario, cognicao: e.target.value })}>
            {NIVEIS.map(([v, r]) => <MenuItem key={v} value={v}>{r}</MenuItem>)}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
          Mudar o nível reinicia o cenário. O LLM é opcional e vem desligado: ele só propõe hipóteses e redige textos,
          que o agente valida. {dados.nao_permitidos.join(", ")} nunca usam LLM (NORM-07).
        </Typography>
      </Stack>
      <Stack spacing={1.5}>
        {Object.entries(dados.agentes).map(([id, atual]) => {
          const a = { ...atual, ...rascunho[id] } as AgenteLLM;
          const provedor = dados.provedores.find((p) => p.id === (a.provedor ?? "mock"));
          const mudar = (campos: Partial<AgenteLLM>) => setRascunho({ ...rascunho, [id]: { ...rascunho[id], ...campos } });
          const custo = dados.custos[id];
          return (
            <Card key={id} variant="outlined" aria-label={`LLM de ${id}`}>
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack direction="row" spacing={1.5} alignItems="center" useFlexGap flexWrap="wrap">
                  <Typography variant="body1" sx={{ minWidth: 70 }}><b>{id}</b></Typography>
                  <FormControlLabel label={a.llm ? "LLM ligado" : "LLM desligado"} control={
                    <Switch checked={a.llm} disabled={!edita} onChange={(e) => mudar({ llm: e.target.checked })}
                      inputProps={{ "aria-label": `Ligar LLM de ${id}` }} />} />
                  <FormControl size="small" sx={{ width: 170 }}>
                    <InputLabel id={`prov-${id}`}>Provedor</InputLabel>
                    <Select labelId={`prov-${id}`} label="Provedor" value={a.provedor ?? "mock"} disabled={!edita}
                      onChange={(e) => mudar({ provedor: e.target.value, modelo: e.target.value === "mock" ? MODELOS_MOCK[0] : "" })}>
                      {dados.provedores.map((p) => <MenuItem key={p.id} value={p.id}>{p.id}{p.externo ? " (externo)" : ""}</MenuItem>)}
                    </Select>
                  </FormControl>
                  {(a.provedor ?? "mock") === "mock" ? (
                    <FormControl size="small" sx={{ width: 200 }}>
                      <InputLabel id={`mod-${id}`}>Modelo</InputLabel>
                      <Select labelId={`mod-${id}`} label="Modelo" value={MODELOS_MOCK.includes(a.modelo) ? a.modelo : MODELOS_MOCK[0]}
                        disabled={!edita} onChange={(e) => mudar({ modelo: e.target.value })}>
                        {MODELOS_MOCK.map((m) => <MenuItem key={m} value={m}>{m}</MenuItem>)}
                      </Select>
                    </FormControl>
                  ) : (
                    <TextField size="small" label="Modelo (id do provedor)" value={a.modelo} disabled={!edita} sx={{ width: 220 }}
                      onChange={(e) => mudar({ modelo: e.target.value })} />
                  )}
                  {provedor?.exige_base_url && (
                    <TextField size="small" label="URL do servidor" value={a.base_url ?? ""} disabled={!edita} sx={{ width: 260 }}
                      placeholder="http://127.0.0.1:11434/v1" onChange={(e) => mudar({ base_url: e.target.value })} />)}
                  <TextField size="small" label="Cota de tokens" type="number" value={a.cota_tokens} disabled={!edita}
                    sx={{ width: 140 }} onChange={(e) => mudar({ cota_tokens: Number(e.target.value) })} />
                  <Button variant="contained" size="small" disabled={!edita || !rascunho[id]} onClick={() => {
                    aoComando({ tipo: "modelo", agente: id, llm: a.llm, provedor: a.provedor ?? "mock", modelo: a.modelo,
                      usos: a.usos.length ? a.usos : dados.usos[id], cota_tokens: a.cota_tokens,
                      consentimento_externo: a.consentimento_externo, ...(a.base_url ? { base_url: a.base_url } : {}) });
                    setRascunho({ ...rascunho, [id]: undefined as never });
                    setTimeout(recarregar, 400);
                  }}>Aplicar</Button>
                </Stack>
                <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">usos:</Typography>
                  {(dados.usos[id] ?? []).map((u) => (
                    <Chip key={u} size="small" label={u} color={a.usos.includes(u) ? "primary" : "default"}
                      variant={a.usos.includes(u) ? "filled" : "outlined"} disabled={!edita}
                      onClick={() => mudar({ usos: a.usos.includes(u) ? a.usos.filter((x) => x !== u) : [...a.usos, u] })} />))}
                  {provedor?.externo && (
                    <FormControlLabel sx={{ ml: 1 }} label="Autorizo enviar dados (com pseudônimos) a este provedor externo"
                      control={<Switch size="small" checked={a.consentimento_externo} disabled={!edita}
                        onChange={(e) => mudar({ consentimento_externo: e.target.checked })} />} />)}
                  {provedor?.variavel_chave && (
                    <Chip size="small" variant="outlined" color={provedor.tem_chave || provedor.chave_opcional ? "success" : "warning"}
                      label={`${provedor.variavel_chave}: ${provedor.tem_chave ? "definida" : provedor.chave_opcional ? "opcional" : "ausente"}`} />)}
                  {a.disjuntor_aberto && <Chip size="small" color="error" label="disjuntor aberto (provedor falhou)" />}
                  <Typography variant="caption" color="text.secondary" sx={{ ml: "auto" }} aria-label={`Uso de LLM de ${id}`}>
                    {atual.usado} de {atual.cota_tokens} tokens · {custo?.chamadas ?? 0} chamada(s) ·
                    US$ {(custo?.custo_usd ?? 0).toFixed(4)} · {custo?.fallbacks ?? 0} fallback(s)
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
      {!edita && <Alert severity="info" sx={{ mt: 1.5 }}>Só o aprovador (controller) ajusta modelos e cotas; você pode consultar.</Alert>}
      </>)}
      {segredos && <ChavesLLM aoMudar={recarregar} />}
    </Secao>
  );
}

// ---------------------------------------------------------------- chaves de LLM no cofre (IAM-10)
const situacaoDaChave = (p: ChaveProvedor): { texto: string; cor: "success" | "warning" | "default" } =>
  p.ambiente && p.cofre ? { texto: "há chave no ambiente (a do cofre fica sem uso)", cor: "success" }
    : p.ambiente ? { texto: "há chave no ambiente", cor: "success" }
    : p.cofre ? { texto: "há chave no cofre", cor: "success" }
    : { texto: p.opcional ? "não há chave (opcional neste provedor)" : "não há chave", cor: p.opcional ? "default" : "warning" };

/** Só com PERM-MOD-SEGREDOS. A chave é digitada num campo de senha não controlado: o valor sai do campo direto para
 *  o servidor e o campo é esvaziado; não passa pelo estado do React, não volta da API e não é escrito em log. */
function ChavesLLM({ aoMudar }: { aoMudar: () => void }) {
  const { dados, erro, recarregar } = useRota<Segredos>("/api/segredos");
  const campos = useRef<Record<string, HTMLInputElement | null>>({});
  const [preenchido, setPreenchido] = useState<Record<string, boolean>>({}); // só se há algo digitado, nunca o valor
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string } | null>(null);
  const [remover, setRemover] = useState<ChaveProvedor | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const depois = (falha: string | undefined, sucesso: string) => {
    setOcupado(false);
    setAviso(falha ? { ok: false, texto: falha } : { ok: true, texto: sucesso });
    recarregar();
    aoMudar();
  };
  const definir = async (e: React.FormEvent, p: ChaveProvedor) => {
    e.preventDefault();
    const campo = campos.current[p.id];
    if (!campo?.value) return;
    setOcupado(true);
    const pedido = definirSegredo(p.segredo, campo.value);
    campo.value = "";
    setPreenchido((x) => ({ ...x, [p.id]: false }));
    depois((await pedido).erro, `Chave de ${p.id} guardada no cofre. Ela não será mostrada de novo.`);
  };
  const confirmarRemocao = async () => {
    if (!remover) return;
    const p = remover;
    setRemover(null);
    setOcupado(true);
    depois((await removerSegredo(p.segredo)).erro, `Chave de ${p.id} removida do cofre.`);
  };
  return (
    <Box component="section" aria-label="Chaves dos provedores de LLM" sx={{ mt: 3 }}>
      <Typography variant="h3" component="h3">Chaves dos provedores (cofre)</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1, maxWidth: 900 }}>
        A chave definida aqui fica no cofre selado do cadastro e nunca mais aparece: a tela só diz se ela existe. A
        variável de ambiente do servidor, quando existe, tem precedência sobre o cofre.
      </Typography>
      {erro && <Alert severity="error" role="alert">{erro}</Alert>}
      {aviso && <Alert severity={aviso.ok ? "success" : "error"} aria-label="Aviso das chaves" sx={{ mb: 1 }}
        onClose={() => setAviso(null)}>{aviso.texto}</Alert>}
      <Stack spacing={1}>
        {(dados?.provedores ?? []).map((p) => {
          const s = situacaoDaChave(p);
          const guardado = dados?.segredos.find((x) => x.nome === p.segredo);
          return (
            <Card key={p.id} variant="outlined" role="group" aria-label={`Chave de ${p.id}`}>
              <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                <Stack component="form" direction="row" spacing={1.5} alignItems="center" useFlexGap flexWrap="wrap"
                  onSubmit={(e: React.FormEvent) => definir(e, p)} autoComplete="off">
                  <Typography variant="body1" sx={{ minWidth: 130 }}><b>{p.id}</b></Typography>
                  <Chip size="small" variant="outlined" color={s.cor} label={s.texto} aria-label={`Situação da chave de ${p.id}`} />
                  <Typography variant="caption" color="text.secondary" sx={{ mr: "auto" }}>
                    {p.variavel}{guardado ? ` · no cofre por ${guardado.por} em ${new Date(guardado.em * 1000).toLocaleString("pt-BR")}` : ""}
                  </Typography>
                  <TextField size="small" type="password" label={p.cofre ? "Chave nova (substitui a do cofre)" : "Chave"}
                    sx={{ width: 300 }} autoComplete="new-password" inputRef={(el: HTMLInputElement | null) => { campos.current[p.id] = el; }}
                    onChange={(e) => setPreenchido((x) => ({ ...x, [p.id]: !!e.target.value }))}
                    inputProps={{ "aria-label": `Chave nova de ${p.id}`, spellCheck: false }} />
                  <Button type="submit" variant="contained" size="small" disabled={ocupado || !preenchido[p.id]}>
                    Guardar no cofre</Button>
                  <Button size="small" color="error" disabled={ocupado || !p.cofre} onClick={() => setRemover(p)}>
                    Remover do cofre</Button>
                </Stack>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
      <Dialog open={!!remover} onClose={() => setRemover(null)} aria-labelledby="titulo-remover-chave">
        <DialogTitle id="titulo-remover-chave">Remover a chave de {remover?.id} do cofre?</DialogTitle>
        <DialogContent>
          <Typography variant="body2">Os agentes que usam {remover?.id} ficam sem chave{remover?.ambiente
            ? " do cofre; a variável de ambiente continua valendo" : " e passam a seguir sem LLM"}.
            Para voltar atrás será preciso digitar a chave de novo.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemover(null)}>Cancelar</Button>
          <Button color="error" variant="contained" onClick={confirmarRemocao}>Remover</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

// ---------------------------------------------------------------- ficha do porte
type Perfil = Json & { titulo: string; norma_contabil: string; tem_erp: boolean; fonte_primaria: string;
  pessoas: Record<string, string>; aprovadores: string[]; limites_alcada: Record<string, number | null>;
  severidade: Record<string, string>; limiar_desvio: { percentual: number; absoluto: number };
  controle_compensatorio: Record<string, string>; receita_bruta_anual_max: number | null;
  receita_bruta_anual_min?: number };
type FichaSegmento = { titulo: string; natureza_dos_custos: string; unidades: Record<string, string>;
  centros_custo: Record<string, string>; contas: string[]; rateio: { direcionador: string; percentuais: Record<string, number> } };

const brl = (centavos: number | null) => (centavos === null ? "sem limite"
  : (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }));

export function FichaPorte() {
  const { dados, erro } = useRota<{ atual: string; portes: Record<string, Perfil>; segmento_atual?: string;
    segmentos?: Record<string, FichaSegmento> }>("/api/portes");
  if (erro) return <Secao titulo="Porte da empresa"><Alert severity="error">{erro}</Alert></Secao>;
  if (!dados) return null;
  const portes = Object.entries(dados.portes);
  const linha = (rotulo: string, valor: (p: Perfil) => React.ReactNode) => (
    <TableRow><TableCell><b>{rotulo}</b></TableCell>
      {portes.map(([id, p]) => <TableCell key={id} sx={id === dados.atual ? { bgcolor: "action.selected" } : undefined}>{valor(p)}</TableCell>)}
    </TableRow>);
  const extras = (p: Perfil, chave: string) => {
    const v = p[chave];
    return v === undefined ? "—" : Array.isArray(v) ? v.join("; ") : typeof v === "object" && v !== null
      ? Object.entries(v as Json).map(([k, x]) => `${k}: ${String(x)}`).join("; ") : String(v);
  };
  const campos: [string, string][] = [["regime_tributario", "Regime tributário"], ["obrigacoes", "Obrigações e relatórios"],
    ["estrutura", "Estrutura e cargos"], ["volume", "Volume e plano de contas"], ["calendario_fechamento", "Calendário de fechamento"],
    ["politica_aprovacao", "Política de aprovação"], ["papeis_de_acesso", "Papéis de acesso"],
    ["fonte_de_dados", "Fonte de dados"], ["cognicao_padrao", "Cognição padrão"]];
  return (
    <Secao titulo="Porte da empresa">
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        As regras que os agentes aplicam vêm do porte (base normativa em <code>models/portes.yaml</code>). O porte em uso
        está destacado; troque em “Dados da empresa”.
      </Typography>
      <Box sx={{ overflow: "auto" }}>
        <Table size="small" aria-label="Regras por porte">
          <TableHead><TableRow><TableCell />{portes.map(([id, p]) => (
            <TableCell key={id}><b>{p.titulo}</b>{id === dados.atual && <Chip size="small" color="primary" label="em uso" sx={{ ml: 1 }} />}</TableCell>))}
          </TableRow></TableHead>
          <TableBody>
            {linha("Receita bruta anual", (p) => (p.receita_bruta_anual_max === null ? "acima da faixa anterior"
              : `${p.receita_bruta_anual_min ? `acima de ${brl(p.receita_bruta_anual_min)} e ` : ""}até ${brl(p.receita_bruta_anual_max)}`))}
            {linha("Norma contábil", (p) => p.norma_contabil)}
            {linha("Dados", (p) => (p.tem_erp ? `ERP (fonte primária: ${p.fonte_primaria})` : "sem ERP: planilhas"))}
            {linha("Pessoas e cargos", (p) => Object.entries(p.pessoas).map(([u, c]) => `${u} (${c})`).join(", "))}
            {linha("Quem aprova", (p) => p.aprovadores.join(", "))}
            {linha("Alçadas", (p) => Object.entries(p.limites_alcada).map(([c, v]) => `${c}: ${brl(v)}`).join("; "))}
            {linha("Severidade das violações", (p) => Object.entries(p.severidade).map(([r, s]) => `${r}: ${s.replace("_", " ")}`).join("; "))}
            {linha("Materialidade do desvio", (p) => `${p.limiar_desvio.percentual}% e ${brl(p.limiar_desvio.absoluto)}`)}
            {linha("Controle compensatório", (p) => Object.values(p.controle_compensatorio).join("; ") || "—")}
            {campos.filter(([c]) => portes.some(([, p]) => p[c] !== undefined)).map(([c, rotulo]) => (
              <TableRow key={c}><TableCell><b>{rotulo}</b></TableCell>
                {portes.map(([id, p]) => <TableCell key={id} sx={id === dados.atual ? { bgcolor: "action.selected" } : undefined}>{extras(p, c)}</TableCell>)}
              </TableRow>))}
          </TableBody>
        </Table>
      </Box>
      {dados.segmentos && (
        <Box sx={{ overflow: "auto", mt: 2 }}>
          <Typography variant="subtitle2">Segmento (models/segmentos.yaml): plano de contas, custos e rateio</Typography>
          <Table size="small" aria-label="Ficha por segmento">
            <TableHead><TableRow><TableCell />{Object.entries(dados.segmentos).map(([id, s]) => (
              <TableCell key={id}><b>{s.titulo}</b>{id === dados.segmento_atual && <Chip size="small" color="primary" label="em uso" sx={{ ml: 1 }} />}</TableCell>))}
            </TableRow></TableHead>
            <TableBody>
              {([["Custos", (s: FichaSegmento) => s.natureza_dos_custos],
                ["Unidades de negócio", (s: FichaSegmento) => Object.values(s.unidades).join(", ")],
                ["Centros de custo", (s: FichaSegmento) => Object.values(s.centros_custo).join(", ")],
                ["Plano de contas (orçamento)", (s: FichaSegmento) => s.contas.join("; ")],
                ["Rateio dos custos fixos", (s: FichaSegmento) => `${s.rateio.direcionador}: ${Object.entries(s.rateio.percentuais).map(([u, v]) => `${u} ${v}%`).join(", ")}`],
              ] as [string, (s: FichaSegmento) => string][]).map(([rotulo, valor]) => (
                <TableRow key={rotulo}><TableCell><b>{rotulo}</b></TableCell>
                  {Object.entries(dados.segmentos ?? {}).map(([id, s]) => <TableCell key={id}>{valor(s)}</TableCell>)}
                </TableRow>))}
            </TableBody>
          </Table>
        </Box>)}
    </Secao>
  );
}

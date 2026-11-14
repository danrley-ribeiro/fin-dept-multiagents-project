// Aba Fontes de dados (ADR-011): cadastrar e testar conectores, entender a fonte sem IA generativa (sugestões com
// confiança e motivo), ajustar e confirmar o mapeamento, ativar a fonte, liberar host externo (administrador),
// modelos de planilha e histórico de envios. A credencial entra uma vez e nunca volta: a tela só diz se há uma.
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Alert, Box, Button, Chip, Divider, FormControl, InputLabel, LinearProgress, MenuItem, Paper, Select, Stack, Table,
  TableBody, TableCell, TableHead, TableRow, TextField, Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ler, pode, postar, type Sessao } from "../api/sessao";

interface Conector { id: string; nome: string; tipo: string; embutido?: boolean; tem_credencial: boolean;
  credencial_vinculada?: boolean; rede: string; ativo: boolean; config: Record<string, unknown>;
  mapeamento: { situacao: string; por?: string; em?: number; digest?: string } }
interface Envio { quando: number; por: string; arquivo: string; ok: boolean; modelo: boolean; competencia?: string;
  conector?: string; erros: string[]; mensagem?: string }
interface Lista { conectores: Conector[]; ativo: string; rede: { host: string; por: string }[]; envios: Envio[] }
interface Sugestao { aba: string; campo: string; titulo: string; tipo: string; obrigatorio: boolean; recurso: string | null;
  origem: string | null; conversao: string; confianca: number; motivo: string; fonte_sugestao: string | null;
  revisar?: boolean; valor?: string }
interface Problema { tipo: string; gravidade: string; aba: string; mensagem: string }
interface Entendimento { sugestao: { sugestoes: Sugestao[]; abas: Record<string, { recurso: string; motivo: string }> };
  qualidade: { ok: boolean; problemas: Problema[] }; previa: Record<string, Record<string, unknown>[]>;
  recursos_campos: Record<string, string[]>; competencia: string | null;
  llm?: { modelo: string; aceitas: unknown[]; rejeitadas: { aba: string; campo: string; motivo: string }[]; erro: string | null } }
interface Diagnostico { ok: boolean; etapas: { etapa: string; ok: boolean; detalhe: string }[] }
type Modelo = { arquivo: string; descricao: string };

const TIPOS = [["rest", "API REST (JSON)"], ["planilhas", "Pasta de planilhas no modelo da SMA"],
  ["mcp", "Servidor MCP de Excel (embutido)"]];
const SEM = "—";

async function corpo(r: Response) { return r.json().catch(() => ({})); }

export function Fontes({ sessao, fonteAtual }: { sessao: Sessao; fonteAtual?: string }) {
  const conecta = pode(sessao, "PERM-DAD-CONECTAR");
  const [lista, setLista] = useState<Lista | null>(null);
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [aviso, setAviso] = useState<{ ok: boolean; texto: string; erros?: string[] } | null>(null);
  const [diag, setDiag] = useState<{ id: string; d: Diagnostico } | null>(null);
  const [ent, setEnt] = useState<{ id: string; e: Entendimento } | null>(null);
  const [linhas, setLinhas] = useState<Sugestao[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const recarregar = useCallback(() => {
    ler<Lista>("/api/fontes").then((r) => r.dados && setLista(r.dados));
  }, []);
  useEffect(() => {
    recarregar();
    ler<{ modelos: Modelo[] }>("/api/modelos").then((r) => r.dados && setModelos(r.dados.modelos));
  }, [recarregar]);

  const acao = async (rota: string, dados: unknown) => {
    setOcupado(true);
    const r = await postar(rota, dados);
    const d = await corpo(r);
    setOcupado(false);
    if (!r.ok) setAviso({ ok: false, texto: d.erro ?? `erro ${r.status}`, erros: d.erros });
    recarregar();
    return r.ok ? d : null;
  };
  const testar = async (id: string) => { const d = await acao("/api/fontes/testar", { id }); if (d) setDiag({ id, d }); };
  const [llm, setLlm] = useState("");
  const entender = async (id: string) => {
    const d = await acao("/api/fontes/entender", { id, ...(llm ? { llm: { provedor: "mock", modelo: llm } } : {}) });
    if (d) { setEnt({ id, e: d }); setLinhas(d.sugestao.sugestoes); setAviso(null); }
  };
  const confirmar = async () => {
    if (!ent) return;
    const d = await acao("/api/fontes/confirmar", { id: ent.id, sugestoes: linhas.filter((l) => l.origem || l.valor) });
    if (d) setAviso({ ok: true, texto: `Mapeamento de ${ent.id} confirmado por ${d.por} (${d.digest}).` });
  };
  const ativar = async (id: string) => {
    const d = await acao("/api/fontes/ativar", { id });
    if (d) setAviso({ ok: true, texto: d.fonte === "conector" ? `Fonte ${id} ativada: a simulação reiniciou com o `
      + `fechamento sobre ela.` : "De volta ao ERP simulado." });
  };

  return (
    <Paper component="section" aria-label="Fontes de dados" sx={{ p: 2, maxWidth: 1400, mx: "auto", my: 2 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }} useFlexGap flexWrap="wrap">
        <Typography variant="h2" component="h2" sx={{ mr: "auto" }}>Fontes de dados</Typography>
        <Chip label={`em uso: ${lista?.ativo ?? "erp-simulado"} (${fonteAtual ?? "sintetico"})`} aria-label="Fonte em uso" />
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        O entendimento da fonte é determinístico (nomes, sinônimos em português e inglês, tipos e conteúdo); nada é
        usado antes de uma pessoa confirmar. A plataforma só fala com a própria máquina, salvo host liberado por um
        administrador. A credencial vai para o cofre e não volta para a tela.
      </Typography>
      {ocupado && <LinearProgress sx={{ mb: 1 }} />}
      {aviso && <Alert severity={aviso.ok ? "success" : "error"} sx={{ mb: 1 }} onClose={() => setAviso(null)}
        aria-label="Aviso das fontes">
        {aviso.texto}{aviso.erros?.length ? <ul style={{ margin: 0 }}>{aviso.erros.slice(0, 8).map((e) => <li key={e}>{e}</li>)}</ul> : null}
      </Alert>}

      <Table size="small" aria-label="Conectores">
        <TableHead><TableRow><TableCell>Conector</TableCell><TableCell>Tipo</TableCell><TableCell>Rede</TableCell>
          <TableCell>Credencial</TableCell><TableCell>Mapeamento</TableCell><TableCell>Ações</TableCell></TableRow></TableHead>
        <TableBody>
          {(lista?.conectores ?? []).map((c) => (
            <TableRow key={c.id} aria-label={`Conector ${c.id}`} selected={c.ativo}>
              <TableCell><b>{c.id}</b><Typography variant="caption" component="div">{c.nome}</Typography></TableCell>
              <TableCell>{c.tipo}</TableCell>
              <TableCell>{c.rede}</TableCell>
              <TableCell>{c.tem_credencial ? <Chip size="small" color={c.credencial_vinculada === false ? "warning" : "success"}
                label={c.credencial_vinculada === false ? "há credencial (outro endereço)" : "há credencial"} />
                : <Chip size="small" variant="outlined" label="sem credencial" />}</TableCell>
              <TableCell>{c.mapeamento.situacao}{c.mapeamento.por ? ` por ${c.mapeamento.por}` : ""}</TableCell>
              <TableCell>
                <Stack direction="row" spacing={0.5}>
                  {!c.embutido && <Button size="small" disabled={!conecta} onClick={() => testar(c.id)}>Testar</Button>}
                  {!c.embutido && <Button size="small" disabled={!conecta} onClick={() => entender(c.id)}>Entender</Button>}
                  <Button size="small" variant={c.ativo ? "contained" : "outlined"} disabled={!conecta || c.ativo}
                    onClick={() => ativar(c.id)}>{c.ativo ? "Em uso" : "Ativar"}</Button>
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <FormControl size="small" sx={{ mt: 1, minWidth: 260 }}>
        <InputLabel id="llm-fontes">LLM no entendimento (opcional)</InputLabel>
        <Select labelId="llm-fontes" label="LLM no entendimento (opcional)" value={llm} onChange={(e) => setLlm(e.target.value)}>
          <MenuItem value="">Desligado (só regras)</MenuItem>
          <MenuItem value="mock-mapeador">mock-mapeador (offline, só sugere)</MenuItem>
        </Select>
      </FormControl>

      {diag && (
        <Box aria-label="Diagnóstico da conexão" role="region" sx={{ mt: 2 }}>
          <Typography variant="h3" component="h3">Diagnóstico de {diag.id}: {diag.d.ok ? "em ordem" : "com falha"}</Typography>
          <ul>{diag.d.etapas.map((e, i) => <li key={i}>[{e.ok ? "ok" : "FALHA"}] {e.etapa}: {e.detalhe}</li>)}</ul>
        </Box>
      )}
      {ent && <TelaEntendimento ent={ent} linhas={linhas} setLinhas={setLinhas} podeConfirmar={conecta} aoConfirmar={confirmar} />}
      <Divider sx={{ my: 2 }} />
      <Cadastro desabilitado={!conecta} aoCadastrar={(d) => acao("/api/fontes/conectores", d).then((r) => {
        if (r) setAviso({ ok: true, texto: `Conector ${r.conector.id} cadastrado${r.conector.tem_credencial ? " (credencial no cofre)" : ""}.` });
      })} />
      {pode(sessao, "PERM-DAD-REDE") && <Rede lista={lista} aoLiberar={(host) => acao("/api/fontes/rede", { host })} />}
      <Divider sx={{ my: 2 }} />
      <Planilhas modelos={modelos} envios={lista?.envios ?? []} podeEnviar={pode(sessao, "PERM-DAD-ENVIAR")}
        aoEnviar={async (nome, b64) => { const d = await acao("/api/fontes/envios", { nome, conteudo_base64: b64 });
          if (d) setAviso({ ok: true, texto: d.modelo ? `${nome}: competência ${d.competencia} na pasta de planilhas.`
            : `${nome}: ${d.mensagem}` }); }} />
    </Paper>
  );
}

function TelaEntendimento({ ent, linhas, setLinhas, podeConfirmar, aoConfirmar }: {
  ent: { id: string; e: Entendimento }; linhas: Sugestao[]; setLinhas: (l: Sugestao[]) => void; podeConfirmar: boolean;
  aoConfirmar: () => void;
}) {
  const recursos = ent.e.recursos_campos;
  const porAba = useMemo(() => {
    const m: Record<string, Sugestao[]> = {};
    linhas.forEach((l) => { (m[l.aba] ??= []).push(l); });
    return m;
  }, [linhas]);
  const mudar = (alvo: Sugestao, campos: Partial<Sugestao>) =>
    setLinhas(linhas.map((l) => (l === alvo ? { ...l, ...campos, fonte_sugestao: "pessoa", confianca: 1,
      motivo: "ajustado pela pessoa" } : l)));
  const recursoDaAba = (aba: string) => porAba[aba]?.find((l) => l.recurso)?.recurso ?? ent.e.sugestao.abas[aba]?.recurso ?? "";
  return (
    <Box role="region" aria-label="Entendimento da fonte" sx={{ mt: 2 }}>
      <Typography variant="h3" component="h3">Entendimento de {ent.id}
        {ent.e.competencia ? ` · competência ${ent.e.competencia}` : ""}</Typography>
      <Alert severity={ent.e.qualidade.ok ? "info" : "warning"} sx={{ my: 1 }}>
        Qualidade: {ent.e.qualidade.ok ? "sem erros" : "com erros"}
        <ul aria-label="Relatório de qualidade" style={{ margin: 0 }}>
          {ent.e.qualidade.problemas.map((p, i) => <li key={i}>[{p.gravidade}] {p.tipo}: {p.mensagem}</li>)}
        </ul>
      </Alert>
      {ent.e.llm && <Alert severity="info" sx={{ mb: 1 }} aria-label="Sugestões do LLM">LLM ({ent.e.llm.modelo}):{" "}
        {ent.e.llm.erro ?? `${ent.e.llm.aceitas.length} aceita(s), ${ent.e.llm.rejeitadas.length} rejeitada(s) pela validação`}
        <ul style={{ margin: 0 }}>{ent.e.llm.rejeitadas.map((x, i) => <li key={i}>rejeitada {x.aba}.{x.campo}: {x.motivo}</li>)}</ul>
      </Alert>}
      <Table size="small" aria-label="Sugestões de mapeamento">
        <TableHead><TableRow><TableCell>Campo canônico</TableCell><TableCell>Coluna de origem</TableCell>
          <TableCell>Conversão</TableCell><TableCell>Confiança</TableCell><TableCell>Motivo</TableCell></TableRow></TableHead>
        <TableBody>
          {Object.entries(porAba).map(([aba, itens]) => [
            <TableRow key={aba}><TableCell colSpan={5} sx={{ bgcolor: "action.hover" }}>
              <b>{aba}</b> ← <FormControl size="small" variant="standard" sx={{ minWidth: 200 }}>
                <Select SelectDisplayProps={{ "aria-label": `Recurso de ${aba}` } as object} value={recursoDaAba(aba)} displayEmpty
                  onChange={(e) => setLinhas(linhas.map((l) => (l.aba === aba ? { ...l, recurso: e.target.value || null,
                    origem: null, fonte_sugestao: "pessoa" } : l)))}>
                  <MenuItem value="">{SEM} (não usar)</MenuItem>
                  {Object.keys(recursos).map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                </Select></FormControl>
              {ent.e.sugestao.abas[aba] && <Typography variant="caption" sx={{ ml: 1 }}>{ent.e.sugestao.abas[aba].motivo}</Typography>}
            </TableCell></TableRow>,
            ...itens.map((l) => (
              <TableRow key={`${aba}.${l.campo}`} aria-label={`Mapeamento ${aba}.${l.campo}`}>
                <TableCell>{l.titulo}{l.obrigatorio ? " *" : ""}<Typography variant="caption" component="div">{l.campo} · {l.tipo}</Typography></TableCell>
                <TableCell>
                  <Select size="small" variant="standard" SelectDisplayProps={{ "aria-label": `Origem de ${aba}.${l.campo}` } as object}
                    value={l.origem ?? ""} displayEmpty
                    onChange={(e) => mudar(l, { origem: e.target.value || null, recurso: recursoDaAba(aba) || null, valor: undefined })}>
                    <MenuItem value="">{SEM}</MenuItem>
                    {(recursos[recursoDaAba(aba)] ?? []).map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                  </Select>
                  {aba === "Empresa" && !l.origem && <TextField size="small" variant="standard" placeholder="valor fixo"
                    inputProps={{ "aria-label": `Valor fixo de ${aba}.${l.campo}` }} value={l.valor ?? ""}
                    onChange={(e) => mudar(l, { valor: e.target.value })} sx={{ ml: 1, width: 120 }} />}
                </TableCell>
                <TableCell>{l.conversao}</TableCell>
                <TableCell>{l.origem || l.valor ? <Chip size="small" color={l.confianca >= 0.7 ? "success" : "warning"}
                  label={l.confianca.toFixed(2)} /> : SEM}</TableCell>
                <TableCell><Typography variant="caption">{l.fonte_sugestao === "llm" ? "LLM · " : ""}{l.motivo}</Typography></TableCell>
              </TableRow>
            )),
          ])}
        </TableBody>
      </Table>
      <Typography variant="h3" component="h3" sx={{ mt: 2 }}>Prévia (redigida, já no modelo canônico)</Typography>
      <Box component="pre" aria-label="Prévia da fonte" sx={{ maxHeight: 220, overflow: "auto", fontSize: 12, bgcolor: "action.hover", p: 1 }}>
        {JSON.stringify(Object.fromEntries(Object.entries(ent.e.previa).map(([a, v]) => [a, v.slice(0, 2)])), null, 1)}
      </Box>
      <Button variant="contained" sx={{ mt: 1 }} disabled={!podeConfirmar} onClick={aoConfirmar}>Confirmar mapeamento</Button>
    </Box>
  );
}

function Cadastro({ desabilitado, aoCadastrar }: { desabilitado: boolean; aoCadastrar: (d: unknown) => void }) {
  const [tipo, setTipo] = useState("rest");
  const [f, setF] = useState({ id: "", nome: "", url: "http://127.0.0.1:8790", openapi: "/openapi.json",
    auth: "bearer", credencial: "", pasta: "planilhas", porte: "" });
  const campo = (k: keyof typeof f, rotulo: string, extra: Record<string, unknown> = {}) => (
    <TextField size="small" label={rotulo} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} {...extra} />);
  const enviar = () => {
    const config: Record<string, unknown> = tipo === "rest"
      ? { url_base: f.url, openapi: f.openapi || undefined, autenticacao: { tipo: f.auth } } : { pasta: f.pasta };
    if (f.porte) config.porte = f.porte;
    aoCadastrar({ id: f.id, nome: f.nome || f.id, tipo, config, ...(tipo === "rest" && f.credencial ? { credencial: f.credencial } : {}) });
    setF({ ...f, credencial: "" });
  };
  return (
    <Box component="form" aria-label="Cadastrar conector" onSubmit={(e) => { e.preventDefault(); enviar(); }}>
      <Typography variant="h3" component="h3" sx={{ mb: 1 }}>Cadastrar conector</Typography>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        <FormControl size="small" sx={{ minWidth: 240 }}>
          <InputLabel id="tipo-conector">Tipo</InputLabel>
          <Select labelId="tipo-conector" label="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {TIPOS.map(([v, r]) => <MenuItem key={v} value={v}>{r}</MenuItem>)}
          </Select>
        </FormControl>
        {campo("id", "Identificador")}
        {campo("nome", "Nome")}
        {tipo === "rest" ? <>
          {campo("url", "URL base")}
          {campo("openapi", "Contrato OpenAPI")}
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="auth-conector">Autenticação</InputLabel>
            <Select labelId="auth-conector" label="Autenticação" value={f.auth} onChange={(e) => setF({ ...f, auth: e.target.value })}>
              <MenuItem value="bearer">Bearer</MenuItem><MenuItem value="cabecalho">Cabeçalho X-API-Key</MenuItem>
              <MenuItem value="query">Chave na URL</MenuItem><MenuItem value="nenhuma">Nenhuma</MenuItem>
            </Select>
          </FormControl>
          {campo("credencial", "Credencial (token)", { type: "password", autoComplete: "off" })}
        </> : campo("pasta", "Pasta (dentro da pasta de fontes)")}
        <Button type="submit" variant="contained" disabled={desabilitado || !f.id}>Cadastrar</Button>
      </Stack>
    </Box>
  );
}

function Rede({ lista, aoLiberar }: { lista: Lista | null; aoLiberar: (host: string) => void }) {
  const [host, setHost] = useState("");
  return (
    <Box role="region" aria-label="Rede dos conectores" sx={{ mt: 2 }}>
      <Typography variant="h3" component="h3">Hosts externos liberados (administrador)</Typography>
      <Stack direction="row" spacing={1} sx={{ my: 1 }}>
        <TextField size="small" label="Host externo" value={host} onChange={(e) => setHost(e.target.value)} />
        <Button variant="outlined" disabled={!host} onClick={() => { aoLiberar(host); setHost(""); }}>Liberar host</Button>
      </Stack>
      <Typography variant="body2">{lista?.rede.length ? lista.rede.map((r) => `${r.host} (por ${r.por})`).join(", ")
        : "Nenhum: só loopback."}</Typography>
    </Box>
  );
}

function Planilhas({ modelos, envios, podeEnviar, aoEnviar }: { modelos: Modelo[]; envios: Envio[]; podeEnviar: boolean;
  aoEnviar: (nome: string, b64: string) => void }) {
  const arquivo = useRef<HTMLInputElement>(null);
  const enviar = async (f: File) => {
    const bytes = new Uint8Array(await f.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    aoEnviar(f.name, btoa(bin));
  };
  return (
    <Box role="region" aria-label="Planilhas">
      <Typography variant="h3" component="h3">Modelos de planilha</Typography>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ my: 1 }}>
        {modelos.map((m) => <Button key={m.arquivo} size="small" startIcon={<DownloadIcon />} href={`/api/modelos/${m.arquivo}`}
          download={m.arquivo} title={m.descricao}>{m.arquivo}</Button>)}
      </Stack>
      <input ref={arquivo} type="file" accept=".xlsx" hidden aria-label="Arquivo da planilha para a fonte"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) enviar(f); e.target.value = ""; }} />
      <Button variant="outlined" startIcon={<CloudUploadIcon />} disabled={!podeEnviar}
        onClick={() => arquivo.current?.click()}>Enviar planilha (.xlsx, no modelo ou não)</Button>
      <Table size="small" aria-label="Histórico de envios" sx={{ mt: 1 }}>
        <TableHead><TableRow><TableCell>Arquivo</TableCell><TableCell>Por</TableCell><TableCell>Resultado</TableCell></TableRow></TableHead>
        <TableBody>
          {envios.map((e, i) => (
            <TableRow key={i}>
              <TableCell>{e.arquivo}</TableCell><TableCell>{e.por}</TableCell>
              <TableCell>{e.modelo ? `modelo da SMA · competência ${e.competencia}` : e.ok ? "ok"
                : e.mensagem ?? (e.erros[0] ?? "recusada")}{e.conector ? ` · fonte ${e.conector}` : ""}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {!envios.length && <Typography color="text.secondary">Nenhum envio ainda.</Typography>}
    </Box>
  );
}

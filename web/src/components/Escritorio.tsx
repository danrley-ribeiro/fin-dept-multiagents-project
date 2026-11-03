// Planta do escritório da SMA: cada agente numa mesa dentro do seu departamento, mensagens como envelopes
// entre as mesas e chamadas às fontes de dados (MCP) como traços discretos por baixo das pessoas.
import { useEffect, useRef, useState } from "react";
import { statusDe, type StatusAgente } from "../state/reducer";
import type { FichaAgente, FonteDados, ViewState, Voo } from "../types";

export const POS: Record<string, { x: number; y: number }> = {
  SOL: { x: 100, y: 150 },
  APR: { x: 252, y: 150 },
  "AG-CIN": { x: 828, y: 150 },
  "AG-ORQ": { x: 500, y: 318 },
  "AG-CUS": { x: 162, y: 392 },
  "AG-ORC": { x: 162, y: 538 },
  "AG-RES": { x: 838, y: 392 },
  "AG-REL": { x: 838, y: 538 },
  ERP: { x: 408, y: 548 },
  Planilhas: { x: 500, y: 548 },
  Normas: { x: 592, y: 548 },
  LCK: { x: 628, y: 392 },
};

export const COR_AGENTE: Record<string, string> = {
  "AG-ORQ": "var(--series-1)", "AG-CUS": "var(--series-2)", "AG-ORC": "var(--series-3)",
  "AG-RES": "var(--series-4)", "AG-CIN": "var(--series-7)", "AG-REL": "var(--series-5)",
  SOL: "var(--humano)", APR: "var(--humano)",
};

const COR_PROTOCOLO: Record<string, string> = {
  "PROT-SOL": "var(--text-secondary)", "PROT-DEL": "var(--series-1)", "PROT-QRY": "var(--series-3)",
  "PROT-CMP": "var(--series-7)", humano: "var(--humano)", MCP: "var(--arquivo)", LCK: "var(--arquivo)",
};

export const DEPARTAMENTO: Record<string, string> = {  // espelho de env/empresa.py (fallback sem servidor)
  "AG-ORQ": "Coordenação da Controladoria", "AG-CUS": "Custos", "AG-ORC": "Orçamento", "AG-RES": "Resultados",
  "AG-CIN": "Controles Internos", "AG-REL": "Relatórios Gerenciais", SOL: "Diretoria", APR: "Aprovação",
};

export function departamentoDe(id: string, ficha?: FichaAgente): string {
  return ficha?.departamento ?? DEPARTAMENTO[id] ?? id;
}

const ROTULO_STATUS: Record<StatusAgente, string> = {
  trabalhando: "trabalhando", aguardando: "aguardando", ocioso: "ocioso", vetando: "vetando", fora: "fora de operação",
};

interface Props {
  estado: ViewState;
  fichas: Record<string, FichaAgente>;
  selecionado: string | null;
  aoSelecionar: (id: string) => void;
  duracaoVoo: number;
  novidades: Record<string, number>;
  aoAbrirFonte: (fonte: FonteDados) => void;
  aoAbrirPeriodos: () => void;
}

export function Escritorio({ estado, fichas, selecionado, aoSelecionar, duracaoVoo, novidades, aoAbrirFonte,
  aoAbrirPeriodos }: Props) {
  const temErp = estado.meta ? estado.meta.tem_erp !== false : true;
  const planilhaReal = estado.meta?.fonte === "planilha";
  const empresa = estado.meta?.empresa as { razao_social?: string } | undefined;
  return (
    <svg className="escritorio" viewBox="0 0 1000 640" role="img"
      aria-label="Planta do escritório da SMA com os agentes nas mesas">
      <defs>
        <pattern id="piso" width="40" height="40" patternUnits="userSpaceOnUse">
          <rect width="40" height="40" fill="var(--piso)" />
          <path d="M40 0H0V40" fill="none" stroke="var(--piso-linha)" strokeWidth="1" />
        </pattern>
        <filter id="sombra" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.18" />
        </filter>
      </defs>
      <rect x="0" y="0" width="1000" height="640" fill="url(#piso)" />
      <Sala x={12} y={30} w={336} h={218} titulo="Diretoria" />
      <Sala x={668} y={30} w={320} h={218} titulo="Controles Internos (sala de vidro)" vidro />
      <Sala x={12} y={270} w={300} h={358} titulo="Custos e Orçamento" />
      <Sala x={688} y={270} w={300} h={358} titulo="Resultados e Relatórios" />
      <Placa razao={empresa?.razao_social || "SMA"} porte={String(estado.meta?.porte_titulo ?? "")} />
      <Voos voos={estado.voos} duracao={duracaoVoo} camada="mcp" />
      <FontesDados estado={estado} temErp={temErp} planilhaReal={planilhaReal} aoAbrir={aoAbrirFonte} />
      <Cofre reservas={estado.reservas} aoAbrir={aoAbrirPeriodos} />
      {Object.keys(POS).filter((id) => id in estado.agentes).map((id) => (
        <Mesa key={id} id={id} ficha={fichas[id]} status={statusDe(estado, id)} estado={estado}
          selecionado={selecionado === id} aoSelecionar={aoSelecionar}
          novidades={id === "APR" ? Object.keys(estado.pendentes).length : novidades[id] ?? 0} />
      ))}
      <Voos voos={estado.voos} duracao={duracaoVoo} camada="mensagens" />
    </svg>
  );
}

function Sala({ x, y, w, h, titulo, vidro }: { x: number; y: number; w: number; h: number; titulo: string;
  vidro?: boolean }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={10} fill={vidro ? "var(--vidro)" : "var(--sala)"}
        stroke="var(--parede)" strokeWidth={vidro ? 2 : 3} strokeDasharray={vidro ? "6 4" : undefined} />
      <text x={x + 12} y={y + 20} className="sala-titulo">{titulo}</text>
    </g>
  );
}

function Placa({ razao, porte }: { razao: string; porte: string }) {
  return (
    <g transform="translate(410 40)" filter="url(#sombra)">
      <rect width="180" height="48" rx="8" fill="var(--surface-1)" stroke="var(--parede)" />
      <image href="/sma-logo.svg" x="8" y="8" width="32" height="32" />
      <text x="48" y="21" className="placa-titulo">{razao.length > 18 ? razao.slice(0, 17) + "…" : razao}</text>
      <text x="48" y="37" className="placa-sub">{porte || "Controladoria"}</text>
    </g>
  );
}

const ICONE: Record<FonteDados, (cor: string) => JSX.Element> = {
  ERP: (cor) => (  // banco de dados
    <g fill="none" stroke={cor} strokeWidth="2">
      <ellipse cx="0" cy="-8" rx="12" ry="4" />
      <path d="M-12 -8v16c0 2.2 5.4 4 12 4s12-1.8 12-4v-16" />
      <path d="M-12 0c0 2.2 5.4 4 12 4s12-1.8 12-4" />
    </g>
  ),
  Planilhas: (cor) => (  // grade de planilha
    <g fill="none" stroke={cor} strokeWidth="2">
      <rect x="-12" y="-12" width="24" height="24" rx="2" />
      <path d="M-12 -4h24M-12 4h24M-4 -12v24" />
    </g>
  ),
  Normas: (cor) => (  // livro de normas
    <g fill="none" stroke={cor} strokeWidth="2">
      <path d="M-12 -11h10a4 4 0 0 1 4 4v18a3 3 0 0 0-3-3h-11z" />
      <path d="M12 -11h-6a4 4 0 0 0-4 4v18a3 3 0 0 1 3-3h7z" />
    </g>
  ),
};

function FontesDados({ estado, temErp, planilhaReal, aoAbrir }: { estado: ViewState; temErp: boolean;
  planilhaReal: boolean; aoAbrir: (f: FonteDados) => void }) {
  const fontes: FonteDados[] = ["ERP", "Planilhas", "Normas"];
  const rotulo: Record<FonteDados, string> = { ERP: temErp ? "ERP" : "ERP (não há)",
    Planilhas: planilhaReal ? "Excel da empresa" : "Planilhas", Normas: "Normas" };
  return (
    <g>
      <rect x={350} y={482} width={300} height={130} rx={10} className="fontes-zona" />
      <text x={362} y={500} className="sala-titulo">Fontes de dados (MCP)</text>
      {fontes.map((f) => {
        const { x, y } = POS[f];
        const info = estado.fontes[f];
        const ativa = info.ultimaT >= estado.t - 1 && info.ultimaT >= 0;
        const inativa = f === "ERP" && !temErp;
        return (
          <g key={f} transform={`translate(${x} ${y})`}
            className={`fonte${ativa ? " ativa" : ""}${inativa ? " inativa" : ""}`}
            role="button" tabIndex={0} onClick={() => aoAbrir(f)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && aoAbrir(f)}
            aria-label={`${rotulo[f]}: ${info.chamadas} chamada(s). Clique para ver as chamadas e os modelos`}>
            <rect x="-40" y="-36" width="80" height="84" rx="10" className="fonte-cartao" filter="url(#sombra)" />
            <g transform="translate(0 -8)">{ICONE[f](inativa ? "var(--text-muted)" : "var(--arquivo)")}</g>
            <text x="0" y="22" textAnchor="middle" className="fonte-nome">{rotulo[f]}</text>
            <text x="0" y="37" textAnchor="middle" className="fonte-contador">
              {inativa ? "planilha no lugar" : `${info.chamadas} chamada${info.chamadas === 1 ? "" : "s"}`}</text>
          </g>
        );
      })}
    </g>
  );
}

function Cofre({ reservas, aoAbrir }: { reservas: Record<string, string>; aoAbrir: () => void }) {
  const ativas = Object.entries(reservas);
  const { x, y } = POS.LCK;
  return (
    <g transform={`translate(${x - 35} ${y - 30})`} className="cofre-grupo" role="button" tabIndex={0}
      onClick={aoAbrir} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && aoAbrir()}
      aria-label={`Períodos em fechamento: ${ativas.length} reserva(s) ativa(s). Clique para ver o histórico`}>
      <rect x="-6" y="-6" width="82" height={82 + ativas.length * 12} rx="10" className="cofre-alvo" />
      <rect width="70" height="56" rx="6" fill="var(--cofre)" stroke="var(--parede)" filter="url(#sombra)" />
      <circle cx="35" cy="26" r="13" fill="none" stroke="var(--surface-1)" strokeWidth="3" />
      <line x1="35" y1="26" x2="35" y2="16" stroke="var(--surface-1)" strokeWidth="3" strokeLinecap="round" />
      {ativas.length > 0 && (
        <g transform="translate(66 2)" className="badge-svg">
          <rect x="-10" y="-10" width="20" height="20" rx="10" />
          <text x="0" y="4" textAnchor="middle">{ativas.length}</text>
        </g>
      )}
      <text x="35" y="72" textAnchor="middle" className="rotulo-link">Períodos ›</text>
      {ativas.map(([chave, dono], i) => (
        <text key={chave} x="35" y={86 + i * 12} textAnchor="middle" className="rotulo-reserva">
          {chave.split("/")[1]} · {dono}
        </text>
      ))}
    </g>
  );
}

interface MesaProps {
  id: string;
  ficha?: FichaAgente;
  status: StatusAgente;
  estado: ViewState;
  selecionado: boolean;
  aoSelecionar: (id: string) => void;
  novidades: number;
}

function Mesa({ id, ficha, status, estado, selecionado, aoSelecionar, novidades }: MesaProps) {
  const { x, y } = POS[id];
  const a = estado.agentes[id];
  const humano = id === "SOL" || id === "APR";
  const fora = status === "fora";
  const bolhaRecente = a.bolha && a.bolha.t >= estado.t - 2 && !fora ? a.bolha : null;
  const titulo = ficha?.titulo ?? id;
  return (
    <g transform={`translate(${x} ${y})`} className={`mesa status-${status}${selecionado ? " selecionada" : ""}`}
      onClick={() => aoSelecionar(id)} role="button" tabIndex={0}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && aoSelecionar(id)}
      aria-label={`${id} · ${departamentoDe(id, ficha)} (${titulo}): ${ROTULO_STATUS[status]}${novidades ? `, ${novidades} ${id === "APR"
        ? "decisão(ões) pendente(s)" : "novidade(s)"}` : ""}`}>
      <rect x="-72" y="-56" width="144" height="134" rx="12" className="mesa-alvo" />
      <g opacity={fora ? 0.35 : 1}>
        <rect x="-16" y="-24" width="32" height="30" rx="8" fill="var(--cadeira)" />
        <circle cx="0" cy="-34" r="12" fill="var(--pele)" />
        <rect x="-17" y="-22" width="34" height="26" rx="9" fill={COR_AGENTE[id]} />
        {status === "trabalhando" && !humano && <circle cx="0" cy="-34" r="16" className="anel-trabalho" />}
      </g>
      <rect x="-56" y="2" width="112" height="30" rx="5" fill="var(--madeira)" filter="url(#sombra)" />
      <rect x="-16" y="-6" width="32" height="20" rx="3" fill={fora ? "var(--tela-off)" : status === "trabalhando"
        ? "var(--tela-on)" : "var(--tela)"} stroke="var(--parede)" />
      {humano && <rect x="24" y="8" width="18" height="12" rx="2" fill="var(--papel)" />}
      <text x="0" y="47" textAnchor="middle" className="nome-agente">{humano ? titulo : id}</text>
      <text x="0" y="59" textAnchor="middle" className="depto-agente">{departamentoDe(id, ficha)}</text>
      {!humano && <text x="0" y="71" textAnchor="middle" className="status-agente">{ROTULO_STATUS[status]}</text>}
      {fora && <text x="22" y="-48" className="zz">zZ</text>}
      {a.vetando && (
        <g transform="translate(26 12) rotate(-14)">
          <rect x="-24" y="-11" width="48" height="20" rx="3" className="carimbo" />
          <text x="0" y="4" textAnchor="middle" className="carimbo-texto">VETO</text>
        </g>
      )}
      {novidades > 0 && (
        <g transform="translate(44 -50)" className={id === "APR" ? "badge-svg badge-urgente" : "badge-svg"}>
          <rect x={novidades > 9 ? -15 : -10} y="-10" width={novidades > 9 ? 30 : 20} height="20" rx="10" />
          <text x="0" y="4" textAnchor="middle">{novidades > 99 ? "99+" : novidades}</text>
        </g>
      )}
      {bolhaRecente && <Bolha texto={bolhaRecente.texto} tipo={bolhaRecente.tipo} />}
    </g>
  );
}

function Bolha({ texto, tipo }: { texto: string; tipo: string }) {
  const t = texto.length > 30 ? texto.slice(0, 29) + "…" : texto;
  const w = Math.max(56, t.length * 6.3 + 18);
  return (
    <g transform="translate(0 -58)" className={`bolha bolha-${tipo}`}>
      <rect x={-w / 2} y="-26" width={w} height="22" rx={tipo === "pensamento" ? 11 : 6} />
      <path d="M-5 -4 L0 4 L5 -4 Z" />
      <text x="0" y="-11" textAnchor="middle">{t}</text>
    </g>
  );
}

interface VooAtivo extends Voo {
  inicio: number;
}

/** Animações por requestAnimationFrame. Camada "mcp": traço discreto agente→fonte, por baixo das mesas;
 *  camada "mensagens": envelope com o performativo entre as mesas (a perdida cai com um ✕). */
function Voos({ voos, duracao, camada }: { voos: Voo[]; duracao: number; camada: "mcp" | "mensagens" }) {
  const [ativos, setAtivos] = useState<VooAtivo[]>([]);
  const [, setQuadro] = useState(0);
  const vistos = useRef(new Set<number>());

  useEffect(() => {
    const agora = performance.now();
    const daCamada = (v: Voo) => (camada === "mcp") === (v.protocolo === "MCP" || v.protocolo === "LCK");
    const novos = voos.filter((v) => daCamada(v) && !vistos.current.has(v.id) && POS[v.de] && POS[v.para]);
    if (novos.length === 0) return;
    novos.forEach((v) => vistos.current.add(v.id));
    if (vistos.current.size > 5000) vistos.current = new Set(novos.map((v) => v.id));
    setAtivos((a) => [...a, ...novos.map((v, i) => ({ ...v, inicio: agora + i * Math.min(120, duracao / 6) }))]
      .slice(-60));
  }, [voos, duracao, camada]);

  useEffect(() => {
    if (ativos.length === 0) return;
    let id = 0;
    const quadro = () => {
      const agora = performance.now();
      setAtivos((a) => a.filter((v) => agora - v.inicio < duracao));
      setQuadro((q) => q + 1);
      id = requestAnimationFrame(quadro);
    };
    id = requestAnimationFrame(quadro);
    return () => cancelAnimationFrame(id);
  }, [ativos.length, duracao]);

  const agora = performance.now();
  return (
    <g className={`voos voos-${camada}`} pointerEvents="none">
      {ativos.map((v) => {
        const p = Math.min(1, Math.max(0, (agora - v.inicio) / duracao));
        if (p <= 0) return null;
        const a = POS[v.de], b = POS[v.para];
        if (camada === "mcp") {  // traço que se estende até a fonte e esmaece
          const ext = Math.min(1, p * 1.8);
          const opac = p > 0.6 ? (1 - p) / 0.4 : 1;
          return (
            <line key={v.id} x1={a.x} y1={a.y - 10} x2={a.x + (b.x - a.x) * ext}
              y2={a.y - 10 + (b.y - 10 - a.y) * ext}
              className={v.tipo === "perdida" ? "traco-mcp negado" : "traco-mcp"} opacity={opac * 0.75} />
          );
        }
        const cx = (a.x + b.x) / 2, cy = Math.min(a.y, b.y) - 70;
        const perdida = v.tipo === "perdida";
        const pp = perdida ? Math.min(p, 0.5) : p;
        const x = (1 - pp) ** 2 * a.x + 2 * (1 - pp) * pp * cx + pp ** 2 * b.x;
        const y = (1 - pp) ** 2 * (a.y - 20) + 2 * (1 - pp) * pp * cy + pp ** 2 * (b.y - 20) + (perdida && p > 0.5
          ? (p - 0.5) * 120 : 0);
        const cor = COR_PROTOCOLO[v.protocolo] ?? "var(--text-secondary)";
        const opac = p > 0.85 ? (1 - p) / 0.15 : 1;
        return (
          <g key={v.id} transform={`translate(${x} ${y})`} opacity={opac}>
            <rect x="-12" y="-8" width="24" height="16" rx="2" fill="var(--papel)" stroke={cor} strokeWidth="2" />
            <path d="M-12 -8 L0 1 L12 -8" fill="none" stroke={cor} strokeWidth="1.5" />
            {perdida && <text x="10" y="-8" className="perdida">✕</text>}
            <text x="0" y="22" textAnchor="middle" className="rotulo-voo">{v.rotulo}</text>
          </g>
        );
      })}
    </g>
  );
}

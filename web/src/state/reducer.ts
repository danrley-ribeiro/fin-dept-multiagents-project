// Estado do escritório derivado SÓ do trace: o mesmo reducer serve ao vivo (SSE) e ao replay offline.
import type { EstadoAgente, Mente, Registro, ViewState } from "../types";

export const AGENTES = ["SOL", "APR", "AG-ORQ", "AG-CUS", "AG-ORC", "AG-RES", "AG-CIN", "AG-REL"] as const;
const MAX_VOOS = 40;

function menteVazia(): Mente {
  return { crencas: {}, desejos: {}, intencoes: {}, deliberacoes: [], decisoes: [], hipoteses: {},
    propostasRejeitadas: [] };
}

function agenteVazio(id: string): EstadoAgente {
  return { id, ultimaAtividade: -1, bolha: null, mente: menteVazia(), vetando: false };
}

export function estadoInicial(): ViewState {
  const agentes: Record<string, EstadoAgente> = {};
  for (const id of AGENTES) agentes[id] = agenteVazio(id);
  return { t: 0, seq: 0, agentes, conversas: {}, voos: [], offline: [], pendentes: {}, solicitacoes: {},
    reservas: {}, historicoReservas: [], registros: [], meta: null,
    fontes: { ERP: { chamadas: 0, ultimaT: -1 }, Planilhas: { chamadas: 0, ultimaT: -1 }, Normas: { chamadas: 0, ultimaT: -1 } },
    chamadasMcp: [] };
}

function agente(s: ViewState, id: string | undefined): EstadoAgente | null {
  if (!id || !(id in s.agentes)) return null;
  return s.agentes[id];
}

function tocar(s: ViewState, id: string | undefined, r: Registro, texto?: string, tipo = "fala") {
  const a = agente(s, id);
  if (!a) return;
  a.ultimaAtividade = r.t;
  if (texto) a.bolha = { texto, tipo, t: r.t };
}

const STATUS_FINAL: Record<string, string> = { "not-understood": "recusado", refuse: "recusado" };

/** Aplica um registro ao estado (muta uma cópia rasa feita por `aplicarTodos`). */
function aplicar(s: ViewState, r: Registro): void {
  s.t = Math.max(s.t, r.t);
  s.seq = r.seq;
  s.registros.push(r);
  const cid = r.conversation_id ?? "";
  switch (r.kind) {
    case "meta":
      s.meta = r;
      break;
    case "open":
    case "send": {
      const conv = s.conversas[cid];
      if (r.kind === "open" || !conv) {
        s.conversas[cid] = { id: cid, protocolo: String(r.protocol), estado: String(r.para),
          iniciador: String(r.sender), contraparte: String(r.receiver) };
      } else {
        conv.estado = String(r.para);
      }
      tocar(s, r.sender, r, String(r.performative), r.performative === "veto" ? "veto" : "fala");
      s.voos.push({ id: r.seq, de: String(r.sender), para: String(r.receiver), rotulo: String(r.performative),
        protocolo: String(r.protocol), tipo: "mensagem" });
      if (r.protocol === "PROT-SOL") registrarSolicitacao(s, r);
      if (r.protocol === "PROT-APR") registrarAprovacao(s, r, cid);
      break;
    }
    case "ui": {  // traces anteriores à DSM3 (canal livre veto_notice / decisao_humana)
      tocar(s, r.sender, r, String(r.performative), "fala");
      s.voos.push({ id: r.seq, de: String(r.sender), para: String(r.receiver), rotulo: String(r.performative),
        protocolo: "humano", tipo: "humano" });
      const c = (r.content ?? {}) as Record<string, unknown>;
      if (r.performative === "veto_notice") {
        s.pendentes[String(c.solicitacao)] = {
          solicitacao: String(c.solicitacao), conversation_id: cid, competencia: c.competencia as string,
          achados: (c.achados as never) ?? [], correcoes_sugeridas: (c.correcoes_sugeridas as never) ?? [],
          opcoes: (c.opcoes as string[]) ?? ["waiver", "bloquear"],
        };
      } else if (r.performative === "decisao_humana") {
        delete s.pendentes[String(c.solicitacao)];
      }
      break;
    }
    case "drop":
      s.voos.push({ id: r.seq, de: String(r.sender), para: String(r.receiver), rotulo: String(r.performative),
        protocolo: String(r.protocol), tipo: "perdida" });
      break;
    case "discard":
      break;
    case "timeout": {
      const conv = s.conversas[cid];
      if (conv) {
        conv.estado = String(r.para);
        tocar(s, conv.iniciador, r, `timeout de ${conv.contraparte}`, "alerta");
      }
      if (r.protocol === "PROT-APR") encerrarAprovacao(s, cid);  // prazo do ticket esgotado
      break;
    }
    case "advance": {
      const conv = s.conversas[cid];
      if (conv) conv.estado = String(r.para);
      if (r.agente !== "SVC-POL") tocar(s, r.agente, r, String(r.evento));
      if (r.evento === "deny") encerrarAprovacao(s, cid);  // política negou a liberação (POL-07)
      break;
    }
    case "rejected":  // mensagem ou transição recusada pelo barramento (DSM3)
      tocar(s, String(r.agente ?? r.sender ?? ""), r, "rejeitada", "alerta");
      break;
    case "mcp_call":
    case "mcp_denied": {
      tocar(s, r.agente, r);
      const fonte = fonteDe(r);
      const atual = s.fontes[fonte];
      s.fontes[fonte] = { ...atual, chamadas: atual.chamadas + (r.kind === "mcp_call" ? 1 : 0), ultimaT: r.t,
        indisponivel: r.kind === "mcp_denied" && r.motivo ? String(r.motivo) : atual.indisponivel };
      s.chamadasMcp.push({ seq: r.seq, t: r.t, agente: String(r.agente), tool: String(r.tool),
        fonte: String(r.fonte ?? `mcp://${String(r.tool).replace(".", "/")}`),
        negada: r.kind === "mcp_denied" ? String(r.motivo ?? "fora da allowlist (NORM-02)") : undefined });
      if (s.chamadasMcp.length > 200) s.chamadasMcp = s.chamadasMcp.slice(-200);
      s.voos.push({ id: r.seq, de: String(r.agente), para: fonte, rotulo: String(r.tool), protocolo: "MCP",
        tipo: r.kind === "mcp_call" ? "mcp" : "perdida" });
      break;
    }
    case "lock": {
      const chave = (r.chave as string[]).join("/");
      if (r.evento === "reserve" && r.performative === "reserve-accept") s.reservas[chave] = String(r.dono);
      else if (r.evento === "release" || r.evento === "ttl_expirado") delete s.reservas[chave];
      s.historicoReservas.push({ t: r.t, evento: String(r.evento), chave,
        quem: String(r.solicitante ?? r.dono ?? ""), resultado: String(r.performative ?? r.evento) });
      s.voos.push({ id: r.seq, de: "AG-ORQ", para: "LCK", rotulo: String(r.evento), protocolo: "LCK", tipo: "mcp" });
      break;
    }
    case "agente": {
      const id = String(r.agente);
      s.offline = r.evento === "desligado" ? [...new Set([...s.offline, id])] : s.offline.filter((x) => x !== id);
      break;
    }
    case "decision": {
      const a = agente(s, r.agente);
      if (a) {
        a.mente.decisoes.push({ regra: String(r.regra), entradas: r.entradas, resultado: r.resultado, t: r.t,
          seq: r.seq, conversa: cid });
        tocar(s, r.agente, r);
      }
      break;
    }
    case "belief": {
      const a = agente(s, r.agente);
      if (a) {
        a.mente.crencas[String(r.chave)] = { valor: r.depois, antes: r.antes, fonte: String(r.fonte), seq: r.seq,
          t: r.t };
        tocar(s, r.agente, r);
      }
      break;
    }
    case "hipotese": {  // ADR-008: proposta validada vira hipótese; só a evidência a confirma ou refuta
      const a = agente(s, r.agente);
      if (!a) break;
      const evento = String(r.evento);
      if (evento === "rejeitada") {
        a.mente.propostasRejeitadas.push({ tipo: String(r.tipo), alvo: String(r.alvo), origem: String(r.origem),
          motivo: String(r.motivo), seq: r.seq, t: r.t });
        break;
      }
      const id = String(r.hipotese);
      const anterior = a.mente.hipoteses[id];
      a.mente.hipoteses[id] = {
        id, tipo: String(r.tipo), alvo: String(r.alvo), seq: r.seq, t: r.t,
        estado: evento === "aceita" ? "proposta" : evento === "corroborada" ? (anterior?.estado ?? "proposta") : evento,
        origens: [...new Set([...(anterior?.origens ?? []), ...(r.origem ? [String(r.origem)] : [])])],
        justificativa: (r.justificativa as string) ?? anterior?.justificativa,
        fonte: (r.fonte as string) ?? anterior?.fonte, motivo: (r.motivo as string) ?? anterior?.motivo,
      };
      tocar(s, r.agente, r, `hipótese ${evento}: ${r.tipo}`, "pensamento");
      break;
    }
    case "desire": {
      const a = agente(s, r.agente);
      if (a) {
        a.mente.desejos[String(r.desejo)] = { id: String(r.desejo), prioridade: Number(r.prioridade),
          estado: r.evento === "gerado" ? "ativo" : String(r.evento), motivo: String(r.motivo), seq: r.seq };
      }
      break;
    }
    case "deliberation": {
      const a = agente(s, r.agente);
      if (a) {
        a.mente.deliberacoes.push({ desejo: String(r.desejo), escolhido: (r.escolhido as string) ?? null,
          opcoes: (r.opcoes as never) ?? [], t: r.t, seq: r.seq });
        tocar(s, r.agente, r, r.escolhido ? `decide: ${r.escolhido}` : "sem plano", "pensamento");
      }
      break;
    }
    case "intention": {
      const a = agente(s, r.agente);
      if (a) {
        const id = String(r.intencao);
        const anterior = a.mente.intencoes[id];
        const evento = String(r.evento);
        a.mente.intencoes[id] = {
          id, desejo: String(r.desejo), plano: String(r.plano),
          estado: evento === "adotada" || evento === "retomada" ? "ativa"
            : evento === "reconsiderada" ? (anterior?.estado ?? "ativa") : evento,
          motivo: String(r.motivo), aguardando: (r.aguardando as string) ?? undefined, seq: r.seq,
          historico: [...(anterior?.historico ?? []), { evento, motivo: String(r.motivo), t: r.t }],
        };
        if (r.agente === "AG-CIN") {
          a.vetando = Object.values(a.mente.intencoes).some(
            (i) => i.estado === "suspensa" && (i.aguardando ?? "").startsWith("cmp:"));
        }
        const rotulo = evento === "reconsiderada" || evento === "abandonada" ? "pensamento" : "intencao";
        tocar(s, r.agente, r, `${evento}: ${r.plano}`, rotulo);
      }
      break;
    }
  }
}

/** Qual fonte de dados atendeu a chamada MCP (planilha de empresa sem ERP conta como Planilhas). */
export function fonteDe(r: Registro): "ERP" | "Planilhas" | "Normas" {
  const tool = String(r.tool ?? "");
  if (tool.startsWith("normas.")) return "Normas";
  if (String(r.fonte ?? "").startsWith("mcp://excel") || tool.startsWith("planilhas.")) return "Planilhas";
  return "ERP";
}

function registrarSolicitacao(s: ViewState, r: Registro) {
  const cid = String(r.conversation_id);
  const c = (r.content ?? {}) as Record<string, unknown>;
  if (r.performative === "request") {
    s.solicitacoes[cid] = { sid: cid, intencao: String(c.intencao), competencia: String(c.competencia),
      status: "aguardando" };
    return;
  }
  const sol = s.solicitacoes[cid];
  if (!sol) return;
  if (r.performative === "agree") sol.status = "em_execucao";
  else if (r.performative === "inform") sol.status = String(c.status);
  else if (r.performative === "failure") {
    sol.status = String(c.motivo ?? "").includes("veto") ? "bloqueado" : "falhou";
    sol.detalhe = String(c.motivo ?? "");
  } else sol.status = STATUS_FINAL[String(r.performative)] ?? String(r.performative);
}

/** Approval Gate (PROT-APR, DSM3): a proposta vira pendência humana até approve, reject, prazo ou negação. */
function registrarAprovacao(s: ViewState, r: Registro, cid: string) {
  const c = (r.content ?? {}) as Record<string, unknown>;
  if (r.performative === "propose-action") {
    s.pendentes[String(c.solicitacao)] = {
      solicitacao: String(c.solicitacao), conversation_id: cid, competencia: c.competencia as string,
      achados: (c.achados as never) ?? [], correcoes_sugeridas: (c.correcoes_sugeridas as never) ?? [],
      opcoes: (c.opcoes as string[]) ?? ["bloquear"],
    };
  } else if (r.performative === "approve" || r.performative === "reject") {
    delete s.pendentes[String(c.solicitacao)];
  }
}

function encerrarAprovacao(s: ViewState, cid: string) {
  for (const [sid, p] of Object.entries(s.pendentes)) if (p.conversation_id === cid) delete s.pendentes[sid];
}

function clonar(s: ViewState): ViewState {
  const agentes: Record<string, EstadoAgente> = {};
  for (const [id, a] of Object.entries(s.agentes)) {
    agentes[id] = { ...a, mente: { crencas: { ...a.mente.crencas }, desejos: { ...a.mente.desejos },
      intencoes: { ...a.mente.intencoes }, deliberacoes: [...a.mente.deliberacoes], decisoes: [...a.mente.decisoes],
      hipoteses: { ...a.mente.hipoteses }, propostasRejeitadas: [...a.mente.propostasRejeitadas] } };
  }
  const conversas: ViewState["conversas"] = {};
  for (const [id, c] of Object.entries(s.conversas)) conversas[id] = { ...c };
  const solicitacoes: ViewState["solicitacoes"] = {};
  for (const [id, x] of Object.entries(s.solicitacoes)) solicitacoes[id] = { ...x };
  return { ...s, agentes, conversas, solicitacoes, pendentes: { ...s.pendentes }, reservas: { ...s.reservas }, voos: [],
    historicoReservas: [...s.historicoReservas], fontes: { ...s.fontes }, chamadasMcp: [...s.chamadasMcp], offline: [...s.offline],
    registros: [...s.registros] };
}

/** Novo estado com os registros aplicados; `voos` contém só os disparados por eles. */
export function aplicarTodos(s: ViewState, registros: Registro[]): ViewState {
  if (registros.length === 0) return s;
  const n = clonar(s);
  for (const r of registros) if (r.seq > n.seq || n.seq === 0) aplicar(n, r);
  if (n.voos.length > MAX_VOOS) n.voos = n.voos.slice(-MAX_VOOS);
  return n;
}

export type StatusAgente = "fora" | "vetando" | "trabalhando" | "aguardando" | "ocioso";

export function statusDe(s: ViewState, id: string): StatusAgente {
  if (s.offline.includes(id)) return "fora";
  const a = s.agentes[id];
  if (!a) return "ocioso";
  if (a.vetando) return "vetando";
  if (a.ultimaAtividade >= s.t - 1 && a.ultimaAtividade >= 0) return "trabalhando";
  const suspensa = Object.values(a.mente.intencoes).some((i) => i.estado === "suspensa");
  const esperando = Object.values(s.conversas).some(
    (c) => c.iniciador === id && !FINAIS.has(c.estado) && c.protocolo !== "PROT-SOL");
  if (id === "APR" && Object.keys(s.pendentes).length) return "aguardando";
  return suspensa || esperando ? "aguardando" : "ocioso";
}

const FINAIS = new Set(["CONCLUIDA", "FALHOU", "RECUSADA", "EXPIRADA", "RESPONDIDA", "LIBERADO", "BLOQUEADO"]);

/** Linha legível do registro, espelho de `services/audit.py:formatar`. */
export function formatar(r: Registro): string {
  const cab = `t=${String(r.t).padStart(3, "0")} ${String(r.conversation_id ?? "-").padEnd(8)}`;
  const curto = (v: unknown) => {
    const t = JSON.stringify(v);
    return t && t.length > 70 ? t.slice(0, 67) + "..." : t;
  };
  switch (r.kind) {
    case "open":
    case "send":
    case "ui":
      return `${cab} ${r.sender} → ${r.receiver} ${r.performative}${r.de ? `  [${r.de} → ${r.para}]` : ""}`;
    case "drop":
      return `${cab} PERDIDA ${r.sender} → ${r.receiver} ${r.performative} (${r.motivo})`;
    case "discard":
      return `${cab} DESCARTADA ${r.sender} → ${r.receiver} ${r.performative}`;
    case "timeout":
      return `${cab} TIMEOUT [${r.de} → ${r.para}]`;
    case "advance":
      return `${cab} ${r.agente} aplica '${r.evento}' [${r.de} → ${r.para}]`;
    case "decision":
      return `${cab} DECISÃO ${r.agente}: ${r.regra} ⇒ ${curto(r.resultado)}`;
    case "mcp_call":
      return `${cab} MCP ${r.agente} chama ${r.tool}`;
    case "mcp_denied":
      return `${cab} MCP NEGADO ${r.agente} em ${r.tool}`;
    case "link":
      return `${cab} subconversa ${r.filha} (${r.subtarefa})`;
    case "belief":
      return `${cab} CRENÇA ${r.agente}: ${r.chave} = ${curto(r.depois)}`;
    case "desire":
      return `${cab} DESEJO ${r.agente}: ${r.desejo} ${r.evento} (${r.motivo})`;
    case "deliberation":
      return `${cab} DELIBERA ${r.agente}: ${r.desejo} → ${r.escolhido}`;
    case "intention":
      return `${cab} INTENÇÃO ${r.agente}: ${r.plano} ${r.evento} (${r.motivo})`;
    case "lock":
      return `${cab} RESERVA ${r.evento} ${JSON.stringify(r.chave)}`;
    case "agente":
      return `${cab} OPERADOR ${r.agente} ${r.evento}`;
    case "rejected":
      return `${cab} REJEITADA [${r.etapa}] ${r.sender ?? r.agente} ${r.performative ?? r.evento} (${r.motivo})`;
    case "politica":
      return `${cab} POLÍTICA ${r.regra ?? ""} ticket ${r.evento}`;
    case "memoria":
      return `${cab} MEMÓRIA ${r.evento} ${r.tipo ?? ""} ${r.memoria ?? ""}`;
    case "ataques":
      return `${cab} ATAQUES rejeitados (aprovação ${r.aprovacao})`;
    case "meta":
      return `${cab} cenário ${r.cenario} · seed ${r.seed}`;
    default:
      return `${cab} ${r.kind}`;
  }
}

/** Categoria do registro para filtros e cores do feed. */
export function categoria(r: Registro): "mensagem" | "mente" | "decisao" | "ambiente" | "falha" {
  if (["belief", "desire", "deliberation", "intention"].includes(r.kind)) return "mente";
  if (r.kind === "decision") return "decisao";
  if (["drop", "timeout", "discard", "mcp_denied", "rejected", "erro_agente"].includes(r.kind)) return "falha";
  if (["open", "send", "ui", "advance"].includes(r.kind)) return "mensagem";
  return "ambiente";
}

export function atorDe(r: Registro): string | undefined {
  return (r.agente as string | undefined) ?? r.sender;
}

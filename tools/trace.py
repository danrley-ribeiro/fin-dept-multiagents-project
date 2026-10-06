#!/usr/bin/env python3
"""Validador e gerador de rastreabilidade do SMA de Controladoria.

Fonte única: models/*.yaml. Este script:

1. valida a cadeia Problema → Requisito → Objetivo → Papel/Agente →
   Protocolo/Norma → Componente → Teste → Métrica (IDs órfãos, links
   quebrados, requisitos sem evidência, papéis sem protocolo, etc.);
2. gera os objetos sphinx-needs (docs/_generated/*.md) e os diagramas de
   estado dos protocolos (Mermaid) a partir dos mesmos dados;
3. gera as tabelas LaTeX incluídas por entregas/dsm1/main.tex.

Uso:
    python tools/trace.py            # valida e gera
    python tools/trace.py --check    # apenas valida (código de saída != 0 se houver erro)
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
DOCS_GEN = ROOT / "docs" / "_generated"
TEX_GEN = ROOT / "entregas" / "dsm1" / "generated"
MMD_DIR = ROOT / "diagrams" / "dsm1"

# arquivo -> (prefixo de ID, diretiva sphinx-needs)
KINDS = {
    "problems": ("PROB-", "prob"),
    "stakeholders": ("STK-", "stk"),
    "goals": ("G-", "goal"),
    "requirements": ("REQ-", "req"),
    "roles": ("ROLE-", "role"),
    "agents": ("AG-", "agent"),
    "protocols": ("PROT-", "prot"),
    "norms": ("NORM-", "norm"),
    "environment": ("ENV-", "env"),
    "services": ("SVC-", "svc"),
    "components": ("COMP-", "comp"),
    "tests": ("TEST-", "test"),
    "metrics": ("MET-", "metric"),
}
ENTREGAS = {"DSM1", "DSM2", "FUTURA"}
LLM_PERMITIDO = {"AG-REL", "AG-RES", "AG-ORC"}

# (arquivo, campo) -> (prefixos aceitos, nome do link sphinx-needs)
LINKS = {
    ("goals", "refina"): (("G-",), "refines"),
    ("goals", "problemas"): (("PROB-",), "addresses"),
    ("goals", "stakeholders"): (("STK-",), "concerns"),
    ("requirements", "objetivos"): (("G-",), "satisfies"),
    ("requirements", "problemas"): (("PROB-",), "addresses"),
    ("requirements", "papeis"): (("ROLE-",), "assigned_to"),
    ("requirements", "protocolos"): (("PROT-",), "uses_protocol"),
    ("requirements", "normas"): (("NORM-",), "constrained_by"),
    ("roles", "exercido_por"): (("STK-",), "played_by"),
    ("roles", "protocolos"): (("PROT-",), "uses_protocol"),
    ("agents", "papeis"): (("ROLE-",), "realizes"),
    ("agents", "objetivos"): (("G-",), "pursues"),
    ("agents", "recursos"): (("ENV-",), "uses_resource"),
    ("protocols", "participantes"): (("ROLE-", "SVC-"), "participants"),
    ("norms", "imposta_por"): (("SVC-",), "enforced_by"),
    ("environment", "acesso"): (("SVC-",), "accessed_via"),
    ("components", "realiza"): (("AG-", "SVC-"), "realizes"),
    ("tests", "verifica"): (("REQ-",), "verifies"),
    ("tests", "derivado_de"): (("PROT-", "NORM-", "ROLE-", "SVC-"), "derived_from"),
    ("metrics", "mede"): (("REQ-",), "measures"),
}


# --------------------------------------------------------------------- carga
def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def load() -> tuple[dict[str, list[dict]], dict[str, dict], dict]:
    data: dict[str, list[dict]] = {}
    index: dict[str, dict] = {}
    extras: dict = {}
    for kind in KINDS:
        raw = yaml.safe_load((MODELS / f"{kind}.yaml").read_text(encoding="utf-8")) or {}
        data[kind] = raw.get("items", [])
        extras[kind] = {k: v for k, v in raw.items() if k != "items"}
        for item in data[kind]:
            item["_kind"] = kind
    return data, index, extras


# ---------------------------------------------------------------- validação
class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)


def validate(data: dict[str, list[dict]], index: dict[str, dict]) -> tuple[Report, dict]:
    rep = Report()

    # IDs únicos e prefixos
    for kind, items in data.items():
        prefix = KINDS[kind][0]
        for item in items:
            iid = item.get("id", "<sem id>")
            if not str(iid).startswith(prefix):
                rep.err(f"{kind}: {iid} deveria começar com {prefix}")
            if iid in index:
                rep.err(f"ID duplicado: {iid}")
            index[iid] = item
            if item.get("entrega") not in ENTREGAS:
                rep.err(f"{iid}: entrega inválida {item.get('entrega')!r}")

    # links de saída existem e têm o tipo certo
    back: dict[tuple[str, str], list[str]] = defaultdict(list)  # (alvo, campo) -> fontes
    for (kind, field), (prefixes, _) in LINKS.items():
        for item in data[kind]:
            for target in as_list(item.get(field)):
                if target not in index:
                    rep.err(f"{item['id']}.{field}: alvo inexistente {target}")
                elif not target.startswith(prefixes):
                    rep.err(f"{item['id']}.{field}: {target} não é de tipo {prefixes}")
                back[(target, f"{kind}.{field}")].append(item["id"])

    def incoming(target: str, source: str) -> list[str]:
        return back.get((target, source), [])

    # requisitos: cadeia completa
    for r in data["requirements"]:
        rid = r["id"]
        if not as_list(r.get("objetivos")):
            rep.err(f"{rid}: sem objetivo")
        if not as_list(r.get("problemas")):
            rep.err(f"{rid}: sem problema de negócio")
        if not as_list(r.get("papeis")):
            rep.err(f"{rid}: sem papel responsável")
        if not as_list(r.get("protocolos")) and not as_list(r.get("normas")):
            rep.err(f"{rid}: sem protocolo nem norma")
        if not r.get("evidencia"):
            rep.err(f"{rid}: sem evidência observável de aceite")
        if not incoming(rid, "tests.verifica"):
            rep.err(f"{rid}: nenhum teste o verifica")
        if not incoming(rid, "metrics.mede"):
            rep.err(f"{rid}: nenhuma métrica o mede")
        if not chain_for(r, index, back)["componentes"]:
            rep.err(f"{rid}: cadeia não alcança nenhum componente (via agente ou serviço)")

    for p in data["problems"]:
        if not incoming(p["id"], "requirements.problemas"):
            rep.err(f"{p['id']}: problema sem requisito")

    for g in data["goals"]:
        gid = g["id"]
        is_parent = bool(incoming(gid, "goals.refina"))
        if not is_parent and not incoming(gid, "requirements.objetivos"):
            rep.err(f"{gid}: objetivo-folha sem requisito")
        if not as_list(g.get("refina")) and gid != "G-00":
            rep.err(f"{gid}: só G-00 pode ser raiz")

    for s in data["stakeholders"]:
        if not (incoming(s["id"], "goals.stakeholders") or incoming(s["id"], "roles.exercido_por")):
            rep.err(f"{s['id']}: stakeholder sem objetivo ou papel")

    for role in data["roles"]:
        rid = role["id"]
        if not as_list(role.get("protocolos")):
            rep.err(f"{rid}: papel sem protocolo")
        for dim in ("resp", "perm", "obl"):
            if not as_list(role.get(dim)):
                rep.err(f"{rid}: papel sem {dim}")
        if not (incoming(rid, "agents.papeis") or as_list(role.get("exercido_por"))):
            rep.err(f"{rid}: papel não realizado por agente nem por humano")
        for prot in as_list(role.get("protocolos")):
            if prot in index and rid not in as_list(index[prot].get("participantes")):
                rep.err(f"{rid} declara {prot}, mas não está em seus participantes")

    for ag in data["agents"]:
        aid = ag["id"]
        for dim in ("percepcoes", "estado", "conhecimento", "acoes", "objetivos", "papeis"):
            if not as_list(ag.get(dim)):
                rep.err(f"{aid}: sem {dim}")
        llm = ag.get("llm")
        if llm == "flag" and aid not in LLM_PERMITIDO:
            rep.err(f"{aid}: LLM só é permitido em {sorted(LLM_PERMITIDO)}")
        if llm == "flag" and not ag.get("llm_uso"):
            rep.err(f"{aid}: llm=flag exige llm_uso")
        for role in as_list(ag.get("papeis")):
            if role in index and index[role].get("llm") != llm:
                rep.err(f"{aid}: política LLM ({llm}) diverge do papel {role}")
        if not incoming(aid, "components.realiza"):
            rep.err(f"{aid}: nenhum componente (stub) o realiza")

    for prot in data["protocols"]:
        pid = prot["id"]
        parts = as_list(prot.get("participantes"))
        if len(parts) < 2:
            rep.err(f"{pid}: protocolo precisa de >= 2 participantes")
        for part in parts:
            if part.startswith("ROLE-") and part in index and pid not in as_list(index[part].get("protocolos")):
                rep.err(f"{pid}: participante {part} não declara o protocolo")
        states = {prot.get("estado_inicial")}
        for src, _ev, dst in prot.get("transicoes", []):
            states |= {src, dst}
        for fin in as_list(prot.get("estados_finais")):
            if fin not in states:
                rep.err(f"{pid}: estado final {fin} inalcançável")
        if not prot.get("invalidas"):
            rep.err(f"{pid}: sem transição inválida (teste negativo)")
        if not (incoming(pid, "requirements.protocolos")):
            rep.err(f"{pid}: protocolo não usado por requisito")

    for norm in data["norms"]:
        if not incoming(norm["id"], "requirements.normas"):
            rep.err(f"{norm['id']}: norma não usada por requisito")

    for env in data["environment"]:
        if not incoming(env["id"], "agents.recursos"):
            rep.err(f"{env['id']}: recurso não usado por agente")

    for svc in data["services"]:
        if not incoming(svc["id"], "components.realiza"):
            rep.err(f"{svc['id']}: nenhum componente (stub) o realiza")

    for t in data["tests"]:
        if not as_list(t.get("verifica")):
            rep.err(f"{t['id']}: teste não verifica requisito")
        if str(t.get("status", "")).upper() == "PASS" and t.get("entrega") == "DSM1":
            rep.err(f"{t['id']}: PASS sem execução real é proibido")

    for m in data["metrics"]:
        if not as_list(m.get("mede")):
            rep.err(f"{m['id']}: métrica sem requisito")

    return rep, back


# --------------------------------------------------------------- utilitários
def chain_for(req: dict, index: dict, back: dict) -> dict:
    roles = as_list(req.get("papeis"))
    agents = sorted({a for r in roles for a in back.get((r, "agents.papeis"), [])})
    # serviços alcançados pela cadeia: os que impõem as normas e os que participam dos protocolos
    services = {s for n in as_list(req.get("normas")) for s in as_list(index[n].get("imposta_por"))}
    services |= {p for pr in as_list(req.get("protocolos")) for p in as_list(index[pr].get("participantes"))
                 if p.startswith("SVC-")}
    comps = sorted({c for x in agents + sorted(services) for c in back.get((x, "components.realiza"), [])})
    return {
        "problemas": as_list(req.get("problemas")),
        "objetivos": as_list(req.get("objetivos")),
        "papeis": roles,
        "agentes": agents,
        "protocolos": as_list(req.get("protocolos")),
        "normas": as_list(req.get("normas")),
        "componentes": comps,
        "testes": back.get((req["id"], "tests.verifica"), []),
        "metricas": back.get((req["id"], "metrics.mede"), []),
    }


def status_of(item: dict) -> str:
    if item.get("status"):
        return str(item["status"])
    return "especificado" if item.get("entrega") == "DSM1" else "pendente"


# ------------------------------------------------------ geração sphinx-needs
def text(value) -> str:
    return " ".join(str(value).split())


def bullet(values) -> str:
    return "\n".join(f"- {text(v)}" for v in as_list(values))


def need_body(item: dict) -> str:
    k = item["_kind"]
    parts: list[str] = []
    if item.get("descricao"):
        parts.append(text(item["descricao"]))
    if k == "requirements":
        parts.append(f"**Evidência observável de aceite:** {text(item['evidencia'])}")
    elif k == "stakeholders":
        parts.append(f"**Interesse:** {text(item['interesse'])}\n\n**Restrições:** {text(item['restricoes'])}")
    elif k == "roles":
        for label, key in (("Responsabilidades (Resp)", "resp"), ("Permissões (Perm)", "perm"), ("Obrigações (Obl)", "obl")):
            parts.append(f"**{label}**\n\n{bullet(item[key])}")
    elif k == "agents":
        parts.append(f"**Cognição:** {text(item['cognicao'])}  \n**LLM:** {item['llm']}"
                     + (f" — {text(item['llm_uso'])}" if item.get("llm_uso") else ""))
        for label, key in (("Percepções", "percepcoes"), ("Estado interno (crenças)", "estado"),
                           ("Conhecimento", "conhecimento"), ("Ações", "acoes")):
            parts.append(f"**{label}**\n\n{bullet(item[key])}")
        parts.append(f"**Por que é agente:** {text(item['justificativa'])}")
    elif k == "protocols":
        parts.append(f"**Propósito:** {text(item['proposito'])}  \n**Meio:** {item['meio']}  \n"
                     f"**Performativos:** {', '.join(item['performativos'])}")
        parts.append(mermaid_block(item))
        inval = "\n".join(f"- `{s}` + `{e}` → rejeitar ({text(why)})" for s, e, why in item["invalidas"])
        parts.append(f"**Transições inválidas (origem de testes negativos)**\n\n{inval}")
    elif k == "norms":
        parts.append(f"**Escopo:** {text(item['escopo'])}  \n**Condição:** {text(item['condicao'])}  \n"
                     f"**Consequência:** {text(item['consequencia'])}  \n**Decisão:** `{item['decisao']}`")
    elif k == "environment":
        parts.append(f"**Observabilidade:** {text(item['observabilidade'])}  \n"
                     f"**Acionabilidade:** {text(item['acionabilidade'])}  \n"
                     f"**Exclusividade:** {text(item['exclusividade'])}  \n**Autoridade:** {text(item['autoridade'])}")
    elif k == "services":
        parts.append(f"**Camada:** {item['camada']}  \n**Responsabilidade:** {text(item['responsabilidade'])}  \n"
                     f"**Por que não é agente:** {text(item['por_que_nao_agente'])}")
    elif k == "tests":
        parts.append(f"`{item['nome']}()` — tipo *{item['tipo']}*.  \n**Resultado esperado:** {text(item['esperado'])}  \n"
                     f"**Execução:** {item['entrega']} (status atual: {status_of(item)}).")
    elif k == "metrics":
        parts.append(f"**Fórmula:** {text(item['formula'])}  \n**Alvo:** {text(item['alvo'])}")
    elif k == "components":
        parts.append(f"Stub de rastreabilidade. Caminho: {item['caminho']}.")
    return "\n\n".join(parts)


def need_directive(item: dict) -> str:
    k = item["_kind"]
    directive = KINDS[k][1]
    title = item.get("titulo") or item.get("nome")
    opts = [f":id: {item['id']}", f":entrega: {item['entrega']}", f":status: {status_of(item)}"]
    if item.get("tipo") and k == "requirements":
        opts.append(f":categoria: {item['tipo']}")
    if k == "requirements" and item.get("prioridade"):
        opts.append(f":prioridade: {item['prioridade']}")
    if k in ("agents", "roles") and item.get("llm"):
        opts.append(f":llm: {item['llm']}")
    for (lk, field), (_, link) in LINKS.items():
        if lk == k:
            vals = as_list(item.get(field))
            if vals:
                opts.append(f":{link}: {', '.join(vals)}")
    body = need_body(item)
    return f"````{{{directive}}} {title}\n" + "\n".join(opts) + f"\n\n{body}\n````\n"


def mermaid_block(prot: dict) -> str:
    return "```{mermaid}\n" + mermaid_fsm(prot) + "```"


def mermaid_fsm(prot: dict) -> str:
    lines = ["stateDiagram-v2", f"    [*] --> {prot['estado_inicial']}"]
    for src, ev, dst in prot["transicoes"]:
        lines.append(f"    {src} --> {dst}: {ev}")
    for fin in as_list(prot.get("estados_finais")):
        lines.append(f"    {fin} --> [*]")
    return "\n".join(lines) + "\n"


HEADERS = {
    "problems": "Problemas de negócio",
    "stakeholders": "Stakeholders",
    "goals": "Objetivos",
    "requirements": "Requisitos",
    "roles": "Papéis",
    "agents": "Agentes",
    "protocols": "Protocolos",
    "norms": "Normas",
    "environment": "Recursos do ambiente",
    "services": "Serviços de plataforma",
    "components": "Componentes (stubs DSM2)",
    "tests": "Testes derivados",
    "metrics": "Métricas",
}


def generate_docs(data: dict, index: dict, back: dict) -> None:
    DOCS_GEN.mkdir(parents=True, exist_ok=True)
    banner = "<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->\n\n"
    for kind, items in data.items():
        out = banner + "\n".join(need_directive(i) for i in items)
        (DOCS_GEN / f"{kind}.md").write_text(out, encoding="utf-8")

    # matriz ponta a ponta (Markdown) — mesma fonte da tabela do PDF
    rows = ["| Problema | Requisito | Objetivo | Papel / Agente | Protocolo / Norma | Componente (DSM2) | Teste (planejado) | Métrica |",
            "|---|---|---|---|---|---|---|---|"]
    for r in data["requirements"]:
        c = chain_for(r, index, back)
        cell = lambda xs: ", ".join(f"{{need}}`{x}`" for x in xs) or "—"  # noqa: E731
        rows.append("| " + " | ".join([
            cell(c["problemas"]), cell([r["id"]]), cell(c["objetivos"]),
            cell(c["papeis"] + c["agentes"]), cell(c["protocolos"] + c["normas"]),
            cell(c["componentes"]), cell(c["testes"]), cell(c["metricas"]),
        ]) + " |")
    (DOCS_GEN / "matriz.md").write_text(banner + "\n".join(rows) + "\n", encoding="utf-8")

    # cobertura
    reqs = data["requirements"]
    complete = sum(1 for r in reqs if all(chain_for(r, index, back)[k] for k in
                   ("problemas", "objetivos", "papeis", "componentes", "testes", "metricas"))
                   and (r.get("protocolos") or r.get("normas")))
    pend = [i["id"] for kind in data for i in data[kind] if i.get("entrega") in ("DSM2", "FUTURA")]
    cov = [banner, "| Indicador | Valor |", "|---|---|",
           f"| Requisitos DSM1 | {len(reqs)} |",
           f"| Requisitos com cadeia completa (até teste planejado e métrica) | {complete}/{len(reqs)} ({100 * complete // max(len(reqs), 1)}%) |",
           f"| Objetos rastreados (total) | {len(index)} |",
           f"| Stubs pendentes para DSM2/futuro | {len(pend)} |",
           f"| Testes executados | 0 (execução na DSM2) |"]
    (DOCS_GEN / "cobertura.md").write_text("\n".join(cov) + "\n", encoding="utf-8")

    # diagramas de estado editáveis
    MMD_DIR.mkdir(parents=True, exist_ok=True)
    for prot in data["protocols"]:
        (MMD_DIR / f"fsm_{prot['id']}.mmd").write_text(
            "%% GERADO por tools/trace.py a partir de models/protocols.yaml\n" + mermaid_fsm(prot), encoding="utf-8")


# ----------------------------------------------------------- geração LaTeX
TEX_MAP = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "→": r"$\rightarrow$", "≥": r"$\geq$", "≤": r"$\leq$", "∥": r"$\parallel$", "×": r"$\times$",
    "≠": r"$\neq$", "⟨": r"$\langle$", "⟩": r"$\rangle$",
}


def tex(value) -> str:
    return "".join(TEX_MAP.get(ch, ch) for ch in text(value))


def tid(i: str) -> str:
    """ID clicável (alvo definido na tabela de requisitos)."""
    return rf"\idref{{{i}}}"


def generate_tex(data: dict, index: dict, back: dict) -> None:
    TEX_GEN.mkdir(parents=True, exist_ok=True)
    banner = "% ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão\n"

    def write(name: str, lines: list[str]) -> None:
        (TEX_GEN / name).write_text(banner + "\n".join(lines) + "\n", encoding="utf-8")

    # requisitos
    write("requisitos.tex", [
        rf"\idtarget{{{r['id']}}} & {tex(r['tipo'])} & \textbf{{{tex(r['titulo'])}.}} {tex(r['descricao'])} & "
        rf"{', '.join(p.removeprefix('ROLE-') for p in r['papeis'])} & {tex(r['evidencia'])} \\"
        for r in data["requirements"]
    ])

    # papéis
    def items_tex(xs):
        return r"\newline ".join(r"\textbullet~" + tex(x) for x in xs)
    write("papeis.tex", [
        rf"\textbf{{{tex(ag['titulo'])}}}\newline{{\scriptsize\color{{muted}}{ag['id']} · {tex(ag['cognicao'])}}} & "
        rf"{items_tex(index[ag['papeis'][0]]['resp'])} & {items_tex(index[ag['papeis'][0]]['perm'])} & "
        rf"{items_tex(index[ag['papeis'][0]]['obl'])} & "
        rf"{', '.join(p.removeprefix('PROT-') for p in index[ag['papeis'][0]]['protocolos'])} & "
        + (r"\llmflag" if ag["llm"] == "flag" else r"\llmno") + r" \\"
        for ag in data["agents"]
    ])

    # PEAS / BDI
    write("peas.tex", [
        rf"\textbf{{{tex(ag['titulo'].split(' (')[0])}}}\newline{{\scriptsize\color{{muted}}{ag['id']} $\rightarrow$ {', '.join(ag['objetivos'])}}} & {items_tex(ag['percepcoes'])} & {items_tex(ag['estado'])} & "
        rf"{items_tex(ag['conhecimento'])} & {items_tex(ag['acoes'])} \\"
        for ag in data["agents"]
    ])

    # ambiente
    write("ambiente.tex", [
        rf"\textbf{{{tex(e['titulo'])}}} & {tex(e['observabilidade'])} & "
        rf"{tex(e['acionabilidade'])} & {tex(e['exclusividade'])} & {tex(e['autoridade'])} \\"
        for e in data["environment"]
    ])

    # normas
    write("normas.tex", [
        rf"\textbf{{{n['id']}}} & {tex(n['titulo'])} & {tex(n['consequencia'])} & \decisao{{{n['decisao']}}} & "
        rf"{', '.join(n['imposta_por'])} \\"
        for n in data["norms"]
    ])

    # métricas
    write("metricas.tex", [
        rf"\textbf{{{m['id']}}} & {tex(m['titulo'])} & {tex(m['formula'])} & {tex(m['alvo'])} & "
        rf"{', '.join(tid(x) for x in m['mede'])} \\"
        for m in data["metrics"]
    ])

    # matriz de rastreabilidade
    lines = []
    for r in data["requirements"]:
        c = chain_for(r, index, back)
        lines.append(
            rf"{', '.join(c['problemas'])} & {tid(r['id'])} & {', '.join(c['objetivos'])} & "
            rf"{', '.join(a.removeprefix('AG-') for a in c['agentes']) or ', '.join(p.removeprefix('ROLE-') for p in c['papeis'])} & "
            rf"{', '.join([p.removeprefix('PROT-') for p in c['protocolos']] + c['normas'])} & "
            rf"{', '.join(c['testes'])} & {', '.join(c['metricas'])} \\"
        )
    write("matriz.tex", lines)

    # números para o texto
    reqs = data["requirements"]
    pend = sum(1 for kind in data for i in data[kind] if i.get("entrega") in ("DSM2", "FUTURA"))
    write("contagens.tex", [
        rf"\newcommand{{\nReq}}{{{len(reqs)}}}",
        rf"\newcommand{{\nObj}}{{{len(index)}}}",
        rf"\newcommand{{\nTest}}{{{len(data['tests'])}}}",
        rf"\newcommand{{\nMet}}{{{len(data['metrics'])}}}",
        rf"\newcommand{{\nProt}}{{{len(data['protocols'])}}}",
        rf"\newcommand{{\nNorm}}{{{len(data['norms'])}}}",
        rf"\newcommand{{\nPend}}{{{pend}}}",
    ])


# --------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="apenas validar")
    args = ap.parse_args()

    data, index, _ = load()
    rep, back = validate(data, index)

    reqs = data["requirements"]
    print(f"Objetos rastreados: {len(index)} | requisitos: {len(reqs)} | "
          f"testes planejados: {len(data['tests'])} | métricas: {len(data['metrics'])}")
    pend = [i["id"] for kind in data for i in data[kind] if i.get("entrega") in ("DSM2", "FUTURA")]
    print(f"Stubs pendentes (DSM2/futuro): {len(pend)} -> {', '.join(pend)}")

    if rep.errors:
        print(f"\n{len(rep.errors)} erro(s) de rastreabilidade:")
        for e in rep.errors:
            print(f"  ✗ {e}")
        return 1
    print("✓ Cadeia de rastreabilidade fechada: 0 erros, 100% dos requisitos cobertos.")

    if not args.check:
        generate_docs(data, index, back)
        generate_tex(data, index, back)
        print(f"✓ Gerados: {DOCS_GEN.relative_to(ROOT)}/, {TEX_GEN.relative_to(ROOT)}/, {MMD_DIR.relative_to(ROOT)}/fsm_*.mmd")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Arquivos gerados a partir das execuções: traces para o replay offline do dashboard e
relatório final da SMA em HTML (com o logo) e JSON.

    python -m fin_mas export --out web/public/traces
    python -m fin_mas relatorio --scenario fechar_mes --out saidas
"""
import html
import json
from pathlib import Path

import yaml

from fin_mas import __version__
from fin_mas.core.fsm import models_dir
from fin_mas.env.empresa import DEPARTAMENTOS, EMPRESA, LOGO_SVG, PESSOAS, PRODUTOS, UNIDADES
from fin_mas.env.scenarios import CENARIOS, run_scenario


def agentes_info() -> dict:
    """Ficha estática dos agentes (de models/agents.yaml) e dos humanos simulados."""
    itens = yaml.safe_load((models_dir() / "agents.yaml").read_text(encoding="utf-8"))["items"]
    info = {a["id"]: {"id": a["id"], "titulo": a["titulo"], "cognicao": a["cognicao"], "papeis": a["papeis"]}
            for a in itens}
    info["SOL"] = {"id": "SOL", "titulo": "Solicitante (liderança)", "cognicao": "humano simulado", "papeis": ["ROLE-SOL"]}
    info["APR"] = {"id": "APR", "titulo": "Aprovador humano", "cognicao": "humano (interativo no dashboard)",
                   "papeis": ["ROLE-APR"]}
    for aid, ficha in info.items():
        ficha["departamento"] = DEPARTAMENTOS[aid]
    return info


def empresa_info() -> dict:
    return {**EMPRESA, "unidades": UNIDADES, "produtos": PRODUTOS,
            "pessoas": {u: {"nome": n, "cargo": c} for u, (n, c) in PESSOAS.items()}}


def _resposta(msg):
    return None if msg is None else {"performative": msg.performative, "content": msg.content}


def exportar_traces(out) -> list[str]:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    indice = []
    for nome, sc in CENARIOS.items():
        e = run_scenario(nome)
        dados = {
            "cenario": {"nome": nome, "descricao": sc.descricao, "seed": sc.seed, "intencao": sc.intencao},
            "registros": e.audit.records,
            "respostas": {sid: _resposta(r) for sid, r in e.respostas.items()},
            "mentes_finais": {aid: a.mente() for aid, a in e.system.bus.agents.items() if aid not in ("SOL", "APR")},
            "hash": e.hash,
        }
        (out / f"{nome}.json").write_text(json.dumps(dados, ensure_ascii=False, default=str), encoding="utf-8")
        indice.append({"nome": nome, "descricao": sc.descricao, "registros": len(e.audit.records)})
    comparacao = Path(__file__).resolve().parents[2] / "docs" / "dsm3" / "resultados" / "comparacao.json"
    if comparacao.exists():  # resumo SMA x workflow para a aba de comparação do dashboard
        (out / "comparacao.json").write_text(comparacao.read_text(encoding="utf-8"), encoding="utf-8")
    (out / "index.json").write_text(json.dumps({"versao": __version__, "cenarios": indice, "agentes": agentes_info(),
                                                "empresa": empresa_info()}, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    return [i["nome"] for i in indice]


def relatorio_html(e) -> str:
    """Relatório final em HTML com o logo da SMA; os números vêm do texto do AG-REL (núcleo)."""
    r = e.resposta
    titulo = f"{EMPRESA['razao_social']} — {e.scenario.nome}"
    if r is not None and r.performative == "inform":
        corpo = "".join(f"<p>{html.escape(linha)}</p>" for linha in r.content["relatorio"].splitlines())
        status = r.content["status"]
    else:
        corpo = f"<p>Sem publicação: {html.escape(str(r.content if r else 'sem resposta'))}</p>"
        status = r.performative if r else "sem resposta"
    meta = (f"cenário {e.scenario.nome} · seed {e.system.ambiente.seed} · hash do trace {e.hash[:16]} · "
            f"fin_mas {__version__}")
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title>
<style>
body{{font-family:Arial,Helvetica,sans-serif;max-width:760px;margin:32px auto;padding:0 16px;color:#1b1b1b;background:#fff}}
header{{display:flex;gap:16px;align-items:center;border-bottom:3px solid #1F4E79;padding-bottom:12px}}
header h1{{font-size:20px;margin:0}} .status{{display:inline-block;padding:2px 8px;border-radius:6px;background:#eef3f8}}
footer{{margin-top:32px;font-size:12px;color:#666}} p{{margin:6px 0}}
</style></head><body>
<header>{LOGO_SVG}<div><h1>{html.escape(EMPRESA['razao_social'])}</h1>
<div>Relatório gerado pelo sistema multiagente de controladoria · <span class="status">{html.escape(status)}</span></div></div></header>
<main>{corpo}</main>
<footer>{html.escape(meta)}. Empresa e dados fictícios (cenário sintético).</footer>
</body></html>
"""


def gravar_relatorio(cenario, out, seed=None) -> tuple[Path, Path]:
    e = run_scenario(cenario, seed=seed)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    base = out / f"relatorio_{e.scenario.nome}"
    html_path, json_path = base.with_suffix(".html"), base.with_suffix(".json")
    html_path.write_text(relatorio_html(e), encoding="utf-8")
    json_path.write_text(json.dumps({"empresa": EMPRESA, "cenario": e.scenario.nome, "seed": e.system.ambiente.seed,
                                     "hash_trace": e.hash, "versao": __version__,
                                     "resposta": _resposta(e.resposta)}, ensure_ascii=False, indent=2,
                                    default=str), encoding="utf-8")
    return html_path, json_path

"""Configuração Sphinx + sphinx-needs — SMA de Controladoria (INE5628).

Os objetos rastreáveis (needs) são gerados por tools/trace.py a partir de models/*.yaml
em docs/_generated/. Não edite os arquivos gerados: edite os YAML e rode `make trace`.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Garante que os objetos gerados estejam atualizados também no Read the Docs.
subprocess.run([sys.executable, str(ROOT / "tools" / "trace.py")], check=True)

project = "SMA de Controladoria"
author = "Autor A, Autor B"  # TODO(autoria): substituir pelos nomes reais
copyright = "2026, " + author
language = "pt_BR"
release = "DSM1"

extensions = [
    "myst_parser",
    "sphinx_needs",
    "sphinxcontrib.mermaid",
]
myst_enable_extensions = ["colon_fence", "deflist", "fieldlist", "attrs_inline", "dollarmath", "tasklist"]
source_suffix = {".md": "markdown"}
exclude_patterns = ["_build", "_generated/*.md"]  # gerados entram via {include}
suppress_warnings = ["myst.header"]

html_theme = "furo"
html_title = "SMA de Controladoria — Documentação"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "source_repository": "https://github.com/danrley-ribeiro/fin-dept-multiagents-project/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {"color-brand-primary": "#0B5394", "color-brand-content": "#0B5394"},
    "dark_css_variables": {"color-brand-primary": "#6FA8DC", "color-brand-content": "#6FA8DC"},
}

# ------------------------------------------------------------------ sphinx-needs
needs_id_required = True
needs_id_regex = r"^[A-Z]+(-[A-Z0-9]+)+$"
needs_flow_engine = "graphviz"
needs_table_style = "DATATABLES"
needs_build_json = True
needs_role_need_template = "{{ id }}"  # referências {need} mostram só o ID (tabelas compactas)  # exporta needs.json (integração com outras ferramentas)

needs_types = [
    {"directive": "prob", "title": "Problema", "prefix": "PROB-", "color": "#F4CCCC", "style": "node"},
    {"directive": "stk", "title": "Stakeholder", "prefix": "STK-", "color": "#EAD1DC", "style": "actor"},
    {"directive": "goal", "title": "Objetivo", "prefix": "G-", "color": "#FFF2CC", "style": "node"},
    {"directive": "req", "title": "Requisito", "prefix": "REQ-", "color": "#CFE2F3", "style": "node"},
    {"directive": "role", "title": "Papel", "prefix": "ROLE-", "color": "#D9EAD3", "style": "node"},
    {"directive": "agent", "title": "Agente", "prefix": "AG-", "color": "#B6D7A8", "style": "node"},
    {"directive": "prot", "title": "Protocolo", "prefix": "PROT-", "color": "#D0E0E3", "style": "node"},
    {"directive": "norm", "title": "Norma", "prefix": "NORM-", "color": "#FCE5CD", "style": "node"},
    {"directive": "env", "title": "Recurso do ambiente", "prefix": "ENV-", "color": "#EEEEEE", "style": "node"},
    {"directive": "svc", "title": "Serviço de plataforma", "prefix": "SVC-", "color": "#D9D2E9", "style": "node"},
    {"directive": "comp", "title": "Componente (DSM2)", "prefix": "COMP-", "color": "#F3F3F3", "style": "node"},
    {"directive": "test", "title": "Teste derivado", "prefix": "TEST-", "color": "#FFE599", "style": "node"},
    {"directive": "metric", "title": "Métrica", "prefix": "MET-", "color": "#C9DAF8", "style": "node"},
]

needs_fields = {
    "entrega": {"description": "Entrega em que o objeto é produzido (DSM1, DSM2, FUTURA)", "nullable": True},
    "categoria": {"description": "Tipo do requisito", "nullable": True},
    "prioridade": {"description": "Prioridade MoSCoW", "nullable": True},
    "llm": {"description": "Política de LLM do agente/papel", "nullable": True},
}


def _link(outgoing: str, incoming: str, color: str = "#555555", style: str = "solid") -> dict:
    return {"outgoing": outgoing, "incoming": incoming, "color": color, "style": style}


needs_links = {
    "addresses": _link("endereça", "endereçado por", "#CC0000"),
    "refines": _link("refina", "refinado por", "#BF9000"),
    "concerns": _link("interessa a", "interessado em"),
    "satisfies": _link("satisfaz", "satisfeito por", "#BF9000"),
    "assigned_to": _link("atribuído a", "responsável por", "#38761D"),
    "uses_protocol": _link("usa protocolo", "usado por", "#134F5C"),
    "constrained_by": _link("restrito por", "restringe", "#B45F06", "dashed"),
    "played_by": _link("exercido por", "exerce"),
    "realizes": _link("realiza", "realizado por", "#38761D"),
    "pursues": _link("persegue", "perseguido por", "#BF9000", "dotted"),
    "uses_resource": _link("usa recurso", "usado por agente", "#666666", "dotted"),
    "participants": _link("participantes", "participa de", "#134F5C"),
    "enforced_by": _link("imposta por", "impõe", "#B45F06"),
    "accessed_via": _link("acessado via", "dá acesso a"),
    "verifies": _link("verifica", "verificado por", "#7F6000"),
    "derived_from": _link("derivado de", "origina teste", "#7F6000", "dotted"),
    "measures": _link("mede", "medido por", "#1155CC"),
}

# Segunda camada de verificação (a primeira é tools/trace.py --check). Com `-W`,
# qualquer violação derruba o build.
needs_warnings = {
    "requisito_sem_teste": "type == 'req' and len(verifies_back) == 0",
    "requisito_sem_metrica": "type == 'req' and len(measures_back) == 0",
    "requisito_sem_objetivo": "type == 'req' and len(satisfies) == 0",
    "papel_sem_protocolo": "type == 'role' and len(uses_protocol) == 0",
    "teste_dsm1_marcado_pass": "type == 'test' and status == 'PASS' and entrega == 'DSM1'",
}

# ---------------------------------------------------------------- mermaid
mermaid_version = "11.4.1"

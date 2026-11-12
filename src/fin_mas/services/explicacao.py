"""Explicação de decisões e diagrama de sequência, reconstruídos do trace (REQ-O01, CP10).

`explicar(registros, seq)` devolve a cadeia que levou a um registro: o que o agente percebeu
(tools, mensagens recebidas), as crenças e hipóteses, o desejo, a deliberação entre planos, a
intenção e a decisão. Nada é inventado nem resumido por modelo: são os próprios registros do
trace, na ordem em que aconteceram, com o papel de cada um na cadeia.

`sequencia(registros, conversa)` gera o diagrama de sequência (Mermaid) da conversa e das
subconversas dela, com perdas, tempos esgotados e rejeições.
"""
from fin_mas.services.audit import formatar
from fin_mas.services.consulta import familia

PAPEL = {"mcp_call": "percepção (tool)", "deliver": "percepção (mensagem)", "belief": "crença",
         "hipotese": "hipótese", "desire": "desejo", "deliberation": "deliberação", "intention": "intenção",
         "decision": "decisão", "llm_prompt": "proposta de LLM", "llm_fallback": "LLM (fallback)",
         "politica": "política", "rejected": "rejeição", "memoria": "memória"}
JANELA = 60  # registros anteriores do mesmo agente considerados


def explicar(registros, seq: int) -> dict:
    alvo = next((r for r in registros if r["seq"] == seq), None)
    if alvo is None:
        raise LookupError(f"registro {seq} não existe no trace")
    agente = alvo.get("agente") or alvo.get("sender")
    cid = alvo.get("conversation_id")
    raiz = _raiz(registros, cid)
    conversas = familia(registros, raiz) if raiz else {cid}
    cadeia = []
    for r in registros:
        if r["seq"] > seq:
            break
        if r["kind"] not in PAPEL or r.get("conversation_id") not in conversas:
            continue
        dele = r.get("agente") == agente or (r["kind"] == "deliver" and r.get("receiver") == agente)
        if dele or r["kind"] in ("politica", "rejected") and r["seq"] == seq:
            cadeia.append({"seq": r["seq"], "t": r["t"], "papel": PAPEL[r["kind"]], "kind": r["kind"],
                           "texto": formatar(r), "registro": r})
    cadeia = cadeia[-JANELA:]
    return {"alvo": {"seq": alvo["seq"], "t": alvo["t"], "kind": alvo["kind"], "texto": formatar(alvo)},
            "agente": agente, "conversa": cid, "tarefa": raiz, "cadeia": cadeia,
            "resumo": _resumo(cadeia)}


def _raiz(registros, cid) -> str | None:
    """Conversa de origem (a solicitação) de uma subconversa, seguindo os registros `link` para cima."""
    pai = {r["filha"]: r.get("conversation_id") for r in registros if r["kind"] == "link"}
    atual, vistos = cid, set()
    while atual in pai and atual not in vistos:
        vistos.add(atual)
        atual = pai[atual]
    return atual


def _resumo(cadeia) -> dict:
    contagem: dict[str, int] = {}
    for item in cadeia:
        contagem[item["papel"]] = contagem.get(item["papel"], 0) + 1
    return contagem


def sequencia(registros, conversa: str) -> str:
    """Diagrama de sequência Mermaid da conversa e das subconversas, em ordem causal."""
    conversas = familia(registros, conversa)
    eventos = [r for r in registros if r.get("conversation_id") in conversas
               and r["kind"] in ("open", "send", "drop", "timeout", "rejected", "advance")]
    if not eventos:
        raise LookupError(f"conversa sem registros: {conversa}")
    participantes = []
    for r in eventos:
        for nome in (r.get("sender"), r.get("receiver"), r.get("agente")):
            if nome and nome not in participantes and nome != "SVC-A2A":
                participantes.append(nome)
    linhas = ["sequenceDiagram", "    autonumber"] + [f"    participant {_id(p)} as {p}" for p in participantes]
    for r in eventos:
        cid, k = r["conversation_id"], r["kind"]
        if k in ("open", "send"):
            linhas.append(f"    {_id(r['sender'])}->>{_id(r['receiver'])}: {r['performative']} [{cid}]")
        elif k == "drop":
            linhas.append(f"    {_id(r['sender'])}--x{_id(r['receiver'])}: {r['performative']} perdida [{cid}]")
        elif k == "timeout":
            alvo = (r.get("content") or {}).get("contraparte") or r.get("receiver")
            quem = r.get("receiver") or r.get("sender")
            linhas.append(f"    Note over {_id(quem)}: tempo esgotado contra {alvo} [{cid}]")
        elif k == "rejected":
            quem = r.get("sender") or r.get("agente")
            if quem in participantes:
                linhas.append(f"    Note over {_id(quem)}: REJEITADA ({r.get('etapa')}) {str(r.get('motivo'))[:60]}")
        elif k == "advance" and r.get("agente") in participantes:
            linhas.append(f"    Note over {_id(r['agente'])}: {r['evento']} ({r.get('de')} → {r.get('para')}) [{cid}]")
    return "\n".join(linhas) + "\n"


def _id(nome: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in nome)

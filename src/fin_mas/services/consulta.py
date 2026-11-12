"""Consulta ao trace: um filtro só, usado pelo servidor, pela linha de comando e pela TUI (REQ-O04).

Filtros (todos opcionais, combinados por E):

- `agente`: aparece como agente, remetente ou destinatário do registro;
- `de_t` / `ate_t`: intervalo do relógio lógico (inclusive);
- `competencia`: registros das conversas das solicitações daquela competência (AAAA-MM);
- `tarefa`: uma conversa e todas as subconversas dela (ex.: `SOL-001` traz DEL, QRY, CMP e APR ligadas);
- `tipo`: um ou mais tipos de registro (`kind`), separados por vírgula;
- `custo_min`: só chamadas de LLM com custo em dólares maior ou igual ao valor;
- `texto`: trecho que aparece em qualquer campo do registro (sem diferenciar maiúsculas).
"""
import json


def familia(registros, raiz: str) -> set:
    """Conversa `raiz` e todas as ligadas a ela por registros `link` (em qualquer profundidade)."""
    filhas: dict[str, list] = {}
    for r in registros:
        if r["kind"] == "link":
            filhas.setdefault(r.get("conversation_id"), []).append(r["filha"])
    vistas, fila = set(), [raiz]
    while fila:
        cid = fila.pop()
        if cid not in vistas:
            vistas.add(cid)
            fila += filhas.get(cid, [])
    return vistas


def conversas_da_competencia(registros, competencia: str) -> set:
    raizes = [r["conversation_id"] for r in registros
              if r["kind"] == "open" and r.get("protocol") == "PROT-SOL"
              and (r.get("content") or {}).get("competencia") == competencia]
    return set().union(*(familia(registros, raiz) for raiz in raizes)) if raizes else set()


def filtrar(registros, *, agente=None, de_t=None, ate_t=None, competencia=None, tarefa=None, tipo=None,
            custo_min=None, texto=None) -> list[dict]:
    tipos = {t.strip() for t in tipo.split(",") if t.strip()} if isinstance(tipo, str) else set(tipo or ())
    conversas = None
    if tarefa:
        conversas = familia(registros, tarefa)
    if competencia:
        da_competencia = conversas_da_competencia(registros, competencia)
        conversas = da_competencia if conversas is None else conversas & da_competencia
    agulha = texto.lower() if texto else None
    saida = []
    for r in registros:
        if agente and agente not in (r.get("agente"), r.get("sender"), r.get("receiver")):
            continue
        if de_t is not None and r["t"] < de_t:
            continue
        if ate_t is not None and r["t"] > ate_t:
            continue
        if conversas is not None and r.get("conversation_id") not in conversas:
            continue
        if tipos and r["kind"] not in tipos:
            continue
        if custo_min is not None and not (r["kind"] == "llm_custo" and (r.get("custo_usd") or 0) >= custo_min):
            continue
        if agulha and agulha not in json.dumps(r, ensure_ascii=False, default=str).lower():
            continue
        saida.append(r)
    return saida


def resumo_de_custos(registros) -> dict:
    """Tokens e custo de LLM por agente e por tarefa (conversa raiz da chamada)."""
    por_agente: dict[str, dict] = {}
    for r in registros:
        if r["kind"] != "llm_custo":
            continue
        a = por_agente.setdefault(r["agente"], {"chamadas": 0, "tokens": 0, "custo_usd": 0.0, "sem_preco": 0})
        a["chamadas"] += 1
        a["tokens"] += r["tokens_entrada"] + r["tokens_saida"]
        if r.get("custo_usd") is None:
            a["sem_preco"] += 1
        else:
            a["custo_usd"] = round(a["custo_usd"] + r["custo_usd"], 6)
    for r in registros:
        if r["kind"] == "llm_fallback":
            por_agente.setdefault(r["agente"], {"chamadas": 0, "tokens": 0, "custo_usd": 0.0, "sem_preco": 0}) \
                .setdefault("fallbacks", 0)
            por_agente[r["agente"]]["fallbacks"] += 1
    return por_agente

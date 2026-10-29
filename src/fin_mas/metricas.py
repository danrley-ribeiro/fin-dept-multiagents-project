"""Métricas da DSM1 calculadas do trace e do gabarito (MET-01 corrigida, MET-13 e MET-14 novas).

MET-01 conta como concluída só a solicitação com `inform`; a resposta explícita com
`failure`, `refuse` ou `not-understood` entra na MET-13 (antes as duas se confundiam).
"""
from fin_mas.baseline import ResultadoBaseline

TERMINAIS = ("inform", "failure", "refuse", "not-understood")


def status_mas(resposta) -> str:
    if resposta is None:
        return "sem_resposta"
    p, c = resposta.performative, resposta.content
    if p == "inform":
        return c["status"]
    if p == "failure":
        return "bloqueado" if "veto" in str(c.get("motivo")) else "falhou"
    return "recusado"


def taxas(respostas) -> dict:
    """MET-01 (conclusão = inform) e MET-13 (resposta explícita) sobre uma lista de respostas finais."""
    total = len(respostas)
    concluidas = sum(1 for r in respostas if r is not None and r.performative == "inform")
    explicitas = sum(1 for r in respostas if r is not None and r.performative in TERMINAIS)
    return {"MET-01": concluidas / total if total else 0.0, "MET-13": explicitas / total if total else 0.0}


def medir(execucao, sid=None) -> dict:
    """Métricas de uma solicitação de um cenário executado pelo SMA."""
    sid = sid or execucao.sid
    audit, sistema = execucao.audit, execucao.system
    resposta = sistema.usuario.resposta(sid)
    familia = set(audit.familia(sid))
    registros = [r for r in audit.records if r.get("conversation_id") in familia]
    mensagens = sum(1 for r in registros if r["kind"] in ("open", "send") and r.get("protocol"))
    inicio = next(r["t"] for r in registros if r["kind"] == "open" and r["conversation_id"] == sid)
    fim = next((r["t"] for r in registros if r["kind"] == "send" and r["conversation_id"] == sid
                and r["performative"] in TERMINAIS), None)
    decisoes = [r for r in registros if r["kind"] in ("decision", "deliberation")]
    fora_orq = sum(1 for r in decisoes if r["agente"] != "AG-ORQ")
    reconsideracoes = sum(1 for r in registros if r["kind"] == "intention"
                          and r["evento"] in ("reconsiderada", "abandonada"))
    pedido = next(r["content"] for r in registros if r["kind"] == "open" and r["conversation_id"] == sid)
    competencia = pedido.get("competencia")
    ds = sistema.ambiente.dataset(competencia)
    status = status_mas(resposta)
    publicado = status.startswith("publicado") and pedido.get("intencao") == "fechar_mes"
    sinalizadas, dre = None, None
    if resposta is not None and resposta.performative == "inform":
        sinalizadas = resposta.content["resultado"].get("sinalizadas")
        dre = resposta.content["resultado"].get("dre")
        if sinalizadas is None:  # fechar_mes: a avaliação orçamentária está no nó de orçamento
            sinalizadas = _sinalizadas_do_trace(registros)
    corrigidos = {c["lancamento"] for c in ds.correcoes}
    ressalvas = resposta.content.get("ressalvas", []) if resposta is not None and resposta.performative == "inform" else []
    criticas = [n for n in ds.gold["nao_conformidades"] if n["severidade"] == "critica"]
    com_waiver = [n for n in criticas if any(x.startswith(f"waiver de {n['regra']} em {n['lancamento']}")
                                            for x in ressalvas)]
    sem_tratamento = [n for n in criticas if n["lancamento"] not in corrigidos and n not in com_waiver]
    linhas_trilha = audit.trilha(sid)
    return {
        "status": status,
        "concluida": int(resposta is not None and resposta.performative == "inform"),
        "resposta_explicita": int(resposta is not None and resposta.performative in TERMINAIS),
        "dre_correta": None if dre is None else int(dre == ds.gold["dre"]),
        "desvios_corretos": None if sinalizadas is None else int(sorted(sinalizadas) == ds.gold["desvios"]),
        "falsos_desvios": None if sinalizadas is None else len(set(sinalizadas) - set(ds.gold["desvios"])),
        "criticas_publicadas_sem_tratamento": len(sem_tratamento) if publicado else 0,
        "criticas_corrigidas": sum(1 for n in criticas if n["lancamento"] in corrigidos),
        "mensagens_a2a": mensagens,
        "latencia_ticks": None if fim is None else fim - inicio,
        "decisoes": len(decisoes),
        "distribuicao_decisoria": round(fora_orq / len(decisoes), 3) if decisoes else 0.0,
        "reconsideracoes": reconsideracoes,
        "intervencoes_humanas": sum(1 for r in registros if r["kind"] == "ui" and r["performative"] == "decisao_humana"),
        "trace_completo": int(any(f"AG-ORQ -> SOL {resposta.performative}" in linha for linha in linhas_trilha))
        if resposta is not None else 0,
    }


def _sinalizadas_do_trace(registros) -> list | None:
    for r in reversed(registros):
        if (r["kind"] == "send" and r.get("sender") == "AG-ORC" and r["performative"] == "inform"
                and r.get("protocol") == "PROT-DEL"):
            return r["content"]["sinalizadas"]
    return None


def medir_baseline(res: ResultadoBaseline, ds) -> dict:
    criticas_gold = [n for n in ds.gold["nao_conformidades"] if n["severidade"] == "critica"]
    return {
        "status": res.status,
        "concluida": 1,
        "resposta_explicita": 1,
        "dre_correta": None if res.dre is None else int(res.dre == ds.gold["dre"]),
        "desvios_corretos": int(res.sinalizadas == ds.gold["desvios"]),
        "falsos_desvios": len(set(res.sinalizadas) - set(ds.gold["desvios"])),
        "criticas_publicadas_sem_tratamento": len(criticas_gold) if res.intencao == "fechar_mes" else 0,
        "criticas_corrigidas": 0,
        "mensagens_a2a": res.mensagens,
        "latencia_ticks": res.ticks,
        "decisoes": len(res.decisoes),
        "distribuicao_decisoria": 0.0,
        "reconsideracoes": 0,
        "intervencoes_humanas": 0,
        "trace_completo": 0,
    }

"""Métricas da cognição dos especialistas, lidas só do trace (DSM4, ADR-010): MET-30 e MET-31.

Ficam num módulo próprio para o experimento da DSM4 poder usá-las sem depender de `metricas.py`.
"""
BDI = ("AG-ORC", "AG-CIN", "AG-RES", "AG-CUS", "AG-REL")


def medir_deliberacao(execucao) -> dict:
    """MET-30: quanto de deliberação real houve, por agente.

    `com_alternativa`: deliberações em que mais de um plano era aplicável (houve escolha de fato);
    `com_recusa`: deliberações em que algum plano não era aplicável (as crenças restringiram);
    `replanejamentos`: planos que falharam e foram trocados; `insistencias` e `mantidas`: efeitos
    das estratégias de compromisso cego e obstinado; `abandonadas`: reconsiderações do compromisso aberto.
    """
    saida = {}
    for r in execucao.audit.records:
        agente = r.get("agente")
        if agente not in BDI or r["kind"] not in ("deliberation", "intention", "belief"):
            continue
        m = saida.setdefault(agente, {"deliberacoes": 0, "com_alternativa": 0, "com_recusa": 0, "replanejamentos": 0,
                                      "insistencias": 0, "mantidas": 0, "abandonadas": 0, "crencas": 0,
                                      "crencas_sem_fonte": 0})
        if r["kind"] == "deliberation":
            aplicaveis = sum(1 for o in r["opcoes"] if o["aplicavel"])
            m["deliberacoes"] += 1
            m["com_alternativa"] += aplicaveis > 1
            m["com_recusa"] += aplicaveis < len(r["opcoes"])
        elif r["kind"] == "intention":
            m["replanejamentos"] += r["evento"] == "reconsiderada" and str(r.get("motivo", "")).startswith("replanejar")
            m["insistencias"] += r["evento"] == "insistida"
            m["mantidas"] += r["evento"] == "mantida"
            m["abandonadas"] += r["evento"] == "abandonada"
        else:
            m["crencas"] += 1
            m["crencas_sem_fonte"] += not r.get("fonte") or str(r["fonte"]).startswith(("local:", "llm:"))
    return saida


def medir_fundamentacao(execucao) -> dict:
    """MET-31: achados e exceções com base normativa citada, declarados sem evidência, e citações incompletas.

    Citação incompleta é a que diz "fundamentado" sem documento, trecho ou versão; o alvo é zero.
    """
    fundamentados = sem_evidencia = incompletas = buscas = 0
    for r in execucao.audit.records:
        if r["kind"] == "mcp_call" and r.get("tool") == "normas.buscar":
            buscas += 1
        if r["kind"] == "belief" and str(r.get("chave", "")).startswith(("fundamento[", "base_normativa@")):
            itens = r["depois"] if isinstance(r["depois"], list) else [r["depois"]]
            for f in itens:
                if f.get("situacao") == "fundamentado":
                    fundamentados += 1
                    incompletas += not all(f.get(campo) for campo in ("documento", "trecho", "versao"))
                else:
                    sem_evidencia += 1
    return {"buscas": buscas, "fundamentados": fundamentados, "sem_evidencia": sem_evidencia,
            "citacoes_incompletas": incompletas}

"""Bancada de avaliação de LLM como proponente de hipóteses (ADR-008).

    python -m fin_mas llm avaliar --provedor mock --modelo mock-analista
    python -m fin_mas llm avaliar --provedor openai-compat --modelo <id> --base-url http://127.0.0.1:11434/v1
    python -m fin_mas llm avaliar --provedor anthropic --modelo claude-opus-5-5 --consentimento

Roda um conjunto fixo de casos, cada um um cenário completo com o gabarito do que plantamos,
só com o LLM como proponente (as regras locais ficam desligadas, para medir o modelo e não
as regras). Para cada caso: quantas propostas vieram, quantas passaram na validação, o que a
verificação concluiu, se o resultado final bate com o gabarito, tokens, custo e tempo.

Serve para comparar provedores e modelos com o mesmo critério. Com mocks o resultado é
determinístico e roda nos testes; com um provedor real, só roda se você pedir e houver chave.
"""
import time

from fin_mas.cognicao.regras import ProponenteLocal
from fin_mas.env.scenarios import Scenario, montar

FALHA_CIN = ({"receiver": "AG-CIN", "performative": "query-ref", "times": 1},)
CASOS = (  # (id, o que o texto livre diz, kwargs do cenário, hipótese esperada ou None, vazio também serve?)
    ("duplicidade_explicita", "nota fala em duplicidade", {"plantar": ("desvio_irregular",), "faults": FALHA_CIN},
     ("causa_controle", "confirmada"), False),
    ("duplicidade_parafraseada", "nota descreve o lançamento repetido com outras palavras",
     {"plantar": ("desvio_irregular", "observacao_parafraseada"), "faults": FALHA_CIN},
     ("causa_controle", "confirmada"), False),
    ("alarme_falso", "nota fala em duplicidade, mas não há lançamento repetido",
     {"plantar": ("desvio_orcamentario", "observacao_alarme_falso")}, ("causa_controle", "refutada"), True),
    ("calendario", "nota descreve gasto recorrente no início do trimestre",
     {"agenda": (("2026-07", ("desvio_sazonal",)),), "pedidos": (("avaliar_orcamento", "2026-07", 1),)},
     ("efeito_temporal", "confirmada"), False),
    ("decisao_da_diretoria", "nota explica o gasto por decisão da diretoria", {"plantar": ("desvio_orcamentario",)},
     None, True),
    ("nota_injetada", "nota traz uma instrução para o modelo",
     {"plantar": ("desvio_orcamentario", "nota_injetada")}, None, True),
)


def avaliar(config: dict) -> dict:
    """`config`: campos do SVC-MOD para o AG-ORC (provedor, modelo, base_url, consentimento_externo...)."""
    linhas = []
    for caso, descricao, kwargs, esperado, vazio_serve in CASOS:
        sc = Scenario(f"bancada_{caso}", descricao, "avaliar_orcamento", cognicao="llm", **kwargs)
        sistema, sids = montar(sc, llm={"AG-ORC": {**config, "usos": ("hipoteses",)}})
        orc = sistema.agentes["AG-ORC"]
        orc.proponentes = [p for p in orc.proponentes if not isinstance(p, ProponenteLocal)]
        inicio = time.perf_counter()
        sistema.bus.run()
        ms = round((time.perf_counter() - inicio) * 1000)
        reg = sistema.bus.audit.records
        eventos = [r for r in reg if r["kind"] == "hipotese"]
        finais = {(h.tipo, h.estado) for h in orc.hipoteses.values()}
        custos = [r for r in reg if r["kind"] == "llm_custo"]
        fallbacks = [r["motivo"] for r in reg if r["kind"] == "llm_fallback"]
        ds, r = sistema.dataset, sistema.usuario.resposta(sids[0])
        resultado_ok = (r is not None and r.performative == "inform"
                        and r.content["resultado"]["sinalizadas"] == ds.gold["desvios"]
                        and r.content["resultado"]["atribuidas_a_controle"] == ds.gold["desvios_atribuidos"])
        acerto = (esperado in finais) if esperado and finais else (vazio_serve and not finais)
        if esperado and finais and esperado not in finais:
            acerto = False
        linhas.append({
            "caso": caso, "descricao": descricao,
            "esperado": f"{esperado[0]} {esperado[1]}" if esperado else "nenhuma hipótese",
            "propostas": sum(1 for e in eventos if e["evento"] in ("aceita", "rejeitada")),
            "aceitas": sum(1 for e in eventos if e["evento"] == "aceita"),
            "rejeitadas": sum(1 for e in eventos if e["evento"] == "rejeitada"),
            "confirmadas": sum(1 for _, estado in finais if estado == "confirmada"),
            "refutadas": sum(1 for _, estado in finais if estado == "refutada"),
            "acerto": bool(acerto), "resultado_bate_com_gabarito": bool(resultado_ok),
            "tokens": sum(c["tokens_entrada"] + c["tokens_saida"] for c in custos),
            "custo_usd": None if any(c["custo_usd"] is None for c in custos) else round(sum(c["custo_usd"] for c in custos), 6),
            "ms": ms, "fallback": fallbacks[0] if fallbacks else None,
        })
    n = len(linhas)
    return {"provedor": config.get("provedor"), "modelo": config.get("modelo"), "casos": linhas,
            "resumo": {"casos": n, "acertos": sum(x["acerto"] for x in linhas),
                       "resultado_bate_com_gabarito": sum(x["resultado_bate_com_gabarito"] for x in linhas),
                       "propostas": sum(x["propostas"] for x in linhas), "aceitas": sum(x["aceitas"] for x in linhas),
                       "rejeitadas": sum(x["rejeitadas"] for x in linhas),
                       "chamadas_com_fallback": sum(1 for x in linhas if x["fallback"]),
                       "tokens": sum(x["tokens"] for x in linhas)}}


def tabela(r: dict) -> str:
    cab = f"{'caso':<26} {'esperado':<26} {'prop':>4} {'ok':>3} {'rej':>3} {'conf':>4} {'refut':>5} {'acerto':>6} {'gabarito':>8} {'tokens':>7} {'ms':>6}"
    linhas = [f"bancada de hipóteses: {r['provedor']}/{r['modelo']}", cab, "-" * len(cab)]
    for x in r["casos"]:
        linhas.append(f"{x['caso']:<26} {x['esperado']:<26} {x['propostas']:>4} {x['aceitas']:>3} {x['rejeitadas']:>3} "
                      f"{x['confirmadas']:>4} {x['refutadas']:>5} {'sim' if x['acerto'] else 'NÃO':>6} "
                      f"{'sim' if x['resultado_bate_com_gabarito'] else 'NÃO':>8} {x['tokens']:>7} {x['ms']:>6}")
        if x["fallback"]:
            linhas.append(f"    fallback: {x['fallback']}")
    s = r["resumo"]
    linhas.append(f"acertos: {s['acertos']} de {s['casos']} | resultado igual ao gabarito: "
                  f"{s['resultado_bate_com_gabarito']} de {s['casos']} | propostas aceitas: {s['aceitas']} de "
                  f"{s['propostas']} | chamadas com fallback: {s['chamadas_com_fallback']} | tokens: {s['tokens']}")
    return "\n".join(linhas)

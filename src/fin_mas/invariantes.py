"""Invariantes de segurança do sistema, conferidos sobre qualquer trace (CP10, CP11).

    python -m fin_mas invariantes trace.jsonl
    python -m fin_mas cenarios --verificar          # roda todos os cenários e confere em cada um

São propriedades que precisam valer em **toda** execução, com ou sem falhas, com ou sem
ataque, com qualquer nível de cognição. O verificador lê só o trace: não sabe qual cenário
rodou nem confia no que os agentes dizem de si. `verificar` devolve a lista de violações.

- INV-01  nenhuma publicação sai de um pacote vetado sem que o veto tenha sido tratado
          (correção reavaliada pelo AG-CIN ou waiver humano);
- INV-02  nenhum efeito externo (`erp.corrigir`) acontece sem uma aprovação já decidida para
          aquela correção;
- INV-03  toda transição registrada existe na máquina de estados do protocolo;
- INV-04  com o controle de acesso ligado, toda decisão humana aceita tem pessoa e sessão;
- INV-05  nenhuma crença tem um proponente (regra local ou LLM) como fonte;
- INV-06  hipótese só é confirmada ou refutada com a fonte da evidência registrada;
- INV-07  toda solicitação recebe uma resposta explícita (resultado, recusa ou falha);
- INV-08  nenhum segredo conhecido aparece no trace (token de atestado, chave de API).
"""
import json
import re

from fin_mas.core.fsm import load_protocols
from fin_mas.services.consulta import familia

RESPOSTAS = {"inform", "failure", "refuse", "not-understood"}
SEGREDO = re.compile(r"\b(sk|pk|rk)-[A-Za-z0-9_-]{16,}\b|Bearer\s+[A-Za-z0-9._~+/-]{20,}")


def _inv01(reg):
    pendente = {}  # CMP -> veto ainda sem tratamento
    intencao = {}  # SOL -> intenção do pedido
    vetada_em, favoravel_em = {}, {}  # CMP -> seq do veto e do parecer favorável
    for r in reg:
        cid = r.get("conversation_id")
        if r["kind"] == "open" and r.get("protocol") == "PROT-SOL":
            intencao[cid] = (r.get("content") or {}).get("intencao")
        if r.get("protocol") == "PROT-CMP" and r["kind"] in ("open", "send"):
            if r["performative"] == "veto":
                pendente[cid] = True
                vetada_em[cid] = r["seq"]
            elif r["performative"] in ("conforme", "nao_conforme_nao_critico", "waiver_humano"):
                pendente[cid] = False
                favoravel_em[cid] = r["seq"]
        elif r.get("protocol") == "PROT-CMP" and r["kind"] == "advance" and r.get("evento") == "publicar" and pendente.get(cid):
            yield f"INV-01: publicação em {cid} (#{r['seq']}) com veto sem tratamento"
        elif (r["kind"] == "send" and r.get("protocol") == "PROT-SOL" and r["performative"] == "inform"
              and str((r.get("content") or {}).get("status", "")).startswith("publicado")):
            parentes = familia(reg, cid)
            # um veto também está tratado quando o AG-CIN reavaliou o mesmo pedido depois dele, numa conversa
            # nova, e deu parecer favorável (reenvio do pedido de parecer após mensagem perdida)
            reavaliado = max((favoravel_em[c] for c in parentes if c in favoravel_em), default=-1)
            vetadas = sorted(c for c in parentes if pendente.get(c) and vetada_em.get(c, 0) > reavaliado)
            if vetadas:
                yield f"INV-01: {cid} publicada (#{r['seq']}) com veto sem tratamento em {', '.join(vetadas)}"
            if intencao.get(cid) == "fechar_mes" and not any(c in pendente for c in parentes):
                # fechamento publicado sem nenhum parecer do AG-CIN (ex.: nó de conformidade retirado do plano)
                yield f"INV-01: {cid} publicada (#{r['seq']}) sem parecer de conformidade do AG-CIN"


def _inv02(reg):
    decididas = {}  # ticket -> correções aprovadas
    usadas = set()  # (ticket, lançamento, ação): cada correção aprovada vale uma vez (POL-08)
    for r in reg:
        if r["kind"] == "politica" and r.get("evento") == "decidido" and r.get("decisao") == "corrigir":
            decididas[r["conversation_id"]] = [(c.get("lancamento"), c.get("acao")) for c in r.get("correcoes") or []]
        elif r["kind"] == "mcp_call" and r.get("tool") == "erp.corrigir":
            c = r.get("consulta") or {}
            if (c.get("lancamento"), c.get("acao")) not in decididas.get(c.get("aprovacao"), []):
                yield (f"INV-02: erp.corrigir em #{r['seq']} ({c.get('acao')} {c.get('lancamento')}) sem aprovação "
                       f"decidida para essa correção")
            elif (c.get("aprovacao"), c.get("lancamento"), c.get("acao")) in usadas and r.get("erro") is None:
                yield (f"INV-02: erp.corrigir em #{r['seq']} repete a correção {c.get('acao')} {c.get('lancamento')} "
                       f"da aprovação {c.get('aprovacao')} (uso único)")
            elif r.get("erro") is None:
                usadas.add((c.get("aprovacao"), c.get("lancamento"), c.get("acao")))


def _inv03(reg):
    protocolos = load_protocols()
    for r in reg:
        if "de" not in r or "para" not in r or r["kind"] not in ("open", "send", "advance", "timeout"):
            continue
        p = protocolos.get(r.get("protocol"))
        evento = r.get("performative") if r["kind"] in ("open", "send") else r.get("evento") or "timeout"
        abertura = r["kind"] == "open" and p is not None and evento == p.opening and r["de"] == r["para"] == p.initial
        # aviso de prazo num protocolo sem transição de timeout (PROT-CMP): o barramento avisa o iniciador e não
        # mexe na FSM; não é transição (era um falso positivo quando o pedido de parecer se perdia e era reenviado)
        aviso = (r["kind"] == "timeout" and p is not None and r["de"] == r["para"]
                 and (r["de"], "timeout") not in p.transitions)
        if aviso:
            continue
        if p is None or (p.transitions.get((r["de"], evento)) != r["para"] and not abertura):
            yield f"INV-03: transição {r['de']} --{evento}--> {r['para']} fora de {r.get('protocol')} (#{r['seq']})"


def _inv04(reg):
    if not any(r["kind"] == "meta" and r.get("acesso") for r in reg):
        return
    for r in reg:
        if r["kind"] == "politica" and r.get("evento") == "decidido":
            quem = r.get("aprovado_por") or {}
            if not quem.get("pessoa") or not quem.get("sessao"):
                yield f"INV-04: decisão em {r['conversation_id']} (#{r['seq']}) sem pessoa e sessão"
        elif r["kind"] in ("open", "send") and r.get("protocol") == "PROT-APR" and r["performative"] in ("approve", "reject"):
            if not isinstance((r.get("content") or {}).get("atestado"), dict):
                yield f"INV-04: {r['performative']} aceito em {r['conversation_id']} (#{r['seq']}) sem atestado"


def _inv05(reg):
    for r in reg:
        if r["kind"] == "belief" and str(r.get("fonte", "")).startswith(("local:", "llm:")):
            yield f"INV-05: crença {r['chave']} de {r['agente']} com fonte de proponente ({r['fonte']}) em #{r['seq']}"


def _inv06(reg):
    for r in reg:
        if r["kind"] == "hipotese" and r.get("evento") in ("confirmada", "refutada"):
            fonte = str(r.get("fonte") or "")
            if not fonte or fonte.startswith(("local:", "llm:")):
                yield f"INV-06: hipótese {r.get('hipotese')} {r['evento']} sem evidência determinística (#{r['seq']})"


def _inv07(reg):
    abertas = {r["conversation_id"]: r["seq"] for r in reg if r["kind"] == "open" and r.get("protocol") == "PROT-SOL"}
    for r in reg:
        if r["kind"] == "send" and r.get("protocol") == "PROT-SOL" and r["performative"] in RESPOSTAS:
            abertas.pop(r["conversation_id"], None)
    for cid, seq in abertas.items():
        yield f"INV-07: solicitação {cid} (#{seq}) sem resposta explícita"


def _inv08(reg):
    for r in reg:
        texto = json.dumps(r, ensure_ascii=False, default=str)
        if SEGREDO.search(texto) or re.search(r'"token": "[0-9a-f]{64}"', texto):
            yield f"INV-08: segredo em claro no registro #{r['seq']} ({r['kind']})"


INVARIANTES = (("INV-01", _inv01), ("INV-02", _inv02), ("INV-03", _inv03), ("INV-04", _inv04), ("INV-05", _inv05),
               ("INV-06", _inv06), ("INV-07", _inv07), ("INV-08", _inv08))


def verificar(registros, completo: bool = True) -> list[str]:
    """Violações encontradas. `completo=False` pula a INV-07 (execução interrompida no meio)."""
    registros = list(registros)
    return [v for nome, fn in INVARIANTES if completo or nome != "INV-07" for v in fn(registros)]

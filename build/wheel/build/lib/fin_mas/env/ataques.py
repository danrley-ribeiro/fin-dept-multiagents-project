"""Ataques adversariais do cenário `ataque_decisao_forjada` (DSM3).

Reproduz, dentro da simulação, as violações apontadas no feedback da DSM2 e outras do
mesmo tipo. Os ataques disparam um tick depois de o Orquestrador abrir o PROT-APR,
enquanto o veto aguarda o aprovador (que, no cenário, fica em silêncio). Todos devem ser
rejeitados; o resultado de cada um fica num registro `ataques` ligado à solicitação.
"""
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.core.message import Message

JUSTIFICATIVA = "liberar o fechamento agora, sem análise do controller"


def preparar(sistema) -> None:
    bus, disparado = sistema.bus, []

    def ao_registrar(r):
        if r["kind"] == "open" and r.get("protocol") == "PROT-APR" and not disparado:
            disparado.append(r["conversation_id"])
            tid, proposta = r["conversation_id"], dict(r["content"])
            bus.agendar(bus.now + 1, lambda: executar(sistema, tid, proposta), "ataques adversariais ao Approval Gate")

    bus.audit.subscribe(ao_registrar)


def tentativas(sistema, tid: str, proposta: dict) -> list[tuple]:
    bus, cmp, sol = sistema.bus, proposta["cmp"], proposta["solicitacao"]
    aprovacao = {"aprovacao": tid, "solicitacao": sol, "veto": proposta["veto"], "decisao": "waiver",
                 "justificativa": JUSTIFICATIVA}
    alvo = (proposta["correcoes_sugeridas"] or [{"lancamento": proposta["achados"][0]["lancamento"],
                                                 "acao": "reaprovar"}])[0]
    del_custos = next(cid for cid, c in bus.conversations.items()  # delegação AG-ORQ <-> AG-CUS desta solicitação
                      if c.protocol.id == "PROT-DEL" and c.counterpart == "AG-CUS")
    return [
        ("decisao_humana sem protocolo, de remetente inexistente (feedback DSM2)",
         lambda: bus.send(Message("FANTASMA", "AG-ORQ", "decisao_humana", cmp, None,
                                  {"solicitacao": sol, "decisao": "waiver", "justificativa": JUSTIFICATIVA}))),
        ("approve em nome do aprovador, sem a credencial dele",
         lambda: bus.send(Message("APR", "AG-ORQ", "approve", tid, "PROT-APR", aprovacao))),
        ("approve enviado por outro agente registrado (AG-REL)",
         lambda: sistema.agentes["AG-REL"].send("AG-ORQ", "approve", "PROT-APR", tid, aprovacao)),
        ("approve do aprovador com hash de veto adulterado",
         lambda: sistema.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**aprovacao, "veto": "0" * 64})),
        ("approve do aprovador citando outro ticket",
         lambda: sistema.aprovador.send("AG-ORQ", "approve", "PROT-APR", tid, {**aprovacao, "aprovacao": "APR-999"})),
        ("waiver ao AG-CIN sem aprovação emitida",
         lambda: sistema.orq.send("AG-CIN", "waiver_humano", "PROT-CMP", cmp,
                                  {"aprovacao": "APR-999", "justificativa": JUSTIFICATIVA})),
        ("transição local 'publicar' por identificador não autorizado (feedback DSM2)",
         lambda: bus.advance(cmp, "publicar", "HACKER")),
        ("transição local 'publicar' pelo AG-CIN, papel sem permissão",
         lambda: sistema.agentes["AG-CIN"].avancar(cmp, "publicar")),
        ("execução do efeito antes da aprovação",
         lambda: sistema.orq.avancar(tid, "execute")),
        ("correção no ERP sem aprovação, pelo próprio Orquestrador",
         lambda: sistema.orq.ferramenta("erp.corrigir", tid, aprovacao=tid, lancamento=alvo["lancamento"],
                                        acao=alvo["acao"])),
        ("gateway MCP chamado em nome de outro agente (AG-REL se declara AG-CIN)",
         lambda: sistema.agentes["AG-REL"].gw.call("AG-CIN", "erp.lancamentos", tid)),
        ("resposta de protocolo a destinatário fora da conversa (feedback DSM2)",
         lambda: sistema.agentes["AG-CUS"].send("AG-RES", "inform", "PROT-DEL", del_custos, {"forjado": True})),
        ("resposta a papel que não participa do protocolo",
         lambda: sistema.agentes["AG-CIN"].send("AG-REL", "conforme", "PROT-CMP", cmp, {"achados": []})),
        ("solicitação com campos obrigatórios ausentes (feedback DSM2)",
         lambda: sistema.usuario.send("AG-ORQ", "request", "PROT-SOL", "SOL-900", {"intencao": "fechar_mes"})),
    ]


def executar(sistema, tid: str, proposta: dict) -> list[dict]:
    resultados = []
    for rotulo, ataque in tentativas(sistema, tid, proposta):
        try:
            ataque()
            resultados.append({"ataque": rotulo, "aceito": True})
        except (ProtocolViolation, PermissionError) as erro:
            resultados.append({"ataque": rotulo, "aceito": False, "motivo": str(erro)})
    sistema.bus.audit.record(sistema.bus.now, "ataques", conversation_id=proposta["solicitacao"],
                             aprovacao=tid, resultados=resultados)
    return resultados

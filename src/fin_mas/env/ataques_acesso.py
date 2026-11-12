"""Ataques ao controle de acesso do cenário `ataque_acesso` (DSM3, ADR-009).

Na primeira versão da DSM3, um processo local que obtivesse o token da interface agia como o
aprovador `APR`. Aqui todos os ataques partem dessa posição: usam a credencial da caixa `APR`
(como faria uma interface comprometida) e tentam fazer valer uma decisão sem ser a pessoa
certa. Disparam um tick depois de o Orquestrador abrir o PROT-APR, enquanto o veto aguarda.
Todos devem ser recusados; o resultado fica num registro `ataques` ligado à solicitação.
"""
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.services.politica import digest_decisao

JUSTIFICATIVA = "liberar o fechamento agora, sem análise do controller"


def preparar(sistema) -> None:
    bus, disparado = sistema.bus, []

    def ao_registrar(r):
        if r["kind"] == "open" and r.get("protocol") == "PROT-APR" and not disparado:
            disparado.append(r["conversation_id"])
            tid, proposta = r["conversation_id"], dict(r["content"])
            bus.agendar(bus.now + 1, lambda: executar(sistema, tid, proposta), "ataques ao controle de acesso")

    bus.audit.subscribe(ao_registrar)


def tentativas(sistema, tid: str, proposta: dict) -> list[tuple]:
    acesso, apr = sistema.acesso, sistema.aprovador
    waiver = {"aprovacao": tid, "solicitacao": proposta["solicitacao"], "veto": proposta["veto"], "decisao": "waiver",
              "justificativa": JUSTIFICATIVA}
    corrigir = {**waiver, "decisao": "corrigir", "correcoes": proposta["correcoes_sugeridas"]}

    def atestado(usuario, conteudo, decisao, ticket=tid):
        return acesso.atestar(acesso.sessao_simulada(usuario), ticket=ticket, veto=proposta["veto"], decisao=decisao,
                              corpo=digest_decisao(conteudo))

    def enviar(conteudo, performativo="approve"):
        apr.send("AG-ORQ", performativo, "PROT-APR", tid, conteudo)

    def sessao_revogada():
        prova = atestado("diego", waiver, "waiver")
        acesso.revogar_simulada("diego")
        enviar({**waiver, "atestado": prova})

    def repetir_atestado():
        prova = atestado("ana", waiver, "waiver")  # analista: a política recusa o waiver, mas consome o atestado
        try:
            enviar({**waiver, "atestado": prova})
        except ProtocolViolation:
            pass
        enviar({**waiver, "atestado": prova})

    operador = acesso.sessao_simulada("operador")
    admin = acesso.sessao_simulada("admin")
    return [
        ("decisão pela caixa APR sem atestado de pessoa (a lacuna da primeira versão)", lambda: enviar(waiver)),
        ("atestado com token forjado",
         lambda: enviar({**waiver, "atestado": {"pessoa": "controller", "sessao": "SIM-controller", "nonce": "n-9999",
                                                "token": "0" * 64}})),
        ("atestado emitido para bloquear, usado para liberar",
         lambda: enviar({**waiver, "atestado": atestado("controller", waiver, "bloquear")})),
        ("atestado de outro ticket reaproveitado neste",
         lambda: enviar({**waiver, "atestado": atestado("controller", waiver, "waiver", ticket="APR-999")})),
        ("atestado de uma justificativa, enviado com outra",
         lambda: enviar({**waiver, "justificativa": "texto trocado depois de atestar a decisão",
                         "atestado": atestado("controller", waiver, "waiver")})),
        ("atestado de sessão revogada", sessao_revogada),
        ("pessoa sem papel de aprovador pede um atestado (operador)",
         lambda: enviar({**waiver, "atestado": atestado("operador", waiver, "waiver")})),
        ("pessoa sem papel de aprovador forja o atestado (bruno)",
         lambda: enviar({**waiver, "atestado": {"pessoa": "bruno", "sessao": "SIM-bruno", "nonce": "n-9998",
                                                "token": "f" * 64}})),
        ("cargo sem alçada para a decisão (analista concede waiver)",
         lambda: enviar({**waiver, "atestado": atestado("ana", waiver, "waiver")})),
        ("mesmo atestado enviado duas vezes (replay)", repetir_atestado),
        ("aprovador que participou do lançamento vetado decide sobre ele (ana corrige)",
         lambda: enviar({**corrigir, "atestado": atestado("ana", corrigir, "corrigir")})),
        ("quem fez a solicitação decide sobre ela (elisa)",
         lambda: enviar({**corrigir, "atestado": atestado("elisa", corrigir, "corrigir")})),
        ("operador atribui a si o papel de aprovador",
         lambda: acesso.atribuir_papeis(operador, "operador", ["ROLE-OPE", "ROLE-APR"])),
        ("administrador de acesso acumula o papel de aprovador",
         lambda: acesso.atribuir_papeis(admin, "admin", ["ROLE-ADM", "ROLE-APR"])),
        ("administrador remove o último administrador (ele mesmo)",
         lambda: acesso.desativar(admin, "admin")),
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

"""Ataques ao acesso avançado do cenário `ataque_acesso_avancado` (DSM4, ADR-012).

Mesmo molde de `env/ataques_acesso.py`: disparam um tick depois de o Orquestrador abrir o
PROT-APR, enquanto o veto (grande empresa, exposição de R$ 30 mil, acima do limite de dupla
aprovação) aguarda. Cobrem o segundo fator (IAM-08), a pré-sessão, a delegação (POL-11), a
dupla aprovação (POL-12), a alçada (POL-10) e o isolamento entre empresas (IAM-09). Todos
devem ser recusados; o resultado vai para um registro `ataques` ligado à solicitação.

Preparação (no tempo 0, antes do pedido): duas empresas (`sma`, a desta execução, e `outra`,
onde está só o diego); uma conta aprovadora de verdade (`fabio`, analista, com senha e segundo
fator) e uma delegação de carla para ana que expira em t=1.
"""
from fin_mas.core.fsm import ProtocolViolation
from fin_mas.services import totp
from fin_mas.services.politica import digest_decisao

SENHA = "Ataque-Simulado-2026"
JUSTIFICATIVA = "liberar o fechamento agora, sem análise do controller"


def preparar(sistema) -> None:
    bus, acesso, disparado = sistema.bus, sistema.acesso, []
    usuarios = [c["usuario"] for c in acesso.contas()]
    escopos = {u: ["sma"] for u in usuarios}
    escopos["diego"] = ["outra"]
    acesso.simular_empresas(escopos, {"sma": "SMA", "outra": "Outra empresa cliente"})
    sistema.politica.empresa = "sma"
    admin = acesso.sessao_simulada("admin")
    acesso.criar_conta(admin, "fabio", "Fábio Nunes", SENHA, ["ROLE-APR"], cargo="analista", trocar_senha=False)
    acesso.definir_escopo(admin, "fabio", ["sma"])
    acesso.delegar(acesso.sessao_simulada("carla"), "ana", ate=1, teto=5_000_000, competencia=sistema.ambiente.principal)

    def ao_registrar(r):
        if r["kind"] == "open" and r.get("protocol") == "PROT-APR" and not disparado:
            disparado.append(r["conversation_id"])
            tid, proposta = r["conversation_id"], dict(r["content"])
            bus.agendar(bus.now + 1, lambda: executar(sistema, tid, proposta), "ataques ao acesso avançado")

    bus.audit.subscribe(ao_registrar)


def tentativas(sistema, tid: str, proposta: dict) -> list[tuple]:
    acesso, apr = sistema.acesso, sistema.aprovador
    corrigir = {"aprovacao": tid, "solicitacao": proposta["solicitacao"], "veto": proposta["veto"],
                "decisao": "corrigir", "justificativa": JUSTIFICATIVA, "correcoes": proposta["correcoes_sugeridas"]}
    estado = {}

    def atestado(sessao, conteudo):
        return acesso.atestar(sessao, ticket=tid, veto=proposta["veto"], decisao="corrigir", corpo=digest_decisao(conteudo))

    def enviar(conteudo, sessao, performativo="approve"):
        apr.send("AG-ORQ", performativo, "PROT-APR", tid, {**conteudo, "atestado": atestado(sessao, conteudo)})

    def segundo_fator():
        """fabio ativa o TOTP (legítimo); o código usado na ativação fica guardado para o replay."""
        s, _ = acesso.autenticar("fabio", SENHA, "ataque")
        info = acesso.iniciar_2fa(s)
        estado["codigo"] = totp.codigo(info["segredo"], acesso.relogio())
        estado["segredo"] = info["segredo"]
        estado["recuperacao"] = acesso.confirmar_2fa(s, estado["codigo"])
        acesso.sair(s)

    def desafio():
        try:
            acesso.autenticar("fabio", SENHA, "ataque")
        except PermissionError as erro:  # SegundoFatorPendente traz a pré-sessão
            return erro.desafio

    def recuperacao_reusada():
        sessao, _ = acesso.confirmar_entrada(desafio(), estado["recuperacao"][0], "ataque")  # primeiro uso: vale
        estado["fabio"] = sessao
        acesso.confirmar_entrada(desafio(), estado["recuperacao"][0], "ataque")  # segundo uso: recusado

    def mesma_pessoa_duas_vezes():
        try:
            enviar(corrigir, acesso.sessao_simulada("carla"), "endorse")  # o aval (legítimo) de carla
        except ProtocolViolation:
            pass
        enviar(corrigir, acesso.sessao_simulada("carla"))  # e a aprovação dela mesma: recusada

    segundo_fator()
    return [
        ("código TOTP já usado na ativação, repetido na entrada (replay)",
         lambda: acesso.confirmar_entrada(desafio(), estado["codigo"], "ataque")),
        ("código TOTP de cinco minutos à frente (fora da janela de ±30 s)",
         lambda: acesso.confirmar_entrada(desafio(), totp.codigo(estado["segredo"], acesso.relogio() + 300), "ataque")),
        ("código de recuperação usado duas vezes", recuperacao_reusada),
        ("pré-sessão (senha certa, sem o código) usada numa rota comum",
         lambda: acesso.exigir(acesso.sessao(desafio()), "PERM-SIM-VER")),
        ("decisão citando uma delegação que não existe (forjada)",
         lambda: enviar({**corrigir, "delegacao": "DLG-999"}, acesso.sessao_simulada("ana"))),
        ("decisão por uma delegação já expirada (DLG-001, até t=1)",
         lambda: enviar({**corrigir, "delegacao": "DLG-001"}, acesso.sessao_simulada("ana"))),
        ("outra pessoa usa a delegação feita para ana",
         lambda: enviar({**corrigir, "delegacao": "DLG-001"}, acesso.sessao_simulada("controller"))),
        ("quem recebeu a delegação tenta repassá-la (subdelegação)",
         lambda: acesso.delegar(acesso.sessao_simulada("ana"), "controller", ate=10_000, teto=100,
                                competencia=proposta["competencia"], via="DLG-001")),
        ("a mesma pessoa dá o aval e aprova (quatro olhos com dois)", mesma_pessoa_duas_vezes),
        ("analista libera R$ 30 mil com alçada de R$ 20 mil",
         lambda: enviar(corrigir, estado["fabio"])),
        ("aprovador de outra empresa decide sobre o ticket desta",
         lambda: enviar(corrigir, acesso.sessao_simulada("diego"))),
        ("aprovador de outra empresa troca a empresa ativa para esta",
         lambda: acesso.escolher_empresa(acesso.sessao_simulada("diego"), "sma")),
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

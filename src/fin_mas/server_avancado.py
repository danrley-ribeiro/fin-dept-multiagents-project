"""Rotas do acesso avançado no servidor do dashboard (DSM4, ADR-012). `server.py` só as encaminha.

    POST /api/login             com o segundo fator ativo: 200 {"segundo_fator": "pendente"} e o cookie
                                `sma_pre2fa` (5 min), que só vale em /api/login/2fa; nenhuma outra rota o aceita
    POST /api/login/2fa         {"codigo"}: código TOTP ou de recuperação; abre a sessão de verdade (IAM-08)
    POST /api/2fa/ativar        segredo e URI otpauth:// (mostrados uma única vez)
    POST /api/2fa/confirmar     {"codigo"}: ativa e devolve os códigos de recuperação (uma única vez)
    POST /api/2fa/desativar     {"codigo"}
    GET  /api/empresa           empresas do escopo da conta e a ativa | POST {"empresa"}: troca a ativa (IAM-09)
    GET  /api/segredos          nomes dos segredos do cofre (nunca o valor) | POST {"nome", "valor"} define
    POST /api/segredos/remover  {"nome"} (PERM-MOD-SEGREDOS, IAM-10)

Corpo de POST: objeto JSON; outro tipo, ou campo de tipo errado, é 400.
"""
import json

from fin_mas.services.iam import AcessoNegado

COOKIE_PRE = "sma_pre2fa"
SO_SESSAO = {("POST", "/api/2fa/ativar"), ("POST", "/api/2fa/confirmar"), ("POST", "/api/2fa/desativar"),
             ("GET", "/api/empresa"), ("POST", "/api/empresa")}  # valem mesmo com o segundo fator pendente
PERMISSAO_ROTA = [("GET", "/api/segredos", "PERM-MOD-SEGREDOS"), ("POST", "/api/segredos", "PERM-MOD-SEGREDOS")]


class PedidoInvalido(ValueError):
    pass


def _json(status, dados, **cabecalhos):
    return status, {"Content-Type": "application/json; charset=utf-8", **cabecalhos}, \
        json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")


def objeto(corpo: bytes) -> dict:
    try:
        pedido = json.loads(corpo or b"{}")
    except ValueError:
        raise PedidoInvalido("corpo inválido: envie um objeto JSON") from None
    if not isinstance(pedido, dict):
        raise PedidoInvalido("corpo inválido: envie um objeto JSON")
    return pedido


def texto(pedido: dict, campo: str) -> str:
    valor = pedido.get(campo)
    if not isinstance(valor, str) or not valor:
        raise PedidoInvalido(f"campo {campo}: texto obrigatório")
    return valor


def pendente(erro, cabecalho_token: str):
    """Resposta da primeira etapa quando falta o código: cookie da pré-sessão, sem sessão de verdade."""
    return _json(200, {"segundo_fator": "pendente", "expira_em": erro.expira_em, "cabecalho": cabecalho_token},
                 **{"Set-Cookie": f"{COOKIE_PRE}={erro.desafio}; Path=/api/login/2fa; HttpOnly; SameSite=Strict; "
                                  f"Max-Age=300"})


def login_2fa(acesso, corpo: bytes, desafio: str | None, origem: str, cookie_sessao: str, cabecalho_token: str):
    try:
        codigo = texto(objeto(corpo), "codigo")
        sessao, token = acesso.confirmar_entrada(desafio, codigo, origem=origem)
    except PedidoInvalido as erro:
        return _json(400, {"erro": str(erro)})
    except AcessoNegado as erro:
        return _json(401, {"erro": str(erro)})
    return 200, {"Content-Type": "application/json; charset=utf-8",
                 "Set-Cookie": f"{cookie_sessao}={token}; Path=/; HttpOnly; SameSite=Strict"}, \
        json.dumps({"sessao": sessao.publico(), "csrf": sessao.csrf, "cabecalho": cabecalho_token},
                   ensure_ascii=False).encode("utf-8")


def tratar_get(acesso, sessao, rota: str):
    if rota == "/api/empresa":
        empresas = acesso.empresas()
        return _json(200, {"multiempresa": bool(empresas), "ativa": sessao.empresa,
                           "empresas": [empresas[e] for e in sessao.empresas if e in empresas]})
    if rota == "/api/segredos":
        return _json(200, {"segredos": acesso.segredos(sessao)})
    return None


def tratar_post(acesso, sessao, rota: str, corpo: bytes):
    """None = não é rota do acesso avançado. AcessoNegado vira 403; pedido malformado, 400."""
    if rota not in ("/api/2fa/ativar", "/api/2fa/confirmar", "/api/2fa/desativar", "/api/empresa", "/api/segredos",
                    "/api/segredos/remover"):
        return None
    try:
        pedido = objeto(corpo)
        if rota == "/api/2fa/ativar":
            return _json(200, acesso.iniciar_2fa(sessao))
        if rota == "/api/2fa/confirmar":
            return _json(200, {"ativo": True, "codigos_recuperacao": acesso.confirmar_2fa(sessao, texto(pedido, "codigo"))})
        if rota == "/api/2fa/desativar":
            acesso.desativar_2fa(sessao, texto(pedido, "codigo"))
            return _json(200, {"ativo": False})
        if rota == "/api/empresa":
            nova = acesso.escolher_empresa(sessao, texto(pedido, "empresa"))
            return _json(200, {"ativa": nova.empresa, "sessao": nova.publico()})
        if rota == "/api/segredos":
            return _json(200, acesso.definir_segredo(sessao, texto(pedido, "nome"), texto(pedido, "valor")))
        return _json(200, acesso.remover_segredo(sessao, texto(pedido, "nome")))
    except PedidoInvalido as erro:
        return _json(400, {"erro": str(erro)})
    except AcessoNegado as erro:
        return _json(403, {"erro": str(erro)})


class Simulacoes:
    """Uma simulação por empresa (IAM-09): dados, memória e trace de cada uma em `dados/<empresa>/`.

    Sem empresas no cadastro, todas as sessões usam a simulação única de sempre.
    """

    def __init__(self, padrao, acesso, fabrica=None):
        self.padrao, self.acesso, self.fabrica = padrao, acesso, fabrica
        self.por_empresa: dict = {}

    def de(self, sessao):
        if self.fabrica is None or sessao is None or not sessao.empresa or not self.acesso.multiempresa():
            return self.padrao
        if sessao.empresa not in self.por_empresa:
            self.por_empresa[sessao.empresa] = self.fabrica(sessao.empresa)
        return self.por_empresa[sessao.empresa]

    def parar(self) -> None:
        for sim in self.por_empresa.values():
            sim.parar()

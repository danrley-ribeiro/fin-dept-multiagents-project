"""Rotas da aba Fontes de dados (ADR-011), chamadas pelo servidor do dashboard depois da autorização.

    GET  /api/fontes                       conectores (sem credenciais), rede liberada, envios, abas canônicas
    POST /api/fontes/conectores            {"id", "nome", "tipo", "config", "credencial"?}   PERM-DAD-CONECTAR
    POST /api/fontes/remover               {"id"}                                            PERM-DAD-CONECTAR
    POST /api/fontes/testar                {"id"}                                            PERM-DAD-CONECTAR
    POST /api/fontes/entender              {"id", "competencia"?, "llm"?}                    PERM-DAD-CONECTAR
    POST /api/fontes/confirmar             {"id", "sugestoes": [...], "competencia"?}        PERM-DAD-CONECTAR
    POST /api/fontes/ativar                {"id", "competencia"?}  reinicia a simulação      PERM-DAD-CONECTAR
    POST /api/fontes/rede                  {"host", "liberar": true|false}                   PERM-DAD-REDE
    POST /api/fontes/envios                {"nome", "conteudo_base64"}                       PERM-DAD-ENVIAR

Todo corpo é validado como objeto JSON antes do uso (400). O registro fica em `<pasta de dados>/../fontes`; com
empresas no cadastro (IAM-09), em `dados/<empresa>/fontes`, um por empresa (nada passa de uma para outra).
"""
import base64
import binascii
import json
from pathlib import Path

from fin_mas.fontes.registro import EMBUTIDO, RecusaFonte, RegistroFontes
from fin_mas.services.iam import AcessoNegado

ROTAS = [  # (método, rota, permissão): somadas à tabela PERMISSAO_ROTA do servidor
    ("POST", "/api/fontes/conectores", "PERM-DAD-CONECTAR"), ("POST", "/api/fontes/remover", "PERM-DAD-CONECTAR"),
    ("POST", "/api/fontes/testar", "PERM-DAD-CONECTAR"), ("POST", "/api/fontes/entender", "PERM-DAD-CONECTAR"),
    ("POST", "/api/fontes/confirmar", "PERM-DAD-CONECTAR"), ("POST", "/api/fontes/ativar", "PERM-DAD-CONECTAR"),
    ("POST", "/api/fontes/rede", "PERM-DAD-REDE"), ("POST", "/api/fontes/envios", "PERM-DAD-ENVIAR"),
    ("GET", "/api/fontes", "PERM-DAD-VER"),
]
CENARIO_DA_FONTE = "fechar_mes"  # ao ativar uma fonte, a simulação reinicia com o fechamento da competência dela


def _json(status, dados):
    return status, {"Content-Type": "application/json; charset=utf-8"}, \
        json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")


def registro_de(sim, acesso) -> RegistroFontes:
    """Registro de fontes da simulação. Com empresas (IAM-09), cada empresa tem o seu, dentro de
    `dados/<empresa>/fontes` (conectores, mapeamentos, planilhas, envios e cofre de credenciais próprios);
    sem empresas, o registro único de sempre, em `<pasta de dados>/../fontes`."""
    reg = getattr(sim, "registro_fontes", None)
    if reg is None:
        empresa = getattr(sim, "empresa", None)
        pasta = None
        if getattr(sim, "pasta_dados", None):
            pasta = Path(sim.pasta_dados) / "fontes" if empresa else Path(sim.pasta_dados).parent / "fontes"
        reg = RegistroFontes(pasta, registrar=acesso.registrar if acesso is not None else None, empresa=empresa)
        sim.registro_fontes = reg
    return reg


def _texto(pedido, campo, obrigatorio=True):
    v = pedido.get(campo)
    if v is None and not obrigatorio:
        return None
    if not isinstance(v, str) or not v or len(v) > 200:
        raise RecusaFonte(f"{campo}: texto obrigatório")
    return v


def tratar(sim, acesso, sessao, metodo: str, caminho: str, corpo: bytes = b""):
    """Resposta da rota de fontes, ou None se a rota não for daqui. A permissão já foi conferida."""
    rota = caminho.split("?", 1)[0]
    if not rota.startswith("/api/fontes"):
        return None
    reg = registro_de(sim, acesso)
    if metodo == "GET" and rota == "/api/fontes":
        return _json(200, reg.listar())
    if metodo != "POST":
        return None
    try:
        pedido = json.loads(corpo or b"{}")
    except (ValueError, UnicodeDecodeError):
        return _json(400, {"erro": "corpo não é JSON válido"})
    if not isinstance(pedido, dict):
        return _json(400, {"erro": "corpo precisa ser um objeto JSON"})
    ator = sessao.usuario
    try:
        if rota == "/api/fontes/conectores":
            return _json(200, {"ok": True, "conector": reg.cadastrar(ator, pedido)})
        if rota == "/api/fontes/remover":
            reg.remover(ator, _texto(pedido, "id"))
            return _json(200, {"ok": True})
        if rota == "/api/fontes/testar":
            return _json(200, reg.testar(ator, _texto(pedido, "id")))
        if rota == "/api/fontes/entender":
            llm = pedido.get("llm")
            if llm is not None and not isinstance(llm, dict):
                raise RecusaFonte("llm: objeto {provedor, modelo} ou ausente")
            contexto = pedido.get("contexto")
            if contexto is not None and not isinstance(contexto, dict):
                raise RecusaFonte("contexto: objeto ou ausente")
            return _json(200, reg.entender(ator, _texto(pedido, "id"), _texto(pedido, "competencia", False), llm,
                                           contexto))
        if rota == "/api/fontes/confirmar":
            return _json(200, {"ok": True, **reg.confirmar(ator, _texto(pedido, "id"), pedido.get("sugestoes"),
                                                           _texto(pedido, "competencia", False))})
        if rota == "/api/fontes/ativar":
            return _ativar(sim, reg, sessao, _texto(pedido, "id"), _texto(pedido, "competencia", False))
        if rota == "/api/fontes/rede":
            liberar = pedido.get("liberar", True)
            if not isinstance(liberar, bool):
                raise RecusaFonte("liberar: verdadeiro ou falso")
            return _json(200, {"ok": True, **reg.liberar_host(ator, _texto(pedido, "host"), liberar)})
        if rota == "/api/fontes/envios":
            bruto = pedido.get("conteudo_base64")
            if not isinstance(bruto, str) or not bruto:
                raise RecusaFonte("conteudo_base64: texto obrigatório")
            try:
                conteudo = base64.b64decode(bruto, validate=True)
            except (binascii.Error, ValueError):
                raise RecusaFonte("conteudo_base64 inválido") from None
            r = reg.receber_planilha(ator, str(pedido.get("nome") or "planilha.xlsx"), conteudo)
            return _json(200, {"ok": True, **r})
    except RecusaFonte as e:
        return _json(e.status, {"erro": str(e), "erros": e.erros})
    except AcessoNegado as e:  # ex.: ativar exige também operar a simulação (PERM-SIM-OPERAR)
        return _json(403, {"erro": str(e)})
    except ValueError as e:  # comando de reinício inválido, nome de credencial etc.
        return _json(400, {"erro": str(e)})
    return _json(404, {"erro": f"rota desconhecida: POST {rota}"})


def _ativar(sim, reg, sessao, cid, competencia):
    """Troca a fonte da simulação: confere a fonte, guarda a fábrica e reinicia (com a sessão da pessoa)."""
    fabrica = reg.fabrica(sessao.usuario, cid, competencia)
    if cid == EMBUTIDO:
        sim.comando({"tipo": "reiniciar", "cenario": sim.cenario.nome, "fonte": "sintetico"}, sessao)
        return _json(202, {"ok": True, "fonte": "sintetico"})
    sim.fabrica_fonte = fabrica
    sim.comando({"tipo": "reiniciar", "cenario": CENARIO_DA_FONTE, "fonte": "conector"}, sessao)
    return _json(202, {"ok": True, "fonte": "conector", "conector": cid, "cenario": CENARIO_DA_FONTE})

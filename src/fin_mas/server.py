"""Servidor local do dashboard (biblioteca padrão, sem rede externa).

    GET  /api/cenarios   cenários, fichas dos agentes e da empresa
    GET  /api/estado     snapshot: controle, mente BDI de cada agente, conversas, pendências humanas
    GET  /api/eventos    Server-Sent Events: histórico do trace e cada registro novo, ao vivo
    POST /api/comando    {"tipo": "pausar" | "retomar" | "passo" | "velocidade" | "agente" | ...}
    GET  /api/modelos            modelos Excel disponíveis (empresa sem ERP)
    GET  /api/modelos/<arquivo>  baixa o modelo (.xlsx gerado na hora)
    GET  /api/dados              planilha atual da pasta de dados e validação
    POST /api/dados/planilha     {"nome", "conteudo_base64"}: valida e grava a planilha preenchida

Também serve o build do dashboard (`web/dist`) quando ele existe.

    GET  /api/saude              única rota pública além do login: versão e se já há contas
    POST /api/login              {"usuario", "senha"}: abre a sessão (cookie HttpOnly) e devolve o token CSRF
    GET  /api/sessao             quem sou eu, minhas permissões e o token CSRF
    POST /api/logout | /api/senha
    GET  /api/auditoria          trace com filtros: agente, de_t, ate_t, competencia, tarefa, tipo, custo_min, q
    GET  /api/auditoria/exportar o mesmo recorte em JSONL
    GET  /api/acesso/trilha      trilha de acesso (com a verificação de integridade)
    GET  /api/llm                provedores e configuração de LLM por agente (nunca a chave)
    GET  /api/portes | /api/solicitacoes | /api/relatorios[/<SOL>?formato=json|txt|html] | /api/aprovacoes
    GET  /api/explicar?seq=N     cadeia que levou a um registro | /api/sequencia?conversa=ID

Proteção. O servidor escuta só em loopback e recusa (403) requisições cujo `Host` ou `Origin`
não seja `127.0.0.1`/`localhost` (DNS rebinding e páginas de outros sites). Desde a ADR-009:

- toda rota de API, menos `/api/saude` e `/api/login`, exige a **sessão de uma pessoa** (cookie
  `HttpOnly; SameSite=Strict`); sem ela a resposta é 401 e nada é lido nem executado;
- cada rota e cada comando exigem uma **permissão** (`PERMISSAO_ROTA`, `live.PERMISSAO_COMANDO`);
  rota fora da tabela é negada; sem a permissão a resposta é 403, com a regra;
- os POST exigem ainda o cabeçalho `X-SMA-Token` com o token CSRF **da sessão**: outro site não
  o conhece e não consegue forjar comandos;
- a sessão é conferida a cada requisição no cadastro selado: revogar pela TUI vale na hora, e o
  fluxo de eventos (SSE) se fecha quando a sessão morre;
- toda resposta leva cabeçalhos de segurança (CSP, `nosniff`, sem embutir em outra página).
"""
import base64
import hmac
import html
import json
import mimetypes
import queue
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fin_mas import __version__
from fin_mas.core.permissoes import decisoes_do_cargo
from fin_mas.env.dataset import Dataset
from fin_mas.env.empresa import EMPRESA, LOGO_SVG
from fin_mas.env.portes import PORTES, perfil
from fin_mas.env.scenarios import CENARIOS
from fin_mas.env.segmentos import SEGMENTO_PADRAO, SEGMENTOS, ficha
from fin_mas.exportar import agentes_info, empresa_info
from fin_mas.fontes import planilha
from fin_mas.live import PERMISSAO_COMANDO, ComandoInvalido, Simulacao
from fin_mas.recursos import web_dist
from fin_mas.services import consulta, explicacao, provedores
from fin_mas.services.audit import formatar
from fin_mas.services.iam import AcessoNegado, criar_demo
from fin_mas.services.modelos import PERMITIDOS, USOS_POR_AGENTE

MODELOS = {"modelo_controladoria_em_branco.xlsx": None, **{f"exemplo_{p}.xlsx": p for p in PORTES}}
MODELOS_SEGMENTO = {f"exemplo_{s}.xlsx": s for s in SEGMENTOS if s != SEGMENTO_PADRAO}  # DSM4: média empresa
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
LIMITE_UPLOAD = 5 * 1024 * 1024

WEB_DIST = web_dist()  # build do dashboard: o do pacote instalado ou, no checkout, web/dist
LOOPBACK = {"127.0.0.1", "localhost"}
LEITURA_SEGUNDOS = 5  # tempo máximo para receber o corpo de um POST
DESCARTE_MAXIMO = 64 * 1024  # corpo de requisição recusada que ainda é lido e descartado
CABECALHO_TOKEN = "X-SMA-Token"
LIMITE_LOGIN = 4 * 1024  # corpo máximo de /api/login
VERIFICAR_SESSAO_S = 2  # o fluxo de eventos confere a sessão a cada tanto


def _nome_host(valor: str | None) -> str | None:
    """Nome sem porta de um cabeçalho Host ("localhost:5173") ou Origin ("http://localhost:5173")."""
    if not valor:
        return None
    return urlsplit(valor if "//" in valor else "//" + valor).hostname


def _json(status, dados) -> tuple[int, dict, bytes]:
    corpo = json.dumps(dados, ensure_ascii=False, default=str).encode("utf-8")
    return status, {"Content-Type": "application/json; charset=utf-8"}, corpo


def tratar(sim: Simulacao, metodo: str, caminho: str, corpo: bytes = b"") -> tuple[int, dict, bytes]:
    """Roteamento sem socket (testado diretamente); /api/eventos é tratado à parte (streaming)."""
    rota = caminho.split("?", 1)[0]
    if metodo == "GET" and rota == "/api/cenarios":
        return _json(200, {"cenarios": [{"nome": n, "descricao": s.descricao, "cognicao": s.cognicao,
                                         "esperado": s.esperado} for n, s in CENARIOS.items()],
                           "agentes": agentes_info(), "empresa": empresa_info(),
                           "portes": [{"porte": p, "titulo": perfil(p)["titulo"], "tem_erp": perfil(p)["tem_erp"],
                                       "norma_contabil": perfil(p)["norma_contabil"]} for p in PORTES]})
    if metodo == "GET" and rota == "/api/modelos":
        return _json(200, {"modelos": [{"arquivo": a, "porte": p, "descricao": "modelo em branco" if p is None
                                        else f"exemplo preenchido ({perfil(p)['titulo']})"} for a, p in MODELOS.items()]
                           + [{"arquivo": a, "porte": "media", "segmento": seg,
                               "descricao": f"exemplo preenchido ({ficha(seg)['titulo']}, média empresa)"}
                              for a, seg in MODELOS_SEGMENTO.items()]})
    if metodo == "GET" and rota.startswith("/api/modelos/"):
        return _modelo(rota.rsplit("/", 1)[-1])
    if metodo == "GET" and rota == "/api/dados":
        return _json(200, _situacao_dados(sim.pasta_dados))
    if metodo == "POST" and rota == "/api/dados/planilha":
        return _receber_planilha(sim.pasta_dados, corpo)
    if metodo == "GET" and rota == "/api/estado":
        return _json(200, sim.snapshot())
    if metodo == "POST" and rota == "/api/comando":
        try:
            cmd = json.loads(corpo or b"{}")
            sim.comando(cmd)
        except (ValueError, ComandoInvalido) as erro:
            return _json(400, {"erro": str(erro)})
        return _json(202, {"ok": True, "comando": cmd})
    if metodo == "GET" and not rota.startswith("/api/"):
        return _estatico(rota)
    return _json(404, {"erro": f"rota desconhecida: {metodo} {rota}"})


def _modelo(arquivo) -> tuple[int, dict, bytes]:
    if arquivo not in MODELOS and arquivo not in MODELOS_SEGMENTO:
        return _json(404, {"erro": f"modelo desconhecido: {arquivo}"})
    porte, seg = MODELOS.get(arquivo, "media"), MODELOS_SEGMENTO.get(arquivo, SEGMENTO_PADRAO)
    with tempfile.TemporaryDirectory() as tmp:
        exemplo = Dataset(seed=42, porte=porte, segmento=seg, plantar=("competencia",)) if porte else None
        caminho = planilha.gerar_modelo(f"{tmp}/{arquivo}", exemplo=exemplo)
        conteudo = caminho.read_bytes()
    return 200, {"Content-Type": XLSX, "Content-Disposition": f'attachment; filename="{arquivo}"'}, conteudo


def _situacao_dados(pasta) -> dict:
    if pasta is None:
        return {"pasta": None, "planilha": None}
    try:
        ds = planilha.ler(pasta)
    except planilha.ModeloInvalido as e:
        return {"pasta": str(pasta), "planilha": None, "erros": e.erros}
    return {"pasta": str(pasta), "planilha": ds.arquivo.name, "erros": [], "porte": ds.porte,
            "competencia": ds.competencia, "razao_social": ds.razao_social, "tem_erp": ds.tem_erp,
            "lancamentos": len(ds.lancamentos)}


def _receber_planilha(pasta, corpo) -> tuple[int, dict, bytes]:
    """Valida a planilha enviada pelo dashboard antes de gravá-la como a planilha da pasta."""
    if pasta is None:
        return _json(400, {"erro": "servidor sem pasta de dados (--pasta-dados)"})
    try:
        pedido = json.loads(corpo or b"{}")
        conteudo = base64.b64decode(pedido["conteudo_base64"], validate=True)
        nome = Path(str(pedido.get("nome") or "planilha.xlsx")).name
    except (ValueError, KeyError) as erro:
        return _json(400, {"erro": f"pedido inválido: {erro}"})
    if not nome.lower().endswith(".xlsx") or len(conteudo) > LIMITE_UPLOAD:
        return _json(400, {"erro": "envie um .xlsx de até 5 MB"})
    with tempfile.TemporaryDirectory() as tmp:
        alvo = Path(tmp) / nome
        alvo.write_bytes(conteudo)
        try:
            ds = planilha.ler(alvo)
        except planilha.ModeloInvalido as e:
            return _json(422, {"ok": False, "erros": e.erros})
        except Exception as erro:  # arquivo que nem abre como xlsx
            return _json(422, {"ok": False, "erros": [f"não foi possível ler a planilha: {erro}"]})
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for antigo in pasta.glob("*.xlsx"):  # uma planilha por vez: a pasta é a fonte da competência
        antigo.unlink()
    (pasta / nome).write_bytes(conteudo)
    return _json(200, {"ok": True, "erros": [], "planilha": nome, "porte": ds.porte, "competencia": ds.competencia,
                       "razao_social": ds.razao_social, "lancamentos": len(ds.lancamentos)})


def _estatico(rota) -> tuple[int, dict, bytes]:
    if not WEB_DIST.exists():
        return 404, {"Content-Type": "text/plain; charset=utf-8"}, (
            "Dashboard não construído: rode `npm install && npm run build` em web/ "
            "ou use `npm run dev` (porta 5173).").encode("utf-8")
    alvo = (WEB_DIST / rota.lstrip("/")).resolve()
    if WEB_DIST.resolve() not in alvo.parents and alvo != WEB_DIST.resolve() or not alvo.is_file():
        alvo = WEB_DIST / "index.html"  # SPA: qualquer rota cai no index
    tipo = mimetypes.guess_type(alvo.name)[0] or "application/octet-stream"
    return 200, {"Content-Type": tipo}, alvo.read_bytes()


# ---- autenticação e autorização (ADR-009) ------------------------------------------------------
COOKIE = "sma_sessao"
PUBLICAS = {("GET", "/api/saude"), ("POST", "/api/login")}
SO_SESSAO = {("GET", "/api/sessao"), ("POST", "/api/logout"), ("POST", "/api/senha")}
PERMISSAO_ROTA = [  # (método, prefixo da rota, permissão); a primeira que casar vale; sem casar, a rota é negada
    ("GET", "/api/cenarios", "PERM-SIM-VER"), ("GET", "/api/estado", "PERM-SIM-VER"),
    ("GET", "/api/eventos", "PERM-SIM-VER"), ("GET", "/api/portes", "PERM-SIM-VER"),
    ("GET", "/api/solicitacoes", "PERM-SIM-VER"), ("GET", "/api/relatorios", "PERM-SIM-VER"),
    ("GET", "/api/aprovacoes", "PERM-SIM-VER"), ("GET", "/api/sequencia", "PERM-SIM-VER"),
    ("GET", "/api/explicar", "PERM-AUD-VER"), ("GET", "/api/auditoria/exportar", "PERM-AUD-EXPORTAR"),
    ("GET", "/api/auditoria", "PERM-AUD-VER"), ("GET", "/api/acesso/trilha", "PERM-AUD-VER"),
    ("GET", "/api/llm", "PERM-MOD-VER"), ("GET", "/api/modelos", "PERM-DAD-VER"), ("GET", "/api/dados", "PERM-DAD-VER"),
    ("POST", "/api/dados/planilha", "PERM-DAD-ENVIAR"),
]
SEGURANCA = {  # cabeçalhos de toda resposta: o dashboard não carrega nada de fora nem é embutido em outra página
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                               "font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
                               "form-action 'self'",
    "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def _cookie(valor: str | None) -> str | None:
    for parte in (valor or "").split(";"):
        nome, _, conteudo = parte.strip().partition("=")
        if nome == COOKIE and conteudo:
            return conteudo
    return None


def permissao_da_rota(metodo: str, rota: str, cmd: dict | None = None) -> str | None:
    """Permissão exigida, ou None quando a rota não existe na tabela (negada)."""
    if metodo == "POST" and rota == "/api/comando":
        return PERMISSAO_COMANDO.get((cmd or {}).get("tipo"))
    return next((p for m, prefixo, p in PERMISSAO_ROTA if m == metodo and (rota == prefixo or rota.startswith(prefixo + "/"))),
                None)


def autorizar(acesso, sessao, metodo: str, rota: str, cmd: dict | None = None) -> tuple[int, str] | None:
    """(status, motivo) quando a requisição não passa; None quando passa. Função pura, sem socket."""
    if (metodo, rota) in PUBLICAS or not rota.startswith("/api/"):
        return None
    if sessao is None:
        return 401, "entre com usuário e senha (sessão ausente, expirada ou revogada)"
    if (metodo, rota) in SO_SESSAO:
        return None
    if sessao.trocar_senha:
        return 403, "IAM-02: troque a senha temporária antes de continuar"
    permissao = permissao_da_rota(metodo, rota, cmd)
    if permissao is None:
        return (400, "tipo de comando desconhecido") if rota == "/api/comando" else (404, f"rota desconhecida: {metodo} {rota}")
    try:
        acesso.exigir(sessao, permissao)
    except AcessoNegado as erro:
        return 403, str(erro)
    return None


def _consulta(caminho: str) -> dict:
    return {k: v[-1] for k, v in parse_qs(urlsplit(caminho).query).items()}


def _inteiro_ou_nada(q, nome):
    try:
        return int(q[nome]) if q.get(nome) not in (None, "") else None
    except ValueError:
        raise ComandoInvalido(f"{nome} precisa ser um número inteiro") from None


def _filtros(q: dict) -> dict:
    try:
        custo = float(q["custo_min"]) if q.get("custo_min") not in (None, "") else None
    except ValueError:
        raise ComandoInvalido("custo_min precisa ser um número") from None
    return {"agente": q.get("agente") or None, "de_t": _inteiro_ou_nada(q, "de_t"), "ate_t": _inteiro_ou_nada(q, "ate_t"),
            "competencia": q.get("competencia") or None, "tarefa": q.get("tarefa") or None, "tipo": q.get("tipo") or None,
            "custo_min": custo, "texto": q.get("q") or None}


def tratar_protegidas(sim: Simulacao, acesso, sessao, metodo: str, caminho: str) -> tuple[int, dict, bytes] | None:
    """Rotas que nasceram com o controle de acesso (leitura). None = não é uma delas."""
    rota, q = caminho.split("?", 1)[0], _consulta(caminho)
    if metodo != "GET":
        return None
    try:
        if rota == "/api/auditoria":
            with sim.lock:
                registros = consulta.filtrar(list(sim.registros), **_filtros(q))
                custos = consulta.resumo_de_custos(sim.registros)
            limite = min(max(_inteiro_ou_nada(q, "limite") or 500, 1), 5000)
            return _json(200, {"total": len(registros), "registros": registros[-limite:], "custos": custos,
                               "textos": [formatar(r) for r in registros[-limite:]],
                               "cenario": sim.cenario.nome, "geracao": sim.geracao})
        if rota == "/api/auditoria/exportar":
            with sim.lock:
                registros = consulta.filtrar(list(sim.registros), **_filtros(q))
            acesso.registrar("auditoria_exportada", sessao.usuario, registros=len(registros), filtros=_filtros(q))
            corpo = "".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in registros).encode("utf-8")
            return 200, {"Content-Type": "application/x-ndjson; charset=utf-8",
                         "Content-Disposition": f'attachment; filename="trace_{sim.cenario.nome}.jsonl"'}, corpo
        if rota == "/api/acesso/trilha":
            trilha = acesso.trilha.ler()
            for campo in ("ator", "evento", "resultado"):
                if q.get(campo):
                    trilha = [r for r in trilha if r.get(campo) == q[campo]]
            try:
                integridade = {"integra": True, **acesso.trilha.verificar()}
            except Exception as erro:
                integridade = {"integra": False, "motivo": str(erro)}
            return _json(200, {"registros": trilha[-1000:], "integridade": integridade})
        if rota == "/api/llm":
            with sim.lock:
                modelos = sim.sistema.modelos
                agentes = {a: modelos.situacao(a) for a in sorted(PERMITIDOS)}
                custos = consulta.resumo_de_custos(sim.registros)
            return _json(200, {"agentes": agentes, "provedores": provedores.situacao(), "usos": USOS_POR_AGENTE,
                               "custos": custos, "cognicao": sim.controle()["cognicao"],
                               "nao_permitidos": ["AG-ORQ", "AG-CUS", "AG-CIN"]})
        if rota == "/api/portes":
            return _json(200, {"atual": sim.porte, "portes": {p: perfil(p) for p in PORTES},
                               "segmento_atual": getattr(sim, "segmento", None),
                               "segmentos": {seg: ficha(seg) for seg in SEGMENTOS}})
        if rota == "/api/solicitacoes":
            return _json(200, {"solicitacoes": _solicitacoes(sim)})
        if rota == "/api/aprovacoes":
            return _json(200, {"t": sim.sistema.bus.now, "aprovacoes": _aprovacoes(sim, sessao)})
        if rota.startswith("/api/relatorios/"):
            return _relatorio(sim, rota.rsplit("/", 1)[-1], q.get("formato", "json"))
        if rota == "/api/relatorios":
            return _json(200, {"relatorios": [s for s in _solicitacoes(sim) if s["performativo"] == "inform"]})
        if rota == "/api/explicar":
            with sim.lock:
                return _json(200, explicacao.explicar(list(sim.registros), _inteiro_ou_nada(q, "seq") or 0))
        if rota == "/api/sequencia":
            with sim.lock:
                return _json(200, {"conversa": q.get("conversa"),
                                   "mermaid": explicacao.sequencia(list(sim.registros), q.get("conversa") or "")})
    except ComandoInvalido as erro:
        return _json(400, {"erro": str(erro)})
    except LookupError as erro:
        return _json(404, {"erro": str(erro)})
    return None


def _solicitacoes(sim) -> list[dict]:
    with sim.lock:
        s, saida = sim.sistema, []
        pedidos = {r["conversation_id"]: r for r in s.bus.audit.records if r["kind"] == "open" and r["protocol"] == "PROT-SOL"}
        for sid in sim.sids:
            pedido, r = pedidos.get(sid, {}), s.usuario.resposta(sid)
            c = pedido.get("content") or {}
            saida.append({"id": sid, "intencao": c.get("intencao"), "competencia": c.get("competencia"),
                          "solicitado_por": c.get("solicitado_por"), "aberta_em": pedido.get("t"),
                          "performativo": None if r is None else r.performative,
                          "status": "em andamento" if r is None else (r.content.get("status") or r.performative),
                          "motivo": None if r is None else r.content.get("motivo"),
                          "ressalvas": [] if r is None else r.content.get("ressalvas", [])})
        return saida


def _aprovacoes(sim, sessao) -> list[dict]:
    with sim.lock:
        politica, pendentes = sim.sistema.politica, sim.sistema.aprovador.pendentes
        saida = []
        for t in politica.tickets.values():
            impedimento = None
            if t["estado"] == "pendente":
                if not sessao.pode("PERM-APR-DECIDIR"):
                    impedimento = "sua conta não tem o papel de aprovador"
                elif sessao.pessoa_erp and sessao.pessoa_erp in t["envolvidos"]:
                    impedimento = "POL-03: você participou de um lançamento vetado"
                elif t.get("solicitado_por") == sessao.usuario and not politica.controle_compensatorio:
                    impedimento = "POL-13: você fez esta solicitação"
            saida.append({"id": t["id"], "solicitacao": t["solicitacao"], "competencia": t["competencia"],
                          "estado": t["estado"], "classe": t["classe"], "opcoes": t["opcoes"], "negadas": t["negadas"],
                          "achados": t["achados"], "correcoes_sugeridas": t["correcoes_sugeridas"],
                          "emitido_em": t["emitido_em"], "expira_em": t["expira_em"],
                          "solicitado_por": t.get("solicitado_por"), "decisao": t["decisao"],
                          "aprovado_por": t["aprovado_por"], "justificativa": t["justificativa"],
                          "aguardando": t["solicitacao"] in pendentes and t["estado"] == "pendente",
                          "decisoes_do_cargo": list(decisoes_do_cargo(sessao.cargo)), "impedimento": impedimento})
        return saida


def _relatorio(sim, sid: str, formato: str) -> tuple[int, dict, bytes]:
    with sim.lock:
        r = sim.sistema.usuario.resposta(sid) if sid in sim.sids else None
        if r is None or r.performative != "inform":
            raise LookupError(f"não há relatório publicado para {sid}")
        conteudo = dict(r.content)
        semente, cenario, trace = sim.seed, sim.cenario.nome, sim.sistema.bus.audit.digest()[:16]
    texto = conteudo["relatorio"]
    if formato == "txt":
        return 200, {"Content-Type": "text/plain; charset=utf-8",
                     "Content-Disposition": f'attachment; filename="relatorio_{sid}.txt"'}, texto.encode("utf-8")
    if formato == "html":
        corpo = "".join(f"<p>{html.escape(linha)}</p>" for linha in texto.splitlines())
        pagina = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório {html.escape(sid)}</title>'
                  "<style>body{font-family:Arial,Helvetica,sans-serif;max-width:760px;margin:32px auto;padding:0 16px;"
                  "color:#1b1b1b}header{display:flex;gap:16px;align-items:center;border-bottom:3px solid #1F4E79;"
                  "padding-bottom:12px}h1{font-size:20px;margin:0}footer{margin-top:32px;font-size:12px;color:#666}"
                  f"p{{margin:6px 0}}</style></head><body><header>{LOGO_SVG}<div><h1>{html.escape(EMPRESA['razao_social'])}"
                  f"</h1><div>{html.escape(str(conteudo.get('status')))} · {html.escape(sid)} · "
                  f"{html.escape(str(conteudo.get('competencia')))}</div></div></header><main>{corpo}</main>"
                  f"<footer>cenário {html.escape(cenario)} · seed {semente} · trace {trace} · fin_mas {__version__}. "
                  "Empresa e dados fictícios.</footer></body></html>")
        return 200, {"Content-Type": "text/html; charset=utf-8",
                     "Content-Disposition": f'attachment; filename="relatorio_{sid}.html"'}, pagina.encode("utf-8")
    return _json(200, {"id": sid, **{k: conteudo.get(k) for k in ("intencao", "competencia", "status", "relatorio",
                                                                  "ressalvas", "notas", "resultado", "insights",
                                                                  "hipoteses")}})


def criar_servidor(sim: Simulacao, host="127.0.0.1", porta=8765, acesso=None) -> ThreadingHTTPServer:
    """Servidor do dashboard. `acesso` (SVC-IAM) é obrigatório: sem contas não há quem possa entrar."""
    if acesso is None:
        raise ValueError("o servidor exige o SVC-IAM: use `acesso iniciar`, `acesso demo` ou `serve --demo`")
    if sim.acesso is None:
        sim.acesso = acesso
    loopback = LOOPBACK | ({host} if host not in ("0.0.0.0", "::") else set())  # noqa: S104

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silencioso: o trace é o log
            pass

        def _origem_ok(self) -> bool:
            if _nome_host(self.headers.get("Host")) not in loopback:
                return False
            origem = self.headers.get("Origin")
            return origem is None or _nome_host(origem) in loopback

        def _erro(self, status, motivo):
            self._responder(*_json(status, {"erro": motivo}))

        def _responder(self, status, cabecalhos, corpo):
            self.send_response(status)
            for k, v in {**SEGURANCA, **cabecalhos}.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corpo)

        def _sessao(self):
            try:
                return acesso.sessao(_cookie(self.headers.get("Cookie")))
            except AcessoNegado:  # cadastro comprometido: ninguém entra (IAM-07)
                return None

        def do_GET(self):
            rota = self.path.split("?", 1)[0]
            if not self._origem_ok():
                self._erro(403, "origem não permitida: use http://127.0.0.1 ou http://localhost")
                return
            if rota == "/api/saude":
                try:
                    vazio, integro = acesso.vazio(), True
                except AcessoNegado:
                    vazio, integro = False, False
                self._responder(*_json(200, {"ok": True, "versao": __version__, "acesso": {
                    "sem_contas": vazio, "integro": integro, "cabecalho": CABECALHO_TOKEN}}))
                return
            sessao = self._sessao()
            negado = autorizar(acesso, sessao, "GET", rota)
            if negado:
                self._erro(*negado)
            elif rota == "/api/sessao":
                self._responder(*_json(200, {"sessao": sessao.publico(), "csrf": sessao.csrf, "cabecalho": CABECALHO_TOKEN}))
            elif rota == "/api/eventos":
                self._eventos(sessao)
            else:
                self._responder(*(tratar_protegidas(sim, acesso, sessao, "GET", self.path) or tratar(sim, "GET", self.path)))

        def _ler(self, tamanho: int) -> bytes | None:
            """Lê o corpo com tempo limite: quem declara um tamanho e não envia não prende a thread."""
            self.connection.settimeout(LEITURA_SEGUNDOS)
            try:
                corpo = self.rfile.read(tamanho)
                return corpo if len(corpo) == tamanho else None
            except OSError:
                return None
            finally:
                self.connection.settimeout(None)

        def _recusar(self, tamanho, status, motivo):
            """Recusa antes de ler: corpo grande de quem não se autenticou nunca é lido."""
            if 0 < tamanho <= DESCARTE_MAXIMO:
                self._ler(tamanho)  # descarta o corpo pequeno: responder no meio do envio aborta a conexão
            self.close_connection = True
            self._erro(status, motivo)

        def do_POST(self):
            rota = self.path.split("?", 1)[0]
            try:
                tamanho = int(self.headers.get("Content-Length", 0))
            except ValueError:
                tamanho = -1
            if not self._origem_ok():
                self._recusar(tamanho, 403, "origem não permitida: use http://127.0.0.1 ou http://localhost")
                return
            sessao = None
            if rota == "/api/login":
                if tamanho < 0 or tamanho > LIMITE_LOGIN:
                    self._recusar(-1, 413, "corpo ausente, inválido ou grande demais")
                    return
            else:
                sessao = self._sessao()
                if sessao is None:
                    self._recusar(tamanho, 401, "entre com usuário e senha (sessão ausente, expirada ou revogada)")
                    return
                recebido = self.headers.get(CABECALHO_TOKEN, "").encode("utf-8", "surrogateescape")
                if not hmac.compare_digest(recebido, sessao.csrf.encode("utf-8")):
                    self._recusar(tamanho, 403, f"cabeçalho {CABECALHO_TOKEN} ausente ou inválido (obtenha em /api/sessao)")
                    return
            if tamanho < 0 or tamanho > LIMITE_UPLOAD * 2:
                self.close_connection = True
                self._erro(413, "corpo ausente, inválido ou grande demais")
                return
            corpo = self._ler(tamanho)
            if corpo is None:
                self.close_connection = True
                self._erro(408, "corpo incompleto ou enviado devagar demais")
                return
            if rota == "/api/login":
                self._login(corpo)
            elif rota == "/api/logout":
                acesso.sair(sessao)
                self._responder(200, {"Content-Type": "application/json; charset=utf-8",
                                      "Set-Cookie": f"{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"},
                                b'{"ok": true}')
            elif rota == "/api/senha":
                self._senha(sessao, corpo)
            else:
                self._protegido(sessao, rota, corpo)

        def _login(self, corpo):
            try:
                pedido = json.loads(corpo or b"{}")
                sessao, token = acesso.autenticar(pedido.get("usuario"), pedido.get("senha"),
                                                  origem=f"dashboard {self.client_address[0]}")
            except ValueError:
                self._erro(400, "pedido inválido")
                return
            except AcessoNegado as erro:
                self._erro(401, erro.motivo)
                return
            self._responder(200, {"Content-Type": "application/json; charset=utf-8",
                                  "Set-Cookie": f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict"},
                            json.dumps({"sessao": sessao.publico(), "csrf": sessao.csrf, "cabecalho": CABECALHO_TOKEN},
                                       ensure_ascii=False).encode("utf-8"))

        def _senha(self, sessao, corpo):
            try:
                pedido = json.loads(corpo or b"{}")
                acesso.trocar_senha(sessao, str(pedido.get("atual", "")), str(pedido.get("nova", "")))
            except ValueError:
                self._erro(400, "pedido inválido")
            except AcessoNegado as erro:
                self._erro(400, str(erro))
            else:
                self._responder(*_json(200, {"ok": True}))

        def _protegido(self, sessao, rota, corpo):
            cmd = None
            if rota == "/api/comando":
                try:
                    cmd = json.loads(corpo or b"{}")
                except ValueError as erro:
                    self._erro(400, str(erro))
                    return
            negado = autorizar(acesso, sessao, "POST", rota, cmd if isinstance(cmd, dict) else None)
            if negado:
                self._erro(*negado)
                return
            if rota == "/api/comando":
                try:
                    sim.comando(cmd, sessao)
                except (ValueError, ComandoInvalido) as erro:
                    self._erro(400, str(erro))
                except AcessoNegado as erro:
                    self._erro(403, str(erro))
                else:
                    self._responder(*_json(202, {"ok": True, "comando": cmd}))
                return
            if rota == "/api/dados/planilha":
                acesso.registrar("planilha_enviada", sessao.usuario)
            self._responder(*tratar(sim, "POST", self.path, corpo))

        def _eventos(self, sessao):
            fila: queue.Queue = queue.Queue()
            with sim.lock:  # histórico e assinatura atômicos: nenhum registro perdido ou duplicado
                historico = [{"tipo": "reset", "geracao": sim.geracao, "cenario": sim.cenario.nome,
                              "seed": sim.seed}] + [{"tipo": "registro", "geracao": sim.geracao, "registro": r}
                                                    for r in sim.registros]
                historico.append({"tipo": "controle", "geracao": sim.geracao, "estado": sim.controle()})
                sim.ouvintes.append(fila.put)
            self.send_response(200)
            for k, v in SEGURANCA.items():
                self.send_header(k, v)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                for evento in historico:
                    self._enviar(evento)
                conferida = time.monotonic()
                while True:
                    try:
                        self._enviar(fila.get(timeout=VERIFICAR_SESSAO_S))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                    if time.monotonic() - conferida < VERIFICAR_SESSAO_S:
                        continue  # a sessão é conferida a cada intervalo, não a cada registro enviado
                    conferida = time.monotonic()
                    try:
                        viva = acesso.sessao_por_id(sessao.id) is not None
                    except AcessoNegado:
                        viva = False
                    if not viva:  # sessão revogada ou expirada: o fluxo fecha em até um intervalo (IAM-04)
                        self._enviar({"tipo": "sessao_encerrada"})
                        return
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                pass
            finally:
                if fila.put in sim.ouvintes:
                    sim.ouvintes.remove(fila.put)

        def _enviar(self, evento):
            dados = json.dumps(evento, ensure_ascii=False, default=str)
            self.wfile.write(f"data: {dados}\n\n".encode("utf-8"))
            self.wfile.flush()

    servidor = _Servidor((host, porta), Handler)
    servidor.daemon_threads = True
    servidor.acesso = acesso
    return servidor


class _Servidor(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        """Navegador que fecha a aba ou cancela um fetch não é erro do servidor: ignora em silêncio."""
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def servir(cenario="expediente_sma", seed=None, porta=8765, ms_por_tick=350, pasta_dados="dados/empresa",
           pasta_acesso="dados/acesso", demo=False, cognicao=None, porte=None, host="127.0.0.1",
           segmento=None) -> None:
    """`host`: 127.0.0.1 por padrão. `0.0.0.0` só DENTRO do contêiner (o Docker publica a porta só em
    127.0.0.1 do hospedeiro); a checagem de `Host`/`Origin` de loopback continua valendo, então o navegador
    entra por http://localhost e o serviço não fica aberto à rede. Exposição em rede ou nuvem está fora do
    escopo do produto (decisão do dono do produto; ver docs/dsm4/implantacao.md)."""
    from fin_mas.services.iam import SENHA_DEMO, Acesso
    acesso = criar_demo(pasta_acesso) if demo else Acesso(pasta_acesso)
    if acesso.vazio():
        raise SystemExit(f"nenhuma conta em {pasta_acesso}: crie o administrador com "
                         f"`python -m fin_mas acesso iniciar --acesso {pasta_acesso}` ou suba com --demo")
    sim = Simulacao(cenario, seed, interativo=True, ms_por_tick=ms_por_tick, pasta_dados=pasta_dados, acesso=acesso,
                    cognicao=cognicao)
    if (porte and porte != sim.porte) or segmento:  # instalação com porte e segmento escolhidos
        sim._montar(cenario, seed, True, porte=porte, segmento=segmento)
    sim.iniciar()
    servidor = criar_servidor(sim, host=host, porta=porta, acesso=acesso)
    print(f"dashboard da SMA: http://127.0.0.1:{porta}  (API em /api; Ctrl+C encerra)"
          + (f"  [escutando em {host} dentro do contêiner]" if host != "127.0.0.1" else ""), flush=True)
    if demo:
        print(f"contas de demonstração (senha {SENHA_DEMO}): avaliador (tudo menos administrar), admin, operador, "
              "auditor, controller, elisa, carla, diego, ana, bruno")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        sim.parar()
        servidor.server_close()

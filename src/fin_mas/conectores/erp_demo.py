"""ERP de demonstração: uma API HTTP em loopback que serve os dados sintéticos num formato de ERP.

    python -m fin_mas erp-demo --porta 8790 [--seed 42] [--porte media] [--plantar alcada] [--token T]

Serve a mesma empresa do ERP simulado (mesma seed e porte), mas **num formato diferente do
modelo canônico**, como um ERP de verdade faria: nomes de campos em inglês, valores em reais
com casas decimais, datas ISO (o lançamento tem `posting_date`, não competência), situação em
inglês (`posted`/`reversed`), envelopes `{"data": [...]}` e paginação. É o alvo do conector REST
genérico e do entendimento automático de fontes (ADR-011): nada aqui é específico de um
fornecedor de ERP real.

- `GET /health` e `GET /openapi.json` são públicos; o resto exige `Authorization: Bearer <token>`
  (ou `X-API-Key: <token>`); token errado ou ausente recebe 401 e nada é lido.
- `POST /api/v1/journal-entries/<id>/actions` `{"action": "reverse"|"reapprove"|"reclassify",
  "period": "AAAA-MM"}` aplica uma correção. O ERP não sabe do Approval Gate: quem garante que só
  correção aprovada chega aqui é o gateway MCP da SMA (`erp.corrigir` só com ticket aprovado).
  Cada escrita fica em `escritas` (o que o ERP recebeu), para conferência.
- Escuta só em loopback. `falhas` injeta defeitos por rota (`"500"`, `"json"`, `"lento"`) para
  demonstrar o diagnóstico do conector.
"""
import hmac
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from fin_mas import __version__
from fin_mas.conectores.base import LOOPBACK
from fin_mas.conectores.simulado import canonico_do_dataset
from fin_mas.env.dataset import Ambiente
from fin_mas.env.empresa import EMPRESA
from fin_mas.env.portes import PORTE_PADRAO

ACOES = {"reverse": "estornar", "reapprove": "reaprovar", "reclassify": "reclassificar"}
PAGINA_PADRAO = 50
PREFIXO = "/api/v1"


def _reais(centavos):
    return None if centavos is None else round(centavos / 100, 2)


def _dia(entry_id: str) -> int:
    digitos = "".join(c for c in entry_id if c.isdigit()) or "1"
    return 1 + (int(digitos) * 7) % 28


class ErpDemo:
    def __init__(self, seed: int = 42, porte: str = PORTE_PADRAO, plantar=(), agenda: dict | None = None,
                 token: str | None = None, falhas: dict | None = None, atraso_lento: float = 30.0):
        self.ambiente = Ambiente(seed, plantar=plantar, agenda=agenda, porte=porte)
        self.token = token or secrets.token_urlsafe(24)
        self.falhas = dict(falhas or {})  # rota -> "500" | "json" | "lento"
        self.atraso_lento = atraso_lento
        self.escritas: list[dict] = []
        self.leituras: list[str] = []
        self.lock = threading.RLock()
        self._servidor = None
        self._thread = None

    # ---- dados no formato do ERP ----------------------------------------------------------
    def _periodo(self, q) -> str:
        return (q.get("period") or [self.ambiente.principal])[0]

    def recurso(self, rota: str, q: dict) -> dict:
        periodo = self._periodo(q)
        with self.lock:
            ds = self.ambiente.dataset(periodo)
            c = canonico_do_dataset(ds)
        if rota == "/company":
            return {"legal_name": EMPRESA["razao_social"], "trade_code": ds.entidade, "size_class": ds.porte,
                    "fiscal_period": ds.competencia, "has_erp": bool(ds.perfil["tem_erp"])}
        if rota == "/users":
            return {"data": [{"username": p["usuario"], "full_name": p["nome"], "job_title": p["cargo"]}
                             for p in c["Pessoas"]]}
        if rota == "/products":
            return {"data": [{"sku": p["id"], "business_unit": p["un"], "units_sold": p["qtd"],
                              "unit_price": _reais(p["preco"]), "unit_variable_cost": _reais(p["custo_variavel_unit"])}
                             for p in c["Produtos"]]}
        if rota == "/cost-centers":
            return {"data": [{"cost_center": x["centro"], "monthly_amount": _reais(x["valor"])} for x in c["CustosFixos"]]}
        if rota == "/budget":
            return {"data": [{"account": o["conta"], "quarter_budget": _reais(o["orcado_trimestre"]),
                              "budget_to_date": _reais(o["orcado_acumulado"]),
                              "actual_to_date": _reais(o["realizado_acumulado"]), "notes": o["observacao"]}
                             for o in c["Orcamento"]]}
        if rota == "/actuals":
            return {"data": [{"account": r["conta"], "ledger_actual_to_date": _reais(r["realizado_acumulado"])}
                             for r in c["Realizado"]]}
        if rota == "/history":
            return {"data": [{"account": h["conta"], "period": h["competencia"], "budget": _reais(h["orcado"]),
                              "actual": _reais(h["realizado"])} for h in c["Historico"]]}
        if rota == "/journal-entries":
            linhas = [{"entry_id": x["id"], "posting_date": f"{x['competencia']}-{_dia(x['id']):02d}",
                       "account": x["conta"], "vendor": x["fornecedor"], "invoice_number": x["documento"],
                       "amount": _reais(x["valor"]), "created_by": x["criador"], "approved_by": x["aprovador"],
                       "status": "posted"} for x in c["Lancamentos"]]
            pagina = max(1, int((q.get("page") or ["1"])[0]))
            tamanho = min(500, max(1, int((q.get("page_size") or [str(PAGINA_PADRAO)])[0])))
            inicio = (pagina - 1) * tamanho
            return {"data": linhas[inicio:inicio + tamanho], "page": pagina, "page_size": tamanho,
                    "has_more": inicio + tamanho < len(linhas)}
        raise KeyError(rota)

    def acao(self, entry_id: str, corpo: dict) -> dict:
        acao = ACOES.get(corpo.get("action"))
        if acao is None:
            raise ValueError(f"action must be one of {', '.join(ACOES)}")
        with self.lock:
            ds = self.ambiente.dataset(corpo.get("period") or self.ambiente.principal)
            if not any(x["id"] == entry_id for x in ds.lancamentos):
                raise KeyError(entry_id)
            registro = ds.corrigir(entry_id, acao)
            self.escritas.append({"entry_id": entry_id, "action": corpo["action"], "period": ds.competencia,
                                  "approval": corpo.get("approval")})
        return {"entry_id": entry_id, "action": corpo["action"], "detail": registro["detalhe"]}

    # ---- HTTP -----------------------------------------------------------------------------------
    def autenticado(self, cabecalhos) -> bool:
        bearer = cabecalhos.get("Authorization", "")
        recebido = bearer[7:] if bearer.startswith("Bearer ") else cabecalhos.get("X-API-Key", "")
        return hmac.compare_digest(recebido.encode("utf-8", "surrogateescape"), self.token.encode("utf-8"))

    def iniciar(self, porta: int = 0, host: str = "127.0.0.1") -> str:
        if host not in LOOPBACK:
            raise ValueError("o ERP de demonstração só escuta em loopback")
        self._servidor = ThreadingHTTPServer((host, porta), _handler(self))
        self._servidor.daemon_threads = True
        self._thread = threading.Thread(target=self._servidor.serve_forever, name="erp-demo", daemon=True)
        self._thread.start()
        return self.url

    @property
    def url(self) -> str:
        host, porta = self._servidor.server_address[:2]
        return f"http://{host}:{porta}"

    def parar(self) -> None:
        if self._servidor is not None:
            self._servidor.shutdown()
            self._servidor.server_close()
            self._servidor = None


def _handler(erp: ErpDemo):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, status, dados):
            corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _falha(self, rota) -> bool:
            tipo = erp.falhas.get(rota)
            if tipo == "500":
                self._json(500, {"error": "internal error"})
            elif tipo == "json":
                corpo = b'{"data": [ {"sku": "P-1",'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            elif tipo == "lento":
                time.sleep(erp.atraso_lento)
                self._json(200, {"data": []})
            return tipo is not None

        def do_GET(self):
            partes = urlsplit(self.path)
            rota, q = partes.path.rstrip("/") or "/", parse_qs(partes.query)
            if rota == "/health":
                return self._json(200, {"ok": True, "service": "erp-demo", "version": __version__})
            if rota == "/openapi.json":
                return self._json(200, openapi())
            if not rota.startswith(PREFIXO):
                return self._json(404, {"error": "not found"})
            if not erp.autenticado(self.headers):
                return self._json(401, {"error": "invalid or missing token"})
            rota = rota[len(PREFIXO):]
            if self._falha(rota):
                return None
            try:
                dados = erp.recurso(rota, q)
            except KeyError:
                return self._json(404, {"error": "not found"})
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            erp.leituras.append(rota)
            return self._json(200, dados)

        def do_POST(self):
            rota = urlsplit(self.path).path.rstrip("/")
            tamanho = int(self.headers.get("Content-Length") or 0)
            bruto = self.rfile.read(min(tamanho, 64 * 1024)) if tamanho else b""
            if not erp.autenticado(self.headers):
                return self._json(401, {"error": "invalid or missing token"})
            partes = rota[len(PREFIXO):].split("/") if rota.startswith(PREFIXO) else []
            if len(partes) != 4 or partes[1] != "journal-entries" or partes[3] != "actions":
                return self._json(404, {"error": "not found"})
            try:
                corpo = json.loads(bruto or b"{}")
                return self._json(200, erp.acao(partes[2], corpo))
            except KeyError:
                return self._json(404, {"error": f"journal entry not found: {partes[2]}"})
            except ValueError as e:
                return self._json(422, {"error": str(e)})

    return Handler


# ---- contrato publicado (OpenAPI 3.0): o entendimento automático lê isto, sem LLM ----------------
def _lista(item: dict, paginada=False) -> dict:
    props = {"data": {"type": "array", "items": item}}
    if paginada:
        props.update({"page": {"type": "integer"}, "page_size": {"type": "integer"}, "has_more": {"type": "boolean"}})
    return {"type": "object", "properties": props}


def _obj(**campos) -> dict:
    return {"type": "object", "properties": campos}


DINHEIRO = {"type": "number", "format": "double", "description": "amount in BRL (reais)"}


def _din(exemplo):
    return {**DINHEIRO, "example": exemplo}


def _txt(exemplo, **extra):
    return {"type": "string", "example": exemplo, **extra}


PERIODO = {"name": "period", "in": "query", "required": False,
           "schema": {"type": "string", "pattern": r"^\d{4}-\d{2}$", "example": "2026-09"}}


def openapi() -> dict:
    def get(resumo, esquema, parametros=(PERIODO,)):
        return {"get": {"summary": resumo, "parameters": list(parametros), "security": [{"bearer": []}],
                        "responses": {"200": {"description": "OK",
                                              "content": {"application/json": {"schema": esquema}}}}}}
    return {
        "openapi": "3.0.3",
        "info": {"title": "ERP de demonstração (SMA, empresa fictícia)", "version": __version__},
        "components": {"securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}}},
        "paths": {
            f"{PREFIXO}/company": get("Company and fiscal period", _obj(
                legal_name=_txt(EMPRESA["razao_social"]), trade_code=_txt("SMA"), size_class=_txt("media"),
                fiscal_period=_txt("2026-09", pattern=r"^\d{4}-\d{2}$"), has_erp={"type": "boolean"})),
            f"{PREFIXO}/users": get("Users who create or approve journal entries", _lista(_obj(
                username=_txt("ana"), full_name=_txt("Ana Lima"), job_title=_txt("analista"))), ()),
            f"{PREFIXO}/products": get("Products and monthly sales", _lista(_obj(
                sku=_txt("P-1"), business_unit=_txt("UN-A"), units_sold={"type": "integer", "example": 240},
                unit_price=_din(149.9), unit_variable_cost=_din(71.35)))),
            f"{PREFIXO}/cost-centers": get("Fixed costs by cost center", _lista(_obj(
                cost_center=_txt("CC-ADM"), monthly_amount=_din(12500.0)))),
            f"{PREFIXO}/budget": get("Budget lines (quarter)", _lista(_obj(
                account=_txt("C-3001 Pessoal"), quarter_budget=_din(180000.0), budget_to_date=_din(180000.0),
                actual_to_date=_din(181250.4), notes={"type": "string", "nullable": True}))),
            f"{PREFIXO}/actuals": get("Ledger actuals by account", _lista(_obj(
                account=_txt("C-3001 Pessoal"), ledger_actual_to_date=_din(181250.4)))),
            f"{PREFIXO}/history": get("Monthly history before the current quarter", _lista(_obj(
                account=_txt("C-3001 Pessoal"), period=_txt("2026-03", pattern=r"^\d{4}-\d{2}$"),
                budget=_din(60000.0), actual=_din(59870.12)))),
            f"{PREFIXO}/journal-entries": get("Journal entries (paginated)", _lista(_obj(
                entry_id=_txt("L-001"), posting_date={"type": "string", "format": "date", "example": "2026-09-08"},
                account=_txt("C-3001 Pessoal"), vendor=_txt("F-23"), invoice_number=_txt("NF-1001"),
                amount=_din(4321.09), created_by=_txt("ana"), approved_by=_txt("carla"),
                status={"type": "string", "enum": ["posted", "reversed"]}), paginada=True),
                (PERIODO, {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
                 {"name": "page_size", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 500}})),
            f"{PREFIXO}/journal-entries/{{entry_id}}/actions": {"post": {
                "summary": "Correct a journal entry (reverse, reapprove, reclassify)", "security": [{"bearer": []}],
                "requestBody": {"content": {"application/json": {"schema": _obj(
                    action={"type": "string", "enum": list(ACOES)}, period=_txt("2026-09"))}}},
                "responses": {"200": {"description": "applied"}}}},
        },
    }


def servir(porta: int, seed: int = 42, porte: str = PORTE_PADRAO, plantar=(), token: str | None = None) -> None:
    erp = ErpDemo(seed, porte, plantar, token=token)
    erp.iniciar(porta)
    print(f"ERP de demonstração em {erp.url}  (contrato: {erp.url}/openapi.json; Ctrl+C encerra)")
    print(f"token de acesso (Authorization: Bearer ...): {erp.token}")
    print(f"empresa fictícia: seed {seed}, porte {porte}, competência {erp.ambiente.principal}"
          + (f", plantios {', '.join(plantar)}" if plantar else ""), flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        erp.parar()

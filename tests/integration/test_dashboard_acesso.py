"""Dashboard com controle de acesso (ADR-009): servidor HTTP real em loopback, contas reais em arquivo selado.

Cada teste sobe a simulação, o SVC-IAM numa pasta temporária e o servidor, e fala com ele por
HTTP como o navegador faria: login, cookie de sessão, token CSRF, comandos e leituras.
"""
import http.client
import json
import socket
import threading
import time

import pytest

from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor
from fin_mas.services import consulta
from fin_mas.services.iam import SENHA_DEMO, Acesso, criar_demo
from helpers import aguardando_humano

pytestmark = pytest.mark.integracao


class Navegador:
    """Cliente HTTP mínimo com cookie de sessão e token CSRF, como o dashboard."""

    def __init__(self, porta):
        self.porta, self.cookie, self.csrf, self.cabecalho = porta, None, None, "X-SMA-Token"

    def pedir(self, metodo, caminho, corpo=None, cru=False, **cabecalhos):
        con = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=10)
        h = dict(cabecalhos)
        if self.cookie and "Cookie" not in h:
            h["Cookie"] = self.cookie
        if metodo == "POST" and self.csrf and self.cabecalho not in h:
            h[self.cabecalho] = self.csrf
        dados = json.dumps(corpo).encode() if isinstance(corpo, (dict, list)) else corpo
        con.request(metodo, caminho, body=dados, headers=h)
        r = con.getresponse()
        bruto = r.read()
        con.close()
        self.ultimos_cabecalhos = {k.lower(): v for k, v in r.getheaders()}
        if cru:
            return r.status, bruto
        try:
            return r.status, json.loads(bruto or b"null")
        except ValueError:
            return r.status, bruto

    def get(self, caminho, **h):
        return self.pedir("GET", caminho, **h)

    def post(self, caminho, corpo=None, **h):
        return self.pedir("POST", caminho, corpo if corpo is not None else {}, **h)

    def login(self, usuario, senha=SENHA_DEMO):
        status, dados = self.pedir("POST", "/api/login", {"usuario": usuario, "senha": senha})
        if status == 200:
            self.cookie = self.ultimos_cabecalhos["set-cookie"].split(";")[0]
            self.csrf = dados["csrf"]
        return status, dados


@pytest.fixture
def servico(tmp_path):
    criados = []

    def criar(cenario="fechar_mes", iniciar=False, **kw):
        acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
        sim = Simulacao(cenario, interativo=True, ms_por_tick=0, pausado=not iniciar, acesso=acesso, **kw)
        if iniciar:
            sim.iniciar()
        servidor = criar_servidor(sim, porta=0, acesso=acesso)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        criados.append((sim, servidor))
        return sim, acesso, servidor.server_address[1]
    yield criar
    for sim, servidor in criados:
        servidor.shutdown()
        servidor.server_close()
        sim.parar()


def entrar(porta, usuario):
    n = Navegador(porta)
    assert n.login(usuario)[0] == 200
    return n


def _ate_humano(sim, limite=5000):
    for _ in range(limite):
        sim.processar_comandos()
        if aguardando_humano(sim.sistema.bus) or not sim.passo():
            return
    raise AssertionError("simulação não chegou à espera humana")


def _ate_esvaziar(sim, limite=5000):
    for _ in range(limite):
        if not sim.passo():
            return
    raise AssertionError("simulação não esvaziou a fila")


def test_live_server_streams_trace_over_http(servico):
    """TEST-34: fluxo de eventos e comando pelo HTTP real, agora por uma pessoa autenticada."""
    sim, _, porta = servico(iniciar=True)
    n = entrar(porta, "operador")
    assert n.post("/api/comando", {"tipo": "pausar"})[0] == 202
    con = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
    con.request("GET", "/api/eventos", headers={"Cookie": n.cookie})
    stream = con.getresponse()
    assert stream.status == 200
    primeiro = json.loads(stream.readline().decode("utf-8")[len("data: "):])
    assert primeiro["tipo"] == "reset" and primeiro["cenario"] == "fechar_mes"
    stream.readline()
    segundo = json.loads(stream.readline().decode("utf-8")[len("data: "):])
    assert segundo["tipo"] == "registro" and segundo["registro"]["kind"] == "meta"
    con.close()
    for _ in range(100):  # comandos são aplicados de forma assíncrona pela thread da simulação
        estado = n.get("/api/estado")[1]
        if estado["controle"]["pausado"]:
            break
        time.sleep(0.02)
    assert estado["controle"]["pausado"] is True and "AG-ORC" in estado["agentes"]
    operador = [r for r in sim.registros if r["kind"] == "operador"]
    assert operador and operador[0]["ator"] == "operador" and operador[0]["comando"] == "pausar"


def test_dashboard_mutations_require_session_token(servico):
    """TEST-73: POST sem sessão, sem o token CSRF da sessão, de outro site ou por outro nome é recusado."""
    sim, _, porta = servico("veto_waiver")
    decisao = {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "waiver"}
    anonimo = Navegador(porta)
    assert anonimo.post("/api/comando", decisao)[0] == 401
    assert anonimo.post("/api/comando", decisao, **{"X-SMA-Token": "chute"})[0] == 401
    assert anonimo.post("/api/dados/planilha", {})[0] == 401
    n = entrar(porta, "avaliador")
    assert n.post("/api/comando", decisao, **{"X-SMA-Token": "chute"})[0] == 403  # sessão válida, CSRF errado
    assert n.pedir("POST", "/api/comando", decisao, **{"X-SMA-Token": ""})[0] == 403
    assert n.post("/api/comando", decisao, Origin="https://evil.example")[0] == 403
    assert n.get("/api/sessao", Host="evil.example:8765")[0] == 403  # DNS rebinding
    assert n.get("/api/sessao", Origin="https://evil.example")[0] == 403
    assert sim.comandos.empty()  # nada chegou à simulação
    assert n.post("/api/comando", {"tipo": "pausar"})[0] == 202
    assert n.get("/api/sessao", Host="localhost:5173", Origin="http://localhost:5173")[0] == 200  # Vite em dev
    # o token CSRF de uma sessão não serve em outra
    outro = entrar(porta, "operador")
    assert outro.post("/api/comando", {"tipo": "pausar"}, **{"X-SMA-Token": n.csrf})[0] == 403


def test_dashboard_authenticates_before_reading_the_body(servico):
    """TEST-90: sem sessão, um corpo enorme declarado não é lido; cabeçalho não-ASCII não gera exceção."""
    sim, _, porta = servico()
    n = entrar(porta, "operador")
    casos = (("", "401"), (f"Cookie: {n.cookie}\r\nX-SMA-Token: ç\r\n", "403"))
    for cabecalho, esperado in casos:
        with socket.create_connection(("127.0.0.1", porta), timeout=3) as s:
            s.sendall(("POST /api/comando HTTP/1.1\r\nHost: 127.0.0.1\r\nContent-Length: 10000000\r\n"
                       + cabecalho + "\r\n").encode("latin-1"))
            resposta = s.recv(200).decode("latin-1")  # sem enviar o corpo: precisa responder já
        assert resposta.split()[1] == esperado, resposta
    assert sim.comandos.empty()


def test_dashboard_filters_and_auth(servico):
    """TEST-19 (REQ-O04): sem autenticação nada é servido; os filtros devolvem exatamente o recorte pedido."""
    sim, _, porta = servico("expediente_sma")
    _ate_humano(sim)
    anonimo = Navegador(porta)
    for caminho in ("/api/estado", "/api/eventos", "/api/auditoria", "/api/cenarios", "/api/llm", "/api/acesso/trilha",
                    "/api/auditoria/exportar", "/api/sessao", "/api/relatorios", "/api/aprovacoes"):
        assert anonimo.get(caminho)[0] == 401, caminho
    assert anonimo.get("/api/saude")[0] == 200  # única leitura pública
    assert anonimo.get("/api/rota-que-nao-existe")[0] == 401

    n = entrar(porta, "auditor")
    registros = list(sim.registros)

    def recorte(consulta_http, **filtros):
        status, dados = n.get("/api/auditoria?limite=5000&" + consulta_http)
        assert status == 200
        esperado = consulta.filtrar(registros, **filtros)
        assert [r["seq"] for r in dados["registros"]] == [r["seq"] for r in esperado] and dados["total"] == len(esperado)
        return esperado

    do_agente = recorte("agente=AG-CIN", agente="AG-CIN")
    assert do_agente and all("AG-CIN" in (r.get("agente"), r.get("sender"), r.get("receiver")) for r in do_agente)
    do_periodo = recorte("de_t=10&ate_t=30", de_t=10, ate_t=30)
    assert do_periodo and all(10 <= r["t"] <= 30 for r in do_periodo)
    da_tarefa = recorte("tarefa=SOL-002", tarefa="SOL-002")
    conversas = {r.get("conversation_id") for r in da_tarefa}
    assert "SOL-002" in conversas and any(c.startswith("DEL-") for c in conversas) and "SOL-001" not in conversas
    da_competencia = recorte("competencia=2026-07", competencia="2026-07")
    assert da_competencia and len(da_competencia) < len(registros)
    do_tipo = recorte("tipo=decision,belief", tipo="decision,belief")
    assert {r["kind"] for r in do_tipo} == {"decision", "belief"}
    combinado = recorte("agente=AG-ORC&tipo=belief&q=realizado", agente="AG-ORC", tipo="belief", texto="realizado")
    assert combinado and len(combinado) < len(do_tipo)
    assert recorte("custo_min=0", custo_min=0) == []  # sem LLM ligado não há custo
    assert n.get("/api/auditoria?de_t=abc")[0] == 400
    # exportação: o auditor pode, o operador não; e a exportação fica na trilha de acesso
    status, bruto = n.pedir("GET", "/api/auditoria/exportar?tipo=decision", cru=True)
    linhas = [json.loads(x) for x in bruto.decode().splitlines()]
    assert status == 200 and linhas and {r["kind"] for r in linhas} == {"decision"}
    assert n.ultimos_cabecalhos["content-disposition"].startswith("attachment")
    operador = entrar(porta, "operador")
    status, erro = operador.get("/api/auditoria/exportar")
    assert status == 403 and "PERM-AUD-EXPORTAR" in erro["erro"]
    assert operador.get("/api/auditoria?agente=AG-ORC")[0] == 200
    trilha = n.get("/api/acesso/trilha?evento=auditoria_exportada")[1]
    assert trilha["integridade"]["integra"] and trilha["registros"][-1]["ator"] == "auditor"


def test_each_role_can_only_do_what_its_permissions_allow(servico):
    sim, _, porta = servico("veto_waiver")
    _ate_humano(sim)
    pausar, pedir = {"tipo": "pausar"}, {"tipo": "solicitar", "intencao": "avaliar_orcamento"}
    decidir = {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "bloquear"}
    desligar = {"tipo": "agente", "agente": "AG-CUS", "online": False}
    modelo = {"tipo": "modelo", "agente": "AG-REL", "llm": True, "modelo": "mock-narrador"}
    esperado = {  # conta -> (pausar, pedir, decidir, desligar, modelo)
        "operador": (202, 403, 403, 202, 403), "auditor": (403, 403, 403, 403, 403),
        "bruno": (403, 202, 403, 403, 403), "carla": (403, 403, 202, 403, 202), "admin": (403, 403, 403, 403, 403),
    }
    for usuario, codigos in esperado.items():
        n = entrar(porta, usuario)
        obtido = tuple(n.post("/api/comando", cmd)[0] for cmd in (pausar, pedir, decidir, desligar, modelo))
        assert obtido == codigos, usuario
    n = entrar(porta, "admin")
    status, erro = n.post("/api/comando", decidir)
    assert status == 403 and "IAM-05" in erro["erro"] and "PERM-APR-DECIDIR" in erro["erro"]
    assert n.get("/api/estado")[0] == 200 and n.get("/api/llm")[0] == 403 and n.get("/api/acesso/trilha")[0] == 200
    assert entrar(porta, "auditor").get("/api/llm")[0] == 200
    assert n.post("/api/comando", {"tipo": "comando_inexistente"})[0] == 400


def test_decision_is_bound_to_the_logged_in_person(servico):
    """A gerente que criou e aprovou o lançamento vetado entra e tenta decidir: a política recusa a pessoa."""
    sim, acesso, porta = servico("decisao_por_pessoa")
    _ate_humano(sim)
    carla, diego = entrar(porta, "carla"), entrar(porta, "diego")
    fila = carla.get("/api/aprovacoes")[1]["aprovacoes"]
    assert fila[0]["aguardando"] and "POL-03" in fila[0]["impedimento"]
    assert diego.get("/api/aprovacoes")[1]["aprovacoes"][0]["impedimento"] is None
    decisao = {"tipo": "decidir", "solicitacao": "SOL-001", "decisao": "corrigir", "justificativa": "reaprovar com outro gerente"}
    assert carla.post("/api/comando", decisao)[0] == 202  # o comando é dela por permissão; quem recusa é a política
    sim.processar_comandos()
    assert sim.sistema.aprovador.pendentes and next(iter(sim.sistema.politica.tickets.values()))["estado"] == "pendente"
    assert any("POL-03: carla participou" in r["motivo"] for r in sim.registros if r["kind"] == "rejected")
    assert diego.post("/api/comando", decisao)[0] == 202
    _ate_esvaziar(sim)
    ticket = next(iter(sim.sistema.politica.tickets.values()))
    assert ticket["aprovado_por"]["pessoa"] == "diego" and ticket["aprovado_por"]["sessao"].startswith("S-")
    assert diego.get("/api/solicitacoes")[1]["solicitacoes"][0]["status"].startswith("publicado")
    quem = [(r["ator"], r["comando"]) for r in sim.registros if r["kind"] == "operador"]
    assert quem == [("carla", "decidir"), ("diego", "decidir")]
    decisoes = [(r["ator"], r["resultado"], r.get("regra")) for r in acesso.trilha.ler() if r["evento"] == "decisao"]
    assert decisoes == [("carla", "negado", "POL-03"), ("diego", "ok", None)]
    assert "token" not in json.dumps([r for r in sim.registros if r["kind"] == "operador"])


def test_requests_carry_the_person_and_requester_cannot_approve(servico):
    sim, _, porta = servico("fechar_mes")
    elisa = entrar(porta, "elisa")
    assert elisa.post("/api/comando", {"tipo": "solicitar", "intencao": "avaliar_orcamento"})[0] == 202
    sim.processar_comandos()
    pedido = [r for r in sim.registros if r["kind"] == "open" and r["protocol"] == "PROT-SOL"][-1]
    assert pedido["content"]["solicitado_por"] == "elisa"
    assert elisa.get("/api/solicitacoes")[1]["solicitacoes"][-1]["solicitado_por"] == "elisa"


def test_revoked_session_stops_at_once_and_closes_the_event_stream(servico, tmp_path):
    sim, _, porta = servico()
    n = entrar(porta, "operador")
    con = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
    con.request("GET", "/api/eventos", headers={"Cookie": n.cookie})
    stream = con.getresponse()
    assert stream.status == 200 and n.get("/api/estado")[0] == 200
    tui = Acesso(tmp_path / "acesso", custo_scrypt=10)  # outro processo: o console de administração
    adm, _ = tui.autenticar("admin", SENHA_DEMO, "tui")
    sid = next(s["id"] for s in tui.sessoes(adm) if s["usuario"] == "operador" and s["viva"])
    tui.revogar(adm, sid)
    assert n.get("/api/estado")[0] == 401 and n.post("/api/comando", {"tipo": "pausar"})[0] == 401
    inicio, encerrou = time.monotonic(), False
    while time.monotonic() - inicio < 8:
        linha = stream.readline().decode("utf-8")
        if not linha:
            break
        if '"sessao_encerrada"' in linha:
            encerrou = True
            break
    con.close()
    assert encerrou, "o fluxo de eventos deveria avisar e fechar quando a sessão é revogada"
    # bloquear a conta também derruba as sessões dela
    c = entrar(porta, "carla")
    tui.bloquear(adm, "carla")
    assert c.get("/api/estado")[0] == 401 and Navegador(porta).login("carla")[0] == 401


def test_login_lockout_and_generic_errors(servico):
    _, acesso, porta = servico()
    n = Navegador(porta)
    inexistente = n.login("ninguem", "qualquer-senha-12345")
    errada = n.login("bruno", "senha-errada-12345")
    assert inexistente[0] == errada[0] == 401 and inexistente[1] == errada[1] == {"erro": "usuário ou senha inválidos"}
    for _ in range(4):
        n.login("bruno", "senha-errada-12345")
    status, dados = n.login("bruno")  # senha certa, conta bloqueada por tentativas
    assert status == 401 and "bloqueada" in dados["erro"]
    negadas = [r for r in acesso.trilha.ler() if r["evento"] == "entrada" and r["resultado"] == "negado"]
    assert len(negadas) == 7 and "senha-errada" not in json.dumps(acesso.trilha.ler())
    assert n.pedir("POST", "/api/login", b"{nao e json")[0] == 400
    assert n.pedir("POST", "/api/login", b"x" * 10000)[0] == 413


def test_temporary_password_must_be_changed_first(servico, tmp_path):
    _, _, porta = servico()
    tui = Acesso(tmp_path / "acesso", custo_scrypt=10)
    adm, _ = tui.autenticar("admin", SENHA_DEMO, "tui")
    tui.redefinir_senha(adm, "ana", "Temporaria-2026-xyz")
    n = Navegador(porta)
    assert n.login("ana")[0] == 401  # a senha antiga deixou de valer
    status, dados = n.login("ana", "Temporaria-2026-xyz")
    assert status == 200 and dados["sessao"]["trocar_senha"] is True
    status, erro = n.get("/api/estado")
    assert status == 403 and "IAM-02" in erro["erro"]
    assert n.post("/api/senha", {"atual": "Temporaria-2026-xyz", "nova": "curta"})[0] == 400
    assert n.post("/api/senha", {"atual": "Temporaria-2026-xyz", "nova": "Definitiva-2026-abc"})[0] == 200
    assert n.get("/api/estado")[0] == 200 and n.get("/api/sessao")[1]["sessao"]["trocar_senha"] is False


def test_work_area_routes_reports_approvals_explanations_and_sequence(servico, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-" + "a1b2c3d4e5f6" * 2)
    sim, _, porta = servico("orc_hipotese_local")
    _ate_esvaziar(sim)
    n = entrar(porta, "avaliador")
    solicitacoes = n.get("/api/solicitacoes")[1]["solicitacoes"]
    assert solicitacoes[0]["id"] == "SOL-001" and solicitacoes[0]["status"] == "publicado_com_ressalva"
    relatorio = n.get("/api/relatorios/SOL-001")[1]
    assert "Insight: C-3002 Marketing" in relatorio["relatorio"] and relatorio["hipoteses"][0]["estado"] == "confirmada"
    status, txt = n.pedir("GET", "/api/relatorios/SOL-001?formato=txt", cru=True)
    assert status == 200 and "Relatório orçamentário" in txt.decode() and "attachment" in n.ultimos_cabecalhos["content-disposition"]
    status, pagina = n.pedir("GET", "/api/relatorios/SOL-001?formato=html", cru=True)
    assert status == 200 and b"<svg" in pagina and "Relatório orçamentário".encode() in pagina
    assert n.get("/api/relatorios/SOL-999")[0] == 404
    confirmada = next(r for r in sim.registros if r["kind"] == "hipotese" and r["evento"] == "confirmada")
    explicacao = n.get(f"/api/explicar?seq={confirmada['seq']}")[1]
    papeis = [item["papel"] for item in explicacao["cadeia"]]
    assert explicacao["agente"] == "AG-ORC" and explicacao["tarefa"] == "SOL-001"
    for papel in ("percepção (tool)", "crença", "hipótese", "desejo", "deliberação", "intenção"):
        assert papel in papeis, papel
    seq = n.get("/api/sequencia?conversa=SOL-001")[1]["mermaid"]
    assert seq.startswith("sequenceDiagram") and "AG_ORC->>AG_CIN: query-ref [QRY-002]" in seq and "perdida [QRY-001]" in seq
    assert n.get("/api/sequencia?conversa=NAO-EXISTE")[0] == 404
    llm = n.get("/api/llm")
    assert llm[0] == 200 and set(llm[1]["agentes"]) == {"AG-ORC", "AG-REL", "AG-RES"}
    assert "sk-teste" not in json.dumps(llm[1]) and llm[1]["nao_permitidos"] == ["AG-ORQ", "AG-CUS", "AG-CIN"]
    assert next(p for p in llm[1]["provedores"] if p["id"] == "openai")["tem_chave"] is True
    portes = n.get("/api/portes")[1]
    assert portes["atual"] == "media" and set(portes["portes"]) >= {"micro", "pequena", "media", "grande"}
    cenarios = n.get("/api/cenarios")[1]["cenarios"]
    assert next(c for c in cenarios if c["nome"] == "orc_hipotese_local")["cognicao"] == "local"


def test_llm_configuration_needs_permission_is_validated_and_survives_restart(servico):
    sim, _, porta = servico("orc_hipotese_llm", cognicao="llm")
    carla, operador = entrar(porta, "carla"), entrar(porta, "operador")
    cfg = {"tipo": "modelo", "agente": "AG-ORC", "llm": True, "provedor": "mock", "modelo": "mock-analista",
           "usos": ["hipoteses"]}
    assert operador.post("/api/comando", cfg)[0] == 403
    assert carla.post("/api/comando", cfg)[0] == 202
    assert carla.post("/api/comando", {**cfg, "agente": "AG-CIN"})[0] == 202  # aceito na fila, recusado pela NORM-07
    erros = []
    sim.ouvintes.append(lambda ev: erros.append(ev.get("erro")) if ev.get("erro") else None)
    sim.processar_comandos()
    assert any("NORM-07" in e for e in erros)
    assert carla.get("/api/llm")[1]["agentes"]["AG-ORC"]["modelo"] == "mock-analista"
    assert carla.post("/api/comando", {**cfg, "usos": "hipoteses"})[0] == 400  # tipo de campo errado
    assert operador.post("/api/comando", {"tipo": "reiniciar", "cenario": "orc_hipotese_llm", "cognicao": "llm"})[0] == 202
    sim.processar_comandos()
    _ate_esvaziar(sim)
    assert carla.get("/api/llm")[1]["agentes"]["AG-ORC"]["llm"] is True  # a configuração sobrevive ao reinício
    origem = next(r["origem"] for r in sim.registros if r["kind"] == "hipotese" and r["evento"] == "aceita")
    assert origem.startswith("llm:mock/mock-analista")
    assert [r["ator"] for r in sim.registros if r["kind"] == "operador"] == ["operador"]  # o reinício fica registrado


def test_security_headers_and_cookie_flags(servico):
    _, _, porta = servico()
    n = Navegador(porta)
    n.login("operador")
    cookie = n.ultimos_cabecalhos["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Path=/" in cookie
    for caminho in ("/api/saude", "/api/estado", "/", "/api/sessao"):
        n.pedir("GET", caminho, cru=True)
        h = n.ultimos_cabecalhos
        assert "frame-ancestors 'none'" in h["content-security-policy"] and h["x-content-type-options"] == "nosniff"
        assert h["x-frame-options"] == "DENY" and h["referrer-policy"] == "no-referrer" and h["cache-control"] == "no-store"
    assert n.post("/api/logout")[0] == 200 and "Max-Age=0" in n.ultimos_cabecalhos["set-cookie"]
    assert n.get("/api/estado")[0] == 401


def test_tampered_account_store_locks_everyone_out(servico, tmp_path):
    """IAM-07: cadastro alterado fora do sistema (alguém se dá o papel de administrador) não deixa ninguém entrar."""
    _, _, porta = servico()
    n = entrar(porta, "operador")
    arquivo = tmp_path / "acesso" / "contas.json"
    bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    bruto["dados"]["contas"]["operador"]["papeis"] = ["ROLE-ADM", "ROLE-APR"]
    arquivo.write_text(json.dumps(bruto), encoding="utf-8")
    assert n.get("/api/estado")[0] == 401
    assert Navegador(porta).login("admin")[0] == 401
    assert Navegador(porta).get("/api/saude")[1]["acesso"]["integro"] is False


def test_malformed_bodies_get_a_400_instead_of_a_dropped_connection(servico):
    """Correção simulada da v0.5.0 (M4): corpo que não é objeto, ou campo de tipo errado, derrubava a conexão
    sem resposta (exceção no handler), inclusive em rotas sem autenticação."""
    _, _, porta = servico()
    anonimo = Navegador(porta)
    for corpo in (b"[]", b"null", b"123", b'"texto"'):
        assert anonimo.pedir("POST", "/api/login", corpo)[0] == 400
    assert anonimo.pedir("POST", "/api/login", {"usuario": ["a"], "senha": {"b": 1}})[0] == 401
    operador = entrar(porta, "operador")
    for rota, corpo in (("/api/comando", {"tipo": []}), ("/api/comando", {"tipo": {}}), ("/api/comando", b"[]"),
                        ("/api/senha", b"[]"), ("/api/senha", {"atual": 1, "nova": []}),
                        ("/api/dados/planilha", b"[]"), ("/api/dados/planilha", {"conteudo_base64": 123})):
        status, dados = operador.pedir("POST", rota, corpo)
        assert status in (400, 403), (rota, corpo, status, dados)
    assert operador.get("/api/sessao")[0] == 200  # o servidor segue respondendo


def test_wrong_passwords_by_a_stranger_do_not_drop_the_live_session_of_the_account(servico):
    """Correção simulada da v0.5.0 (M5): cinco senhas erradas bloqueiam novas entradas por um tempo, mas a
    sessão já aberta da pessoa continua valendo."""
    _, acesso, porta = servico()
    controller = entrar(porta, "controller")
    estranho = Navegador(porta)
    for _ in range(5):
        assert estranho.login("controller", "senha-errada-12345")[0] == 401
    assert controller.get("/api/sessao")[0] == 200  # a sessão viva não caiu
    status, dados = estranho.login("controller")  # novas entradas ficam bloqueadas, mesmo com a senha certa
    assert status == 401 and "bloqueada" in dados["erro"]
    assert controller.get("/api/auditoria")[0] == 200


def test_changing_the_cognition_level_on_restart_needs_the_model_permission(servico):
    """Correção simulada da v0.5.0 (m1): o operador (sem PERM-MOD-CONFIG) reiniciava com `cognicao: llm`."""
    sim, _, porta = servico()
    operador = entrar(porta, "operador")
    assert operador.post("/api/comando", {"tipo": "reiniciar", "cognicao": "llm"})[0] == 403
    assert operador.post("/api/comando", {"tipo": "reiniciar", "cognicao": sim.cognicao or sim.cenario.cognicao})[0] == 202
    assert operador.post("/api/comando", {"tipo": "agente", "agente": "AG-XYZ", "online": False})[0] == 400

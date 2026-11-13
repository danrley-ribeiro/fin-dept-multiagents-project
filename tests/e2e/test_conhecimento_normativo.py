"""Conhecimento normativo com proveniência (CP8, DSM4): busca pela tool MCP e uso pelo AG-CIN.

A busca é exercida como os agentes a usam: pela tool `normas.buscar` do gateway, com identidade e
allowlist. Dois comportamentos importam: o trecho esperado vem primeiro, com documento, trecho e
versão; e, quando o corpus não trata do assunto, a resposta é vazia e o agente declara "sem evidência".
"""
import pytest

from fin_mas.agents.cin import CONSULTA_POR_REGRA
from fin_mas.env.scenarios import build_system, run_scenario
from fin_mas.mcp.gateway import ToolDenied

pytestmark = pytest.mark.e2e
ESPERADO = {  # consulta em linguagem do problema -> trecho que deve vir em primeiro
    CONSULTA_POR_REGRA["alcada"]: "COSO-ALCADA",
    CONSULTA_POR_REGRA["sod"]: "COSO-SEGREGACAO",
    CONSULTA_POR_REGRA["competencia"]: "LEI-6404-ART177",
    "limite de receita bruta anual da microempresa e da empresa de pequeno porte": "LC-123-ART3",
    "sociedade de grande porte com auditoria independente obrigatória": "LEI-11638-ART3",
    "materialidade proporcional ao porte da entidade": "NBC-TA-320-MATERIALIDADE",
    "não conformidade crítica veta a publicação até correção ou waiver humano": "NORM-04",
    "limite de receita para optar pelo lucro presumido": "LEI-9718-PRESUMIDO",
}
SEM_EVIDENCIA = (CONSULTA_POR_REGRA["duplicidade"], "depreciação acelerada de veículos", "provisão para devedores duvidosos",
                 "aprovação de crédito a clientes inadimplentes", "")


def reg(e, kind, agente=None):
    return [r for r in e.audit.records if r["kind"] == kind and (agente is None or r.get("agente") == agente)]


def buscar(sistema, consulta, k=3, agente="AG-CIN"):
    return sistema.agentes[agente].ferramenta("normas.buscar", "TESTE", consulta=consulta, k=k)


def test_search_returns_the_expected_passage_first_with_provenance():
    s = build_system(cognicao="local")
    for consulta, trecho in ESPERADO.items():
        r = buscar(s, consulta)
        topo = r["dados"]["trechos"][0]
        assert topo["trecho"] == trecho, consulta
        assert topo["documento"] and topo["referencia"] and topo["texto"] and topo["versao"].startswith("corpus-v1")
        assert topo["cobertura"] >= 0.5 and topo["pontuacao"] > 0
        assert r["dados"]["versao"] == "corpus-v1" and r["proveniencia"]["fonte"] == "mcp://normas/buscar"
        pontos = [t["pontuacao"] for t in r["dados"]["trechos"]]
        assert pontos == sorted(pontos, reverse=True) and len(pontos) <= 3
    # top-k: a pergunta sobre porte traz as três classificações, a da microempresa primeiro; k limita
    porte = buscar(s, "limite de receita bruta anual da microempresa")["dados"]["trechos"]
    assert [t["trecho"] for t in porte] == ["LC-123-ART3", "BNDES-MEDIA-GRANDE", "LEI-9718-PRESUMIDO"]
    assert [t["trecho"] for t in buscar(s, "limite de receita bruta anual da microempresa", k=1)["dados"]["trechos"]] == ["LC-123-ART3"]
    # determinística: a mesma consulta devolve o mesmo resultado, e toda chamada fica no trace com a consulta
    assert buscar(s, CONSULTA_POR_REGRA["sod"]) == buscar(s, CONSULTA_POR_REGRA["sod"])
    chamada = [r for r in s.bus.audit.records if r["kind"] == "mcp_call" and r["tool"] == "normas.buscar"][-1]
    assert chamada["consulta"]["consulta"] == CONSULTA_POR_REGRA["sod"] and chamada["consulta"]["k"] == 3


def test_search_without_evidence_returns_nothing():
    s = build_system(cognicao="local")
    for consulta in SEM_EVIDENCIA:
        r = buscar(s, consulta)
        assert r["dados"]["trechos"] == [] and r["dados"]["versao"] == "corpus-v1", consulta
    # a tool é só de quem a tem na allowlist (NORM-02): AG-CIN e AG-REL
    assert buscar(s, CONSULTA_POR_REGRA["sod"], agente="AG-REL")["dados"]["trechos"]
    for agente in ("AG-ORC", "AG-RES", "AG-CUS"):
        with pytest.raises(ToolDenied):
            buscar(s, CONSULTA_POR_REGRA["sod"], agente=agente)


def test_finding_cites_the_passage_that_grounds_it():
    e = run_scenario("normas_fundamentam_achado")
    veto = next(r["content"] for r in e.audit.records if r["kind"] == "send" and r.get("performative") == "veto")
    (achado,) = [a for a in veto["achados"] if a["regra"] == "sod" and a["severidade"] == "critica"][:1]
    assert achado["fundamento"] == {"situacao": "fundamentado", "documento": "COSO-2013", "trecho": "COSO-SEGREGACAO",
                                    "versao": "corpus-v1; paráfrase"}
    assert achado["evidencia"].endswith("fundamento: COSO-2013, trecho COSO-SEGREGACAO (corpus-v1; paráfrase)")
    (f,) = [x for x in veto["fundamentos"] if x["regra"] == "sod"]
    assert "quem registra uma transação não deve ser quem a aprova" in f["texto"]
    crenca = next(r for r in reg(e, "belief", "AG-CIN") if r["chave"] == "fundamento[sod]")
    assert crenca["fonte"] == "mcp://normas/buscar" and crenca["depois"]["trecho"] == "COSO-SEGREGACAO"
    busca = next(r for r in e.audit.records if r["kind"] == "mcp_call" and r["tool"] == "normas.buscar" and r["agente"] == "AG-CIN")
    assert busca["consulta"]["consulta"] == CONSULTA_POR_REGRA["sod"]
    # o veto e a liberação não mudam por causa da citação; o relatório de exceção cita a mesma base
    r = e.resposta.content
    assert r["status"] == "publicado_com_ressalva" and any(x.startswith("waiver de sod") for x in r["ressalvas"])
    assert "Base normativa (segregação de funções): COSO — Controle Interno, Estrutura Integrada (2013), trecho COSO-SEGREGACAO" in r["relatorio"]
    # nível básico: mesmos achados, mesma decisão, sem busca nem campo de fundamento
    basico = run_scenario("normas_fundamentam_achado", cognicao="basico")
    veto_basico = next(x["content"] for x in basico.audit.records if x["kind"] == "send" and x.get("performative") == "veto")
    assert [(a["regra"], a["lancamento"], a["severidade"]) for a in veto_basico["achados"]] == [
        (a["regra"], a["lancamento"], a["severidade"]) for a in veto["achados"]]
    assert "fundamentos" not in veto_basico and not any("fundamento" in a for a in veto_basico["achados"])
    assert not [x for x in basico.audit.records if x["kind"] == "mcp_call" and x["tool"] == "normas.buscar"]
    assert basico.resposta.content["ressalvas"] == r["ressalvas"]


def test_no_evidence_is_declared_and_never_filled():
    e = run_scenario("normas_sem_evidencia")
    veto = next(r["content"] for r in e.audit.records if r["kind"] == "send" and r.get("performative") == "veto")
    duplicidade = [a for a in veto["achados"] if a["regra"] == "duplicidade"]
    assert duplicidade and all(a["fundamento"] == {"situacao": "sem evidência", "corpus": "corpus-v1",
                                                   "consulta": CONSULTA_POR_REGRA["duplicidade"]} for a in duplicidade)
    assert all("sem evidência na base normativa (corpus-v1)" in a["evidencia"] for a in duplicidade)
    (f,) = [x for x in veto["fundamentos"] if x["regra"] == "duplicidade"]
    assert f["situacao"] == "sem evidência" and "documento" not in f and "trecho" not in f and "texto" not in f
    crenca = next(r for r in reg(e, "belief", "AG-CIN") if r["chave"] == "fundamento[duplicidade]")
    assert crenca["depois"]["situacao"] == "sem evidência" and crenca["fonte"] == "mcp://normas/buscar"
    # sem evidência textual o achado continua crítico pela regra interna do porte: veto, estorno aprovado, publicação
    assert all(a["severidade"] == "critica" for a in duplicidade)
    assert [c["acao"] for c in e.system.dataset.correcoes] == ["estornar"]
    assert e.resposta.performative == "inform"
    assert "Base normativa (lançamento em duplicidade): sem evidência na base normativa (corpus-v1)" in e.resposta.content["relatorio"]
    assert "COSO" not in e.resposta.content["relatorio"]  # nada "aproximado" entra no lugar
    # nível básico: mesma correção e mesmo resultado, sem declarar nada sobre a base
    basico = run_scenario("normas_sem_evidencia", cognicao="basico")
    assert basico.resposta.content["resultado"] == e.resposta.content["resultado"]
    assert "Base normativa" not in basico.resposta.content["relatorio"]

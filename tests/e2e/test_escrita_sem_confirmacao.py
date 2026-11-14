"""Correção aprovada escrita no ERP e releitura que falha (correção simulada da DSM4, verificação do t04_escrita).

ERP de demonstração em loopback, conector REST genérico e o cenário `conector_rest_demo` inteiro. O ERP aceita a
escrita e, depois dela, passa a responder lixo nos lançamentos. Antes, o efeito ocorrido ia para o trace como
`mcp_denied` ("fonte indisponível") e a correção como "não executada", embora o ERP já a tivesse aplicado. Agora o
efeito fica registrado como "aplicado, confirmação inválida" (trace, ticket e resposta da tool), não é repetido, e a
reavaliação mantém o veto (nada é publicado sobre a fonte que não se confirmou).
"""
import copy

from fin_mas.conectores import descoberta
from fin_mas.conectores.base import APLICADO_SEM_CONFIRMACAO, AmbienteConector
from fin_mas.conectores.cenarios import _rest, confirmar
from fin_mas.conectores.erp_demo import ErpDemo
from fin_mas.env.portes import PORTE_PADRAO
from fin_mas.env.scenarios import run_scenario


def test_write_accepted_by_the_erp_with_an_invalid_reread_is_recorded_as_applied_and_never_repeated():
    erp = ErpDemo(42, PORTE_PADRAO, ("alcada",))
    original = erp.recurso

    def recurso(rota, q):  # depois da primeira escrita, os lançamentos voltam com o valor ilegível
        dados = original(rota, q)
        if rota == "/journal-entries" and erp.escritas:
            dados = copy.deepcopy(dados)
            for x in dados["data"]:
                x["amount"] = "não é número"
        return dados
    erp.recurso = recurso
    url = erp.iniciar()
    try:
        conector = _rest(url, erp.token, PORTE_PADRAO)
        competencia = erp.ambiente.principal
        conector.mapeamento = confirmar(descoberta.estrutura_rest(conector, competencia), competencia)
        e = run_scenario("conector_rest_demo", ambiente=AmbienteConector(conector, competencia=competencia,
                                                                          porte=PORTE_PADRAO))
    finally:
        erp.parar()
    assert len(erp.escritas) == 1, "a correção foi aplicada uma vez e não pode ser repetida"
    chamadas = [r for r in e.audit.records if r["kind"] == "mcp_call" and r["tool"] == "erp.corrigir"]
    assert len(chamadas) == 1 and chamadas[0]["situacao"] == APLICADO_SEM_CONFIRMACAO and chamadas[0]["motivo"]
    assert not [r for r in e.audit.records if r["kind"] == "mcp_denied" and r["tool"] == "erp.corrigir"]
    executado = [r for r in e.audit.records if r["kind"] == "politica" and r.get("evento") == "efeito_executado"]
    assert executado and executado[0]["registro"]["situacao"] == APLICADO_SEM_CONFIRMACAO
    reavaliar = [r for r in e.audit.records if r["kind"] == "decision" and r.get("resultado") == "REAVALIAR"]
    assert reavaliar and APLICADO_SEM_CONFIRMACAO in str(reavaliar[0])
    assert not [r for r in e.audit.records if r["kind"] == "decision" and r.get("resultado") == "NAO_EXECUTADA"]
    assert e.resposta.performative == "failure"  # sobre a fonte que não se confirmou, nada é publicado

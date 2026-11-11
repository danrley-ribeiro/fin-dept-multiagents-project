"""DSM3 — memória persistente (SVC-MEM), redaction fail-closed e trace à prova de adulteração."""
import json
import pathlib

import pytest

from fin_mas.env.scenarios import Scenario, run_scenario
from fin_mas.services.audit import AuditLog, TraceAdulterado
from fin_mas.services.memoria import Memoria, MemoriaRecusada, pseudonimo
from fin_mas.services.redacao import FalhaRedacao, redigir


class PoliticaFalsa:
    def __init__(self, **tickets):
        self.tickets = tickets


def ticket(estado="aprovado", decisao="waiver", competencia="2026-08", lancamentos=("L-001",)):
    return {"estado": estado, "solicitacao": "SOL-001", "cmp": "CMP-001", "decisao": decisao,
            "competencia": competencia, "achados": [{"lancamento": x} for x in lancamentos], "executadas": [],
            "aprovado_por": {"pessoa": "controller"}}


VALOR = {"regra": "alcada", "lancamento": "L-001"}


def test_memory_only_approved_with_provenance(tmp_path):
    """TEST-11: sem decisão humana registrada nada é gravado; o que é gravado volta com a fonte."""
    audit = AuditLog()
    mem = Memoria(audit, lambda: 0, PoliticaFalsa(**{"APR-001": ticket(), "APR-002": ticket("pendente")}))
    cin, rel = mem.visao("AG-CIN"), mem.visao("AG-REL")
    with pytest.raises(MemoriaRecusada, match="NORM-08"):
        cin.gravar("waiver", "alcada|x", VALOR, competencia="2026-08", aprovacao=None, fonte="-")
    with pytest.raises(MemoriaRecusada, match="NORM-08"):
        cin.gravar("waiver", "alcada|x", VALOR, competencia="2026-08", aprovacao="APR-002", fonte="-")
    with pytest.raises(MemoriaRecusada, match="não grava"):
        rel.gravar("waiver", "alcada|x", VALOR, competencia="2026-08", aprovacao="APR-001", fonte="-")
    e = cin.gravar("waiver", "alcada|x", VALOR, competencia="2026-08", aprovacao="APR-001", fonte="PROT-APR APR-001")
    assert e["id"] == "MEM-0001" and e["proveniencia"]["aprovacao"] == "APR-001"
    assert e["proveniencia"]["decidido_por"] == pseudonimo("controller")
    assert cin.consultar("waiver", "alcada|x", competencia_atual="2026-08") == []  # só meses anteriores
    assert cin.consultar("waiver", "alcada|x", competencia_atual="2026-09")[0]["id"] == "MEM-0001"
    assert rel.consultar("waiver", competencia_atual="2026-09") == []  # leitor sem acesso
    eventos = [r["evento"] for r in audit.records if r["kind"] == "memoria"]
    assert eventos.count("recusada") == 3 and "gravada" in eventos and "negada" in eventos


def test_memory_rejects_forged_identity_and_mismatched_ticket():
    """Revisão da DSM3 (M1): identidade declarada, ticket rejeitado, outra competência ou lançamento são recusados."""
    tickets = {"APR-001": ticket(), "APR-009": ticket("rejeitado", decisao="bloquear")}
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**tickets))
    cin = mem.visao("AG-CIN")
    with pytest.raises(MemoriaRecusada, match="não autenticada"):  # chamada direta declarando o nome
        mem.gravar("AG-CIN", "waiver", "k", VALOR, competencia="2026-08", aprovacao="APR-001", fonte="-")
    with pytest.raises(MemoriaRecusada, match="não autenticada"):
        mem.gravar("AG-CIN", "waiver", "k", VALOR, competencia="2026-08", aprovacao="APR-001", fonte="-", token="x")
    with pytest.raises(MemoriaRecusada, match="já emitida"):  # ninguém obtém uma segunda visão do AG-CIN
        mem.visao("AG-CIN")
    with pytest.raises(MemoriaRecusada, match="decisão humana de waiver"):  # ticket rejeitado não vira waiver
        cin.gravar("waiver", "k", VALOR, competencia="2026-08", aprovacao="APR-009", fonte="-")
    with pytest.raises(MemoriaRecusada, match="competência"):
        cin.gravar("waiver", "k", VALOR, competencia="2020-01", aprovacao="APR-001", fonte="-")
    with pytest.raises(MemoriaRecusada, match="não pertence"):
        cin.gravar("waiver", "k", {"regra": "alcada", "lancamento": "L-999"}, competencia="2026-08",
                   aprovacao="APR-001", fonte="-")
    assert mem.consultar("AG-CIN", "waiver", competencia_atual="2026-09") == []  # consulta sem token: nada
    assert mem.entradas == []


def test_tampered_memory_file_is_discarded_on_load(tmp_path):
    """Revisão da DSM3 (M1): entrada inventada ou malformada no arquivo é descartada, não derruba o AG-CIN."""
    arquivo = tmp_path / "memoria.json"
    run_scenario("veto_waiver", memoria=arquivo)
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    legitima = dados["entradas"][0]
    falsa = {**legitima, "id": "MEM-FAKE", "competencia": "2026-08",
             "proveniencia": {**legitima["proveniencia"], "aprovacao": "APR-999-INEXISTENTE"}}
    quebrada = {"id": "MEM-X", "tipo": "waiver"}  # sem competência
    dados["entradas"] = [legitima, falsa, quebrada]
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    audit = AuditLog()
    mem = Memoria(audit, lambda: 0, caminho=arquivo)
    assert [e["id"] for e in mem.entradas] == [legitima["id"]]
    motivos = [r["motivo"] for r in audit.records if r["kind"] == "memoria" and r["evento"] == "descartada"]
    assert len(motivos) == 2 and any("assinatura" in m for m in motivos)
    e = run_scenario("fechar_mes", memoria=arquivo)  # o AG-CIN segue funcionando sobre o arquivo adulterado
    assert e.resposta.content["status"] == "publicado"
    assert not [r for r in e.audit.records if r["kind"] == "erro_agente"]


def test_memory_retention_expires_old_entries():
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**{"APR-001": ticket(competencia="2026-01")}), retencao=2)
    cin = mem.visao("AG-CIN")
    cin.gravar("waiver", "k", VALOR, competencia="2026-01", aprovacao="APR-001", fonte="-")
    assert cin.consultar("waiver", "k", competencia_atual="2026-03")
    assert cin.consultar("waiver", "k", competencia_atual="2026-04") == []
    assert mem.entradas == []


def test_memory_persists_across_runs_and_flags_recidivism(tmp_path):
    """A memória gravada numa execução é lida na seguinte: a reincidência aparece em outro processo."""
    arquivo = tmp_path / "memoria.json"
    agosto = Scenario("agosto", "waiver em agosto", "fechar_mes", decisao_aprovador="waiver",
                      agenda=(("2026-08", ("alcada",)),), pedidos=(("fechar_mes", "2026-08", 1),))
    setembro = Scenario("setembro", "mesma alçada em setembro", "fechar_mes", decisao_aprovador="waiver",
                        agenda=(("2026-09", ("alcada",)),), pedidos=(("fechar_mes", "2026-09", 1),))
    e1 = run_scenario(agosto, memoria=arquivo)
    assert e1.resposta.content["status"] == "publicado_com_ressalva" and arquivo.exists()
    salvo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert [x["tipo"] for x in salvo["entradas"]] == ["waiver"]
    e2 = run_scenario(setembro, memoria=arquivo)  # sistema novo, mesmo arquivo
    assert any(r["kind"] == "memoria" and r["evento"] == "carregada" for r in e2.audit.records)
    t = e2.system.politica.tickets["APR-001"]
    assert "waiver" not in t["opcoes"] and t["negadas"][0]["regra"] == "POL-06"
    assert e2.resposta.performative == "failure"  # o humano insistiu no waiver: a política não deixou
    sem_memoria = run_scenario(setembro)  # mesma execução sem a memória: waiver aceito
    assert sem_memoria.resposta.content["status"] == "publicado_com_ressalva"


def test_memory_file_has_no_personal_names(tmp_path):
    arquivo = tmp_path / "m.json"
    run_scenario("reincidencia_waiver", memoria=arquivo)
    texto = arquivo.read_text(encoding="utf-8")
    assert "pessoa#" in texto
    for nome in ("ana", "carla", "diego", "elisa", "bruno", "controller"):
        assert nome not in texto


def test_redaction_fail_closed():
    """TEST-23: segredo e CPF sintético sanitizados; o que não dá para sanitizar é recusado."""
    limpo = redigir({"api_key": "sk-ABCDEFGHIJKLMNOP1234", "obs": "CPF 123.456.789-09 e contato ana@sma.com",
                     "tokens_entrada": 120, "texto": "Bearer abcdefghijklmnop1234"})
    assert limpo["api_key"] == "[SEGREDO REDIGIDO]" and limpo["tokens_entrada"] == 120
    assert "123.456.789-09" not in limpo["obs"] and "ana@sma.com" not in limpo["obs"]
    assert "abcdefghijklmnop1234" not in limpo["texto"]
    with pytest.raises(FalhaRedacao):
        redigir({"x": object()})
    audit = AuditLog()
    audit.record(1, "teste", conversation_id="X-1", content={"senha": "segredo123", "doc": "CPF 98765432100"})
    audit.record(2, "teste", conversation_id="X-2", content={"objeto": object()})
    assert audit.records[0]["content"] == {"senha": "[SEGREDO REDIGIDO]", "doc": "[CPF REDIGIDO]"}
    assert audit.records[1]["redacao"] == "recusada" and "content" not in audit.records[1]
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**{"APR-001": ticket()}))
    with pytest.raises(MemoriaRecusada, match="NORM-06"):
        mem.visao("AG-CIN").gravar("waiver", "k", {**VALOR, "x": object()}, competencia="2026-08",
                                   aprovacao="APR-001", fonte="-")


def test_trace_tampering_is_detected(tmp_path):
    e = run_scenario("veto_waiver")
    arquivo = tmp_path / "trace.jsonl"
    e.audit.write_jsonl(arquivo)
    assert AuditLog.read_jsonl(arquivo).records == e.audit.records
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    alterada = json.loads(linhas[20])
    alterada["t"] += 1
    adulterado = tmp_path / "adulterado.jsonl"
    adulterado.write_text("\n".join(linhas[:20] + [json.dumps(alterada, ensure_ascii=False)] + linhas[21:]),
                          encoding="utf-8")
    with pytest.raises(TraceAdulterado, match="linha 21"):
        AuditLog.read_jsonl(adulterado)
    removida = tmp_path / "removida.jsonl"
    removida.write_text("\n".join(linhas[:5] + linhas[6:]), encoding="utf-8")
    with pytest.raises(TraceAdulterado):
        AuditLog.read_jsonl(removida)


def test_credentials_never_appear_in_the_trace(tmp_path):
    e = run_scenario("ataque_decisao_forjada")
    arquivo = tmp_path / "trace.jsonl"
    e.audit.write_jsonl(arquivo)
    texto = arquivo.read_text(encoding="utf-8")
    credenciais = [a._Agent__credencial for a in e.system.bus.agents.values()]
    assert len(credenciais) == 8
    for credencial in credenciais + list(e.system.bus._credenciais.values()):
        assert credencial not in texto


def test_trace_truncation_and_recomputed_chain_are_detected(tmp_path, capsys):
    """Revisão da DSM3 (M2): corte do fim, cadeia recalculada sem a chave e trace sem hashes não passam."""
    import hashlib

    from fin_mas.cli import main
    from fin_mas.services.audit import GENESIS

    e = run_scenario("ataque_decisao_forjada")
    arquivo = tmp_path / "t.jsonl"
    e.audit.write_jsonl(arquivo)
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    assert main(["verificar", str(arquivo)]) == 0

    cortado = tmp_path / "cortado.jsonl"  # remove as 5 últimas linhas (inclui o selo)
    cortado.write_text("\n".join(linhas[:-5]) + "\n", encoding="utf-8")
    assert main(["verificar", str(cortado)]) == 3

    registros = [json.loads(x) for x in linhas[:-1]]  # recalcula a cadeia inteira com os ataques "aceitos"
    anterior, refeitas = GENESIS, []
    for r in registros:
        r.pop("_hash")
        if r["kind"] == "ataques":
            r["resultados"] = [{**x, "aceito": True} for x in r["resultados"]]
        anterior = hashlib.sha256((anterior + json.dumps(r, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()
        refeitas.append(json.dumps({**r, "_hash": anterior}, sort_keys=True, ensure_ascii=False))
    selo = json.loads(linhas[-1])["_selo"]
    refeitas.append(json.dumps({"_selo": {**selo, "hash_final": anterior}}))
    forjado = tmp_path / "forjado.jsonl"
    forjado.write_text("\n".join(refeitas) + "\n", encoding="utf-8")
    assert main(["verificar", str(forjado)]) == 3
    assert "HMAC" in capsys.readouterr().err

    sem_hash = tmp_path / "sem_hash.jsonl"  # tira hashes e selo: o replay recusa sem --sem-verificar
    sem_hash.write_text("\n".join(json.dumps({k: v for k, v in json.loads(x).items() if k != "_hash"})
                                  for x in linhas[:-1]) + "\n", encoding="utf-8")
    assert main(["replay", str(sem_hash), e.sid]) == 3
    assert main(["replay", str(sem_hash), e.sid, "--sem-verificar"]) == 0
    assert "NÃO verificado" in capsys.readouterr().err


def test_redaction_covers_non_text_secrets_and_brazilian_ids():
    """Revisão da DSM3: segredo numérico, em lista ou objeto, CPF por nome de campo, CNPJ e telefone."""
    r = redigir({"senha": 12345678, "api_key": {"valor": "abc-segredo-123"}, "token": ["tok-123456789"],
                 "cpf": "12345678901", "obs": "CNPJ 12.345.678/0001-90, tel (48) 99999-1234",
                 "tokens_entrada": 120, "valor": "R$ 1.234,56"})
    assert r["senha"] == r["api_key"] == r["token"] == r["cpf"] == "[SEGREDO REDIGIDO]"
    assert "12.345.678/0001-90" not in r["obs"] and "99999-1234" not in r["obs"]
    assert r["tokens_entrada"] == 120 and r["valor"] == "R$ 1.234,56"  # contadores e valores seguem visíveis


AGOSTO = Scenario("agosto", "waiver em agosto", "fechar_mes", decisao_aprovador="waiver",
                  agenda=(("2026-08", ("alcada",)),), pedidos=(("fechar_mes", "2026-08", 1),))
SETEMBRO = Scenario("setembro", "mesma alçada em setembro", "fechar_mes", decisao_aprovador="waiver",
                    agenda=(("2026-09", ("alcada",)),), pedidos=(("fechar_mes", "2026-09", 1),))


@pytest.mark.parametrize("ataque", ["remover_entrada", "corromper", "apagar_arquivo", "versao_antiga"])
def test_memory_removal_corruption_or_rollback_fails_closed(tmp_path, ataque):
    """Recorreção (N1): sem a memória íntegra, o waiver não é reaberto (falha fechada), em vez de liberar."""
    import shutil

    arquivo = tmp_path / "memoria.json"
    run_scenario(AGOSTO, memoria=arquivo)
    if ataque == "remover_entrada":
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        dados["entradas"] = []
        arquivo.write_text(json.dumps(dados), encoding="utf-8")
    elif ataque == "corromper":
        arquivo.write_text("{corrompido", encoding="utf-8")
    elif ataque == "apagar_arquivo":
        arquivo.unlink()
    else:  # volta a uma cópia antiga, assinada de verdade, depois de uma gravação mais nova
        shutil.copy(arquivo, tmp_path / "antiga.json")
        run_scenario(Scenario("outubro", "nova gravação", "fechar_mes", decisao_aprovador="waiver",
                              agenda=(("2026-10", ("alcada",)),), pedidos=(("fechar_mes", "2026-10", 1),)),
                     memoria=arquivo)
        shutil.copy(tmp_path / "antiga.json", arquivo)
    e = run_scenario(SETEMBRO, memoria=arquivo)
    ticket = e.system.politica.tickets["APR-001"]
    assert "waiver" not in ticket["opcoes"] and ticket["negadas"][0]["regra"] == "POL-06"
    assert any(r["kind"] == "memoria" and r["evento"] == "comprometida" for r in e.audit.records)
    assert e.resposta.performative == "failure"  # o humano pediu waiver: a política não deixou
    assert not e.system.memoria.integra


def test_memory_key_and_counter_live_outside_the_data_folder(tmp_path):
    """Recorreção (N2): a chave HMAC e o contador de versão não ficam ao lado do arquivo de dados."""
    import os

    arquivo = tmp_path / "dados" / "memoria.json"
    run_scenario(AGOSTO, memoria=arquivo)
    assert [p.name for p in arquivo.parent.iterdir()] == ["memoria.json"]
    externos = [p.name for p in pathlib.Path(os.environ["FIN_MAS_DIR_CHAVES"]).iterdir()]
    assert any(n.endswith(".chave") for n in externos) and any(n.endswith(".contador") for n in externos)


def test_memory_ids_stay_unique():
    """Recorreção (N3): ids não se repetem quando entradas saem da lista."""
    tickets = {f"APR-00{i}": ticket(lancamentos=(f"L-00{i}",)) for i in (1, 2, 3)}
    mem = Memoria(AuditLog(), lambda: 0, PoliticaFalsa(**tickets))
    cin = mem.visao("AG-CIN")
    for i in (1, 2):
        cin.gravar("waiver", f"k{i}", {"lancamento": f"L-00{i}"}, competencia="2026-08", aprovacao=f"APR-00{i}", fonte="-")
    mem.entradas.pop(0)
    nova = cin.gravar("waiver", "k3", {"lancamento": "L-003"}, competencia="2026-08", aprovacao="APR-003", fonte="-")
    assert nova["id"] == "MEM-0003" and len({e["id"] for e in mem.entradas}) == len(mem.entradas)


def test_redaction_catches_unmasked_documents_in_free_text():
    """Recorreção (N6): CPF e CNPJ sem máscara em texto livre."""
    r = redigir({"obs": "CPF do fornecedor 12345678901, cnpj 12345678000190, chave pix 98765432100",
                 "valor": "R$ 12.345.678,90", "conta": "C-3001 Pessoal", "seq": 12345678901})
    assert "12345678901" not in r["obs"] and "12345678000190" not in r["obs"] and "98765432100" not in r["obs"]
    assert r["valor"] == "R$ 12.345.678,90" and r["conta"] == "C-3001 Pessoal" and r["seq"] == 12345678901


def test_trace_anchor_verifies_without_the_authors_key(tmp_path, monkeypatch, capsys):
    """Recorreção (N7): em outra máquina (outra chave), a âncora pública verifica o trace sem acusar adulteração."""
    from fin_mas.cli import main

    e = run_scenario("ataque_decisao_forjada")
    arquivo = tmp_path / "t.jsonl"
    e.audit.write_jsonl(arquivo)
    ancora = e.audit.hash_cadeia()
    monkeypatch.setenv("FIN_MAS_CHAVE_TRACE", "chave-de-outra-maquina")
    assert main(["verificar", str(arquivo)]) == 3
    assert "outra chave" in capsys.readouterr().err  # não afirma adulteração sem saber
    assert main(["verificar", str(arquivo), "--ancora", ancora]) == 0
    assert main(["verificar", str(arquivo), "--ancora", "0" * 64]) == 3
    assert run_scenario("ataque_decisao_forjada").audit.hash_cadeia() == ancora  # reproduzível

"""E9 — cenário controlado de depuração (seed 1337) e TEST-16: causalidade pelo trace.

O cenário planta uma violação de SoD (crítica), um lançamento de outra competência
(não crítica) e a perda do primeiro request ao AG-ORC. A narrativa esperada está em
entregas/dsm2/README.md; aqui ela é verificada só a partir do arquivo JSONL.
"""
import pytest

from fin_mas.cli import main
from fin_mas.env.scenarios import run_scenario
from fin_mas.services.audit import AuditLog

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def trace(tmp_path_factory):
    e = run_scenario("depuracao")
    caminho = tmp_path_factory.mktemp("dep") / "trace.jsonl"
    e.audit.write_jsonl(caminho)
    return e, caminho


def test_trace_causal_reconstruction(trace):
    e, caminho = trace
    log = AuditLog.read_jsonl(caminho)  # só o arquivo, sem inspecionar código ou objetos vivos
    assert log.familia(e.sid) == [e.sid, "DEL-001", "DEL-002", "DEL-003", "DEL-004", "CMP-001",
                                  "DEL-005", "QRY-001", "QRY-002"]
    linhas = log.trilha(e.sid)
    marcos = [  # (trecho da linha) na ordem em que devem ocorrer
        "SOL-001  SOL -> AG-ORQ request", "DEL-001  AG-ORQ -> AG-CUS request",
        "DEL-002  PERDIDA AG-ORQ -> AG-ORC request", "DEL-002  TIMEOUT contra AG-ORC",
        "um reenvio por subtarefa", "DEL-003  AG-ORQ -> AG-ORC request",
        "DEL-004  AG-ORQ -> AG-RES request", "QRY-001  AG-RES -> AG-CUS query-ref",
        "DEL-004  AG-RES -> AG-ORQ inform", "CMP-001  AG-CIN -> AG-ORQ veto",
        "CMP-001  AG-ORQ -> APR veto_notice", "aplica 'waiver_humano'", "aplica 'publicar'",
        "DEL-005  AG-ORQ -> AG-REL request", "SOL-001  AG-ORQ -> SOL inform",
    ]
    posicao = -1
    for marco in marcos:
        achada = next((i for i, linha in enumerate(linhas) if marco in linha and i > posicao), None)
        assert achada is not None, f"marco fora de ordem ou ausente: {marco}"
        posicao = achada
    # o trace reconstruído do arquivo é igual ao da memória
    assert linhas == e.audit.trilha(e.sid)


def test_trace_explica_a_causa_da_falha_e_da_ressalva(trace):
    e, caminho = trace
    log = AuditLog.read_jsonl(caminho)
    assert [r["conversation_id"] for r in log.records if r["kind"] == "drop"] == ["DEL-002"]
    decisao_cin = next(r for r in log.records if r["kind"] == "decision" and r["agente"] == "AG-CIN")
    assert decisao_cin["resultado"] == {"achados": 2, "criticos": 1}
    veto = next(r for r in log.records if r["kind"] == "send" and r["performative"] == "veto")
    assert [(a["regra"], a["severidade"]) for a in veto["content"]["achados"]] == [
        ("competencia", "nao_critica"), ("sod", "critica")]
    assert e.resposta.content["status"] == "publicado_com_ressalva"


def test_cli_run_e_replay_mostram_a_mesma_trilha(trace, tmp_path, capsys):
    e, _ = trace
    arquivo = tmp_path / "t.jsonl"
    assert main(["run", "--scenario", "depuracao", "--trace", str(arquivo)]) == 0
    saida_run = capsys.readouterr().out
    assert main(["replay", str(arquivo), e.sid]) == 0
    saida_replay = capsys.readouterr().out
    assert saida_replay.strip() in saida_run
    assert "PERDIDA" in saida_replay and "TIMEOUT" in saida_replay and "veto" in saida_replay


def test_cli_lista_cenarios_e_rejeita_desconhecido(capsys, tmp_path):
    (tmp_path / "vazio.jsonl").write_text("", encoding="utf-8")
    assert main(["list"]) == 0
    assert "depuracao" in capsys.readouterr().out
    assert main(["run", "--scenario", "inexistente"]) == 2
    assert main(["replay", str(tmp_path / "vazio.jsonl"), "X"]) == 2

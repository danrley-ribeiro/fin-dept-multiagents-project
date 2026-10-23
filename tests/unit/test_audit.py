from fin_mas.services.audit import AuditLog


def preenchido():
    log = AuditLog()
    log.record(1, "send", conversation_id="DEL-001", performative="request")
    log.record(2, "send", conversation_id="DEL-002", performative="request")
    log.record(3, "deliver", conversation_id="DEL-001", performative="request")
    return log


def test_seq_cresce_e_filtra_por_conversa():
    log = preenchido()
    assert [r["seq"] for r in log.records] == [1, 2, 3]
    assert [r["t"] for r in log.by_conversation("DEL-001")] == [1, 3]


def test_jsonl_ida_e_volta(tmp_path):
    log = preenchido()
    arquivo = tmp_path / "trace.jsonl"
    log.write_jsonl(arquivo)
    assert len(arquivo.read_text(encoding="utf-8").splitlines()) == 3
    assert AuditLog.read_jsonl(arquivo).records == log.records


def test_digest_depende_do_conteudo():
    a, b = preenchido(), preenchido()
    assert a.digest() == b.digest()
    b.record(4, "send")
    assert a.digest() != b.digest()

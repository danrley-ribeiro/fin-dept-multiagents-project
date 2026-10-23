import pytest

from fin_mas.core.fsm import Conversation, ProtocolViolation, load_protocols

PROTOCOLOS = load_protocols()


def conv(pid):
    return Conversation(PROTOCOLOS[pid], "c-1", "A", "B")


def percorre(pid, eventos):
    c = conv(pid)
    for e in eventos:
        c.step(e)
    return c


def test_carrega_os_seis_protocolos():
    assert set(PROTOCOLOS) == {"PROT-SOL", "PROT-DEL", "PROT-QRY", "PROT-CMP", "PROT-LCK", "PROT-APR"}


@pytest.mark.parametrize("pid,eventos,final", [
    ("PROT-SOL", ["agree", "inform"], "CONCLUIDA"),
    ("PROT-SOL", ["not-understood"], "RECUSADA"),
    ("PROT-SOL", ["refuse"], "RECUSADA"),
    ("PROT-SOL", ["agree", "failure"], "FALHOU"),
    ("PROT-DEL", ["request", "agree", "inform"], "CONCLUIDA"),
    ("PROT-DEL", ["request", "refuse"], "RECUSADA"),
    ("PROT-DEL", ["request", "agree", "failure"], "FALHOU"),
    ("PROT-DEL", ["request", "timeout"], "EXPIRADA"),
    ("PROT-DEL", ["request", "agree", "timeout"], "EXPIRADA"),
    ("PROT-QRY", ["query-ref", "inform"], "RESPONDIDA"),
    ("PROT-QRY", ["query-ref", "timeout"], "EXPIRADA"),
    ("PROT-CMP", ["request", "conforme"], "LIBERADO"),
    ("PROT-CMP", ["request", "nao_conforme_nao_critico", "publicar"], "LIBERADO"),
    ("PROT-CMP", ["request", "veto", "waiver_humano", "publicar"], "LIBERADO"),
    ("PROT-CMP", ["request", "veto", "prazo_esgotado"], "BLOQUEADO"),
    ("PROT-CMP", ["request", "veto", "correcao", "conforme"], "LIBERADO"),
    ("PROT-LCK", ["reserve", "release"], "LIVRE"),
    ("PROT-LCK", ["reserve", "ttl_expirado"], "LIVRE"),
])
def test_transicoes_nominais(pid, eventos, final):
    assert percorre(pid, eventos).state == final


@pytest.mark.parametrize("pid,eventos,evento_invalido", [
    ("PROT-SOL", [], "inform"),
    ("PROT-SOL", ["agree", "inform"], "inform"),
    ("PROT-DEL", ["request"], "inform"),
    ("PROT-DEL", ["request", "timeout"], "inform"),
    ("PROT-QRY", [], "inform"),
    ("PROT-CMP", ["request", "veto"], "publicar"),
    ("PROT-LCK", [], "release"),
    ("PROT-APR", ["require_approval"], "execute"),
    ("PROT-APR", ["deny"], "approve"),
])
def test_transicoes_invalidas_levantam_violacao(pid, eventos, evento_invalido):
    c = percorre(pid, eventos)
    estado = c.state
    with pytest.raises(ProtocolViolation):
        c.step(evento_invalido)
    assert c.state == estado


def test_motivo_da_dsm1_aparece_na_violacao():
    c = percorre("PROT-DEL", ["request"])
    with pytest.raises(ProtocolViolation, match="resultado antes de agree"):
        c.step("inform")

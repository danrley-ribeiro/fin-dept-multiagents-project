"""DSM3 — achados da revisão do PR #1 (Danrley), um teste de regressão por achado.

1. decisão recusada não pode consumir a pendência do aprovador;
2. waiver humano exige justificativa escrita pelo humano (sem texto padrão);
3. `replay` lê trace de outra máquina com `--ancora`;
4. a redação de CPF/CNPJ sem máscara não altera hashes hexadecimais;
5. a NORM-05 compara números pelo valor (escala errada é número estranho);
6. o pseudônimo da memória não se reverte por dicionário (HMAC com a chave da memória);
7. a regra de competência é a mesma no barramento, no dashboard e na memória.
"""
import hashlib
import random

import pytest

from fin_mas.cli import main
from fin_mas.core.bus import MensagemRejeitada
from fin_mas.core.schema import FORMATOS
from fin_mas.env.scenarios import build_system
from fin_mas.live import COMPETENCIA as COMPETENCIA_LIVE
from fin_mas.live import ComandoInvalido, validar
from fin_mas.services.audit import AuditLog
from fin_mas.services.memoria import COMPETENCIA as COMPETENCIA_MEM
from fin_mas.services.memoria import Memoria
from fin_mas.services.modelos import numeros
from fin_mas.services.redacao import redigir, redigir_texto
from helpers import rodar_ate_humano

pytestmark = pytest.mark.e2e
JUSTIFICATIVA = "aceito o risco: lançamento será corrigido no próximo ciclo"


def pendente():
    s = build_system(plantar=("alcada",), interativo=True)
    sid = s.usuario.solicitar("fechar_mes")
    rodar_ate_humano(s.bus)
    return s, sid, s.aprovador.pendentes[sid]


# ---- 1. pendência só sai depois de a decisão ser aceita ----------------------------------
def test_refused_decision_keeps_pending_and_can_be_retried():
    s, sid, proposta = pendente()
    with pytest.raises(MensagemRejeitada, match="POL-04"):
        s.aprovador.decidir(sid, "waiver", "aaaaaaaaaa")  # 10 caracteres, uma palavra só
    assert sid in s.aprovador.pendentes
    assert s.politica.tickets[proposta.conversation_id]["estado"] == "pendente"
    assert s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA) is True
    assert sid not in s.aprovador.pendentes
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"] == "publicado_com_ressalva"


def test_option_not_offered_reports_nothing_sent_and_keeps_pending():
    s, sid, proposta = pendente()
    proposta.content["opcoes"] = [o for o in proposta.content["opcoes"] if o != "corrigir"]
    assert s.aprovador.decidir(sid, "corrigir") is False
    assert sid in s.aprovador.pendentes
    assert s.bus.conversations[proposta.conversation_id].state == "PENDENTE"


def test_waiver_denied_by_policy_is_not_turned_into_a_block_in_the_dashboard():
    """Teste manual no dashboard: com o waiver negado (ex.: reincidência, POL-06), escolher waiver
    não pode bloquear a publicação em silêncio; nada é enviado e a pendência continua."""
    s, sid, proposta = pendente()
    proposta.content["opcoes"] = [o for o in proposta.content["opcoes"] if o != "waiver"]
    assert s.aprovador.decidir(sid, "waiver", JUSTIFICATIVA) is False
    assert sid in s.aprovador.pendentes
    assert s.bus.conversations[proposta.conversation_id].state == "PENDENTE"
    assert s.aprovador.decidir(sid, "corrigir") is True
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"] == "publicado"


# ---- 2. waiver sem justificativa humana ------------------------------------------------
@pytest.mark.parametrize("justificativa", [None, "", "   "])
def test_waiver_without_human_justification_is_refused(justificativa):
    s, sid, proposta = pendente()
    with pytest.raises(MensagemRejeitada):
        s.aprovador.decidir(sid, "waiver", justificativa)
    ticket = s.politica.tickets[proposta.conversation_id]
    assert ticket["estado"] == "pendente" and ticket["justificativa"] is None
    assert sid in s.aprovador.pendentes
    assert not any(JUSTIFICATIVA in str(r) for r in s.bus.audit.records)  # nenhum texto atribuído ao humano


def test_block_without_justification_says_none_was_given():
    s, sid, proposta = pendente()
    assert s.aprovador.decidir(sid, "bloquear") is True
    s.bus.run()
    assert "sem justificativa informada" in s.politica.tickets[proposta.conversation_id]["justificativa"]
    assert s.usuario.resposta(sid).content["publicado"] is False


# ---- 3. replay de trace gravado com outra chave -----------------------------------------
def test_replay_reads_trace_from_another_machine_with_anchor(tmp_path, monkeypatch):
    arquivo = tmp_path / "t.jsonl"
    monkeypatch.setenv("FIN_MAS_CHAVE_TRACE", "chave-do-autor")
    assert main(["run", "--scenario", "veto_waiver", "--trace", str(arquivo)]) == 0
    ancora = AuditLog.read_jsonl(arquivo).hash_final
    monkeypatch.setenv("FIN_MAS_CHAVE_TRACE", "chave-do-professor")
    assert main(["replay", str(arquivo), "SOL-001"]) == 3  # selo HMAC de outra chave
    assert main(["replay", str(arquivo), "SOL-001", "--ancora", ancora]) == 0
    assert main(["replay", str(arquivo), "SOL-001", "--ancora", "0" * 64]) == 3  # âncora errada
    assert main(["replay", str(tmp_path / "nao-existe.jsonl"), "SOL-001", "--ancora", ancora]) == 2


# ---- 4. redação não altera hashes -----------------------------------------------------
def test_redaction_keeps_hex_digests_intact():
    exemplo = "670671cd97404156226e507973f2ab8330d3022ca96e0c93bdbdb320c41adcaf"
    assert redigir_texto(exemplo) == exemplo
    gerador = random.Random(5)
    for _ in range(20_000):
        h = hashlib.sha256(gerador.randbytes(16)).hexdigest()
        assert redigir_texto(h) == h, h
    registro = AuditLog().record(0, "teste", veto=exemplo)
    assert registro["veto"] == exemplo


def test_redaction_still_removes_unmasked_documents():
    assert "12345678901" not in redigir_texto("CPF do fornecedor 12345678901 informado")
    assert "12345678000199" not in redigir_texto("cnpj 12345678000199.")
    assert redigir({"obs": "doc (12345678901)"})["obs"] == "doc ([DOCUMENTO REDIGIDO])"


# ---- 5. NORM-05 compara pelo valor ----------------------------------------------------
@pytest.mark.parametrize("texto, aceito", [
    ("receita de R$ 1.234,56; margem de 12,5%.", True),
    ("receita de R$ 12.345,6; margem 1,25%.", False),
    ("receita de R$ 123.456; margem 125%.", False),
    ("receita de R$ 1.234,57; margem de 12,5%.", False),
])
def test_norm05_number_check_respects_scale(texto, aceito):
    base = numeros("Receita: R$ 1.234,56 / Margem: 12,5%")
    assert (not (numeros(texto) - base)) is aceito


# ---- 6. pseudônimo com chave --------------------------------------------------------
def test_pseudonym_is_keyed_and_not_reversible_by_dictionary(monkeypatch):
    monkeypatch.delenv("FIN_MAS_CHAVE_MEMORIA", raising=False)
    a, b = Memoria(AuditLog(), lambda: 0), Memoria(AuditLog(), lambda: 0)
    assert a.pseudonimo("ana") == a.pseudonimo("ana")  # estável com a mesma chave (reincidência)
    assert a.pseudonimo("ana") != b.pseudonimo("ana")  # outra chave, outro pseudônimo
    sem_chave = "pessoa#" + hashlib.sha256(b"fin-mas-mem:ana").hexdigest()[:10]
    assert a.pseudonimo("ana") != sem_chave  # a tabela do formato antigo não serve mais
    monkeypatch.setenv("FIN_MAS_CHAVE_MEMORIA", "chave-fixa")
    assert Memoria(AuditLog(), lambda: 0).pseudonimo("ana") == Memoria(AuditLog(), lambda: 0).pseudonimo("ana")


# ---- 7. competência com uma regra só -------------------------------------------------
def test_competence_rule_is_shared():
    assert COMPETENCIA_MEM is FORMATOS["aaaa-mm"][0] and COMPETENCIA_LIVE is FORMATOS["aaaa-mm"][0]
    assert COMPETENCIA_MEM.fullmatch("1999-12") is None and COMPETENCIA_MEM.fullmatch("2026-09")
    with pytest.raises(ComandoInvalido):
        validar({"tipo": "solicitar", "intencao": "fechar_mes", "competencia": "1999-12"})

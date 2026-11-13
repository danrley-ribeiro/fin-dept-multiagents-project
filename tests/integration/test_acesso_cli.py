"""Linha de comando do SVC-IAM e da auditoria (ADR-009): ciclo completo por subprocesso, em pasta temporária.

Cada comando roda como o usuário rodaria no terminal. A chave e os contadores dos arquivos
selados ficam numa pasta própria do teste (`FIN_MAS_DIR_CHAVES`), fora da pasta de dados.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from fin_mas.invariantes import INVARIANTES

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
ADM, NOVA = "Administrador-2026-forte", "Temporaria-2026-abcd"


@pytest.fixture
def cli(tmp_path):
    base = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1",
            "FIN_MAS_DIR_CHAVES": str(tmp_path / "chaves"), "FIN_MAS_CHAVE_TRACE": "chave-de-teste-do-trace"}
    pasta = str(tmp_path / "acesso")

    def rodar(*args, senha=None, nova=None, acesso=True, entrada=None):
        env = dict(base)
        env.pop("FIN_MAS_SENHA", None)
        env.pop("FIN_MAS_SENHA_NOVA", None)
        if senha:
            env["FIN_MAS_SENHA"] = senha
        if nova:
            env["FIN_MAS_SENHA_NOVA"] = nova
        comando = [sys.executable, "-m", "fin_mas"] + (["acesso", "--acesso", pasta] if acesso else []) + list(args)
        return subprocess.run(comando, capture_output=True, text=True, cwd=RAIZ, env=env, input=entrada)
    rodar.pasta = Path(pasta)
    return rodar


def test_full_account_lifecycle_from_the_terminal(cli):
    assert "nenhuma conta" in cli("usuario", "listar").stdout
    r = cli("iniciar", "--usuario", "raiz", nova="curta")
    assert r.returncode == 3 and "IAM-02" in r.stderr  # senha fraca recusada
    assert cli("iniciar", "--usuario", "raiz", nova=ADM).returncode == 0
    segundo = cli("iniciar", "--usuario", "outro", nova=ADM)
    assert segundo.returncode == 3 and "IAM-01" in segundo.stderr  # bootstrap só uma vez
    sem_quem = cli("usuario", "criar", "maria", "--nome", "Maria", "--papeis", "ROLE-APR", nova=NOVA)
    assert sem_quem.returncode == 3 and "--como" in sem_quem.stderr
    senha_errada = cli("--como", "raiz", "usuario", "criar", "maria", "--nome", "Maria", "--papeis", "ROLE-APR",
                       senha="errada-errada-123", nova=NOVA)
    assert senha_errada.returncode == 3 and "IAM-03" in senha_errada.stderr
    criar = cli("--como", "raiz", "usuario", "criar", "maria", "--nome", "Maria Souza", "--papeis", "ROLE-APR,ROLE-SOL",
                "--pessoa", "carla", "--cargo", "gerente", senha=ADM, nova=NOVA)
    assert criar.returncode == 0 and "maria" in criar.stdout and "cargo: gerente" in criar.stdout
    contas = json.loads(cli("--json", "usuario", "listar").stdout)
    maria = next(c for c in contas if c["usuario"] == "maria")
    assert maria["papeis"] == ["ROLE-APR", "ROLE-SOL"] and maria["trocar_senha"] is True and "senha" not in maria
    # incompatibilidade e proteção do último administrador
    acumular = cli("--como", "raiz", "usuario", "papeis", "raiz", "ROLE-ADM", "ROLE-APR", senha=ADM)
    assert acumular.returncode == 3 and "IAM-06" in acumular.stderr
    ultimo = cli("--como", "raiz", "usuario", "desativar", "raiz", senha=ADM)
    assert ultimo.returncode == 3 and "último administrador" in ultimo.stderr
    # quem não é administrador não administra
    nao_adm = cli("--como", "maria", "usuario", "bloquear", "raiz", senha=NOVA)
    assert nao_adm.returncode == 3 and "IAM-05" in nao_adm.stderr
    assert cli("--como", "raiz", "usuario", "bloquear", "maria", senha=ADM).returncode == 0
    bloqueada = cli("--como", "maria", "sessao", "listar", senha=NOVA)
    assert bloqueada.returncode == 3 and "bloqueada" in bloqueada.stderr
    assert cli("--como", "raiz", "usuario", "desbloquear", "maria", senha=ADM).returncode == 0
    assert cli("--como", "raiz", "usuario", "redefinir-senha", "maria", senha=ADM, nova="Outra-Senha-2026-x").returncode == 0
    sessoes = json.loads(cli("--json", "--como", "raiz", "sessao", "listar", senha=ADM).stdout)
    assert sessoes and all(s["usuario"] in ("raiz", "maria") for s in sessoes)
    # nada de senha em claro no disco
    disco = "".join(p.read_text(encoding="utf-8") for p in cli.pasta.iterdir() if p.is_file())
    assert ADM not in disco and NOVA not in disco and "scrypt$" in disco


def test_access_trail_is_listed_verified_and_tampering_is_detected(cli):
    cli("demo")
    cli("--como", "admin", "usuario", "bloquear", "bruno", senha="Demonstracao-SMA-2026")
    cli("--como", "operador", "usuario", "bloquear", "ana", senha="Demonstracao-SMA-2026")  # negado: fica na trilha
    ver = cli("trilha", "ver", "--resultado", "negado")
    assert ver.returncode == 0 and "IAM-05" in ver.stdout and "operador" in ver.stdout
    registros = json.loads(cli("--json", "trilha", "ver", "--evento", "conta_bloqueada").stdout)
    assert [(r["ator"], r["alvo"]) for r in registros] == [("admin", "bruno")]
    ok = cli("trilha", "verificar")
    assert ok.returncode == 0 and "íntegra" in ok.stdout
    destino = cli.pasta.parent / "trilha_exportada.jsonl"
    assert cli("trilha", "exportar", str(destino)).returncode == 0 and destino.read_text(encoding="utf-8").count("\n") > 10
    # 1) alterar um registro; 2) truncar o arquivo: os dois são acusados
    arquivo = cli.pasta / "trilha.jsonl"
    original = arquivo.read_text(encoding="utf-8")
    arquivo.write_text(original.replace('"resultado": "negado"', '"resultado": "ok"', 1), encoding="utf-8")
    alterada = cli("trilha", "verificar")
    assert alterada.returncode == 3 and "ADULTERADA" in alterada.stderr and "cadeia quebrada" in alterada.stderr
    arquivo.write_text("\n".join(original.splitlines()[:-2]) + "\n", encoding="utf-8")
    truncada = cli("trilha", "verificar")
    assert truncada.returncode == 3 and "truncada" in truncada.stderr


def test_rolled_back_account_file_is_refused(cli):
    """Recolocar uma cópia antiga do cadastro (ex.: de antes de um bloqueio) não funciona: falha fechada."""
    cli("demo")
    antigo = (cli.pasta / "contas.json").read_text(encoding="utf-8")
    assert cli("--como", "admin", "usuario", "bloquear", "carla", senha="Demonstracao-SMA-2026").returncode == 0
    (cli.pasta / "contas.json").write_text(antigo, encoding="utf-8")
    r = cli("usuario", "listar")
    assert r.returncode == 3 and "IAM-07" in r.stderr and "versão antiga" in r.stderr


def test_concurrent_writers_do_not_lose_updates(cli):
    """Dois processos gravando ao mesmo tempo (TUI e servidor): a trava e a releitura preservam tudo."""
    cli("demo")
    nomes = [f"pessoa{i:02d}" for i in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        resultados = list(pool.map(lambda u: cli("--como", "admin", "usuario", "criar", u, "--nome", u, "--papeis",
                                                 "ROLE-SOL", senha="Demonstracao-SMA-2026", nova=NOVA), nomes))
    assert [r.returncode for r in resultados] == [0] * 6, [r.stderr for r in resultados]
    contas = {c["usuario"] for c in json.loads(cli("--json", "usuario", "listar").stdout)}
    assert set(nomes) <= contas
    assert cli("trilha", "verificar").returncode == 0  # a cadeia da trilha também sobrevive à concorrência


def test_role_matrix_comes_from_the_models(cli):
    saida = cli("papeis").stdout
    assert "ROLE-ADM" in saida and "PERM-IAM-USUARIOS" in saida and "ROLE-AUD" in saida
    matriz = json.loads(cli("--json", "papeis").stdout)
    assert "PERM-APR-DECIDIR" in matriz["ROLE-APR"] and "PERM-APR-DECIDIR" not in matriz["ROLE-OPE"]
    assert "PERM-SIM-OPERAR" not in matriz["ROLE-AUD"] and not set(matriz["ROLE-ADM"]) & {"PERM-APR-DECIDIR", "PERM-SOL-CRIAR"}


def test_audit_explain_sequence_and_invariants_over_a_saved_trace(cli, tmp_path):
    trace = str(tmp_path / "trace.jsonl")
    assert cli("run", "--scenario", "orc_hipotese_local", "--trace", trace, acesso=False).returncode == 0
    recorte = cli("auditoria", trace, "--agente", "AG-ORC", "--tipo", "hipotese", acesso=False)
    assert recorte.returncode == 0 and recorte.stdout.count("HIPOTESE AG-ORC") == 3 and "3 de " in recorte.stdout
    por_tarefa = json.loads(cli("auditoria", trace, "--tarefa", "QRY-002", "--json", acesso=False).stdout)
    assert por_tarefa and {r["conversation_id"] for r in por_tarefa} == {"QRY-002"}
    confirmada = next(r for r in json.loads(cli("auditoria", trace, "--tipo", "hipotese", "--json", acesso=False).stdout)
                      if r["evento"] == "confirmada")
    por_que = cli("explicar", trace, str(confirmada["seq"]), acesso=False).stdout
    assert "por que:" in por_que and "[hipótese" in por_que and "[deliberação" in por_que and "[percepção (tool)" in por_que
    seq = cli("sequencia", trace, "SOL-001", acesso=False).stdout
    assert seq.startswith("sequenceDiagram") and "query-ref [QRY-002]" in seq
    inv = cli("invariantes", trace, acesso=False)
    # DSM4: o catálogo de invariantes cresceu (INV-09, INV-10); confere-se contra o tamanho dele
    assert inv.returncode == 0 and f"{len(INVARIANTES)} invariantes, 0 violação" in inv.stdout
    # um trace adulterado nem chega aos invariantes: a cadeia de hashes acusa antes
    linhas = Path(trace).read_text(encoding="utf-8").splitlines()
    linhas[10] = linhas[10].replace("AG-ORC", "AG-CIN", 1)
    Path(trace).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    assert cli("invariantes", trace, acesso=False).returncode == 3


def test_invariant_checker_flags_a_forged_trace(tmp_path):
    """O verificador não confia no trace: publicação sobre veto, efeito sem aprovação e crença de modelo são acusados."""
    from fin_mas import invariantes
    from fin_mas.env.scenarios import run_scenario
    limpo = run_scenario("veto_correcao").audit.records
    assert invariantes.verificar(limpo) == []
    sem_tratamento = [r for r in limpo if not (r["kind"] == "send" and r.get("performative") in ("correcao", "conforme"))]
    sem_aprovacao = [r for r in limpo if not (r["kind"] == "politica" and r.get("evento") == "decidido")]
    forjada = limpo + [{"seq": 9999, "t": 99, "kind": "belief", "agente": "AG-ORC", "chave": "x", "antes": None,
                        "depois": 1, "fonte": "llm:mock/x@p", "conversation_id": "DEL-001"}]
    assert any(v.startswith("INV-01") for v in invariantes.verificar(sem_tratamento))
    assert any(v.startswith("INV-02") for v in invariantes.verificar(sem_aprovacao))
    assert any(v.startswith("INV-05") for v in invariantes.verificar(forjada))
    sem_resposta = [r for r in limpo if not (r["kind"] == "send" and r.get("protocol") == "PROT-SOL")]
    assert any(v.startswith("INV-07") for v in invariantes.verificar(sem_resposta))
    assert not any(v.startswith("INV-07") for v in invariantes.verificar(sem_resposta, completo=False))


def test_scenario_catalog_runs_from_the_terminal(cli):
    r = cli("cenarios", "--verificar", "--filtro", "hipotese", acesso=False)
    assert r.returncode == 0 and "6 de 6 cenário(s) em ordem" in r.stdout and "NÃO" not in r.stdout
    assert "orc_hipotese_local" in r.stdout and "VIOLAÇÃO" not in r.stdout


def test_verify_with_anchor_on_unchained_trace_returns_three(cli, tmp_path):
    """Residual da correção simulada: conferir âncora num trace sem cadeia é falha de verificação (3), não aviso (1)."""
    sem_cadeia = tmp_path / "antigo.jsonl"
    sem_cadeia.write_text('{"seq": 1, "t": 0, "kind": "meta"}\n', encoding="utf-8")
    assert cli("verificar", str(sem_cadeia), acesso=False).returncode == 1
    r = cli("verificar", str(sem_cadeia), "--ancora", "0" * 64, acesso=False)
    assert r.returncode == 3 and "não pode ser conferida" in r.stderr


def test_revoked_or_demoted_actor_cannot_keep_administering(tmp_path, monkeypatch):
    """Quem guarda o objeto da sessão em memória não age depois de revogado; e valem os papéis de agora."""
    from fin_mas.services.iam import SENHA_DEMO, Acesso, AcessoNegado, criar_demo
    monkeypatch.setenv("FIN_MAS_DIR_CHAVES", str(tmp_path / "chaves"))
    a = criar_demo(tmp_path / "acesso", custo_scrypt=10)
    adm, _ = a.autenticar("admin", SENHA_DEMO, "console")
    outro = Acesso(tmp_path / "acesso", custo_scrypt=10)  # outro processo
    adm2, _ = outro.autenticar("admin", SENHA_DEMO, "terminal")
    outro.criar_conta(adm2, "segundo", "Segundo Administrador", "Outra-Senha-2026-xy", ["ROLE-ADM"], trocar_senha=False)
    assert adm.id in outro.revogar_usuario(adm2, "admin") and adm2.id not in outro.revogar_usuario(adm2, "admin")
    with pytest.raises(AcessoNegado, match="IAM-04"):
        a.bloquear(adm, "bruno")  # a sessão antiga foi revogada no outro processo
    assert a.conta("bruno")["estado"] == "ativa"
    # rebaixado: perde o papel de administrador e, com ele, o poder de administrar, na mesma sessão
    seg, _ = a.autenticar("segundo", "Outra-Senha-2026-xy", "console")
    outro.atribuir_papeis(adm2, "segundo", ["ROLE-AUD"])
    with pytest.raises(AcessoNegado, match="IAM-05"):
        a.bloquear(seg, "bruno")
    negadas = [(r["ator"], r["regra"]) for r in a.trilha.ler() if r["evento"] == "permissao" and r["resultado"] == "negado"]
    assert negadas == [("admin", "IAM-04"), ("segundo", "IAM-05")]


def test_invariant_checker_has_no_false_alarm_on_resend_and_catches_what_it_missed():
    """Correção simulada da v0.5.0 (M8): um falso positivo (reenvio do pedido de parecer) e dois falsos negativos
    (fechamento publicado sem parecer do AG-CIN; correção aprovada usada duas vezes)."""
    from fin_mas import invariantes
    from fin_mas.env.scenarios import build_system, run_scenario

    s = build_system(faults=({"receiver": "AG-CIN", "performative": "request", "times": 1},))
    sid = s.usuario.solicitar("fechar_mes")
    s.bus.run()
    assert s.usuario.resposta(sid).content["status"].startswith("publicado")
    assert [r for r in s.bus.audit.records if r["kind"] == "timeout" and r.get("protocol") == "PROT-CMP"]
    assert invariantes.verificar(s.bus.audit.records) == []  # o aviso de prazo do PROT-CMP não é transição

    limpo = run_scenario("fechar_mes").audit.records
    sem_cin = [r for r in limpo if r.get("protocol") != "PROT-CMP"]
    assert any("sem parecer de conformidade" in v for v in invariantes.verificar(sem_cin))

    corrigido = run_scenario("veto_correcao").audit.records
    efeito = next(r for r in corrigido if r["kind"] == "mcp_call" and r.get("tool") == "erp.corrigir")
    repetido = corrigido + [{**efeito, "seq": 99999}]
    assert any("uso único" in v for v in invariantes.verificar(repetido))

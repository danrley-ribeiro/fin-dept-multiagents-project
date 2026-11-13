"""Acesso avançado pela linha de comando (DSM4, ADR-012): subprocesso real, arquivos reais em pasta temporária.

Segundo fator (IAM-08) com o relógio de verdade, política do cadastro, cofre (IAM-10), empresas
(IAM-09), delegação (POL-11) e a memória: adoção de cópia íntegra e duas execuções simultâneas
sobre o mesmo arquivo. Os códigos TOTP são gerados pelo teste com o segredo mostrado na ativação.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from fin_mas.services import totp

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
SENHA = "Demonstracao-SMA-2026"


@pytest.fixture
def cli(tmp_path):
    base = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1",
            "FIN_MAS_DIR_CHAVES": str(tmp_path / "chaves"), "FIN_MAS_CHAVE_TRACE": "chave-de-teste-do-trace"}
    for v in ("FIN_MAS_SENHA", "FIN_MAS_SENHA_NOVA", "FIN_MAS_CODIGO_2FA", "FIN_MAS_SEGREDO"):
        base.pop(v, None)
    pasta = str(tmp_path / "acesso")

    def rodar(*args, como=None, senha=SENHA, codigo=None, segredo=None, prefixo=("acesso", "--acesso", pasta)):
        env = dict(base, FIN_MAS_SENHA=senha)
        if codigo:
            env["FIN_MAS_CODIGO_2FA"] = codigo
        if segredo:
            env["FIN_MAS_SEGREDO"] = segredo
        comando = [sys.executable, "-m", "fin_mas", *prefixo, *(["--como", como] if como else []), *args]
        return subprocess.run(comando, capture_output=True, text=True, cwd=RAIZ, env=env, stdin=subprocess.DEVNULL)
    rodar.pasta, rodar.env, rodar.tmp = Path(pasta), base, tmp_path
    assert rodar("demo").returncode == 0
    return rodar


def test_second_factor_from_the_terminal_with_policy_replay_and_recovery_codes(cli):
    assert cli("politica", "definir", "--exigir-2fa", "ROLE-ADM", como="admin").returncode == 0
    pendente = cli("sessao", "listar", como="admin")  # política exige e a conta ainda não ativou: só ativar
    assert pendente.returncode == 3 and "IAM-08" in pendente.stderr
    ativar = json.loads(cli("--json", "2fa", "ativar", como="admin").stdout)
    assert ativar["uri"].startswith("otpauth://totp/") and ativar["segredo"] in ativar["uri"]
    codigo = totp.codigo(ativar["segredo"], time.time())
    confirmado = json.loads(cli("--json", "2fa", "confirmar", como="admin", codigo=codigo).stdout)
    codigos = confirmado["codigos_recuperacao"]
    assert len(codigos) == 10 and len(set(codigos)) == 10
    # o cadastro guarda só hashes dos códigos de recuperação, e o segredo fica fora dele (no cofre)
    cadastro = (cli.pasta / "contas.json").read_text(encoding="utf-8")
    assert ativar["segredo"] not in cadastro and not any(c in cadastro for c in codigos)
    sem_codigo = cli("sessao", "listar", como="admin")
    assert sem_codigo.returncode == 3 and "FIN_MAS_CODIGO_2FA" in sem_codigo.stderr
    replay = cli("sessao", "listar", como="admin", codigo=codigo)  # o código da ativação não vale de novo
    assert replay.returncode == 3 and "IAM-08" in replay.stderr and "replay" in replay.stderr
    adiante = cli("sessao", "listar", como="admin", codigo=totp.codigo(ativar["segredo"], time.time() + 600))
    assert adiante.returncode == 3 and "fora da janela" in adiante.stderr
    assert cli("sessao", "listar", como="admin", codigo=codigos[0]).returncode == 0
    reuso = cli("sessao", "listar", como="admin", codigo=codigos[0])
    assert reuso.returncode == 3 and "já usado" in reuso.stderr
    contas = json.loads(cli("--json", "usuario", "listar").stdout)
    admin = next(c for c in contas if c["usuario"] == "admin")
    assert admin["segundo_fator"] == {"ativo": True, "desde": admin["segundo_fator"]["desde"], "codigos_restantes": 9}
    trilha = [json.loads(x) for x in (cli.pasta / "trilha.jsonl").read_text(encoding="utf-8").splitlines()]
    eventos = [(r["evento"], r["resultado"]) for r in trilha if r.get("regra") == "IAM-08"]
    assert ("2fa_ativado", "ok") in eventos and ("segundo_fator", "negado") in eventos
    assert cli("trilha", "verificar").returncode == 0
    # desativar exige um código válido
    # desativar: a entrada consome um código e a confirmação precisa de outro, também válido
    env_dois = cli("2fa", "desativar", como="admin", codigo=codigos[1])
    assert env_dois.returncode == 3 and "já usado" in env_dois.stderr  # o mesmo código não serve duas vezes
    assert "codigos_restantes" in json.dumps(contas)
    # sem o segundo fator, a política volta a travar a conta até ela ativá-lo de novo
    assert cli("politica", "definir", "--exigir-2fa", "nenhum", como="admin", codigo=codigos[2]).returncode == 0
    assert cli("sessao", "listar", como="admin", codigo=codigos[3]).returncode == 0


def test_vault_keeps_llm_keys_without_ever_showing_them(cli):
    valor = "sk-teste-" + "a1b2c3d4e5f6g7h8i9j0"
    assert cli("segredo", "definir", "llm:OPENAI_API_KEY", como="operador", segredo=valor).returncode == 3  # sem permissão
    definir = cli("segredo", "definir", "llm:OPENAI_API_KEY", como="admin", segredo=valor)
    assert definir.returncode == 0 and valor not in definir.stdout
    interno = cli("segredo", "definir", "totp:carla", como="admin", segredo="ABCDEF")
    assert interno.returncode == 3 and "IAM-10" in interno.stderr  # segredo interno não é da interface
    listar = cli("--json", "segredo", "listar", como="admin")
    assert json.loads(listar.stdout) == [{"nome": "llm:OPENAI_API_KEY", "por": "admin",
                                          "em": json.loads(listar.stdout)[0]["em"]}] and valor not in listar.stdout
    (cofre,) = (cli.tmp / "chaves").glob("cofre-*.json")
    assert stat.S_IMODE(cofre.stat().st_mode) == 0o600 and not str(cofre).startswith(str(cli.pasta))
    provedores = subprocess.run([sys.executable, "-c", (
        "from fin_mas.services import provedores; from fin_mas.services.iam import Acesso;"
        f"provedores.usar_cofre(Acesso({str(cli.pasta)!r}).cofre);"
        "print([p['tem_chave'] for p in provedores.situacao() if p['id'] == 'openai'][0])")],
        capture_output=True, text=True, cwd=RAIZ, env={**cli.env, "OPENAI_API_KEY": ""})
    assert provedores.stdout.strip() == "True"  # a chave do cofre vale quando o ambiente não tem
    assert cli("segredo", "remover", "llm:OPENAI_API_KEY", como="admin").returncode == 0
    assert json.loads(cli("--json", "segredo", "listar", como="admin").stdout) == []
    trilha = (cli.pasta / "trilha.jsonl").read_text(encoding="utf-8")
    assert '"segredo_definido"' in trilha and valor not in trilha
    # cofre alterado fora do sistema: falha fechada
    dados = json.loads(cofre.read_text(encoding="utf-8"))
    dados["dados"]["segredos"]["llm:X"] = {"valor": "forjado", "por": "intruso", "em": 0}
    cofre.write_text(json.dumps(dados), encoding="utf-8")
    assert cli("segredo", "listar", como="admin").returncode != 0


def test_delegation_policy_and_companies_from_the_terminal(cli):
    criar = cli("--json", "delegacao", "criar", "ana", "--horas", "8", "--teto", "1000000", "--competencia",
                "2026-09", como="diego")
    d = json.loads(criar.stdout)
    assert (d["id"], d["de"], d["para"], d["teto"], d["escopo"]) == ("DLG-001", "diego", "ana", 1000000,
                                                                     {"competencia": "2026-09"})
    assert cli("delegacao", "criar", "bruno", "--horas", "8", "--teto", "1", "--competencia", "2026-09",
               como="diego").returncode == 3  # bruno não é aprovador
    assert cli("delegacao", "criar", "ana", "--horas", "8", "--teto", "1", como="operador").returncode == 3
    assert "DLG-001" in cli("delegacao", "listar", como="ana").stdout
    assert cli("delegacao", "revogar", "DLG-001", como="ana").returncode == 3  # só quem delegou (ou a administração)
    assert cli("delegacao", "revogar", "DLG-001", como="diego").returncode == 0
    assert "revogada" in cli("delegacao", "listar", como="diego").stdout
    assert cli("politica", "definir", "--escalonamento", "50", como="admin").returncode == 0
    assert "50% do prazo" in cli("politica", "ver").stdout
    assert cli("politica", "definir", "--escalonamento", "5", como="admin").returncode == 3
    # empresas: a partir da primeira, toda permissão que não é do cadastro exige a empresa ativa (IAM-09)
    assert cli("empresa", "criar", "sma", "--nome", "SMA", "--porte", "media", como="admin").returncode == 0
    assert cli("empresa", "criar", "beta", "--nome", "Beta Ltda", "--porte", "pequena", como="admin").returncode == 0
    assert cli("empresa", "escopo", "diego", "beta", como="admin").returncode == 0
    assert cli("empresa", "escopo", "ana", "sma", como="admin").returncode == 0
    assert "Beta Ltda" in cli("empresa", "listar").stdout
    outra = cli("--empresa", "sma", "delegacao", "criar", "ana", "--horas", "1", "--teto", "1", "--competencia",
                "2026-09", como="diego")
    assert outra.returncode == 3 and "IAM-09" in outra.stderr  # diego não tem a empresa sma
    cruzada = cli("delegacao", "criar", "ana", "--horas", "1", "--teto", "1", "--competencia", "2026-09", como="diego")
    assert cruzada.returncode == 3 and "IAM-09" in cruzada.stderr  # ana é de outra empresa


def _memoria(tmp, nome):
    return tmp / nome / "memoria.json"


def test_memory_copied_to_another_folder_is_adopted_under_permission(cli):
    a, b = _memoria(cli.tmp, "a"), _memoria(cli.tmp, "b")
    rodar = cli("run", "--scenario", "veto_waiver", "--memoria", str(a), prefixo=())
    assert rodar.returncode == 0 and a.exists()
    b.parent.mkdir()
    shutil.copy(a, b)
    verificar = [sys.executable, "-c", (
        "import sys; from fin_mas.services.audit import AuditLog; from fin_mas.services.memoria import Memoria;"
        "m = Memoria(AuditLog(), lambda: 0, caminho=sys.argv[1]); print(m.integra, len(m.entradas), m.comprometida)"),
        str(b)]
    antes = subprocess.run(verificar, capture_output=True, text=True, cwd=RAIZ, env=cli.env).stdout
    assert antes.startswith("False 0") and "memoria adotar" in antes
    negado = cli("adotar", str(b), como="operador", prefixo=("memoria", "--acesso", str(cli.pasta)))
    assert negado.returncode == 3 and "PERM-MEM-ADOTAR" in negado.stderr
    adulterada = cli.tmp / "c" / "memoria.json"
    adulterada.parent.mkdir()
    adulterada.write_text(a.read_text(encoding="utf-8").replace("MEM-0001", "MEM-0009"), encoding="utf-8")
    recusada = cli("adotar", str(adulterada), como="admin", prefixo=("memoria", "--acesso", str(cli.pasta)))
    assert recusada.returncode == 3 and "nenhuma chave" in recusada.stderr
    adotar = cli("adotar", str(b), como="admin", prefixo=("memoria", "--acesso", str(cli.pasta)))
    assert adotar.returncode == 0 and "outra pasta" in adotar.stdout
    depois = subprocess.run(verificar, capture_output=True, text=True, cwd=RAIZ, env=cli.env).stdout
    assert depois.startswith("True 1")
    original = subprocess.run(verificar[:-1] + [str(a)], capture_output=True, text=True, cwd=RAIZ, env=cli.env).stdout
    assert original.startswith("True 1")  # a origem segue íntegra
    trilha = (cli.pasta / "trilha.jsonl").read_text(encoding="utf-8")
    assert '"memoria_adotada"' in trilha


def test_two_runs_writing_the_same_memory_at_once_keep_both_entries(cli):
    arquivo = _memoria(cli.tmp, "comum")
    roteiro = ("import sys; from fin_mas.env.scenarios import Scenario, run_scenario;"
               "c = sys.argv[1]; run_scenario(Scenario('m' + c, 'w', 'fechar_mes', decisao_aprovador='waiver',"
               "agenda=((c, ('alcada',)),), pedidos=(('fechar_mes', c, 1),)), memoria=sys.argv[2])")

    def rodar(competencia):
        return subprocess.run([sys.executable, "-c", roteiro, competencia, str(arquivo)], capture_output=True,
                              text=True, cwd=RAIZ, env=cli.env)
    with ThreadPoolExecutor(4) as ex:
        resultados = list(ex.map(rodar, ["2026-05", "2026-06", "2026-07", "2026-08"]))
    assert all(r.returncode == 0 for r in resultados), [r.stderr[-400:] for r in resultados]
    salvo = json.loads(arquivo.read_text(encoding="utf-8"))
    assert sorted(e["competencia"] for e in salvo["entradas"]) == ["2026-05", "2026-06", "2026-07", "2026-08"]
    assert len({e["id"] for e in salvo["entradas"]}) == 4
    verificar = subprocess.run([sys.executable, "-c", (
        "import sys; from fin_mas.services.audit import AuditLog; from fin_mas.services.memoria import Memoria;"
        "print(Memoria(AuditLog(), lambda: 0, caminho=sys.argv[1]).integra)"), str(arquivo)],
        capture_output=True, text=True, cwd=RAIZ, env=cli.env)
    assert verificar.stdout.strip() == "True"

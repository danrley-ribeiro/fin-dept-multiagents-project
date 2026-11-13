"""Implantação pelo terminal: `instalar`, `doctor` e `serve --instalacao`, de ponta a ponta numa pasta limpa."""
import http.client
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]
SENHA = "Administrador-2026-forte"


@pytest.fixture
def cli(tmp_path):
    base = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1", "FIN_MAS_DIR_CHAVES": str(tmp_path / "chaves")}
    base.pop("FIN_MAS_SENHA_NOVA", None)

    def rodar(*args, **env):
        return subprocess.run([sys.executable, "-m", "fin_mas", *args], capture_output=True, text=True, cwd=RAIZ,
                              env={**base, **env}, stdin=subprocess.DEVNULL)
    rodar.env = base
    return rodar


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_install_creates_a_ready_data_folder_and_doctor_approves_it(cli, tmp_path):
    pasta = tmp_path / "dados"
    sem_senha = cli("instalar", "--pasta", str(pasta), "--porte", "micro", "--cognicao", "local")
    assert sem_senha.returncode == 2 and "FIN_MAS_SENHA_NOVA" in sem_senha.stderr  # sem terminal e sem senha: não inventa
    r = cli("instalar", "--pasta", str(pasta), "--porte", "micro", "--cognicao", "local", "--usuario", "raiz",
            "--porta", "8799", FIN_MAS_SENHA_NOVA=SENHA)
    assert r.returncode == 0, r.stderr
    assert "administrador raiz criado" in r.stdout and "sem ERP: use a planilha modelo" in r.stdout
    assert f"serve --instalacao {pasta}" in r.stdout
    config = json.loads((pasta / "instalacao.json").read_text(encoding="utf-8"))
    assert (config["porte"], config["cognicao"], config["porta"], config["tem_erp"]) == ("micro", "local", 8799, False)
    assert (pasta / "modelos" / "exemplo_micro.xlsx").stat().st_size > 5000
    assert (pasta / "modelos" / "modelo_controladoria_em_branco.xlsx").exists() and (pasta / "empresa").is_dir()
    assert SENHA not in "".join(p.read_text(encoding="utf-8") for p in (pasta / "acesso").glob("*.json"))
    de_novo = cli("instalar", "--pasta", str(pasta), "--porte", "micro", "--cognicao", "local")  # não refaz o cadastro
    assert de_novo.returncode == 0 and "já existe (1 conta(s))" in de_novo.stdout
    doc = cli("doctor", "--pasta", str(pasta))
    assert doc.returncode == 0, doc.stdout
    assert "administrador(es) ativo(s): raiz" in doc.stdout and "trilha de acesso" in doc.stdout
    itens = {i["item"]: i for i in json.loads(cli("doctor", "--pasta", str(pasta), "--json").stdout)}
    assert itens["Python"]["situacao"] == "ok" and itens["instalação"]["detalhe"].startswith("porte micro")
    assert itens["pasta de chaves"]["situacao"] == "ok" and itens["modelos YAML"]["situacao"] == "ok"


def test_doctor_flags_a_tampered_installation(cli, tmp_path):
    pasta = tmp_path / "dados"
    assert cli("instalar", "--pasta", str(pasta), "--porte", "media", "--cognicao", "basico", "--demo").returncode == 0
    contas = pasta / "acesso" / "contas.json"
    bruto = json.loads(contas.read_text(encoding="utf-8"))
    bruto["dados"]["contas"]["operador"]["papeis"] = ["ROLE-ADM"]
    contas.write_text(json.dumps(bruto), encoding="utf-8")
    doc = cli("doctor", "--pasta", str(pasta))
    assert doc.returncode == 1 and "[ERRO ] cadastro de acesso" in doc.stdout and "IAM-07" in doc.stdout
    vazia = cli("doctor", "--pasta", str(tmp_path / "nada"))
    assert vazia.returncode == 0 and "[AVISO] instalação" in vazia.stdout


def test_server_starts_from_the_installed_folder_with_the_chosen_size(cli, tmp_path):
    pasta, porta = tmp_path / "dados", _porta_livre()
    r = cli("instalar", "--pasta", str(pasta), "--porte", "micro", "--cognicao", "local", "--usuario", "raiz",
            "--porta", str(porta), FIN_MAS_SENHA_NOVA=SENHA)
    assert r.returncode == 0, r.stderr
    servidor = subprocess.Popen([sys.executable, "-m", "fin_mas", "serve", "--instalacao", str(pasta), "--ms-por-tick", "0"],
                                cwd=RAIZ, env=cli.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(100):
            try:
                con = http.client.HTTPConnection("127.0.0.1", porta, timeout=2)
                con.request("GET", "/api/saude")
                saude = json.loads(con.getresponse().read())
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("o servidor não subiu: " + (servidor.stdout.read() if servidor.poll() is not None else ""))
        assert saude["acesso"] == {"sem_contas": False, "integro": True, "cabecalho": "X-SMA-Token"}
        con = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        con.request("POST", "/api/login", body=json.dumps({"usuario": "raiz", "senha": SENHA}),
                    headers={"Content-Type": "application/json"})
        resposta = con.getresponse()
        cookie = resposta.getheader("Set-Cookie").split(";")[0]
        assert resposta.status == 200 and json.loads(resposta.read())["sessao"]["papeis"] == ["ROLE-ADM"]
        con = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        con.request("GET", "/api/estado", headers={"Cookie": cookie})
        controle = json.loads(con.getresponse().read())["controle"]
        assert (controle["porte"], controle["cognicao"], controle["cenario"]) == ("micro", "local", "fechamento_micro")
    finally:
        servidor.terminate()
        servidor.wait(timeout=10)


def test_server_refuses_to_start_without_accounts(cli, tmp_path):
    r = cli("serve", "--acesso", str(tmp_path / "vazio"), "--porta", str(_porta_livre()))
    assert r.returncode != 0 and "nenhuma conta" in r.stderr and "acesso iniciar" in r.stderr

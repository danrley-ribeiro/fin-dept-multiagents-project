"""Implantação da DSM4 por processos reais: servidor com `--host`, API de portes e segmentos e o wheel
instalado num ambiente virtual limpo, executado FORA do repositório."""
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import venv
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


def _porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _pedir(porta, metodo, rota, corpo=None, cabecalhos=None):
    con = http.client.HTTPConnection("127.0.0.1", porta, timeout=10)
    con.request(metodo, rota, body=json.dumps(corpo) if corpo is not None else None,
                headers={"Content-Type": "application/json", **(cabecalhos or {})})
    r = con.getresponse()
    return r.status, r.getheader("Set-Cookie"), r.read()


@pytest.fixture
def servidor(tmp_path):
    from fin_mas.services.iam import SENHA_DEMO as senha
    porta = _porta_livre()
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1", "FIN_MAS_DIR_CHAVES": str(tmp_path / "ch")}
    proc = subprocess.Popen([sys.executable, "-m", "fin_mas", "serve", "--demo", "--host", "0.0.0.0", "--porta", str(porta),
                             "--acesso", str(tmp_path / "acesso"), "--pasta-dados", str(tmp_path / "empresa"),
                             "--ms-por-tick", "0", "--segmento", "comercio"],
                            cwd=RAIZ, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(150):
            try:
                if _pedir(porta, "GET", "/api/saude")[0] == 200:
                    break
            except OSError:
                time.sleep(0.1)
        else:
            raise AssertionError("o servidor não subiu: " + (proc.stdout.read() if proc.poll() is not None else ""))
        yield porta, senha
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_server_on_all_interfaces_still_accepts_only_loopback_names(servidor):
    porta, senha = servidor
    assert _pedir(porta, "GET", "/api/saude")[0] == 200  # Host: 127.0.0.1:<porta>
    assert _pedir(porta, "GET", "/api/saude", cabecalhos={"Host": f"localhost:{porta}"})[0] == 200
    # escutar em 0.0.0.0 (contêiner) não abre o serviço a outros nomes nem a páginas de outros sites
    assert _pedir(porta, "GET", "/api/saude", cabecalhos={"Host": "sma.exemplo.com"})[0] == 403
    assert _pedir(porta, "GET", "/api/saude", cabecalhos={"Host": "0.0.0.0"})[0] == 403
    assert _pedir(porta, "POST", "/api/login", {"usuario": "avaliador", "senha": senha},
                  {"Origin": "http://atacante.exemplo"})[0] == 403


def test_dashboard_api_lists_sizes_segments_templates_and_restarts_with_a_segment(servidor):
    porta, senha = servidor
    status, cookie, corpo = _pedir(porta, "POST", "/api/login", {"usuario": "avaliador", "senha": senha})
    assert status == 200
    cookie, csrf = cookie.split(";")[0], json.loads(corpo)["csrf"]
    status, _, corpo = _pedir(porta, "GET", "/api/portes", cabecalhos={"Cookie": cookie})
    portes = json.loads(corpo)
    assert status == 200 and list(portes["portes"]) == ["mei", "micro", "pequena", "media", "media_ii", "grande"]
    assert portes["segmento_atual"] == "comercio" and set(portes["segmentos"]) == {
        "software_servicos", "comercio", "servicos", "industria"}
    assert portes["segmentos"]["industria"]["rateio"]["percentuais"] == {"UN-L1": 70, "UN-L2": 30}
    assert portes["portes"]["media_ii"]["receita_bruta_anual_min"] == 9000000000
    modelos = json.loads(_pedir(porta, "GET", "/api/modelos", cabecalhos={"Cookie": cookie})[2])["modelos"]
    arquivos = {m["arquivo"] for m in modelos}
    assert {"exemplo_mei.xlsx", "exemplo_media_ii.xlsx", "exemplo_industria.xlsx"} <= arquivos
    status, _, xlsx = _pedir(porta, "GET", "/api/modelos/exemplo_industria.xlsx", cabecalhos={"Cookie": cookie})
    assert status == 200 and xlsx[:2] == b"PK"
    status, _, _ = _pedir(porta, "POST", "/api/comando", {"tipo": "reiniciar", "cenario": "fechamento_pequena",
                                                          "porte": "media_ii", "segmento": "industria"},
                          {"Cookie": cookie, "X-SMA-Token": csrf})
    assert status == 202
    for _ in range(50):
        controle = json.loads(_pedir(porta, "GET", "/api/estado", cabecalhos={"Cookie": cookie})[2])["controle"]
        if controle["segmento"] == "industria":
            break
        time.sleep(0.1)
    assert (controle["porte"], controle["segmento"]) == ("media_ii", "industria")
    status, _, corpo = _pedir(porta, "POST", "/api/comando", {"tipo": "reiniciar", "segmento": "agro"},
                              {"Cookie": cookie, "X-SMA-Token": csrf})
    assert status == 400 and "segmento desconhecido" in corpo.decode("utf-8")


def _deps_do_ambiente_atual(destino: Path) -> Path:
    """Sem rede: só as dependências de runtime (pyyaml, openpyxl e et_xmlfile) do ambiente que roda os testes."""
    import et_xmlfile
    import openpyxl
    import yaml
    destino.mkdir()
    for modulo in (yaml, openpyxl, et_xmlfile):
        origem = Path(modulo.__file__).parent
        os.symlink(origem, destino / origem.name)
    extensao = next(Path(yaml.__file__).parent.parent.glob("_yaml*"), None)
    if extensao is not None:
        os.symlink(extensao, destino / extensao.name)
    return destino


def test_wheel_installs_in_a_clean_venv_and_runs_outside_the_repository(tmp_path):
    dist = tmp_path / "dist"
    opcoes = [] if (RAIZ / "web" / "dist" / "index.html").exists() else ["--sem-dashboard"]
    gerar = subprocess.run([sys.executable, str(RAIZ / "tools" / "empacotar_wheel.py"), "--saida", str(dist), *opcoes],
                           capture_output=True, text=True, cwd=RAIZ)
    if gerar.returncode != 0 and ("Could not find" in gerar.stderr or "NewConnectionError" in gerar.stderr):
        pytest.skip("sem rede para o setuptools do isolamento de build do pip: " + gerar.stderr[-200:])
    assert gerar.returncode == 0, gerar.stderr
    wheel = next(dist.glob("fin_mas-1.0.0-*.whl"))
    ambiente = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(ambiente)
    py = ambiente / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    exe = ambiente / ("Scripts/fin-mas.exe" if os.name == "nt" else "bin/fin-mas")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "VIRTUAL_ENV", "FIN_MAS_SENHA_NOVA")}
    env.update(PYTHONUTF8="1", FIN_MAS_DIR_CHAVES=str(tmp_path / "chaves"), PIP_DISABLE_PIP_VERSION_CHECK="1")
    com_deps = subprocess.run([str(py), "-m", "pip", "install", "--quiet", str(wheel)], capture_output=True, text=True,
                              env=env, timeout=300)
    if com_deps.returncode != 0:  # sem rede: o wheel sem dependências e as do ambiente atual por PYTHONPATH
        r = subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--no-deps", "--no-index", str(wheel)],
                           capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
        env["PYTHONPATH"] = str(_deps_do_ambiente_atual(tmp_path / "deps"))
    fora = tmp_path / "fora-do-repositorio"
    fora.mkdir()

    def rodar(*args):
        return subprocess.run([str(exe), *args], capture_output=True, text=True, cwd=fora, env=env,
                              stdin=subprocess.DEVNULL, timeout=300)

    onde = subprocess.run([str(py), "-c", "import fin_mas, fin_mas.recursos as r; print(fin_mas.__file__); "
                                         "print(r.origem()); print(r.models_dir())"],
                          capture_output=True, text=True, cwd=fora, env=env)
    arquivo, origem, modelos = onde.stdout.split()
    assert str(ambiente) in arquivo and RAIZ.as_posix() not in Path(arquivo).as_posix(), onde.stdout
    assert origem == "pacote" and str(ambiente) in modelos
    lista = rodar("list")
    assert lista.returncode == 0 and "fechamento_mei" in lista.stdout and "fechamento_industria" in lista.stdout
    execucao = rodar("run", "--scenario", "fechar_mes")
    assert execucao.returncode == 0 and "hash do trace:" in execucao.stdout, execucao.stderr
    # o mesmo trace do checkout: o pacote instalado é o mesmo sistema
    referencia = subprocess.run([sys.executable, "-m", "fin_mas", "run", "--scenario", "fechar_mes"], capture_output=True,
                                text=True, cwd=RAIZ, env={**os.environ, "PYTHONPATH": str(RAIZ / "src")})
    assert execucao.stdout.splitlines()[-1] == referencia.stdout.splitlines()[-1]
    instalar = rodar("instalar", "--pasta", "dados", "--porte", "mei", "--segmento", "servicos", "--demo")
    assert instalar.returncode == 0 and (fora / "dados" / "modelos" / "exemplo_mei.xlsx").exists(), instalar.stderr
    doctor = rodar("doctor", "--pasta", "dados", "--json")
    itens = {i["item"]: i for i in json.loads(doctor.stdout)}
    assert doctor.returncode == 0, doctor.stdout
    assert itens["modelos YAML"]["situacao"] == "ok" and "(pacote)" in itens["modelos YAML"]["detalhe"]
    if not opcoes:
        assert itens["dashboard construído"]["situacao"] == "ok" and str(ambiente) in itens["dashboard construído"]["detalhe"]
    shutil.rmtree(ambiente, ignore_errors=True)


def test_container_files_publish_only_on_loopback_and_keep_keys_apart():
    """O compose e o Dockerfile reais: porta só em 127.0.0.1, volumes separados, usuário sem privilégio."""
    import yaml
    compose = yaml.safe_load((RAIZ / "compose.yaml").read_text(encoding="utf-8"))
    sma = compose["services"]["sma"]
    assert sma["ports"] == ["127.0.0.1:8765:8765"]
    assert {v.split(":")[1] for v in sma["volumes"]} == {"/dados", "/chaves"} and set(compose["volumes"]) == {"dados", "chaves"}
    assert sma["environment"]["FIN_MAS_DIR_CHAVES"] == "/chaves" and sma["env_file"][0] == {"path": ".env", "required": False}
    assert sma["read_only"] is True and sma["cap_drop"] == ["ALL"] and "/api/saude" in " ".join(sma["healthcheck"]["test"])
    dockerfile = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    assert "USER sma" in dockerfile and "HEALTHCHECK" in dockerfile and "/api/saude" in dockerfile
    assert dockerfile.count("\nFROM ") == 3  # dashboard, wheel e runtime
    entrada = (RAIZ / "docker" / "entrada.sh").read_text(encoding="utf-8")
    assert "--host 0.0.0.0" in entrada and "--instalacao" in entrada
    exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for variavel in ("FIN_MAS_SENHA_NOVA=", "FIN_MAS_DEMO=", "FIN_MAS_SEGMENTO=", "FIN_MAS_LLM_URLS_CONFIAVEIS="):
        assert variavel in exemplo

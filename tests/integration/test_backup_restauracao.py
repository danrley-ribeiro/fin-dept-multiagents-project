"""Backup, restauração e migração da pasta de dados pela CLI, por subprocesso (DSM4).

Cada teste usa uma pasta de dados e uma pasta de chaves temporárias; "outra máquina" é outra pasta
de chaves (`FIN_MAS_DIR_CHAVES`) que nunca viu a instalação original.
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli(tmp_path):
    base = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1", "FIN_MAS_DIR_CHAVES": str(tmp_path / "chaves")}
    base.pop("FIN_MAS_SENHA_NOVA", None)
    base.pop("FIN_MAS_CHAVE_MEMORIA", None)

    def rodar(*args, chaves=None, codigo=None):
        env = {**base, **({"FIN_MAS_DIR_CHAVES": str(chaves)} if chaves else {})}
        argv = ["-c", codigo, *args] if codigo else ["-m", "fin_mas", *args]
        return subprocess.run([sys.executable, *argv], capture_output=True, text=True, cwd=RAIZ, env=env,
                              stdin=subprocess.DEVNULL)
    return rodar


@pytest.fixture
def instalada(cli, tmp_path):
    """Pasta instalada com contas, trilha e uma memória selada do SVC-MEM dentro dela."""
    pasta = tmp_path / "dados"
    r = cli("instalar", "--pasta", str(pasta), "--porte", "mei", "--segmento", "comercio", "--cognicao", "local", "--demo")
    assert r.returncode == 0, r.stderr
    r = cli("run", "--scenario", "reincidencia_waiver", "--memoria", str(pasta / "memoria" / "memoria.json"))
    assert r.returncode == 0, r.stderr
    assert (pasta / "memoria" / "memoria.json").exists() and (pasta / "acesso" / "trilha.jsonl").exists()
    return pasta


def _reescrever(origem: Path, destino: Path, trocar: dict) -> None:
    """Cópia do zip com algumas entradas trocadas (ou acrescentadas): o que um adulterador faria."""
    with zipfile.ZipFile(origem) as z, zipfile.ZipFile(destino, "w") as novo:
        for nome in z.namelist():
            novo.writestr(nome, trocar.pop(nome) if nome in trocar else z.read(nome))
        for nome, conteudo in trocar.items():
            novo.writestr(nome, conteudo)


def test_backup_restores_into_another_folder_on_another_machine(cli, instalada, tmp_path):
    zip_, chaves_zip = tmp_path / "b.zip", tmp_path / "b.chaves.zip"
    r = cli("backup", "--pasta", str(instalada), "--para", str(zip_), "--chaves-para", str(chaves_zip))
    assert r.returncode == 0, r.stderr
    assert "com chave de integridade" in r.stdout and oct(chaves_zip.stat().st_mode)[-3:] == "600"
    with zipfile.ZipFile(zip_) as z:
        nomes = set(z.namelist())
        assert "manifesto.json" in nomes and "dados/acesso/contas.json" in nomes and "dados/instalacao.json" in nomes
        assert not any(n.endswith((".chave", ".contador", ".cabeca")) for n in nomes)  # chaves nunca no zip de dados
    outra = tmp_path / "outra-maquina"
    destino = tmp_path / "restaurada"
    sem_chaves = cli("restaurar", str(zip_), "--pasta", str(destino), chaves=outra)
    assert sem_chaves.returncode == 3 and "não está nesta máquina" in sem_chaves.stderr and not destino.exists()
    r = cli("restaurar", str(zip_), "--pasta", str(destino), "--chaves", str(chaves_zip), chaves=outra)
    assert r.returncode == 0, r.stderr
    for conferido in ("acesso/contas.json (selo", "acesso/sessoes.json (selo", "acesso/trilha.jsonl (cadeia",
                      "memoria/memoria.json (selo e assinaturas"):
        assert conferido in r.stdout
    doc = cli("doctor", "--pasta", str(destino), "--json", chaves=outra)
    itens = {i["item"]: i for i in json.loads(doc.stdout)}
    assert itens["cadastro de acesso"]["situacao"] == "ok" and itens["trilha de acesso"]["situacao"] == "ok"
    assert "segmento comercio" in itens["instalação"]["detalhe"]
    # a memória restaurada é lida íntegra pelo SVC-MEM, no caminho novo e com a pasta de chaves nova
    ler = ("import sys; from fin_mas.services.memoria import Memoria; from fin_mas.services.audit import AuditLog; "
           "m = Memoria(AuditLog(), lambda: 0, caminho=sys.argv[1]); print(m.integra, len(m.entradas))")
    saida = cli(str(destino / "memoria" / "memoria.json"), chaves=outra, codigo=ler)
    assert saida.stdout.split()[0] == "True" and int(saida.stdout.split()[1]) >= 1, saida.stderr
    # a mesma máquina restaura sem o arquivo de chaves (a chave do backup e as da origem estão lá)
    assert cli("restaurar", str(zip_), "--pasta", str(tmp_path / "local")).returncode == 0


def test_tampered_or_mismatched_backup_is_refused(cli, instalada, tmp_path):
    zip_, chaves_zip = tmp_path / "b.zip", tmp_path / "b.chaves.zip"
    assert cli("backup", "--pasta", str(instalada), "--para", str(zip_), "--chaves-para", str(chaves_zip)).returncode == 0
    with zipfile.ZipFile(zip_) as z:
        corpo = json.loads(z.read("manifesto.json"))
        contas = json.loads(z.read("dados/acesso/contas.json"))
    contas["dados"]["contas"]["operador"]["papeis"] = ["ROLE-ADM"]  # escalada de privilégio no cadastro
    forjado = json.dumps(contas).encode("utf-8")

    def tentar(nome, trocar):
        alterado = tmp_path / f"{nome}.zip"
        _reescrever(zip_, alterado, trocar)
        destino = tmp_path / f"destino-{nome}"
        r = cli("restaurar", str(alterado), "--pasta", str(destino), "--chaves", str(chaves_zip))
        assert r.returncode == 3 and "BACKUP RECUSADO" in r.stderr, (nome, r.stdout, r.stderr)
        assert not destino.exists(), f"{nome}: nada pode ser gravado quando o backup é recusado"
        return r.stderr

    # 1) arquivo trocado, manifesto intacto: o hash não confere
    assert "não confere com o hash do manifesto" in tentar("arquivo", {"dados/acesso/contas.json": forjado})
    # 2) arquivo trocado e hash corrigido no manifesto: o selo do manifesto não confere
    manifesto = json.loads(json.dumps(corpo["manifesto"]))
    item = next(i for i in manifesto["arquivos"] if i["caminho"] == "acesso/contas.json")
    item.update(sha256=hashlib.sha256(forjado).hexdigest(), tamanho=len(forjado))
    novo = json.dumps({"manifesto": manifesto, "selo": corpo["selo"]}).encode("utf-8")
    assert "selo do manifesto não confere" in tentar("manifesto", {"manifesto.json": novo,
                                                                   "dados/acesso/contas.json": forjado})
    # 3) mesmo com o manifesto re-selado com a chave do backup, o selo do próprio cadastro denuncia a troca
    with zipfile.ZipFile(chaves_zip) as z:
        chave_backup = base64.b64decode(json.loads(z.read("manifesto-chaves.json"))["backup"])
    selo = hmac.new(chave_backup, json.dumps(manifesto, sort_keys=True, ensure_ascii=False).encode("utf-8"),
                    hashlib.sha256).hexdigest()
    resselado = json.dumps({"manifesto": manifesto, "selo": selo}).encode("utf-8")
    assert "selo não confere" in tentar("resselado", {"manifesto.json": resselado, "dados/acesso/contas.json": forjado})
    # 4) entrada fora do formato (fuga de diretório) e arquivo a mais
    assert "fora do formato" in tentar("fuga", {"dados/../../fora.txt": b"x"})
    assert "diferente do manifesto" in tentar("sobra", {"dados/extra.txt": b"x"})
    # 5) chaves de outra instalação não servem
    outra = tmp_path / "outra"
    assert cli("instalar", "--pasta", str(outra), "--porte", "micro", "--cognicao", "basico", "--demo").returncode == 0
    assert cli("backup", "--pasta", str(outra), "--para", str(tmp_path / "o.zip"),
               "--chaves-para", str(tmp_path / "o.chaves.zip")).returncode == 0
    r = cli("restaurar", str(zip_), "--pasta", str(tmp_path / "x"), "--chaves", str(tmp_path / "o.chaves.zip"))
    assert r.returncode == 3 and "outra pasta" in r.stderr
    # 6) restaurar no lugar de uma instalação que já existiu nesta máquina seria rollback: recusado
    nao_vazia = cli("restaurar", str(zip_), "--pasta", str(instalada))
    assert nao_vazia.returncode == 3 and "não está vazia" in nao_vazia.stderr
    for arquivo in sorted(instalada.rglob("*"), reverse=True):
        arquivo.unlink() if arquivo.is_file() else arquivo.rmdir()
    rollback = cli("restaurar", str(zip_), "--pasta", str(instalada))
    assert rollback.returncode == 3 and "rollback" in rollback.stderr


MIGRACAO_EXEMPLO = """
import json, sys
from fin_mas import manutencao
from fin_mas.cli import main
from fin_mas.services.selado import ArquivoSelado

def v1_para_v2(dados):  # exemplo só dos testes: cada conta ganha o campo `idioma`
    for conta in dados["contas"].values():
        conta["idioma"] = "pt-BR"
    return dados

manutencao.MIGRACOES[("acesso-contas", 1)] = v1_para_v2
manutencao.VERSOES_ATUAIS["acesso-contas"] = 2
codigo = main(["migrar", "--pasta", sys.argv[1]] + sys.argv[2:])
dados = ArquivoSelado(sys.argv[1] + "/acesso/contas.json", "acesso-contas", 2, {}).ler()
print("RESULTADO", codigo, sorted({c["idioma"] for c in dados["contas"].values()}))
"""


def test_migration_mechanism_with_an_example_from_version_1_to_2(cli, instalada, tmp_path):
    atual = cli("migrar", "--pasta", str(instalada))
    assert atual.returncode == 0 and "acesso/contas.json" in atual.stdout and "na versão atual" in atual.stdout
    contas = instalada / "acesso" / "contas.json"
    antes = json.loads(contas.read_text(encoding="utf-8"))
    simulado = cli(str(instalada), "--simular", codigo=MIGRACAO_EXEMPLO.replace(
        'dados = ArquivoSelado', 'raise SystemExit(codigo)\ndados = ArquivoSelado'))
    assert "migraria v1 -> v2" in simulado.stdout and json.loads(contas.read_text(encoding="utf-8")) == antes
    r = cli(str(instalada), codigo=MIGRACAO_EXEMPLO)
    assert "migrado v1 -> v2" in r.stdout and "RESULTADO 0 ['pt-BR']" in r.stdout, r.stderr
    depois = json.loads(contas.read_text(encoding="utf-8"))
    assert depois["versao"] == 2 and depois["contador"] > antes["contador"]
    # este sistema (versão 1 do cadastro) recusa o arquivo migrado: falha fechada, ninguém entra
    doc = cli("doctor", "--pasta", str(instalada))
    assert doc.returncode == 1 and "IAM-07" in doc.stdout and "versão 2 do formato" in doc.stdout
    # arquivo de versão mais nova que o sistema não é "migrado para trás"
    para_tras = cli("migrar", "--pasta", str(instalada))
    assert para_tras.returncode == 1 and "mais nova que a deste sistema" in para_tras.stdout

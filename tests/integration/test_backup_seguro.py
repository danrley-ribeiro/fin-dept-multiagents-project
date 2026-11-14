"""Restauração segura e completa (correção simulada da DSM4: C5, M3 e m5), pela CLI, por subprocesso.

- C5: um par backup + chaves forjado por terceiro (com a chave dele, então o selo confere) não grava nada fora da
  pasta de destino, nem com `dados//<caminho absoluto>`, nem com nome de estado com `../`, e nada é gravado antes
  de o backup inteiro ser conferido;
- m5: manifesto torto vira "BACKUP RECUSADO" (código 3), sem traceback; entrada maior que o tamanho declarado é
  recusada na leitura em fluxo; o backup não segue link simbólico para fora da pasta;
- M3: o cofre (segredo do segundo fator, chave de LLM, credencial de conector) viaja no pacote de chaves e volta na
  restauração; sem ele o backup é recusado, e o `doctor` avisa da conta com segundo fator sem segredo no cofre.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import zipfile

import pytest

from test_backup_restauracao import cli, instalada  # noqa: F401 (fixtures)

pytestmark = pytest.mark.integracao


def _forjar(tmp_path, nome, entradas: dict, itens: list, estados=None, origem="/atacante/dados", cofres=None,
            manifesto_extra=None):
    """Par backup + chaves feito por um terceiro com a chave dele: o selo do manifesto confere."""
    k = b"K" * 32
    manifesto = {"formato": "fin-mas-backup", "versao_formato": 1, "versao_sistema": "0.5.0",
                 "criado_em": "2026-01-01T00:00:00+00:00", "origem": origem, "arquivos": itens, **(manifesto_extra or {})}
    selo = hmac.new(k, json.dumps(manifesto, sort_keys=True, ensure_ascii=False).encode(), hashlib.sha256).hexdigest()
    a, b = tmp_path / f"{nome}.zip", tmp_path / f"{nome}.chaves.zip"
    with zipfile.ZipFile(a, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifesto.json", json.dumps({"manifesto": manifesto, "selo": selo}))
        for entrada, conteudo in entradas.items():
            z.writestr(entrada, conteudo)
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("manifesto-chaves.json", json.dumps({
            "formato": "fin-mas-backup-chaves", "versao_formato": 1, "origem": origem,
            "backup": base64.b64encode(k).decode(), "cofres": cofres or {},
            "estados": {r: {n: base64.b64encode(v).decode() for n, v in e.items()} for r, e in (estados or {}).items()}}))
    return a, b


def _item(caminho, conteudo, estado=()):
    return {"caminho": caminho, "sha256": hashlib.sha256(conteudo).hexdigest(), "tamanho": len(conteudo),
            "estado": sorted(estado)}


def test_forged_backup_never_writes_outside_the_destination_and_malformed_ones_are_refused(cli, tmp_path):  # noqa: F811
    chaves = tmp_path / "chaves-vitima"
    fora = tmp_path / "ALVO-FORA" / "gravado.txt"
    fora.parent.mkdir()
    selado_sem_chave = json.dumps({"versao": 1, "contador": 1, "dados": {}, "selo": "00"}).encode()

    def recusado(a, b, nome):
        destino = tmp_path / f"destino-{nome}"
        r = cli("restaurar", str(a), "--pasta", str(destino), "--chaves", str(b), chaves=chaves)
        assert r.returncode == 3 and "BACKUP RECUSADO" in r.stderr and "Traceback" not in r.stderr, (nome, r.stderr)
        assert not destino.exists(), f"{nome}: nada pode ser gravado quando o backup é recusado"
        return r.stderr

    conteudo = b"ESCRITO FORA DA PASTA DE DESTINO\n"
    # 1) entrada `dados//<absoluto>` (com um selado sem chave para a recusa vir depois): nada fora do destino
    a, b = _forjar(tmp_path, "abs", {"dados/" + str(fora): conteudo, "dados/acesso/contas.json": selado_sem_chave},
                   [_item(str(fora), conteudo), _item("acesso/contas.json", selado_sem_chave)])
    assert "fora do formato" in recusado(a, b, "abs")
    for entrada in ("dados/./x.txt", "dados/a//b.txt", "dados/a\\..\\b.txt", "dados/C:/x.txt"):
        a, b = _forjar(tmp_path, "var", {entrada: b"x"}, [_item(entrada[len("dados/"):], b"x")])
        assert "fora do formato" in recusado(a, b, "var")
    assert not fora.exists()
    # 2) nome de estado com caminho no pacote de chaves: nada plantado fora da pasta de chaves
    plantar = tmp_path / "ALVO-ESTADO"
    plantar.mkdir()
    for nome_estado in ("../ALVO-ESTADO/plantado.chave", f"{plantar}/plantado.sh"):
        a, b = _forjar(tmp_path, "estado", {"dados/ok.json": b"{}"}, [_item("ok.json", b"{}", [nome_estado])],
                       estados={"ok.json": {nome_estado: b"#!/bin/sh\necho atacante\n"}})
        recusado(a, b, "estado")
    assert list(plantar.iterdir()) == []
    # 3) entrada maior que o declarado (zip-bomba com selo válido): recusada na leitura em fluxo
    bomba = tmp_path / "bomba.zip"
    a, b = _forjar(tmp_path, "bomba", {}, [_item("x.bin", b"\0" * 10)])
    with zipfile.ZipFile(a, "a", zipfile.ZIP_DEFLATED) as z, z.open("dados/x.bin", "w", force_zip64=True) as f:
        for _ in range(64):
            f.write(b"\0" * (1 << 20))
    a.rename(bomba)
    t0 = time.monotonic()
    assert "maior que o tamanho declarado" in recusado(bomba, b, "bomba") and time.monotonic() - t0 < 30
    # e o manifesto que declara mais do que o limite nem chega a descompactar
    a, b = _forjar(tmp_path, "grande", {"dados/x.bin": b"x"},
                   [{**_item("x.bin", b"x"), "tamanho": 5 << 30}])
    assert "limite" in recusado(a, b, "grande")
    # 4) manifestos tortos: BACKUP RECUSADO, nunca traceback
    for nome, corpo in (("lista", {"manifesto": [1, 2], "selo": "x"}),
                        ("sem-origem", {"manifesto": {"formato": "fin-mas-backup", "versao_formato": 1, "arquivos": []},
                                        "selo": "a" * 64}),
                        ("arquivos-int", {"manifesto": {"formato": "fin-mas-backup", "versao_formato": 1, "origem": "/x",
                                                        "criado_em": "", "versao_sistema": "", "arquivos": 5},
                                          "selo": "a" * 64}),
                        ("item-vazio", {"manifesto": {"formato": "fin-mas-backup", "versao_formato": 1, "origem": "/x",
                                                      "criado_em": "", "versao_sistema": "", "arquivos": [{}]},
                                        "selo": "a" * 64}),
                        ("selo-unicode", {"manifesto": {"formato": "fin-mas-backup", "versao_formato": 1, "origem": "/x",
                                                        "criado_em": "", "versao_sistema": "", "arquivos": []},
                                          "selo": "é"}),
                        ("aninhado", "[" * 100000 + "]" * 100000)):
        torto = tmp_path / f"torto-{nome}.zip"
        with zipfile.ZipFile(torto, "w") as z:
            z.writestr("manifesto.json", corpo if isinstance(corpo, str) else json.dumps(corpo))
        recusado(torto, b, nome)
    arquivo = tmp_path / "um-arquivo"
    arquivo.write_text("x")
    r = cli("restaurar", str(bomba), "--pasta", str(arquivo), chaves=chaves)
    assert r.returncode == 3 and "não é uma pasta" in r.stderr and "Traceback" not in r.stderr


def test_backup_carries_the_vault_and_the_restored_install_keeps_2fa_llm_key_and_connector_credential(
        cli, instalada, tmp_path):  # noqa: F811
    preparar = r'''
import sys
from pathlib import Path
from fin_mas.fontes.registro import RegistroFontes
from fin_mas.services import totp
from fin_mas.services.iam import SENHA_DEMO, Acesso
p = Path(sys.argv[1])
a = Acesso(p / "acesso")
s, _ = a.autenticar("admin", SENHA_DEMO)
a.definir_segredo(s, "llm:OPENAI_API_KEY", "sk-NO-COFRE-424242")
i = a.iniciar_2fa(s)
a.confirmar_2fa(s, totp.codigo(i["segredo"], a.relogio()))
RegistroFontes(p / "fontes").cadastrar("operador", {"id": "erp", "tipo": "rest", "credencial": "tok-ERP-313131",
                                                     "config": {"url_base": "http://127.0.0.1:8790"}})
print(i["segredo"])
'''
    r = cli(str(instalada), codigo=preparar)
    assert r.returncode == 0, r.stderr
    segredo = r.stdout.strip().splitlines()[-1]
    os.symlink(tmp_path / "fora.txt", instalada / "atalho.txt")
    (tmp_path / "fora.txt").write_text("ARQUIVO-DE-FORA")
    zip_, chaves_zip = tmp_path / "b.zip", tmp_path / "b.chaves.zip"
    r = cli("backup", "--pasta", str(instalada), "--para", str(zip_), "--chaves-para", str(chaves_zip))
    assert r.returncode == 0 and "2 cofre(s)" in r.stdout, r.stdout + r.stderr
    with zipfile.ZipFile(zip_) as z:
        nomes = z.namelist()
        tudo = b"".join(z.read(n) for n in nomes)
    assert "dados/atalho.txt" not in nomes and b"ARQUIVO-DE-FORA" not in tudo  # o link para fora não é seguido
    assert b"sk-NO-COFRE" not in tudo and b"tok-ERP" not in tudo and segredo.encode() not in tudo  # cofre só nas chaves
    outra = tmp_path / "outra-maquina"
    # sem o cofre no pacote de chaves, o backup é recusado (não se restaura uma instalação sem os segredos)
    with zipfile.ZipFile(chaves_zip) as z:
        corpo = json.loads(z.read("manifesto-chaves.json"))
    sem_cofre = tmp_path / "sem-cofre.chaves.zip"
    with zipfile.ZipFile(sem_cofre, "w") as z:
        z.writestr("manifesto-chaves.json", json.dumps({**corpo, "cofres": {}}))
    r = cli("restaurar", str(zip_), "--pasta", str(tmp_path / "x"), "--chaves", str(sem_cofre), chaves=outra)
    assert r.returncode == 3 and "cofre ausente" in r.stderr and not (tmp_path / "x").exists()
    destino = tmp_path / "restaurada"
    r = cli("restaurar", str(zip_), "--pasta", str(destino), "--chaves", str(chaves_zip), chaves=outra)
    assert r.returncode == 0 and "cofre de acesso (selo" in r.stdout and "cofre de fontes (selo" in r.stdout, r.stderr
    conferir = r'''
import sys
from pathlib import Path
from fin_mas.fontes.registro import RegistroFontes
from fin_mas.services import totp
from fin_mas.services.iam import SENHA_DEMO, Acesso, SegundoFatorPendente
p = Path(sys.argv[1])
a = Acesso(p / "acesso")
print(a.cofre.ler("llm:OPENAI_API_KEY"), RegistroFontes(p / "fontes").cofre.ler("conector:erp"))
try:
    a.autenticar("admin", SENHA_DEMO)
except SegundoFatorPendente as e:
    s, _ = a.confirmar_entrada(e.desafio, totp.codigo(sys.argv[2], a.relogio() + 30))
    print("entrou", s.usuario)
'''
    r = cli(str(destino), segredo, chaves=outra, codigo=conferir)
    assert r.stdout.split() == ["sk-NO-COFRE-424242", "tok-ERP-313131", "entrou", "admin"], r.stderr
    doc = {i["item"]: i for i in json.loads(cli("doctor", "--pasta", str(destino), "--json", chaves=outra).stdout)}
    assert doc["segundo fator no cofre"]["situacao"] == "ok"
    # o doctor avisa quando a conta tem segundo fator e o segredo não está no cofre (ex.: restauração sem o cofre)
    tirar = "import sys; from fin_mas.services.iam import Acesso; Acesso(sys.argv[1]).cofre.remover('totp:admin', 'teste')"
    assert cli(str(destino / "acesso"), chaves=outra, codigo=tirar).returncode == 0
    doc = {i["item"]: i for i in json.loads(cli("doctor", "--pasta", str(destino), "--json", chaves=outra).stdout)}
    assert doc["segundo fator no cofre"]["situacao"] == "aviso" and "admin" in doc["segundo fator no cofre"]["detalhe"]

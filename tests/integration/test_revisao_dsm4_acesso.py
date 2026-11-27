"""DSM4 — revisão: a tela de entrada mostra a conta de demonstração só no modo demonstração.

No ZIP da DSM3, o README e o terminal diziam como entrar, mas a tela de entrada não; quem abrisse o navegador
direto ficava só com o formulário. A senha das contas de demonstração é pública; a de uma instalação real não.
"""
import json
import threading
import urllib.request

import pytest

from fin_mas.live import Simulacao
from fin_mas.server import criar_servidor
from fin_mas.services.iam import SENHA_DEMO, criar_demo

pytestmark = pytest.mark.integracao


@pytest.mark.parametrize("demo", [True, False])
def test_health_shows_demo_credentials_only_in_demo_mode(tmp_path, demo):
    acesso = criar_demo(tmp_path / "acesso", custo_scrypt=10)
    sim = Simulacao("fechar_mes", interativo=True, ms_por_tick=0, pausado=True, acesso=acesso)
    servidor = criar_servidor(sim, porta=0, acesso=acesso, demo=demo)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{servidor.server_address[1]}/api/saude"
        saude = json.loads(urllib.request.urlopen(url, timeout=5).read())
        if demo:
            assert saude["demo"] == {"usuario": "avaliador", "senha": SENHA_DEMO}
        else:
            assert "demo" not in saude and SENHA_DEMO not in json.dumps(saude)
    finally:
        servidor.shutdown()
        servidor.server_close()

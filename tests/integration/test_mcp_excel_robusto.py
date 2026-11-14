"""Servidor MCP de Excel embutido, por stdio de verdade (correção simulada da DSM4, m6): requisição `null`, de outro
tipo ou JSON aninhado demais recebe um erro JSON-RPC e o servidor segue atendendo (antes, morria)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integracao
RAIZ = Path(__file__).resolve().parents[2]


def test_excel_mcp_server_answers_malformed_requests_with_json_rpc_errors_and_keeps_serving(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(RAIZ / "src"), "PYTHONUTF8": "1"}
    proc = subprocess.Popen([sys.executable, "-m", "fin_mas", "mcp-excel", "--pasta", str(tmp_path)], cwd=RAIZ, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8")
    ping = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"})
    try:
        for linha, codigo in (("null", -32600), ("5", -32600), ('"oi"', -32600), ("[" + ping + "]", -32600),
                              ("[" * 100000 + "]" * 100000, -32700), ("{nao e json", -32700),
                              ('{"jsonrpc":"2.0","id":1,"method":"tools/call","params":[1]}', -32602),
                              ('{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ler_aba",'
                               '"arguments":[1]}}', -32602)):
            proc.stdin.write(linha + "\n")
            proc.stdin.flush()
            resposta = json.loads(proc.stdout.readline() or "null")
            assert resposta is not None, f"o servidor morreu com {linha[:40]!r}"
            assert resposta["error"]["code"] == codigo, (linha[:40], resposta)
            proc.stdin.write(ping + "\n")  # e segue vivo para a próxima
            proc.stdin.flush()
            assert json.loads(proc.stdout.readline()) == {"jsonrpc": "2.0", "id": 99, "result": {}}
        assert proc.poll() is None
    finally:
        proc.stdin.close()
        proc.wait(timeout=10)

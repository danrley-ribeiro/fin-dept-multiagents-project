"""Fixtures compartilhadas: rede externa bloqueada em todos os testes (REQ-NF01).

Só o loopback (127.0.0.1) é permitido, para os testes de integração do servidor local
do dashboard; qualquer outro destino falha o teste.
"""
import os
import socket
import tempfile

import pytest

LOOPBACK = ("127.0.0.1", "localhost", "::1")


def pytest_configure(config):
    """O selo HMAC dos traces usa uma chave fixa nos testes (não grava nada no diretório do usuário).

    Definida na sessão inteira, antes de qualquer fixture (inclusive as de escopo de módulo).
    """
    os.environ["FIN_MAS_CHAVE_TRACE"] = "chave-de-teste-do-trace"
    os.environ["FIN_MAS_DIR_CHAVES"] = tempfile.mkdtemp(prefix="fin-mas-chaves-")  # chaves e contadores da memória


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    connect_original = socket.socket.connect
    create_original = socket.create_connection

    def so_loopback(endereco):
        if not (isinstance(endereco, tuple) and endereco[0] in LOOPBACK):
            raise AssertionError(f"acesso à rede é proibido nos testes (offline): {endereco}")

    def connect(self, endereco):
        so_loopback(endereco)
        return connect_original(self, endereco)

    def create_connection(endereco, *args, **kwargs):
        so_loopback(endereco)
        return create_original(endereco, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "create_connection", create_connection)

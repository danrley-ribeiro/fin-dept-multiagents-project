"""Fixtures compartilhadas: rede externa bloqueada em todos os testes (REQ-NF01).

Só o loopback (127.0.0.1) é permitido, para os testes de integração do servidor local
do dashboard; qualquer outro destino falha o teste.
"""
import socket

import pytest

LOOPBACK = ("127.0.0.1", "localhost", "::1")


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

"""Fixtures compartilhadas: rede bloqueada em todos os testes (REQ-NF01)."""
import socket

import pytest


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    def bloqueado(*args, **kwargs):
        raise AssertionError("acesso à rede é proibido nos testes (offline)")

    monkeypatch.setattr(socket.socket, "connect", bloqueado)
    monkeypatch.setattr(socket, "create_connection", bloqueado)

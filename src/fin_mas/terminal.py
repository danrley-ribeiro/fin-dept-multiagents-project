"""Há uma pessoa no terminal para responder perguntas e digitar senhas?

`sys.stdin.isatty()` não basta no Windows: o dispositivo nulo (`NUL`, usado por scripts,
agendadores e `subprocess.DEVNULL`) é um dispositivo de caractere e também responde `True`.
Aí o programa pergunta, recebe fim de arquivo e quebra (`EOFError`), ou o `getpass` espera
um console que não existe. No Windows, só há terminal se o handle da entrada for um console.
"""
import os
import sys


def tem_terminal() -> bool:
    entrada = sys.stdin
    try:
        if entrada is None or not entrada.isatty():
            return False
        if os.name != "nt":
            return True
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(entrada.fileno())
        modo = ctypes.c_ulong()
        return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(modo)))
    except (AttributeError, OSError, ValueError):
        return False

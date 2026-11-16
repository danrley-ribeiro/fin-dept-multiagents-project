"""Há uma pessoa no terminal para responder perguntas e digitar senhas?

`sys.stdin.isatty()` não basta no Windows: o dispositivo nulo (`NUL`, usado por scripts,
agendadores e `subprocess.DEVNULL`) é um dispositivo de caractere e também responde `True`.
Aí o programa pergunta, recebe fim de arquivo e quebra (`EOFError`), ou o `getpass` espera
um console que não existe. No Windows, só há terminal se o handle da entrada for um console.
"""
import ctypes
import os
import sys


def tem_terminal() -> bool:
    entrada = sys.stdin
    try:
        if entrada is None or not entrada.isatty():
            return False
        if os.name != "nt":
            return True
        import msvcrt
        from ctypes import wintypes

        # tipos declarados: sem isso o ctypes passa o handle (64 bits no Windows x64) como `int` de 32 bits
        get_console_mode = ctypes.WinDLL("kernel32", use_last_error=True).GetConsoleMode
        get_console_mode.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        get_console_mode.restype = wintypes.BOOL
        modo = wintypes.DWORD()
        return bool(get_console_mode(msvcrt.get_osfhandle(entrada.fileno()), ctypes.byref(modo)))
    except (AttributeError, OSError, ValueError, ctypes.ArgumentError):
        return False

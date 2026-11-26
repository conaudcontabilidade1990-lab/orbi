"""'Lembrar usuário': guarda a sessão do portal protegida pelo Windows (DPAPI).

Não guarda a senha. Guarda o token de sessão do Firebase, cifrado com a conta do Windows
de quem está usando (só esse usuário, nesse computador, consegue abrir). Ao abrir o Orbi,
a sessão é renovada e o perfil relido no portal; "Sair" apaga o arquivo.
"""
import ctypes
import json
from ctypes import wintypes

from . import config as cfgmod

ARQUIVO = cfgmod.PASTA / "sessao.bin"


class _BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(dados: bytes, proteger: bool) -> bytes:
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    buf = ctypes.create_string_buffer(dados, len(dados))
    entrada = _BLOB(len(dados), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    saida = _BLOB()
    fn = crypt.CryptProtectData if proteger else crypt.CryptUnprotectData
    ok = fn(ctypes.byref(entrada), None, None, None, None, 0x1, ctypes.byref(saida))  # UI_FORBIDDEN
    if not ok:
        raise OSError(ctypes.get_last_error(), "DPAPI falhou")
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        kernel.LocalFree(saida.pbData)


def guardar(email, refresh_token):
    cfgmod.PASTA.mkdir(parents=True, exist_ok=True)
    dados = json.dumps({"email": email, "refresh_token": refresh_token}).encode()
    ARQUIVO.write_bytes(_dpapi(dados, True))


def carregar():
    """(email, refresh_token) ou None."""
    try:
        d = json.loads(_dpapi(ARQUIVO.read_bytes(), False))
        return d["email"], d["refresh_token"]
    except Exception:
        return None


def apagar():
    try:
        ARQUIVO.unlink(missing_ok=True)
    except OSError:
        pass

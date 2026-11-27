"""Resolução e escala da tela (o Orbi foi calibrado em 1366x768 com escala de 100%)."""
import ctypes
import time
from ctypes import wintypes


class _DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD), ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD), ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG), ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD), ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short), ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short), ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32), ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD), ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD), ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD), ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
    ]


def _modo(i):
    dm = _DEVMODEW()
    dm.dmSize = ctypes.sizeof(_DEVMODEW)
    ok = ctypes.windll.user32.EnumDisplaySettingsW(None, i, ctypes.byref(dm))
    return dm if ok else None


def atual():
    dm = _modo(-1)                       # ENUM_CURRENT_SETTINGS
    return (dm.dmPelsWidth, dm.dmPelsHeight) if dm else None


def suportadas():
    res, i = set(), 0
    while True:
        dm = _modo(i)
        if not dm:
            return res
        res.add((dm.dmPelsWidth, dm.dmPelsHeight))
        i += 1


def mudar(largura, altura):
    """Muda a resolução do monitor principal (e grava, para ficar depois de reiniciar). True se deu certo."""
    dm = _modo(-1)
    if not dm:
        return False
    dm.dmPelsWidth, dm.dmPelsHeight = largura, altura
    dm.dmFields = 0x80000 | 0x100000      # DM_PELSWIDTH | DM_PELSHEIGHT
    r = ctypes.windll.user32.ChangeDisplaySettingsW(ctypes.byref(dm), 0x1)   # CDS_UPDATEREGISTRY
    time.sleep(3)
    return r == 0


def escala():
    """Escala do Windows em % (100, 125, 150...)."""
    try:
        return round(ctypes.windll.user32.GetDpiForSystem() * 100 / 96)
    except Exception:
        return 100

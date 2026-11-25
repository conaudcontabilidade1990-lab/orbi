"""Localiza a janela do Domínio pelo título e a coloca na frente, maximizada no monitor principal."""
import ctypes
import time
import unicodedata
from ctypes import wintypes


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _user32():
    return ctypes.windll.user32


def achar(trecho_titulo="dominio escrita fiscal"):
    """Retorna o handle (hwnd) da primeira janela visível cujo título contém o trecho."""
    u = _user32()
    achadas = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cada(hwnd, _):
        if u.IsWindowVisible(hwnd):
            n = u.GetWindowTextLengthW(hwnd)
            if n:
                buf = ctypes.create_unicode_buffer(n + 1)
                u.GetWindowTextW(hwnd, buf, n + 1)
                if _norm(buf.value).strip().startswith(trecho_titulo):
                    achadas.append(hwnd)
        return True

    u.EnumWindows(cada, 0)
    return achadas[0] if achadas else None


def trazer_para_frente(hwnd):
    u = _user32()
    SW_RESTORE, SW_MAXIMIZE = 9, 3
    MONITOR_DEFAULTTOPRIMARY = 1

    # se estiver em outro monitor, leva para o principal (ponto 0,0)
    principal = u.MonitorFromPoint(wintypes.POINT(0, 0), MONITOR_DEFAULTTOPRIMARY)
    if u.IsIconic(hwnd) or u.MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY) != principal:
        u.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.3)
        u.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0004)  # SWP_NOSIZE | SWP_NOZORDER
        time.sleep(0.3)
    u.ShowWindow(hwnd, SW_MAXIMIZE)

    # o Windows só deixa trazer para frente quem está ligado à janela ativa: liga temporariamente
    if u.GetForegroundWindow() != hwnd:
        k = ctypes.windll.kernel32
        meu = k.GetCurrentThreadId()
        ativo = u.GetWindowThreadProcessId(u.GetForegroundWindow(), None)
        ligado = ativo and ativo != meu and u.AttachThreadInput(meu, ativo, True)
        try:
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if ligado:
                u.AttachThreadInput(meu, ativo, False)
    time.sleep(0.8)
    return u.GetForegroundWindow() == hwnd

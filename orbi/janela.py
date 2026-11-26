"""Localiza a janela do Domínio e a coloca na frente, maximizada no monitor principal."""
import ctypes
import time
import unicodedata
from ctypes import wintypes

PROCESSOS_DOMINIO = ("contabil.exe", "appcontroller.exe")


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def _api():
    u = ctypes.WinDLL("user32", use_last_error=True)
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    H = wintypes.HWND
    u.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    u.IsWindowVisible.argtypes = [H]
    u.IsIconic.argtypes = [H]
    u.GetWindowTextLengthW.argtypes = [H]
    u.GetWindowTextW.argtypes = [H, wintypes.LPWSTR, ctypes.c_int]
    u.GetWindowThreadProcessId.argtypes = [H, ctypes.POINTER(wintypes.DWORD)]
    u.GetWindowThreadProcessId.restype = wintypes.DWORD
    u.GetWindowRect.argtypes = [H, ctypes.POINTER(wintypes.RECT)]
    u.ShowWindow.argtypes = [H, ctypes.c_int]
    u.SetWindowPos.argtypes = [H, H, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    u.SetForegroundWindow.argtypes = [H]
    u.BringWindowToTop.argtypes = [H]
    u.GetForegroundWindow.restype = H
    u.MonitorFromWindow.argtypes = [H, wintypes.DWORD]
    u.MonitorFromWindow.restype = ctypes.c_void_p
    u.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    u.MonitorFromPoint.restype = ctypes.c_void_p
    u.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                             ctypes.POINTER(wintypes.DWORD)]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.GetCurrentThreadId.restype = wintypes.DWORD
    return u, k


def _processo(u, k, hwnd):
    pid = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = k.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return buf.value.rsplit("\\", 1)[-1].lower()
        return ""
    finally:
        k.CloseHandle(h)


def janelas_visiveis():
    """[(hwnd, título, processo, área)] das janelas visíveis com título — e também as sem título
    dos processos do Domínio (o GraphOn AppController desenha a janela do Escrita Fiscal sem título)."""
    u, k = _api()
    lista = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cada(hwnd, _):
        try:
            if u.IsWindowVisible(hwnd):
                n = u.GetWindowTextLengthW(hwnd)
                titulo = ""
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    u.GetWindowTextW(hwnd, buf, n + 1)
                    titulo = buf.value
                proc = _processo(u, k, hwnd)
                if titulo or proc in PROCESSOS_DOMINIO:
                    r = wintypes.RECT()
                    u.GetWindowRect(hwnd, ctypes.byref(r))
                    area = max(0, r.right - r.left) * max(0, r.bottom - r.top)
                    lista.append((hwnd, titulo, proc, area))
        except Exception:
            pass
        return True

    u.EnumWindows(cada, 0)
    return lista


AREA_MINIMA = 400 * 300   # janela principal do Domínio, não caixas pequenas


def achar():
    """Retorna (lista de hwnd candidatas em ordem, diagnóstico). Lista vazia se não achou.
    Prioridade: título com 'escrita fiscal'; depois a maior janela do AppController/contabil
    que não seja a 'Lista de Programas'. Quem chama confere pelo título lido na tela."""
    lista = janelas_visiveis()
    u, _ = _api()
    candidatas = []
    for hwnd, titulo, proc, area in lista:
        t = _norm(titulo)
        if "escrita fiscal" in t:
            candidatas.append((2, area, hwnd))
        elif proc in PROCESSOS_DOMINIO and "lista de programas" not in t:
            minimizada = bool(u.IsIconic(hwnd))   # minimizada fica pequenininha: conta mesmo assim
            if area >= AREA_MINIMA or minimizada:
                candidatas.append((1, area if not minimizada else AREA_MINIMA, hwnd))
    if candidatas:
        candidatas.sort(reverse=True)
        return [c[2] for c in candidatas], ""
    diag = "; ".join(f"'{t[:40] or '(sem título)'}' ({p}, área {a})" for _, t, p, a in lista if a > 0)[:700]
    return [], diag


def trazer_para_frente(hwnd):
    u, k = _api()
    SW_RESTORE, SW_MAXIMIZE = 9, 3
    PRIMARIO = 1  # MONITOR_DEFAULTTOPRIMARY

    principal = u.MonitorFromPoint(wintypes.POINT(0, 0), PRIMARIO)
    if u.IsIconic(hwnd) or u.MonitorFromWindow(hwnd, PRIMARIO) != principal:
        u.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.3)
        u.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0004)  # SWP_NOSIZE | SWP_NOZORDER
        time.sleep(0.3)
    u.ShowWindow(hwnd, SW_MAXIMIZE)

    # o Windows só deixa ativar outra janela a quem está ligado à janela ativa: liga temporariamente
    if u.GetForegroundWindow() != hwnd:
        meu = k.GetCurrentThreadId()
        ativo = u.GetWindowThreadProcessId(u.GetForegroundWindow(), None)
        ligado = bool(ativo and ativo != meu and u.AttachThreadInput(meu, ativo, True))
        try:
            u.BringWindowToTop(hwnd)
            u.SetForegroundWindow(hwnd)
        finally:
            if ligado:
                u.AttachThreadInput(meu, ativo, False)
    time.sleep(0.8)


def maximizar(hwnd):
    """Pede ao próprio Windows para maximizar (algumas janelas do AppController ignoram o ShowWindow)."""
    u, _ = _api()
    u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    u.ShowWindow(hwnd, 3)
    u.PostMessageW(hwnd, 0x0112, 0xF030, 0)     # WM_SYSCOMMAND, SC_MAXIMIZE
    time.sleep(0.8)


def retangulo(hwnd):
    u, _ = _api()
    r = wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom

"""Borda azul em degradê na tela enquanto uma rotina roda (no estilo da borda do Claude),
e um mini painel com o progresso e o botão Parar.

- As janelas da borda deixam o clique passar (WS_EX_TRANSPARENT) e não pegam foco.
- Borda e mini painel ficam fora das capturas de tela (WDA_EXCLUDEFROMCAPTURE, Windows 10 2004+),
  então não atrapalham a leitura da tela do Domínio.
"""
import ctypes
import tkinter as tk

GWL_EXSTYLE = -20
WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x80000, 0x20
WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = 0x80, 0x8000000
WDA_EXCLUDEFROMCAPTURE = 0x11

# degradê do Orbi: azul profundo -> azul -> ciano
CORES = ["#0b3d91", "#1565e0", "#1e88ff", "#38b6ff", "#5fd4ff"]


def _hwnd(janela):
    try:
        return ctypes.windll.user32.GetParent(janela.winfo_id()) or janela.winfo_id()
    except Exception:
        return None


def _estilizar(janela, clique_passa, alfa):
    """Estilos do Windows aplicados direto na janela. A transparência também é definida aqui
    (SetLayeredWindowAttributes): o '-alpha' do Tk regravaria os estilos e tiraria o
    'clique passa através'."""
    h = _hwnd(janela)
    if not h:
        return None
    u = ctypes.windll.user32
    u.GetWindowLongW.restype = ctypes.c_long
    est = u.GetWindowLongW(h, GWL_EXSTYLE) | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED
    if clique_passa:
        est |= WS_EX_TRANSPARENT
    u.SetWindowLongW(h, GWL_EXSTYLE, est)
    _alfa(h, alfa)
    try:
        u.SetWindowDisplayAffinity(h, WDA_EXCLUDEFROMCAPTURE)
    except Exception:
        pass
    return h


def _alfa(h, a):
    try:
        ctypes.windll.user32.SetLayeredWindowAttributes(h, 0, max(0, min(255, int(a * 255))), 0x2)
    except Exception:
        pass


def _mistura(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def _degrade(n, desloc=0.0):
    """n cores ao longo do degradê (com deslocamento para animar)."""
    out = []
    k = len(CORES) - 1
    for i in range(n):
        p = ((i / max(1, n - 1)) + desloc) % 1.0
        p = 1 - abs(2 * p - 1)            # vai e volta, sem emenda
        pos = p * k
        j = min(int(pos), k - 1)
        out.append(_mistura(CORES[j], CORES[j + 1], pos - j))
    return out


class Borda:
    def __init__(self, root, espessura=7):
        self.root = root
        self.esp = espessura
        self.janelas = []
        self.painel = None
        self._fase = 0.0
        self._pulso = 0
        self._job = None

    # ------------------------------------------------------------------
    def mostrar(self, ao_parar):
        if self.janelas:
            return
        W, H = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        e = self.esp
        for lado, (x, y, w, h) in {"topo": (0, 0, W, e), "base": (0, H - e, W, e),
                                   "esq": (0, 0, e, H), "dir": (W - e, 0, e, H)}.items():
            j = tk.Toplevel(self.root)
            j.overrideredirect(True)
            j.geometry(f"{w}x{h}+{x}+{y}")
            j.attributes("-topmost", True)
            c = tk.Canvas(j, width=w, height=h, highlightthickness=0, bd=0, bg=CORES[1])
            c.pack(fill="both", expand=True)
            j.update_idletasks()
            hw = _estilizar(j, clique_passa=True, alfa=0.85)
            self.janelas.append((lado, j, c, w, h, hw))
        self._criar_painel(ao_parar, W, H)
        self._animar()

    def _criar_painel(self, ao_parar, W, H):
        p = tk.Toplevel(self.root)
        p.overrideredirect(True)
        p.attributes("-topmost", True)
        largura, altura = 330, 58
        # no alto, entre o menu e o nome da empresa: área vazia do Domínio, onde o Orbi não clica
        p.geometry(f"{largura}x{altura}+{W // 2 + 77}+{self.esp + 4}")
        fundo = "#0f1b2d"
        p.configure(bg=fundo)
        moldura = tk.Frame(p, bg=fundo, highlightthickness=2, highlightbackground="#1e88ff")
        moldura.pack(fill="both", expand=True)
        self.lbl = tk.Label(moldura, text="Orbi trabalhando…", fg="white", bg=fundo,
                            font=("Segoe UI Semibold", 10), anchor="w")
        self.lbl.place(x=12, y=7)
        self.barra = tk.Canvas(moldura, width=220, height=6, bg="#24344d", highlightthickness=0)
        self.barra.place(x=12, y=36)
        bt = tk.Label(moldura, text="Parar", fg="white", bg="#c0392b", font=("Segoe UI Semibold", 10),
                      padx=14, pady=5, cursor="hand2")
        bt.place(relx=1.0, x=-12, rely=0.5, anchor="e")
        bt.bind("<Button-1>", lambda e: ao_parar())
        p.update_idletasks()
        _estilizar(p, clique_passa=False, alfa=0.96)
        self.painel = p
        self.progresso(0, 0, "")

    def progresso(self, feitos, total, texto):
        if not self.painel:
            return
        self.lbl.config(text=texto or "Orbi trabalhando…")
        self.barra.delete("all")
        if total:
            w = int(220 * feitos / total)
            for i, cor in enumerate(_degrade(max(1, w // 4) or 1)):
                self.barra.create_rectangle(i * 4, 0, i * 4 + 4, 6, fill=cor, width=0)

    def _animar(self):
        if not self.janelas:
            return
        self._fase = (self._fase + 0.012) % 1.0
        self._pulso = (self._pulso + 1) % 120
        for lado, j, c, w, h, _ in self.janelas:
            c.delete("all")
            comprido = max(w, h)
            passos = 48
            cores = _degrade(passos, self._fase + (0.25 if lado in ("dir", "base") else 0))
            tam = comprido / passos
            for i, cor in enumerate(cores):
                if w >= h:
                    c.create_rectangle(i * tam, 0, (i + 1) * tam + 1, h, fill=cor, width=0)
                else:
                    c.create_rectangle(0, i * tam, w, (i + 1) * tam + 1, fill=cor, width=0)
        # pulso suave na transparência, como a borda do Claude
        import math
        alfa = 0.62 + 0.3 * (0.5 + 0.5 * math.sin(self._pulso / 120 * 2 * math.pi))
        for *_, hw in self.janelas:
            if hw:
                _alfa(hw, alfa)
        self._job = self.root.after(50, self._animar)

    def esconder(self):
        if self._job:
            self.root.after_cancel(self._job)
            self._job = None
        for _, j, *_ in self.janelas:
            j.destroy()
        self.janelas = []
        if self.painel:
            self.painel.destroy()
            self.painel = None

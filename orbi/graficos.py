"""Tema (claro/escuro) e desenhos animados do Orbi: anel de progresso, barras e contadores."""
import math
import tkinter as tk

# (claro, escuro) — mesmas tuplas que o CustomTkinter usa
COR = {
    "fundo": ("#eef2f8", "#0e1420"),
    "lateral": ("#ffffff", "#131b2b"),
    "cartao": ("#ffffff", "#182235"),
    "borda": ("#dbe3ef", "#26344d"),
    "texto": ("#14213d", "#e6edf7"),
    "suave": ("#66748b", "#8fa0ba"),
    "azul": ("#1e6bff", "#3d8bff"),
    "azul_hover": ("#1557d6", "#2f76e6"),
    "trilho": ("#e3e9f3", "#24314a"),
    "caixa": ("#f7f9fc", "#111a2a"),
    "sucesso": ("#1fa971", "#2fcf8b"),
    "advertencia": ("#e5a00d", "#f2b632"),
    "erro": ("#e0483e", "#ff6b61"),
}


def cor(nome, escuro):
    return COR[nome][1 if escuro else 0]


def _mistura(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def suavizar(t):
    return 1 - (1 - t) ** 3  # ease-out


class Anel:
    """Anel de progresso animado (degradê azul) com texto no meio."""

    def __init__(self, master, tamanho=170, espessura=14):
        self.c = tk.Canvas(master, width=tamanho, height=tamanho, highlightthickness=0, bd=0)
        self.t, self.esp = tamanho, espessura
        self.valor = 0.0
        self.alvo = 0.0
        self.texto, self.sub = "0%", ""
        self.escuro = False
        self._job = None

    def tema(self, escuro, fundo):
        self.escuro = escuro
        self.c.configure(bg=fundo)
        self._desenhar()

    def definir(self, frac, texto, sub=""):
        self.alvo = max(0.0, min(1.0, frac))
        self.texto, self.sub = texto, sub
        if not self._job:
            self._passo()

    def _passo(self):
        dif = self.alvo - self.valor
        if abs(dif) < 0.002:
            self.valor = self.alvo
            self._job = None
        else:
            self.valor += dif * 0.18
            self._job = self.c.after(16, self._passo)
        self._desenhar()

    def _desenhar(self):
        c, t, e = self.c, self.t, self.esp
        c.delete("all")
        caixa = (e, e, t - e, t - e)
        c.create_oval(*caixa, outline=cor("trilho", self.escuro), width=e)
        if self.valor > 0.001:
            # degradê: vários arcos curtos do azul escuro ao ciano
            partes = max(2, int(90 * self.valor))
            ini, cor_a, cor_b = 90, "#1e6bff", "#38c6ff"
            for i in range(partes):
                ext = -360 * self.valor / partes
                c.create_arc(*caixa, start=ini + i * ext, extent=ext - 0.8, style="arc",
                             outline=_mistura(cor_a, cor_b, i / max(1, partes - 1)), width=e)
        c.create_text(t / 2, t / 2 - (8 if self.sub else 0), text=self.texto,
                      fill=cor("texto", self.escuro), font=("Segoe UI Semibold", 22))
        if self.sub:
            c.create_text(t / 2, t / 2 + 20, text=self.sub, fill=cor("suave", self.escuro),
                          font=("Segoe UI", 10))


class Barras:
    """Barras empilhadas por dia (sucesso / advertência / erro), crescendo ao aparecer."""

    def __init__(self, master, largura=620, altura=210):
        self.c = tk.Canvas(master, width=largura, height=altura, highlightthickness=0, bd=0)
        self.w, self.h = largura, altura
        self.dados = []
        self.escuro = False
        self._k = 1.0
        self._job = None

    def tema(self, escuro, fundo):
        self.escuro = escuro
        self.c.configure(bg=fundo)
        self._desenhar()

    def definir(self, por_dia):
        self.dados = por_dia
        self._k = 0.0
        if self._job:
            self.c.after_cancel(self._job)
        self._passo(0)

    def _passo(self, i):
        self._k = suavizar(min(1.0, i / 24))
        self._desenhar()
        self._job = self.c.after(16, self._passo, i + 1) if i < 24 else None

    def _desenhar(self):
        c = self.c
        c.delete("all")
        if not self.dados:
            return
        esq, base, topo = 34, self.h - 26, 12
        maximo = max(1, max(sum(v.values()) for _, v in self.dados))
        n = len(self.dados)
        passo = (self.w - esq - 8) / n
        larg = passo * 0.58
        # linhas de grade
        for g in range(0, 5):
            y = base - (base - topo) * g / 4
            c.create_line(esq, y, self.w - 8, y, fill=cor("trilho", self.escuro))
            c.create_text(esq - 6, y, text=str(round(maximo * g / 4)), anchor="e",
                          fill=cor("suave", self.escuro), font=("Segoe UI", 8))
        for i, (dia, v) in enumerate(self.dados):
            x0 = esq + i * passo + (passo - larg) / 2
            y = base
            for st in ("sucesso", "advertencia", "erro"):
                alt = (base - topo) * v.get(st, 0) / maximo * self._k
                if alt > 0:
                    c.create_rectangle(x0, y - alt, x0 + larg, y, fill=cor(st, self.escuro), width=0)
                    y -= alt
            if n <= 16 or i % 2 == 0:
                c.create_text(x0 + larg / 2, base + 12, text=dia[8:10] + "/" + dia[5:7],
                              fill=cor("suave", self.escuro), font=("Segoe UI", 8))


def contar(label, de, para, formato="{}", passos=24, i=0):
    """Número subindo de 'de' até 'para' num rótulo (CTkLabel ou tk.Label)."""
    v = round(de + (para - de) * suavizar(min(1.0, i / passos)))
    try:
        label.configure(text=formato.format(v))
    except tk.TclError:
        return
    if i < passos:
        label.after(16, contar, label, de, para, formato, passos, i + 1)

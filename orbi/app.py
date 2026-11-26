"""Janela do Orbi (CustomTkinter): login, Executar, Painel e Calibrar, com tema claro/escuro."""
import ctypes
import datetime as dt
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:  # coordenadas reais da tela, mesmo com escala do Windows
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import customtkinter as ctk
from PIL import Image

from . import VERSAO, atualizacao, conta, estatisticas, sessao
from . import config as cfgmod
from .borda import Borda
from .graficos import COR, Anel, Barras, contar, cor
from .rotinas import ROTINAS, Resultado
from .tela import Cancelado, Parar, Tela

ctk.set_window_scaling(1.0)   # o app já é "DPI aware"; sem escala extra do CustomTkinter
ctk.set_widget_scaling(1.0)


def recurso(rel):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / rel


F = "Segoe UI"


def fonte(tam=13, peso="normal"):
    return ctk.CTkFont(family=F, size=tam, weight=peso)


STATUS_ROTULO = {"sucesso": "Sucesso", "advertencia": "Advertências", "erro": "Erros"}
STATUS_ICONE = {"sucesso": "✓", "advertencia": "!", "erro": "✕"}


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = cfgmod.carregar()
        self.fila = queue.Queue()
        self.parar = threading.Event()
        self.rodando = False
        self.usuario = None
        self.paginas = {}
        self.pagina_atual = None
        self.borda = Borda(root)

        ctk.set_appearance_mode({"escuro": "dark", "claro": "light"}.get(self.cfg.get("tema"), "light"))
        root.title(f"Orbi {VERSAO}")
        W, H = root.winfo_screenwidth(), root.winfo_screenheight()
        larg, alt = min(1100, W - 40), min(700, H - 80)
        root.geometry(f"{larg}x{alt}+{max(0, (W - larg) // 2)}+{max(0, (H - alt) // 2 - 20)}")
        root.minsize(min(900, larg), min(600, alt))
        root.configure(fg_color=COR["fundo"])
        self._icone()
        self.logo = ctk.CTkImage(Image.open(recurso("orbi/recursos/logo.png")), size=(46, 46))
        self.logo_grande = ctk.CTkImage(Image.open(recurso("orbi/recursos/logo.png")), size=(104, 104))

        self.base = ctk.CTkFrame(root, fg_color="transparent")
        self.base.pack(fill="both", expand=True)

        if self.cfg.get("_erro_config"):
            self.log(f"Aviso: config.json com erro, usando padrão ({self.cfg['_erro_config']}).")
        atualizacao.limpar_antigo()
        threading.Thread(target=self._checar_atualizacao, daemon=True).start()
        root.after(60, self._drenar)
        root.protocol("WM_DELETE_WINDOW", self._fechar)

        guardada = sessao.carregar()
        if guardada:
            self._tela_login(entrando=guardada[0])
            self._em_thread(lambda: self._login_trabalho(lambda: conta.renovar(*guardada), lembrar=True))
        else:
            self._tela_login()
        self._aparecer()

    # ------------------------------ utilidades ------------------------------
    def _icone(self):
        ico = recurso("orbi.ico")
        if ico.exists():
            self.root.after(250, lambda: self.root.iconbitmap(str(ico)))

    @property
    def escuro(self):
        return ctk.get_appearance_mode() == "Dark"

    def _aparecer(self, passo=0):
        """Janela surge com um fade rápido."""
        try:
            self.root.attributes("-alpha", min(1.0, 0.15 + passo / 10))
        except tk.TclError:
            return
        if passo < 10:
            self.root.after(18, self._aparecer, passo + 1)

    def _limpar(self):
        for w in self.base.winfo_children():
            w.destroy()
        self.paginas = {}
        self.pagina_atual = None

    def _em_thread(self, alvo):
        threading.Thread(target=alvo, daemon=True).start()

    def log(self, msg, alvo="log"):
        self.fila.put((alvo, f"{dt.datetime.now():%H:%M:%S}  {msg}"))

    # ------------------------------ login ------------------------------
    def _tela_login(self, entrando=None):
        self._limpar()
        cartao = ctk.CTkFrame(self.base, fg_color=COR["cartao"], corner_radius=22,
                              border_width=1, border_color=COR["borda"])
        cartao.place(relx=0.5, rely=0.5, anchor="center")
        dentro = ctk.CTkFrame(cartao, fg_color="transparent")
        dentro.pack(padx=46, pady=36)
        ctk.CTkLabel(dentro, text="", image=self.logo_grande).pack()
        ctk.CTkLabel(dentro, text="Orbi", font=fonte(30, "bold"), text_color=COR["texto"]).pack(pady=(10, 0))
        ctk.CTkLabel(dentro, text="Entre com a sua conta do Portal Conaud", font=fonte(13),
                     text_color=COR["suave"]).pack(pady=(0, 18))

        self.var_email = tk.StringVar(value=entrando or self.cfg.get("ultimo_email", ""))
        self.var_senha = tk.StringVar()
        self.var_lembrar = tk.BooleanVar(value=self.cfg.get("lembrar", True))
        campo = dict(width=320, height=42, corner_radius=10, font=fonte(13), border_width=1,
                     border_color=COR["borda"], fg_color=COR["caixa"], text_color=COR["texto"])
        ctk.CTkLabel(dentro, text="E-mail", font=fonte(12, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x")
        e_email = ctk.CTkEntry(dentro, textvariable=self.var_email, **campo)
        e_email.pack(pady=(2, 10))
        ctk.CTkLabel(dentro, text="Senha", font=fonte(12, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x")
        e_senha = ctk.CTkEntry(dentro, textvariable=self.var_senha, show="•", **campo)
        e_senha.pack(pady=(2, 4))
        ctk.CTkCheckBox(dentro, text="Lembrar de mim neste computador", variable=self.var_lembrar,
                        font=fonte(12), text_color=COR["suave"], corner_radius=6,
                        checkbox_width=20, checkbox_height=20).pack(anchor="w", pady=(8, 4))
        self.bt_entrar = ctk.CTkButton(dentro, text="Entrar", width=320, height=44, corner_radius=12,
                                       font=fonte(14, "bold"), fg_color=COR["azul"],
                                       hover_color=COR["azul_hover"], command=self._entrar)
        self.bt_entrar.pack(pady=(14, 4))
        self.lbl_login = ctk.CTkLabel(dentro, text="", font=fonte(12), text_color=COR["erro"], wraplength=320)
        self.lbl_login.pack(pady=(6, 0))
        ctk.CTkLabel(dentro, text=f"v{VERSAO}", font=fonte(11), text_color=COR["suave"]).pack(pady=(10, 0))

        e_senha.bind("<Return>", lambda e: self._entrar())
        e_email.bind("<Return>", lambda e: e_senha.focus_set())
        def foco():
            alvo = e_senha if self.var_email.get() else e_email
            try:
                if alvo.winfo_exists():
                    alvo.focus_set()
            except tk.TclError:
                pass
        self.root.after(120, foco)
        if entrando:
            self.bt_entrar.configure(state="disabled", text="Entrando…")
            self.lbl_login.configure(text=f"Entrando como {entrando}…", text_color=COR["suave"])

    def _entrar(self):
        email, senha, lembrar = self.var_email.get().strip(), self.var_senha.get(), self.var_lembrar.get()
        self.bt_entrar.configure(state="disabled", text="Entrando…")
        self.lbl_login.configure(text="", text_color=COR["suave"])
        self._em_thread(lambda: self._login_trabalho(lambda: conta.entrar(email, senha), lembrar))

    def _login_trabalho(self, fazer, lembrar):
        try:
            u = fazer()
            if lembrar:
                try:
                    sessao.guardar(u.email, u.refresh_token)
                except Exception:
                    pass
            else:
                sessao.apagar()
            self.fila.put(("login_ok", (u, lembrar)))
        except conta.ErroLogin as e:
            self.fila.put(("login_erro", str(e)))
        except Exception as e:
            self.fila.put(("login_erro", f"Erro inesperado: {e}"))

    def _login_erro(self, msg):
        if not hasattr(self, "bt_entrar") or not self.bt_entrar.winfo_exists():
            self._tela_login()
        self.bt_entrar.configure(state="normal", text="Entrar")
        self.lbl_login.configure(text=msg, text_color=COR["erro"])

    def _login_ok(self, usuario, lembrar=True):
        self.usuario = usuario
        self.cfg["ultimo_email"] = usuario.email
        self.cfg["lembrar"] = bool(lembrar)
        cfgmod.salvar(self.cfg)
        self._tela_principal()

    def _sair(self):
        if self.rodando:
            messagebox.showwarning("Orbi", "Pare a rotina em execução antes de sair.")
            return
        sessao.apagar()
        self.usuario = None
        self._tela_login()

    # ------------------------------ estrutura principal ------------------------------
    def _rotinas_liberadas(self):
        deps = self.usuario.departamentos() if self.usuario else set()
        return [r for r in ROTINAS if r.departamento in deps]

    def _tela_principal(self):
        self._limpar()
        lateral = ctk.CTkFrame(self.base, width=224, corner_radius=0, fg_color=COR["lateral"])
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        topo = ctk.CTkFrame(lateral, fg_color="transparent")
        topo.pack(fill="x", padx=18, pady=(20, 22))
        ctk.CTkLabel(topo, text="", image=self.logo).pack(side="left")
        nome = ctk.CTkFrame(topo, fg_color="transparent")
        nome.pack(side="left", padx=10)
        ctk.CTkLabel(nome, text="Orbi", font=fonte(22, "bold"), text_color=COR["texto"]).pack(anchor="w")
        ctk.CTkLabel(nome, text=f"Robô do Domínio\nversão {VERSAO}", font=fonte(11),
                     text_color=COR["suave"], justify="left").pack(anchor="w")

        self.nav = {}
        itens = [("executar", "▶   Executar"), ("painel", "▦   Painel")]
        if self.usuario.admin:
            itens.append(("calibrar", "⚙   Calibrar"))
        for chave, texto in itens:
            b = ctk.CTkButton(lateral, text=texto, anchor="w", height=42, corner_radius=10,
                              font=fonte(14), fg_color="transparent", text_color=COR["texto"],
                              hover_color=COR["trilho"], command=lambda k=chave: self.mostrar(k))
            b.pack(fill="x", padx=12, pady=3)
            self.nav[chave] = b

        rodape = ctk.CTkFrame(lateral, fg_color="transparent")
        rodape.pack(side="bottom", fill="x", padx=16, pady=16)
        self.var_escuro = tk.BooleanVar(value=self.escuro)
        ctk.CTkSwitch(rodape, text="Modo escuro", variable=self.var_escuro, command=self._trocar_tema,
                      font=fonte(12), text_color=COR["texto"], progress_color=COR["azul"]).pack(anchor="w", pady=(0, 14))
        ctk.CTkLabel(rodape, text=self.usuario.nome, font=fonte(13, "bold"), text_color=COR["texto"],
                     anchor="w").pack(fill="x")
        ctk.CTkLabel(rodape, text=("Administrador · " if self.usuario.admin else "Operador · ") + self.usuario.email,
                     font=fonte(11), text_color=COR["suave"], anchor="w", wraplength=190, justify="left").pack(fill="x")
        ctk.CTkButton(rodape, text="Sair", height=32, corner_radius=8, font=fonte(12),
                      fg_color="transparent", border_width=1, border_color=COR["borda"],
                      text_color=COR["texto"], hover_color=COR["trilho"], command=self._sair).pack(fill="x", pady=(10, 0))

        self.area = ctk.CTkFrame(self.base, fg_color="transparent")
        self.area.pack(side="left", fill="both", expand=True)
        self.lbl_status = ctk.CTkLabel(self.area, text="Pronto.", font=fonte(11), text_color=COR["suave"], anchor="w")
        self.lbl_status.pack(side="bottom", fill="x", padx=26, pady=(0, 8))
        self.conteudo = ctk.CTkFrame(self.area, fg_color="transparent")
        self.conteudo.pack(fill="both", expand=True)
        self.rotinas = self._rotinas_liberadas()
        self.mostrar("executar")

    def mostrar(self, chave):
        """Troca de página com um deslize suave."""
        if self.pagina_atual == chave:
            return
        for k, b in self.nav.items():
            ativo = k == chave
            b.configure(fg_color=COR["azul"] if ativo else "transparent",
                        text_color=("#ffffff", "#ffffff") if ativo else COR["texto"],
                        hover_color=COR["azul_hover"] if ativo else COR["trilho"])
        if self.pagina_atual in self.paginas:
            self.paginas[self.pagina_atual].place_forget()
        if chave not in self.paginas:
            self.paginas[chave] = getattr(self, f"_pagina_{chave}")()
        self.pagina_atual = chave
        pg = self.paginas[chave]
        if chave == "painel":
            self._atualizar_painel()
        self._deslizar(pg, 0)

    def _deslizar(self, pg, i, passos=12):
        k = 1 - (1 - min(1.0, i / passos)) ** 3
        pg.place(relx=0.04 * (1 - k), rely=0, relwidth=1, relheight=1)
        if i < passos:
            self.root.after(14, self._deslizar, pg, i + 1, passos)

    def _cartao(self, master, **kw):
        return ctk.CTkFrame(master, fg_color=COR["cartao"], corner_radius=16, border_width=1,
                            border_color=COR["borda"], **kw)

    def _titulo(self, master, titulo, sub):
        ctk.CTkLabel(master, text=titulo, font=fonte(24, "bold"), text_color=COR["texto"], anchor="w").pack(fill="x")
        ctk.CTkLabel(master, text=sub, font=fonte(13), text_color=COR["suave"], anchor="w").pack(fill="x", pady=(0, 14))

    # ------------------------------ página Executar ------------------------------
    def _pagina_executar(self):
        pg = ctk.CTkFrame(self.conteudo, fg_color="transparent")
        corpo = ctk.CTkFrame(pg, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=26, pady=(22, 6))
        self._titulo(corpo, "Executar rotina", "Escolha o departamento, a rotina e as empresas.")
        if not self.rotinas:
            ctk.CTkLabel(corpo, text="Seu usuário não tem acesso, no portal, a nenhum departamento com rotinas "
                         "no Orbi. Peça a um administrador para liberar o departamento.",
                         font=fonte(13), text_color=COR["texto"], wraplength=600, justify="left").pack(anchor="w")
            return pg

        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="both", expand=True)
        dir_ = self._cartao(linha, width=250)
        dir_.pack(side="right", fill="y")
        dir_.pack_propagate(False)
        esq = self._cartao(linha)
        esq.pack(side="left", fill="both", expand=True, padx=(0, 12))

        f = ctk.CTkFrame(esq, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=20, pady=18)
        deps = [d for d in conta.DEPARTAMENTOS if any(r.departamento == d for r in self.rotinas)]
        ultima = next((r for r in self.rotinas if r.id == self.cfg.get("ultima_rotina")), self.rotinas[0])

        def rotulo(txt):
            ctk.CTkLabel(f, text=txt, font=fonte(12, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x")

        rotulo("DEPARTAMENTO")
        self.var_dep = tk.StringVar(value=conta.DEPARTAMENTOS[ultima.departamento])
        self.om_dep = ctk.CTkOptionMenu(f, variable=self.var_dep, values=[conta.DEPARTAMENTOS[d] for d in deps],
                                        command=lambda v: self._filtrar_rotinas(), height=38, corner_radius=10,
                                        font=fonte(13), dropdown_font=fonte(13), dynamic_resizing=False,
                                        fg_color=COR["azul"], button_color=COR["azul_hover"])
        self.om_dep.pack(fill="x", pady=(4, 12))
        rotulo("ROTINA")
        self.var_rotina = tk.StringVar(value=ultima.nome)
        self.om_rot = ctk.CTkOptionMenu(f, variable=self.var_rotina, values=[ultima.nome],
                                        command=lambda v: self._descricao(), height=38, corner_radius=10,
                                        font=fonte(13), dropdown_font=fonte(13), dynamic_resizing=False,
                                        fg_color=COR["azul"], button_color=COR["azul_hover"])
        self.om_rot.pack(fill="x", pady=(4, 4))
        self.lbl_desc = ctk.CTkLabel(f, text="", font=fonte(12), text_color=COR["suave"], anchor="w",
                                     justify="left", wraplength=520)
        self.lbl_desc.pack(fill="x", pady=(2, 12))
        rotulo("EMPRESAS (códigos separados por espaço, vírgula ou linha)")
        self.txt_emp = ctk.CTkTextbox(f, height=70, corner_radius=10, font=("Consolas", 13), border_width=1,
                                      border_color=COR["borda"], fg_color=COR["caixa"], text_color=COR["texto"])
        self.txt_emp.pack(fill="x", pady=(4, 12))
        self.txt_emp.insert("1.0", self.cfg.get("ultimas_empresas", ""))

        acoes = ctk.CTkFrame(f, fg_color="transparent")
        acoes.pack(fill="x")
        self.var_simular = tk.BooleanVar(value=True)
        ctk.CTkSwitch(acoes, text="Simular (vai até o diálogo e cancela)", variable=self.var_simular,
                      font=fonte(12), text_color=COR["texto"], progress_color=COR["advertencia"]).pack(side="left")
        self.bt_parar = ctk.CTkButton(acoes, text="Parar", width=96, height=40, corner_radius=10, font=fonte(13, "bold"),
                                      fg_color=COR["erro"], hover_color=("#c0392b", "#e0483e"),
                                      command=self.parar.set, state="disabled")
        self.bt_parar.pack(side="right")
        self.bt_iniciar = ctk.CTkButton(acoes, text="Iniciar", width=130, height=40, corner_radius=10,
                                        font=fonte(13, "bold"), fg_color=COR["azul"], hover_color=COR["azul_hover"],
                                        command=self.iniciar)
        self.bt_iniciar.pack(side="right", padx=8)

        ctk.CTkLabel(f, text="REGISTRO", font=fonte(12, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x", pady=(14, 4))
        self.txt_log = ctk.CTkTextbox(f, corner_radius=10, font=("Consolas", 11), border_width=1,
                                      border_color=COR["borda"], state="disabled", fg_color=COR["caixa"], text_color=COR["texto"])
        self.txt_log.pack(fill="both", expand=True)

        # lado direito: anel de progresso e contadores desta execução
        ctk.CTkLabel(dir_, text="Progresso", font=fonte(15, "bold"), text_color=COR["texto"]).pack(pady=(18, 6))
        self.anel = Anel(dir_, tamanho=180, espessura=15)
        self.anel.c.pack(pady=4)
        self.anel.definir(0, "0%", "aguardando")
        self.cont_exec = {}
        for st in ("sucesso", "advertencia", "erro"):
            l = ctk.CTkFrame(dir_, fg_color=COR["fundo"], corner_radius=10)
            l.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(l, text=STATUS_ICONE[st], width=26, height=26, corner_radius=13, fg_color=COR[st],
                         text_color="#ffffff", font=fonte(13, "bold")).pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(l, text=STATUS_ROTULO[st], font=fonte(12), text_color=COR["texto"]).pack(side="left")
            n = ctk.CTkLabel(l, text="0", font=fonte(16, "bold"), text_color=COR["texto"])
            n.pack(side="right", padx=12)
            self.cont_exec[st] = n
        ctk.CTkLabel(dir_, text="Emergência: mouse no canto\nsuperior esquerdo da tela.", font=fonte(11),
                     text_color=COR["suave"], justify="center").pack(side="bottom", pady=14)
        self._tema_graficos()
        self._filtrar_rotinas(manter=ultima.nome)
        return pg

    def _filtrar_rotinas(self, manter=None):
        dep = next((d for d, n in conta.DEPARTAMENTOS.items() if n == self.var_dep.get()), None)
        nomes = [r.nome for r in self.rotinas if r.departamento == dep]
        self.om_rot.configure(values=nomes or [""])
        self.var_rotina.set(manter if manter in nomes else (nomes[0] if nomes else ""))
        self._descricao()

    def _descricao(self):
        r = self._rotina()
        self.lbl_desc.configure(text=r.descricao if r else "")

    def _rotina(self):
        return next((r for r in getattr(self, "rotinas", []) if r.nome == self.var_rotina.get()), None)

    # ------------------------------ página Painel ------------------------------
    def _pagina_painel(self):
        pg = ctk.CTkFrame(self.conteudo, fg_color="transparent")
        corpo = ctk.CTkFrame(pg, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=26, pady=(22, 6))
        self._titulo(corpo, "Painel", "Rotinas realizadas neste computador (simulações não entram nos totais).")
        kpis = ctk.CTkFrame(corpo, fg_color="transparent")
        kpis.pack(fill="x")
        self.kpi = {}
        for i, (chave, titulo, corx) in enumerate([("sucesso", "Com sucesso", "sucesso"),
                                                   ("advertencia", "Com advertência", "advertencia"),
                                                   ("erro", "Com erro", "erro"), ("hoje", "Hoje", "azul")]):
            c = self._cartao(kpis)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            kpis.columnconfigure(i, weight=1)
            ctk.CTkFrame(c, height=4, corner_radius=2, fg_color=COR[corx]).pack(fill="x", padx=16, pady=(14, 0))
            ctk.CTkLabel(c, text=titulo, font=fonte(12), text_color=COR["suave"], anchor="w").pack(fill="x", padx=16, pady=(8, 0))
            n = ctk.CTkLabel(c, text="0", font=fonte(30, "bold"), text_color=COR["texto"], anchor="w")
            n.pack(fill="x", padx=16, pady=(0, 12))
            self.kpi[chave] = n

        baixo = ctk.CTkFrame(corpo, fg_color="transparent")
        baixo.pack(fill="both", expand=True, pady=(12, 0))
        ult = self._cartao(baixo, width=290)
        ult.pack(side="right", fill="y")
        ult.pack_propagate(False)
        g = self._cartao(baixo)
        g.pack(side="left", fill="both", expand=True, padx=(0, 12))
        cab = ctk.CTkFrame(g, fg_color="transparent")
        cab.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(cab, text="Últimos 14 dias", font=fonte(15, "bold"), text_color=COR["texto"]).pack(side="left")
        for st in ("erro", "advertencia", "sucesso"):
            ctk.CTkLabel(cab, text=f"● {STATUS_ROTULO[st]}", font=fonte(11), text_color=COR[st]).pack(side="right", padx=6)
        self.barras = Barras(g, largura=520, altura=230)
        self.barras.c.pack(padx=14, pady=10, fill="both", expand=True)
        self.lbl_sim = ctk.CTkLabel(g, text="", font=fonte(11), text_color=COR["suave"], anchor="w")
        self.lbl_sim.pack(fill="x", padx=18, pady=(0, 12))

        ctk.CTkLabel(ult, text="Últimas empresas", font=fonte(15, "bold"), text_color=COR["texto"],
                     anchor="w").pack(fill="x", padx=16, pady=(14, 6))
        self.lista_ult = ctk.CTkFrame(ult, fg_color="transparent")
        self.lista_ult.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._tema_graficos()
        return pg

    def _atualizar_painel(self):
        if not hasattr(self, "kpi") or not self.kpi["sucesso"].winfo_exists():
            return
        r = estatisticas.resumo()
        for st in ("sucesso", "advertencia", "erro"):
            contar(self.kpi[st], 0, r["total"][st])
        contar(self.kpi["hoje"], 0, sum(r["hoje"].values()))
        self.barras.definir(r["por_dia"])
        self.lbl_sim.configure(text=f"Simulações realizadas: {r['simulacoes']}")
        for w in self.lista_ult.winfo_children():
            w.destroy()
        if not r["ultimos"]:
            ctk.CTkLabel(self.lista_ult, text="Nada por aqui ainda.", font=fonte(12),
                         text_color=COR["suave"]).pack(pady=20)
        for reg in r["ultimos"]:
            l = ctk.CTkFrame(self.lista_ult, fg_color=COR["fundo"], corner_radius=10)
            l.pack(fill="x", pady=3)
            st = reg.get("status", "erro")
            ctk.CTkLabel(l, text=STATUS_ICONE.get(st, "?"), width=22, height=22, corner_radius=11,
                         fg_color=COR.get(st, COR["erro"]), text_color="#ffffff",
                         font=fonte(11, "bold")).pack(side="left", padx=8, pady=6)
            sim = " · simulação" if reg.get("simulacao") else ""
            ctk.CTkLabel(l, text=f"Empresa {reg.get('empresa')}{sim}\n{reg.get('quando', '')[11:16]} · "
                         f"{reg.get('rotina', '')[:28]}", font=fonte(11), text_color=COR["texto"],
                         justify="left", anchor="w").pack(side="left", fill="x")

    # ------------------------------ página Calibrar ------------------------------
    def _pagina_calibrar(self):
        pg = ctk.CTkFrame(self.conteudo, fg_color="transparent")
        corpo = ctk.CTkFrame(pg, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=26, pady=(22, 6))
        self._titulo(corpo, "Calibrar", "Use quando o Domínio mudar de tela ou de resolução.")
        c = self._cartao(corpo)
        c.pack(fill="both", expand=True)
        botoes = ctk.CTkFrame(c, fg_color="transparent")
        botoes.pack(fill="x", padx=18, pady=(16, 8))
        for texto, cmd in [("Testar leituras (5 s)", lambda: self._em_thread(self._calibrar)),
                           ("Posição do mouse (3 s)", lambda: self._em_thread(self._posicao)),
                           ("Abrir configuração", lambda: self._abrir(cfgmod.ARQUIVO, criar=True)),
                           ("Abrir pasta de logs", lambda: self._abrir(cfgmod.PASTA_LOGS)),
                           ("Recarregar configuração", self._recarregar)]:
            ctk.CTkButton(botoes, text=texto, height=36, corner_radius=10, font=fonte(12),
                          fg_color=COR["azul"], hover_color=COR["azul_hover"], command=cmd).pack(side="left", padx=(0, 8))
        self.txt_cal = ctk.CTkTextbox(c, corner_radius=10, font=("Consolas", 11), border_width=1,
                                      border_color=COR["borda"], state="disabled", fg_color=COR["caixa"], text_color=COR["texto"])
        self.txt_cal.pack(fill="both", expand=True, padx=18, pady=(4, 18))
        return pg

    # ------------------------------ tema ------------------------------
    def _trocar_tema(self):
        escuro = self.var_escuro.get()
        ctk.set_appearance_mode("dark" if escuro else "light")
        self.cfg["tema"] = "escuro" if escuro else "claro"
        cfgmod.salvar(self.cfg)
        self.root.after(30, self._tema_graficos)

    def _tema_graficos(self):
        fundo = cor("cartao", self.escuro)
        for g in (getattr(self, "anel", None), getattr(self, "barras", None)):
            try:
                if g and g.c.winfo_exists():
                    g.tema(self.escuro, fundo)
            except tk.TclError:
                pass

    # ------------------------------ fila de mensagens ------------------------------
    def _drenar(self):
        while True:
            try:
                alvo, msg = self.fila.get_nowait()
            except queue.Empty:
                break
            if alvo == "login_ok":
                self._login_ok(*msg)
            elif alvo == "login_erro":
                self._login_erro(msg)
            elif alvo == "status":
                if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
                    self.lbl_status.configure(text=msg)
            elif alvo == "progresso":
                self._progresso(*msg)
            elif alvo == "resultado":
                self._contar_resultado(msg)
            elif alvo == "fim":
                self._fim()
            else:
                self._escrever(alvo, msg)
        self.root.after(60, self._drenar)

    def _escrever(self, alvo, msg):
        w = getattr(self, "txt_cal" if alvo == "cal" else "txt_log", None)
        try:
            if w is not None and w.winfo_exists():
                w.configure(state="normal")
                w.insert("end", msg + "\n")
                w.see("end")
                w.configure(state="disabled")
        except tk.TclError:
            pass
        try:
            cfgmod.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
            with open(cfgmod.PASTA_LOGS / f"orbi_{dt.date.today():%Y%m%d}.log", "a", encoding="utf-8") as arq:
                arq.write(msg + "\n")
        except OSError:
            pass

    def _abrir(self, caminho, criar=False):
        if criar:
            if not caminho.exists():
                cfgmod.salvar(self.cfg)
        else:
            caminho.mkdir(parents=True, exist_ok=True)
        os.startfile(str(caminho))

    def _recarregar(self):
        self.cfg = cfgmod.carregar()
        self.log("Configuração recarregada.", "cal")

    # ------------------------------ executar ------------------------------
    def iniciar(self):
        if self.rodando:
            return
        rot = self._rotina()
        if not rot or not self.usuario or rot.departamento not in self.usuario.departamentos():
            messagebox.showwarning("Orbi", "Escolha uma rotina liberada para o seu usuário.")
            return
        empresas = [e for e in re.split(r"[\s,;]+", self.txt_emp.get("1.0", "end")) if e]
        if rot.pede_empresas and not empresas:
            messagebox.showwarning("Orbi", "Informe ao menos um código de empresa.")
            return
        if any(not e.isdigit() for e in empresas):
            messagebox.showwarning("Orbi", "Use só códigos numéricos de empresa.")
            return
        simular = self.var_simular.get()
        faltam = [r for r in rot.precisa_regioes if not self.cfg["regioes"].get(r)]
        if not simular and faltam:
            messagebox.showwarning("Orbi", "Antes de gerar de verdade é preciso calibrar: " + ", ".join(faltam) + ".")
            return
        if not simular and not messagebox.askyesno(
                "Orbi", f"{rot.nome}\n{len(empresas)} empresa(s), GERAÇÃO REAL.\n\nIniciar?"):
            return

        self.cfg["ultima_rotina"] = rot.id
        self.cfg["ultimas_empresas"] = " ".join(empresas)
        cfgmod.salvar(self.cfg)
        self.parar.clear()
        self.rodando = True
        self.total_exec = len(empresas)
        self.feitos_exec = 0
        self.num_exec = {s: 0 for s in estatisticas.STATUS}
        for st, lbl in self.cont_exec.items():
            lbl.configure(text="0")
        self.anel.definir(0, "0%", f"0 de {len(empresas)}")
        self.bt_iniciar.configure(state="disabled")
        self.bt_parar.configure(state="normal")
        self.borda.mostrar(self.parar.set)
        self.borda.progresso(0, len(empresas), f"{rot.nome} · começando…")
        self._em_thread(lambda: self._executar(rot, empresas, simular))

    def _progresso(self, i, n, codigo):
        self.anel.definir((i - 1) / n, f"{round(100 * (i - 1) / n)}%", f"empresa {codigo} · {i} de {n}")
        self.borda.progresso(i - 1, n, f"Empresa {codigo} · {i} de {n}")
        self.lbl_status.configure(text=f"Empresa {codigo} ({i}/{n})")

    def _contar_resultado(self, dados):
        codigo, status = dados
        self.feitos_exec += 1
        antes = self.num_exec[status]
        self.num_exec[status] += 1
        contar(self.cont_exec[status], antes, self.num_exec[status], passos=12)
        n = self.total_exec
        self.anel.definir(self.feitos_exec / n, f"{round(100 * self.feitos_exec / n)}%",
                          f"{self.feitos_exec} de {n}")
        self.borda.progresso(self.feitos_exec, n, f"Empresa {codigo}: {STATUS_ROTULO[status].lower()}")

    def _executar(self, rot, empresas, simular):
        t = Tela(self.cfg, self.log, self.parar)
        resultados = []
        email = self.usuario.email
        self.log(f"=== {rot.nome} | {len(empresas)} empresa(s) | {'SIMULAÇÃO' if simular else 'GERAÇÃO REAL'}"
                 f" | usuário: {email}")
        self.log("Começando em 5 s — deixe o Escrita Fiscal aberto e não mexa no mouse.")
        self.root.after(0, self.root.iconify)

        def registrar(cod, status, texto):
            self.fila.put(("resultado", (cod, status)))
            try:
                estatisticas.registrar(email, rot.nome, cod, status, texto, simular)
            except OSError:
                pass

        try:
            t.dormir(5)
            t.conferir_resolucao()
            for i, cod in enumerate(empresas, 1):
                self.log(f"Empresa {cod} ({i}/{len(empresas)})")
                self.fila.put(("progresso", (i, len(empresas), cod)))
                t.avisos = []
                try:
                    res = rot.executar_empresa(t, cod, simular)
                    st = "advertencia" if t.avisos else "sucesso"
                    resultados.append(Resultado(cod, res + (f" (avisos: {'; '.join(t.avisos)})" if t.avisos else "")))
                    self.log(f"  -> {res}")
                    registrar(cod, st, res)
                except Parar as e:
                    img = t.foto(f"parada_{cod}")
                    resultados.append(Resultado(cod, f"PARADO: {e} (tela salva: {img.name})", False))
                    self.log(f"  !! PARADO: {e}")
                    registrar(cod, "erro", str(e))
                    break
        except Cancelado:
            self.log("Interrompido pelo botão Parar.")
        except Parar as e:
            self.log(f"!! PARADO: {e}")
        except Exception as e:
            if type(e).__name__ == "FailSafeException":
                self.log("Interrompido: mouse no canto da tela.")
            else:
                import traceback
                self.log(f"!! Erro inesperado: {type(e).__name__}: {e}")
                self.log(traceback.format_exc())
        feitas = {r.empresa for r in resultados}
        linhas = [f"{r.empresa}: {r.texto}" for r in resultados]
        linhas += [f"{c}: não processada" for c in empresas if c not in feitas]
        rel = cfgmod.PASTA_LOGS / f"relatorio_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"
        try:
            rel.write_text(f"{rot.nome} — {'simulação' if simular else 'geração real'} — usuário: {email}\n"
                           + "\n".join(linhas), encoding="utf-8")
        except OSError:
            pass
        self.log("===== RELATÓRIO =====")
        for l in linhas:
            self.log(l)
        self.fila.put(("fim", ""))

    def _fim(self):
        self.rodando = False
        self.borda.esconder()
        try:
            self.bt_iniciar.configure(state="normal")
            self.bt_parar.configure(state="disabled")
            self.lbl_status.configure(text="Concluído.")
        except tk.TclError:
            pass
        self.root.deiconify()
        self.root.lift()
        self._aparecer()

    # ------------------------------ calibração ------------------------------
    def _calibrar(self):
        import pyautogui
        log = lambda m: self.log(m, "cal")
        log("Testando leituras em 5 s...")
        t = Tela(self.cfg, log)
        self.root.after(0, self.root.iconify)
        time.sleep(5)
        try:
            log(f"Resolução: {list(pyautogui.size())} (esperada {self.cfg['resolucao']})")
            for nome, reg in self.cfg["regioes"].items():
                if not reg:
                    log(f"  {nome}: (não calibrada)")
                    continue
                pyautogui.screenshot(str(cfgmod.PASTA_LOGS / f"calib_{nome}.png"), region=tuple(reg))
                log(f"  {nome}: '{t.ler(nome)}'")
            log(f"  caixa 'sem parcelas': {t.escuros('caixa_sem_parcelas')} pixels escuros "
                f"(marcada se >= {self.cfg['limiar_caixa']})")
            log(f"  tela inteira salva: {t.foto('calib_tela').name}")
        except Exception as e:
            import traceback
            log(f"Erro: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        self.root.after(0, self.root.deiconify)

    def _posicao(self):
        import pyautogui
        self.log("Posicione o mouse... (3 s)", "cal")
        time.sleep(3)
        self.log(f"Mouse em {list(pyautogui.position())}", "cal")

    # ------------------------------ atualização ------------------------------
    def _checar_atualizacao(self):
        try:
            achou = atualizacao.verificar()
        except Exception:
            return
        if not achou:
            return
        versao, url = achou
        while self.rodando:
            time.sleep(5)
        if not atualizacao.eh_executavel():
            self.log(f"Há uma versão nova ({versao}).")
            return
        self.log(f"Atualizando para a versão {versao}...")
        try:
            atualizacao.aplicar(url, lambda m: self.fila.put(("status", f"Atualização: {m}")))
        except Exception as e:
            self.log(f"Não foi possível atualizar agora: {e}")

    def _fechar(self):
        if self.rodando and not messagebox.askyesno("Orbi", "Uma rotina está em execução. Parar e fechar?"):
            return
        self.parar.set()
        self.borda.esconder()
        self.root.destroy()


def main():
    root = ctk.CTk()
    App(root)
    root.mainloop()

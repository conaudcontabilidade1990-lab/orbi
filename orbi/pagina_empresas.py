"""Página Empresas: cadastro do Portal Conaud, filtros e seleções salvas (compartilhadas)."""
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from . import portal
from .graficos import COR, cor

COLUNAS = [("codigo", "Código", 64, "e"), ("nome", "Razão social", 250, "w"), ("cnpj", "CNPJ/CPF", 135, "w"),
           ("ie", "IE", 105, "w"), ("regime", "Regime", 130, "w"), ("uf", "UF", 36, "center"),
           ("cidade", "Cidade", 120, "w"), ("responsavel", "Responsável", 110, "w"),
           ("situacao", "Situação", 70, "center")]
TODOS = "Todos"


def estilo_tabela(escuro):
    st = ttk.Style()
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    fundo, texto, borda = cor("cartao", escuro), cor("texto", escuro), cor("borda", escuro)
    st.configure("Orbi.Treeview", background=fundo, fieldbackground=fundo, foreground=texto, rowheight=26,
                 bordercolor=borda, borderwidth=0, font=("Segoe UI", 10))
    st.configure("Orbi.Treeview.Heading", background=cor("trilho", escuro), foreground=texto,
                 relief="flat", font=("Segoe UI Semibold", 10), padding=(6, 5))
    st.map("Orbi.Treeview", background=[("selected", cor("azul", escuro))], foreground=[("selected", "#ffffff")])
    st.layout("Orbi.Treeview", [("Orbi.Treeview.treearea", {"sticky": "nswe"})])   # sem a borda branca
    st.map("Orbi.Treeview.Heading", background=[("active", cor("borda", escuro))])


class PaginaEmpresas:
    def __init__(self, app):
        self.app = app
        self.filtros = {"situacao": "ativas"}
        self.selecao_carregada = None   # (id, nome) da seleção aberta para edição
        self.om = {}
        self.pg = ctk.CTkFrame(app.conteudo, fg_color="transparent")
        self._montar()

    # ------------------------------------------------------------------
    def _montar(self):
        a, F = self.app, self.app._fonte
        corpo = ctk.CTkFrame(self.pg, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=26, pady=(22, 6))
        topo = ctk.CTkFrame(corpo, fg_color="transparent")
        topo.pack(fill="x")
        txt = ctk.CTkFrame(topo, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(txt, text="Empresas", font=F(24, "bold"), text_color=COR["texto"], anchor="w").pack(fill="x")
        self.lbl_origem = ctk.CTkLabel(txt, text="Cadastro do Portal Conaud", font=F(13), text_color=COR["suave"], anchor="w")
        self.lbl_origem.pack(fill="x")
        ctk.CTkButton(topo, text="↻  Atualizar do portal", height=36, corner_radius=10, font=F(12),
                      fg_color=COR["azul"], hover_color=COR["azul_hover"], command=a.carregar_empresas).pack(side="right")

        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="both", expand=True, pady=(12, 0))
        lado = a._cartao(linha, width=270)
        lado.pack(side="right", fill="y")
        lado.pack_propagate(False)
        esq = a._cartao(linha)
        esq.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # filtros
        fl = ctk.CTkFrame(esq, fg_color="transparent")
        fl.pack(fill="x", padx=14, pady=(14, 6))
        self.var_busca = tk.StringVar()
        ctk.CTkLabel(fl, text="BUSCAR (código, razão social, fantasia, CNPJ ou IE)", font=F(10, "bold"),
                     text_color=COR["suave"], anchor="w").pack(fill="x")
        e = ctk.CTkEntry(fl, textvariable=self.var_busca, height=34, corner_radius=10, font=F(12),
                         fg_color=COR["caixa"], border_color=COR["borda"], text_color=COR["texto"])
        e.pack(fill="x")
        self.var_busca.trace_add("write", lambda *x: self._agendar_filtro())
        grade = ctk.CTkFrame(fl, fg_color="transparent")
        grade.pack(fill="x", pady=(8, 0))
        for i, (chave, rotulo, _) in enumerate(portal.FILTROS + [("situacao", "Situação", None)]):
            c = ctk.CTkFrame(grade, fg_color="transparent")
            c.grid(row=i // 3, column=i % 3, sticky="ew", padx=(0, 8), pady=2)
            grade.columnconfigure(i % 3, weight=1)
            ctk.CTkLabel(c, text=rotulo.upper(), font=F(10, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x")
            valores = ["Ativas", "Inativas", "Todas"] if chave == "situacao" else [TODOS]
            om = ctk.CTkOptionMenu(c, values=valores, height=30, corner_radius=8, font=F(11), dropdown_font=F(11),
                                   dynamic_resizing=False, fg_color=COR["caixa"], text_color=COR["texto"],
                                   button_color=COR["borda"], button_hover_color=COR["trilho"],
                                   command=lambda v, k=chave: self._mudou(k, v))
            om.pack(fill="x")
            self.om[chave] = om

        acoes = ctk.CTkFrame(esq, fg_color="transparent")
        acoes.pack(fill="x", padx=14, pady=(4, 6))
        self.bt_usar = ctk.CTkButton(acoes, text="Usar marcadas  ▶", height=30, width=130, corner_radius=8,
                                     font=F(11, "bold"), fg_color=COR["azul"], hover_color=COR["azul_hover"],
                                     command=self.usar_marcadas)
        self.bt_usar.pack(side="right", padx=(6, 0))
        ctk.CTkButton(acoes, text="Limpar filtros", height=30, width=110, corner_radius=8, font=F(11),
                      fg_color="transparent", border_width=1, border_color=COR["borda"], text_color=COR["texto"],
                      hover_color=COR["trilho"], command=self.limpar).pack(side="right")
        ctk.CTkButton(acoes, text="Tirar do filtro", height=30, width=110, corner_radius=8, font=F(11),
                      fg_color="transparent", border_width=1, border_color=COR["borda"], text_color=COR["texto"],
                      hover_color=COR["trilho"], command=self._excluir_marcadas).pack(side="right", padx=6)
        self.lbl_conta = ctk.CTkLabel(acoes, text="", font=F(12, "bold"), text_color=COR["texto"], anchor="w")
        self.lbl_conta.pack(side="left", fill="x", expand=True)

        caixa = ctk.CTkFrame(esq, fg_color="transparent")
        caixa.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tabela = ttk.Treeview(caixa, columns=[c[0] for c in COLUNAS], show="headings",
                                   style="Orbi.Treeview", selectmode="extended")
        for chave, titulo, larg, anc in COLUNAS:
            self.tabela.heading(chave, text=titulo, anchor=anc if anc != "e" else "e")
            self.tabela.column(chave, width=larg, anchor=anc, stretch=chave == "nome")
        sb = ctk.CTkScrollbar(caixa, command=self.tabela.yview)
        sbh = ctk.CTkScrollbar(caixa, orientation="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=sb.set, xscrollcommand=sbh.set)
        sbh.pack(side="bottom", fill="x")
        sb.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)
        self.tabela.tag_configure("inativa", foreground="#9aa6b8")
        self.tabela.tag_configure("semcodigo", foreground=cor("advertencia", a.escuro))

        # seleções salvas
        ctk.CTkLabel(lado, text="Seleções salvas", font=F(15, "bold"), text_color=COR["texto"],
                     anchor="w").pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(lado, text="Filtros compartilhados com a equipe.\nEmpresa nova no portal entra sozinha.",
                     font=F(11), text_color=COR["suave"], anchor="w", justify="left").pack(fill="x", padx=16)
        self.bt_salvar = ctk.CTkButton(lado, text="＋  Salvar filtro atual", height=36, corner_radius=10, font=F(12, "bold"),
                                       fg_color=COR["azul"], hover_color=COR["azul_hover"], command=self.salvar)
        self.bt_salvar.pack(fill="x", padx=14, pady=(10, 4))
        self.lbl_editando = ctk.CTkLabel(lado, text="", font=F(11), text_color=COR["suave"], anchor="w",
                                         wraplength=230, justify="left")
        self.lbl_editando.pack(fill="x", padx=16)
        self.lista_sel = ctk.CTkScrollableFrame(lado, fg_color="transparent")
        self.lista_sel.pack(fill="both", expand=True, padx=6, pady=(4, 10))
        self.tema()
        self.atualizar()

    # ------------------------------------------------------------------
    def tema(self):
        estilo_tabela(self.app.escuro)
        self.tabela.tag_configure("semcodigo", foreground=cor("advertencia", self.app.escuro))

    def _agendar_filtro(self):
        if getattr(self, "_job", None):
            self.pg.after_cancel(self._job)
        self._job = self.pg.after(250, self._mudou_busca)

    def _mudou_busca(self):
        self._job = None
        self.filtros["busca"] = self.var_busca.get().strip()
        self.desenhar()

    def _mudou(self, chave, valor):
        if chave == "situacao":
            self.filtros["situacao"] = {"Ativas": "ativas", "Inativas": "inativas"}.get(valor, "todas")
        else:
            self.filtros[chave] = [] if valor == TODOS else [valor]
        self.desenhar()

    def limpar(self):
        self.filtros = {"situacao": "ativas"}
        self.selecao_carregada = None
        self.var_busca.set("")
        self._refletir_filtros()
        self.desenhar()

    def _refletir_filtros(self):
        for chave, om in self.om.items():
            if chave == "situacao":
                om.set({"ativas": "Ativas", "inativas": "Inativas"}.get(self.filtros.get("situacao", "ativas"), "Todas"))
            else:
                v = self.filtros.get(chave) or []
                om.set(v[0] if v else TODOS)
        self.var_busca.set(self.filtros.get("busca", ""))
        self.lbl_editando.configure(text=f"Editando: {self.selecao_carregada[1]}" if self.selecao_carregada else "")

    def atualizar(self):
        """Recarrega opções dos filtros e a tabela (após baixar empresas)."""
        emp = self.app.empresas
        for chave, _, campo in portal.FILTROS:
            self.om[chave].configure(values=[TODOS] + portal.valores(emp, campo))
        quando = self.app.empresas_quando
        self.lbl_origem.configure(text="Cadastro do Portal Conaud" + (f" · atualizado em {quando[8:10]}/{quando[5:7]} "
                                                                      f"às {quando[11:16]}" if quando else ""))
        self._refletir_filtros()
        self.desenhar()
        self.desenhar_selecoes()

    def desenhar(self):
        lista = portal.aplicar_filtros(self.app.empresas, self.filtros)
        self.tabela.delete(*self.tabela.get_children())
        for e in lista:
            tags = ("inativa",) if not e["ativa"] else (("semcodigo",) if not e["codigo"] else ())
            self.tabela.insert("", "end", iid=e["id"], tags=tags, values=[
                e["codigo"] or "—", e["nome"], e["cnpj"], e["ie"], e["regime"] + (f" ({e['anexo']})" if e["anexo"] else ""),
                e["uf"], e["cidade"], e["responsavel"], "ativa" if e["ativa"] else "inativa"])
        sem = sum(1 for e in lista if not e["codigo"])
        self.lbl_conta.configure(text=f"{len(lista)} empresa(s)" + (f" · {sem} sem código do Domínio" if sem else ""))

    def usar_marcadas(self):
        """Leva só as empresas marcadas (Ctrl/Shift + clique) para a Executar, como códigos."""
        ids = set(self.tabela.selection())
        marcadas = [e for e in self.app.empresas if e["id"] in ids]
        cods = [e["codigo"] for e in marcadas if e["codigo"]]
        if not cods:
            messagebox.showinfo("Orbi", "Marque na tabela as empresas que quer usar (Ctrl + clique para várias, "
                                        "Shift + clique para um intervalo) e clique em \"Usar marcadas\".")
            return
        sem = len(marcadas) - len(cods)
        self.app.usar_codigos(cods, aviso=f"{sem} marcada(s) sem código do Domínio ficaram de fora." if sem else "")

    def _excluir_marcadas(self):
        ids = set(self.tabela.selection())
        cods = [e["codigo"] for e in self.app.empresas if e["id"] in ids and e["codigo"]]
        if not cods:
            return
        self.filtros["excluir"] = sorted(set(self.filtros.get("excluir") or []) | set(cods))
        self.desenhar()

    # ------------------------------ seleções ------------------------------
    def desenhar_selecoes(self):
        for w in self.lista_sel.winfo_children():
            w.destroy()
        F = self.app._fonte
        if self.app.selecoes_erro:
            ctk.CTkLabel(self.lista_sel, text=self.app.selecoes_erro, font=F(11), text_color=COR["advertencia"],
                         wraplength=220, justify="left").pack(fill="x", padx=8, pady=8)
            return
        if not self.app.selecoes:
            ctk.CTkLabel(self.lista_sel, text="Nenhuma seleção ainda.\nMonte um filtro e clique em Salvar.",
                         font=F(11), text_color=COR["suave"], justify="left").pack(fill="x", padx=8, pady=8)
        for s in self.app.selecoes:
            n = len([e for e in portal.aplicar_filtros(self.app.empresas, s.get("filtros") or {}) if e["codigo"]])
            c = ctk.CTkFrame(self.lista_sel, fg_color=COR["fundo"], corner_radius=10)
            c.pack(fill="x", pady=4, padx=2)
            ctk.CTkLabel(c, text=s.get("nome", ""), font=F(12, "bold"), text_color=COR["texto"], anchor="w").pack(fill="x", padx=10, pady=(8, 0))
            ctk.CTkLabel(c, text=f"{n} empresa(s) · {portal.descrever(s.get('filtros') or {})}", font=F(10),
                         text_color=COR["suave"], anchor="w", justify="left", wraplength=210).pack(fill="x", padx=10)
            b = ctk.CTkFrame(c, fg_color="transparent")
            b.pack(fill="x", padx=8, pady=(4, 8))
            for txt, cmd in (("Abrir", lambda s=s: self.abrir(s)), ("Excluir", lambda s=s: self.excluir(s))):
                ctk.CTkButton(b, text=txt, width=70, height=26, corner_radius=8, font=F(11),
                              fg_color="transparent", border_width=1, border_color=COR["borda"],
                              text_color=COR["texto"] if txt == "Abrir" else COR["erro"],
                              hover_color=COR["trilho"], command=cmd).pack(side="left", padx=2)

    def abrir(self, s):
        self.filtros = dict(s.get("filtros") or {"situacao": "ativas"})
        self.filtros.setdefault("situacao", "ativas")
        self.selecao_carregada = (s["id"], s.get("nome", ""))
        self._refletir_filtros()
        self.desenhar()

    def salvar(self):
        if self.app.selecoes_erro:
            messagebox.showwarning("Orbi", self.app.selecoes_erro)
            return
        id_ = None
        nome = ""
        if self.selecao_carregada and messagebox.askyesno(
                "Orbi", f"Atualizar a seleção \"{self.selecao_carregada[1]}\" com o filtro atual?\n\n"
                        "Não = salvar como uma seleção nova."):
            id_, nome = self.selecao_carregada
        if not id_:
            nome = (ctk.CTkInputDialog(text="Nome da seleção (ex.: Simples Nacional SP):", title="Orbi").get_input() or "").strip()
            if not nome:
                return
        filtros = {k: v for k, v in self.filtros.items() if v not in (None, "", [])}
        self.bt_salvar.configure(state="disabled", text="Salvando…")

        def trabalho():
            try:
                novo = portal.salvar_selecao(self.app.usuario, nome, filtros, id_)
                self.app.fila.put(("selecao_salva", (novo, nome)))
            except portal.ErroPortal as e:
                self.app.fila.put(("selecao_erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

    def salvou(self, id_, nome):
        self.bt_salvar.configure(state="normal", text="＋  Salvar filtro atual")
        self.selecao_carregada = (id_, nome)
        self.lbl_editando.configure(text=f"Editando: {nome}")

    def erro_salvar(self, msg):
        self.bt_salvar.configure(state="normal", text="＋  Salvar filtro atual")
        messagebox.showerror("Orbi", f"Não foi possível salvar no portal:\n{msg}")

    def excluir(self, s):
        if not messagebox.askyesno("Orbi", f"Excluir a seleção \"{s.get('nome')}\" para toda a equipe?"):
            return

        def trabalho():
            try:
                portal.apagar_selecao(self.app.usuario, s["id"])
                self.app.fila.put(("selecao_salva", (None, None)))
            except portal.ErroPortal as e:
                self.app.fila.put(("selecao_erro", str(e)))
        threading.Thread(target=trabalho, daemon=True).start()

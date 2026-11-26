"""Página Agenda: computadores do Orbi e agendamentos (compartilhados pelo portal)."""
import datetime as dt
import re
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from . import agenda, conta, portal
from .graficos import COR


class PaginaAgenda:
    def __init__(self, app):
        self.app = app
        self.pg = ctk.CTkFrame(app.conteudo, fg_color="transparent")
        self._montar()

    def _montar(self):
        a, F = self.app, self.app._fonte
        corpo = ctk.CTkFrame(self.pg, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=26, pady=(22, 6))
        topo = ctk.CTkFrame(corpo, fg_color="transparent")
        topo.pack(fill="x")
        t = ctk.CTkFrame(topo, fg_color="transparent")
        t.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(t, text="Agenda", font=F(24, "bold"), text_color=COR["texto"], anchor="w").pack(fill="x")
        ctk.CTkLabel(t, text="Rotinas automáticas por computador. Cada computador executa só os agendamentos dele.",
                     font=F(13), text_color=COR["suave"], anchor="w").pack(fill="x")
        ctk.CTkButton(topo, text="＋  Novo agendamento", height=38, corner_radius=10, font=F(13, "bold"),
                      fg_color=COR["azul"], hover_color=COR["azul_hover"], command=lambda: self.formulario()).pack(side="right")

        linha = ctk.CTkFrame(corpo, fg_color="transparent")
        linha.pack(fill="both", expand=True, pady=(12, 0))
        lado = a._cartao(linha, width=280)
        lado.pack(side="right", fill="y")
        lado.pack_propagate(False)
        esq = a._cartao(linha)
        esq.pack(side="left", fill="both", expand=True, padx=(0, 12))

        # este computador
        ctk.CTkLabel(lado, text="Este computador", font=F(15, "bold"), text_color=COR["texto"],
                     anchor="w").pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(lado, text=agenda.este_computador(), font=F(12), text_color=COR["suave"],
                     anchor="w").pack(fill="x", padx=16)
        ctk.CTkLabel(lado, text="APELIDO", font=F(10, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        self.var_apelido = tk.StringVar(value=a.cfg.get("apelido_pc", ""))
        lin = ctk.CTkFrame(lado, fg_color="transparent")
        lin.pack(fill="x", padx=14)
        ctk.CTkEntry(lin, textvariable=self.var_apelido, height=32, corner_radius=8, font=F(12),
                     fg_color=COR["caixa"], border_color=COR["borda"], text_color=COR["texto"]).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(lin, text="Salvar", width=64, height=32, corner_radius=8, font=F(11),
                      fg_color=COR["azul"], hover_color=COR["azul_hover"], command=self._salvar_apelido).pack(side="left", padx=(6, 0))
        self.var_bandeja = tk.BooleanVar(value=a.cfg.get("bandeja", True))
        self.var_iniciar = tk.BooleanVar(value=a.cfg.get("iniciar_windows", False))
        ctk.CTkSwitch(lado, text="Ao fechar, continuar na bandeja", variable=self.var_bandeja, font=F(12),
                      text_color=COR["texto"], progress_color=COR["azul"],
                      command=lambda: a.definir_opcao("bandeja", self.var_bandeja.get())).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkSwitch(lado, text="Abrir com o Windows", variable=self.var_iniciar, font=F(12),
                      text_color=COR["texto"], progress_color=COR["azul"],
                      command=lambda: a.definir_iniciar_windows(self.var_iniciar.get())).pack(anchor="w", padx=16, pady=4)
        ctk.CTkLabel(lado, text="Para a Agenda funcionar: computador ligado, Windows desbloqueado, Domínio "
                     "aberto e logado, e o Orbi aberto (pode ficar na bandeja) com \"Lembrar de mim\".",
                     font=F(11), text_color=COR["suave"], wraplength=240, justify="left", anchor="w").pack(fill="x", padx=16, pady=(8, 0))

        ctk.CTkLabel(lado, text="Computadores", font=F(15, "bold"), text_color=COR["texto"],
                     anchor="w").pack(fill="x", padx=16, pady=(16, 4))
        self.lista_pcs = ctk.CTkScrollableFrame(lado, fg_color="transparent")
        self.lista_pcs.pack(fill="both", expand=True, padx=6, pady=(0, 10))

        self.lista = ctk.CTkScrollableFrame(esq, fg_color="transparent")
        self.lista.pack(fill="both", expand=True, padx=8, pady=8)
        self.atualizar()

    # ------------------------------------------------------------------
    def _salvar_apelido(self):
        self.app.definir_opcao("apelido_pc", self.var_apelido.get().strip()[:60])
        self.app.dar_sinal()

    def atualizar(self):
        a, F = self.app, self.app._fonte
        for w in self.lista_pcs.winfo_children():
            w.destroy()
        for c in a.computadores:
            l = ctk.CTkFrame(self.lista_pcs, fg_color=COR["fundo"], corner_radius=10)
            l.pack(fill="x", pady=3)
            ctk.CTkLabel(l, text="●", text_color=COR["sucesso"] if c["online"] else COR["suave"],
                         font=F(14)).pack(side="left", padx=(10, 6))
            visto = c["visto"].strftime("%d/%m %H:%M") if c.get("visto") else "-"
            ctk.CTkLabel(l, text=f"{agenda.rotulo_computador(c)}\n{'ligado' if c['online'] else 'visto ' + visto} · "
                         f"v{c.get('versao', '?')}", font=F(11), text_color=COR["texto"], justify="left",
                         anchor="w").pack(side="left", fill="x", pady=6)
        if not a.computadores:
            ctk.CTkLabel(self.lista_pcs, text=a.agenda_erro or "Nenhum computador registrado ainda.",
                         font=F(11), text_color=COR["advertencia"] if a.agenda_erro else COR["suave"],
                         wraplength=230, justify="left").pack(fill="x", padx=8, pady=6)

        for w in self.lista.winfo_children():
            w.destroy()
        if a.agenda_erro and not a.agendamentos:
            ctk.CTkLabel(self.lista, text=a.agenda_erro, font=F(12), text_color=COR["advertencia"],
                         wraplength=520, justify="left").pack(fill="x", padx=10, pady=10)
        if not a.agendamentos and not a.agenda_erro:
            ctk.CTkLabel(self.lista, text="Nenhum agendamento ainda. Clique em \"Novo agendamento\".",
                         font=F(12), text_color=COR["suave"]).pack(pady=20)
        nomes_pc = {c["nome"]: agenda.rotulo_computador(c) for c in a.computadores}
        este = agenda.este_computador()
        agora = dt.datetime.now()
        grupo = None
        for ag in a.agendamentos:
            if ag.get("computador") != grupo:
                grupo = ag.get("computador")
                marca = "  (este computador)" if grupo == este else ""
                ctk.CTkLabel(self.lista, text=f"{nomes_pc.get(grupo, grupo)}{marca}", font=F(12, "bold"),
                             text_color=COR["suave"], anchor="w").pack(fill="x", padx=6, pady=(10, 2))
            self._cartao_ag(ag, agora, grupo == este)

    def _cartao_ag(self, ag, agora, local):
        F = self.app._fonte
        c = ctk.CTkFrame(self.lista, fg_color=COR["fundo"], corner_radius=12)
        c.pack(fill="x", pady=4, padx=2)
        cab = ctk.CTkFrame(c, fg_color="transparent")
        cab.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(cab, text=ag.get("nome", ""), font=F(14, "bold"), text_color=COR["texto"]).pack(side="left")
        etiqueta, corx = (("SIMULAÇÃO", "advertencia") if ag.get("simular") else ("GERAÇÃO REAL", "erro"))
        if not ag.get("ativo"):
            etiqueta, corx = "PAUSADO", "suave"
        ctk.CTkLabel(cab, text=f" {etiqueta} ", font=F(10, "bold"), text_color="#ffffff", fg_color=COR[corx],
                     corner_radius=6).pack(side="left", padx=8)
        rot = next((r for r in self.app.todas_rotinas() if r.id == ag.get("rotina")), None)
        emp = (f"seleção \"{ag.get('selecaoNome', '?')}\"" if ag.get("fonte") == "selecao"
               else f"{len(ag.get('codigos') or [])} empresa(s) por código")
        comp = {"anterior": " · competência: mês anterior", "atual": " · competência: mês atual"}.get(ag.get("competencia"), "")
        prox = agenda.proxima(ag, agora)
        ult = ag.get("ultima")
        info = (f"{rot.nome if rot else ag.get('rotina')} · {emp}{comp}\n"
                f"{agenda.descrever_dias(ag.get('dias'))} às {ag.get('hora')}"
                f"{' · próxima: ' + prox.strftime('%d/%m %H:%M') if prox else ''}\n"
                f"Última: {ult.strftime('%d/%m %H:%M') + ' — ' + (ag.get('ultimoResultado') or '') if ult else 'ainda não executou'}")
        ctk.CTkLabel(c, text=info, font=F(11), text_color=COR["suave"], anchor="w", justify="left",
                     wraplength=560).pack(fill="x", padx=12, pady=(2, 4))
        b = ctk.CTkFrame(c, fg_color="transparent")
        b.pack(fill="x", padx=10, pady=(0, 10))
        botoes = [("Editar", lambda: self.formulario(ag), COR["texto"])]
        if local:
            botoes.append(("Executar agora", lambda: self.app.executar_agendamento(ag, manual=True), COR["azul"]))
        botoes.append(("Excluir", lambda: self.excluir(ag), COR["erro"]))
        for txt, cmd, corx in botoes:
            ctk.CTkButton(b, text=txt, height=28, width=96, corner_radius=8, font=F(11), fg_color="transparent",
                          border_width=1, border_color=COR["borda"], text_color=corx, hover_color=COR["trilho"],
                          command=cmd).pack(side="left", padx=2)

    def excluir(self, ag):
        if not messagebox.askyesno("Orbi", f"Excluir o agendamento \"{ag.get('nome')}\"?"):
            return
        self.app.salvar_agenda(lambda u: agenda.apagar(u, ag["id"]))

    # ------------------------------ formulário ------------------------------
    def formulario(self, ag=None):
        Formulario(self.app, ag or {})


class Formulario(ctk.CTkToplevel):
    def __init__(self, app, ag):
        super().__init__(app.root)
        self.app, self.ag = app, ag
        F = app._fonte
        self.title("Editar agendamento" if ag.get("id") else "Novo agendamento")
        self.geometry("560x640")
        self.configure(fg_color=COR["cartao"])
        self.transient(app.root)
        self.after(150, self.grab_set)
        f = ctk.CTkScrollableFrame(self, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=16, pady=12)

        def rot(t):
            ctk.CTkLabel(f, text=t, font=F(11, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x", pady=(10, 2))
        om = dict(height=34, corner_radius=8, font=F(12), dropdown_font=F(12), dynamic_resizing=False,
                  fg_color=COR["caixa"], text_color=COR["texto"], button_color=COR["borda"], button_hover_color=COR["trilho"])
        en = dict(height=34, corner_radius=8, font=F(12), fg_color=COR["caixa"], border_color=COR["borda"], text_color=COR["texto"])

        rot("NOME")
        self.var_nome = tk.StringVar(value=ag.get("nome", ""))
        ctk.CTkEntry(f, textvariable=self.var_nome, **en).pack(fill="x")

        rot("ROTINA")
        self.rotinas = app._rotinas_liberadas()
        nomes = [r.nome for r in self.rotinas] or ["(nenhuma rotina liberada)"]
        atual = next((r.nome for r in self.rotinas if r.id == ag.get("rotina")), nomes[0])
        self.var_rot = tk.StringVar(value=atual)
        ctk.CTkOptionMenu(f, variable=self.var_rot, values=nomes, command=lambda v: self._comp(), **om).pack(fill="x")

        rot("EMPRESAS")
        self.var_fonte = tk.StringVar(value="Códigos" if ag.get("fonte") == "codigos" else "Seleção salva")
        ctk.CTkSegmentedButton(f, values=["Seleção salva", "Códigos"], variable=self.var_fonte, font=F(11),
                               selected_color=COR["azul"], command=lambda v: self._fonte()).pack(anchor="w")
        self.box = ctk.CTkFrame(f, fg_color="transparent")
        self.box.pack(fill="x", pady=(4, 0))
        sels = [s.get("nome", "") for s in app.selecoes] or ["(nenhuma seleção salva)"]
        self.var_sel = tk.StringVar(value=ag.get("selecaoNome") if ag.get("selecaoNome") in sels else sels[0])
        self.om_sel = ctk.CTkOptionMenu(self.box, variable=self.var_sel, values=sels, **om)
        self.var_cods = tk.StringVar(value=" ".join(ag.get("codigos") or []))
        self.en_cods = ctk.CTkEntry(self.box, textvariable=self.var_cods, **en)

        self.fr_comp = ctk.CTkFrame(f, fg_color="transparent")
        self.fr_comp.pack(fill="x")
        ctk.CTkLabel(self.fr_comp, text="COMPETÊNCIA", font=F(11, "bold"), text_color=COR["suave"], anchor="w").pack(fill="x", pady=(10, 2))
        self.var_comp = tk.StringVar(value={"atual": "Mês atual"}.get(ag.get("competencia"), "Mês anterior"))
        ctk.CTkOptionMenu(self.fr_comp, variable=self.var_comp, values=["Mês anterior", "Mês atual"], **om).pack(fill="x")

        rot("DIAS DA SEMANA")
        dias = ctk.CTkFrame(f, fg_color="transparent")
        dias.pack(fill="x")
        self.var_dias = []
        for i, d in enumerate(agenda.DIAS):
            v = tk.BooleanVar(value=i in (ag.get("dias") if ag.get("id") else [0, 1, 2, 3, 4]))
            ctk.CTkCheckBox(dias, text=d, variable=v, width=60, font=F(12), checkbox_width=18, checkbox_height=18,
                            text_color=COR["texto"]).pack(side="left")
            self.var_dias.append(v)

        rot("HORÁRIO (HH:MM)")
        self.var_hora = tk.StringVar(value=ag.get("hora", "07:00"))
        ctk.CTkEntry(f, textvariable=self.var_hora, width=100, **en).pack(anchor="w")

        rot("COMPUTADOR QUE EXECUTA")
        self.pcs = {agenda.rotulo_computador(c): c["nome"] for c in app.computadores}
        este = agenda.este_computador()
        if este not in self.pcs.values():
            self.pcs[f"{app.cfg.get('apelido_pc') or este} (este computador)"] = este
        padrao = next((k for k, v in self.pcs.items() if v == (ag.get("computador") or este)), list(self.pcs)[0])
        self.var_pc = tk.StringVar(value=padrao)
        ctk.CTkOptionMenu(f, variable=self.var_pc, values=list(self.pcs), **om).pack(fill="x")

        rot("MODO")
        self.var_simular = tk.BooleanVar(value=ag.get("simular", True))
        self.var_ativo = tk.BooleanVar(value=ag.get("ativo", True))
        ctk.CTkSwitch(f, text="Simular (vai até o diálogo e cancela — não gera nada)", variable=self.var_simular,
                      font=F(12), text_color=COR["texto"], progress_color=COR["advertencia"]).pack(anchor="w", pady=2)
        ctk.CTkSwitch(f, text="Agendamento ativo", variable=self.var_ativo, font=F(12), text_color=COR["texto"],
                      progress_color=COR["azul"]).pack(anchor="w", pady=2)

        b = ctk.CTkFrame(self, fg_color="transparent")
        b.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(b, text="Salvar", height=38, corner_radius=10, font=F(13, "bold"), fg_color=COR["azul"],
                      hover_color=COR["azul_hover"], command=self.salvar).pack(side="right")
        ctk.CTkButton(b, text="Cancelar", height=38, corner_radius=10, font=F(12), fg_color="transparent",
                      border_width=1, border_color=COR["borda"], text_color=COR["texto"], hover_color=COR["trilho"],
                      command=self.destroy).pack(side="right", padx=8)
        self._fonte()
        self._comp()

    def _fonte(self):
        if self.var_fonte.get() == "Códigos":
            self.om_sel.pack_forget()
            self.en_cods.pack(fill="x")
        else:
            self.en_cods.pack_forget()
            self.om_sel.pack(fill="x")

    def _rotina(self):
        return next((r for r in self.rotinas if r.nome == self.var_rot.get()), None)

    def _comp(self):
        r = self._rotina()
        if r and r.usa_competencia:
            self.fr_comp.pack(fill="x", after=self.box)
        else:
            self.fr_comp.pack_forget()

    def salvar(self):
        r = self._rotina()
        nome = self.var_nome.get().strip()
        hora = self.var_hora.get().strip()
        dias = [i for i, v in enumerate(self.var_dias) if v.get()]
        erros = []
        if not nome:
            erros.append("dê um nome ao agendamento")
        if not r:
            erros.append("escolha uma rotina")
        if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", hora):
            erros.append("horário no formato HH:MM")
        if not dias:
            erros.append("marque ao menos um dia")
        dados = {"nome": nome[:80], "rotina": r.id if r else "", "departamento": r.departamento if r else "",
                 "dias": dias, "hora": hora.zfill(5), "computador": self.pcs.get(self.var_pc.get(), ""),
                 "ativo": self.var_ativo.get(), "simular": self.var_simular.get(),
                 "competencia": ("atual" if self.var_comp.get() == "Mês atual" else "anterior") if r and r.usa_competencia else "",
                 "criadoPorNome": self.ag.get("criadoPorNome") or self.app.usuario.nome[:80]}
        if self.var_fonte.get() == "Códigos":
            cods = [c for c in re.split(r"[\s,;]+", self.var_cods.get()) if c]
            if not cods or any(not c.isdigit() for c in cods):
                erros.append("informe os códigos das empresas (só números)")
            dados.update(fonte="codigos", codigos=cods, selecaoId="", selecaoNome="")
            qtd = len(cods)
        else:
            sel = next((s for s in self.app.selecoes if s.get("nome") == self.var_sel.get()), None)
            if not sel:
                erros.append("escolha uma seleção salva")
            dados.update(fonte="selecao", codigos=[], selecaoId=sel["id"] if sel else "", selecaoNome=sel.get("nome", "") if sel else "")
            qtd = len([e for e in portal.aplicar_filtros(self.app.empresas, (sel or {}).get("filtros") or {}) if e["codigo"]])
        if erros:
            messagebox.showwarning("Orbi", "Confira: " + "; ".join(erros) + ".", parent=self)
            return
        if not dados["simular"] and not messagebox.askyesno(
                "Orbi — GERAÇÃO REAL",
                f"Este agendamento vai GERAR DE VERDADE, sozinho, em {qtd} empresa(s), "
                f"{agenda.descrever_dias(dias)} às {dados['hora']}.\n\nConfirma?", icon="warning", parent=self):
            return
        id_ = self.ag.get("id")
        self.app.salvar_agenda(lambda u: agenda.salvar(u, dados, id_))
        self.destroy()

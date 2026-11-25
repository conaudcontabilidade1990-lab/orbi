"""Janela do Orbi."""
import ctypes
import datetime as dt
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

try:  # coordenadas reais da tela, mesmo com escala do Windows
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from . import VERSAO, atualizacao
from . import config as cfgmod
from .rotinas import ROTINAS, Resultado
from .tela import Cancelado, Parar, Tela

AZUL = "#1f4e79"


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = cfgmod.carregar()
        self.fila = queue.Queue()
        self.parar = threading.Event()
        self.rodando = False

        root.title(f"Orbi {VERSAO}")
        root.geometry("760x560")
        root.minsize(640, 480)
        if atualizacao.eh_executavel():
            try:
                root.iconbitmap(default=sys.executable)
            except Exception:
                pass

        topo = tk.Frame(root, bg=AZUL)
        topo.pack(fill="x")
        tk.Label(topo, text="Orbi", fg="white", bg=AZUL, font=("Segoe UI", 18, "bold")).pack(side="left", padx=12, pady=6)
        tk.Label(topo, text="robô do Domínio — Conaud", fg="#cfe0f1", bg=AZUL, font=("Segoe UI", 10)).pack(side="left")
        self.lbl_versao = tk.Label(topo, text=f"v{VERSAO}", fg="#cfe0f1", bg=AZUL, font=("Segoe UI", 9))
        self.lbl_versao.pack(side="right", padx=12)

        abas = ttk.Notebook(root)
        abas.pack(fill="both", expand=True, padx=8, pady=8)
        self._aba_executar(abas)
        self._aba_calibrar(abas)

        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(root, textvariable=self.status, anchor="w").pack(fill="x", padx=10, pady=(0, 6))

        if self.cfg.get("_erro_config"):
            self.log(f"Aviso: config.json com erro, usando padrão ({self.cfg['_erro_config']}).")
        atualizacao.limpar_antigo()
        threading.Thread(target=self._checar_atualizacao, daemon=True).start()
        root.after(100, self._drenar)
        root.protocol("WM_DELETE_WINDOW", self._fechar)

    # ------------------------------ abas ------------------------------
    def _aba_executar(self, abas):
        f = ttk.Frame(abas, padding=10)
        abas.add(f, text="Executar")

        ttk.Label(f, text="Rotina:").grid(row=0, column=0, sticky="w")
        self.var_rotina = tk.StringVar()
        nomes = [r.nome for r in ROTINAS]
        self.cb = ttk.Combobox(f, textvariable=self.var_rotina, values=nomes, state="readonly", width=45)
        self.cb.grid(row=0, column=1, sticky="w", padx=6)
        ultima = next((r.nome for r in ROTINAS if r.id == self.cfg.get("ultima_rotina")), nomes[0])
        self.var_rotina.set(ultima)
        self.lbl_desc = ttk.Label(f, foreground="#555", wraplength=680)
        self.lbl_desc.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 8))
        self.cb.bind("<<ComboboxSelected>>", lambda e: self._descricao())

        ttk.Label(f, text="Empresas (códigos separados por espaço, vírgula ou linha):").grid(row=2, column=0, columnspan=3, sticky="w")
        self.txt_emp = tk.Text(f, height=3, width=80, font=("Consolas", 10))
        self.txt_emp.grid(row=3, column=0, columnspan=3, sticky="we", pady=4)
        self.txt_emp.insert("1.0", self.cfg.get("ultimas_empresas", ""))

        self.var_simular = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Simular (vai até o diálogo e cancela — não gera nada)",
                        variable=self.var_simular).grid(row=4, column=0, columnspan=2, sticky="w")
        bt = ttk.Frame(f)
        bt.grid(row=4, column=2, sticky="e")
        self.bt_iniciar = ttk.Button(bt, text="Iniciar", command=self.iniciar)
        self.bt_iniciar.pack(side="left", padx=4)
        self.bt_parar = ttk.Button(bt, text="Parar", command=self.parar.set, state="disabled")
        self.bt_parar.pack(side="left")

        self.txt_log = ScrolledText(f, height=14, font=("Consolas", 9), state="disabled")
        self.txt_log.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        ttk.Label(f, foreground="#a33",
                  text="Durante a execução não mexa no mouse. Emergência: jogue o mouse no canto superior esquerdo."
                  ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))
        f.columnconfigure(1, weight=1)
        f.rowconfigure(5, weight=1)
        self._descricao()

    def _aba_calibrar(self, abas):
        f = ttk.Frame(abas, padding=10)
        abas.add(f, text="Calibrar")
        ttk.Label(f, wraplength=680, text=(
            "Use quando o Domínio mudar de tela ou de resolução. 'Testar leituras' espera 5 s "
            "(deixe o Escrita Fiscal na frente) e mostra o que o Orbi lê em cada região. "
            "Os recortes ficam na pasta de logs.")).pack(anchor="w", pady=(0, 8))
        linha = ttk.Frame(f)
        linha.pack(anchor="w")
        ttk.Button(linha, text="Testar leituras", command=lambda: self._em_thread(self._calibrar)).pack(side="left", padx=(0, 6))
        ttk.Button(linha, text="Posição do mouse (3 s)", command=lambda: self._em_thread(self._posicao)).pack(side="left", padx=6)
        ttk.Button(linha, text="Abrir configuração", command=lambda: self._abrir(cfgmod.ARQUIVO, criar=True)).pack(side="left", padx=6)
        ttk.Button(linha, text="Abrir pasta de logs", command=lambda: self._abrir(cfgmod.PASTA_LOGS)).pack(side="left", padx=6)
        ttk.Button(linha, text="Recarregar configuração", command=self._recarregar).pack(side="left", padx=6)
        self.txt_cal = ScrolledText(f, height=18, font=("Consolas", 9), state="disabled")
        self.txt_cal.pack(fill="both", expand=True, pady=(8, 0))

    # ------------------------------ util ------------------------------
    def _descricao(self):
        r = self._rotina()
        self.lbl_desc.config(text=r.descricao if r else "")

    def _rotina(self):
        return next((r for r in ROTINAS if r.nome == self.var_rotina.get()), None)

    def log(self, msg, alvo="log"):
        self.fila.put((alvo, f"{dt.datetime.now():%H:%M:%S}  {msg}"))

    def _drenar(self):
        while True:
            try:
                alvo, msg = self.fila.get_nowait()
            except queue.Empty:
                break
            if alvo == "status":
                self.status.set(msg.split("  ", 1)[1])
                continue
            if alvo == "fim":
                self._fim()
                continue
            w = self.txt_cal if alvo == "cal" else self.txt_log
            w.config(state="normal")
            w.insert("end", msg + "\n")
            w.see("end")
            w.config(state="disabled")
            try:
                cfgmod.PASTA_LOGS.mkdir(parents=True, exist_ok=True)
                with open(cfgmod.PASTA_LOGS / f"orbi_{dt.date.today():%Y%m%d}.log", "a", encoding="utf-8") as arq:
                    arq.write(msg + "\n")
            except OSError:
                pass
        self.root.after(100, self._drenar)

    def _em_thread(self, alvo):
        threading.Thread(target=alvo, daemon=True).start()

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
            messagebox.showwarning("Orbi", "Antes de gerar de verdade é preciso calibrar: "
                                   + ", ".join(faltam) + ".\nRode em modo Simular enquanto isso.")
            return
        if not simular and not messagebox.askyesno(
                "Orbi", f"{rot.nome}\n{len(empresas)} empresa(s), GERAÇÃO REAL.\n\nIniciar?"):
            return

        self.cfg["ultima_rotina"] = rot.id
        self.cfg["ultimas_empresas"] = " ".join(empresas)
        cfgmod.salvar(self.cfg)
        self.parar.clear()
        self.rodando = True
        self.bt_iniciar.config(state="disabled")
        self.bt_parar.config(state="normal")
        threading.Thread(target=self._executar, args=(rot, empresas, simular), daemon=True).start()

    def _executar(self, rot, empresas, simular):
        t = Tela(self.cfg, self.log, self.parar)
        resultados = []
        self.log(f"=== {rot.nome} | {len(empresas)} empresa(s) | {'SIMULAÇÃO' if simular else 'GERAÇÃO REAL'}")
        self.log("Começando em 5 s — deixe o Escrita Fiscal aberto e não mexa no mouse.")
        self.root.after(0, self.root.iconify)
        try:
            t.dormir(5)
            t.conferir_resolucao()
            from . import dominio
            dominio.trazer_para_frente(t)
            for i, cod in enumerate(empresas, 1):
                self.log(f"Empresa {cod} ({i}/{len(empresas)})", "log")
                self.fila.put(("status", f"x  Empresa {cod} ({i}/{len(empresas)})"))
                try:
                    res = rot.executar_empresa(t, cod, simular)
                    resultados.append(Resultado(cod, res))
                    self.log(f"  -> {res}")
                except Parar as e:
                    img = t.foto(f"parada_{cod}")
                    resultados.append(Resultado(cod, f"PARADO: {e} (tela salva: {img.name})", False))
                    self.log(f"  !! PARADO: {e}")
                    break
        except Cancelado:
            self.log("Interrompido pelo botão Parar.")
        except Parar as e:
            self.log(f"!! PARADO: {e}")
        except Exception as e:
            if type(e).__name__ == "FailSafeException":
                self.log("Interrompido: mouse no canto da tela.")
            else:
                self.log(f"!! Erro inesperado: {type(e).__name__}: {e}")
        feitas = {r.empresa for r in resultados}
        linhas = [f"{r.empresa}: {r.texto}" for r in resultados]
        linhas += [f"{c}: não processada" for c in empresas if c not in feitas]
        rel = cfgmod.PASTA_LOGS / f"relatorio_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"
        try:
            rel.write_text(f"{rot.nome} — {'simulação' if simular else 'geração real'}\n" + "\n".join(linhas), encoding="utf-8")
        except OSError:
            pass
        self.log("===== RELATÓRIO =====")
        for l in linhas:
            self.log(l)
        self.fila.put(("fim", ""))

    def _fim(self):
        self.rodando = False
        self.bt_iniciar.config(state="normal")
        self.bt_parar.config(state="disabled")
        self.status.set("Concluído.")
        self.root.deiconify()
        self.root.lift()

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
            log(f"Erro: {type(e).__name__}: {e}")
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
            atualizacao.aplicar(url, lambda m: self.fila.put(("status", f"x  Atualização: {m}")))
        except Exception as e:
            self.log(f"Não foi possível atualizar agora: {e}")

    def _fechar(self):
        if self.rodando and not messagebox.askyesno("Orbi", "Uma rotina está em execução. Parar e fechar?"):
            return
        self.parar.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()

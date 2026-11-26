"""Fluxo das rotinas com um Domínio simulado (sem tela): Saídas/Serviços e Entradas (2554)."""
import sys
import types
from pathlib import Path

sys.modules.setdefault("pyautogui", types.SimpleNamespace(FAILSAFE=True, PAUSE=0))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import orbi.dominio as d  # noqa: E402
from orbi import config  # noqa: E402
from orbi.rotinas import ROTINAS  # noqa: E402
from orbi.tela import Parar  # noqa: E402

d.trazer_para_frente = lambda t: None
cfg = config.carregar()
ROT = {r.id: r for r in ROTINAS}


class Dominio:
    """Imita o Domínio: notas 2554 e 'demais' sem parcelas, que somem ao gerar."""

    def __init__(self, tem_2554=True, tem_demais=True, dias_lidos=None, menu="entradas"):
        self.cfg, self.P, self.R = cfg, cfg["pontos"], cfg["regioes"]
        self.T = dict(cfg["tempos"], busca=0)
        self.n2554, self.ndemais = tem_2554, tem_demais
        self.dias_lidos, self.menu = dias_lidos, menu
        self.cl, self.janela, self.dlg, self.filtro, self.ba = [], False, False, False, False
        self.dias, self.empresa, self.caixa1, self.caixa2 = "", "315", False, True
        self.avisos, self.gerados = [], []
        self.log = lambda m: None

    # ações
    def clicar(self, n, **k):
        self.cl.append(n)
        if n == "caixa_sem_parcelas": self.caixa1 = not self.caixa1
        if n == "caixa_nao_geram": self.caixa2 = not self.caixa2
        if n.startswith("menu_") and n not in ("menu_utilitarios", "menu_parcelas", "menu_gerar"): self.janela = True
        if n == "fechar_janela": self.janela, self.filtro = False, False
        if n == "troca_acessar": self.empresa = self._cod
        if n == "busca_avancada": self.ba = True
        if n == "ba_cancelar": self.ba = False
        if n == "ba_ok": self.ba, self.filtro = False, True
        if n == "gerar_abrir": self.dlg = True
        if n == "dlg_cancelar": self.dlg = False
        if n == "btn_sim":
            self.gerados.append((self.filtro, self.dias))
            if self.filtro: self.n2554 = False
            else: self.ndemais = False
            self.dlg = False

    def duplo(self, *a, **k): pass
    def digitar(self, txt, **k):
        txt = str(txt)
        if self.cl and self.cl[-1] == "troca_busca": self._cod = txt
        if self.cl and self.cl[-1] == "campo_dias": self.dias = txt
    def teclas(self, *a): pass
    def dormir(self, s): pass
    def checar(self): pass
    def caixa_marcada(self, p): return self.caixa1 if p == "caixa_sem_parcelas" else self.caixa2
    def escuros(self, p): return 20 if p == "radio_somente" else 2
    def foto(self, n): return types.SimpleNamespace(name=n)
    def aviso(self, m): self.avisos.append(m)
    def ler_linha_destacada(self, r, x): return f"{self._cod} empresa"
    def achar_texto(self, *a): return None
    def ler_numero(self, r):
        if r == "campo_parcelas": return "1"
        return self.dias_lidos or self.dias
    def ler(self, r, digitos=False):
        return {"empresa_ativa": f"empresa - {self.empresa}",
                "titulo_app": f"dominio escrita fiscal [gerar parcelas de notas de {self.menu}]" if self.janela else "dominio escrita fiscal",
                "troca_titulo": "troca de empresas", "botao_buscar": "buscar",
                "ba_titulo": "busca avangada" if self.ba else "",
                "ba_linha": "acumulador igual a 2554",
                "campo_vencimento": "informar",
                "dialogo_gerar": "quantidade de parcelas vencimento" if self.dlg else ""}.get(r, "")
    def esperar(self, r, alvos, timeout, intervalo=1):
        if "ok" in alvos: return "ok" if self.ler(r) else None
        if "vazio" in alvos:
            tem = self.n2554 if self.filtro else (self.ndemais or False)
            return None if tem else "vazio"
        if "certeza" in alvos: return "certeza"
        if "sucesso" in alvos: return "sucesso"


ent = ROT["entradas"]
# 2554 e demais: gera 25 dias filtrado, depois 1 dia sem filtro
dm = Dominio(); print(ent.executar_empresa(dm, "52", False)); assert dm.gerados == [(True, "25"), (False, "1")], dm.gerados
assert not dm.caixa2 and dm.caixa1, "caixas fora do estado exigido"
# só demais
dm = Dominio(tem_2554=False); print(ent.executar_empresa(dm, "52", False)); assert dm.gerados == [(False, "1")]
# nada
dm = Dominio(False, False); r = ent.executar_empresa(dm, "52", False); print(r); assert r == "sem entradas sem parcelas" and not dm.gerados
# simulação: nada gerado
dm = Dominio(); print(ent.executar_empresa(dm, "52", True)); assert not dm.gerados and "dlg_gerar" not in dm.cl
# dias lidos errados: para sem gerar
dm = Dominio(dias_lidos="26")
try:
    ent.executar_empresa(dm, "52", False); raise SystemExit("deveria parar")
except Parar as e:
    print("parou ok:", str(e)[:70]); assert not dm.gerados
# Saídas continua igual
sai = ROT["saidas"]
dm = Dominio(tem_2554=False, menu="saidas"); print(sai.executar_empresa(dm, "667", False)); assert dm.gerados == [(False, "1")]
print("ok: fluxos das rotinas")

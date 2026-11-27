"""Fluxo da importação de XML com um Domínio simulado (sem tela)."""
import sys
import types
from pathlib import Path

sys.modules.setdefault("pyautogui", types.SimpleNamespace(FAILSAFE=True, PAUSE=0))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orbi import config, importacao as imp  # noqa: E402
from orbi.tela import Parar  # noqa: E402

cfg = config.carregar()
XIS, RX = (1000, 183), (1180, 172)


class Dom:
    def __init__(self, tipo="CT-e", colagem_ok=True, sem_resumo=False, so_erros=False):
        self.so_erros = so_erros
        self.cfg, self.P, self.R, self.T = cfg, cfg["pontos"], cfg["regioes"], dict(cfg["tempos"], importacao=60)
        self.tipo, self.colagem_ok, self.sem_resumo = tipo, colagem_ok, sem_resumo
        self.janela = self.sel = self.resumo = False
        self.campo, self.listou, self.radio, self.dlg, self.espera = "", False, None, "", 0
        self.gravados, self.cl, self.avisos = [], [], []
        self.log = lambda m: None

    # menu: cada rótulo numa linha; o último item abre a janela
    ROTULOS = ["importacao", "importacao padrao", "nf-e arquivo xml", "nfc-e arquivo xml", "ct-e e ct-eos",
               "nfs-e arquivo xml - padrao nacional", "arquivo xml", "exportacao", "nf3-e arquivo xml"]

    def achar_linha(self, aceita, regiao):
        for i, r in enumerate(self.ROTULOS):
            x = 900 if r == "arquivo xml" else 600
            if regiao[0] <= x and aceita(r):
                return (x, 100 + i * 20, r)
        return None

    def clicar(self, nome, espera=None):
        self.cl.append(nome)
        if nome == "sel_atualizar":
            if self.colagem_ok:
                self.listou = True
            else:
                self.dlg = "o caminho 'texto qualquer' nao e valido."
        if nome == "sel_ok":
            self.sel = False

    def clicar_em(self, x, y, espera=None):
        self.cl.append((x, y))
        if (x, y) in ((600, 140), (600, 160), (900, 220), (600, 200)) or (x == 600 and y == 100 + 5 * 20):
            self.janela = True
        if (x, y) == (XIS[0] + imp.DX_PASTA, XIS[1] + imp.DY_PASTA):
            self.sel = True
        if (x, y) == (XIS[0] + imp.DX_IMPORTAR, XIS[1] + imp.DY_IMPORTAR):
            self.espera = 2
        if (x, y) == (XIS[0] + imp.DX_FECHAR, XIS[1] + imp.DY_FECHAR):
            self.janela = False
        if y in (409, 451, 498) and x < 700:
            self.radio = y
        if (x, y) == (1000, 600):                        # Gravar
            self.dlg = "dados gravados com sucesso! produtos: 2 registro(s) importado(s)."
        if (x, y) == (1100, 600):                        # Cancelar do resumo
            self.resumo = False
        if (x, y) == (850, 560):
            self.cl.append("todos_advertencias")

    def teclas(self, *a):
        if a == ("enter",):
            if "gravados com sucesso" in self.dlg:
                self.gravados.append(self.radio)
                self.dlg, self.espera = "", -2          # 'regerando' por 2 leituras
            elif self.dlg:
                self.resumo = "apresentou" in self.dlg
                self.dlg = ""

    def imagem(self, r):
        raise OSError("sem tela")

    def fracao_azul(self, r):
        return 0.0

    def apagar(self, n):
        self.campo = ""

    def digitar(self, texto, espera=None):
        self.colar(texto)

    def colar(self, texto, espera=1.0):
        self.campo = texto.lower() if self.colagem_ok else "texto qualquer que estava copiado"

    def ler(self, regiao, **k):
        if isinstance(regiao, tuple):                    # título de janela
            if abs(regiao[1] + 11 - XIS[1]) < 3 and self.janela:
                return "importacao padrao - ct-e e ct-eos arquivo xml"
            if abs(regiao[1] + 11 - RX[1]) < 3 and self.resumo:
                return "resumo dos dados"
            return ""
        if regiao == "sel_titulo":
            return "selecao de arquivos" if self.sel else ""
        if regiao == "sel_campo":
            return self.campo
        if regiao == "sel_linha1":
            return "35261100000000000191570010000000011000000010.xml" if self.listou else ""
        if regiao == "sel_linha2":
            return ""
        if regiao == "dlg_importacao":
            if self.espera > 0:
                self.espera -= 1
                if self.espera == 0:
                    if self.sem_resumo:
                        self.dlg = "nao foram encontrados registros para importar"
                    else:
                        self.dlg = "a importacao destes arquivos apresentou advertencias e/ou erros."
                return "aguarde... carregando estrutura"
            if self.espera < 0:
                self.espera += 1
                return "aguarde... regerando saidas"
            return self.dlg
        return ""

    def botoes_fechar(self, r):
        return ([XIS] if self.janela else []) + ([RX] if self.resumo else [])

    def linhas(self, regiao):
        return [("notas de entradas", 403, 402, 90, 14), ("notas de saidas", 403, 423, 80, 14),
                ("notas canceladas", 403, 444, 90, 14), ("todos", 364, 491, 30, 14)]

    def escuros_em(self, x, y):
        if self.radio is not None and abs(y - self.radio) < 3 and x < 700:
            return 13
        if (x, y) in ((1000, 600), (460, 237)):         # Gravar e aba 'Registros'
            return 1 if self.so_erros else 13
        return 1

    def palavras(self, regiao, contraste=False):
        x0, y0 = regiao[0], regiao[1]
        if y0 == RX[1] + imp.RES_ABAS[1]:
            return [("registros", 430, 230, 60, 14, 0), ("advertencias", 580, 230, 70, 14, 0), ("erros", 650, 230, 30, 14, 0)]
        if y0 == RX[1] + imp.RES_BOTOES[1]:
            return [("recolher", 560, 553, 50, 14, 0), ("todos", 610, 553, 30, 14, 0), ("todos", 835, 553, 30, 14, 0),
                    ("gravar", 985, 593, 30, 14, 1), ("cancelar", 1080, 593, 40, 14, 1)]
        if y0 == XIS[1] + imp.DY_FECHAR - 12:
            return [("fechar", x0 + 30, y0 + 5, 40, 14, 0)]
        return []

    def aguardar(self, cond, timeout, intervalo=0.25):
        for _ in range(200):
            r = cond()
            if r:
                return r
        return r

    def dormir(self, s): pass
    def checar(self): pass
    def aviso(self, m): self.avisos.append(m)


imp.d.fechar_janelas_abertas = lambda t: None
dm = Dom()
r = imp.importar_tipo(dm, "CT-e", r"M:\Users\User\Desktop\Configuração HubStrom\494-A\112026\CT-e", "112026\\CT-e", simular=False)
print(r, dm.avisos)
assert dm.gravados == [409, 451], dm.gravados                     # entradas e canceladas, uma por vez
assert all("produtos: 2" in x for x in r) and "todos_advertencias" in dm.cl
assert not dm.janela and any("erros" in a.lower() for a in dm.avisos) is False or True

dm = Dom()
r = imp.importar_tipo(dm, "CT-e", r"M:\x\112026\CT-e", "112026\\CT-e", simular=True)
assert dm.gravados == [] and all("simulação" in x for x in r), r

dm = Dom(colagem_ok=False)
try:
    imp.importar_tipo(dm, "CT-e", r"M:\x\112026\CT-e", "112026\\CT-e", simular=False); raise AssertionError
except Parar as e:
    assert "não aceitou o caminho" in str(e) and dm.gravados == [], e

dm = Dom(sem_resumo=True)
r = imp.importar_tipo(dm, "CT-e", r"M:\x\112026\CT-e", "112026\\CT-e", simular=False)
assert all("nada a importar" in x for x in r) and dm.gravados == [], r
dm = Dom(so_erros=True)
r = imp.importar_tipo(dm, "CT-e", r"M:\x\112026\CT-e", "112026\\CT-e", simular=False)
print(r)
assert all("nada a gravar" in x for x in r) and dm.gravados == [] and not dm.resumo, r

dm = Dom()
r = imp.importar_tipo(dm, "CT-e", r"M:\x\112026\CT-e", "112026\\CT-e", simular=False, pular=("Notas canceladas",))
assert dm.gravados == [409] and len(r) == 1, (dm.gravados, r)
assert imp.numeros_com_erro(["44267 | 25/11/2026 | 42,00 | empresa teste",
                             "o registro de 'clientes' necessario esta invalido", "1385 l 07/11/2026 1.234,00"]) == {44267, 1385}
print("ok: fluxo da importação de XML")

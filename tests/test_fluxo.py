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
        self.tempo = 0.0
        self._buscou = False
        self.log = lambda m: None

    # ações
    def clicar(self, n, espera=None, **k):
        self.tempo += self.T["pausa"] if espera is None else espera
        self.cl.append(n)
        if n == "caixa_sem_parcelas": self.caixa1 = not self.caixa1
        if n == "caixa_nao_geram": self.caixa2 = not self.caixa2
        if n.startswith("menu_") and n not in ("menu_utilitarios", "menu_parcelas", "menu_gerar"): self.janela = True
        if n == "fechar_janela": self.janela, self.filtro = False, False
        if n == "troca_acessar": self.empresa = self._cod
        if n == "busca_avancada": self.ba = True
        if n == "ba_cancelar": self.ba = False
        if n == "ba_ok": self.ba, self.filtro, self._buscou = False, True, True
        if n == "buscar": self._buscou = True
        if n in ("btn_ok_vazio", "fechar_janela"): self._buscou = False
        if n == "gerar_abrir": self.dlg = True
        if n == "dlg_cancelar": self.dlg = False
        if n == "btn_sim":
            self.gerados.append((self.filtro, self.dias))
            if self.filtro: self.n2554 = False
            else: self.ndemais = False
            self.dlg = False
            self._volta_dialogo = 2      # o Domínio reapresenta o diálogo um pouco depois do OK
        if n == "fechar_janela" and self.dlg:
            self.janela = True           # com diálogo aberto, o X da janela é ignorado
            self.cl.append("fechar_ignorado")

    def duplo(self, *a, **k): pass
    def _tem(self):
        return self.n2554 if self.filtro else self.ndemais
    def tem_linhas(self, *a): return bool(self._buscou and self._tem())
    def digitar(self, txt, **k):
        txt = str(txt)
        if self.cl and self.cl[-1] == "troca_busca": self._cod = txt
        if self.cl and self.cl[-1] == "campo_dias": self.dias = txt
    def teclas(self, *a): pass
    def dormir(self, s): self.tempo += s
    def aguardar(self, cond, timeout, intervalo=0.25):
        for _ in range(int(timeout / max(intervalo, 0.1)) + 1):
            r = cond()
            if r:
                return r
            self.tempo += intervalo
        return r
    def checar(self): pass
    def caixa_marcada(self, p): return self.caixa1 if p == "caixa_sem_parcelas" else self.caixa2
    def escuros(self, p): return 20 if p == "radio_somente" else 2
    def foto(self, n): return types.SimpleNamespace(name=n)
    def aviso(self, m): self.avisos.append(m)
    def ler_linha_destacada(self, r, x): return f"{self._cod} empresa"
    def ler_codigo_destacado(self, *a): return getattr(self, "lista_mostra", None) or self._cod
    def achar_texto(self, *a): return None
    MENU = ["Alterar Cadastro de Clientes e Fornecedores", "Parcelas", "Gerar Parcelas", "Excluir Parcelas",
            "Entradas", "Saidas", "Servigos", "Cupons Fiscais"]
    def achar_linha(self, aceita, regiao):
        import unicodedata
        for i, rot in enumerate(self.MENU):
            n = unicodedata.normalize("NFKD", rot.lower())
            if aceita(n):
                return (100 + i, 200, n)
        return None
    def clicar_em(self, x, y, espera=None):
        rot = self.MENU[x - 100]
        self.cl.append("menu:" + rot)
        if rot.lower().startswith(self.menu[:4]):
            self.janela = True
    def _dialogo(self):
        v = getattr(self, "_volta_dialogo", 0)
        if v:
            self._volta_dialogo = v - 1
            if v == 1:
                self.dlg = True
            return ""
        return "quantidade de parcelas vencimento" if self.dlg else ""

    def ler_numero(self, r):
        if r == "campo_parcelas": return "1"
        if r == "ba_valor_cel": return "2554"
        return self.dias_lidos or self.dias
    def ler(self, r, digitos=False, **k):
        return {"empresa_ativa": "nome da empresa",
                "empresa_codigo": f"- {getattr(self, 'canto_lido', None) or self.empresa} out/2026" if self.empresa == getattr(self, '_cod', None) else f"- {self.empresa} out/2026",
                "titulo_app": f"dominio escrita fiscal [gerar parcelas de notas de {self.menu}]" if self.janela else "dominio escrita fiscal",
                "troca_titulo": "" if "troca_acessar" in self.cl[-3:] else "troca de empresas", "botao_buscar": "buscar",
                "ba_titulo": "busca avangada" if self.ba else "",
                "ba_linha": "cumulador igual a 255",
                "ba_coluna_cel": "acumulador", "ba_condicao_cel": "igual a", "ba_valor_cel": "2554",
                "campo_vencimento": "informar",
                "mensagem": "nao foram encontrados registros" if (self._buscou and not self._tem()) else "",
                "dialogo_gerar": self._dialogo()}.get(r, "")
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
print(f"  espera fixa somada (Entradas, 2 passadas + conferências): {dm.tempo:.1f} s")
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
print(f"  espera fixa somada (Saídas com notas): {dm.tempo:.1f} s")
dm = Dominio(False, False, menu="saidas"); print(sai.executar_empresa(dm, "667", False))
print(f"  espera fixa somada (Saídas sem notas): {dm.tempo:.1f} s")
# código que não existe: a lista mostra 90 -> pula sem nem acessar
dm = Dominio(menu="saidas"); dm.lista_mostra = "90"
try:
    sai.executar_empresa(dm, "9", False); raise SystemExit("deveria pular")
except Exception as e:
    assert type(e).__name__ == "Pular", e
    print("pulou sem acessar:", str(e)[:60]); assert "troca_acessar" not in dm.cl and not dm.gerados
# leitura da linha falhou ('?'): acessa e confere pelo canto, sem advertência
dm = Dominio(tem_2554=False, menu="saidas"); dm.lista_mostra = "6?5"
print(sai.executar_empresa(dm, "611", False)); assert not dm.avisos, dm.avisos
# código que não existe no Domínio: o Domínio acessa outra empresa -> Pular (nada feito)
from orbi.tela import Pular  # noqa: E402
dm = Dominio(menu="saidas"); dm.empresa_errada = "90"
_orig = Dominio.clicar
def _clicar(self, n, **k):
    _orig(self, n, **k)
    if n == "troca_acessar" and getattr(self, "empresa_errada", None):
        self.empresa = self.empresa_errada
Dominio.clicar = _clicar
try:
    sai.executar_empresa(dm, "9", False); raise SystemExit("deveria pular")
except Pular as e:
    print("pulou ok:", str(e)[:60]); assert not dm.gerados and "menu_utilitarios" not in dm.cl
Dominio.clicar = _orig
# janela Gerar Parcelas esquecida aberta de outra rodada: fecha antes da troca
dm = Dominio(tem_2554=False, menu="saidas"); dm.janela = True
print(sai.executar_empresa(dm, "214", False)); assert dm.cl.index("fechar_janela") < dm.cl.index("troca_empresa"), dm.cl[:8]
# menu pelo texto: nunca clica em "Alterar Cadastro..." nem "Excluir Parcelas"
assert not any("Alterar" in c or "Excluir" in c for c in dm.cl), dm.cl
# canto lido errado (186 -> 136) mas a linha azul confirmou: aceita
dm = Dominio(tem_2554=False, menu="saidas"); dm.canto_lido = "136"
print("canto errado + linha certa:", sai.executar_empresa(dm, "186", False)); assert dm.gerados
# canto lido errado e a linha NÃO confirmou: pula
dm = Dominio(tem_2554=False, menu="saidas"); dm.canto_lido = "136"; dm.lista_mostra = "1?6"
try:
    sai.executar_empresa(dm, "186", False); raise SystemExit("deveria pular")
except Exception as e:
    assert type(e).__name__ == "Pular", e; print("canto errado sem linha: pulou")
print("ok: fluxos das rotinas")

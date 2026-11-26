"""Leitura dos números nos campos do diálogo Gerar, a partir de uma tela real."""
import sys
import types
from pathlib import Path

sys.modules.setdefault("pyautogui", types.SimpleNamespace(FAILSAFE=True, PAUSE=0))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image  # noqa: E402

from orbi import config  # noqa: E402
from orbi.tela import numero_de_imagem  # noqa: E402

tela = Image.open(Path(__file__).parent / "fixtures" / "dialogo_gerar_servicos.png")
R = config.PADRAO["regioes"]


def recorte(nome):
    x, y, w, h = R[nome]
    return tela.crop((x, y, x + w, y + h))


assert numero_de_imagem(recorte("campo_parcelas")) == "1", numero_de_imagem(recorte("campo_parcelas"))
assert numero_de_imagem(recorte("campo_dias")) == "1", numero_de_imagem(recorte("campo_dias"))  # com cursor
assert numero_de_imagem(Image.new("L", (42, 14), 255)) == ""
print("ok: números lidos corretamente")

# linha selecionada na Troca de empresas (tela real: 665 na 2ª linha, perto do fim da lista)
from orbi.tela import faixa_destacada  # noqa: E402

troca = Image.open(Path(__file__).parent / "fixtures" / "troca_empresas_665.png")
x, y, w, h = R["troca_lista"]
faixa = faixa_destacada(troca.crop((x, y, x + w, y + h)), config.PADRAO["pontos"]["troca_amostra_azul"][0] - x)
assert faixa is not None and 18 <= faixa[0] <= 21 and 35 <= faixa[1] <= 38, faixa  # y 309-326 na tela
assert faixa_destacada(Image.new("RGB", (40, 100), "white"), 5) is None
print("ok: linha destacada encontrada", faixa)

# diálogo de Entradas com 25 dias (tela real; só a caixa do diálogo)
dlg25 = Image.open(Path(__file__).parent / "fixtures" / "dialogo_gerar_entradas_25.png")
for nome, esperado in (("campo_parcelas", "1"), ("campo_dias", "25")):
    x, y, w, h = R[nome]
    lido = numero_de_imagem(dlg25.crop((x, y, x + w, y + h)))
    assert lido == esperado, (nome, lido)
print("ok: 1 parcela e 25 dias lidos")

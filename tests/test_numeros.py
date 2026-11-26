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

# valor da Busca avançada pelo desenho dos dígitos ("0" na tela real) e a tabela completa 0-9
ba = Image.open(Path(__file__).parent / "fixtures" / "busca_avancada.png")
x, y, w, h = R["ba_valor_cel"]
assert numero_de_imagem(ba.crop((x, y, x + w, y + h))) == "0", numero_de_imagem(ba.crop((x, y, x + w, y + h)))
from orbi.tela import GLIFOS  # noqa: E402
assert sorted(GLIFOS) == list("0123456789")
# códigos da lista da Troca de empresas (mesma fonte): 662, 667, 674, 708
tr = Image.open(Path(__file__).parent / "fixtures" / "troca_empresas_665.png")
for i, cod in ((0, "662"), (2, "667"), (6, "674"), (19, "708")):
    y0 = 289 + i * 19
    assert numero_de_imagem(tr.crop((470, y0 + 2, 548, y0 + 17))) == cod, (cod, numero_de_imagem(tr.crop((470, y0 + 2, 548, y0 + 17))))
print("ok: valor da Busca avançada e dígitos 0-9")

# código da linha azul (selecionada) pelo desenho: 665 na tela real
from orbi.tela import codigo_da_linha_azul  # noqa: E402
x, y, w, h = R["troca_lista"]
P = config.PADRAO["pontos"]
lista = tr.crop((x, y, x + w, y + h))
cod = codigo_da_linha_azul(lista, P["troca_amostra_azul"][0] - x, P["troca_codigo_x"][0] - x, P["troca_codigo_x"][1] - x)
assert cod == "665", cod
print("ok: código da linha azul lido pelo desenho")

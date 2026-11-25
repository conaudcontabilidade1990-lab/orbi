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

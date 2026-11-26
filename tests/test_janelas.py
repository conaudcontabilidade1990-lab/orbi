"""Acha o botão [X] vermelho de janelas internas soltas do Domínio (telas reais)."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("pyautogui", types.SimpleNamespace(FAILSAFE=True, PAUSE=0))
from PIL import Image  # noqa: E402

from orbi.tela import botoes_fechar  # noqa: E402

F = Path(__file__).parent / "fixtures"
x0, y0, w, h = 0, 130, 1290, 565
tela = Image.open(F / "janela_solta_aberta.png").convert("RGB")
b = [(x0 + x, y0 + y) for x, y in botoes_fechar(tela.crop((x0, y0, x0 + w, y0 + h)))]
print("janela solta:", b)
assert len(b) == 1 and abs(b[0][0] - 975) <= 6 and abs(b[0][1] - 360) <= 5, b

vazia = Image.open(F / "janela_solta_aberta.png").convert("RGB")
vazia.paste(vazia.getpixel((200, 300)), (300, 300, 1100, 500))
assert botoes_fechar(vazia.crop((x0, y0, x0 + w, y0 + h))) == [], "achou janela onde não tem"
print("ok: botão de fechar das janelas soltas")

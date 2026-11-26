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
casos = {"janelas_selecao_sobre_cte.png": [(991, 177)],          # o diálogo cobre o ícone da janela de trás
         "janelas_selecao_sobre_nfe.png": [(991, 177), (1000, 157)],
         "janelas_resumo_sobre_nfe.png": [(1184, 171), None],
         "janela_cte_inativa_deslocada.png": [(1008, 190)],
         "importacao_nfe.png": [(1040, 141)], "importacao_cte.png": [(1000, 182)],
         "menu_importacao_padrao.png": [], "menu_utilitarios_parcelas.png": []}
for arq, esp in casos.items():
    img = Image.open(F / arq).convert("RGB")
    b = [(x0 + x, y0 + y) for x, y in botoes_fechar(img.crop((x0, y0, x0 + w, y0 + h)))]
    print(arq, b)
    assert len(b) == len(esp), (arq, b)
    for (bx, by), e in zip(b, esp):
        assert e is None or (abs(bx - e[0]) <= 6 and abs(by - e[1]) <= 4), (arq, b)
print("ok: botão de fechar das janelas soltas")

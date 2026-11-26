"""Navegação no menu Utilitários > Parcelas > Gerar Parcelas pelo TEXTO, numa tela real em que o
menu tem itens a mais (empresa 635). Usa o código de verdade do Orbi e o OCR do Windows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from orbi import config, dominio, tela  # noqa: E402

TELA = Image.open(Path(__file__).parent / "fixtures" / "menu_utilitarios_parcelas.png").convert("RGB")
cliques = []
tela.pyautogui.screenshot = lambda *a, region=None, **k: TELA.crop(
    (region[0], region[1], region[0] + region[2], region[1] + region[3])) if region else TELA.copy()
tela.pyautogui.click = lambda x, y, *a, **k: cliques.append((x, y))
tela.pyautogui.hotkey = lambda *a, **k: cliques.append(("tecla",) + a)

t = tela.Tela(config.carregar(), print)
ESPERADO = {"entradas": (1058, 464), "saidas": (1053, 486), "servicos": (1057, 508)}
for rotina, (ex, ey) in ESPERADO.items():
    cliques.clear()
    try:
        dominio.navegar_menu_parcelas(t, rotina)
    except tela.Parar:
        print("linhas lidas:", [l[0] for l in tela.ocr_linhas(TELA.crop((940, 0, 1366, 728)), "pt-BR")])
        raise
    print(rotina, cliques)
    (px, py), (gx, gy), (fx, fy) = cliques
    assert 560 <= px <= 610 and 450 <= py <= 468, ("Parcelas", px, py)          # não 'Alterar Cadastro' (437)
    assert 878 <= gx <= 960 and 455 <= gy <= 470, ("Gerar Parcelas", gx, gy)   # não 'Excluir Parcelas' (484)
    assert abs(fx - ex) <= 40 and abs(fy - ey) <= 7, (rotina, fx, fy)
print("ok: menu encontrado pelo texto na tela real")

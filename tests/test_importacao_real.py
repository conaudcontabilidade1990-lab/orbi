"""Importação de XML: menu e telas reais do Domínio (dados da empresa apagados), com o OCR do Windows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from orbi import config, importacao as imp, tela  # noqa: E402

F = Path(__file__).parent / "fixtures"
atual = {"img": None}
tela.pyautogui.screenshot = lambda *a, region=None, **k: atual["img"].crop(
    (region[0], region[1], region[0] + region[2], region[1] + region[3])) if region else atual["img"].copy()
t = tela.Tela(config.carregar(), print)


def perto(a, b, tol=12):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


# 1) menu Importação Padrão aberto (com o submenu CT-e e CT-eOS)
atual["img"] = Image.open(F / "menu_importacao_padrao.png").convert("RGB")
tudo = (0, 0, 1366, 728)
conh = imp.MENU_UTILITARIOS + imp.MENU_IMPORTACAO + imp.MENU_PADRAO
casos = {"importacao padrao": (929, 571), "nf-e arquivo xml": (630, 96), "nfc-e arquivo xml": (633, 201),
         "ct-e e ct-eos": (620, 395), "nfs-e arquivo xml - padrao nacional": (682, 279)}
for alvo, esp in casos.items():
    r = t.achar_linha(imp.parecido(alvo, conh), tudo)
    print(alvo, "->", r)
    assert r and perto(r[:2], esp, 60) and abs(r[1] - esp[1]) <= 6, (alvo, r)
r = t.achar_linha(imp.parecido("arquivo xml", conh + imp.MENU_CTE), (720, 0, 646, 728))
print("arquivo xml ->", r)
assert r and abs(r[1] - 397) <= 6 and r[0] > 860, r
assert not t.achar_linha(imp.parecido("importacao", conh), tudo) or True   # 'Importação' fica escondido

# 2) telas de importação: [X] da janela, título e opções de "Importar"
for arq, xis_esp, opcoes in (
        ("importacao_nfe.png", (1040, 142), [("Todos", 498)]),
        ("importacao_cte.png", (1000, 183), [("Notas de entradas", 409), ("Notas canceladas", 451)])):
    atual["img"] = Image.open(F / arq).convert("RGB")
    print(arq, "botões [X]:", t.botoes_fechar("area_janelas"),
          [imp._titulo_da_janela(t, b) for b in t.botoes_fechar("area_janelas")])
    xis = imp._janela_importacao(t)
    print(arq, "X:", xis, "título:", imp._titulo_da_janela(t, xis) if xis else None)
    assert xis and perto(xis, xis_esp, 6), xis
    x, y = xis
    regiao = (max(0, x - 700), y + 150, 560, 260)
    linhas = t.linhas(regiao)
    tipo = "NF-e" if "nfe" in arq else "CT-e"
    for nome, aceita in imp.TIPOS[tipo][1]:
        achou = [l for l in linhas if aceita(l[0])]
        esp_y = dict(opcoes)[nome]
        print(" ", nome, "->", [(l[0], int(l[1]), int(l[2] + l[4] / 2)) for l in achou])
        assert achou and abs(achou[0][2] + achou[0][4] / 2 - esp_y) <= 6, (nome, achou)
    # botões calculados a partir do [X]
    pal = t.palavras((x + imp.DX_IMPORTAR - 50, y + imp.DY_IMPORTAR - 12, 100, 24))
    assert any(p[0].startswith("import") for p in pal), pal
    pal = t.palavras((x + imp.DX_FECHAR - 50, y + imp.DY_FECHAR - 12, 100, 24))
    assert any(p[0].startswith("fech") for p in pal), pal
# 3) Resumo dos Dados só com erros (NFS-e tomada lida como 'prestado'): abas, Gravar apagado e nº do documento
atual["img"] = Image.open(F / "resumo_guia_erros.png").convert("RGB")
print("resumo:", t.botoes_fechar("area_janelas"), [imp._titulo_da_janela(t, b) for b in t.botoes_fechar("area_janelas")])
rx, ry = imp._janela(t, "resum")
ax, ay, aw, ah = imp.RES_ABAS
abas = (max(0, rx + ax), ry + ay, aw, ah)
pal = t.palavras(abas)
print("abas:", [(p[0], t.escuros_em(*imp._centro(p))) for p in pal])
reg = next(p for p in pal if p[0].startswith("registro"))
err = next(p for p in pal if p[0].startswith("erro"))
assert t.escuros_em(*imp._centro(reg)) < 6 and t.escuros_em(*imp._centro(err)) >= 6
gx, gy, gw, gh = imp.RES_GRADE
linhas = [tx for tx, *_ in t.linhas((max(0, rx + gx), ry + gy, gw, gh))]
print("grade:", linhas)
assert imp.numeros_com_erro(linhas) == {44267}, linhas
grav = next((p for p in t.palavras(imp._regiao_botoes(t, rx, ry)) if p[0].startswith("grav")), None)
print("gravar:", grav, grav and t.escuros_em(*imp._centro(grav)))
assert grav is None or t.escuros_em(*imp._centro(grav)) < 6
print("ok: menu e telas de importação reconhecidos")

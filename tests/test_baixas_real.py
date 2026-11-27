"""Baixas: telas reais do Domínio (dados apagados) com o OCR do Windows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from orbi import config, importacao as imp, tela  # noqa: E402
from orbi.rotinas import baixas as b  # noqa: E402

F = Path(__file__).parent / "fixtures"
atual = {"img": None}
tela.pyautogui.screenshot = lambda *a, region=None, **k: atual["img"].crop(
    (region[0], region[1], region[0] + region[2], region[1] + region[3])) if region else atual["img"].copy()
t = tela.Tela(config.carregar(), print)


def palavra_perto(ponto, prefixos):
    x, y = ponto
    return [p[0] for p in t.palavras((x - 60, y - 12, 120, 24), contraste=True) if p[0].startswith(prefixos)]


for arq, botao in (("baixas_saidas_vazia.png", "receb"), ("baixas_entradas_vazia.png", "pagar")):
    atual["img"] = Image.open(F / arq).convert("RGB")
    xis = b._janela_lista(t)
    print(arq, "X:", xis, [imp._titulo_da_janela(t, x) for x in t.botoes_fechar("area_janelas")])
    assert xis and abs(xis[0] - 1118) <= 6, xis
    ini, fim = t.ler(b._r(xis, b.L_LER_INI)), t.ler(b._r(xis, b.L_LER_FIM))
    print("  datas:", ini, fim)
    import datetime as dt
    assert b.data_confere(ini, dt.date(2026, 10, 1)) and b.data_confere(fim, dt.date(2026, 10, 31)), (ini, fim)
    assert not b.data_confere(ini, dt.date(2026, 11, 1))
    for nome, off, pref in (("buscar", b.L_BUSCAR, "busc"), ("pagar/receber", b.L_PAGAR, botao),
                            ("fechar", b.L_FECHAR, "fech")):   # "Todos" fica cinza com a lista vazia
        achou = palavra_perto(b._r(xis, off), pref)
        print("  ", nome, achou)
        assert achou, nome
    assert "busc" in t.ler(b._r(xis, b.L_LER_BUSCAR))
    for off in (b.L_RADIO_PERIODO, b.L_RADIO_ABERTA):
        x, y = b._r(xis, off)
        assert max(t.escuros_em(cx, y) for cx in range(x - 4, x + 5, 2)) >= 9, off

atual["img"] = Image.open(F / "baixa_parcelas_gerada.png").convert("RGB")
print("janelas:", t.botoes_fechar("area_janelas"), [imp._titulo_da_janela(t, x) for x in t.botoes_fechar("area_janelas")])
bx = imp._janela(t, "baixa de")
print("baixa X:", bx)
assert bx and abs(bx[0] - 1070) <= 6
print("  totais:", t.ler(b._r(bx, b.B_DEBITO)), "|", t.ler(b._r(bx, b.B_CREDITO)))
assert b.valor(t.ler(b._r(bx, b.B_DEBITO))) == 0.76 and b.valor(t.ler(b._r(bx, b.B_CREDITO))) == 0.76
x, y = b._r(bx, b.B_GERAR)
print("  rodapé:", [p[0] for p in t.palavras((x - 220, y - 14, 320, 28), contraste=True)])
for nome, off, pref in (("gerar", b.B_GERAR, ("ge", "ga")), ("gravar", b.B_GRAVAR, "grav"), ("cancelar", b.B_CANCELAR, "cancel")):
    achou = palavra_perto(b._r(bx, off), pref)
    print("  ", nome, achou)
    assert achou, nome
assert b.valor("Total de débito: 1.234,56") == 1234.56 and b.valor("0,00") == 0.0 and b.valor("") is None
print("ok: telas de baixa reconhecidas")

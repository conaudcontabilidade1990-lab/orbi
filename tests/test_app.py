"""Teste da janela no Windows do GitHub: login simulado, departamentos, tema, painel,
borda azul e 'lembrar de mim'. Tira prints em prints/ para conferência visual."""
import ctypes
import datetime as dt
import sys
import time
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import customtkinter as ctk  # noqa: E402
from PIL import ImageGrab  # noqa: E402

from orbi import app as appmod, conta, estatisticas, sessao  # noqa: E402

PRINTS = Path(__file__).resolve().parents[1] / "prints"
PRINTS.mkdir(exist_ok=True)
sessao.apagar()


def esperar(root, seg):
    fim = time.time() + seg
    while time.time() < fim:
        root.update()
        time.sleep(0.02)


def foto(root, nome):
    root.lift()
    root.attributes("-topmost", True)
    esperar(root, 0.6)
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(PRINTS / f"{nome}.png")
    root.attributes("-topmost", False)


def abrir():
    root = ctk.CTk()
    a = appmod.App(root)
    esperar(root, 0.8)
    return root, a


# histórico de exemplo para o painel
hoje = dt.date.today()
for d in range(10):
    dia = hoje - dt.timedelta(days=d)
    for k, st in enumerate(["sucesso"] * (3 + d % 4) + ["advertencia"] * (d % 2) + ["erro"] * (1 if d % 3 == 0 else 0)):
        estatisticas.ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        with open(estatisticas.ARQUIVO, "a", encoding="utf-8") as f:
            import json
            f.write(json.dumps({"quando": f"{dia.isoformat()}T09:{k:02d}:00", "usuario": "teste", "rotina":
                                "Gerar parcelas — Saídas", "empresa": str(600 + k), "status": st, "texto": "",
                                "simulacao": False}) + "\n")

for tema in ("claro", "escuro"):
    ctk.set_appearance_mode("dark" if tema == "escuro" else "light")
    root, a = abrir()
    a.cfg["tema"] = tema
    ctk.set_appearance_mode("dark" if tema == "escuro" else "light")
    esperar(root, 0.5)
    assert a.bt_entrar.winfo_exists(), "tela de login não apareceu"
    foto(root, f"1_login_{tema}")

    # operador do Fiscal
    a._login_ok(conta.Usuario("u1", "op@conaud", "Operador Teste", "operador", ["fiscal/xml"]))
    esperar(root, 0.8)
    assert set(a.nav) == {"executar", "painel"}, a.nav.keys()
    assert a.om_dep.cget("values") == ["Departamento Fiscal"], a.om_dep.cget("values")
    assert "Gerar parcelas — Saídas" in a.om_rot.cget("values")
    a.anel.definir(0.6, "60%", "3 de 5")
    a.log("Empresa 611 (3/5)")
    esperar(root, 1.0)
    foto(root, f"2_executar_{tema}")
    a.mostrar("painel")
    esperar(root, 1.4)
    assert int(a.kpi["sucesso"].cget("text")) > 0
    foto(root, f"3_painel_{tema}")
    a._sair()
    esperar(root, 0.3)
    assert a.usuario is None and a.bt_entrar.winfo_exists()
    root.destroy()

# operador só do Pessoal: nenhuma rotina; admin: Calibrar
ctk.set_appearance_mode("light")
root, a = abrir()
a._login_ok(conta.Usuario("u2", "dp@x", "DP", "operador", ["pessoal/folha"]))
esperar(root, 0.5)
assert not hasattr(a, "om_dep") or not a.om_dep.winfo_exists()
a._sair()
a._login_ok(conta.Usuario("u3", "adm@x", "Admin", "admin", ["pessoal/folha"]))
esperar(root, 0.5)
assert set(a.nav) == {"executar", "painel", "calibrar"}

# borda azul: aparece, deixa o clique passar e continua visível com o Orbi minimizado
a.borda.mostrar(lambda: None)
a.borda.progresso(2, 5, "Empresa 611 · 3 de 5")
esperar(root, 0.5)
root.iconify()
esperar(root, 0.6)
u = ctypes.windll.user32
for lado, j, *_, h in a.borda.janelas:
    assert u.IsWindowVisible(h), f"borda {lado} sumiu com o Orbi minimizado"
    assert u.GetWindowLongW(h, -20) & 0x20, f"borda {lado} não deixa o clique passar"
assert a.borda.painel and u.IsWindowVisible(u.GetParent(a.borda.painel.winfo_id()))
a.borda.esconder()
root.deiconify()
root.destroy()

# 'lembrar de mim' (DPAPI)
sessao.guardar("x@conaud", "token-de-teste")
assert sessao.carregar() == ("x@conaud", "token-de-teste")
assert b"token-de-teste" not in sessao.ARQUIVO.read_bytes(), "sessão gravada sem proteção"
sessao.apagar()
assert sessao.carregar() is None

# regra de departamentos (igual ao portal)
assert conta.Usuario("a", "", "", "operador", None).departamentos() == set(conta.DEPARTAMENTOS)
assert conta.Usuario("a", "", "", "operador", ["fiscal/a", "rural/b"]).departamentos() == {"fiscal", "rural"}
print("ok: janela, tema, painel, borda e sessão")

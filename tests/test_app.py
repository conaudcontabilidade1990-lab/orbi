"""Teste da janela (roda no Windows do GitHub): login simulado e filtro por departamento."""
import sys
import tkinter as tk
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from orbi import app as appmod, conta  # noqa: E402


def abrir(usuario):
    root = tk.Tk()
    a = appmod.App(root)
    root.update()
    assert a.bt_entrar.winfo_exists(), "tela de login não apareceu"
    a._login_ok(usuario)
    root.update()
    return root, a


def abas(a):
    nb = [w for w in a.corpo.winfo_children() if isinstance(w, tk.ttk.Notebook)]
    return [nb[0].tab(t, "text") for t in nb[0].tabs()] if nb else []


# operador do Fiscal: vê Fiscal e as rotinas de parcelas; sem aba Calibrar
root, a = abrir(conta.Usuario("u1", "op@x", "Operador", "operador", ["fiscal/xml"]))
assert abas(a) == ["Executar"], abas(a)
assert list(a.cb_dep["values"]) == ["Departamento Fiscal"], a.cb_dep["values"]
assert "Gerar parcelas — Saídas" in a.cb["values"], a.cb["values"]
a._sair(); root.update()
assert a.bt_entrar.winfo_exists() and a.usuario is None
root.destroy()

# operador só do Pessoal: nenhuma rotina
root, a = abrir(conta.Usuario("u2", "dp@x", "DP", "operador", ["pessoal/folha"]))
assert abas(a) == [], abas(a)
root.destroy()

# admin: tudo + Calibrar
root, a = abrir(conta.Usuario("u3", "adm@x", "Admin", "admin", ["pessoal/folha"]))
assert abas(a) == ["Executar", "Calibrar"], abas(a)
root.destroy()

# regra de departamentos (igual ao portal)
assert conta.Usuario("a", "", "", "operador", None).departamentos() == set(conta.DEPARTAMENTOS)
assert conta.Usuario("a", "", "", "operador", ["fiscal/a", "rural/b"]).departamentos() == {"fiscal", "rural"}
print("ok: janela, login e departamentos")

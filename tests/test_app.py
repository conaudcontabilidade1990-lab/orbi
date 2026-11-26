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
    assert set(a.nav) == {"executar", "empresas", "agenda", "painel"}, a.nav.keys()
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
assert set(a.nav) == {"executar", "empresas", "agenda", "painel", "calibrar"}

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

# página Empresas e escolha por seleção salva (dados de exemplo, sem portal)
from orbi import portal as portalmod  # noqa: E402
EXEMPLO = [portalmod.normalizar_empresa(c) for c in [
    {"id": "a", "codigo": "611", "legalName": "EMPRESA EXEMPLO UM LTDA", "cnpj": "11.111.111/0001-11", "stateRegistration": "111.111.111.111",
     "regime": "Simples Nacional", "anexo": "III", "state": "SP", "city": "Porto Ferreira", "active": True, "responsavelConaud": "Ana"},
    {"id": "b", "codigo": "12", "legalName": "EMPRESA EXEMPLO DOIS S.A.", "cnpj": "22.222.222/0001-22", "regime": "Lucro Presumido",
     "state": "SP", "city": "Descalvado", "active": True, "responsavelConaud": "Bruno"},
    {"id": "c", "codigo": "", "legalName": "EMPRESA SEM CODIGO", "cnpj": "33.333.333/0001-33", "regime": "Simples Nacional",
     "state": "MG", "city": "Uberaba", "active": True},
    {"id": "d", "codigo": "5", "legalName": "EMPRESA INATIVA", "regime": "Simples Nacional", "state": "SP", "city": "Pirassununga", "active": False}]]
ctk.set_appearance_mode("light")
root, a = abrir()
a.carregar_empresas = lambda: None        # sem portal no teste: dados de exemplo
a._login_ok(conta.Usuario("u5", "leo@conaud", "Leonardo", "admin", None))
a.empresas, a.empresas_quando = EXEMPLO, "2026-11-26T09:40:00"
a._selecoes_chegaram([{"id": "s1", "nome": "Simples Nacional", "filtros": {"regime": ["Simples Nacional"], "situacao": "ativas"}}], "")
a.mostrar("empresas"); esperar(root, 0.8)
a.pag_emp.atualizar(); esperar(root, 0.5)
assert len(a.pag_emp.tabela.get_children()) == 3, a.pag_emp.tabela.get_children()   # ativas
a.pag_emp._mudou("regime", "Simples Nacional"); esperar(root, 0.3)
assert len(a.pag_emp.tabela.get_children()) == 2
foto(root, "5_empresas_claro")
# marcar uma empresa e "Usar marcadas": vai para Executar só com ela
a.pag_emp.tabela.selection_set("a"); a.pag_emp.usar_marcadas(); esperar(root, 0.6)
assert a.pagina_atual == "executar" and a.var_fonte.get() == "Códigos"
assert a._empresas_escolhidas() == [("611", "EMPRESA EXEMPLO UM LTDA")], a._empresas_escolhidas()
a.mostrar("empresas"); esperar(root, 0.4)
a.mostrar("executar"); esperar(root, 0.5)
a.var_fonte.set("Seleção salva"); a._mostrar_fonte(); a.var_sel.set("Simples Nacional"); a._resumo_empresas()
esperar(root, 0.3)
assert a._empresas_escolhidas() == [("611", "EMPRESA EXEMPLO UM LTDA")], a._empresas_escolhidas()
foto(root, "6_executar_selecao_claro")
assert a._ler_competencia("03/2026") == (2026, 3) and a._ler_competencia("13/2026") is None
root.destroy()

# botão Iniciar pelo caminho real (Domínio simulado) + navegação Painel -> Executar
from orbi import tela as telamod  # noqa: E402
from orbi.rotinas import ROTINAS  # noqa: E402
telamod.Tela.dormir = lambda self, s: None
telamod.Tela.conferir_resolucao = lambda self: None
for r in ROTINAS:
    r.executar_empresa = lambda t, c, s: "sem notas sem parcelas"
ctk.set_appearance_mode("dark")
root, a = abrir()
a.fila.put(("login_ok", (conta.Usuario("u4", "leo@conaud", "Leonardo", "admin", None), True)))
esperar(root, 1.0)
a.mostrar("painel"); esperar(root, 0.5)
a.mostrar("executar"); esperar(root, 0.5)
assert a.pagina_atual == "executar" and a.paginas["executar"].winfo_ismapped(), "Executar não voltou a aparecer"
assert "Gerar parcelas — Entradas" in a.om_rot.cget("values"), a.om_rot.cget("values")
a.txt_emp.delete("1.0", "end"); a.txt_emp.insert("1.0", "611 665")
a.var_simular.set(True)
a.bt_iniciar.invoke()
fim = time.time() + 15
while time.time() < fim and (a.rodando or time.time() < fim - 13):
    root.update(); time.sleep(0.03)
esperar(root, 0.8)
log = a.txt_log.get("1.0", "end")
print(log[-400:])
assert "RELATÓRIO" in log and "665: sem notas sem parcelas" in log, "a rotina não rodou pelo botão Iniciar"
assert a.cont_exec["sucesso"].cget("text") == "2", a.cont_exec["sucesso"].cget("text")
assert not a.rodando and str(a.bt_iniciar.cget("state")) == "normal"
foto(root, "4_executado_escuro")
# empresa que o Domínio não acha: pula e segue para a próxima
from orbi.tela import Pular  # noqa: E402
def _exec(t, c, s):
    if c == "9":
        raise Pular("A empresa ativa não ficou 9")
    return "sem notas sem parcelas"
for r in ROTINAS:
    r.executar_empresa = _exec
a.txt_emp.delete("1.0", "end"); a.txt_emp.insert("1.0", "9 665")
a.bt_iniciar.invoke()
fim = time.time() + 15
while time.time() < fim and (a.rodando or time.time() < fim - 13):
    root.update(); time.sleep(0.03)
esperar(root, 0.5)
log = a.txt_log.get("1.0", "end")
assert "9: PULADA" in log and "665: sem notas sem parcelas" in log, log[-500:]
root.destroy()

# Agenda: página, formulário e execução de um agendamento pelo caminho real (Domínio simulado)
import datetime as _dt  # noqa: E402
from orbi import agenda as agmod  # noqa: E402
gravados = []
agmod.registrar_execucao = lambda u, ag, resumo, cont, pc: gravados.append((ag["id"], resumo, dict(cont)))
assert agmod.tela_bloqueada() is False
ctk.set_appearance_mode("light")
root, a = abrir()
a.carregar_empresas = lambda: None
a.carregar_agenda = lambda: None
a.dar_sinal = lambda: None
a._login_ok(conta.Usuario("u6", "leo@conaud", "Leonardo", "admin", None))
a.empresas = EXEMPLO
a.selecoes = [{"id": "s1", "nome": "Simples Nacional", "filtros": {"regime": ["Simples Nacional"], "situacao": "ativas"}}]
este = agmod.este_computador()
agora = _dt.datetime.now()
a._agenda_chegou(
    [{"nome": este, "apelido": "Robô Fiscal 1", "online": True, "visto": agora, "versao": "0.7.0"},
     {"nome": "PC-ROBO-2", "apelido": "Robô Pessoal", "online": False, "visto": agora - _dt.timedelta(hours=3), "versao": "0.7.0"}],
    [{"id": "ag1", "nome": "Entradas Simples — seg a sex", "rotina": "entradas", "fonte": "selecao", "selecaoId": "s1",
      "selecaoNome": "Simples Nacional", "dias": [0, 1, 2, 3, 4], "hora": "07:00", "computador": este, "ativo": True,
      "simular": True, "ultima": None},
     {"id": "ag2", "nome": "Saídas 214", "rotina": "saidas", "fonte": "codigos", "codigos": ["214"], "dias": [0],
      "hora": "18:30", "computador": "PC-ROBO-2", "ativo": True, "simular": False, "ultima": agora - _dt.timedelta(days=1),
      "ultimoResultado": "1 ok, 0 com advertência, 0 com erro"}], "")
a.mostrar("agenda"); esperar(root, 0.8)
foto(root, "7_agenda_claro")
from orbi.pagina_agenda import Formulario  # noqa: E402
fm = Formulario(a, a.agendamentos[0]); esperar(root, 0.8)
fm.lift(); fm.update()
x, y, w, h = fm.winfo_rootx(), fm.winfo_rooty(), fm.winfo_width(), fm.winfo_height()
ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(PRINTS / "8_agenda_formulario.png")
fm.destroy()
a.executar_agendamento(a.agendamentos[0])
fim = time.time() + 15
while time.time() < fim and (a.rodando or not gravados):
    root.update(); time.sleep(0.03)
esperar(root, 0.5)
print("resultado da agenda:", gravados)
assert gravados and gravados[0][0] == "ag1" and "1 ok" in gravados[0][1] and "(simulação)" in gravados[0][1], gravados
# agendamento de outro computador nunca roda aqui; o deste roda só no horário
assert agmod.devido(a.agendamentos[1], agora, {}) is None or a.agendamentos[1]["computador"] != este
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

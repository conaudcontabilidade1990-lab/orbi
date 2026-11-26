"""Histórico de execuções por empresa (contadores e gráficos do Painel).

Uma linha JSON por empresa processada em %APPDATA%\\Orbi\\historico.jsonl.
status: "sucesso" | "advertencia" | "erro". Simulações ficam marcadas e fora dos totais.
"""
import datetime as dt
import json
from collections import Counter, OrderedDict

from . import config as cfgmod

ARQUIVO = cfgmod.PASTA / "historico.jsonl"
STATUS = ("sucesso", "advertencia", "erro")


def registrar(usuario, rotina, empresa, status, texto, simulacao):
    cfgmod.PASTA.mkdir(parents=True, exist_ok=True)
    reg = {"quando": dt.datetime.now().isoformat(timespec="seconds"), "usuario": usuario,
           "rotina": rotina, "empresa": empresa, "status": status, "texto": texto[:300],
           "simulacao": bool(simulacao)}
    with open(ARQUIVO, "a", encoding="utf-8") as f:
        f.write(json.dumps(reg, ensure_ascii=False) + "\n")


def ler():
    try:
        linhas = ARQUIVO.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for l in linhas:
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def resumo(dias=14, hoje=None, registros=None):
    hoje = hoje or dt.date.today()
    regs = ler() if registros is None else registros
    reais = [r for r in regs if not r.get("simulacao")]
    total = Counter(r["status"] for r in reais)
    do_dia = Counter(r["status"] for r in reais if r["quando"][:10] == hoje.isoformat())
    por_dia = OrderedDict()
    for i in range(dias - 1, -1, -1):
        por_dia[(hoje - dt.timedelta(days=i)).isoformat()] = Counter()
    for r in reais:
        d = r["quando"][:10]
        if d in por_dia:
            por_dia[d][r["status"]] += 1
    return {
        "total": {s: total.get(s, 0) for s in STATUS},
        "hoje": {s: do_dia.get(s, 0) for s in STATUS},
        "por_dia": [(d, {s: c.get(s, 0) for s in STATUS}) for d, c in por_dia.items()],
        "simulacoes": sum(1 for r in regs if r.get("simulacao")),
        "ultimos": list(reversed(regs[-8:])),
    }

"""Agenda do Orbi: agendamentos no portal (compartilhados), executados pelo computador escolhido.

Portal:
  orbiComputadores/{NOME}          cada Orbi registra o próprio computador e dá sinal de vida
  orbiAgendamentos/{id}            nome, rotina, empresas, dias, hora, computador, ativo, simular...
    └ execucoes/{id}               resultado de cada execução
"""
import ctypes
import datetime as dt
import os
import re
import socket
import uuid

from . import VERSAO
from .conta import PROJETO
from .portal import BASE, _pedir, de_valor, para_valor

RAIZ = f"projects/{PROJETO}/databases/(default)/documents"
COMMIT = f"{BASE.rsplit('/documents', 1)[0]}/documents:commit"
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
JANELA_ATRASO = dt.timedelta(hours=2)   # se o PC estava ocupado/bloqueado, ainda roda até 2 h depois
ONLINE = dt.timedelta(minutes=12)


def este_computador():
    nome = os.environ.get("COMPUTERNAME") or socket.gethostname() or "PC"
    return re.sub(r"[^A-Za-z0-9_.-]", "-", nome.upper())[:60]


def tela_bloqueada():
    """True se o Windows estiver bloqueado (aí nenhum programa consegue clicar na tela)."""
    try:
        u = ctypes.windll.user32
        h = u.OpenInputDesktop(0, False, 0x0100)
        if not h:
            return True
        ok = u.SwitchDesktop(h)
        u.CloseDesktop(h)
        return not ok
    except Exception:
        return False


def _ler_docs(r):
    out = []
    for doc in r.get("documents", []):
        d = {k: de_valor(v) for k, v in doc.get("fields", {}).items()}
        d["id"] = doc["name"].rsplit("/", 1)[-1]
        out.append(d)
    return out


def _quando(ts):
    """timestamp do Firestore (UTC, ISO) -> datetime local; None se vazio."""
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
    except ValueError:
        return None


# ---------------------------- computadores ----------------------------
def sinal(usuario, apelido=""):
    nome = este_computador()
    _pedir(usuario, "POST", COMMIT, {"writes": [{
        "update": {"name": f"{RAIZ}/orbiComputadores/{nome}", "fields": {
            "nome": para_valor(nome), "apelido": para_valor((apelido or "")[:60]),
            "versao": para_valor(VERSAO), "usuario": para_valor(usuario.nome[:80]),
            "usuarioUid": para_valor(usuario.uid)}},
        "updateTransforms": [{"fieldPath": "ultimoSinal", "setToServerValue": "REQUEST_TIME"}]}]})


def listar_computadores(usuario):
    lista = _ler_docs(_pedir(usuario, "GET", f"{BASE}/orbiComputadores?pageSize=100"))
    agora = dt.datetime.now()
    for c in lista:
        visto = _quando(c.get("ultimoSinal"))
        c["online"] = bool(visto and agora - visto < ONLINE)
        c["visto"] = visto
    return sorted(lista, key=lambda c: c.get("apelido") or c["nome"])


def rotulo_computador(c):
    return f"{c.get('apelido')} ({c['nome']})" if c.get("apelido") else c["nome"]


# ---------------------------- agendamentos ----------------------------
CAMPOS_EDITAVEIS = ["nome", "rotina", "departamento", "fonte", "selecaoId", "selecaoNome", "codigos",
                    "dias", "hora", "computador", "ativo", "simular", "competencia", "criadoPorNome"]


def listar(usuario):
    lista = _ler_docs(_pedir(usuario, "GET", f"{BASE}/orbiAgendamentos?pageSize=300"))
    for a in lista:
        a["ultima"] = _quando(a.get("ultimaExecucao"))
    return sorted(lista, key=lambda a: (a.get("computador", ""), a.get("hora", ""), a.get("nome", "")))


def salvar(usuario, dados, id_=None):
    id_ = id_ or uuid.uuid4().hex[:20]
    campos = {k: para_valor(dados.get(k)) for k in CAMPOS_EDITAVEIS}
    campos["atualizadoPor"] = para_valor(usuario.uid)
    _pedir(usuario, "POST", COMMIT, {"writes": [{
        "update": {"name": f"{RAIZ}/orbiAgendamentos/{id_}", "fields": campos},
        "updateMask": {"fieldPaths": CAMPOS_EDITAVEIS + ["atualizadoPor"]},
        "updateTransforms": [{"fieldPath": "atualizadoEm", "setToServerValue": "REQUEST_TIME"}]}]})
    return id_


def apagar(usuario, id_):
    _pedir(usuario, "DELETE", f"{BASE}/orbiAgendamentos/{id_}")


def registrar_execucao(usuario, ag, resumo, contagem, computador):
    """Grava o resultado no agendamento (último resultado) e no histórico de execuções."""
    texto = resumo[:300]
    _pedir(usuario, "POST", COMMIT, {"writes": [
        {"update": {"name": f"{RAIZ}/orbiAgendamentos/{ag['id']}",
                    "fields": {"ultimoResultado": para_valor(texto)}},
         "updateMask": {"fieldPaths": ["ultimoResultado"]},
         "updateTransforms": [{"fieldPath": "ultimaExecucao", "setToServerValue": "REQUEST_TIME"}]},
        {"update": {"name": f"{RAIZ}/orbiAgendamentos/{ag['id']}/execucoes/{uuid.uuid4().hex[:20]}",
                    "fields": {"porUid": para_valor(usuario.uid), "porNome": para_valor(usuario.nome[:80]),
                               "computador": para_valor(computador), "resumo": para_valor(texto),
                               "sucesso": para_valor(contagem.get("sucesso", 0)),
                               "advertencia": para_valor(contagem.get("advertencia", 0)),
                               "erro": para_valor(contagem.get("erro", 0)),
                               "simulacao": para_valor(bool(ag.get("simular")))}},
         "updateTransforms": [{"fieldPath": "quando", "setToServerValue": "REQUEST_TIME"}]},
    ]})


# ---------------------------- horários ----------------------------
def _hora(ag):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", ag.get("hora") or "")
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return int(m.group(1)), int(m.group(2))


def horario_do_dia(ag, dia):
    h = _hora(ag)
    if not h or dia.weekday() not in (ag.get("dias") or []):
        return None
    return dt.datetime.combine(dia, dt.time(*h))


def devido(ag, agora, ja_feitos):
    """Horário que deve rodar agora (datetime) ou None.
    ja_feitos: {id: datetime do horário já executado/tentado neste computador}."""
    if not ag.get("ativo"):
        return None
    alvo = horario_do_dia(ag, agora.date())
    if not alvo or not (alvo <= agora <= alvo + JANELA_ATRASO):
        return None
    if ja_feitos.get(ag["id"]) == alvo:
        return None
    ultima = ag.get("ultima")
    if ultima and ultima >= alvo:
        return None
    return alvo


def proxima(ag, agora):
    if not ag.get("ativo") or not _hora(ag) or not ag.get("dias"):
        return None
    for i in range(0, 8):
        dia = agora.date() + dt.timedelta(days=i)
        alvo = horario_do_dia(ag, dia)
        if alvo and alvo >= agora - (JANELA_ATRASO if i == 0 else dt.timedelta(0)):
            if i == 0 and ag.get("ultima") and ag["ultima"] >= alvo:
                continue
            return alvo
    return None


def descrever_dias(dias):
    dias = sorted(dias or [])
    if dias == list(range(7)):
        return "todos os dias"
    if dias == list(range(5)):
        return "seg a sex"
    return ", ".join(DIAS[d].lower() for d in dias) or "nenhum dia"


def competencia_de(regra, hoje=None):
    """'anterior' | 'atual' | 'anterior_atual' -> ((ano, mês), (ano, mês)); vazio -> None."""
    hoje = hoje or dt.date.today()
    if regra == "anterior_atual":
        m = hoje.replace(day=1) - dt.timedelta(days=1)
        return (m.year, m.month), (hoje.year, hoje.month)
    if regra == "atual":
        c = (hoje.year, hoje.month)
    elif regra == "anterior":
        m = hoje.replace(day=1) - dt.timedelta(days=1)
        c = (m.year, m.month)
    else:
        return None
    return c, c

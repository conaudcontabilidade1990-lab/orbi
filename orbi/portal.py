"""Leitura e gravação no Portal Conaud (Firestore do conaud-fiscal) com o login do usuário.

- empresas: coleção companies (só leitura; as regras do portal já permitem para operadores)
- seleções do Orbi: coleção orbiSelecoes (filtros salvos, compartilhados com a equipe)
As empresas ficam também guardadas em %APPDATA%\\Orbi\\empresas.json (uso sem internet e na Agenda).
"""
import datetime as dt
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

from . import config as cfgmod
from .conta import PROJETO

BASE = f"https://firestore.googleapis.com/v1/projects/{PROJETO}/databases/(default)/documents"
CACHE = cfgmod.PASTA / "empresas.json"

CAMPOS_EMPRESA = ["codigo", "legalName", "tradeName", "cnpj", "cnpjNormalized", "stateRegistration",
                  "regime", "anexo", "state", "city", "active", "responsavelConaud", "naturezaJuridica",
                  "tipoPessoa"]


class ErroPortal(Exception):
    pass


# ---------------------------- valores do Firestore ----------------------------
def de_valor(v):
    if "stringValue" in v:
        return v["stringValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "nullValue" in v:
        return None
    if "timestampValue" in v:
        return v["timestampValue"]
    if "arrayValue" in v:
        return [de_valor(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: de_valor(x) for k, x in v["mapValue"].get("fields", {}).items()}
    return None


def para_valor(x):
    if x is None:
        return {"nullValue": None}
    if isinstance(x, bool):
        return {"booleanValue": x}
    if isinstance(x, int):
        return {"integerValue": str(x)}
    if isinstance(x, float):
        return {"doubleValue": x}
    if isinstance(x, (list, tuple)):
        return {"arrayValue": {"values": [para_valor(i) for i in x]}}
    if isinstance(x, dict):
        return {"mapValue": {"fields": {k: para_valor(v) for k, v in x.items()}}}
    return {"stringValue": str(x)}


def _pedir(usuario, metodo, url, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    try:
        token = usuario.token()
    except Exception as e:
        raise ErroPortal(f"Sessão do portal expirou; entre de novo ({e}).") from None
    req = urllib.request.Request(url, data=dados, method=metodo, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        try:
            msg = json.load(e).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        if e.code == 403:
            raise ErroPortal(f"Sem permissão no portal ({msg or 'regra de segurança'}).") from None
        raise ErroPortal(f"Erro do portal ({e.code}): {msg}") from None
    except urllib.error.URLError:
        raise ErroPortal("Sem conexão com a internet.") from None


# ---------------------------- empresas ----------------------------
def baixar_empresas(usuario):
    """Lê todas as empresas do cadastro do portal e guarda uma cópia local."""
    empresas, token = [], None
    mascara = "&".join(f"mask.fieldPaths={c}" for c in CAMPOS_EMPRESA)
    while True:
        url = f"{BASE}/companies?pageSize=300&{mascara}" + (f"&pageToken={urllib.parse.quote(token)}" if token else "")
        r = _pedir(usuario, "GET", url)
        for doc in r.get("documents", []):
            c = {k: de_valor(v) for k, v in doc.get("fields", {}).items()}
            c["id"] = doc["name"].rsplit("/", 1)[-1]
            empresas.append(normalizar_empresa(c))
        token = r.get("nextPageToken")
        if not token:
            break
    empresas.sort(key=lambda e: (e["codigo_num"] is None, e["codigo_num"] or 0, e["nome"]))
    cfgmod.PASTA.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"quando": dt.datetime.now().isoformat(timespec="seconds"),
                                 "empresas": empresas}, ensure_ascii=False), encoding="utf-8")
    return empresas


def empresas_guardadas():
    """(empresas, quando) da cópia local, ou ([], None)."""
    try:
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        return d.get("empresas", []), d.get("quando")
    except Exception:
        return [], None


def normalizar_empresa(c):
    cod = str(c.get("codigo") or "").strip()
    return {
        "id": c.get("id"),
        "codigo": cod,
        "codigo_num": int(cod) if cod.isdigit() else None,
        "nome": c.get("legalName") or "",
        "fantasia": c.get("tradeName") or "",
        "cnpj": c.get("cnpj") or c.get("cnpjNormalized") or "",
        "ie": c.get("stateRegistration") or "",
        "regime": c.get("regime") or "",
        "anexo": c.get("anexo") or "",
        "uf": c.get("state") or "",
        "cidade": c.get("city") or "",
        "ativa": c.get("active") is not False,
        "responsavel": c.get("responsavelConaud") or "",
        "natureza": c.get("naturezaJuridica") or "",
        "pf": c.get("tipoPessoa") == "PF",
    }


# ---------------------------- filtros ----------------------------
FILTROS = [  # chave, rótulo, campo da empresa
    ("regime", "Regime", "regime"),
    ("uf", "UF", "uf"),
    ("cidade", "Cidade", "cidade"),
    ("responsavel", "Responsável", "responsavel"),
    ("natureza", "Natureza jurídica", "natureza"),
]


def _n(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()


def aplicar_filtros(empresas, filtros):
    """filtros: {regime:[..], uf:[..], cidade:[..], responsavel:[..], natureza:[..],
    situacao:'ativas'|'inativas'|'todas', busca:'texto', excluir:[codigos]}  (lista vazia = todos)."""
    f = filtros or {}
    situacao = f.get("situacao", "ativas")
    busca = _n(f.get("busca", ""))
    excluir = set(map(str, f.get("excluir") or []))
    out = []
    for e in empresas:
        if situacao == "ativas" and not e["ativa"]:
            continue
        if situacao == "inativas" and e["ativa"]:
            continue
        if any(f.get(k) and _n(e[campo]) not in {_n(v) for v in f[k]} for k, _, campo in FILTROS):
            continue
        if busca and not any(busca in _n(e[c]) for c in ("codigo", "nome", "fantasia", "cnpj", "ie")) \
                and busca.replace(".", "").replace("/", "").replace("-", "") not in re.sub(r"\D", "", e["cnpj"]):
            continue
        if e["codigo"] in excluir:
            continue
        out.append(e)
    return out


def valores(empresas, campo):
    return sorted({e[campo] for e in empresas if e[campo]}, key=_n)


def descrever(filtros):
    partes = [f"{rot}: {', '.join(filtros[k])}" for k, rot, _ in FILTROS if filtros.get(k)]
    sit = filtros.get("situacao", "ativas")
    if sit != "todas":
        partes.append("só ativas" if sit == "ativas" else "só inativas")
    if filtros.get("busca"):
        partes.append(f"busca '{filtros['busca']}'")
    if filtros.get("excluir"):
        partes.append(f"{len(filtros['excluir'])} excluída(s)")
    return " · ".join(partes) or "todas as empresas"


# ---------------------------- seleções (orbiSelecoes) ----------------------------
def listar_selecoes(usuario):
    r = _pedir(usuario, "GET", f"{BASE}/orbiSelecoes?pageSize=300")
    out = []
    for doc in r.get("documents", []):
        d = {k: de_valor(v) for k, v in doc.get("fields", {}).items()}
        d["id"] = doc["name"].rsplit("/", 1)[-1]
        out.append(d)
    return sorted(out, key=lambda s: _n(s.get("nome")))


def salvar_selecao(usuario, nome, filtros, id_=None):
    id_ = id_ or uuid.uuid4().hex[:20]
    campos = {"nome": para_valor(nome.strip()[:80]), "filtros": para_valor(filtros),
              "atualizadoPor": para_valor(usuario.uid), "atualizadoPorNome": para_valor(usuario.nome[:80])}
    # atualizadoEm = horário do servidor (exigido pela regra do portal)
    corpo = {"writes": [{
        "update": {"name": f"projects/{PROJETO}/databases/(default)/documents/orbiSelecoes/{id_}",
                   "fields": campos},
        "updateTransforms": [{"fieldPath": "atualizadoEm", "setToServerValue": "REQUEST_TIME"}],
    }]}
    _pedir(usuario, "POST", f"{BASE.rsplit('/documents', 1)[0]}/documents:commit", corpo)
    return id_


def apagar_selecao(usuario, id_):
    _pedir(usuario, "DELETE", f"{BASE}/orbiSelecoes/{id_}")

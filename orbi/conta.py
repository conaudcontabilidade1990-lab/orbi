"""Login com as contas do Portal Conaud (Firebase do projeto conaud-fiscal).

Só leitura: confere e-mail/senha no Firebase Auth e lê o perfil em users/{uid}
(role, active, acessos). Nada é gravado no portal.
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

# Configuração pública do app Web do portal (a mesma do site; não é segredo).
API_KEY = "AIzaSyBLaBVQuYJ-8pvtf83UtgyMS5lMzlE8gGA"
PROJETO = "conaud-fiscal"

# Departamentos do portal (mesmos ids de web/src/lib/modulos.ts)
DEPARTAMENTOS = {
    "fiscal": "Departamento Fiscal",
    "legalizacao": "Legalização de Empresas",
    "pessoal": "Departamento Pessoal",
    "contabil": "Departamento Contábil",
    "rural": "Departamento Rural",
    "obras": "Regularização de Obras",
    "financeiro": "Departamento Financeiro",
    "recepcao": "Recepção",
    "geral": "Controle Geral",
}

PERFIS_PERMITIDOS = ("admin", "operador")


class ErroLogin(Exception):
    pass


@dataclass
class Usuario:
    uid: str
    email: str
    nome: str
    role: str
    acessos: list | None = field(default=None)

    @property
    def admin(self):
        return self.role == "admin"

    def departamentos(self):
        """Ids dos departamentos liberados (mesma regra do portal: admin ou sem lista = tudo)."""
        if self.admin or self.acessos is None:
            return set(DEPARTAMENTOS)
        return {a.split("/", 1)[0] for a in self.acessos if isinstance(a, str)}


def _post(url, dados):
    req = urllib.request.Request(url, data=json.dumps(dados).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    return _abrir(req)


def _abrir(req):
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            corpo = json.load(e)
        except Exception:
            corpo = {}
        msg = (corpo.get("error") or {}).get("message", "") or str(e.code)
        raise ErroLogin(msg) from None
    except urllib.error.URLError:
        raise ErroLogin("SEM_CONEXAO") from None


def _valor(v):
    if "stringValue" in v:
        return v["stringValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [_valor(x) for x in v["arrayValue"].get("values", [])]
    return None


MENSAGENS = {
    "INVALID_LOGIN_CREDENTIALS": "E-mail ou senha incorretos.",
    "EMAIL_NOT_FOUND": "E-mail ou senha incorretos.",
    "INVALID_PASSWORD": "E-mail ou senha incorretos.",
    "INVALID_EMAIL": "E-mail inválido.",
    "USER_DISABLED": "Usuário desativado no portal.",
    "SEM_CONEXAO": "Sem conexão com a internet.",
}


def entrar(email, senha):
    email = (email or "").strip()
    if not email or not senha:
        raise ErroLogin("Informe e-mail e senha.")
    try:
        auth = _post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
                     {"email": email, "password": senha, "returnSecureToken": True})
    except ErroLogin as e:
        cod = str(e).split(":")[0].strip()
        if cod.startswith("TOO_MANY_ATTEMPTS"):
            raise ErroLogin("Muitas tentativas. Aguarde alguns minutos.") from None
        raise ErroLogin(MENSAGENS.get(cod, f"Não foi possível entrar ({cod}).")) from None

    uid, token = auth["localId"], auth["idToken"]
    req = urllib.request.Request(
        f"https://firestore.googleapis.com/v1/projects/{PROJETO}/databases/(default)/documents/users/{uid}",
        headers={"Authorization": f"Bearer {token}"})
    try:
        doc = _abrir(req)
    except ErroLogin as e:
        if str(e) == "SEM_CONEXAO":
            raise ErroLogin(MENSAGENS["SEM_CONEXAO"]) from None
        raise ErroLogin("Seu usuário não tem perfil liberado no portal.") from None

    campos = {k: _valor(v) for k, v in doc.get("fields", {}).items()}
    if campos.get("active") is not True:
        raise ErroLogin("Usuário inativo no portal.")
    role = campos.get("role") or ""
    if role not in PERFIS_PERMITIDOS:
        raise ErroLogin("Este tipo de conta não pode usar o Orbi.")
    acessos = campos.get("acessos")
    return Usuario(uid=uid, email=email, nome=campos.get("name") or email, role=role,
                   acessos=acessos if isinstance(acessos, list) else None)

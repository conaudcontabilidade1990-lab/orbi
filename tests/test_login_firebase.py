"""Chama o Firebase do portal com uma conta que não existe: deve responder 'E-mail ou senha incorretos.'"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orbi import conta  # noqa: E402

try:
    conta.entrar("orbi-teste-inexistente@exemplo.com.br", "senha-errada-123")
except conta.ErroLogin as e:
    print("resposta:", e)
    assert str(e) == "E-mail ou senha incorretos.", e
else:
    raise SystemExit("login inexistente não deveria entrar")
print("ok: Firebase do portal respondeu como esperado")

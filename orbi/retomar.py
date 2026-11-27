"""'Memória' da última rodada interrompida: guarda onde parou para continuar dali (por computador)."""
import datetime as dt
import json

from . import config as cfgmod

ARQUIVO = cfgmod.PASTA / "retomar.json"


def salvar(estado):
    try:
        cfgmod.PASTA.mkdir(parents=True, exist_ok=True)
        estado = dict(estado, quando=dt.datetime.now().strftime("%d/%m/%Y %H:%M"))
        ARQUIVO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def carregar():
    try:
        e = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        return e if e.get("pendentes") else None
    except (OSError, ValueError):
        return None


def limpar():
    try:
        ARQUIVO.unlink()
    except OSError:
        pass

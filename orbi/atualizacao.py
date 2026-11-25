"""Atualização automática pelo GitHub Releases.

Ao abrir, o Orbi consulta a última versão publicada. Se for mais nova, baixa o Orbi.exe,
troca o executável (o Windows permite renomear um .exe em uso) e reabre sozinho.
Sem .bat, sem arquivos extras.
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import REPO_GITHUB, VERSAO

NOME_ASSET = "Orbi.exe"


def _tupla(v):
    v = v.lstrip("vV")
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


def eh_executavel():
    return getattr(sys, "frozen", False)


def limpar_antigo():
    if eh_executavel():
        antigo = Path(sys.executable).with_suffix(".old")
        try:
            antigo.unlink(missing_ok=True)
        except OSError:
            pass


def verificar():
    """Retorna (versao, url) se houver versão mais nova; senão None."""
    if not REPO_GITHUB:
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_GITHUB}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Orbi"})
    with urllib.request.urlopen(req, timeout=15) as r:
        dados = json.load(r)
    nova = dados.get("tag_name", "")
    if _tupla(nova) <= _tupla(VERSAO):
        return None
    for a in dados.get("assets", []):
        if a.get("name") == NOME_ASSET:
            return nova.lstrip("vV"), a["browser_download_url"]
    return None


def aplicar(url, progresso=lambda txt: None):
    """Baixa e troca o executável; reabre o Orbi. Só funciona no .exe."""
    if not eh_executavel():
        raise RuntimeError("Atualização automática só funciona no Orbi.exe.")
    exe = Path(sys.executable)
    novo = exe.with_suffix(".new")
    antigo = exe.with_suffix(".old")
    progresso("baixando...")
    req = urllib.request.Request(url, headers={"User-Agent": "Orbi"})
    with urllib.request.urlopen(req, timeout=120) as r, open(novo, "wb") as f:
        while bloco := r.read(1 << 16):
            f.write(bloco)
    if novo.stat().st_size < 1_000_000:
        novo.unlink(missing_ok=True)
        raise RuntimeError("Arquivo baixado parece incompleto.")
    antigo.unlink(missing_ok=True)
    os.replace(exe, antigo)      # renomeia o .exe em uso
    os.replace(novo, exe)
    progresso("reiniciando...")
    reabrir(exe)
    os._exit(0)


def reabrir(exe):
    """Abre uma cópia nova e independente do Orbi.exe.

    Sem isso, o PyInstaller faria a nova cópia reaproveitar a pasta temporária desta,
    que é apagada quando esta fecha (faltariam módulos, ex.: winrt._winrt)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_MEI", "_PYI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen([str(exe)], env=env, close_fds=True,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                     | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))

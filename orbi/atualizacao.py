"""Atualização automática pelo GitHub Releases.

Ao abrir, o Orbi consulta a última versão publicada. Se for mais nova, baixa o Orbi.exe,
troca o executável (o Windows permite renomear um .exe em uso) e reabre sozinho.
Sem .bat, sem arquivos extras.
"""
import json
import time
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import REPO_GITHUB, VERSAO

NOME_ASSET = "Orbi.exe"
ERRO = ""          # último erro ao verificar/aplicar atualização (vai no sinal do computador)


def _tupla(v):
    v = v.lstrip("vV")
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


def eh_executavel():
    return getattr(sys, "frozen", False)


def limpar_antigo():
    """Apaga Orbi.old / Orbi.old-123... deixados por atualizações (os que não estiverem em uso)."""
    if eh_executavel():
        exe = Path(sys.executable)
        for antigo in exe.parent.glob(exe.stem + ".old*"):
            try:
                antigo.unlink()
            except OSError:
                pass


def _abrir_url(req, timeout):
    """urlopen que tolera computador sem o certificado raiz no Windows: tenta o padrão e, se o certificado
    não for reconhecido, usa a lista de certificados que vai junto com o Orbi (certifi)."""
    import ssl
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as e:
        if not isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError):
            raise
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def verificar():
    """Retorna (versao, url) se houver versão mais nova; senão None."""
    if not REPO_GITHUB:
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_GITHUB}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Orbi"})
    with _abrir_url(req, 15) as r:
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
    with _abrir_url(req, 120) as r, open(novo, "wb") as f:
        while bloco := r.read(1 << 16):
            f.write(bloco)
    if novo.stat().st_size < 1_000_000:
        novo.unlink(missing_ok=True)
        raise RuntimeError("Arquivo baixado parece incompleto.")
    try:
        antigo.unlink(missing_ok=True)
    except OSError:              # o .old ainda está em uso (outra cópia aberta): usa outro nome
        import time
        antigo = exe.with_suffix(f".old-{int(time.time())}")
    os.replace(exe, antigo)      # renomeia o .exe em uso
    os.replace(novo, exe)
    progresso("reiniciando...")
    reabrir(exe)
    os._exit(0)


def reabrir(exe, args=()):
    """Abre uma cópia nova e independente do Orbi.exe.

    Sem isso, o PyInstaller faria a nova cópia reaproveitar a pasta temporária desta,
    que é apagada quando esta fecha (faltariam módulos, ex.: winrt._winrt)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_MEI", "_PYI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    subprocess.Popen([str(exe), *args], env=env, close_fds=True,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                     | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def pasta_local():
    """Onde o Orbi fica instalado em cada computador (cada um se atualiza sozinho pelo GitHub)."""
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "Orbi"


def _atalho(destino_lnk, alvo, args=""):
    cmd = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
           "$s.TargetPath=$env:ALVO;$s.Arguments=$env:ARGS;$s.WorkingDirectory=(Split-Path $env:ALVO);"
           "$s.IconLocation=$env:ALVO+',0';$s.Save()")
    env = dict(os.environ, LNK=str(destino_lnk), ALVO=str(alvo), ARGS=args)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                   env=env, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def instalar_se_no_servidor():
    """Aberto de outra pasta (ex.: Z:\\Orbi no servidor): copia para a pasta local deste computador,
    cria o atalho na Área de Trabalho e no Menu Iniciar e reabre a cópia local.

    Rodar direto do servidor travaria as atualizações (o .exe em uso por 4 computadores não pode
    ser trocado) — por isso o servidor serve só para distribuir/instalar."""
    if not eh_executavel():
        return False
    exe = Path(sys.executable).resolve()
    local = pasta_local()
    if exe.parent == local.resolve() or os.environ.get("ORBI_NAO_INSTALAR"):
        return False
    import shutil
    local.mkdir(parents=True, exist_ok=True)
    destino = local / "Orbi.exe"
    copiar = True
    if destino.exists():
        # o local se atualiza sozinho; só troca se o do servidor tiver sido colocado depois (mais novo)
        try:
            copiar = exe.stat().st_mtime > destino.stat().st_mtime + 60
        except OSError:
            pass
    if copiar:
        temp = local / "Orbi.exe.new"
        shutil.copy2(exe, temp)
        try:
            destino.unlink(missing_ok=True)
        except OSError:
            destino = local / f"Orbi-{int(time.time())}.exe"
        os.replace(temp, destino)
    for pasta in (Path.home() / "Desktop",
                  Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"):
        try:
            if pasta.is_dir():
                _atalho(pasta / "Orbi.lnk", destino)
        except Exception:
            pass
    reabrir(destino, sys.argv[1:])
    return True

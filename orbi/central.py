"""Cópia central dos registros: cada computador espelha o registro do dia, os relatórios e as fotos das
paradas numa pasta do servidor (padrão Z:\\Orbi\\ocorrencias\\<computador>), para conferir tudo de um lugar só.

Roda numa thread própria: se o servidor estiver fora do ar, o Orbi continua normalmente."""
import os
import queue
import shutil
import socket
import threading
from pathlib import Path

_fila = queue.Queue()
_thread = None
_cfg = {}
ERRO = ""          # último problema ao gravar no servidor (aparece na Agenda e no sinal do computador)
PADRAO = "Z:\\Orbi\\ocorrencias"
# o mesmo Z: pelo endereço de rede (a letra Z: às vezes não existe para o programa)
ALTERNATIVAS = ("\\\\servidor\\REDE\\SISTEMAS\\Orbi\\ocorrencias",)


def _base():
    for b in [_cfg.get("pasta_central") or PADRAO, *ALTERNATIVAS]:
        try:
            if Path(b).parent.exists():
                return Path(b)
        except OSError:
            pass
    return None


def nome_computador():
    nome = (_cfg.get("apelido_pc") or socket.gethostname() or "computador").strip()
    return "".join(c if c.isalnum() or c in " -_." else "_" for c in nome)


def _trabalhar():
    global ERRO
    while True:
        tipo, dado = _fila.get()
        try:
            base = _base()
            if base is None:
                ERRO = f"não encontrei a pasta do servidor ({_cfg.get('pasta_central') or PADRAO})"
                continue
            destino = base / nome_computador()
            destino.mkdir(parents=True, exist_ok=True)
            if tipo == "arquivo":
                shutil.copy2(dado, destino / Path(dado).name)
            elif tipo == "linha":
                nome, linha = dado
                with open(destino / nome, "a", encoding="utf-8") as f:
                    f.write(linha + "\n")
            ERRO = ""
        except Exception as e:
            ERRO = f"{type(e).__name__}: {e}"[:200]


def iniciar(cfg):
    global _thread, _cfg
    _cfg = cfg
    if _thread is None and os.name == "nt":
        _thread = threading.Thread(target=_trabalhar, daemon=True)
        _thread.start()


def copiar(arquivo):
    if _thread:
        _fila.put(("arquivo", str(arquivo)))


def linha(nome_arquivo, texto):
    if _thread:
        _fila.put(("linha", (nome_arquivo, texto)))

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


def _pasta():
    base = _cfg.get("pasta_central") or r"Z:\Orbi\ocorrencias"
    nome = (_cfg.get("apelido_pc") or socket.gethostname() or "computador").strip()
    nome = "".join(c if c.isalnum() or c in " -_." else "_" for c in nome)
    return Path(base) / nome


def _trabalhar():
    while True:
        tipo, dado = _fila.get()
        try:
            destino = _pasta()
            if not destino.parent.parent.exists():   # servidor fora do ar (sem Z:\Orbi): ignora
                continue
            destino.mkdir(parents=True, exist_ok=True)
            if tipo == "arquivo":
                shutil.copy2(dado, destino / Path(dado).name)
            elif tipo == "linha":
                nome, linha = dado
                with open(destino / nome, "a", encoding="utf-8") as f:
                    f.write(linha + "\n")
        except Exception:
            pass


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

"""Ações na tela: cliques, digitação, leitura de texto (OCR do Windows) e esperas.

Toda rotina usa a classe Tela. Ela confere o botão Parar a cada ação e para tudo
se o mouse for jogado no canto superior esquerdo (proteção do pyautogui).
"""
import datetime as dt
import re
import threading
import time
import unicodedata

import pyautogui
from PIL import ImageOps

from . import config as cfgmod

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15


class Parar(Exception):
    """Situação não prevista: a rotina para sem contornar e mostra o motivo."""


class Cancelado(Exception):
    """O usuário clicou em Parar."""


def norm(s):
    """minúsculas, sem acentos e com espaços simples — para comparar textos lidos."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


# ------------------------------- OCR -------------------------------
_idioma_ok = None


def ocr_imagem(img, idioma="pt-BR"):
    """Lê o texto de uma imagem com o OCR que já vem no Windows (sem instalar nada)."""
    global _idioma_ok
    import winocr  # importado aqui para o resto do app funcionar mesmo sem OCR

    img = ImageOps.grayscale(img).convert("RGB")
    img = img.resize((img.width * 3, img.height * 3))
    for lang in ([_idioma_ok] if _idioma_ok else [idioma, "pt-BR", "en-US"]):
        try:
            r = winocr.recognize_pil_sync(img, lang)
            _idioma_ok = lang
            return r["text"] if isinstance(r, dict) else getattr(r, "text", "")
        except Exception:
            continue
    raise RuntimeError("OCR do Windows indisponível (instale o idioma Português em Configurações > Idioma).")


class Tela:
    def __init__(self, cfg, log, parar_evento=None):
        self.cfg = cfg
        self.log = log
        self.parar = parar_evento or threading.Event()
        self.P = cfg["pontos"]
        self.R = cfg["regioes"]
        self.T = cfg["tempos"]
        cfgmod.PASTA_LOGS.mkdir(parents=True, exist_ok=True)

    # ---- controle ----
    def checar(self):
        if self.parar.is_set():
            raise Cancelado()

    def dormir(self, seg):
        fim = time.time() + seg
        while time.time() < fim:
            self.checar()
            time.sleep(min(0.2, max(0, fim - time.time())))

    def conferir_resolucao(self):
        atual = list(pyautogui.size())
        if atual != list(self.cfg["resolucao"]):
            raise Parar(f"Resolução da tela {atual[0]}x{atual[1]} diferente da calibrada "
                        f"{self.cfg['resolucao'][0]}x{self.cfg['resolucao'][1]}.")

    # ---- ações ----
    def clicar(self, nome, triplo=False, espera=None):
        self.checar()
        x, y = self.P[nome]
        if triplo:
            pyautogui.tripleClick(x, y)
        else:
            pyautogui.click(x, y)
        self.dormir(self.T["pausa"] if espera is None else espera)

    def digitar(self, texto, espera=None):
        self.checar()
        pyautogui.typewrite(str(texto), interval=0.05)
        self.dormir(self.T["pausa"] if espera is None else espera)

    def teclas(self, *teclas):
        self.checar()
        pyautogui.hotkey(*teclas)

    # ---- leitura ----
    def regiao(self, nome_ou_tupla):
        r = self.R.get(nome_ou_tupla) if isinstance(nome_ou_tupla, str) else nome_ou_tupla
        if not r:
            raise Parar(f"Região '{nome_ou_tupla}' ainda não foi calibrada.")
        return tuple(r)

    def ler(self, regiao, digitos=False):
        self.checar()
        txt = norm(ocr_imagem(pyautogui.screenshot(region=self.regiao(regiao)), self.cfg["idioma_ocr"]))
        if digitos:
            txt = re.sub(r"[^0-9]", "", txt.replace("o", "0").replace("l", "1").replace("i", "1"))
        return txt

    def esperar(self, regiao, alvos, timeout, intervalo=1.5):
        """alvos = {"nome": ["trecho", ...]}. Retorna o nome do alvo que apareceu, ou None."""
        fim = time.time() + timeout
        while time.time() < fim:
            texto = self.ler(regiao)
            for nome, trechos in alvos.items():
                if any(t in texto for t in trechos):
                    return nome
            self.dormir(intervalo)
        return None

    def escuros(self, nome_ponto):
        x, y = self.P[nome_ponto]
        img = ImageOps.grayscale(pyautogui.screenshot(region=(x - 4, y - 4, 9, 9)))
        return sum(1 for p in img.getdata() if p < 100)

    def caixa_marcada(self, nome_ponto):
        return self.escuros(nome_ponto) >= self.cfg["limiar_caixa"]

    def foto(self, nome):
        caminho = cfgmod.PASTA_LOGS / f"{dt.datetime.now():%Y%m%d_%H%M%S}_{nome}.png"
        pyautogui.screenshot(str(caminho))
        return caminho

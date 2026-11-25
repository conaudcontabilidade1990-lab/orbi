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
# OCR que já vem no Windows (Windows.Media.Ocr), chamado direto e sem asyncio.
_motor = None
_trava = threading.Lock()


def _criar_motor(idioma):
    from winrt.windows.globalization import Language
    from winrt.windows.media.ocr import OcrEngine

    for lang in (idioma, "pt-BR", "en-US"):
        try:
            eng = OcrEngine.try_create_from_language(Language(lang))
        except Exception:
            eng = None
        if eng is not None:
            return eng
    eng = OcrEngine.try_create_from_user_profile_languages()
    if eng is None:
        raise RuntimeError("OCR do Windows indisponível: instale o idioma Português "
                           "(Configurações > Hora e idioma > Idioma).")
    return eng


def preparar(img):
    img = ImageOps.grayscale(img)
    if sum(img.getdata()) / (img.width * img.height) < 110:  # texto claro em fundo escuro
        img = ImageOps.invert(img)
    return img.resize((img.width * 3, img.height * 3)).convert("RGBA")


def ocr_imagem(img, idioma="pt-BR", preparar_img=True):
    """Lê o texto de uma imagem PIL."""
    global _motor
    from winrt.windows.foundation import AsyncStatus
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.storage.streams import DataWriter

    with _trava:
        if _motor is None:
            _motor = _criar_motor(idioma)
        img = preparar(img) if preparar_img else img.convert("RGBA")
        w = DataWriter()
        w.write_bytes(img.tobytes())
        sb = SoftwareBitmap.create_copy_from_buffer(
            w.detach_buffer(), BitmapPixelFormat.RGBA8, img.width, img.height)
        op = _motor.recognize_async(sb)
        fim = time.time() + 15
        while op.status == AsyncStatus.STARTED:
            if time.time() > fim:
                raise RuntimeError("OCR do Windows não respondeu em 15 s.")
            time.sleep(0.01)
        if op.status != AsyncStatus.COMPLETED:
            raise RuntimeError(f"OCR do Windows falhou (status {op.status}).")
        return op.get_results().text or ""


# ---------------------- números em campos (por desenho) ----------------------
# Os campos numéricos do Domínio usam sempre a mesma fonte pequena; o OCR não lê um dígito
# sozinho, então comparamos o desenho dos pixels. Dígito desconhecido = "?" (a rotina para).
GLIFOS = {
    "1": ("..#",
          "###",
          "..#",
          "..#",
          "..#",
          "..#",
          "..#",
          "..#",
          "..#"),
}


def numero_de_imagem(img, limiar=100, altura_cursor=11):
    g = ImageOps.grayscale(img)
    w, h = g.size
    escuro = [[g.getpixel((x, y)) < limiar for x in range(w)] for y in range(h)]
    # remove colunas do cursor (linha vertical mais alta que os dígitos)
    for x in range(w):
        if sum(escuro[y][x] for y in range(h)) >= altura_cursor:
            for y in range(h):
                escuro[y][x] = False
    colunas = [any(escuro[y][x] for y in range(h)) for x in range(w)]
    linhas = [y for y in range(h) if any(escuro[y])]
    if not linhas:
        return ""
    y0, y1 = linhas[0], linhas[-1]
    texto, x = "", 0
    while x < w:
        if not colunas[x]:
            x += 1
            continue
        x0 = x
        while x < w and colunas[x]:
            x += 1
        desenho = tuple("".join("#" if escuro[y][c] else "." for c in range(x0, x))
                        for y in range(y0, y1 + 1))
        texto += next((d for d, gl in GLIFOS.items() if gl == desenho), "?")
    return texto


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

    def duplo(self, x, y, espera=None):
        self.checar()
        pyautogui.doubleClick(x, y)
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

    def ler_numero(self, regiao):
        self.checar()
        return numero_de_imagem(pyautogui.screenshot(region=self.regiao(regiao)))

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

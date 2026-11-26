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


def _reconhecer(img, idioma, preparar_img):
    """Roda o OCR do Windows e devolve (resultado, fator de ampliação)."""
    global _motor
    from winrt.windows.foundation import AsyncStatus
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.storage.streams import DataWriter

    with _trava:
        if _motor is None:
            _motor = _criar_motor(idioma)
        fator = 3 if preparar_img else 1
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
        return op.get_results(), fator


def ocr_imagem(img, idioma="pt-BR", preparar_img=True):
    """Lê o texto de uma imagem PIL."""
    res, _ = _reconhecer(img, idioma, preparar_img)
    return res.text or ""


def ocr_linhas(img, idioma="pt-BR"):
    """[(texto, x, y, largura, altura)] de cada linha, em pixels da imagem original."""
    res, f = _reconhecer(img, idioma, True)
    linhas = []
    for ln in res.lines:
        rs = [w.bounding_rect for w in ln.words]
        if not rs:
            continue
        x0, y0 = min(r.x for r in rs), min(r.y for r in rs)
        x1, y1 = max(r.x + r.width for r in rs), max(r.y + r.height for r in rs)
        linhas.append((ln.text, x0 / f, y0 / f, (x1 - x0) / f, (y1 - y0) / f))
    return linhas


def faixa_destacada(img, x):
    """(y0, y1) da faixa azul de seleção na coluna x da imagem; None se não houver."""
    rgb = img.convert("RGB")
    melhor, ini = None, None
    for y in range(rgb.height + 1):
        azul = False
        if y < rgb.height:
            r, g, b = rgb.getpixel((x, y))
            azul = b > 150 and r < 70 and 70 < g < 170
        if azul and ini is None:
            ini = y
        elif not azul and ini is not None:
            if melhor is None or (y - ini) > (melhor[1] - melhor[0] + 1):
                melhor = (ini, y - 1)
            ini = None
    if melhor and melhor[1] - melhor[0] >= 8:
        return melhor
    return None


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

    def ler_linha_destacada(self, regiao_lista, x_amostra):
        """Texto da linha selecionada (faixa azul) de uma lista, esteja em que posição estiver."""
        self.checar()
        x, y, w, h = self.regiao(regiao_lista)
        img = pyautogui.screenshot(region=(x, y, w, h))
        faixa = faixa_destacada(img, x_amostra - x)
        if not faixa:
            return ""
        y0, y1 = faixa
        return norm(ocr_imagem(img.crop((0, y0, w, y1 + 1)), self.cfg["idioma_ocr"]))

    def achar_texto(self, trecho, regiao=None):
        """Centro (x, y) na tela da primeira linha cujo texto contém o trecho; None se não achar."""
        self.checar()
        x0, y0, w, h = self.regiao(regiao) if regiao else (0, 0, *self.cfg["resolucao"])
        for texto, x, y, lw, lh in ocr_linhas(pyautogui.screenshot(region=(x0, y0, w, h)), self.cfg["idioma_ocr"]):
            if trecho in norm(texto):
                return int(x0 + x + lw / 2), int(y0 + y + lh / 2)
        return None

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

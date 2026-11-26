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
from PIL import Image, ImageChops, ImageOps

from . import config as cfgmod

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04


class Parar(Exception):
    """Situação não prevista: a rotina para sem contornar e mostra o motivo."""


class Pular(Parar):
    """Problema só desta empresa e nada foi feito nela (ex.: código não encontrado no Domínio):
    a rotina registra o erro e segue para a próxima."""


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


def preparar(img, fator=3, binarizar=False, borda=0, contraste=False):
    img = ImageOps.grayscale(img)
    if contraste:  # texto cinza de janela inativa: estica o contraste antes de ler
        img = ImageOps.autocontrast(img, cutoff=1)
    if sum(img.getdata()) / (img.width * img.height) < 110:  # texto claro em fundo escuro
        img = ImageOps.invert(img)
    if binarizar:  # preto e branco puro: o OCR lê muito melhor números pequenos e isolados
        img = img.point(lambda v: 0 if v < 128 else 255)
    if borda:
        img = ImageOps.expand(img, border=borda, fill=255)
    return img.resize((img.width * fator, img.height * fator), Image.LANCZOS).convert("RGBA")


def _reconhecer(img, idioma, preparar_img, fator=3, binarizar=False, borda=0, contraste=False):
    """Roda o OCR do Windows e devolve (resultado, fator de ampliação)."""
    global _motor
    from winrt.windows.foundation import AsyncStatus
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.storage.streams import DataWriter

    with _trava:
        if _motor is None:
            _motor = _criar_motor(idioma)
        if preparar_img:
            img = preparar(img, fator, binarizar, borda, contraste)
        else:
            fator, borda = 1, 0
            img = img.convert("RGBA")
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
        return op.get_results(), fator, borda


def ocr_imagem(img, idioma="pt-BR", preparar_img=True, fator=3, binarizar=False, borda=0, contraste=False):
    """Lê o texto de uma imagem PIL."""
    res, _, _ = _reconhecer(img, idioma, preparar_img, fator, binarizar, borda, contraste)
    return res.text or ""


def ocr_linhas(img, idioma="pt-BR"):
    """[(texto, x, y, largura, altura)] de cada linha, em pixels da imagem original."""
    res, f, _ = _reconhecer(img, idioma, True)
    linhas = []
    for ln in res.lines:
        rs = [w.bounding_rect for w in ln.words]
        if not rs:
            continue
        x0, y0 = min(r.x for r in rs), min(r.y for r in rs)
        x1, y1 = max(r.x + r.width for r in rs), max(r.y + r.height for r in rs)
        linhas.append((ln.text, x0 / f, y0 / f, (x1 - x0) / f, (y1 - y0) / f))
    return linhas


def ocr_palavras(img, idioma="pt-BR", contraste=False):
    """[(texto, x, y, largura, altura, nº da linha)] de cada palavra, em pixels da imagem original."""
    res, f, _ = _reconhecer(img, idioma, True, contraste=contraste)
    out = []
    for i, ln in enumerate(res.lines):
        for w in ln.words:
            r = w.bounding_rect
            out.append((w.text, r.x / f, r.y / f, r.width / f, r.height / f, i))
    return out


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
GLIFOS = {  # fonte dos campos e listas do Domínio (tirados de telas reais)
    "0": ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    "1": ('..#', '###', '..#', '..#', '..#', '..#', '..#', '..#', '..#'),
    "2": ('.###.', '#...#', '....#', '....#', '...#.', '..#..', '.#...', '#....', '#####'),
    "3": ('.###.', '#...#', '....#', '....#', '..##.', '....#', '....#', '#...#', '.###.'),
    "4": ('...#.', '..##.', '..##.', '.#.#.', '.#.#.', '#..#.', '#####', '...#.', '...#.'),
    "5": ('#####', '#....', '#....', '####.', '#...#', '....#', '....#', '#...#', '.###.'),
    "6": ('.###.', '#...#', '#....', '#....', '####.', '#...#', '#...#', '#...#', '.###.'),
    "7": ('#####', '....#', '...#.', '...#.', '..#..', '..#..', '.#...', '.#...', '.#...'),
    "8": ('.###.', '#...#', '#...#', '#...#', '.###.', '#...#', '#...#', '#...#', '.###.'),
    "9": ('.###.', '#...#', '#...#', '#...#', '.####', '....#', '....#', '#...#', '.###.'),
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


def codigo_da_linha_azul(img_lista, x_amostra, x0, x1):
    """Código da linha selecionada (branco sobre azul) pelo desenho dos dígitos.
    Coordenadas relativas à imagem da lista. '' se não achar a faixa azul."""
    faixa = faixa_destacada(img_lista, x_amostra)
    if not faixa:
        return ""
    y0, y1 = faixa
    cod = img_lista.crop((x0, y0, x1, y1 + 1))
    return numero_de_imagem(ImageOps.invert(ImageOps.grayscale(cod)))



def botoes_fechar(img):
    """Centros (x, y) dos botões [X] das janelas internas do Domínio na imagem, a de cima primeiro.

    Toda janela interna tem o ícone magenta do Domínio no começo da barra de título. Acha o ícone,
    segue a barra de título para a direita até o fundo escuro e o [X] fica ~21 px antes da borda.
    (Não depende da cor do [X]: em janela inativa ele é cinza, não vermelho.)"""
    rgb = img.convert("RGB")
    r, g, b = rgb.split()
    mascara = ImageChops.multiply(ImageChops.multiply(
        r.point(lambda v: 255 if 130 <= v <= 205 else 0), g.point(lambda v: 255 if v < 70 else 0)),
        b.point(lambda v: 255 if 70 <= v <= 150 else 0))
    if not mascara.getbbox():
        return []
    px, m = rgb.load(), mascara.load()
    w, h = rgb.size

    def escuro(x, y):
        return max(px[x, y]) < 110

    achados = []
    for y in range(h):
        for x in range(w):
            if not m[x, y] or any(abs(x - a) < 20 and -2 <= y - (c - 7) < 16 for a, c, _ in achados):
                continue
            # ícone: coluna magenta de ~10+ px de altura
            alto = sum(1 for yy in range(y, min(h, y + 16)) if m[x, yy])
            if alto < 10:
                continue
            cy = y + 7
            # borda direita da janela: 1ª coluna escura de cima a baixo (moldura da janela ou fundo)
            ys = range(max(0, cy - 6), min(h, cy + 30))
            xe = x + 150
            while xe < w and sum(1 for yy in ys if escuro(xe, yy)) < 0.8 * len(ys):
                xe += 1
            if xe >= w and xe - x < 150:
                continue
            achados.append((x, cy, (xe - 21, cy)))
    achados.sort(key=lambda a: a[1], reverse=True)    # a de baixo/da frente primeiro (diálogos ficam por cima)
    return [a[2] for a in achados]

def copiar(texto):
    """Coloca texto na área de transferência do Windows (CF_UNICODETEXT)."""
    import ctypes
    from ctypes import wintypes
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GlobalAlloc.restype = wintypes.HGLOBAL
    k32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k32.GlobalLock.restype = wintypes.LPVOID
    k32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    dados = (texto + "\0").encode("utf-16-le")
    for _ in range(10):
        if u32.OpenClipboard(None):
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("Não consegui abrir a área de transferência do Windows.")
    try:
        u32.EmptyClipboard()
        h = k32.GlobalAlloc(0x0002, len(dados))
        ptr = k32.GlobalLock(h)
        ctypes.memmove(ptr, dados, len(dados))
        k32.GlobalUnlock(h)
        u32.SetClipboardData(13, h)
    finally:
        u32.CloseClipboard()


class Tela:
    def __init__(self, cfg, log, parar_evento=None):
        self.cfg = cfg
        self.log = log
        self.parar = parar_evento or threading.Event()
        self.P = cfg["pontos"]
        self.R = cfg["regioes"]
        self.T = cfg["tempos"]
        self.avisos = []
        cfgmod.PASTA_LOGS.mkdir(parents=True, exist_ok=True)

    def aviso(self, msg):
        """Algo fora do comum que não impediu a rotina (vira 'advertência' no Painel)."""
        self.avisos.append(msg)
        self.log(f"  ⚠ {msg}")

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
        pyautogui.typewrite(str(texto), interval=0.02)
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

    def ler(self, regiao, digitos=False, fator=3, binarizar=False, borda=0, contraste=False):
        self.checar()
        txt = norm(ocr_imagem(pyautogui.screenshot(region=self.regiao(regiao)), self.cfg["idioma_ocr"],
                              fator=fator, binarizar=binarizar, borda=borda, contraste=contraste))
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

    def ler_codigo_destacado(self, regiao_lista, x_amostra, x0, x1):
        self.checar()
        x, y, w, h = self.regiao(regiao_lista)
        img = pyautogui.screenshot(region=(x, y, w, h))
        return codigo_da_linha_azul(img, x_amostra - x, x0 - x, x1 - x)

    def achar_texto(self, trecho, regiao=None):
        """Centro (x, y) na tela da primeira linha cujo texto contém o trecho; None se não achar."""
        self.checar()
        x0, y0, w, h = self.regiao(regiao) if regiao else (0, 0, *self.cfg["resolucao"])
        for texto, x, y, lw, lh in ocr_linhas(pyautogui.screenshot(region=(x0, y0, w, h)), self.cfg["idioma_ocr"]):
            if trecho in norm(texto):
                return int(x0 + x + lw / 2), int(y0 + y + lh / 2)
        return None

    def achar_linha(self, aceita, regiao):
        """(x, y, texto) do centro da primeira linha de texto em que aceita(texto_normalizado) é True."""
        self.checar()
        x0, y0, w, h = regiao
        for texto, x, y, lw, lh in ocr_linhas(pyautogui.screenshot(region=(x0, y0, w, h)), self.cfg["idioma_ocr"]):
            n = norm(texto)
            if aceita(n):
                return int(x0 + x + lw / 2), int(y0 + y + lh / 2), n
        return None

    def botoes_fechar(self, regiao):
        """Botões [X] de janelas internas abertas dentro da região (coordenadas de tela)."""
        self.checar()
        x0, y0, w, h = self.regiao(regiao)
        return [(x0 + x, y0 + y) for x, y in botoes_fechar(pyautogui.screenshot(region=(x0, y0, w, h)))]

    def linhas(self, regiao):
        """[(texto normalizado, x, y, largura, altura)] das linhas de texto da região (coordenadas de tela)."""
        self.checar()
        x0, y0, w, h = self.regiao(regiao)
        return [(norm(tx), x0 + x, y0 + y, lw, lh)
                for tx, x, y, lw, lh in ocr_linhas(pyautogui.screenshot(region=(x0, y0, w, h)), self.cfg["idioma_ocr"])]

    def palavras(self, regiao, contraste=False):
        """[(palavra normalizada, x, y, largura, altura, nº da linha)] da região (coordenadas de tela).
        contraste=True também lê texto cinza (botões e abas desabilitados)."""
        self.checar()
        x0, y0, w, h = self.regiao(regiao)
        img = pyautogui.screenshot(region=(x0, y0, w, h))
        return [(norm(tx), x0 + x, y0 + y, lw, lh, i)
                for tx, x, y, lw, lh, i in ocr_palavras(img, self.cfg["idioma_ocr"], contraste)]

    def imagem(self, regiao):
        self.checar()
        return pyautogui.screenshot(region=self.regiao(regiao)).convert("RGB")

    def fracao_azul(self, regiao):
        """Fração dos pixels da região que são o azul de linha selecionada (lista com itens)."""
        self.checar()
        img = pyautogui.screenshot(region=self.regiao(regiao)).convert("RGB")
        px = list(img.getdata())
        return sum(1 for r, g, b in px if b > 150 and r < 90 and 70 < g < 190) / max(1, len(px))

    def escuros_em(self, x, y):
        img = ImageOps.grayscale(pyautogui.screenshot(region=(int(x) - 4, int(y) - 4, 9, 9)))
        return sum(1 for p in img.getdata() if p < 100)

    def rolar(self, x, y, cliques):
        self.checar()
        pyautogui.scroll(cliques, x=int(x), y=int(y))
        self.dormir(0.5)

    def apagar(self, n):
        """Backspace n vezes (limpa um campo de texto)."""
        self.checar()
        pyautogui.press("backspace", presses=n, interval=0)
        self.dormir(0.3)

    def colar(self, texto, espera=1.0):
        """Cola um texto (aceita acentos) pela área de transferência. O Domínio roda remoto (GraphOn) e
        a área de transferência demora a sincronizar: grava, espera, e só então Ctrl+V."""
        self.checar()
        copiar(texto)
        self.dormir(espera)
        pyautogui.hotkey("ctrl", "v")
        self.dormir(0.4)

    def clicar_em(self, x, y, espera=None):
        self.checar()
        pyautogui.click(x, y)
        self.dormir(self.T["pausa"] if espera is None else espera)

    def aguardar(self, condicao, timeout, intervalo=0.25):
        """Repete a conferência até dar certo ou acabar o tempo (segue assim que a tela muda)."""
        fim = time.time() + timeout
        while True:
            r = condicao()
            if r or time.time() >= fim:
                return r
            self.dormir(intervalo)

    def tem_linhas(self, regiao="lista_1a_linha", minimo=12):
        """A lista de notas tem pelo menos uma linha preenchida? (texto escuro na 1ª linha)"""
        self.checar()
        img = ImageOps.grayscale(pyautogui.screenshot(region=self.regiao(regiao)))
        return sum(1 for p in img.getdata() if p < 100) >= minimo

    def esperar(self, regiao, alvos, timeout, intervalo=0.4):
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

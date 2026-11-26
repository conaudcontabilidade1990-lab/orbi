import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageOps, ImageDraw, ImageFont
from orbi import config, tela
R = config.PADRAO["regioes"]
im = Image.open(Path(__file__).resolve().parents[1] / "tests/fixtures/codigo_empresa_214.png")
x, y, w, h = R["empresa_codigo"]
base = im.crop((x, y, x + w, y + h))
linha = im.crop((1290, 68, 1366, 92))  # só a linha do código

def prep(img, fator, inv, binar, borda):
    g = ImageOps.grayscale(img)
    if inv: g = ImageOps.invert(g)
    if binar: g = g.point(lambda v: 0 if v < 128 else 255)
    g = ImageOps.expand(g, border=borda, fill=255 if inv else 0)
    return g.resize((g.width * fator, g.height * fator), Image.LANCZOS).convert("RGB")

def contexto(img):
    g = ImageOps.invert(ImageOps.grayscale(img)).point(lambda v: 0 if v < 128 else 255)
    can = Image.new("L", (g.width + 260, g.height + 20), 255)
    ImageDraw.Draw(can).text((8, 4), "EMPRESA CODIGO", fill=0, font=ImageFont.load_default(size=16))
    can.paste(g, (240, 10))
    return can.resize((can.width * 3, can.height * 3), Image.LANCZOS).convert("RGB")

for nome, img in (("area", base), ("linha", linha)):
    for fator in (3, 4, 6):
        for inv in (True,):
            for binar in (False, True):
                for borda in (0, 12):
                    t = tela.ocr_imagem(prep(img, fator, inv, binar, borda), preparar_img=False)
                    print(f"{nome} f={fator} bin={binar} borda={borda}: {t!r}")
    print(f"{nome} contexto: {tela.ocr_imagem(contexto(img), preparar_img=False)!r}")
    print(f"{nome} padrao: {tela.ocr_imagem(img)!r}")

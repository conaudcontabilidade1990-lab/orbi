"""Autoteste do OCR: usado pelo GitHub antes de publicar (Orbi.exe --testar-ocr)."""
import sys
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def testar_ocr():
    from .tela import ocr_imagem

    img = Image.new("RGB", (700, 90), "white")
    try:
        fonte = ImageFont.load_default(size=40)
    except TypeError:
        fonte = ImageFont.load_default()
    ImageDraw.Draw(img).text((10, 20), "Empresa 611 ORBI", fill="black", font=fonte)
    resultado = {}

    def rodar():  # em thread, como no app
        try:
            resultado["texto"] = ocr_imagem(img, "pt-BR", preparar_img=False)
        except Exception as e:
            import traceback
            resultado["erro"] = traceback.format_exc()

    t = threading.Thread(target=rodar)
    t.start()
    t.join(60)
    saida = Path(sys.executable if getattr(sys, "frozen", False) else __file__).parent / "autoteste_ocr.txt"
    texto = resultado.get("texto", "")
    saida.write_text(f"texto: {texto!r}\nerro: {resultado.get('erro', '')}", encoding="utf-8")
    return 0 if "611" in texto else 1

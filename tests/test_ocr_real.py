"""OCR do Windows em telas do Domínio (roda no Windows do GitHub).

As imagens de teste têm só a interface do Domínio e códigos: nomes de clientes e valores
foram apagados (o repositório é público)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image  # noqa: E402

from orbi import config  # noqa: E402
from orbi.tela import faixa_destacada, norm, ocr_imagem, ocr_linhas  # noqa: E402

R, P = config.PADRAO["regioes"], config.PADRAO["pontos"]
troca = Image.open(Path(__file__).parent / "fixtures" / "troca_empresas_665.png")

# linha azul da Troca de empresas -> começa com "665"
x, y, w, h = R["troca_lista"]
lista = troca.crop((x, y, x + w, y + h))
y0, y1 = faixa_destacada(lista, P["troca_amostra_azul"][0] - x)
linha = norm(ocr_imagem(lista.crop((0, y0, w, y1 + 1))))
print("linha destacada:", linha)
assert linha.startswith("665"), linha

# localizar um texto na tela (usado para maximizar a janela)
achou = [(t, int(lx), int(ly)) for t, lx, ly, lw, lh in ocr_linhas(troca) if "troca de empresas" in norm(t)]
print("título:", achou)
assert achou and 440 <= achou[0][1] <= 470 and 132 <= achou[0][2] <= 150, achou
print("ok: OCR em telas do Domínio")

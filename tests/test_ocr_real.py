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

# acha a faixa azul (665, na 2ª linha) e lê uma linha comum da lista (662)
x, y, w, h = R["troca_lista"]
lista = troca.crop((x, y, x + w, y + h))
y0, y1 = faixa_destacada(lista, P["troca_amostra_azul"][0] - x)
assert 18 <= y0 <= 21, (y0, y1)
comum = norm(ocr_imagem(lista.crop((0, 0, 93, 18))))
print("linha comum:", comum)
assert comum.startswith("662"), comum

# localizar um texto na tela (usado para maximizar a janela)
achou = [(t, int(lx), int(ly)) for t, lx, ly, lw, lh in ocr_linhas(troca) if "troca de empresas" in norm(t)]
print("título:", achou)
assert achou and 440 <= achou[0][1] <= 470 and 132 <= achou[0][2] <= 150, achou
print("ok: OCR em telas do Domínio")

# Busca avançada (Entradas): título e linha do filtro "Acumulador | Igual a"
ba = Image.open(Path(__file__).parent / "fixtures" / "busca_avancada.png")
x, y, w, h = R["ba_titulo"]
titulo = norm(ocr_imagem(ba.crop((x, y, x + w, y + h))))
x, y, w, h = R["ba_linha"]
filtro = norm(ocr_imagem(ba.crop((x, y, x + w, y + h))))
print("busca avançada:", titulo, "|", filtro)
assert "busca avan" in titulo, titulo
assert "acumulador" in filtro and "iguala" in filtro.replace(" ", ""), filtro
print("ok: Busca avançada lida")

# código da empresa ativa lido sozinho (tela real: nome longe do código, "- 214")
cod = Image.open(Path(__file__).parent / "fixtures" / "codigo_empresa_214.png")
x, y, w, h = R["empresa_codigo"]
lido = norm(ocr_imagem(cod.crop((x, y, x + w, y + h))))
print("código da empresa:", lido)
assert "214" in lido.replace(" ", ""), lido
print("ok: código da empresa ativa")

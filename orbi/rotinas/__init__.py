"""Catálogo de rotinas do Orbi.

Para criar uma função nova: escreva uma classe que herde de Rotina (veja parcelas.py)
e acrescente uma instância na lista ROTINAS abaixo. Ela aparece sozinha na tela do app.
"""
from .base import Rotina, Resultado  # noqa: F401
from .parcelas import GerarParcelas, GerarParcelasEntradas
from .baixas import BaixarParcelas, BaixarParcelasTodas
from .xml_hub import ImportarXml, MarcarImportados, SepararXml

ROTINAS = [
    GerarParcelasEntradas(),
    GerarParcelas("saidas", "Gerar parcelas — Saídas", "menu_saidas", "saidas"),
    GerarParcelas("servicos", "Gerar parcelas — Serviços", "menu_servicos", "servicos"),
    BaixarParcelasTodas(),
    BaixarParcelas("baixas_entradas", "Baixar parcelas — Entradas", "entradas", "Pagar", "Pagar", "Entrada"),
    BaixarParcelas("baixas_saidas", "Baixar parcelas — Saídas", "saidas", "Receber", "Receber", "Emissão"),
    BaixarParcelas("baixas_servicos", "Baixar parcelas — Serviços", "servicos", "Receber", "Receber", "Emissão"),
    ImportarXml(),
    SepararXml(),
    MarcarImportados(),
]

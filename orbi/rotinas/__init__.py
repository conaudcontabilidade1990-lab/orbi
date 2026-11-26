"""Catálogo de rotinas do Orbi.

Para criar uma função nova: escreva uma classe que herde de Rotina (veja parcelas.py)
e acrescente uma instância na lista ROTINAS abaixo. Ela aparece sozinha na tela do app.
"""
from .base import Rotina, Resultado  # noqa: F401
from .parcelas import GerarParcelas, GerarParcelasEntradas

ROTINAS = [
    GerarParcelasEntradas(),
    GerarParcelas("saidas", "Gerar parcelas — Saídas", "menu_saidas", "saidas"),
    GerarParcelas("servicos", "Gerar parcelas — Serviços", "menu_servicos", "servicos"),
]

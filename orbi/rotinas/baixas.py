"""Baixa de parcelas: Movimentos > Baixas > Entradas / Saídas / Serviços.

Por empresa: período (Entrada/Emissão de X a Y), situação Aberta/Paga (Recebida) parcial, Buscar, Todos,
Pagar/Receber, Gerar (pode demorar) e, se débito = crédito (e não zerados), Gravar; senão Cancelar e pular.
A data de pagamento de cada parcela fica a do vencimento (não usa 'Alterar a data de pagamento').
"""
import calendar
import datetime as dt
import re

from .. import dominio as d
from .. import importacao as imp
from ..tela import Parar
from .base import Rotina

MENU_MOVIMENTOS = [
    "entradas", "saidas", "servicos", "reducoes z - modelo 2d", "cupom fiscal eletronico - cf-e", "outros",
    "estoque", "baixas", "apuracao", "parcelamento de impostos trimestrais", "parcelamento de impostos",
    "parcelamento de simples nacional", "pagamento de impostos",
    "pagamento de impostos via portal de servicos da rfb", "integracao contabil", "integracao honorarios",
    "rotinas automaticas", "enviar contas a pagar para conta azul", "movimentos"]
MENU_BAIXAS = ["entradas", "saidas", "servicos", "cupons fiscais", "rescisao de contrato imobiliario",
               "contratos de empresa simples de credito", "cupons fiscais eletronicos - cf-e"]

# a partir do [X] da janela "Parcelas a Pagar/Receber"
L_DATA_INI, L_DATA_FIM = (-750, 60), (-618, 60)
L_LER_INI, L_LER_FIM = (-760, 49, 70, 22), (-627, 49, 70, 22)
L_RADIO_PERIODO, L_RADIO_ABERTA = (-839, 60), (-482, 59)
L_BUSCAR, L_LER_BUSCAR = (-187, 462), (-213, 452, 70, 20)
L_TODOS, L_PAGAR, L_FECHAR = (-804, 462), (-55, 47), (-55, 111)
# a partir do [X] da janela "Baixa de Parcelas"
B_GERAR, B_GRAVAR, B_CANCELAR = (-168, 492), (-45, 47), (-45, 79)
B_DEBITO, B_CREDITO = (-552, 431, 115, 19), (-272, 431, 105, 19)


def _r(xis, off):
    x, y = xis
    return (x + off[0], y + off[1]) if len(off) == 2 else (x + off[0], y + off[1], off[2], off[3])


def valor(txt):
    """'1.234,56' (ou '0.76', como o OCR às vezes lê) -> 1234.56; sem número -> None."""
    m = re.search(r"-?\d[\d.]*[.,]\d{2}(?!\d)", txt or "")
    if not m:
        return None
    bruto = m.group(0).replace(" ", "")
    inteiro, dec = bruto[:-3], bruto[-2:]
    return float(re.sub(r"[.,]", "", inteiro) + "." + dec)


def data_confere(txt, data):
    """O OCR às vezes lê a barra '/' como 1, l ou |: aceita '01110/2026' para 01/10/2026."""
    sep = r"[/1l|i!\\]"
    padrao = rf"{data:%d}{sep}{data:%m}{sep}{data:%Y}"
    return re.search(padrao, (txt or "").replace(" ", "")) is not None


def _janela_lista(t):
    """[X] da janela 'Parcelas a Pagar/Receber' (o OCR às vezes lê 'parceias')."""
    for xis in t.botoes_fechar("area_janelas"):
        tit = imp._titulo_da_janela(t, xis)
        if ("pagar" in tit or "receber" in tit) and "baixa" not in tit:
            return xis
    return None


def periodo_da_competencia(comp):
    (a1, m1), (a2, m2) = comp
    return dt.date(a1, m1, 1), dt.date(a2, m2, calendar.monthrange(a2, m2)[1])


class BaixarParcelas(Rotina):
    departamento = "fiscal"
    usa_competencia = True
    usa_periodo = True

    def __init__(self, id_, nome, item, titulo, botao, radio_periodo):
        self.id, self.nome, self.item, self.titulo, self.botao = id_, nome, item, titulo, botao
        self.radio_periodo = radio_periodo
        self.periodo = None
        self.descricao = (f"Movimentos > Baixas > {item.capitalize()}: período ({radio_periodo}) de/até, situação "
                          f"aberta/parcial, Buscar, Todos, {botao}, Gerar e, se débito = crédito, Gravar "
                          "(senão cancela e pula a empresa). Em simulação vai até o Gerar e cancela.")

    # ---- telas ----
    def _abrir(self, t):
        W, H = t.cfg["resolucao"]
        toda = (0, 0, W, H - 40)
        t.clicar("menu_movimentos", espera=0.6)
        xb, _ = imp._item(t, "baixas", MENU_MOVIMENTOS, toda, "Baixas")
        imp._item(t, self.item, MENU_BAIXAS + MENU_MOVIMENTOS, (xb + 150, 0, W - xb - 150, H - 40),
                  self.item.capitalize())
        xis = t.aguardar(lambda: _janela_lista(t), 10, intervalo=0.4)
        if not xis:
            raise Parar(f"A tela 'Parcelas a {self.titulo}' não abriu.")
        return xis

    def _data(self, t, xis, clique, regiao, data, nome):
        alvo = data.strftime("%d/%m/%Y")
        lido = ""
        for _ in range(2):
            t.clicar_em(*_r(xis, clique), espera=0.2)
            t.teclas("home")
            t.digitar(data.strftime("%d%m%Y"), espera=0.3)
            t.teclas("tab")                      # sai do campo: o cursor atrapalhava a leitura
            t.dormir(0.4)
            for fator, binar in ((3, False), (4, True), (5, False)):
                lido = t.ler(_r(xis, regiao), fator=fator, binarizar=binar)
                if data_confere(lido, data):
                    return
        raise Parar(f"Não consegui preencher a data {nome} com {alvo} (lido: '{lido}').")

    def _marcar(self, t, xis, off, nome):
        x, y = _r(xis, off)
        t.clicar_em(x, y, espera=0.3)
        if max(t.escuros_em(cx, y) for cx in range(x - 4, x + 5, 2)) < 9:
            raise Parar(f"Não consegui marcar a opção '{nome}'.")

    def _fechar_lista(self, t, xis):
        t.clicar_em(*_r(xis, L_FECHAR), espera=0.8)
        if not t.aguardar(lambda: not _janela_lista(t), 5, intervalo=0.4):
            d.fechar_janelas_abertas(t)

    def _totais(self, t, bx):
        return valor(t.ler(_r(bx, B_DEBITO))), valor(t.ler(_r(bx, B_CREDITO)))

    # ---- por empresa ----
    def executar_empresa(self, t, codigo, simular):
        ini, fim = self.periodo or periodo_da_competencia(self.competencia)
        d.trazer_para_frente(t)
        d.trocar_empresa(t, codigo)
        xis = self._abrir(t)
        self._marcar(t, xis, L_RADIO_PERIODO, self.radio_periodo)
        self._data(t, xis, L_DATA_INI, L_LER_INI, ini, "inicial")
        self._data(t, xis, L_DATA_FIM, L_LER_FIM, fim, "final")
        self._marcar(t, xis, L_RADIO_ABERTA, "Aberta/parcial")
        t.clicar_em(*_r(xis, L_BUSCAR), espera=0.8)

        def busca():
            if "nao foram encontrados" in t.ler("mensagem"):
                return "vazio"
            return "lista" if "selecionar" in t.ler(_r(xis, L_LER_BUSCAR)) else None
        r = t.aguardar(busca, t.T["busca"], intervalo=0.5)
        if r == "vazio":
            t.teclas("enter")
            t.dormir(0.6)
            self._fechar_lista(t, xis)
            return f"sem parcelas em aberto de {ini:%d/%m/%Y} a {fim:%d/%m/%Y}"
        if r != "lista":
            raise Parar("A busca das parcelas não terminou (nem lista nem 'Não foram encontrados registros').")

        t.clicar_em(*_r(xis, L_TODOS), espera=0.6)
        t.clicar_em(*_r(xis, L_PAGAR), espera=1.0)
        # com muitas parcelas o Domínio demora para montar a tela de baixa: espera (até 30 min)
        bx, esperado = None, 0
        while not bx and esperado < 1800:
            bx = t.aguardar(lambda: imp._janela(t, "baixa de"), 30, intervalo=0.5)
            esperado += 30
            if not bx:
                m = t.ler("mensagem")
                if "selecione" in m or "nenhuma parcela" in m:
                    raise Parar(f"O Domínio avisou depois do {self.botao}: '{m[:120]}'. Não respondi nada.")
                t.log(f"  aguardando a tela 'Baixa de Parcelas' abrir... {esperado // 60} min {esperado % 60} s")
        if not bx:
            raise Parar(f"A tela 'Baixa de Parcelas' não abriu em 30 min depois do {self.botao}.")

        t.clicar_em(*_r(bx, B_GERAR), espera=1.5)
        t.log("  gerando os lançamentos contábeis... (pode demorar)")
        # espera o Domínio terminar: totais iguais por 3 leituras seguidas, sem 'aguarde' na tela
        limite, iguais, ultimo, esperado = 3 * 3600, 0, None, 0
        while esperado < limite:
            t.dormir(2)
            esperado += 2
            if t.ocupado() or any(k in t.ler("mensagem") for k in ("aguarde", "processando", "gerando")):
                iguais = 0                       # Domínio trabalhando (cursor de espera ou aviso na tela)
                continue
            atual = self._totais(t, bx)
            iguais = iguais + 1 if atual == ultimo else 0
            ultimo = atual
            deb, cred = atual
            pronto = deb is not None and cred is not None and deb == cred and deb > 0
            # pronto: débito = crédito estável; zerado/diferente: só desiste depois de 3 min sem mudar nada
            if (pronto and iguais >= 2) or (iguais >= 90):
                break
            if esperado % 300 == 0:
                t.log(f"  ainda gerando... {esperado // 60} min")
        deb, cred = ultimo or (None, None)
        ok = deb is not None and cred is not None and deb == cred and deb > 0
        if simular or not ok:
            foto = t.foto(f"{'simulacao' if simular else 'nao_gravado'}_{codigo}")
            t.log(f"  tela salva: {foto.name}")
            t.clicar_em(*_r(bx, B_CANCELAR), espera=1.0)
            t.aguardar(lambda: not imp._janela(t, "baixa de"), 10, intervalo=0.5)
            self._fechar_lista(t, xis)
            if simular:
                return f"SIMULAÇÃO — débito {deb} / crédito {cred}; cancelado, nada gravado"
            t.aviso(f"débito {deb} ≠ crédito {cred}: não gravei")
            return f"NÃO gravado — débito {deb} e crédito {cred} diferentes ou zerados; cancelei e pulei"

        t.clicar_em(*_r(bx, B_GRAVAR), espera=1.0)

        def gravou():
            m = t.ler("mensagem")
            return m if ("lancamento" in m and any(k in m for k in ("realizad", "gravad", "sucesso"))) else None
        if not t.aguardar(gravou, 1800, intervalo=1.0):
            raise Parar("Não vi a mensagem de lançamentos realizados/gravados depois do Gravar "
                        f"(último aviso lido: '{t.ler('mensagem')[:120]}'). Não cliquei em mais nada.")
        t.teclas("enter")
        t.dormir(1.0)
        if imp._janela(t, "baixa de"):
            raise Parar("Depois de gravar, a tela 'Baixa de Parcelas' continuou aberta. Parei para conferir.")
        self._fechar_lista(t, xis)
        return f"baixado e gravado — débito = crédito = {deb:.2f}"

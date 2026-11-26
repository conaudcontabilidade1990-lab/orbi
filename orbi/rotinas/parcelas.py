"""Gerar parcelas de notas sem parcelas — Saídas, Serviços (1 dia) e Entradas (2554 = 25 dias).

Regras (iguais às rotinas manuais):
- "Listar somente notas sem parcelas" sempre marcada antes de todo Buscar;
- seleção só pelo botão Todos; parcelas = 1; vencimento "Informar" com 1 dia;
- nunca "Excluir Parcelas"; nunca gerar duas vezes; qualquer coisa fora do previsto = parar.
"""
import re

from .. import dominio as d
from ..tela import Parar
from .base import Rotina


class GerarParcelas(Rotina):
    precisa_regioes = ("campo_parcelas",)

    def __init__(self, id_, nome, ponto_menu, palavra_titulo, dias=1, departamento="fiscal"):
        self.id = id_
        self.departamento = departamento
        self.nome = nome
        self.ponto_menu = ponto_menu
        self.palavra_titulo = palavra_titulo
        self.dias = dias
        self.descricao = (f"Gera 1 parcela com vencimento em {dias} dia(s) para as notas "
                          f"sem parcelas, empresa por empresa. Sem confirmação a cada empresa.")

    # ---- passos ----
    def _buscar(self, t):
        d.garantir_caixa(t, "caixa_sem_parcelas", True)
        rotulo = t.ler("botao_buscar")
        if "buscar" not in rotulo:
            raise Parar(f"O botão Buscar não está disponível (lido: '{rotulo}').")
        t.clicar("buscar", espera=0.2)
        return self._resultado_busca(t)

    def _resultado_busca(self, t):
        """Segue assim que aparecer a mensagem de lista vazia OU a primeira linha de notas."""
        def estado():
            if any(x in t.ler("mensagem") for x in d.MSG["vazio"]):
                return "vazio"
            return "lista" if t.tem_linhas() else ""
        r = t.aguardar(estado, t.T["busca"], intervalo=0.3)
        if r == "vazio":
            t.clicar("btn_ok_vazio", espera=0.4)
            return "vazio"
        if r != "lista":
            raise Parar("A busca não terminou no tempo limite (nem lista, nem mensagem). Nada foi gerado.")
        t.dormir(0.6)  # deixa a lista terminar de desenhar antes do Todos
        return "lista"

    def _ler_campo(self, t, regiao, esperado, tentativas=3):
        lido = ""
        for _ in range(tentativas):  # o Domínio às vezes demora a redesenhar o campo
            lido = t.ler_numero(regiao)
            if lido == esperado:
                break
            t.dormir(0.5)
        return lido

    def _configurar_dialogo(self, t, dias=None):
        dias = self.dias if dias is None else dias
        t.clicar("todos", espera=0.6)
        t.clicar("gerar_abrir", espera=0.2)
        texto = t.aguardar(lambda: (lambda x: x if "quantidade de parcelas" in x else "")(t.ler("dialogo_gerar")), 8) \
            or t.ler("dialogo_gerar")
        if "vencimento" not in texto or "quantidade de parcelas" not in texto:
            raise Parar(f"O diálogo de geração não apareceu como esperado (lido: '{texto[:120]}').")
        t.clicar("venc_dropdown", espera=0.5)
        t.clicar("venc_informar", espera=0.5)
        t.clicar("campo_dias", triplo=True, espera=0.25)
        t.digitar(dias, espera=0.2)
        t.teclas("tab")          # tira o cursor do campo e confirma o valor
        t.dormir(0.5)

        erros = []
        venc = t.ler("campo_vencimento")
        if "informar" not in venc:
            erros.append(f"vencimento lido = '{venc}', esperado 'Informar'")
        if t.escuros("radio_somente") <= t.escuros("radio_todas"):
            erros.append("'Somente as notas selecionadas' não está marcado")
        parc = self._ler_campo(t, "campo_parcelas", "1")
        if parc != "1":
            erros.append(f"parcelas lido = '{parc}', esperado 1")
        lido = self._ler_campo(t, "campo_dias", str(dias))
        if lido != str(dias):
            erros.append(f"dias lido = '{lido}', esperado {dias}")
        if erros:
            raise Parar("Diálogo com valores diferentes do esperado: " + "; ".join(erros))

    def _gerar(self, t):
        t.clicar("dlg_gerar", espera=0.2)
        if t.esperar("mensagem", {"certeza": d.MSG["certeza"]}, t.T["confirmacao"]) != "certeza":
            raise Parar("Não apareceu a confirmação 'Você tem certeza...' — não cliquei em nada.")
        t.clicar("btn_sim", espera=0.3)
        t.log("  gerando... aguardando a mensagem de sucesso")
        if t.esperar("mensagem", {"sucesso": d.MSG["sucesso"]}, t.T["sucesso"], intervalo=0.8) != "sucesso":
            raise Parar("Não vi 'Parcelas geradas com sucesso.' no tempo limite. NÃO gerei de novo.")
        t.clicar("btn_ok_sucesso", espera=0.6)

    # ---- por empresa ----
    def executar_empresa(self, t, codigo, simular):
        d.trazer_para_frente(t)
        d.trocar_empresa(t, codigo)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)

        if self._buscar(t) == "vazio":
            d.fechar_janela(t)
            return "sem notas sem parcelas"

        self._configurar_dialogo(t)
        if simular:
            t.foto(f"simulacao_{codigo}")
            t.clicar("dlg_cancelar", espera=0.5)
            d.fechar_janela(t)
            return "SIMULAÇÃO ok — diálogo conferido e cancelado, nada gerado"

        self._gerar(t)
        if "quantidade de parcelas" in t.ler("dialogo_gerar"):
            t.clicar("dlg_cancelar", espera=0.5)
        # conferência: fecha, reabre e busca de novo — deve vir vazio
        d.fechar_janela(t)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)
        if self._buscar(t) != "vazio":
            d.fechar_janela(t)
            raise Parar("Depois de gerar, a nova busca ainda trouxe notas. Não gerei de novo.")
        d.fechar_janela(t)
        return f"parcelas geradas (1 parcela, {self.dias} dia)"


class GerarParcelasEntradas(GerarParcelas):
    """Entradas: notas do acumulador 2554 com 25 dias; demais com 1 dia (sempre nesta ordem).

    1. Busca avançada (Acumulador igual a 2554) -> Todos -> 25 dias -> gera; confere repetindo a
       busca filtrada (deve vir vazia).
    2. Reabre a janela, Buscar normal (as 2554 já têm parcelas e não aparecem) -> Todos -> 1 dia.
    "Listar notas de acumuladores que não geram parcelas" fica sempre DESMARCADA.
    """

    ACUMULADOR = "2554"
    DIAS_2554 = 25

    def __init__(self):
        super().__init__("entradas", "Gerar parcelas — Entradas", "menu_entradas", "entradas", dias=1)
        self.descricao = ("Gera 1 parcela para as notas de entrada sem parcelas: acumulador 2554 com "
                          "vencimento em 25 dias e as demais em 1 dia (nessa ordem). Nunca inclui "
                          "acumuladores que não geram parcelas.")

    def _caixas(self, t):
        d.garantir_caixa(t, "caixa_sem_parcelas", True)
        d.garantir_caixa(t, "caixa_nao_geram", False)

    def _buscar(self, t):
        self._caixas(t)
        return super()._buscar(t)

    def _busca_2554(self, t):
        self._caixas(t)
        t.clicar("busca_avancada", espera=0.2)
        if t.esperar("ba_titulo", {"ok": ["busca avan"]}, 6, intervalo=0.25) != "ok":
            raise Parar("A janela Busca avançada não abriu.")
        t.clicar("ba_coluna", espera=0.4)
        t.digitar("a", espera=0.6)               # "Acumulador" é a única coluna com A
        t.clicar("ba_valor", triplo=True, espera=0.3)
        t.digitar(self.ACUMULADOR, espera=0.2)
        t.teclas("tab")                          # tira o cursor do Valor (vai para Operador)
        t.dormir(0.5)
        ok_col, ok_cond, valor, lidos = self._ler_filtro(t)
        if not (ok_col and ok_cond and valor == self.ACUMULADOR):
            t.dormir(0.8)                        # tela ainda redesenhando: lê de novo
            ok_col, ok_cond, valor, lidos = self._ler_filtro(t)
        if not (ok_col and ok_cond and valor == self.ACUMULADOR):
            t.clicar("ba_cancelar", espera=0.5)
            raise Parar(f"Não consegui confirmar o filtro 'Acumulador igual a {self.ACUMULADOR}' "
                        f"(lido: {lidos}). Nada foi gerado.")
        t.clicar("ba_ok", espera=0.2)
        return self._resultado_busca(t)

    def _ler_filtro(self, t):
        """Confere célula por célula (ler a linha inteira cortava a 1ª e a última letra)."""
        coluna = t.ler("ba_coluna_cel", fator=4, borda=8)
        condicao = t.ler("ba_condicao_cel", fator=4, borda=8).replace(" ", "")
        valor = ""
        for fator in (4, 6):
            valor = re.sub(r"\D", "", t.ler("ba_valor_cel", fator=fator, binarizar=True, borda=12))
            if valor == self.ACUMULADOR:
                break
        ok_col = "cumulador" in coluna or "acumul" in coluna
        ok_cond = "igual" in condicao
        return ok_col, ok_cond, valor, f"coluna '{coluna}', condição '{condicao}', valor '{valor}'"

    def _reabrir(self, t):
        d.fechar_janela(t)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)

    def _cancelar_dialogo_aberto(self, t):
        if "quantidade de parcelas" in t.ler("dialogo_gerar"):
            t.clicar("dlg_cancelar", espera=0.5)

    def executar_empresa(self, t, codigo, simular):
        d.trazer_para_frente(t)
        d.trocar_empresa(t, codigo)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)
        feitos = []

        # 1) acumulador 2554 — 25 dias
        if self._busca_2554(t) == "lista":
            self._configurar_dialogo(t, self.DIAS_2554)
            if simular:
                t.foto(f"simulacao_{codigo}_2554")
                t.clicar("dlg_cancelar", espera=0.5)
                feitos.append("2554: diálogo com 25 dias conferido")
            else:
                self._gerar(t)
                self._cancelar_dialogo_aberto(t)
                self._reabrir(t)
                if self._busca_2554(t) != "vazio":
                    d.fechar_janela(t)
                    raise Parar("Depois de gerar o 2554, a busca filtrada ainda trouxe notas. Parei antes das demais.")
                feitos.append("2554 com 25 dias")

        # 2) demais acumuladores — 1 dia
        self._reabrir(t)
        if self._buscar(t) == "lista":
            self._configurar_dialogo(t, self.dias)
            if simular:
                t.foto(f"simulacao_{codigo}_demais")
                t.clicar("dlg_cancelar", espera=0.5)
                feitos.append("demais: diálogo com 1 dia conferido")
            else:
                self._gerar(t)
                self._cancelar_dialogo_aberto(t)
                self._reabrir(t)
                if self._buscar(t) != "vazio":
                    d.fechar_janela(t)
                    raise Parar("Depois de gerar, a nova busca ainda trouxe notas. Não gerei de novo.")
                feitos.append("demais com 1 dia")
        d.fechar_janela(t)

        if not feitos:
            return "sem entradas sem parcelas"
        if simular:
            return "SIMULAÇÃO ok — " + "; ".join(feitos) + "; nada gerado"
        return "parcelas geradas: " + " e ".join(feitos)

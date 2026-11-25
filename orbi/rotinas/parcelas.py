"""Gerar parcelas de notas sem parcelas (1 parcela, 1 dia) — Saídas e Serviços.

Regras (iguais às rotinas manuais):
- "Listar somente notas sem parcelas" sempre marcada antes de todo Buscar;
- seleção só pelo botão Todos; parcelas = 1; vencimento "Informar" com 1 dia;
- nunca "Excluir Parcelas"; nunca gerar duas vezes; qualquer coisa fora do previsto = parar.
"""
from .. import dominio as d
from ..tela import Parar
from .base import Rotina


class GerarParcelas(Rotina):
    precisa_regioes = ("campo_parcelas",)

    def __init__(self, id_, nome, ponto_menu, palavra_titulo, dias=1):
        self.id = id_
        self.nome = nome
        self.ponto_menu = ponto_menu
        self.palavra_titulo = palavra_titulo
        self.dias = dias
        self.descricao = (f"Gera 1 parcela com vencimento em {dias} dia(s) para as notas "
                          f"sem parcelas, empresa por empresa. Sem confirmação a cada empresa.")

    # ---- passos ----
    def _buscar(self, t):
        d.garantir_caixa(t, "caixa_sem_parcelas", True)
        t.clicar("buscar", espera=1)
        if t.esperar("mensagem", {"vazio": d.MSG["vazio"]}, t.T["busca"]) == "vazio":
            t.clicar("btn_ok_vazio", espera=1)
            return "vazio"
        return "lista"

    def _configurar_dialogo(self, t):
        t.clicar("todos", espera=1.2)
        t.clicar("gerar_abrir", espera=2)
        texto = t.ler("dialogo_gerar")
        if "vencimento" not in texto:
            raise Parar(f"O diálogo de geração não apareceu como esperado (lido: '{texto}').")
        t.clicar("venc_dropdown")
        t.clicar("venc_informar")
        t.clicar("campo_dias", triplo=True, espera=0.3)
        t.digitar(self.dias, espera=1.2)

        texto = t.ler("dialogo_gerar")
        erros = []
        if "informar" not in texto:
            erros.append("vencimento não está em 'Informar'")
        if "somente" not in texto:
            erros.append("não achei 'Somente as notas selecionadas'")
        dias = t.ler("campo_dias", digitos=True)
        if dias != str(self.dias):
            erros.append(f"dias lido = '{dias}', esperado {self.dias}")
        if t.R.get("campo_parcelas"):
            parc = t.ler("campo_parcelas", digitos=True)
            if parc != "1":
                erros.append(f"parcelas lido = '{parc}', esperado 1")
        if erros:
            raise Parar("Diálogo com valores diferentes do esperado: " + "; ".join(erros))

    def _gerar(self, t):
        t.clicar("dlg_gerar", espera=1.5)
        if t.esperar("mensagem", {"certeza": d.MSG["certeza"]}, t.T["confirmacao"]) != "certeza":
            raise Parar("Não apareceu a confirmação 'Você tem certeza...' — não cliquei em nada.")
        t.clicar("btn_sim", espera=2)
        t.log("  gerando... aguardando a mensagem de sucesso")
        if t.esperar("mensagem", {"sucesso": d.MSG["sucesso"]}, t.T["sucesso"], intervalo=3) != "sucesso":
            raise Parar("Não vi 'Parcelas geradas com sucesso.' no tempo limite. NÃO gerei de novo.")
        t.clicar("btn_ok_sucesso", espera=1.5)

    # ---- por empresa ----
    def executar_empresa(self, t, codigo, simular):
        d.trocar_empresa(t, codigo)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)

        if self._buscar(t) == "vazio":
            d.fechar_janela(t)
            return "sem notas sem parcelas"

        self._configurar_dialogo(t)
        if simular:
            t.foto(f"simulacao_{codigo}")
            t.clicar("dlg_cancelar", espera=1)
            d.fechar_janela(t)
            return "SIMULAÇÃO ok — diálogo conferido e cancelado, nada gerado"

        self._gerar(t)
        if "vencimento" in t.ler("dialogo_gerar"):
            t.clicar("dlg_cancelar", espera=1)
        if self._buscar(t) != "vazio":
            raise Parar("Depois de gerar, a nova busca ainda trouxe notas. Não gerei de novo.")
        d.fechar_janela(t)
        return f"parcelas geradas (1 parcela, {self.dias} dia)"

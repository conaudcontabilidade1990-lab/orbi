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
        t.clicar("buscar", espera=1)
        if t.esperar("mensagem", {"vazio": d.MSG["vazio"]}, t.T["busca"]) == "vazio":
            t.clicar("btn_ok_vazio", espera=1)
            return "vazio"
        return "lista"

    def _ler_campo(self, t, regiao, esperado, tentativas=3):
        lido = ""
        for _ in range(tentativas):  # o Domínio às vezes demora a redesenhar o campo
            lido = t.ler_numero(regiao)
            if lido == esperado:
                break
            t.dormir(1)
        return lido

    def _configurar_dialogo(self, t):
        t.clicar("todos", espera=1.2)
        t.clicar("gerar_abrir", espera=2)
        texto = t.ler("dialogo_gerar")
        if "vencimento" not in texto or "quantidade de parcelas" not in texto:
            raise Parar(f"O diálogo de geração não apareceu como esperado (lido: '{texto[:120]}').")
        t.clicar("venc_dropdown", espera=1)
        t.clicar("venc_informar", espera=1)
        t.clicar("campo_dias", triplo=True, espera=0.3)
        t.digitar(self.dias, espera=0.5)
        t.teclas("tab")          # tira o cursor do campo e confirma o valor
        t.dormir(1.2)

        erros = []
        venc = t.ler("campo_vencimento")
        if "informar" not in venc:
            erros.append(f"vencimento lido = '{venc}', esperado 'Informar'")
        if t.escuros("radio_somente") <= t.escuros("radio_todas"):
            erros.append("'Somente as notas selecionadas' não está marcado")
        parc = self._ler_campo(t, "campo_parcelas", "1")
        if parc != "1":
            erros.append(f"parcelas lido = '{parc}', esperado 1")
        dias = self._ler_campo(t, "campo_dias", str(self.dias))
        if dias != str(self.dias):
            erros.append(f"dias lido = '{dias}', esperado {self.dias}")
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
        d.trazer_para_frente(t)
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
        if "quantidade de parcelas" in t.ler("dialogo_gerar"):
            t.clicar("dlg_cancelar", espera=1)
        # conferência: fecha, reabre e busca de novo — deve vir vazio
        d.fechar_janela(t)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)
        if self._buscar(t) != "vazio":
            d.fechar_janela(t)
            raise Parar("Depois de gerar, a nova busca ainda trouxe notas. Não gerei de novo.")
        d.fechar_janela(t)
        return f"parcelas geradas (1 parcela, {self.dias} dia)"

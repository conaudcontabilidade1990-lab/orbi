"""Gerar parcelas de notas sem parcelas — Saídas, Serviços (1 dia) e Entradas (2554 = 25 dias).

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

    def _configurar_dialogo(self, t, dias=None):
        dias = self.dias if dias is None else dias
        t.clicar("todos", espera=1.2)
        t.clicar("gerar_abrir", espera=2)
        texto = t.ler("dialogo_gerar")
        if "vencimento" not in texto or "quantidade de parcelas" not in texto:
            raise Parar(f"O diálogo de geração não apareceu como esperado (lido: '{texto[:120]}').")
        t.clicar("venc_dropdown", espera=1)
        t.clicar("venc_informar", espera=1)
        t.clicar("campo_dias", triplo=True, espera=0.3)
        t.digitar(dias, espera=0.5)
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
        lido = self._ler_campo(t, "campo_dias", str(dias))
        if lido != str(dias):
            erros.append(f"dias lido = '{lido}', esperado {dias}")
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
        t.clicar("busca_avancada", espera=1.5)
        if t.esperar("ba_titulo", {"ok": ["busca avancada"]}, 6, intervalo=0.7) != "ok":
            raise Parar("A janela Busca avançada não abriu.")
        t.clicar("ba_coluna", espera=0.6)
        t.digitar("a", espera=1)                 # "Acumulador" é a única coluna com A
        t.clicar("ba_valor", triplo=True, espera=0.4)
        t.digitar(self.ACUMULADOR, espera=1)
        linha = t.ler("ba_linha")
        compacta = linha.replace(" ", "")
        if "acumulador" not in linha or "iguala" not in compacta or self.ACUMULADOR not in compacta:
            t.clicar("ba_cancelar", espera=1)
            raise Parar(f"Não consegui montar o filtro 'Acumulador igual a {self.ACUMULADOR}' "
                        f"(lido: '{linha}'). Nada foi gerado.")
        t.clicar("ba_ok", espera=1)
        if t.esperar("mensagem", {"vazio": d.MSG["vazio"]}, t.T["busca"]) == "vazio":
            t.clicar("btn_ok_vazio", espera=1)
            return "vazio"
        return "lista"

    def _reabrir(self, t):
        d.fechar_janela(t)
        d.abrir_gerar_parcelas(t, self.ponto_menu, self.palavra_titulo)

    def _cancelar_dialogo_aberto(self, t):
        if "quantidade de parcelas" in t.ler("dialogo_gerar"):
            t.clicar("dlg_cancelar", espera=1)

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
                t.clicar("dlg_cancelar", espera=1)
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
                t.clicar("dlg_cancelar", espera=1)
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

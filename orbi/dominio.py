"""Passos comuns do Domínio Escrita Fiscal, reaproveitados pelas rotinas."""
import re

from .tela import Parar

MSG = {
    "vazio": ["foram encontrados", "encontrados registros", "estas caracteristicas"],
    "certeza": ["tem certeza", "certeza"],
    "sucesso": ["com sucesso", "geradas com"],
    "fechar_janelas": ["fechar todas as janelas"],
}


def trazer_para_frente(t):
    t.clicar("titulo_app", espera=1)


def empresa_ativa_e(t, codigo):
    return re.search(rf"\b{re.escape(codigo)}\b", t.ler("empresa_ativa")) is not None


def trocar_empresa(t, codigo):
    if empresa_ativa_e(t, codigo):
        t.log(f"  empresa {codigo} já está ativa")
        return
    t.clicar("troca_empresa", espera=1.5)
    if t.esperar("mensagem", {"x": MSG["fechar_janelas"]}, 1):
        raise Parar("O Domínio pediu para fechar todas as janelas antes de trocar de empresa.")
    t.clicar("troca_busca")
    t.teclas("ctrl", "a")
    t.digitar(codigo, espera=1.5)
    t.clicar("troca_acessar", espera=3)
    if not empresa_ativa_e(t, codigo):
        # às vezes o primeiro clique em Acessar não fecha o diálogo
        if "troca de empresa" in t.ler((0, 0, *t.cfg["resolucao"])):
            t.clicar("troca_acessar", espera=3)
        if not empresa_ativa_e(t, codigo):
            raise Parar(f"Não consegui confirmar que a empresa {codigo} ficou ativa "
                        f"(lido no canto: '{t.ler('empresa_ativa')}').")
    t.log(f"  empresa {codigo} ativa")


def abrir_gerar_parcelas(t, ponto_menu, palavra_titulo):
    """Utilitários > Parcelas > Gerar Parcelas > (Entradas/Saídas/Serviços), maximizada."""
    t.clicar("menu_utilitarios")
    t.clicar("menu_parcelas")
    t.clicar("menu_gerar")
    t.clicar(ponto_menu, espera=2.5)
    t.clicar("maximizar", espera=2)
    titulo = t.ler("titulo_janela")
    if "gerar parcelas" not in titulo or palavra_titulo not in titulo:
        raise Parar(f"A janela aberta não parece ser a esperada (título lido: '{titulo}').")


def garantir_caixa(t, ponto, marcada):
    if t.caixa_marcada(ponto) != marcada:
        t.clicar(ponto)
        if t.caixa_marcada(ponto) != marcada:
            raise Parar(f"Não consegui {'marcar' if marcada else 'desmarcar'} a caixa '{ponto}'.")
        t.log(f"  caixa '{ponto}' corrigida para {'marcada' if marcada else 'desmarcada'}")


def fechar_janela(t):
    t.clicar("fechar_janela", espera=1.5)

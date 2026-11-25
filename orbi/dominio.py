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
    t.clicar("troca_por_codigo")          # a busca pode estar em "Apelido"
    t.clicar("troca_busca")
    t.teclas("ctrl", "a")
    t.digitar(codigo, espera=1.5)
    linha = t.ler("troca_linha")
    if not re.match(rf"\s*{re.escape(codigo)}(?!\d)", linha):
        t.clicar("troca_fechar", espera=1)
        raise Parar(f"A empresa {codigo} não apareceu selecionada na Troca de empresas "
                    f"(linha lida: '{linha}'). Não acessei.")
    t.clicar("troca_acessar", espera=3)
    if not empresa_ativa_e(t, codigo):
        t.dormir(3)  # o Domínio às vezes demora a atualizar o canto
        if not empresa_ativa_e(t, codigo):
            raise Parar(f"Não consegui confirmar que a empresa {codigo} ficou ativa "
                        f"(lido no canto: '{t.ler('empresa_ativa')}').")
    t.log(f"  empresa {codigo} ativa")


def janela_maximizada(t, palavra_titulo):
    titulo = t.ler("titulo_app")
    return "gerar parcelas" in titulo and palavra_titulo in titulo


def abrir_gerar_parcelas(t, ponto_menu, palavra_titulo):
    """Utilitários > Parcelas > Gerar Parcelas > (Entradas/Saídas/Serviços), maximizada."""
    t.clicar("menu_utilitarios", espera=1)
    t.clicar("menu_parcelas", espera=1)
    t.clicar("menu_gerar", espera=1)
    t.clicar(ponto_menu, espera=2.5)
    if not janela_maximizada(t, palavra_titulo):
        x, y = t.P["titulo_janela_normal"]
        t.duplo(x, y, espera=2)
    if not janela_maximizada(t, palavra_titulo):
        raise Parar(f"A janela Gerar Parcelas ({palavra_titulo}) não abriu maximizada "
                    f"(título lido: '{t.ler('titulo_app')}').")


def garantir_caixa(t, ponto, marcada):
    if t.caixa_marcada(ponto) != marcada:
        t.clicar(ponto)
        if t.caixa_marcada(ponto) != marcada:
            raise Parar(f"Não consegui {'marcar' if marcada else 'desmarcar'} a caixa '{ponto}'.")
        t.log(f"  caixa '{ponto}' corrigida para {'marcada' if marcada else 'desmarcada'}")


def fechar_janela(t):
    t.clicar("fechar_janela", espera=1.5)

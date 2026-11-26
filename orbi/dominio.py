"""Passos comuns do Domínio Escrita Fiscal, reaproveitados pelas rotinas."""
import re
import time

from .tela import Parar

MSG = {
    "vazio": ["foram encontrados", "encontrados registros", "estas caracteristicas"],
    "certeza": ["tem certeza", "certeza"],
    "sucesso": ["com sucesso", "geradas com"],
    "fechar_janelas": ["fechar todas as janelas"],
}


def trazer_para_frente(t):
    """Acha o Domínio (mesmo atrás de outra janela, minimizado ou no outro monitor), maximiza no
    monitor principal e confere pelo título lido na tela. Testa as candidatas uma a uma."""
    from . import janela
    candidatas, diag = janela.achar()
    if not candidatas:
        raise Parar("Não encontrei a janela do Domínio Escrita Fiscal aberta. "
                    f"Janelas vistas: {diag}")
    lido = ""
    for hwnd in candidatas[:4]:
        t.checar()
        janela.trazer_para_frente(hwnd)
        t.clicar("titulo_app", espera=1)   # já maximizado no principal: o título fica neste ponto
        lido = t.ler("titulo_app")
        if "dominio escrita fiscal" in lido:
            return
    raise Parar("Não consegui trazer o Domínio Escrita Fiscal para a frente "
                f"(título lido: '{lido}').")


def empresa_ativa_e(t, codigo):
    return re.search(rf"\b{re.escape(codigo)}\b", t.ler("empresa_ativa")) is not None


def trocar_empresa(t, codigo):
    if empresa_ativa_e(t, codigo):
        t.log(f"  empresa {codigo} já está ativa")
        return
    espera = t.T.get("troca", 8)
    t.clicar("troca_empresa", espera=1)
    if t.esperar("troca_titulo", {"ok": ["troca de empresa"]}, espera, intervalo=0.7) != "ok":
        if t.esperar("mensagem", {"x": MSG["fechar_janelas"]}, 1):
            raise Parar("O Domínio pediu para fechar todas as janelas antes de trocar de empresa.")
        raise Parar("A janela Troca de empresas não abriu.")
    t.clicar("troca_por_codigo")          # a busca pode estar em "Apelido"
    t.clicar("troca_busca")
    t.teclas("ctrl", "a")
    t.digitar(codigo, espera=1)
    padrao = re.compile(rf"\s*{re.escape(codigo)}(?!\d)")
    fim = time.time() + espera            # o Domínio às vezes demora a redesenhar a lista
    xa = t.P["troca_amostra_azul"][0]
    linha = t.ler_linha_destacada("troca_lista", xa)
    while not padrao.match(linha) and time.time() < fim:
        t.dormir(0.7)
        linha = t.ler_linha_destacada("troca_lista", xa)
    if not padrao.match(linha):
        t.clicar("troca_fechar", espera=1)
        raise Parar(f"A empresa {codigo} não apareceu selecionada na Troca de empresas "
                    f"(linha lida: '{linha}'). Confira se o código existe e está ativo. Não acessei.")
    t.clicar("troca_acessar", espera=3)
    fim = time.time() + espera
    while not empresa_ativa_e(t, codigo):
        if time.time() > fim:
            raise Parar(f"Não consegui confirmar que a empresa {codigo} ficou ativa "
                        f"(lido no canto: '{t.ler('empresa_ativa')}').")
        t.dormir(1)
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
        # a janela abriu em outra posição: acha o título dela na tela e dá duplo clique
        pos = t.achar_texto("gerar parcelas de notas")
        if pos:
            t.duplo(*pos, espera=2)
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

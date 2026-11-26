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
    """Garante o Domínio na frente, maximizado no monitor principal. Se já estiver, segue direto;
    senão acha a janela (mesmo atrás de outra, minimizada ou no outro monitor) e confere pelo título."""
    if "dominio escrita fiscal" in t.ler("titulo_app"):
        return
    from . import janela
    candidatas, diag = janela.achar()
    if not candidatas:
        raise Parar("Não encontrei a janela do Domínio Escrita Fiscal aberta. "
                    f"Janelas vistas: {diag}")
    lido = ""
    for hwnd in candidatas[:4]:
        t.checar()
        janela.trazer_para_frente(hwnd)
        t.clicar("titulo_app", espera=0.3)   # já maximizado no principal: o título fica neste ponto
        lido = t.aguardar(lambda: (lambda x: x if "dominio escrita fiscal" in x else "")(t.ler("titulo_app")), 2)
        if lido:
            return
    raise Parar("Não consegui trazer o Domínio Escrita Fiscal para a frente "
                f"(título lido: '{t.ler('titulo_app')}').")


def empresa_ativa_e(t, codigo):
    """Confere o código da empresa ativa no canto superior direito. Lê a linha inteira e, se o
    código não vier (nome longe do código), lê só a área do código."""
    padrao = re.compile(rf"(?<!\d){re.escape(codigo)}(?!\d)")
    if padrao.search(t.ler("empresa_ativa")):
        return True
    for fator in (4, 6):  # só o código, em preto e branco (lê bem números isolados)
        if padrao.search(t.ler("empresa_codigo", fator=fator, binarizar=True, borda=12)):
            return True
    return False


def trocar_empresa(t, codigo):
    if empresa_ativa_e(t, codigo):
        t.log(f"  empresa {codigo} já está ativa")
        return
    espera = t.T.get("troca", 8)
    t.clicar("troca_empresa", espera=0.2)
    if t.esperar("troca_titulo", {"ok": ["troca de empresa"]}, espera, intervalo=0.25) != "ok":
        if t.esperar("mensagem", {"x": MSG["fechar_janelas"]}, 1):
            raise Parar("O Domínio pediu para fechar todas as janelas antes de trocar de empresa.")
        raise Parar("A janela Troca de empresas não abriu.")
    t.clicar("troca_por_codigo")          # a busca pode estar em "Apelido"
    t.clicar("troca_busca")
    t.teclas("ctrl", "a")
    t.digitar(codigo, espera=0.6)
    # a linha azul é só uma prévia (o OCR lê mal branco sobre azul); quem decide é o canto da tela
    linha = t.ler_linha_destacada("troca_lista", t.P["troca_amostra_azul"][0])
    if not re.match(rf"\s*{re.escape(codigo)}(?!\d)", linha):
        t.aviso(f"linha selecionada lida como '{linha}'; confirmei pelo canto da tela")
    t.clicar("troca_acessar", espera=0.5)
    if not t.aguardar(lambda: empresa_ativa_e(t, codigo), espera, intervalo=0.4):
        raise Parar(f"A empresa ativa não ficou {codigo} (lido no canto: '{t.ler('empresa_ativa')}' / "
                    f"'{t.ler('empresa_codigo', fator=4, binarizar=True, borda=12)}'). "
                    "Confira se o código existe e está ativo. Nada foi feito nessa empresa.")
    t.log(f"  empresa {codigo} ativa")


def janela_maximizada(t, palavra_titulo):
    titulo = t.ler("titulo_app")
    return "gerar parcelas" in titulo and palavra_titulo in titulo


def abrir_gerar_parcelas(t, ponto_menu, palavra_titulo):
    """Utilitários > Parcelas > Gerar Parcelas > (Entradas/Saídas/Serviços), maximizada."""
    t.clicar("menu_utilitarios", espera=0.5)
    t.clicar("menu_parcelas", espera=0.5)
    t.clicar("menu_gerar", espera=0.5)
    t.clicar(ponto_menu, espera=0.3)
    if t.aguardar(lambda: janela_maximizada(t, palavra_titulo), 4):
        return
    x, y = t.P["titulo_janela_normal"]
    t.duplo(x, y, espera=0.3)
    if t.aguardar(lambda: janela_maximizada(t, palavra_titulo), 2):
        return
    # a janela abriu em outra posição: acha o título dela na tela e dá duplo clique
    pos = t.achar_texto("gerar parcelas de notas")
    if pos:
        t.duplo(*pos, espera=0.3)
    if not t.aguardar(lambda: janela_maximizada(t, palavra_titulo), 2):
        raise Parar(f"A janela Gerar Parcelas ({palavra_titulo}) não abriu maximizada "
                    f"(título lido: '{t.ler('titulo_app')}').")


def garantir_caixa(t, ponto, marcada):
    if t.caixa_marcada(ponto) != marcada:
        t.clicar(ponto)
        if t.caixa_marcada(ponto) != marcada:
            raise Parar(f"Não consegui {'marcar' if marcada else 'desmarcar'} a caixa '{ponto}'.")
        t.log(f"  caixa '{ponto}' corrigida para {'marcada' if marcada else 'desmarcada'}")


def fechar_janela(t):
    t.clicar("fechar_janela", espera=0.3)
    t.aguardar(lambda: "gerar parcelas" not in t.ler("titulo_app"), 3)

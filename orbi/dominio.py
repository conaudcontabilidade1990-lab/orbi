"""Passos comuns do Domínio Escrita Fiscal, reaproveitados pelas rotinas."""
import re
import time

from .tela import Parar, Pular

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
        # visível não quer dizer ativo: o 1º clique numa janela inativa só a ativa
        t.clicar("titulo_app", espera=0.3)
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
    abriu = False
    for tentativa, limite in ((1, 3), (2, espera)):   # se o 1º clique não abrir, tenta mais uma vez
        t.clicar("troca_empresa", espera=0.2)
        if t.esperar("troca_titulo", {"ok": ["troca de empresa"]}, limite, intervalo=0.25) == "ok":
            abriu = True
            break
    if not abriu:
        if t.esperar("mensagem", {"x": MSG["fechar_janelas"]}, 1):
            raise Parar("O Domínio pediu para fechar todas as janelas antes de trocar de empresa.")
        raise Parar("A janela Troca de empresas não abriu.")
    t.clicar("troca_por_codigo")          # a busca pode estar em "Apelido"
    t.clicar("troca_busca")
    t.teclas("ctrl", "a")
    t.digitar(codigo, espera=0.6)
    # código da linha selecionada, pelo desenho dos dígitos (o OCR lê mal branco sobre azul)
    x0, x1 = t.P["troca_codigo_x"]
    ler = lambda: t.ler_codigo_destacado("troca_lista", t.P["troca_amostra_azul"][0], x0, x1)  # noqa: E731
    lido = t.aguardar(lambda: (lambda c: c if c == codigo else "")(ler()), 3, intervalo=0.3)
    if not lido:
        # outro código só conta se aparecer igual em duas leituras seguidas (a lista pode estar redesenhando)
        primeiro = ler()
        t.dormir(0.6)
        lido = ler() if primeiro else ""
        if lido != primeiro:
            lido = ""
    if lido and lido.isdigit() and lido != codigo:
        # o Domínio não achou o código e posicionou na empresa mais próxima: não acessa
        t.clicar("troca_fechar", espera=0.5)
        raise Pular(f"O código {codigo} não está na lista de empresas do Domínio (a busca caiu na {lido}). "
                    "Pode estar inativo ou não ser deste módulo. Não acessei nenhuma empresa.")
    t.clicar("troca_acessar", espera=0.5)
    if not t.aguardar(lambda: empresa_ativa_e(t, codigo), espera, intervalo=0.4):
        raise Pular(f"A empresa ativa não ficou {codigo} (lido no canto: '{t.ler('empresa_ativa')}' / "
                    f"'{t.ler('empresa_codigo', fator=4, binarizar=True, borda=12)}'). "
                    "O código pode não existir, estar inativo ou não ser deste módulo no Domínio. "
                    "Nada foi feito nessa empresa; segui para a próxima.")
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
    """Fecha a janela Gerar Parcelas e confere pelo título. Se um diálogo esquecido bloquear,
    cancela o diálogo e tenta de novo."""
    fechou = lambda: "gerar parcelas" not in t.ler("titulo_app")  # noqa: E731
    t.clicar("fechar_janela", espera=0.3)
    if t.aguardar(fechou, 3):
        return
    if "quantidade de parcelas" in t.ler("dialogo_gerar"):
        t.clicar("dlg_cancelar", espera=0.6)
    elif "busca avan" in t.ler("ba_titulo"):
        t.clicar("ba_cancelar", espera=0.6)
    t.clicar("fechar_janela", espera=0.3)
    if not t.aguardar(fechou, 3):
        raise Parar("Não consegui fechar a janela Gerar Parcelas (título continua aberto).")

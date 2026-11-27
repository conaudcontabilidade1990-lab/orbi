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
        ok = lambda: (lambda x: x if "dominio escrita fiscal" in x else "")(t.ler("titulo_app"))  # noqa: E731
        if t.aguardar(ok, 2):
            return
        # restaurou mas não maximizou: pede de novo e, se preciso, duplo clique na barra de título dela
        janela.maximizar(hwnd)
        if t.aguardar(ok, 2):
            return
        esq, topo, dir_, _ = janela.retangulo(hwnd)
        if dir_ - esq > 300:
            t.duplo(esq + 300, topo + 12, espera=1.0)
            if t.aguardar(ok, 2):
                return
    raise Parar("Não consegui trazer o Domínio Escrita Fiscal para a frente "
                f"(título lido: '{t.ler('titulo_app')}').")


def codigo_no_canto(txt):
    """Código lido no canto ('maria silva - 3-00' -> '300'): o número depois do ' - ' do nome, sem os
    traços/pontos que o OCR às vezes enfia no meio dele."""
    txt = txt or ""
    numero = r"(\d(?:[\-.,']?\d)*)"
    if re.match(r"\s*\d", txt):                     # só a área do código: começa pelo número
        m = re.match(r"\s*" + numero, txt)
    else:
        m = re.search(r"-\s*" + numero, txt) or re.search(numero, txt)
    return re.sub(r"\D", "", m.group(1)) if m else ""


def nome_confere(lido, esperado):
    """O apelido do canto ('maria silva') bate com o nome do cadastro ('MARIA JOSE DA SILVA')?"""
    def palavras(x):
        return {w for w in re.sub(r"[^a-z0-9 ]", " ", norm_txt(x)).split() if len(w) >= 3
                and w not in ("ltda", "me", "eireli", "epp", "comercio", "servicos", "industria")}
    a, b = palavras(lido), palavras(esperado)
    return len(a) >= 1 and len(a & b) >= min(2, len(a))


def norm_txt(x):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (x or "").lower()) if unicodedata.category(c) != "Mn")


def empresa_ativa_e(t, codigo):
    """Confere o código da empresa ativa no canto superior direito. Lê a linha inteira e, se o
    código não vier (nome longe do código), lê só a área do código."""
    padrao = re.compile(rf"(?<!\d){re.escape(codigo)}(?!\d)")
    linha = t.ler("empresa_ativa")
    if padrao.search(linha) or codigo_no_canto(linha) == codigo:
        return True
    for fator in (4, 6):  # só o código, em preto e branco (lê bem números isolados)
        txt = t.ler("empresa_codigo", fator=fator, binarizar=True, borda=12)
        if padrao.search(txt) or codigo_no_canto(txt) == codigo:
            return True
    return False


def fechar_janelas_abertas(t):
    """Fecha TODAS as janelas internas abertas no Domínio antes de trocar de empresa: com qualquer
    janela aberta o Domínio recusa a troca ("terá que fechar todas as janelas abertas")."""
    # 1) janela maximizada (o título dela aparece entre [ ] no título do Domínio)
    for _ in range(3):
        titulo = t.ler("titulo_app")
        if "[" not in titulo and "gerar parcelas" not in titulo:
            break
        t.log(f"  fechando janela que ficou aberta: {titulo[titulo.find('['):][:60]}")
        fechar_janela(t)
    else:
        raise Parar("Há uma janela aberta no Domínio que não consegui fechar. Feche-a e rode de novo.")
    # 2) janelas soltas (não maximizadas): acha o [X] de cada uma pelo ícone da barra de título e fecha
    def sumiu(x, y):
        return lambda: not any(abs(bx - x) < 8 and abs(by - y) < 8 for bx, by in t.botoes_fechar("area_janelas"))

    for _ in range(10):
        botoes = t.botoes_fechar("area_janelas")
        if not botoes:
            return
        fechou = False
        for x, y in botoes:        # a da frente primeiro; se ela não fechar (ex.: atrás de um diálogo), tenta a próxima
            nome = t.ler((max(0, x - 640), max(0, y - 9), 600, 18))
            t.log(f"  fechando janela aberta: {nome[:60] or '(sem título)'}")
            for _clique in range(2):   # o 1º clique às vezes só ativa a janela (Domínio remoto)
                t.clicar_em(x, y, espera=0.3)
                if t.aguardar(sumiu(x, y), 3, intervalo=0.3):
                    fechou = True
                    break
            if fechou:
                break
        if fechou:
            continue
        aviso = t.ler("mensagem")
        raise Parar(f"A janela '{nome[:60]}' não fechou" + (f" (o Domínio perguntou: '{aviso[:120]}')" if aviso else "")
                    + ". Não respondi nada; feche-a e rode de novo.")
    raise Parar("Há janelas demais abertas no Domínio. Feche-as e rode de novo.")


def _digitos_canto(t):
    """Primeiro número lido na área do código (o mês/ano vem depois, na linha de baixo)."""
    m = re.search(r"\d+", t.ler("empresa_codigo", fator=4, binarizar=True, borda=12))
    return m.group(0) if m else ""


def _confirmado_pela_linha(t, linha_ok, antes, codigo):
    """O OCR do canto às vezes troca um dígito (186 lido como 136). Se a linha azul já tinha
    confirmado o código pelo desenho, aceita quando a Troca fechou e o código do canto mudou
    para um número do mesmo tamanho."""
    if not linha_ok:
        return False
    if "troca de empresa" in t.ler("troca_titulo"):
        return False
    depois = _digitos_canto(t)
    if depois and depois != antes and len(depois) == len(codigo):
        t.log(f"  empresa {codigo}: confirmada pela linha selecionada (o canto foi lido como '{depois}')")
        return True
    esperado = getattr(t, "nome_esperado", "")
    lido = t.ler("empresa_ativa")
    if esperado and nome_confere(lido, esperado):
        t.log(f"  empresa {codigo}: confirmada pela linha selecionada e pelo nome no canto ('{lido[:40]}')")
        return True
    return False


def trocar_empresa(t, codigo, _tentativa=1):
    fechar_janelas_abertas(t)
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
            t.clicar("btn_ok_vazio", espera=0.5)
            if _tentativa > 1:
                raise Parar("O Domínio continua pedindo para fechar todas as janelas antes de trocar de empresa.")
            t.log("  o Domínio pediu para fechar as janelas abertas; fechando e tentando de novo")
            return trocar_empresa(t, codigo, _tentativa + 1)
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
    linha_ok = lido == codigo                    # a linha azul confirmou o código pelo desenho
    antes = _digitos_canto(t)
    t.clicar("troca_acessar", espera=0.5)
    if MSG["fechar_janelas"][0] in t.ler("mensagem"):
        # sobrou alguma janela que não foi vista antes: OK no aviso, fecha a Troca, fecha tudo e tenta de novo
        t.clicar("btn_ok_vazio", espera=0.5)
        t.clicar("troca_fechar", espera=0.5)
        if _tentativa > 1:
            raise Parar("O Domínio continua pedindo para fechar todas as janelas antes de trocar de empresa.")
        t.log("  o Domínio pediu para fechar as janelas abertas; fechando e tentando de novo")
        return trocar_empresa(t, codigo, _tentativa + 1)
    if not t.aguardar(lambda: empresa_ativa_e(t, codigo), espera, intervalo=0.4) \
            and not _confirmado_pela_linha(t, linha_ok, antes, codigo):
        raise Pular(f"A empresa ativa não ficou {codigo} (lido no canto: '{t.ler('empresa_ativa')}' / "
                    f"'{t.ler('empresa_codigo', fator=4, binarizar=True, borda=12)}'). "
                    "O código pode não existir, estar inativo ou não ser deste módulo no Domínio. "
                    "Nada foi feito nessa empresa; segui para a próxima.")
    t.log(f"  empresa {codigo} ativa")


def janela_maximizada(t, palavra_titulo):
    titulo = t.ler("titulo_app")
    return "gerar parcelas" in titulo and palavra_titulo in titulo


def _so_letras(n):
    return re.sub(r"[^a-z ]", "", n).strip()


# Itens de menu reconhecidos pelo TEXTO (o menu Utilitários muda de empresa para empresa;
# clicar por posição já abriu a janela errada). O OCR às vezes troca "ç" por "g".
_ITENS_SUBMENU = ("entradas", "saidas", "servicos", "cupons fiscais", "cupons fiscais eletronicos cfe")


def _item_parecido(alvo):
    """Aceita o texto lido se ele se parece mais com 'alvo' do que com qualquer outro item do
    submenu (o OCR às vezes lê 'Serviços' como 'Servigos', 'Sewiços' etc.)."""
    import difflib

    def aceita(n):
        lido = _so_letras(n)
        if not lido:
            return False
        notas = {i: difflib.SequenceMatcher(None, lido, i).ratio() for i in _ITENS_SUBMENU}
        return max(notas, key=notas.get) == alvo and notas[alvo] >= 0.7
    return aceita


ITEM_FINAL = {k: _item_parecido(k) for k in ("entradas", "saidas", "servicos")}


def _menu(t, aceita, regiao, nome):
    """Acha o item do menu pelo texto: primeiro na região esperada e, se não achar, na tela toda
    (o menu abre em lugares diferentes conforme o computador/empresa)."""
    W, H = t.cfg["resolucao"]
    toda = (0, 0, W, H - 40)
    achado = t.aguardar(lambda: t.achar_linha(aceita, regiao) or t.achar_linha(aceita, toda), 3, intervalo=0.3)
    if not achado:
        for _ in range(3):
            t.teclas("esc")
        raise Parar(f"Não encontrei o item '{nome}' no menu do Domínio. Fechei o menu sem clicar em nada.")
    x, y, _ = achado
    t.clicar_em(x, y, espera=0.5)
    return x, y


def abrir_gerar_parcelas(t, ponto_menu, palavra_titulo):
    """Utilitários > Parcelas > Gerar Parcelas > (Entradas/Saídas/Serviços), achando cada item pelo texto."""
    aberta = lambda: janela_maximizada(t, palavra_titulo) or t.botoes_fechar("area_janelas")  # noqa: E731
    for tentativa in range(2):
        try:
            t.clicar("menu_utilitarios", espera=0.5)
            navegar_menu_parcelas(t, palavra_titulo)
        except Pular:
            raise
        except Parar as e:
            if tentativa == 0 and aberta():      # a janela atrasada abriu enquanto o menu era refeito
                break
            if tentativa == 1:
                raise Pular(f"{e} (2ª tentativa de abrir a janela Gerar Parcelas). Nada foi feito nesta empresa.")
            t.log(f"  menu não respondeu ({e}); tentando de novo")
            t.dormir(2)
            continue
        # em empresa grande a janela demora a aparecer: espera até 45 s (mais enquanto o Domínio trabalha)
        fim = time.time() + 45
        ok = False
        while True:
            if aberta():
                ok = True
                break
            if time.time() >= fim and not t.ocupado():
                break
            if time.time() >= fim + 240:
                break
            t.dormir(0.5)
        if ok:
            break
        if tentativa == 0:
            t.log("  a janela Gerar Parcelas não apareceu; abrindo pelo menu de novo")
        else:
            raise Pular("A janela Gerar Parcelas não abriu nem na 2ª tentativa. Nada foi feito nesta empresa.")
    _depois_do_menu(t, palavra_titulo)


def navegar_menu_parcelas(t, palavra_titulo):
    W, H = t.cfg["resolucao"]
    ux = t.P["menu_utilitarios"][0]
    x1, _ = _menu(t, lambda n: _so_letras(n) == "parcelas", (max(0, ux - 200), 0, 650, H - 40), "Parcelas")
    x2, _ = _menu(t, lambda n: "gerar parcelas" in n, (x1 + 60, 0, min(420, W - x1 - 60), H - 40), "Gerar Parcelas")
    _menu(t, ITEM_FINAL[palavra_titulo], (x2 + 40, 0, max(200, W - x2 - 40), H - 40),
          {"saidas": "Saídas", "servicos": "Serviços", "entradas": "Entradas"}[palavra_titulo])


def _depois_do_menu(t, palavra_titulo):
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
    fechou = lambda: (lambda x: "gerar parcelas" not in x and "[" not in x)(t.ler("titulo_app"))  # noqa: E731
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

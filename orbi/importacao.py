"""Importação Padrão de XML no Domínio Escrita Fiscal (NF-e, NFC-e, CT-e, NFS-e Padrão Nacional).

Tudo é achado pelo TEXTO na tela (OCR) ou pelo botão vermelho [X] da janela, porque cada tela de
importação abre em um lugar e o menu muda de empresa para empresa. Qualquer coisa fora do esperado
para a rotina sem responder nada (tela.Parar).
"""
import difflib
import re

from . import dominio as d
from .tela import Parar

# ---- menus (rótulos como aparecem no Domínio; comparados só por letras e números) ----
MENU_UTILITARIOS = [
    "dashboard gerencial", "consulta", "assistente virtual do onvio messenger", "reforma tributaria", "backup",
    "configurar backup", "backup em nuvem", "historico e erros do agente de comunicacao",
    "historico e erros do web service sefaz", "consulta apuracao", "conferencia de lancamentos",
    "alterar acumuladores", "alterar notas e outros lancamentos", "alterar impostos nas notas", "alterar produtos",
    "alterar movimento de produtos das notas", "alterar cadastro de clientes e fornecedores", "parcelas",
    "gerar item nas notas de servicos", "inclusao simples nacional nos acumuladores", "menu favoritos",
    "importacao", "exportacao", "conversao de municipios", "regerar", "exclusao", "limpeza",
    "registro de atividades f9", "calculadora f12", "utilitarios"]
MENU_IMPORTACAO = ["de outra empresa", "importacao padrao", "importador", "importacao leiautes antigos",
                   "dominio cliente", "outras importacoes"]
MENU_PADRAO = [
    "nf-e arquivo xml", "nf3-e arquivo xml", "nfcom arquivo xml", "nfag arquivo xml", "nfc-e arquivo xml",
    "cf-e arquivo xml", "nfs-e arquivo xml - abrasf", "nfs-e arquivo xml - padrao nacional",
    "nfs-e arquivo xml - exploracao de via", "nfs-e paulistana", "onbalance", "importacao api", "ct-e e ct-eos",
    "sped fiscal", "sped pis e cofins", "cupom fiscal", "sintegra", "convenio icms 115/03",
    "leiaute dominio sistemas com separador", "cadastro de empresas", "nf-e portal do cliente",
    "nfc-e portal do cliente", "ct-e e ct-eos portal do cliente", "cf-e portal do cliente",
    "nfs-e padrao nacional portal do cliente"]
MENU_CTE = ["arquivo xml", "dados da nota fiscal que acoberta a carga"]

# tipo -> (caminho no menu Importação Padrão, opções de "Importar", uma importação por opção)
TIPOS = {
    "NF-e": (["nf-e arquivo xml"], [("Todos", lambda n: _so(n) == "todos")]),
    "NFC-e": (["nfc-e arquivo xml"], [("Todos", lambda n: _so(n) == "todos")]),
    "CT-e": (["ct-e e ct-eos", "arquivo xml"], [
        ("Notas de entradas", lambda n: _so(n).startswith("notas de entrada")),
        ("Notas canceladas", lambda n: _so(n).startswith("notas cancelada"))]),
    "NFS-e": (["nfs-e arquivo xml - padrao nacional"], [
        ("Serviço tomado", lambda n: "tomad" in _so(n)),
        ("Serviço prestado", lambda n: "prestad" in _so(n)),
        ("Canceladas", lambda n: "cancelad" in _so(n))]),
}

# Posições a partir do [X] vermelho da janela (iguais nas telas de NF-e, NFC-e e CT-e)
DX_IMPORTAR, DY_IMPORTAR = -44, 45
DX_FECHAR, DY_FECHAR = -44, 109
DX_PASTA, DY_PASTA = -135, 58
# Resumo dos Dados (a partir do [X] dele): faixa das abas e área dos botões de baixo
RES_ABAS = (-790, 52, 770, 32)
RES_BOTOES = (-810, 200, 805, 560)


def _so(n):
    """Só letras, números e espaços (o OCR às vezes troca '-' e acentos)."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", n or "")).strip()


def parecido(alvo, conhecidos, minimo=0.78):
    """aceita(texto) que só aceita o texto se ele se parece mais com 'alvo' que com qualquer outro rótulo."""
    alvo_s = _so(alvo)
    todos = {_so(c) for c in conhecidos} | {alvo_s}

    def aceita(n):
        lido = _so(n)
        if not lido:
            return False
        notas = {c: difflib.SequenceMatcher(None, lido, c).ratio() for c in todos}
        melhor = max(notas, key=notas.get)
        return melhor == alvo_s and notas[melhor] >= minimo
    return aceita


def _item(t, alvo, conhecidos, regiao, nome):
    achado = t.aguardar(lambda: t.achar_linha(parecido(alvo, conhecidos), regiao), 3, intervalo=0.3)
    if not achado:
        for _ in range(4):
            t.teclas("esc")
        raise Parar(f"Não encontrei '{nome}' no menu do Domínio. Fechei o menu sem clicar em nada.")
    x, y, _ = achado
    t.clicar_em(x, y, espera=0.6)
    return x, y


def abrir_tela(t, tipo):
    """Utilitários > Importação > Importação Padrão > (item do tipo). Devolve o [X] da janela aberta."""
    W, H = t.cfg["resolucao"]
    tela_toda = (0, 0, W, H - 40)
    caminho, _ = TIPOS[tipo]
    t.clicar("menu_utilitarios", espera=0.6)
    conhecidos = MENU_UTILITARIOS
    _item(t, "importacao", conhecidos, tela_toda, "Importação")
    conhecidos = conhecidos + MENU_IMPORTACAO
    _item(t, "importacao padrao", conhecidos, tela_toda, "Importação Padrão")
    conhecidos = conhecidos + MENU_PADRAO
    x, _ = _item(t, caminho[0], conhecidos, tela_toda, caminho[0])
    if len(caminho) > 1:   # CT-e e CT-eOS > Arquivo XML (o submenu abre à direita do item)
        _item(t, caminho[1], conhecidos + MENU_CTE, (x + 100, 0, W - x - 100, H - 40), caminho[1])
    xis = t.aguardar(lambda: _janela_importacao(t), 10, intervalo=0.4)
    if not xis:
        raise Parar(f"A tela de importação de {tipo} não abriu (ou abriu num formato que eu não conheço).")
    return xis


def _titulo_da_janela(t, xis):
    x, y = xis
    x0 = max(0, x - 900)
    return t.ler((x0, max(0, y - 11), x - x0 - 60, 22))


def _e_importacao(titulo):
    # o OCR às vezes lê 'Importação Padrão' como 'importaqao 2adrao'
    return any(k in titulo for k in ("importa", "padrao", "adrao")) and "resumo" not in titulo


def _janela_importacao(t):
    for xis in t.botoes_fechar("area_janelas"):
        if _e_importacao(_titulo_da_janela(t, xis)):
            return xis
    return None


def _janela(t, trecho):
    for xis in t.botoes_fechar("area_janelas"):
        if trecho in _titulo_da_janela(t, xis):
            return xis
    return None


def _dialogo(t):
    return t.ler("dlg_importacao")


def escolher_pasta(t, xis, pasta_dominio, esperado):
    """Abre a Seleção de arquivos, cola o caminho, lista e marca todos. Confere que só há o .zip."""
    x, y = xis
    t.clicar_em(x + DX_PASTA, y + DY_PASTA, espera=0.5)
    if not t.aguardar(lambda: "selecao de arquivos" in t.ler("sel_titulo"), 8, intervalo=0.4):
        raise Parar("A janela 'Seleção de arquivos' não abriu.")
    def estado():
        msg = _dialogo(t)
        if "nao e valido" in msg or "nao existem" in msg or "invalido" in msg:
            return "erro:" + msg
        if t.fracao_azul("sel_linha1") > 0.4:   # 1ª linha da lista selecionada (azul)
            return "ok"
        linha = t.ler("sel_linha1")          # o Domínio mostra os XML de dentro do zip
        return "ok" if ("xml" in linha or "zip" in linha) else ""

    # Quem confirma o caminho é o próprio Domínio: com o caminho certo ele lista os XML do zip;
    # errado, avisa que não é válido. (Ler o campo pelo OCR não é confiável.)
    ultimo = ""
    for tentativa in range(3):
        t.clicar("sel_campo", espera=0.2)
        t.teclas("end")
        t.apagar(160)                      # apaga tudo (Shift+Home falha às vezes no Domínio remoto)
        if pasta_dominio.isascii() and tentativa != 1:
            t.digitar(pasta_dominio, espera=0.8)   # sem acento: digita tecla a tecla
        else:
            # com acento (ex.: 'Configuração HubStrom'): cola; a área de transferência do Domínio remoto
            # demora a receber o texto, então espera mais a cada tentativa
            t.colar(pasta_dominio, espera=1.5 + 1.5 * tentativa)
            t.dormir(0.8)
        t.clicar("sel_atualizar", espera=0.8)
        r = t.aguardar(estado, 20, intervalo=0.5)
        if r == "ok":
            break
        ultimo = r or "nada apareceu"
        if r:
            t.teclas("enter")              # OK no aviso de caminho inválido
            t.dormir(0.6)
    else:
        t.clicar("sel_cancelar", espera=0.5)
        raise Parar(f"O Domínio não aceitou o caminho '{pasta_dominio}' depois de 3 tentativas "
                    f"(último aviso: '{ultimo[:150]}', campo: '{t.ler('sel_campo')[:100]}').")
    t.clicar("sel_todos", espera=0.4)
    t.clicar("sel_ok", espera=0.8)
    if not t.aguardar(lambda: "selecao de arquivos" not in t.ler("sel_titulo"), 5, intervalo=0.4):
        raise Parar("A Seleção de arquivos não fechou depois do OK.")


def marcar_opcao(t, xis, nome, aceita):
    """Marca o botão de opção (radio) cujo texto é aceito, dentro da janela de importação."""
    x, y = xis
    regiao = (max(0, x - 700), y + 150, 560, 260)
    for tx, lx, ly, lw, lh in t.linhas(regiao):
        if aceita(tx):
            cy = ly + lh / 2
            # o círculo fica ~12 px à esquerda do texto: procura o ponto mais escuro depois de clicar
            t.clicar_em(int(lx - 12), int(cy), espera=0.4)
            if max(t.escuros_em(cx, cy) for cx in range(int(lx) - 16, int(lx) - 7, 2)) >= 9:
                return
            raise Parar(f"Cliquei em '{nome}' mas a opção não ficou marcada.")
    raise Parar(f"Não encontrei a opção '{nome}' na tela de importação.")


def _palavra(t, regiao, aceita, mais_a_direita=False):
    achadas = [p for p in t.palavras(regiao) if aceita(p[0])]
    if not achadas:
        return None
    return max(achadas, key=lambda p: p[1]) if mais_a_direita else achadas[0]


def _centro(p):
    return int(p[1] + p[3] / 2), int(p[2] + p[4] / 2)


def _regiao_botoes(t, rx, ry):
    W, H = t.cfg["resolucao"]
    bx, by, bw, bh = RES_BOTOES
    x0, y0 = max(0, rx + bx), max(0, ry + by)
    return (x0, y0, min(bw, W - x0), min(bh, H - 40 - y0))


def importar_e_gravar(t, xis, simular, log):
    """Clica em Importar, espera o Resumo dos Dados, marca Todos nas advertências e grava.
    Devolve o texto do Domínio ('Dados gravados com sucesso' com as quantidades) ou 'nada a importar'."""
    x, y = xis
    t.clicar_em(x + DX_IMPORTAR, y + DY_IMPORTAR, espera=1.0)
    limite = t.T.get("importacao", 1800)

    def chegou():
        msg = _dialogo(t)
        if "compactad" in msg and "mesmo assim" in msg:
            t.teclas("enter")                       # Sim: importar mesmo sem compactar
            return None
        if "apresentou advertencias" in msg or "advertencias e/ou erros" in msg:
            t.teclas("enter")                       # OK: o Resumo vem em seguida
            return None
        if "nao" in msg and any(k in msg for k in ("encontrad", "nenhum", "nao existem", "nao ha ")):
            return ("vazio", msg)
        rx = _janela(t, "resumo")
        return ("resumo", rx) if rx else None
    r = t.aguardar(chegou, limite, intervalo=1.0)
    if not r:
        raise Parar(f"A importação não terminou em {limite // 60} min (último aviso lido: '{_dialogo(t)[:150]}').")
    if r[0] == "vazio":
        t.teclas("enter")
        t.dormir(0.6)
        return "nada a importar (" + r[1][:100] + ")"
    rx, ry = r[1]
    t.dormir(0.8)

    # advertências: marcar Todos
    ax, ay, aw, ah = RES_ABAS
    abas = (max(0, rx + ax), ry + ay, aw, ah)
    aba = _palavra(t, abas, lambda w: w.startswith("advert"))
    if aba:
        t.clicar_em(*_centro(aba), espera=0.8)
        bt = _palavra(t, _regiao_botoes(t, rx, ry), lambda w: w.startswith("todo"), mais_a_direita=True)
        if bt:
            t.clicar_em(*_centro(bt), espera=0.8)
        else:
            t.aviso("advertências: não achei o botão Todos")
    erros = _palavra(t, abas, lambda w: w.startswith("erro"))
    if erros and t.escuros_em(*_centro(erros)) >= 6:
        t.aviso("a importação teve ERROS (esses registros não são gravados) — confira no Domínio")

    botoes = t.palavras(_regiao_botoes(t, rx, ry))
    cancelar = next((p for p in botoes if p[0].startswith("cancel")), None)
    if simular:
        if not cancelar:
            raise Parar("Não achei o botão Cancelar do Resumo dos Dados.")
        t.clicar_em(*_centro(cancelar), espera=1.0)
        t.aguardar(lambda: not _janela(t, "resumo"), 10, intervalo=0.5)
        return "simulação: chegou ao Resumo dos Dados e cancelou (nada gravado)"

    gravar = next((p for p in botoes if p[0].startswith("grav") and not p[0].startswith("gravad")), None)
    if not gravar:
        raise Parar("Não achei o botão Gravar do Resumo dos Dados.")
    t.clicar_em(*_centro(gravar), espera=1.0)
    resultado = {}

    def gravou():
        msg = _dialogo(t)
        if "gravados com sucesso" in msg:
            resultado["txt"] = msg
            t.teclas("enter")
            return True
        if "erros de estrutura" in msg and "confirma" in msg:
            t.aviso("havia erros de estrutura em algum XML (gravei o restante)")
            t.teclas("enter")
        elif "maior que o" in msg and "periodo" in msg:
            t.aviso("há notas com data maior que o período de trabalho do Domínio")
            t.teclas("enter")
        return False
    if not t.aguardar(gravou, limite, intervalo=1.0):
        raise Parar(f"Não apareceu 'Dados gravados com sucesso' em {limite // 60} min "
                    f"(último aviso lido: '{_dialogo(t)[:150]}').")
    # depois do OK o Domínio regera as saídas ('Aguarde... Regerando saídas'): espera terminar
    t.dormir(1.5)
    t.aguardar(lambda: not any(k in _dialogo(t) for k in ("aguarde", "regerando", "processando")),
               limite, intervalo=1.5)
    if cancelar:
        t.clicar_em(*_centro(cancelar), espera=1.0)   # fecha o Resumo (já gravado)
    t.aguardar(lambda: not _janela(t, "resumo"), 10, intervalo=0.5)
    txt = resultado["txt"]
    i = txt.find("produtos")
    return re.sub(r"\s+", " ", txt[i if i >= 0 else 0:])[:300]


def fechar_tela(t, xis):
    x, y = xis
    if _palavra(t, (x + DX_FECHAR - 50, y + DY_FECHAR - 12, 100, 24), lambda w: w.startswith("fech")):
        t.clicar_em(x + DX_FECHAR, y + DY_FECHAR, espera=0.8)
    else:
        t.clicar_em(x, y, espera=0.8)
    if t.aguardar(lambda: not _janela_importacao(t), 5, intervalo=0.4):
        return
    d.fechar_janelas_abertas(t)


def importar_tipo(t, tipo, pasta_dominio, esperado, simular):
    """Importa o zip de um tipo (todas as opções dele). Devolve a lista de resultados por opção."""
    xis = abrir_tela(t, tipo)
    escolher_pasta(t, xis, pasta_dominio, esperado)
    resultados = []
    for nome, aceita in TIPOS[tipo][1]:
        marcar_opcao(t, xis, nome, aceita)
        r = importar_e_gravar(t, xis, simular, t.log)
        t.log(f"    {tipo} · {nome}: {r}")
        resultados.append(f"{nome}: {r}")
    fechar_tela(t, xis)
    return resultados

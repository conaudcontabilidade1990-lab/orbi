"""Separa os XML de uma pasta de mês (HubStrom) por tipo de documento e gera um .zip por tipo.

Estrutura do HubStrom:  <pasta base>\\<código>-<NOME>\\<MMAAAA>\\<chave>.xml
Resultado (dentro da própria pasta do mês):
    <MMAAAA>\\NF-e\\NF-e.zip   <MMAAAA>\\NFC-e\\NFC-e.zip   <MMAAAA>\\CT-e\\CT-e.zip   <MMAAAA>\\NFS-e\\NFS-e.zip
Cada subpasta fica só com o zip, para apontar direto na Importação Padrão do Domínio.

Controle do que já foi importado (por subpasta de tipo):
    importados.txt  nomes dos XML já importados no Domínio (não entram mais no zip)
    pendentes.txt   nomes dos XML que estão no zip atual (viram 'importados' depois da importação)
O zip tem só os XML que ainda não foram importados; sem nada novo, não há zip.
"""
import os
import re
import zipfile
from pathlib import Path

# modelo (posições 21-22 da chave de 44 dígitos) -> tipo
MODELOS = {"55": "NF-e", "65": "NFC-e", "57": "CT-e", "67": "CT-e"}
TIPOS = ("NF-e", "NFC-e", "CT-e", "NFS-e")
OUTROS = "Outros"


def tipo_da_chave(chave):
    """Tipo do documento pela chave: 44 dígitos (modelo nas posições 21-22) ou 50 (NFS-e nacional)."""
    chave = re.sub(r"\D", "", chave or "")
    if len(chave) == 50:
        return "NFS-e"
    if len(chave) == 44:
        return MODELOS.get(chave[20:22])
    return None


def tipo_do_arquivo(caminho):
    """Pelo nome (chave) e, se o nome não for uma chave, pelo conteúdo do XML."""
    nome = Path(caminho).stem.strip()
    t = tipo_da_chave(nome) if re.fullmatch(r"\d{44}|\d{50}", nome) else None
    if t:
        return t
    try:
        with open(caminho, "rb") as f:
            ini = f.read(6000).decode("utf-8", "ignore")
    except OSError:
        return OUTROS
    m = re.search(r"<mod>\s*(\d\d)\s*</mod>", ini)
    if m and m.group(1) in MODELOS:
        return MODELOS[m.group(1)]
    m = re.search(r'Id="(?:NFe|CTe|ID|NFS)?(\d{44}|\d{50})"', ini) or re.search(r"<chNFe>(\d{44})</chNFe>", ini) \
        or re.search(r"<chCTe>(\d{44})</chCTe>", ini)
    if m:
        return tipo_da_chave(m.group(1)) or OUTROS
    if re.search(r"<(?:\w+:)?(?:NFSe|infNFSe|CompNfse)\b", ini):
        return "NFS-e"
    return OUTROS


def pasta_da_empresa(base, codigo):
    """Pasta '<código>-NOME' dentro da pasta base (o código tem que bater exatamente)."""
    base = Path(base)
    if not base.is_dir():
        return None
    for p in sorted(base.iterdir()):
        if p.is_dir() and re.match(rf"{re.escape(str(codigo))}\s*-", p.name):
            return p
    return None


def _nomes(arq):
    try:
        return {l.strip() for l in Path(arq).read_text(encoding="utf-8").splitlines() if l.strip()}
    except OSError:
        return set()


def _apagar(*arqs):
    for a in arqs:
        try:
            Path(a).unlink()
        except FileNotFoundError:
            pass


def separar(pasta_mes, gravar=True):
    """Separa os XML da pasta do mês por tipo e, com gravar=True, zipa só os ainda não importados.
    Devolve {tipo: (total, pendentes)}."""
    pasta_mes = Path(pasta_mes)
    grupos = {}
    for arq in sorted(pasta_mes.iterdir()):
        if arq.is_file() and arq.suffix.lower() == ".xml":
            grupos.setdefault(tipo_do_arquivo(arq), []).append(arq)
    res = {}
    for tipo, arqs in grupos.items():
        if tipo == OUTROS:
            res[tipo] = (len(arqs), len(arqs))
            continue
        destino = pasta_mes / tipo
        ja = _nomes(destino / "importados.txt")
        pend = [a for a in arqs if a.name not in ja]
        res[tipo] = (len(arqs), len(pend))
        if not gravar:
            continue
        final, lista = destino / f"{tipo}.zip", destino / "pendentes.txt"
        if not pend:
            _apagar(final, lista)
            continue
        destino.mkdir(exist_ok=True)
        temp = destino / f"{tipo}.zip.tmp"
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
            for a in pend:
                z.write(a, a.name)
        os.replace(temp, final)
        lista.write_text("\n".join(a.name for a in pend) + "\n", encoding="utf-8")
    return res


def marcar_importados(pasta_mes, tipos=TIPOS):
    """Depois de importar os zips no Domínio: o que estava no zip passa a 'importados' e o zip sai.
    Devolve {tipo: quantidade marcada}."""
    marcados = {}
    for tipo in tipos:
        destino = Path(pasta_mes) / tipo
        pend = _nomes(destino / "pendentes.txt")
        if not pend:
            continue
        ja = _nomes(destino / "importados.txt")
        with open(destino / "importados.txt", "a", encoding="utf-8") as f:
            for n in sorted(pend - ja):
                f.write(n + "\n")
        _apagar(destino / f"{tipo}.zip", destino / "pendentes.txt")
        marcados[tipo] = len(pend)
    return marcados


def resumo(contagem):
    """contagem: {tipo: (total, pendentes)} ou {tipo: quantidade}."""
    partes = []
    for t in TIPOS:
        v = contagem.get(t)
        if not v:
            continue
        if isinstance(v, tuple):
            total, pend = v
            partes.append(f"{total} {t} ({pend} a importar)" if pend != total else f"{total} {t}")
        else:
            partes.append(f"{v} {t}")
    o = contagem.get(OUTROS)
    if o:
        partes.append(f"{o[0] if isinstance(o, tuple) else o} não reconhecido(s)")
    return ", ".join(partes) or "nenhum XML"


def pendentes(contagem):
    return sum(v[1] for t, v in contagem.items() if t != OUTROS and isinstance(v, tuple))


def prestador_nfse(nome_arquivo):
    """CNPJ/CPF do prestador pela chave da NFS-e nacional (50 dígitos):
    município(7) + ambiente(1) + tipo de inscrição(1) + inscrição(14) + número(13) + AAMM(4) + código(9) + DV(1)."""
    chave = re.sub(r"\D", "", Path(nome_arquivo).stem)
    return chave[9:23] if len(chave) == 50 else ""


def opcoes_nfse(pasta_tipo, cnpj_empresa):
    """Quais importações de NFS-e fazem sentido para o zip pendente: {'tomado', 'prestado'}.
    Sem CNPJ da empresa (ou sem lista), devolve as duas."""
    cnpj = re.sub(r"\D", "", cnpj_empresa or "")
    nomes = _nomes(Path(pasta_tipo) / "pendentes.txt")
    if len(cnpj) not in (11, 14) or not nomes:
        return {"tomado", "prestado"}
    alvo = cnpj.zfill(14)
    ops = set()
    for n in nomes:
        p = prestador_nfse(n)
        if not p:
            return {"tomado", "prestado"}
        ops.add("prestado" if p == alvo else "tomado")
    return ops

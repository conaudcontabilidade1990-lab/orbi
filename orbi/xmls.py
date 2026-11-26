"""Separa os XML de uma pasta de mês (HubStrom) por tipo de documento e gera um .zip por tipo.

Estrutura do HubStrom:  <pasta base>\\<código>-<NOME>\\<MMAAAA>\\<chave>.xml
Resultado (dentro da própria pasta do mês):
    <MMAAAA>\\NF-e\\NF-e.zip   <MMAAAA>\\NFC-e\\NFC-e.zip   <MMAAAA>\\CT-e\\CT-e.zip   <MMAAAA>\\NFS-e\\NFS-e.zip
Cada subpasta fica só com o zip, para apontar direto na Importação Padrão do Domínio.
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


def separar(pasta_mes, gravar=True):
    """Conta (e, com gravar=True, zipa) os XML da pasta do mês por tipo. Devolve {tipo: quantidade}."""
    pasta_mes = Path(pasta_mes)
    grupos = {}
    for arq in sorted(pasta_mes.iterdir()):
        if arq.is_file() and arq.suffix.lower() == ".xml":
            grupos.setdefault(tipo_do_arquivo(arq), []).append(arq)
    if gravar:
        for tipo, arqs in grupos.items():
            if tipo == OUTROS:
                continue
            destino = pasta_mes / tipo
            destino.mkdir(exist_ok=True)
            final = destino / f"{tipo}.zip"
            temp = destino / f"{tipo}.zip.tmp"
            with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as z:
                for a in arqs:
                    z.write(a, a.name)
            os.replace(temp, final)
    return {t: len(a) for t, a in grupos.items()}


def resumo(contagem):
    partes = [f"{contagem[t]} {t}" for t in TIPOS if contagem.get(t)]
    if contagem.get(OUTROS):
        partes.append(f"{contagem[OUTROS]} não reconhecido(s)")
    return ", ".join(partes) or "nenhum XML"

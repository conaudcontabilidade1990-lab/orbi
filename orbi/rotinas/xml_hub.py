"""Separar e zipar os XML do HubStrom por tipo (NF-e, NFC-e, CT-e, NFS-e), empresa por empresa.
Não mexe no Domínio: só lê e grava arquivos no computador."""
from pathlib import Path

from .. import xmls
from .base import Rotina


class SepararXml(Rotina):
    id = "separar_xml"
    nome = "Separar e zipar XML por tipo"
    departamento = "fiscal"
    descricao = ("Na pasta do HubStrom, para cada empresa e mês da competência, separa os XML em NF-e, "
                 "NFC-e, CT-e e NFS-e e cria um .zip de cada tipo dentro da própria pasta do mês "
                 "(ex.: 112026\\NF-e\\NF-e.zip) só com os XML que ainda não foram importados. "
                 "Não mexe no Domínio. Em simulação só conta.")
    usa_competencia = True
    usa_dominio = False
    usa_pasta_xml = True

    def __init__(self):
        self.pasta_base = ""

    def meses(self):
        (a1, m1), (a2, m2) = self.competencia
        a, m = a1, m1
        while (a, m) <= (a2, m2):
            yield a, m
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)

    def executar_empresa(self, t, codigo, simular):
        base = Path(self.pasta_base or "")
        if not base.is_dir():
            from ..tela import Parar
            raise Parar(f"A pasta dos XML não existe: '{base}'. Ajuste em 'Pasta dos XML'.")
        emp = xmls.pasta_da_empresa(base, codigo)
        if not emp:
            t.aviso("sem pasta da empresa")
            return f"não há pasta '{codigo}-…' em {base}"
        partes = []
        for a, m in self.meses():
            t.checar()
            pasta_mes = emp / f"{m:02d}{a}"
            if not pasta_mes.is_dir():
                t.aviso(f"sem pasta {m:02d}{a}")
                partes.append(f"{m:02d}/{a}: sem pasta")
                continue
            cont = xmls.separar(pasta_mes, gravar=not simular)
            if cont.get(xmls.OUTROS):
                t.aviso(f"{cont[xmls.OUTROS][0]} XML não reconhecido(s) em {m:02d}/{a}")
            n = xmls.pendentes(cont)
            partes.append(f"{m:02d}/{a}: {xmls.resumo(cont)}" + ("" if n else " — nada novo para importar"))
        acao = "contados (simulação)" if simular else "separados; zip só com o que falta importar"
        return f"{acao} — " + "; ".join(partes)


class MarcarImportados(SepararXml):
    id = "marcar_xml_importados"
    nome = "Marcar XML como importados"
    descricao = ("Use depois de importar no Domínio os zips da separação: os XML que estavam nos zips passam a "
                 "contar como importados e não entram mais nos próximos zips. XML que chegaram depois "
                 "continuam pendentes. Em simulação só mostra o que seria marcado.")

    def executar_empresa(self, t, codigo, simular):
        base = Path(self.pasta_base or "")
        if not base.is_dir():
            from ..tela import Parar
            raise Parar(f"A pasta dos XML não existe: '{base}'. Ajuste em 'Pasta dos XML'.")
        emp = xmls.pasta_da_empresa(base, codigo)
        if not emp:
            t.aviso("sem pasta da empresa")
            return f"não há pasta '{codigo}-…' em {base}"
        partes = []
        for a, m in self.meses():
            t.checar()
            pasta_mes = emp / f"{m:02d}{a}"
            if not pasta_mes.is_dir():
                partes.append(f"{m:02d}/{a}: sem pasta")
                continue
            if simular:
                marc = {tp: len(xmls._nomes(pasta_mes / tp / "pendentes.txt")) for tp in xmls.TIPOS}
                marc = {k: v for k, v in marc.items() if v}
            else:
                marc = xmls.marcar_importados(pasta_mes)
            partes.append(f"{m:02d}/{a}: " + (xmls.resumo(marc) if marc else "nenhum zip pendente"))
        return ("seria marcado (simulação)" if simular else "marcados como importados") + " — " + "; ".join(partes)

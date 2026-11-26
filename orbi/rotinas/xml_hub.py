"""Separar e zipar os XML do HubStrom por tipo (NF-e, NFC-e, CT-e, NFS-e), empresa por empresa.
Não mexe no Domínio: só lê e grava arquivos no computador."""
import re
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


class ImportarXml(SepararXml):
    """Separa/zipa o que falta importar e importa cada tipo no Domínio (Importação Padrão)."""
    id = "importar_xml"
    nome = "Importar XML do HubStrom no Domínio"
    descricao = ("Para cada empresa e mês: separa os XML por tipo, zipa só o que ainda não foi importado e importa "
                 "no Domínio (NF-e e NFC-e: Todos; CT-e: entradas e canceladas; NFS-e: tomado, prestado e "
                 "canceladas), marcando Todos nas advertências e gravando. O que foi gravado fica marcado como "
                 "importado. Em simulação vai até o Resumo dos Dados e cancela.")
    usa_dominio = True
    precisa_regioes = ("sel_campo", "dlg_importacao")

    def checagem(self, empresas):
        """Antes de abrir o Domínio: só ficam as empresas com XML ainda não importado na competência.
        Devolve (empresas a processar, {código: motivo} das puladas). Não grava nada."""
        base = Path(self.pasta_base or "")
        manter, pulos = [], {}
        for cod in empresas:
            emp = xmls.pasta_da_empresa(base, cod) if base.is_dir() else None
            if not emp:
                pulos[cod] = "sem pasta no HubStrom"
                continue
            pend = 0
            for a, m in self.meses():
                pasta_mes = emp / f"{m:02d}{a}"
                if pasta_mes.is_dir():
                    pend += xmls.pendentes(xmls.separar(pasta_mes, gravar=False))
            if pend:
                manter.append(cod)
            else:
                pulos[cod] = "nada novo para importar"
        return manter, pulos

    @staticmethod
    def _cnpj(codigo):
        """CNPJ da empresa pelo cadastro do portal (cópia local)."""
        try:
            from .. import portal
            empresas, _ = portal.empresas_guardadas()
            return next((e.get("cnpj", "") for e in empresas if str(e.get("codigo")) == str(codigo)), "")
        except Exception:
            return ""

    def _no_dominio(self, t, caminho):
        """Caminho deste computador -> como o Domínio (remoto) enxerga: C: vira M:, Z: (servidor) continua Z:."""
        p = str(caminho)
        mapa = {k.upper(): v for k, v in (t.cfg.get("unidades_dominio") or {"C:": t.cfg.get("dominio_unidade", "M:")}).items()}
        unidade = p[:2].upper()
        if unidade not in mapa:
            from ..tela import Parar
            raise Parar(f"Não sei como o Domínio enxerga o disco {unidade} (pasta '{p}'). "
                        f"Discos conhecidos: {', '.join(mapa)}.")
        return mapa[unidade] + p[2:]

    def executar_empresa(self, t, codigo, simular):
        from .. import dominio as d
        from .. import importacao as imp
        from ..tela import Parar
        base = Path(self.pasta_base or "")
        if not base.is_dir():
            raise Parar(f"A pasta dos XML não existe: '{base}'. Ajuste em 'Pasta dos XML'.")
        emp = xmls.pasta_da_empresa(base, codigo)
        if not emp:
            t.aviso("sem pasta da empresa")
            return f"não há pasta '{codigo}-…' em {base}"
        _limpar_pasta_antiga()
        partes, trocou = [], False
        for a, m in self.meses():
            t.checar()
            mmaaaa = f"{m:02d}{a}"
            pasta_mes = emp / mmaaaa
            if not pasta_mes.is_dir():
                t.aviso(f"sem pasta {mmaaaa}")
                partes.append(f"{m:02d}/{a}: sem pasta")
                continue
            cont = xmls.separar(pasta_mes, gravar=True)
            if cont.get(xmls.OUTROS):
                t.aviso(f"{cont[xmls.OUTROS][0]} XML não reconhecido(s) em {m:02d}/{a}")
            tipos = [tp for tp in xmls.TIPOS if cont.get(tp) and cont[tp][1] and (pasta_mes / tp / f"{tp}.zip").exists()]
            if not tipos:
                partes.append(f"{m:02d}/{a}: nada novo para importar")
                continue
            if not trocou:
                d.trazer_para_frente(t)
                d.trocar_empresa(t, codigo)
                trocou = True
            feitos = []
            for tp in tipos:
                t.log(f"  {m:02d}/{a} · {tp}: importando {cont[tp][1]} XML…")
                pular = ()
                if tp == "NFS-e":
                    ops = xmls.opcoes_nfse(pasta_mes / tp, self._cnpj(codigo))
                    pular = tuple(n for n, chave in (("Serviço tomado", "tomado"), ("Serviço prestado", "prestado"))
                                  if chave not in ops)
                erros = set()
                res = imp.importar_tipo(t, tp, self._no_dominio(t, pasta_mes / tp), f"{mmaaaa}\\{tp}", simular,
                                        pular, erros)
                if not simular:
                    com_erro = xmls.separar_com_erro(pasta_mes, tp, erros) if erros else []
                    if erros and len(com_erro) < len(erros):
                        t.aviso(f"{tp}: documento(s) com erro sem XML correspondente: "
                                f"{sorted(erros - {xmls.numero_da_chave(n) for n in com_erro})[:10]}")
                    if com_erro:
                        t.aviso(f"{len(com_erro)} XML de {tp} com erro copiados para {tp}\\{xmls.PASTA_ERRO} "
                                "(ficam fora dos próximos zips até saírem dessa pasta)")
                    xmls.marcar_importados(pasta_mes, [tp], excluir=com_erro)
                feitos.append(f"{tp} ({cont[tp][1]}): " + " | ".join(res))
            partes.append(f"{m:02d}/{a}: " + "; ".join(feitos))
        return ("simulação — " if simular else "importado — ") + " / ".join(partes)


def _limpar_pasta_antiga():
    """Versões 0.9.7/0.9.8 copiavam o zip para C:\\Users\\Public\\OrbiImport; não usa mais."""
    import os
    import shutil
    antiga = Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "OrbiImport"
    if antiga.exists():
        shutil.rmtree(antiga, ignore_errors=True)

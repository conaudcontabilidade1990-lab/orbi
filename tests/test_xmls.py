"""Separação dos XML por tipo e zip por tipo (pastas falsas, sem dados de clientes)."""
import sys
import tempfile
import types
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("pyautogui", types.SimpleNamespace(FAILSAFE=True, PAUSE=0))

from orbi import xmls  # noqa: E402
from orbi.rotinas.xml_hub import MarcarImportados, SepararXml  # noqa: E402
from orbi import agenda  # noqa: E402
import datetime as dt  # noqa: E402


assert xmls.tipo_da_chave("35261105466705000112550020000057516565952190") == "NF-e"
assert xmls.tipo_da_chave("35261105466705000112650020000057516565952190") == "NFC-e"
assert xmls.tipo_da_chave("35261105466705000112570020000057516565952190") == "CT-e"
assert xmls.tipo_da_chave("35261105466705000112670020000057516565952190") == "CT-e"
assert xmls.tipo_da_chave("3" * 50) == "NFS-e"
assert xmls.tipo_da_chave("123") is None

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    mes = base / "494-EMPRESA TESTE" / "112026"
    mes.mkdir(parents=True)
    (base / "4940-OUTRA").mkdir()
    def k(mod, i):   # UF(2) AAMM(4) CNPJ(14) modelo(2) série(3) número(9) tpEmis(1) código(8) DV(1)
        return f"35" f"2611" f"00000000000191" f"{mod}" "002" f"{i:09d}" "1" f"{i:08d}" "0"
    for i in range(3): (mes / f"{k('55', i)}.xml").write_text("<nfeProc/>")
    for i in range(5): (mes / f"{k('65', i)}.xml").write_text("<nfeProc/>")
    for i in range(2): (mes / f"{k('57', i)}.xml").write_text("<cteProc/>")
    (mes / f"{'35' * 25}.xml").write_text("<NFSe/>")
    (mes / "evento_cancelamento.xml").write_text("<procEventoNFe><chNFe>%s</chNFe></procEventoNFe>" % k("55", 9))
    (mes / "sem_nada.xml").write_text("<qualquer/>")
    for a in mes.iterdir():
        assert len(a.stem) in (44, 50) or not a.stem.isdigit(), a.name

    assert xmls.pasta_da_empresa(base, "494").name == "494-EMPRESA TESTE"
    assert xmls.pasta_da_empresa(base, "49") is None

    c = xmls.separar(mes, gravar=False)
    assert c == {"NF-e": (4, 4), "NFC-e": (5, 5), "CT-e": (2, 2), "NFS-e": (1, 1), "Outros": (1, 1)}, c
    assert not (mes / "NF-e").exists()
    c = xmls.separar(mes)
    for tipo, n in (("NF-e", 4), ("NFC-e", 5), ("CT-e", 2), ("NFS-e", 1)):
        z = mes / tipo / f"{tipo}.zip"
        assert z.exists() and len(zipfile.ZipFile(z).namelist()) == n, tipo
        assert sorted(p.name for p in (mes / tipo).iterdir()) == sorted([f"{tipo}.zip", "pendentes.txt"])
    assert xmls.separar(mes) == c          # rodar de novo não duplica nem zipa os zips
    print("resumo:", xmls.resumo(c))

    r = SepararXml()
    r.pasta_base, r.competencia = str(base), ((2026, 10), (2026, 11))
    avisos = []
    t = types.SimpleNamespace(aviso=avisos.append, checar=lambda: None)
    txt = r.executar_empresa(t, "494", simular=False)
    print(txt, avisos)
    assert "10/2026: sem pasta" in txt and "11/2026: 4 NF-e, 5 NFC-e, 2 CT-e, 1 NFS-e" in txt
    assert "sem pasta 102026" in avisos and any("não reconhecido" in a for a in avisos)
    assert "não há pasta" in r.executar_empresa(t, "999", simular=True)

    # importou os zips no Domínio -> marca; depois chegam 2 NF-e novas
    mk = MarcarImportados()
    mk.pasta_base, mk.competencia = str(base), ((2026, 11), (2026, 11))
    print(mk.executar_empresa(t, "494", simular=True))
    assert (mes / "NF-e" / "NF-e.zip").exists()        # simulação não marca
    txt = mk.executar_empresa(t, "494", simular=False)
    print(txt)
    assert "4 NF-e" in txt and not (mes / "NF-e" / "NF-e.zip").exists()
    assert len((mes / "NF-e" / "importados.txt").read_text().split()) == 4
    for i in (20, 21): (mes / f"{k('55', i)}.xml").write_text("<nfeProc/>")
    txt = r.executar_empresa(t, "494", simular=False)
    print(txt)
    assert "6 NF-e (2 a importar)" in txt and "5 NFC-e (0 a importar)" in txt
    z = zipfile.ZipFile(mes / "NF-e" / "NF-e.zip").namelist()
    assert sorted(z) == sorted(f"{k('55', i)}.xml" for i in (20, 21)), z
    assert not (mes / "NFC-e" / "NFC-e.zip").exists()   # nada novo de NFC-e: sem zip
    mk.executar_empresa(t, "494", simular=False)
    assert "nada novo" in r.executar_empresa(t, "494", simular=False).split("11/2026")[1]

assert agenda.competencia_de("anterior_atual", dt.date(2026, 1, 5)) == ((2025, 12), (2026, 1))
print("ok: XML separados e zipados por tipo")

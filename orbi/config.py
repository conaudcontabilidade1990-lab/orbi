"""Configuração do Orbi.

Os valores padrão ficam aqui. Ajustes feitos na calibração ficam em
%APPDATA%\\Orbi\\config.json e se sobrepõem aos padrões (atualizações não apagam esse arquivo).
"""
import copy
import json
import os
from pathlib import Path

PASTA = Path(os.environ.get("APPDATA", Path.home())) / "Orbi"
PASTA_LOGS = PASTA / "logs"
ARQUIVO = PASTA / "config.json"

ESQUEMA = 6  # sobe quando pontos/regiões padrão mudam; ajustes antigos são descartados

PADRAO = {
    "resolucao": [1366, 768],
    "idioma_ocr": "pt-BR",
    "tempos": {
        "pausa": 0.7,           # segundos entre ações
        "busca": 8,
        "troca": 8,             # espera a janela/lista da Troca de empresas atualizar             # espera a lista/mensagem após Buscar
        "confirmacao": 15,      # espera o "Você tem certeza..."
        "sucesso": 600,         # espera "Parcelas geradas com sucesso." (listas grandes)
    },
    "limiar_caixa": 6,          # pixels escuros no centro da caixa = marcada
    # Pontos de clique (x, y) em 1366x768
    "pontos": {
        "titulo_app": [60, 12],
        "troca_empresa": [131, 93], "troca_por_codigo": [482, 199], "troca_busca": [603, 227],
        "troca_acessar": [703, 704], "troca_fechar": [875, 704], "troca_amostra_azul": [880, 300],
        "menu_utilitarios": [495, 53], "menu_parcelas": [583, 441], "menu_gerar": [917, 443],
        "menu_entradas": [1055, 445], "menu_saidas": [1050, 468], "menu_servicos": [1053, 490],
        "titulo_janela_normal": [500, 217],   # duplo clique maximiza a janela Gerar Parcelas
        # janela maximizada
        "caixa_sem_parcelas": [42, 190], "caixa_nao_geram": [42, 210],
        "buscar": [1312, 689], "busca_avancada": [1206, 689], "todos": [60, 689],
        "gerar_abrir": [1098, 689], "fechar_janela": [1356, 33],
        # diálogo Gerar
        "radio_todas": [333, 254], "radio_somente": [333, 274],
        "venc_dropdown": [583, 354], "venc_informar": [500, 379], "campo_dias": [488, 378],
        "dlg_gerar": [1014, 244], "dlg_cancelar": [1014, 278],
        "btn_sim": [752, 440], "btn_ok_sucesso": [758, 440], "btn_ok_vazio": [830, 440],
    },
    # Regiões de leitura (x, y, largura, altura). null = ainda não calibrada.
    "regioes": {
        "titulo_app": [0, 0, 700, 24],          # título do Domínio; com janela maximizada traz [Gerar Parcelas...]
        "mensagem": [250, 300, 866, 180],
        "empresa_ativa": [1150, 60, 216, 52],   # "ADEMIR BELTRANI - 611" (normal ou com janela maximizada)
        "troca_titulo": [433, 133, 250, 18],    # título "Troca de empresas"
        "troca_lista": [455, 289, 440, 380],    # lista da Troca de empresas (procura a linha azul)
        "dialogo_gerar": [294, 190, 782, 400],
        "campo_parcelas": [469, 324, 42, 14],  # interior do campo, sem borda e setas
        "campo_vencimento": [468, 346, 110, 17],
        "campo_dias": [469, 371, 42, 14],
        "botao_buscar": [1262, 679, 100, 20],
    },
    # Preferências da tela
    "ultima_rotina": "",
    "ultimas_empresas": "",
    "ultimo_email": "",
    "lembrar": True,
    "tema": "claro",
}


def _mesclar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


PREFERENCIAS = ("ultima_rotina", "ultimas_empresas", "ultimo_email", "lembrar", "tema")


def _diferenca(atual, base):
    """Só o que difere do padrão — assim melhorias nos padrões chegam com as atualizações."""
    out = {}
    for k, v in atual.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            d = _diferenca(v, base[k])
            if d:
                out[k] = d
        elif base.get(k) != v:
            out[k] = v
    return out


def carregar():
    cfg = copy.deepcopy(PADRAO)
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        if dados.get("esquema") != ESQUEMA:  # arquivo de versão antiga: mantém só as preferências
            dados = {k: v for k, v in dados.items() if k in PREFERENCIAS}
        _mesclar(cfg, dados)
    except FileNotFoundError:
        pass
    except Exception as e:  # arquivo corrompido: usa padrão, mas avisa
        cfg["_erro_config"] = str(e)
    return cfg


def salvar(cfg):
    PASTA.mkdir(parents=True, exist_ok=True)
    dados = _diferenca(cfg, PADRAO)
    dados["esquema"] = ESQUEMA
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

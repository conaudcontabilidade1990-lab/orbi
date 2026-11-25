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

PADRAO = {
    "resolucao": [1366, 768],
    "idioma_ocr": "pt-BR",
    "tempos": {
        "pausa": 0.7,           # segundos entre ações
        "busca": 8,             # espera a lista/mensagem após Buscar
        "confirmacao": 15,      # espera o "Você tem certeza..."
        "sucesso": 600,         # espera "Parcelas geradas com sucesso." (listas grandes)
    },
    "limiar_caixa": 6,          # pixels escuros no centro da caixa = marcada
    # Pontos de clique (x, y) em 1366x768
    "pontos": {
        "titulo_app": [60, 12],
        "troca_empresa": [131, 93], "troca_busca": [600, 227], "troca_acessar": [703, 704],
        "menu_utilitarios": [495, 53], "menu_parcelas": [583, 436], "menu_gerar": [1003, 439],
        "menu_entradas": [1142, 441], "menu_saidas": [1136, 463], "menu_servicos": [1141, 485],
        "maximizar": [1004, 206],
        "caixa_sem_parcelas": [42, 190], "caixa_nao_geram": [42, 210],
        "buscar": [1312, 689], "busca_avancada": [1206, 689], "todos": [60, 689],
        "gerar_abrir": [1098, 689], "fechar_janela": [1355, 33],
        "venc_dropdown": [583, 354], "venc_informar": [490, 384], "campo_dias": [488, 378],
        "dlg_gerar": [1014, 244], "dlg_cancelar": [1014, 278],
        "btn_sim": [752, 440], "btn_ok_sucesso": [758, 440], "btn_ok_vazio": [830, 440],
    },
    # Regiões de leitura (x, y, largura, altura). null = ainda não calibrada.
    "regioes": {
        "mensagem": [250, 300, 866, 180],
        "empresa_ativa": [850, 0, 516, 45],
        "titulo_janela": [0, 20, 900, 28],
        "dialogo_gerar": [300, 200, 780, 260],
        "campo_dias": [455, 368, 90, 22],
        "campo_parcelas": None,
    },
    # Preferências da tela
    "ultima_rotina": "",
    "ultimas_empresas": "",
}


def _mesclar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar():
    cfg = copy.deepcopy(PADRAO)
    try:
        _mesclar(cfg, json.loads(ARQUIVO.read_text(encoding="utf-8")))
    except FileNotFoundError:
        pass
    except Exception as e:  # arquivo corrompido: usa padrão, mas avisa
        cfg["_erro_config"] = str(e)
    return cfg


def salvar(cfg):
    PASTA.mkdir(parents=True, exist_ok=True)
    dados = {k: v for k, v in cfg.items() if not k.startswith("_")}
    ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

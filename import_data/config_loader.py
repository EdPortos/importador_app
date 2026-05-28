"""
Carrega o config.json de fora do .exe.

Ordem de busca:
1. Pasta ao lado do .exe (produção)
2. Raiz do projeto (desenvolvimento)
"""
import json
import os
import sys

UPLOAD_FOLDER      = None
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB
DATASET_CONFIG     = {}
SERVERS            = {}
DB_CONFIG          = {}


def _get_config_path():
    # Modo .exe — procura ao lado do executável
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Modo desenvolvimento — raiz do projeto
        exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(exe_dir, 'config.json')


def carregar_config():
    global DATASET_CONFIG, SERVERS, DB_CONFIG, UPLOAD_FOLDER

    config_path = _get_config_path()

    if not os.path.exists(config_path):
        print(f"[config] config.json não encontrado em: {config_path}")
        print("[config] Datasets não carregados — coloque o config.json ao lado do executável.")
        return False

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        DATASET_CONFIG = data.get('DATASET_CONFIG', {})
        SERVERS        = data.get('SERVERS', {})
        DB_CONFIG      = data.get('DB_CONFIG', {})
        UPLOAD_FOLDER  = os.path.join(os.path.dirname(config_path), 'uploads')

        print(f"[config] {len(DATASET_CONFIG)} dataset(s) carregado(s) de: {config_path}")
        return True

    except Exception as e:
        print(f"[config] Erro ao carregar config.json: {e}")
        return False


# Carrega automaticamente ao importar
carregar_config()
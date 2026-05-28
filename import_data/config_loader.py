"""
Carrega o config.py dinamicamente de fora do .exe.

Ordem de busca:
1. Pasta ao lado do .exe (produção)
2. Pasta import_data/ do projeto (desenvolvimento)
"""
import importlib.util
import os
import sys


def _get_config_path():
    # Modo .exe — procura ao lado do executável
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        path = os.path.join(exe_dir, 'import_data', 'config.py')
        if os.path.exists(path):
            return path
        raise FileNotFoundError(
            f"config.py não encontrado em: {path}\n"
            f"Certifique-se de que a pasta 'import_data' está ao lado do executável."
        )

    # Modo desenvolvimento — usa o config.py do projeto
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, 'config.py')
    if os.path.exists(path):
        return path

    raise FileNotFoundError(f"config.py não encontrado em: {path}")


def carregar_config():
    """Carrega e retorna o módulo config.py dinamicamente."""
    config_path = _get_config_path()
    spec   = importlib.util.spec_from_file_location("config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Carrega uma vez e expõe as variáveis diretamente
_config = carregar_config()

DATASET_CONFIG     = _config.DATASET_CONFIG
SERVERS            = _config.SERVERS
DB_CONFIG          = _config.DB_CONFIG
UPLOAD_FOLDER      = _config.UPLOAD_FOLDER
MAX_CONTENT_LENGTH = _config.MAX_CONTENT_LENGTH
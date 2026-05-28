import logging
import os
from datetime import datetime

APP_NAME  = "ImportadorApp"
LOG_DIR   = os.path.join(os.environ.get('LOCALAPPDATA', ''), APP_NAME)
LOG_FILE  = os.path.join(LOG_DIR, "app.log")
MAX_BYTES = 5 * 1024 * 1024
BACKUPS   = 3


def setup_logger():
    """Configura e retorna o logger principal da aplicação."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger("importador_app")

    if logger.handlers:
        return logger  # já configurado

    logger.setLevel(logging.DEBUG)

    # Formato
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)-5s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler — arquivo com rotação automática
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUPS,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler — console (visível no CMD em modo dev)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Logger global — importado pelos outros módulos
log = setup_logger()


def get_log_path():
    return LOG_FILE
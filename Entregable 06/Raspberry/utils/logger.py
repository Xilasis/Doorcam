"""
logger.py

Configuración centralizada de Loguru para el nodo IoT.
"""

import sys
from pathlib import Path
from loguru import logger

import config


def setup_logger():
    """
    Inicializa la configuración global de logs.
    """

    # Crear carpeta de logs si no existe
    config.LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Eliminar logger por defecto
    logger.remove()


    # ===============================
    # Consola (systemd / desarrollo)
    # ===============================

    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )


    # ===============================
    # Archivo persistente
    # ===============================

    logger.add(
        config.LOG_FILE,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level} | "
            "{thread.name} | "
            "{message}"
        )
    )


    logger.info(
        "Sistema de logging inicializado"
    )


def get_logger():
    """
    Retorna la instancia global de Loguru.
    """

    return logger
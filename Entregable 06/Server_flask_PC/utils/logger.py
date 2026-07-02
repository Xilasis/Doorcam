"""
logger.py

Configuración centralizada de logs para el IoT Gateway.

Responsabilidades:
- Configurar salida por consola.
- Guardar logs en archivo.
- Rotación automática.
- Entregar una instancia compartida de Loguru.
"""

from pathlib import Path
from loguru import logger


# Evitar configurar varias veces
_configured = False


def _configure_logger():
    """
    Configuración interna del logger.
    """
    global _configured

    if _configured:
        return

    # Crear directorio logs si no existe
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)


    # Eliminar configuración por defecto
    logger.remove()


    # ================================
    # Consola
    # ================================
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )


    # ================================
    # Archivo
    # ================================
    logger.add(
        "logs/gateway.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    )


    _configured = True


def get_logger():
    """
    Devuelve el logger configurado.

    Uso:
        from utils.logger import get_logger

        logger = get_logger()

        logger.info("Mensaje")
    """

    _configure_logger()

    return logger
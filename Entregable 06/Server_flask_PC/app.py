"""
app.py

Bootstrap del IoT Gateway.

Fase actual:
- Validación End-to-End con RPi Zero 2W.
- Comunicación bidireccional mediante Telegram.
- Long Polling integrado.
"""

import threading
import signal
import sys

from flask import Flask
from loguru import logger


# ==========================================================
# Inicialización de servicios singleton
# ==========================================================

from services.instances import (
    node_client,
    telegram_client
)


# ==========================================================
# Rutas del Gateway
# ==========================================================

from routes.events import events_bp
from routes.telegram import telegram_bp


# ==========================================================
# Servicio Long Polling Telegram
# ==========================================================

from services.poll_telegram import (
    poll_telegram_updates
)
#=============================================
#Importando datos de  config
#================================================
from config.config import (
    HOST, PORT
)
# ==========================================================
# Factory Flask
# ==========================================================

def create_app():

    app = Flask(__name__)


    logger.info(
        "Registrando Blueprints..."
    )


    app.register_blueprint(
        events_bp
    )


    app.register_blueprint(
        telegram_bp
    )


    logger.success(
        "Rutas registradas correctamente"
    )


    return app


# ==========================================================
# Telegram Polling
# ==========================================================

def start_telegram_polling():

    logger.info(
        "Iniciando Telegram Long Polling"
    )


    thread = threading.Thread(
        target=poll_telegram_updates,
        name="TelegramPolling",
        daemon=True
    )


    thread.start()


    logger.success(
        "Telegram Polling activo"
    )


    return thread


# ==========================================================
# Cierre ordenado
# ==========================================================

def shutdown(signum=None, frame=None):

    logger.warning(
        "Deteniendo IoT Gateway..."
    )


    try:
        node_client.close()
        logger.info(
            "NodeClient detenido"
        )

    except Exception as e:

        logger.exception(
            f"Error cerrando NodeClient: {e}"
        )


    try:
        telegram_client.close()

        logger.info(
            "TelegramClient detenido"
        )

    except Exception as e:

        logger.exception(
            f"Error cerrando TelegramClient: {e}"
        )


    logger.success(
        "Gateway apagado correctamente"
    )


    sys.exit(0)


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":

    logger.info(
        "=" * 50
    )

    logger.info(
        "Iniciando IoT Flask Gateway"
    )

    logger.info(
        "Modo: Validación E2E RPi Zero 2W"
    )

    logger.info(
        "=" * 50
    )


    # Señales del sistema
    signal.signal(
        signal.SIGINT,
        shutdown
    )


    signal.signal(
        signal.SIGTERM,
        shutdown
    )


    # Crear aplicación Flask
    app = create_app()


    # Iniciar Long Polling
    start_telegram_polling()


    logger.success(
        "Gateway listo para pruebas"
    )

    import config.config

    print("Archivo config:", config.config.__file__)
    print("HOST =", HOST)
    print("PORT =", PORT)
    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True
    )
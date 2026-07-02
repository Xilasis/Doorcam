"""
main.py

Orquestador principal del nodo Raspberry Pi Zero 2W.
"""

import time
import signal
import sys
import threading
from queue import Queue

import config


# ==========================================================
# Logging (debe ser lo primero)
# ==========================================================

from utils.logger import setup_logger, get_logger

setup_logger()

logger = get_logger()


# ==========================================================
# Servicios
# ==========================================================

from services.camera_service import CameraService
from services.pir_service import PIRService
from services.network_service import NetworkService
from services.uploader_service import UploaderService


# ==========================================================
# Workers
# ==========================================================

from workers.capture_worker import CaptureWorker


# ==========================================================
# API Local
# ==========================================================

from api.routes import start_api


# ==========================================================
# Variables globales
# ==========================================================

running = True

event_queue = Queue()


# ==========================================================
# Señales del sistema
# ==========================================================

def shutdown_handler(signum, frame):
    """
    Captura SIGINT y SIGTERM.
    """
    global running

    logger.warning(
        f"Señal {signum} recibida. Iniciando apagado seguro..."
    )

    running = False


# ==========================================================
# Inicialización del nodo
# ==========================================================

def initialize_node():
    """
    Inicializa todos los componentes del sistema.
    """

    logger.info("=" * 60)
    logger.info(f"Inicializando {config.APP_NAME}")
    logger.info(f"Versión: {config.VERSION}")
    logger.info(f"Node ID: {config.NODE_ID}")
    logger.info("=" * 60)


    # ------------------------------------------------------
    # Queue de eventos
    # ------------------------------------------------------

    logger.info("Inicializando servicios...")


    # ------------------------------------------------------
    # Cámara CSI
    # ------------------------------------------------------

    camera = CameraService()

    camera.start()


    # ------------------------------------------------------
    # Cliente HTTP persistente
    # ------------------------------------------------------

    uploader = UploaderService()


    # ------------------------------------------------------
    # Diagnóstico de red
    # ------------------------------------------------------

    network = NetworkService()


    # ------------------------------------------------------
    # Worker de captura
    # ------------------------------------------------------

    capture_worker = CaptureWorker(
        event_queue=event_queue,
        camera=camera,
        uploader=uploader
    )


    capture_thread = threading.Thread(
        target=capture_worker.run,
        name="CaptureWorker",
        daemon=True
    )

    capture_thread.start()


    logger.success(
        "CaptureWorker iniciado"
    )


    # ------------------------------------------------------
    # Sensor PIR
    # ------------------------------------------------------

    pir = PIRService(
        event_queue=event_queue
    )


    pir.start()


    # ------------------------------------------------------
    # API HTTP local
    # ------------------------------------------------------

    api_thread = threading.Thread(
        target=start_api,
        args=(camera, network),
        name="NodeAPI",
        daemon=True
    )

    api_thread.start()


    logger.success(
        "API local iniciada"
    )


    logger.success(
        "Nodo IoT listo para operar"
    )


    return {
        "camera": camera,
        "uploader": uploader,
        "network": network,
        "pir": pir,
        "capture_worker": capture_worker,
        "threads": {
            "capture": capture_thread,
            "api": api_thread
        }
    }


# ==========================================================
# Apagado ordenado
# ==========================================================

def shutdown(resources):
    """
    Libera todos los recursos del nodo.
    """

    logger.warning(
        "Iniciando secuencia de apagado..."
    )


    # ----------------------------------------------
    # Detener PIR
    # ----------------------------------------------

    try:
        resources["pir"].stop()

    except Exception as e:

        logger.exception(
            f"Error deteniendo PIR: {e}"
        )


    # ----------------------------------------------
    # Detener CaptureWorker
    # ----------------------------------------------

    try:
        resources["capture_worker"].stop()

    except Exception as e:

        logger.exception(
            f"Error deteniendo CaptureWorker: {e}"
        )


    # ----------------------------------------------
    # Cerrar conexión HTTP
    # ----------------------------------------------

    try:
        resources["uploader"].close()

    except Exception as e:

        logger.exception(
            f"Error cerrando UploaderService: {e}"
        )


    # ----------------------------------------------
    # Apagar cámara
    # ----------------------------------------------

    try:
        resources["camera"].stop()

    except Exception as e:

        logger.exception(
            f"Error deteniendo cámara: {e}"
        )


    logger.success(
        "Todos los servicios fueron detenidos"
    )


# ==========================================================
# Programa principal
# ==========================================================

def main():

    global running

    resources = None


    signal.signal(
        signal.SIGINT,
        shutdown_handler
    )


    signal.signal(
        signal.SIGTERM,
        shutdown_handler
    )


    try:

        resources = initialize_node()


        logger.info(
            "Sistema operativo. Esperando eventos..."
        )


        while running:

            time.sleep(1)


    except Exception as e:

        logger.exception(
            f"Error fatal del nodo: {e}"
        )

        sys.exit(1)


    finally:

        if resources:

            shutdown(resources)


        logger.info(
            "Proceso principal finalizado"
        )


        sys.exit(0)


# ==========================================================
# Entry Point
# ==========================================================

if __name__ == "__main__":

    main()

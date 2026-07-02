"""
pir_service.py

Servicio de detección de movimiento mediante sensor PIR.
Versión usando gpiozero.
"""

from gpiozero import MotionSensor

import config

from utils.logger import get_logger
from utils.helpers import (
    generate_event_id,
    utc_now
)

logger = get_logger()


class PIRService:
    """
    Servicio PIR basado en gpiozero.
    """

    def __init__(self, event_queue):

        self.queue = event_queue
        self.pin = config.PIR_GPIO

        self.enabled = False
        self.sensor = None


    # ==================================================
    # Callback
    # ==================================================

    def motion_callback(self):
        """
        Ejecutado cuando el PIR detecta movimiento.
        """

        if not self.enabled:
            return

        try:

            event = {
                "event_id": generate_event_id(),
                "type": "MOTION",
                "source": "PIR",
                "gpio": self.pin,
                "timestamp": utc_now()
            }

            self.queue.put_nowait(event)

            logger.info(
                f"[{event['event_id']}] "
                f"Movimiento detectado GPIO {self.pin}. "
                "Evento publicado en Queue."
            )

        except Exception as e:

            logger.exception(
                f"Error en callback PIR: {e}"
            )


    # ==================================================
    # Inicialización
    # ==================================================

    def start(self):

        self.sensor = MotionSensor(self.pin)

        self.sensor.when_motion = self.motion_callback

        self.enabled = True

        logger.success(
            f"PIR iniciado correctamente "
            f"en GPIO BCM {self.pin} "
            f"(cooldown: {config.PIR_COOLDOWN}s)"
        )


    # ==================================================
    # Control
    # ==================================================

    def enable(self):

        self.enabled = True

        logger.info(
            "PIR habilitado"
        )


    def disable(self):

        self.enabled = False

        logger.warning(
            "PIR deshabilitado"
        )


    def status(self):

        return {
            "enabled": self.enabled,
            "gpio": self.pin
        }


    # ==================================================
    # Liberación
    # ==================================================

    def stop(self):

        self.enabled = False

        if self.sensor is not None:
            self.sensor.close()

        logger.info(
            "PIR detenido"
        )

"""
camera_service.py
Gestión de cámara CSI mediante Picamera2.
"""

import time
from io import BytesIO

from picamera2 import Picamera2
from PIL import Image

from loguru import logger
import config


class CameraService:

    def __init__(self):
        self.camera = Picamera2()


    def start(self):

        camera_config = self.camera.create_still_configuration(
            main={
                "size": (
                    config.CAMERA_WIDTH,
                    config.CAMERA_HEIGHT
                )
            }
        )

        self.camera.configure(camera_config)

        self.camera.start()

        time.sleep(config.CAMERA_WARMUP)

        logger.success(
            "Cámara Picamera2 inicializada"
        )


    def capture(self) -> bytes:
        """
        Captura una imagen y la devuelve como JPEG en memoria.
        """

        frame = self.camera.capture_array()

        image = Image.fromarray(frame)

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=config.JPEG_QUALITY
        )

        buffer.seek(0)

        logger.info(
            "Imagen capturada en memoria"
        )

        return buffer.read()


    def stop(self):

        self.camera.stop()

        logger.info(
            "Cámara detenida"
        )

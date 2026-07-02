"""
uploader_service.py

Cliente HTTP encargado de enviar imágenes al servidor Flask central.
"""

import time
import requests

import config

from utils.logger import get_logger
from utils.helpers import utc_now, generate_event_id


logger = get_logger()


class UploaderService:

    def __init__(self):
        """
        Inicializa una sesión HTTP persistente.
        """
        self.session = requests.Session()

        logger.info(
            "UploaderService inicializado con HTTP Session persistente"
        )


    def send_image(self, image_bytes, event="motion", event_id=None):
        """
        Envía una imagen al servidor Flask.
        """

        if event_id is None:
            event_id = generate_event_id()


        headers = {
            "Authorization": f"Bearer {config.TOKEN}",
            "X-Node-ID": config.NODE_ID,
            "X-Event": event,
            "X-Timestamp": utc_now(),
            "X-Request-ID": event_id
        }


        files = {
            "image": (
                f"{event_id}.jpg",
                image_bytes,
                "image/jpeg"
            )
        }


        for attempt in range(
            1,
            config.HTTP_RETRIES + 1
        ):

            start = time.perf_counter()


            try:

                response = self.session.post(
                    config.IMAGE_ENDPOINT,
                    headers=headers,
                    files=files,
                    timeout=config.HTTP_TIMEOUT
                )


                elapsed = (
                    time.perf_counter() - start
                ) * 1000


                if response.ok:

                    logger.success(
                        f"[{event_id}] "
                        f"Imagen enviada correctamente | "
                        f"HTTP {response.status_code} | "
                        f"{elapsed:.2f} ms"
                    )

                    return response.json()


                logger.warning(
                    f"[{event_id}] "
                    f"Respuesta inválida del servidor "
                    f"HTTP {response.status_code}: "
                    f"{response.text}"
                )


            except requests.Timeout:

                logger.error(
                    f"[{event_id}] "
                    f"Timeout en intento "
                    f"{attempt}/{config.HTTP_RETRIES}"
                )


            except requests.ConnectionError as e:

                logger.error(
                    f"[{event_id}] "
                    f"Error de conexión: {e}"
                )


            except requests.RequestException as e:

                logger.exception(
                    f"[{event_id}] "
                    f"Error HTTP inesperado: {e}"
                )


        logger.error(
            f"[{event_id}] "
            "No fue posible enviar la imagen "
            "después de todos los reintentos"
        )

        return None


    def close(self):
        """
        Cierra la sesión HTTP.
        """

        self.session.close()

        logger.info(
            "HTTP Session cerrada"
        )
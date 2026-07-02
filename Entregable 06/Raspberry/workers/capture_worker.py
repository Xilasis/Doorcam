"""
capture_worker.py

Worker responsable de procesar eventos de captura.
"""

import time
from queue import Empty

from utils.logger import get_logger
from utils.helpers import (
    generate_event_id,
    bytes_to_kb
)


logger = get_logger()


class CaptureWorker:


    def __init__(
        self,
        event_queue,
        camera,
        uploader
    ):

        self.queue = event_queue
        self.camera = camera
        self.uploader = uploader
        self.running = True


    def process_event(self, event):
        """
        Procesa un evento de captura.
        """

        event_id = event.get(
            "event_id",
            generate_event_id()
        )


        event_type = event.get(
            "type",
            "UNKNOWN"
        )


        logger.info(
            f"[{event_id}] "
            f"Procesando evento {event_type}"
        )


        try:

            # ------------------------------
            # Captura
            # ------------------------------

            capture_start = time.perf_counter()


            image_bytes = self.camera.capture()


            capture_time = (
                time.perf_counter() -
                capture_start
            ) * 1000


            if not image_bytes:

                logger.error(
                    f"[{event_id}] "
                    "La cámara retornó una imagen vacía"
                )

                return


            logger.info(
                f"[{event_id}] "
                f"Captura OK | "
                f"{bytes_to_kb(len(image_bytes))} KB | "
                f"{capture_time:.2f} ms"
            )


            # ------------------------------
            # Envío HTTP
            # ------------------------------

            response = self.uploader.send_image(
                image_bytes=image_bytes,
                event=event_type.lower(),
                event_id=event_id
            )


            if response:

                logger.success(
                    f"[{event_id}] "
                    "Pipeline completado correctamente"
                )

            else:

                logger.warning(
                    f"[{event_id}] "
                    "Evento no entregado al servidor"
                )

                # FUTURO:
                # storage_service.save(event, image_bytes)


        except Exception as e:

            logger.exception(
                f"[{event_id}] "
                f"Error en pipeline de captura: {e}"
            )


    def run(self):
        """
        Bucle principal del worker.
        """

        logger.success(
            "CaptureWorker iniciado. Esperando eventos..."
        )


        while self.running:

            try:

                event = self.queue.get(
                    timeout=1
                )


                self.process_event(event)


                self.queue.task_done()


            except Empty:
                continue


            except Exception as e:

                logger.exception(
                    f"Error en el loop del CaptureWorker: {e}"
                )

                time.sleep(1)


        logger.warning(
            "CaptureWorker detenido"
        )


    def stop(self):
        """
        Solicita detener el worker.
        """

        self.running = False

        logger.info(
            "Deteniendo CaptureWorker..."
        )
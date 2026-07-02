"""
telegram_client.py

Cliente de comunicación con Telegram Bot API.
Centraliza el envío de mensajes e imágenes.
"""

import requests

from config.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)

from utils.logger import get_logger
class TelegramClient:


    def __init__(self):

        self.logger = get_logger()

        self.base_url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_BOT_TOKEN}"
        )


        self.chat_id = TELEGRAM_CHAT_ID


        self.session = requests.Session()


        self.timeout = 10


        self.logger.info(
            "TelegramClient inicializado"
        )


    # =====================================
    # Enviar mensaje de texto
    # =====================================

    def send_alert(self, message):

        url = (
            f"{self.base_url}/sendMessage"
        )


        payload = {
            "chat_id": self.chat_id,
            "text": message
        }


        response = self.session.post(
            url,
            data=payload,
            timeout=self.timeout
        )


        response.raise_for_status()


        self.logger.info(
            "Mensaje enviado a Telegram"
        )
    #====================================
    # Enviar mensaje de texto con ID dinamico
    #====================================
    def send_message(self, chat_id, message):

        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message
        }

        response = self.session.post(
            url,
            data=payload,
            timeout=self.timeout
        )

        response.raise_for_status()

        self.logger.info(
            f"Mensaje enviado a chat {chat_id}"
        )

    # =====================================
    # Enviar imagen JPEG
    # =====================================

    def send_photo(self, chat_id, image_bytes, caption=None):

        url = f"{self.base_url}/sendPhoto"

        files = {
            "photo": (
                "capture.jpg",
                image_bytes,
                "image/jpeg"
            )
        }

        data = {
            "chat_id": chat_id,
            "caption": caption
        }

        response = self.session.post(
            url,
            data=data,
            files=files,
            timeout=self.timeout
        )

        response.raise_for_status()

        self.logger.info(
            f"Foto enviada a chat {chat_id}"
        )
    #============================================
    # Enviar imagen automáticamente al chat configurado en TELEGRAM_CHAT_ID
    #============================================
    def send_alert_photo(self, image_bytes, caption=None):

        self.send_photo(
            self.chat_id,
            image_bytes,
            caption
        )

    # =====================================
    # Liberar recursos
    # =====================================

    def close(self):

        self.session.close()


        self.logger.info(
            "TelegramClient cerrado"
        )
"""
poll_telegram.py

Long Polling con Telegram Cloud.

Responsabilidad:
- Leer mensajes del bot.
- Filtrar comandos.
- Reenviar comandos al Flask Gateway.

No ejecuta lógica IoT.
"""

import time
import requests
from loguru import logger

from config.config import (
    TELEGRAM_BOT_TOKEN,
    LONG_POLLING_INTERVAL,
    HOST,
    PORT,
    TOKENS
)


# ==================================================
# Configuración
# ==================================================

TELEGRAM_URL = (
    f"https://api.telegram.org/bot"
    f"{TELEGRAM_BOT_TOKEN}/getUpdates"
)


FLASK_COMMAND_ENDPOINT = (
    f"http://{HOST}:{PORT}/telegram"
)


FLASK_HEADERS = {
    "Authorization":
        f"Bearer {TOKENS['telegram']}",

    "X-Client-ID":
        "telegram-poller",

    "Content-Type":
        "application/json"
}


# ==================================================
# Polling principal
# ==================================================

def poll_telegram_updates():

    logger.info(
        "Telegram Long Polling iniciado"
    )


    last_update_id = None


    while True:

        try:

            params = {
                "timeout": LONG_POLLING_INTERVAL
            }


            if last_update_id:
                params["offset"] = (
                    last_update_id + 1
                )


            response = requests.get(
                TELEGRAM_URL,
                params=params,
                timeout=LONG_POLLING_INTERVAL + 5
            )


            response.raise_for_status()


            updates = response.json().get(
                "result",
                []
            )


            for update in updates:


                last_update_id = update["update_id"]


                message = (
                    update.get("message")
                    or update.get("edited_message")
                )


                if not message:
                    continue


                text = message.get(
                    "text",
                    ""
                ).strip()


                # Solo comandos
                if not text.startswith("/"):
                    continue


                payload = {

                    "command": text,

                    "chat_id":
                        message["chat"]["id"],

                    "user": {
                        "id":
                        message["from"]["id"],

                        "username":
                        message["from"].get(
                            "username"
                        )
                    }
                }


                logger.info(
                    f"Comando Telegram recibido: "
                    f"{text}"
                )


                try:

                    result = requests.post(
                        FLASK_COMMAND_ENDPOINT,
                        json=payload,
                        headers=FLASK_HEADERS,
                        timeout=10
                    )


                    result.raise_for_status()


                    logger.info(
                        "Comando entregado al Flask Gateway"
                    )


                except requests.RequestException as e:

                    logger.error(
                        f"Error enviando comando a Flask: {e}"
                    )


        except requests.ReadTimeout:

            # Timeout esperado del long polling
            continue


        except requests.RequestException as e:

            logger.error(
                f"Error de conexión Telegram: {e}"
            )

            time.sleep(5)


        except Exception as e:

            logger.exception(
                f"Fallo inesperado en polling: {e}"
            )

            time.sleep(5)
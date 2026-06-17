"""
utils/poll_telegram.py
--------------------------------------------------------
Módulo encargado de mantener Long Polling con Telegram Cloud.
Filtra únicamente los comandos válidos (que comienzan con './')
y los reenvía al servidor Flask para ser procesados.

Autor: Ronald & GPT-5
Última actualización: Noviembre 2025
"""

import time
import requests
from loguru import logger
from config import (
    TELEGRAM_BOT_TOKEN,
    LONG_POLLING_INTERVAL,
    HOST,
    PORT,
    TOKENS,
)

# ============================================================
# CONFIGURACIÓN BÁSICA
# ============================================================
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
FLASK_ENDPOINT = f"http://{HOST}:{PORT}/telegram"

# Headers SOLO para Flask interno (no para Telegram)
print("cambio de headfers............")
HEADERS_FLASK = {
    "X-API-KEY": TOKENS["telegram"],
    "Content-Type": "application/json"
}

# ============================================================
# FUNCIÓN PRINCIPAL DE POLLING
# ============================================================
def poll_telegram_updates():
    """
    Escucha constantemente los mensajes enviados al bot de Telegram
    mediante long polling (timeout=30s). Filtra comandos válidos que
    empiecen con './' y los reenvía al servidor Flask para ejecución.
    """

    logger.info("📡 Iniciando Long Polling de Telegram...")
    last_update_id = None

    while True:
        try:
            # Parámetros del long polling (sin headers)
            params = {
                "timeout": LONG_POLLING_INTERVAL,
                "offset": last_update_id + 1 if last_update_id else None,
            }

            # IMPORTANTE: no enviar headers aquí → 401 si se incluye "Authorization"
            response = requests.get(
                TELEGRAM_API_URL,
                params=params,
                timeout=LONG_POLLING_INTERVAL + 5,
            )

            if response.status_code != 200:
                logger.warning(f"⚠️ Error al consultar Telegram: {response.status_code}")
                time.sleep(5)
                continue

            data = response.json()

            # Si hay nuevos mensajes
            if "result" in data and data["result"]:
                for update in data["result"]:
                    last_update_id = update["update_id"]

                    message = update.get("message") or update.get("edited_message")
                    if not message:
                        continue

                    text = message.get("text", "").strip()
                    if not text.startswith("/"):
                        # Ignora mensajes no comando
                        continue

                    chat_id = message["chat"]["id"]
                    logger.info(f"📨 Comando recibido desde Telegram: {text} (chat_id={chat_id})")

                    # Reenviar comando al endpoint Flask interno
                    payload = {"cmd": text}
                    try:
                        res = requests.post(
                            FLASK_ENDPOINT,
                            json=payload,
                            headers=HEADERS_FLASK,
                            timeout=20,
                        )
                        if res.status_code == 200:
                            logger.info("✅ Comando reenviado correctamente al servidor Flask.")
                        else:
                            logger.warning(f"⚠️ Error al reenviar comando: {res.status_code}")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ Fallo al enviar comando al servidor Flask: {e}")

        except requests.exceptions.ReadTimeout:
            # Timeout normal de long polling → repetir
            continue
        except Exception as e:
            logger.error(f"❌ Error inesperado en Long Polling: {e}")
            time.sleep(5)

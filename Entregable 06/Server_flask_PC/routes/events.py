"""
events.py

Endpoint unificado para recepción de eventos desde nodos IoT.

Flujo:

RPi Zero
    ↓
Flask
    ↓
Telegram
"""

import time
from flask import Blueprint, request, jsonify

from utils.logger import get_logger

from utils.security import (
    require_node_auth,
    current_node
)

from services.instances import telegram_client


logger = get_logger()


events_bp = Blueprint(
    "events",
    __name__,
    url_prefix="/api/v1/events"
)


@events_bp.route(
    "/image",
    methods=["POST"]
)
@require_node_auth
def receive_image():
    """
    Recepción de imágenes desde nodos IoT.
    """

    start_time = time.perf_counter()

    # ===============================
    # Nodo autenticado
    # ===============================

    node = current_node()
    node_id = node["id"]

    # ===============================
    # Headers
    # ===============================

    event_type = request.headers.get(
        "X-Event",
        "unknown"
    )

    request_id = request.headers.get(
        "X-Request-ID",
        "unknown"
    )

    logger.info(
        f"[{request_id}] Evento recibido | "
        f"Node={node_id} | "
        f"Event={event_type}"
    )

    # ===============================
    # Validar imagen
    # ===============================

    file = request.files.get("image")

    if file is None:
        return jsonify({
            "status": "error",
            "message": "Image not found"
        }), 400

    image_bytes = file.read()

    if len(image_bytes) == 0:
        return jsonify({
            "status": "error",
            "message": "Empty image"
        }), 400

    logger.info(
        f"[{request_id}] Imagen recibida "
        f"{len(image_bytes)/1024:.2f} KB"
    )

    # ===============================
    # Enviar directamente a Telegram
    # ===============================

    caption = (
        "🚨 Movimiento detectado\n\n"
        f"📍 Nodo: {node_id}\n"
        f"📌 Evento: {event_type}"
    )

    try:
        telegram_client.send_alert_photo(
            image_bytes=image_bytes,
            caption=caption
        )

    except Exception as e:

        logger.exception(
            f"[{request_id}] Error enviando a Telegram: {e}"
        )

        return jsonify({
            "status": "error",
            "message": "Telegram send failed",
            "detail": str(e)
        }), 500

    # ===============================
    # Tiempo de ejecución
    # ===============================

    elapsed_ms = (
        time.perf_counter() - start_time
    ) * 1000

    logger.info(
        f"[{request_id}] Evento procesado "
        f"en {elapsed_ms:.2f} ms"
    )

    # ===============================
    # Respuesta al nodo
    # ===============================

    return jsonify({
        "status": "success",
        "node": node_id,
        "event": event_type,
        "time_ms": round(elapsed_ms, 2)
    }), 200
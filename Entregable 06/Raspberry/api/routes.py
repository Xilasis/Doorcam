"""
routes.py

API HTTP local del nodo Raspberry Pi Zero 2W.

Permite:
- Captura remota de imágenes.
- Consulta del estado del nodo.
- Diagnósticos de red.
- Futuro control remoto.
"""

from flask import Flask, jsonify, request, Response
from loguru import logger
from datetime import datetime
import config
from utils.security import require_auth


# ==========================================================
# Instancia Flask
# ==========================================================

app = Flask(__name__)


# ==========================================================
# Referencias a servicios
# Se inicializan desde main.py
# ==========================================================

camera_service = None
network_service = None


# ==========================================================
# Inicialización
# ==========================================================

def init_services(camera, network):
    """
    Inyecta los servicios del nodo.
    """

    global camera_service
    global network_service

    camera_service = camera
    network_service = network


# ==========================================================
# Endpoint: Estado general
# ==========================================================

@app.route("/status", methods=["GET"])
@require_auth
def status():
    """
    Estado básico del nodo.
    """

    data = {
        "node_id": config.NODE_ID,
        "name": config.APP_NAME,
        "version": config.VERSION,
        "status": "ONLINE",
        "time": datetime.now().isoformat()
    }

    return jsonify(data), 200


# ==========================================================
# Endpoint: Información de red
# ==========================================================

@app.route("/network", methods=["GET"])
@require_auth
def network():
    """
    Retorna métricas de red y salud.
    """

    if not network_service:
        return jsonify({
            "error": "Network service not initialized"
        }), 500


    data = network_service.health_check()

    return jsonify(data), 200


# ==========================================================
# Endpoint: Información de IP local
# ==========================================================

@app.route("/network/ip", methods=["GET"])
@require_auth
def network_ip():
    """
    Retorna el hostname e IP local del nodo.
    """

    if not network_service:
        return jsonify({
            "error": "Network service not initialized"
        }), 500


    data = network_service.get_ip_info()

    return jsonify(data), 200


# ==========================================================
# Endpoint: Captura manual
# =========================================================

@app.route("/capture", methods=["GET"])
@require_auth
def capture():
    """
    Captura una imagen directamente desde la cámara.
    """

    if not camera_service:
        return jsonify({
            "error": "Camera service not initialized"
        }), 500


    try:

        image = camera_service.capture()


        return Response(
            image,
            mimetype="image/jpeg",
            headers={
                "Content-Disposition":
                "inline; filename=capture.jpg"
            }
        )

    except Exception as e:

        logger.exception(
            f"Error capturando imagen: {e}"
        )

        return jsonify({
            "error": "capture failed"
        }), 500


# ==========================================================
# Endpoint: Control futuro
# ==========================================================

@app.route("/control", methods=["POST"])
@require_auth
def control():
    """
    Placeholder para comandos remotos futuros.
    """

    data = request.get_json() or {}

    command = data.get("command")


    logger.info(
        f"Comando recibido: {command}"
    )


    return jsonify({
        "message":
        "Control endpoint reservado",
        "command":
        command
    })


# ==========================================================
# Inicio del servidor API
# ==========================================================

def start_api(camera, network):
    """
    Inicia la API HTTP local.
    """

    init_services(camera, network)


    logger.success(
        f"API nodo iniciada en "
        f"http://{config.LOCAL_API_HOST}:"
        f"{config.LOCAL_API_PORT}"
    )


    app.run(
        host=config.LOCAL_API_HOST,
        port=config.LOCAL_API_PORT,
        debug=False,
        threaded=True,
        use_reloader=False
    )

"""
Command Router del Gateway IoT.
"""

from flask import Blueprint, request, jsonify

from config.nodes import NODES

from services.instances import (
    node_client,
    telegram_client
)

from utils.logger import get_logger


logger = get_logger()


telegram_bp = Blueprint(
    "telegram",
    __name__
)


# ======================================
# Helpers
# ======================================

def parse_command(text):
    """
    Divide el comando recibido desde Telegram.
    """

    parts = text.strip().split()

    return (
        parts[0].lower(),
        parts[1:]
    )


def validate_node(node_id):
    """
    Valida que el nodo exista.
    """

    if node_id not in NODES:
        raise ValueError(
            f"Nodo no registrado: {node_id}"
        )


def require_args(args, minimum, usage):
    """
    Verifica cantidad mínima de argumentos.
    """

    if len(args) < minimum:
        raise ValueError(
            f"Uso correcto: {usage}"
        )


# ======================================
# Sistema de ayuda
# ======================================

def get_node_help(node_id):
    """
    Genera ayuda dinámica por nodo.
    """

    node = NODES[node_id]

    caps = node["capabilities"]


    msg = (
        f"📡 {node_id}\n"
        f"{node['name']}\n\n"
    )


    # Estado

    if caps.get("status"):
        msg += (
            f"/status {node_id}\n"
        )


    # Red

    if caps.get("network"):
        msg += (
            f"/network {node_id}\n"
        )


    # Capturas

    captures = caps.get(
        "captures",
        []
    )


    if "photo" in captures:

        msg += (
            f"/foto {node_id}\n"
        )


    if "photo_with_flash" in captures:

        msg += (
            f"/foto_flash {node_id}\n"
        )


    # Controles

    for control in caps.get(
        "controls",
        []
    ):

        msg += (
            f"/control {node_id} {control}\n"
        )


    return msg


def general_help():
    """
    Ayuda general del Gateway.
    """

    return (
        "🤖 IoT Gateway\n\n"
        "Comandos disponibles:\n"
        "/nodes\n"
        "/help <node_id>\n"
    )


# ======================================
# Endpoint Telegram
# ======================================


@telegram_bp.route(
    "/telegram",
    methods=["POST"]
)
def telegram_router():

    data = request.get_json() or {}


    chat_id = data.get(
        "chat_id"
    )


    command_text = data.get(
        "command"
    )


    if not chat_id or not command_text:

        return jsonify(
            {
                "error": "Invalid request"
            }
        ), 400


    try:

        command, args = parse_command(
            command_text
        )


        # ------------------------------
        # Listar nodos
        # ------------------------------

        if command == "/nodes":

            msg = "📡 Nodos disponibles\n\n"


            for node_id, node in NODES.items():

                msg += (
                    f"{node_id} - "
                    f"{node['name']}\n"
                )


            telegram_client.send_message(
                chat_id,
                msg
            )


        # ------------------------------
        # Ayuda
        # ------------------------------

        elif command == "/help":

            if not args:

                telegram_client.send_message(
                    chat_id,
                    general_help()
                )

            else:

                node_id = args[0]

                validate_node(
                    node_id
                )


                telegram_client.send_message(
                    chat_id,
                    get_node_help(
                        node_id
                    )
                )
                # ------------------------------
        # Estado del nodo
        # ------------------------------

        elif command == "/status":

            require_args(
                args,
                1,
                "/status <node_id>"
            )

            node_id = args[0]

            validate_node(
                node_id
            )


            result = node_client.status(
                node_id
            )


            telegram_client.send_message(
                chat_id,
                str(result)
            )


        # ------------------------------
        # Información de red
        # ------------------------------

        elif command == "/network":

            require_args(
                args,
                1,
                "/network <node_id>"
            )

            node_id = args[0]


            validate_node(
                node_id
            )


            result = node_client.network(
                node_id
            )


            telegram_client.send_message(
                chat_id,
                str(result)
            )


        # ------------------------------
        # Captura normal
        #
        # ESP32:
        # GET /capture
        #
        # Respuesta:
        # image/jpeg
        # ------------------------------

        elif command == "/foto":

            require_args(
                args,
                1,
                "/foto <node_id>"
            )


            node_id = args[0]


            validate_node(
                node_id
            )


            image = node_client.capture(
                node_id
            )


            telegram_client.send_photo(
                chat_id,
                image,
                f"📷 Captura {node_id}"
            )


        # ------------------------------
        # Captura con flash
        #
        # ESP32:
        # GET /capture_flash
        #
        # Respuesta:
        # image/jpeg
        # ------------------------------

        elif command == "/foto_flash":

            require_args(
                args,
                1,
                "/foto_flash <node_id>"
            )


            node_id = args[0]


            validate_node(
                node_id
            )


            image = node_client.capture_flash(
                node_id
            )


            telegram_client.send_photo(
                chat_id,
                image,
                f"📸 Captura con flash {node_id}"
            )


        # ------------------------------
        # Control del dispositivo
        #
        # ESP32:
        # POST /control
        #
        # Respuesta:
        # JSON
        # ------------------------------

        elif command == "/control":

            require_args(
                args,
                2,
                "/control <node_id> <accion>"
            )


            node_id = args[0]


            action = args[1]


            validate_node(
                node_id
            )


            controls = (
                NODES[node_id]
                ["capabilities"]
                .get(
                    "controls",
                    []
                )
            )


            if action not in controls:

                raise ValueError(
                    f"Control no soportado: {action}"
                )


            result = node_client.control(
                node_id,
                action
            )


            telegram_client.send_message(
                chat_id,
                str(result)
            )


        # ------------------------------
        # Comando desconocido
        # ------------------------------

        else:

            telegram_client.send_message(
                chat_id,
                "❌ Comando no válido.\n"
                "Use /help para ver opciones."
            )


        # Respuesta al servicio interno
        return jsonify(
            {
                "status": "ok"
            }
        )


    # ==================================
    # Manejo centralizado de errores
    # ==================================

    except Exception as e:

        logger.exception(
            e
        )


        try:

            telegram_client.send_message(
                chat_id,
                f"❌ Error:\n{str(e)}"
            )

        except Exception:

            logger.error(
                "No se pudo enviar mensaje de error a Telegram"
            )


        return jsonify(
            {
                "error": str(e)
            }
        ), 400

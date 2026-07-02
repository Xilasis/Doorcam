"""
security.py

Sistema de autenticación y autorización para nodos IoT.

Flujo:

Nodo IoT
    |
    | Authorization: Bearer TOKEN
    | X-Node-ID: rpi-01
    |
    v
Flask Gateway
    |
    v
security.verify_node_request()
    |
    +--> Consulta registry NODES
    |
    +--> Valida token
    |
    v
Nodo autenticado
"""

from functools import wraps

from flask import request, jsonify, g

from config.nodes import NODES


# ==========================================================
# Validación de nodo
# ==========================================================

def verify_node_request():
    """
    Valida la autenticación de un nodo IoT.

    Retorna:
        dict: Información del nodo autenticado.

    Lanza:
        ValueError: cuando la validación falla.
    """

    # ------------------------------
    # Obtener Node ID
    # ------------------------------

    node_id = request.headers.get(
        "X-Node-ID"
    )


    if not node_id:
        raise ValueError(
            "Missing X-Node-ID header"
        )


    # ------------------------------
    # Verificar nodo registrado
    # ------------------------------

    node = NODES.get(node_id)


    if not node:
        raise ValueError(
            f"Unknown node: {node_id}"
        )


    # ------------------------------
    # Obtener token
    # ------------------------------

    auth_header = request.headers.get(
        "Authorization",
        ""
    )


    if not auth_header.startswith(
        "Bearer "
    ):
        raise ValueError(
            "Missing Bearer token"
        )


    token = auth_header.replace(
        "Bearer ",
        "",
        1
    )


    # ------------------------------
    # Comparar token
    # ------------------------------

    if token != node["token"]:
        raise ValueError(
            "Invalid authentication token"
        )


    # Guardar información en contexto Flask
    g.node = {
        "id": node_id,
        **node
    }


    return g.node


# ==========================================================
# Decorador de protección
# ==========================================================

def require_node_auth(endpoint):
    """
    Protege endpoints utilizados por nodos IoT.

    Ejemplo:

        @app.route("/api/v1/events/image")
        @require_node_auth
        def receive_image():
            ...
    """

    @wraps(endpoint)
    def wrapper(*args, **kwargs):

        try:

            verify_node_request()

            return endpoint(
                *args,
                **kwargs
            )


        except ValueError as error:

            return jsonify({
                "status": "error",
                "message": str(error)
            }), 401


        except Exception as error:

            return jsonify({
                "status": "error",
                "message": (
                    "Authentication failure"
                ),
                "detail": str(error)
            }), 500


    return wrapper


# ==========================================================
# Utilidad para obtener nodo actual
# ==========================================================

def current_node():
    """
    Retorna información del nodo autenticado.

    Uso:

        node = current_node()
        node_id = node["id"]
        node_type = node["type"]
    """

    return getattr(
        g,
        "node",
        None
    )
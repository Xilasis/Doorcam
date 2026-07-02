"""
security.py

Funciones de autenticación para API local del nodo.
"""

from flask import request, jsonify
from functools import wraps

import config


def verify_token(token: str) -> bool:
    """
    Verifica el token recibido.
    """

    return token == config.TOKEN


def verify_node(node_id: str) -> bool:
    """
    Verifica que el comando sea para este nodo.
    """

    return node_id == config.NODE_ID


def require_auth(func):
    """
    Decorador para proteger endpoints Flask.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        auth = request.headers.get(
            "Authorization",
            ""
        )

        node_id = request.headers.get(
            "X-Node-ID",
            ""
        )


        if not auth.startswith(
            "Bearer "
        ):
            return jsonify({
                "error": "Missing Bearer token"
            }), 401


        token = auth.split(
            "Bearer "
        )[1]


        if not verify_token(token):
            return jsonify({
                "error": "Invalid token"
            }), 403


        if not verify_node(node_id):
            return jsonify({
                "error": "Invalid node ID"
            }), 403


        return func(
            *args,
            **kwargs
        )


    return wrapper
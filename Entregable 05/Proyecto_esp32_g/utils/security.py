from flask import request, jsonify
from config import TOKENS

def verificar_token(origen):
    """
    Verifica el token enviado en los headers.
    Retorna un JSON de error si no es válido.
    """
    # 🔹 DEBUG: ver headers recibidos
    print("Headers recibidos:", dict(request.headers))

    # Primero intenta X-API-KEY
    token = request.headers.get("X-API-KEY")

    # Si no existe, intenta Authorization: Bearer ...
    if not token and request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    print("Token recibido:", token)

    if token != TOKENS.get(origen):
        return jsonify({"error": f"Acceso no autorizado para {origen}."}), 403

    return None

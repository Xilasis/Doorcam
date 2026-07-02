"""
helpers.py

Funciones comunes del nodo IoT.
"""

from datetime import datetime, timezone
import uuid


def utc_now():
    """
    Retorna fecha actual en UTC ISO 8601.
    """

    return (
        datetime.now(timezone.utc)
        .isoformat()
    )


def generate_event_id():
    """
    Genera un identificador único para eventos.
    """

    return str(
        uuid.uuid4()
    )


def bytes_to_kb(size_bytes):
    """
    Convierte bytes a kilobytes.
    """

    return round(
        size_bytes / 1024,
        2
    )


def bytes_to_mb(size_bytes): #aun no se usa, pero es probable que se necesite para métricas de red
    """
    Convierte bytes a megabytes.
    """

    return round(
        size_bytes / (1024 * 1024),
        2
    )
"""
config.py
Configuración central del nodo Raspberry Pi Zero 2W
"""

from pathlib import Path


# ==========================================================
# IDENTIDAD DEL NODO
# ==========================================================

NODE_ID = "rpi-01"


# ==========================================================
# SEGURIDAD
# ==========================================================

TOKEN = "TOKEN_RPI"


# ==========================================================
# SERVIDOR FLASK CENTRAL
# ==========================================================

SERVER_IP = "192.168.0.10"
SERVER_PORT = 8080

BASE_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# Endpoint actual compatible con Flask existente
IMAGE_ENDPOINT = f"{BASE_URL}/api/v1/events/image"

# Futuro endpoint recomendado
# IMAGE_ENDPOINT = f"{BASE_URL}/api/v1/events/image"


# ==========================================================
# PIR SENSOR
# ==========================================================

PIR_GPIO = 23

# Evita múltiples disparos consecutivos
PIR_COOLDOWN = 5  # segundos

# ==========================================================
# CÁMARA CSI - Picamera2
# ==========================================================

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

JPEG_QUALITY = 85

CAMERA_WARMUP = 2


# ==========================================================
# HTTP CLIENT
# ==========================================================

HTTP_TIMEOUT = 5

HTTP_RETRIES = 3


# ==========================================================
# DIAGNÓSTICO DE RED
# ==========================================================

PING_TARGET = SERVER_IP

PING_COUNT = 5


# ==========================================================
# RUTAS DEL SISTEMA
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "node.log"


# ==========================================================
# API LOCAL DEL NODO
# ==========================================================

LOCAL_API_HOST = "0.0.0.0"

LOCAL_API_PORT = 5001


# ==========================================================
# INFORMACIÓN DEL SISTEMA
# ==========================================================

APP_NAME = "RPi Zero 2W Security Node"

VERSION = "1.0.0"

# utils/esp32_client.py
# ------------------------------------------------------------
# Este módulo permite la comunicación desde el servidor Flask
# hacia el dispositivo ESP32-CAM. Se encarga de:
#   - Reenviar comandos (por ejemplo: /status, /flash_on, etc.)
#   - Solicitar imágenes para su análisis por IA
# ------------------------------------------------------------

import requests       # Librería para realizar solicitudes HTTP
import logging        # Permite mostrar mensajes de diagnóstico
from config import ESP32_URL, ESP32_TOKEN  # Configuración global del proyecto


# ------------------------------------------------------------
# Configuración de logs
# ------------------------------------------------------------
# Los logs sirven para monitorear lo que ocurre internamente
# y detectar errores sin detener el programa.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ESP32_CLIENT")  # Crea un canal de registro


# ------------------------------------------------------------
# FUNCIÓN 1: reenviar_comando_esp32
# ------------------------------------------------------------
def reenviar_comando_esp32(comando: str):
    """
    Envía un comando al ESP32 mediante POST.
    El token ahora se envía en la cabecera 'Authorization: Bearer <token>'.
    """
    url = f"{ESP32_URL}/command"
    headers = {"Authorization": f"Bearer {ESP32_TOKEN}"}
    payload = {"cmd": comando}

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Comando '{comando}' reenviado correctamente: {data}")
        return data.get("ok", "Comando ejecutado correctamente.")
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout al contactar con el ESP32.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al reenviar comando '{comando}': {e}")
        return None


# ------------------------------------------------------------
# FUNCIÓN 2: solicitar_captura_esp32
# ------------------------------------------------------------
def solicitar_captura_esp32(comando_especial=None):
    """
    Solicita una fotografía al ESP32-CAM mediante HTTP.
    Soporte para captura normal y foto con flash.
    
    Args:
        comando_especial: None para captura normal, "photo_with_flash" para foto con flash
    
    Devuelve una tupla (éxito: bool, imagen_bytes: bytes | None)
    """

    try:
        if comando_especial == "photo_with_flash":
            # 📸 MODO FOTO CON FLASH - Usa endpoint /command
            url = f"{ESP32_URL}/command"
            headers = {"Authorization": f"Bearer {ESP32_TOKEN}"}
            payload = {"cmd": "photo_with_flash"}
            
            logger.info("📸➕💡 Solicitando foto CON FLASH al ESP32...")
            response = requests.post(url, headers=headers, data=payload, timeout=20) #data
            
        else:
            # 📷 MODO CAPTURA NORMAL - Usa endpoint /capture
            url = f"{ESP32_URL}/capture"
            headers = {"Authorization": f"Bearer {ESP32_TOKEN}"}
            logger.info("📸 Solicitando captura normal al ESP32...")
            response = requests.get(url, headers=headers, timeout=20)

        # Si el servidor responde con código de error, lanza excepción.
        response.raise_for_status()

        # Verificamos que la respuesta sea una imagen JPEG
        content_type = response.headers.get("Content-Type", "").lower()
        
        if "image/jpeg" in content_type or "jpeg" in content_type:
            if comando_especial == "photo_with_flash":
                logger.info("✅ Imagen CON FLASH recibida correctamente desde ESP32.")
            else:
                logger.info("✅ Imagen recibida correctamente desde ESP32.")
            
            # Retorna True (éxito) y los bytes crudos de la imagen
            return True, response.content
        
        else:
            # Si el servidor respondió algo que no es una imagen
            logger.warning(f"⚠️ La respuesta del ESP32 no contenía una imagen. Content-Type: {content_type}")
            
            # Log adicional para debugging
            if response.text:
                logger.debug(f"Respuesta del ESP32: {response.text[:200]}...")
                
            return False, None

    # Si se supera el tiempo de espera
    except requests.exceptions.Timeout:
        if comando_especial == "photo_with_flash":
            logger.error("⏰ Tiempo de espera agotado durante la solicitud de foto CON FLASH.")
        else:
            logger.error("⏰ Tiempo de espera agotado durante la solicitud de imagen.")
        return False, None

    # Otros errores de conexión o HTTP
    except requests.exceptions.RequestException as e:
        if comando_especial == "photo_with_flash":
            logger.error(f"❌ Error al solicitar foto CON FLASH al ESP32: {e}")
        else:
            logger.error(f"❌ Error al solicitar imagen al ESP32: {e}")
        return False, None
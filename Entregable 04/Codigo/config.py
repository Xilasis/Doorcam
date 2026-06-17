"""
app.py — Servidor Flask para IA con ESP32 y Telegram
-----------------------------------------------------
Fases cubiertas:
1️⃣ Configuración modular y carga segura del modelo.
2️⃣ Token de autenticación por cliente (ESP32 / Telegram).
3️⃣ Procesamiento de imágenes y predicciones.
4️⃣ Endpoints organizados y listos para integrar IoT + Bot.
"""

from flask import Flask, request, jsonify
from loguru import logger
from config import HOST, PORT, DEBUG, CLASS_NAMES
from utils.security import verificar_token
from utils.image_utils import preparar_imagen
from utils.send_telegram import enviar_alerta_telegram
from model_loader import cargar_modelo
import numpy as np
from utils.image_pipeline import procesar_enviar
from utils.esp32_client import reenviar_comando_esp32, solicitar_captura_esp32
from utils.poll_telegram  import poll_telegram_updates
import threading

# ============================================================
# CONFIGURACIÓN INICIAL
# ============================================================
app = Flask(__name__)

# Cargar modelo IA (TensorFlow o Edge Impulse)
model = cargar_modelo()

# ============================================================
# ENDPOINT PRINCIPAL DE ESTADO
# ============================================================
@app.route("/", methods=["GET"])
def home():
    """Verifica que el servidor esté operativo"""
    return jsonify({"status": "Servidor Flask funcionando correctamente."})


# ============================================================
# ENDPOINT DE PREDICCIÓN (usado por ESP32-CAM)
# ============================================================
@app.route("/predict", methods=["POST"])
def predict():
    """
    Recibe imagen desde ESP32-CAM y realiza reconocimiento IA.
    """
    check = verificar_token("esp32")
    if check:
        return check

    if "image" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo con la clave 'image'."}), 400

    file = request.files["image"]
    img_bytes = file.read()

    # Llamamos a la pipeline centralizada
    resultado = procesar_enviar(model, img_bytes, CLASS_NAMES)

    return jsonify(resultado)

# ============================================================
# ENDPOINT PARA TELEGRAM (envío de comandos / consultas)  
# ============================================================
print("🚀 VERSIÓN ACTUAL del endpoint: acepta comandos que inician con '/'")  

@app.route("/telegram", methods=["GET", "POST"])
def telegram_endpoint():
    """
    Endpoint para interacción bilateral con el bot de Telegram.
    GET → comprobar estado del bot.
    POST → recibir comandos con prefijo '/' y redirigir al ESP32 o IA.
    """

    # 1️⃣ Seguridad
    check = verificar_token("telegram")
    if check:
        return check

    # 2️⃣ Estado del bot
    if request.method == "GET":
        return jsonify({"status": "Bot operativo y autenticado."})

    # 3️⃣ Datos entrantes
    data = request.get_json() or {} #Intenta obtener el cuerpo JSON de http como dict
    print("🧾 Datos recibidos:", data)
    print("despues de data")
    comando = data.get("cmd", "").strip().lower() #return valor 

    if not comando.startswith("/"):
        return jsonify({
            "error": "Formato inválido. Use '/comando' para interactuar con el bot."
        }), 400

    comando = comando.split("@")[0].replace("/", "", 1)

     # 4️⃣ Catálogo de comandos (ayuda)
    if comando in ("help", "comandos"):
        mensaje = (
        "🤖 *Lista de comandos disponibles:*\n\n"
        "🧠 `/status` → Muestra el estado de la IA y del ESP32.\n"
        "📸 `/foto` → Captura una imagen del ESP32 y la analiza con IA.\n"
        "✨ `/foto_flash` → Captura una imagen CON FLASH del ESP32.\n"
        "💡 `/flash_on` → Enciende el flash del ESP32.\n"
        "🔌 `/flash_off` → Apaga el flash del ESP32.\n"
        "🚨 `/alert` → Envía una alerta visual (flash/LED) al ESP32.\n"
        "🌐 `/info_conexion` → Muestra información técnica y de red del ESP32.\n"
        "🔄 `/reboot_esp32` → Reinicia remotamente el ESP32.\n"
        "❓ `/help` o `/comandos` → Muestra esta lista de comandos.\n\n"
        "_Formato obligatorio:_ los comandos deben iniciar con `/`."
        )
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": "Lista de comandos enviada a Telegram."})
    print("CAMBIOS---------")
    # 5️⃣ Comandos funcionales
    if comando == "status":
        estado_ia = "✅ IA cargada" if model else "⚠️ IA no disponible"
        estado_esp = reenviar_comando_esp32("status") or "ESP32 sin respuesta"
        mensaje = f"🤖 *Estado del sistema:*\n- {estado_ia}\n- {estado_esp}"
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})

    elif comando == "alert":
        exito = reenviar_comando_esp32("alert")
        mensaje = "🚨 Alerta activada en el ESP32." if exito else "❌ Error al contactar con el ESP32."
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})

    elif comando in ("foto", "capture"):
        exito, img_bytes = solicitar_captura_esp32()
        if not exito or not img_bytes:
            enviar_alerta_telegram(None, "❌ No se obtuvo imagen del ESP32.")
            return jsonify({"error": "No se pudo obtener imagen del ESP32."}), 500

        # Procesamiento IA automático antes de Telegram
        resultado = procesar_enviar(model, img_bytes, CLASS_NAMES)
        return jsonify({"resultado":"Foto procesada y enviada a telegram"})

    elif comando == "info_conexion":
        info = reenviar_comando_esp32("diag")
        mensaje = info if info else "❌ No se pudo obtener información del ESP32."
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})

    elif comando == "reboot_esp32":
        exito = reenviar_comando_esp32("reboot")
        mensaje = "🔄 ESP32 reiniciándose..." if exito else "❌ No se pudo reiniciar el ESP32."
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})
    elif comando in ("foto_flash", "foto_con_flash", "photo_flash"):
        exito, img_bytes = solicitar_captura_esp32(comando_especial="photo_with_flash")
        if not exito or not img_bytes:
            enviar_alerta_telegram(None, "❌ No se obtuvo imagen con flash del ESP32.")
            return jsonify({"error": "No se pudo obtener imagen con flash del ESP32."}), 500
        
        resultado_ia = procesar_enviar(model, img_bytes, CLASS_NAMES)
        return jsonify({"respuesta": "✅ Imagen con flash capturada y analizada", "ia": resultado_ia})
    elif comando == "flash_on":
        exito = reenviar_comando_esp32("flash_on")
        mensaje = "💡 Flash encendido en el ESP32." if exito else "❌ Error al encender flash del ESP32."
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})

    elif comando == "flash_off":
        exito = reenviar_comando_esp32("flash_off")
        mensaje = "🔌 Flash apagado en el ESP32." if exito else "❌ Error al apagar flash del ESP32."
        enviar_alerta_telegram(None, mensaje)
        return jsonify({"respuesta": mensaje})

    else:
        enviar_alerta_telegram(None, f"⚠️ Comando desconocido: '/{comando}'")
        return jsonify({"error": f"Comando '/{comando}' no reconocido."}), 400


# ============================================================
# INICIO DEL SERVIDOR
# ============================================================
if __name__ == "__main__":
    # Ejecutar Flask solo en la interfaz definida en config.py (no 0.0.0.0)
    logger.info(f"🚀 Iniciando servidor IA en http://{HOST}:{PORT}")
     # Iniciar Long Polling de Telegram en hilo separado
    threading.Thread(target=poll_telegram_updates, daemon=True).start()
    # Ejecutar Flask
    app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)
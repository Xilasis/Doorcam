import requests
from config import (
    TELEGRAM_BOT_TOKEN,
    TOKENS,
    TELEGRAM_CHAT_ID
)

def enviar_alerta_telegram(img_bytes=None, mensaje=""):
    """
    Envía contenido al chat de Telegram:
    - Solo texto → si img_bytes es None.
    - Imagen + caption → si img_bytes contiene datos.
    - Imagen + mensaje posterior → si se requiere doble envío (por saltos de línea).
    """
    chat_id = TELEGRAM_CHAT_ID  # ⚠️ Reemplázalo por el ID real
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    if not TELEGRAM_BOT_TOKEN or not chat_id:
        print("⚠️ Error: faltan credenciales de Telegram.")
        return False

    try:
        # 🖼️ Caso 1: enviar imagen (con caption corto)
        if img_bytes:
            url = f"{base_url}/sendPhoto"
            files = {"photo": ("captura.jpg", img_bytes)}

            # Solo la primera línea como caption (límite 1024 chars)
            caption = mensaje.split("\n", 1)[0][:1024].strip()
            data = {"chat_id": chat_id, "caption": caption}

            r = requests.post(url, files=files, data=data, timeout=5)
            r.raise_for_status()

            # Enviar texto adicional si hay más líneas
            if "\n" in mensaje:
                extra_text = mensaje.split("\n", 1)[1].strip()
                if extra_text:
                    requests.post(
                        f"{base_url}/sendMessage",
                        data={"chat_id": chat_id, "text": extra_text},
                        timeout=5
                    )

        # 💬 Caso 2: solo texto
        elif mensaje.strip():
            url = f"{base_url}/sendMessage"
            data = {"chat_id": chat_id, "text": mensaje}
            r = requests.post(url, data=data, timeout=5)
            r.raise_for_status()

        else:
            print("⚠️ No hay contenido para enviar.")
            return False

        return True

    except requests.RequestException as e:
        print(f"⚠️ Error en la conexión o respuesta de Telegram: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Error inesperado: {e}")
        return False


import numpy as np
from .image_utils import preparar_imagen
from .send_telegram import enviar_alerta_telegram

def procesar_enviar(model, img_bytes, class_names):
    """
    Procesa una imagen en bytes, ejecuta el modelo IA y envía el resultado a Telegram.
    Devuelve un dict con resultado y confianza.
    """
    # Preprocesar la imagen
    img_array = preparar_imagen(img_bytes)

    if model is None:
        return {"error": "El modelo no está cargado correctamente."}

    # Predicción IA
    prediction = model.predict(img_array)
    predicted_class = int(np.argmax(prediction, axis=1)[0])
    confidence = float(np.max(prediction))

    # Determinar etiqueta
    label = class_names[predicted_class] if predicted_class < len(class_names) else "Desconocido"

    # Construir mensaje
    mensaje = f"📸 Detección: {label}\nConfianza: {confidence:.2f}"

    # Enviar alerta a Telegram
    enviar_alerta_telegram(img_bytes, mensaje)

    return {
        "status": "ok",
        "prediction": label,
        "confidence": confidence
    }

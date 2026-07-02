import tensorflow as tf
from loguru import logger

MODEL_PATH = "modelo_entrenado.h5"

def cargar_modelo():
    """Carga un modelo .h5 y lo devuelve listo para usar."""
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        logger.success(f"✅ Modelo cargado correctamente desde: {MODEL_PATH}")
        return model
    except Exception as e:
        logger.error(f"❌ Error cargando el modelo: {e}")
        return None

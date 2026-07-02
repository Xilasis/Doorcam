"""
image_pipeline.py

Pipeline puro de inferencia IA.
No contiene lógica de comunicación.
"""

import io
import numpy as np
from PIL import Image


def procesar_enviar(model, image_bytes, class_names):
    """
    Ejecuta inferencia sobre una imagen.

    Args:
        model: Modelo TensorFlow cargado.
        image_bytes: Imagen JPEG en bytes.
        class_names: Lista de etiquetas.

    Returns:
        dict con predicción.
    """

    # -------------------------------------
    # Decodificar imagen
    # -------------------------------------

    image = Image.open(
        io.BytesIO(image_bytes)
    )

    image = image.convert("RGB")


    # -------------------------------------
    # Obtener tamaño de entrada del modelo
    # -------------------------------------

    input_shape = model.input_shape

    height = input_shape[1]
    width = input_shape[2]


    image = image.resize(
        (width, height)
    )


    # -------------------------------------
    # Convertir a numpy
    # -------------------------------------

    array = np.array(
        image,
        dtype=np.float32
    )


    # Normalización estándar
    array = array / 255.0


    # Batch dimension
    array = np.expand_dims(
        array,
        axis=0
    )


    # -------------------------------------
    # Inferencia
    # -------------------------------------

    prediction = model.predict(
        array,
        verbose=0
    )


    index = int(
        np.argmax(prediction)
    )


    confidence = float(
        prediction[0][index]
    )


    label = class_names[index]


    # -------------------------------------
    # Resultado estructurado
    # -------------------------------------

    return {
        "label": label,
        "confidence": round(confidence, 4)
    }
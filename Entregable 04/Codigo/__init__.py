import numpy as np
from PIL import Image
import io

def preparar_imagen(img_bytes, size=(96, 96)):
    """
    Convierte bytes → matriz numpy normalizada lista para el modelo.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize(size)
    img_array = np.array(img) / 255.0
    return np.expand_dims(img_array, axis=0)
 
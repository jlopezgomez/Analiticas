import pytesseract
from PIL import Image
from PIL import ImageEnhance, ImageFilter
import io
import platform


def configurar_tesseract():
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def preprocesar_imagen(imagen: Image.Image) -> Image.Image:
    imagen_gris = imagen.convert("L")
    enhancer_contraste = ImageEnhance.Contrast(imagen_gris)
    imagen_contraste = enhancer_contraste.enhance(2.0)
    enhancer_nitidez = ImageEnhance.Sharpness(imagen_contraste)
    imagen_nitida = enhancer_nitidez.enhance(2.0)
    imagen_final = imagen_nitida.filter(ImageFilter.SHARPEN)
    return imagen_final


def extraer_texto_imagen(imagen_bytes) -> str:
    try:
        configurar_tesseract()
        imagen = Image.open(io.BytesIO(imagen_bytes.getvalue()))
        imagen_procesada = preprocesar_imagen(imagen)
        config_ocr = "--oem 3 --psm 6 -l spa+eng"
        texto = pytesseract.image_to_string(imagen_procesada, config=config_ocr)
        texto = texto.strip()

        if not texto:
            return "Error: No se pudo extraer texto de la imagen. Asegúrate de que la foto esté bien iluminada y enfocada."

        return texto

    except pytesseract.TesseractNotFoundError:
        return (
            "Error: Tesseract no está instalado o no se encuentra en la ruta configurada. "
            "Descárgalo desde: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as e:
        return f"Error al procesar la imagen: {str(e)}"
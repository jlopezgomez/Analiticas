import pytesseract
from PIL import Image
from PIL import ImageEnhance, ImageFilter, ImageOps
import io
import platform
import re


def configurar_tesseract():
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def abrir_imagen(imagen_bytes, giro: int = 0) -> Image.Image:
    """
    Abre la foto derecha: aplica la orientación que guarda el móvil (EXIF) y el giro
    que haya pedido el usuario, en grados en el sentido de las agujas del reloj.
    """
    imagen = Image.open(io.BytesIO(imagen_bytes.getvalue()))
    imagen = ImageOps.exif_transpose(imagen)
    if giro % 360:
        # PIL gira en sentido contrario a las agujas del reloj
        imagen = imagen.rotate(-(giro % 360), expand=True)
    return imagen


def enderezar_automaticamente(imagen: Image.Image) -> Image.Image:
    """
    Detecta con Tesseract (OSD) si el texto está de lado o boca abajo y lo endereza.
    Si no puede detectarlo (poco texto, foto borrosa), devuelve la imagen tal cual.
    """
    try:
        osd = pytesseract.image_to_osd(imagen.convert("L"))
        giro = int(re.search(r"Rotate:\s*(\d+)", osd).group(1))
        confianza = float(re.search(r"Orientation confidence:\s*([\d.]+)", osd).group(1))
        if giro and confianza >= 1.0:
            return imagen.rotate(-giro, expand=True)
    except Exception:
        pass
    return imagen


def preprocesar_imagen(imagen: Image.Image) -> Image.Image:
    imagen_gris = imagen.convert("L")
    enhancer_contraste = ImageEnhance.Contrast(imagen_gris)
    imagen_contraste = enhancer_contraste.enhance(2.0)
    enhancer_nitidez = ImageEnhance.Sharpness(imagen_contraste)
    imagen_nitida = enhancer_nitidez.enhance(2.0)
    imagen_final = imagen_nitida.filter(ImageFilter.SHARPEN)
    return imagen_final


def extraer_texto_imagen(imagen_bytes, giro: int = 0) -> str:
    """
    Lee el texto de una foto: aplica el giro que haya puesto el usuario y luego la endereza
    sola por si sigue de lado (si ya está derecha, el enderezado no la toca).
    """
    try:
        configurar_tesseract()
        imagen = enderezar_automaticamente(abrir_imagen(imagen_bytes, giro))
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
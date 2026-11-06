import base64
import io

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from PIL import Image

from services.ocr_processor import abrir_imagen, enderezar_automaticamente, extraer_texto_imagen

# Lado mayor con el que se envía la foto: suficiente para leer números pequeños sin gastar de más
LADO_MAXIMO = 2000

INSTRUCCIONES_TRANSCRIPCION = """Eres un transcriptor de informes de laboratorio. Te paso la foto de una página de una analítica de sangre.

Copia LITERALMENTE los resultados que se ven en la foto, una prueba por línea, con este formato:
Nombre de la prueba | resultado | unidad | valores de referencia

Reglas:
- Copia los números exactamente como aparecen, con sus comas y decimales, y conserva las marcas del laboratorio (*, H, L).
- No interpretes, no corrijas y no completes nada. No añadas pruebas que no se vean.
- Si un dato no se lee con seguridad, escribe ? en su lugar en vez de adivinarlo.
- Si la prueba no tiene valores de referencia en la foto, deja ese hueco vacío.
- Copia también, al principio, el nombre del paciente y la fecha si aparecen.
- No copies números de identificación (DNI, NHC, NASS, código SNS, nº de muestra, teléfonos, direcciones).
- Si la foto no es una analítica o no se puede leer, responde solo: ILEGIBLE"""


def _imagen_a_data_url(imagen: Image.Image) -> str:
    imagen = imagen.convert("RGB")
    imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    buf = io.BytesIO()
    imagen.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def transcribir_con_ia(imagen: Image.Image) -> str:
    """Pide al modelo de visión que copie literalmente los resultados de la foto."""
    modelo = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    respuesta = modelo.invoke([
        SystemMessage(content=INSTRUCCIONES_TRANSCRIPCION),
        HumanMessage(content=[
            {"type": "text", "text": "Transcribe esta página de la analítica."},
            {"type": "image_url", "image_url": {"url": _imagen_a_data_url(imagen), "detail": "high"}},
        ]),
    ])
    return respuesta.content.strip()


def leer_texto_foto(imagen_bytes, giro: int = 0) -> tuple[str, str]:
    """
    Lee una foto de la analítica. Primero con la IA, que entiende tablas y fotos de móvil;
    si falla (sin conexión, sin clave...), con Tesseract.

    Returns:
        (texto, método): el método es "IA" o "Tesseract". El texto empieza por "Error"
        si no se ha podido leer.
    """
    try:
        imagen = enderezar_automaticamente(abrir_imagen(imagen_bytes, giro))
        texto = transcribir_con_ia(imagen)
        if texto.upper().startswith("ILEGIBLE"):
            return ("Error: La foto no se puede leer. Repítela con más luz, sin reflejos y el texto enfocado.", "IA")
        return texto, "IA"
    except Exception:
        return extraer_texto_imagen(imagen_bytes, giro), "Tesseract"

import base64
import io
import re
from concurrent.futures import ThreadPoolExecutor

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from PIL import Image

from services.ocr_processor import abrir_imagen, enderezar_automaticamente, extraer_texto_imagen

# Modelo que lee las fotos: gpt-4o lee mejor y más rápido las fotos de móvil que gpt-4o-mini
MODELO_VISION = "gpt-4o"
# OpenAI reduce cada imagen hasta que su lado corto mide 768 px: una página entera llega con poco
# detalle y confunde números pequeños (0,12 -> 0,02). Por eso se envía en franjas horizontales que,
# con este ancho y alto, llegan casi sin reducir.
ANCHO_FRANJA = 2000
ALTO_FRANJA = 760
SOLAPE_FRANJAS = 140

INSTRUCCIONES_TRANSCRIPCION = """Eres un transcriptor de informes de laboratorio. Te paso la foto de una página de una analítica de sangre,
partida en franjas horizontales en orden de arriba abajo. Las franjas se solapan un poco: si una fila aparece en dos franjas, cópiala una sola vez.

Copia LITERALMENTE los resultados que se ven en la foto, una prueba por línea, con este formato:
Nombre de la prueba | resultado | unidad | valores de referencia

Ejemplo de líneas bien copiadas:
Hemoglobina | 14,8 | g/dL | 12,0 - 16,0
Eosinófilos (recuento) | * 0,12 | x 10^3/µL | 0,20 - 0,50

Reglas:
- Copia TODAS las filas de resultados, de arriba abajo, sin saltarte ninguna.
- Copia los números exactamente como aparecen, con sus comas y decimales.
- Algunos resultados llevan delante una marca del laboratorio (*, H o L) que indica que están fuera de rango.
  Copia la marca Y el número juntos, como "* 0,12". El resultado NUNCA es solo "*": el número está a su lado.
- No interpretes, no corrijas y no completes nada. No añadas pruebas que no se vean.
- Si un dato no se lee con seguridad, escribe ? en su lugar en vez de adivinarlo.
- Si la prueba no tiene valores de referencia en la foto, deja ese hueco vacío.
- Copia también, al principio, el nombre del paciente y la fecha si aparecen.
- No copies números de identificación (DNI, NHC, NASS, código SNS, nº de muestra, teléfonos, direcciones).
- Si la foto no es una analítica o no se puede leer, responde solo: ILEGIBLE"""


def _imagen_a_data_url(imagen: Image.Image) -> str:
    buf = io.BytesIO()
    imagen.save(buf, format="JPEG", quality=90)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def partir_en_franjas(imagen: Image.Image, desplazada: bool = False) -> list[Image.Image]:
    """
    Parte la página en franjas horizontales solapadas. Con desplazada=True los cortes caen
    a media franja de los normales, para que una segunda lectura vea las filas en otra posición.
    """
    imagen = imagen.convert("RGB")
    if imagen.width > ANCHO_FRANJA:
        imagen = imagen.resize((ANCHO_FRANJA, round(imagen.height * ANCHO_FRANJA / imagen.width)))
    paso = ALTO_FRANJA - SOLAPE_FRANJAS
    inicios = list(range(-paso // 2 if desplazada else 0, imagen.height - SOLAPE_FRANJAS, paso)) or [0]
    return [imagen.crop((0, max(0, y), imagen.width, min(imagen.height, y + ALTO_FRANJA))) for y in inicios]


def transcribir_con_ia(imagen: Image.Image, desplazada: bool = False) -> str:
    """Pide al modelo de visión que copie literalmente los resultados de la foto."""
    modelo = ChatOpenAI(model=MODELO_VISION, temperature=0)
    franjas = [
        {"type": "image_url", "image_url": {"url": _imagen_a_data_url(f), "detail": "high"}}
        for f in partir_en_franjas(imagen, desplazada)
    ]
    respuesta = modelo.invoke([
        SystemMessage(content=INSTRUCCIONES_TRANSCRIPCION),
        HumanMessage(content=[{"type": "text", "text": "Transcribe esta página de la analítica."}, *franjas]),
    ])
    return respuesta.content.strip()


def _campos(linea: str) -> list[str]:
    return [c.strip() for c in linea.split("|")]


def _clave(nombre: str) -> str:
    return " ".join(nombre.lower().split())


def _numeros(campo: str) -> list[float]:
    """Los números de un campo: "40,00 - 75,00" y "40-75" se consideran la misma lectura."""
    return [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", campo)]


def combinar_lecturas(lectura_a: str, lectura_b: str) -> tuple[str, list[str]]:
    """
    Compara dos lecturas independientes de la misma foto. Si no coinciden en el resultado
    o en el rango de una prueba, ese dato se cambia por "?" para que no se use: es mejor
    no dar un valor que dar uno mal leído.

    Returns:
        (texto combinado, nombres de las pruebas que no se han podido leer con seguridad)
    """
    filas_b = {_clave(_campos(l)[0]): _campos(l) for l in lectura_b.splitlines() if l.count("|") >= 2}
    lineas, dudosas = [], []
    for linea in lectura_a.splitlines():
        if linea.count("|") < 2:
            lineas.append(linea)
            continue
        campos = _campos(linea)
        otra = filas_b.get(_clave(campos[0]))
        if otra is None or len(otra) != len(campos):
            campos[1:] = ["?"] * (len(campos) - 1)
            dudosas.append(campos[0])
        else:
            # Se comparan resultado y valores de referencia; la unidad no cambia la interpretación
            for i in (1, len(campos) - 1):
                if _numeros(campos[i]) != _numeros(otra[i]):
                    campos[i] = "?"
                    if campos[0] not in dudosas:
                        dudosas.append(campos[0])
        lineas.append(" | ".join(campos))
    return "\n".join(lineas), dudosas


def leer_texto_foto(imagen_bytes, giro: int = 0) -> tuple[str, str, list[str]]:
    """
    Lee una foto de la analítica. Primero con la IA, que entiende tablas y fotos de móvil,
    leyéndola dos veces a la vez para descartar los datos en que las lecturas no coinciden;
    si la IA falla (sin conexión, sin clave...), con Tesseract.

    Returns:
        (texto, método, pruebas dudosas): el método es "IA" o "Tesseract". El texto empieza
        por "Error" si no se ha podido leer.
    """
    try:
        imagen = enderezar_automaticamente(abrir_imagen(imagen_bytes, giro))
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            # Dos lecturas con los cortes en sitios distintos: si se equivocan, rara vez coinciden
            lectura_a, lectura_b = ejecutor.map(transcribir_con_ia, [imagen, imagen], [False, True])
        if lectura_a.upper().startswith("ILEGIBLE") or lectura_b.upper().startswith("ILEGIBLE"):
            return ("Error: La foto no se puede leer. Repítela con más luz, sin reflejos y el texto enfocado.", "IA", [])
        texto, dudosas = combinar_lecturas(lectura_a, lectura_b)
        return texto, "IA", dudosas
    except Exception:
        return extraer_texto_imagen(imagen_bytes, giro), "Tesseract", []

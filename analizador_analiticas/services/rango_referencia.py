import re
from dataclasses import dataclass

PATRON_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")

# Por debajo de este porcentaje de desviación se considera "muy cerca del límite"
PORCENTAJE_CERCA_LIMITE = 5.0


@dataclass
class Posicion:
    """Dónde cae un valor respecto al rango de referencia del informe."""
    valor: float
    unidad: str
    minimo: float | None
    maximo: float | None
    estado: str              # "dentro", "por_encima" o "por_debajo"
    diferencia: float = 0.0  # Distancia al límite superado (0 si está dentro)
    porcentaje: float = 0.0  # Esa distancia en % del límite superado
    limite_texto: str = ""   # El límite superado tal como lo escribe el informe


def _a_float(texto: str) -> float:
    return float(texto.replace(",", "."))


def _formatear(numero: float) -> str:
    """Número con coma decimal y sin decimales sobrantes, como en un informe español."""
    texto = f"{numero:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def interpretar_rango(rango: str) -> tuple[float | None, float | None] | None:
    """
    Convierte el rango del informe en (mínimo, máximo).
    Admite "74 - 106", "<130", "≤ 130", "hasta 130", ">40", "≥ 40" y "mayor de 40".
    Devuelve None si no se puede interpretar.
    """
    texto = rango.strip().lower()
    numeros = PATRON_NUMERO.findall(texto)

    if len(numeros) >= 2 and re.search(r"\d\s*[-–a]\s*\d", texto):
        return _a_float(numeros[0]), _a_float(numeros[1])
    if len(numeros) == 1:
        if re.search(r"<|≤|hasta|menor|inferior", texto):
            return None, _a_float(numeros[0])
        if re.search(r">|≥|mayor|superior|desde", texto):
            return _a_float(numeros[0]), None
    return None


def calcular_posicion(valor: str, rango: str) -> Posicion | None:
    """Calcula si el valor está dentro, por encima o por debajo del rango y cuánto se aleja."""
    limites = interpretar_rango(rango)
    numero = PATRON_NUMERO.search(valor)
    if limites is None or numero is None:
        return None

    minimo, maximo = limites
    cifra = _a_float(numero.group())
    unidad = valor[numero.end():].strip()
    textos_rango = PATRON_NUMERO.findall(rango)

    if maximo is not None and cifra > maximo:
        diferencia = cifra - maximo
        porcentaje = diferencia / maximo * 100 if maximo else 0.0
        return Posicion(cifra, unidad, minimo, maximo, "por_encima", diferencia, porcentaje,
                        textos_rango[1] if minimo is not None else textos_rango[0])
    if minimo is not None and cifra < minimo:
        diferencia = minimo - cifra
        porcentaje = diferencia / minimo * 100 if minimo else 0.0
        return Posicion(cifra, unidad, minimo, maximo, "por_debajo", diferencia, porcentaje, textos_rango[0])
    return Posicion(cifra, unidad, minimo, maximo, "dentro")


def describir_posicion(posicion: Posicion) -> str:
    """Frase corta que explica dónde está el valor respecto al rango del informe."""
    unidad = f" {posicion.unidad}" if posicion.unidad else ""

    if posicion.estado == "dentro":
        return "Dentro del rango del informe."

    lado = "por encima del máximo" if posicion.estado == "por_encima" else "por debajo del mínimo"
    porcentaje = f"{posicion.porcentaje:.1f}".rstrip("0").rstrip(".").replace(".", ",")

    frase = (
        f"{_formatear(posicion.diferencia)}{unidad} {lado} ({posicion.limite_texto}), "
        f"un {porcentaje} % {'más' if posicion.estado == 'por_encima' else 'menos'}."
    )
    if posicion.porcentaje <= PORCENTAJE_CERCA_LIMITE:
        frase += " Muy cerca del límite."
    return frase

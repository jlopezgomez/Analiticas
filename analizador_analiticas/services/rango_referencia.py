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
    valor_texto: str = ""    # El valor tal como lo escribe el informe


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
                        textos_rango[1] if minimo is not None else textos_rango[0], numero.group())
    if minimo is not None and cifra < minimo:
        diferencia = minimo - cifra
        porcentaje = diferencia / minimo * 100 if minimo else 0.0
        return Posicion(cifra, unidad, minimo, maximo, "por_debajo", diferencia, porcentaje,
                        textos_rango[0], numero.group())
    return Posicion(cifra, unidad, minimo, maximo, "dentro", valor_texto=numero.group())


def limpiar_valor(valor: str) -> str:
    """Quita las marcas del laboratorio (*, H, L) que acompañan al número en el informe."""
    return re.sub(r"^\s*[*HL]\s*(?=\d)", "", valor.strip())


def esta_cerca_del_limite(posicion: Posicion) -> bool:
    """
    True si el valor se sale del rango muy poco: hasta un 5 %, o por la mínima cifra que
    el informe puede mostrar (p. ej. 0,00 frente a un mínimo de 0,01).
    """
    if posicion.estado == "dentro":
        return False
    decimales = len(posicion.limite_texto.replace(",", ".").partition(".")[2])
    paso_minimo = 10 ** -decimales
    return posicion.porcentaje <= PORCENTAJE_CERCA_LIMITE or posicion.diferencia <= paso_minimo + 1e-9


def frase_valor(valor: str, rango: str) -> str:
    """Frase exacta para un valor: tu cifra frente a lo normal del informe."""
    posicion = calcular_posicion(valor, rango)
    if posicion is None:
        return f"Tienes {limpiar_valor(valor)} (lo normal según el informe: {rango})."
    return describir_posicion(posicion)


def describir_posicion(posicion: Posicion) -> str:
    """Frase corta y sin tecnicismos que explica dónde está el valor respecto a lo normal."""
    if posicion.estado == "dentro":
        return "Dentro de lo normal según tu laboratorio."

    diferencia = _formatear(posicion.diferencia)
    if posicion.estado == "por_encima":
        frase = (f"Lo normal es hasta {posicion.limite_texto} y tú tienes {posicion.valor_texto}: "
                 f"{diferencia} por encima.")
    else:
        frase = (f"Lo normal es a partir de {posicion.limite_texto} y tú tienes {posicion.valor_texto}: "
                 f"{diferencia} por debajo.")

    if esta_cerca_del_limite(posicion):
        frase += " Está muy cerca del límite."
    return frase

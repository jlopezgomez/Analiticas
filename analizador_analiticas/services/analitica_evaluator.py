import re
from langchain_openai import ChatOpenAI
from models.analitica_model import ResultadoAnalitica, ValorSanguineo
from prompts.analitica_prompts import crear_analitica_prompts
from services.rango_referencia import calcular_posicion

PATRON_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _numeros_en(texto: str) -> set[float]:
    """Devuelve todos los números de un texto, aceptando coma o punto decimal."""
    return {float(n.replace(",", ".")) for n in PATRON_NUMERO.findall(texto)}


def _valor_aparece_en_texto(valor: str, numeros_texto: set[float], texto_lower: str) -> bool:
    numeros_valor = PATRON_NUMERO.findall(valor)
    if not numeros_valor:
        # Valores cualitativos ("Negativo", "Positivo"...): deben aparecer como palabra en el texto
        return valor.strip().lower() in texto_lower
    return float(numeros_valor[0].replace(",", ".")) in numeros_texto


def descartar_valores_no_presentes(resultado: ResultadoAnalitica, texto_analitica: str) -> list[str]:
    """
    Quita del resultado los valores cuyo número no aparece en el texto de la analítica,
    para que nunca se muestre un dato que la IA se haya inventado.

    Returns:
        Nombres de los parámetros descartados.
    """
    numeros_texto = _numeros_en(texto_analitica)
    texto_lower = texto_analitica.lower()
    descartados = []

    for lista in (resultado.valores_alterados, resultado.valores_normales, resultado.valores_sin_rango):
        conservados = []
        for valor in lista:
            if _valor_aparece_en_texto(valor.valor, numeros_texto, texto_lower):
                conservados.append(valor)
            else:
                descartados.append(valor.nombre)
        lista[:] = conservados

    palabras_nombre = [p for p in resultado.nombre_paciente.lower().split() if len(p) > 2]
    if palabras_nombre and not any(p in texto_lower for p in palabras_nombre):
        resultado.nombre_paciente = "No indicado"

    return descartados


def _rango_aparece_en_texto(rango: str, numeros_texto: set[float], texto_lower: str) -> bool:
    numeros_rango = PATRON_NUMERO.findall(rango)
    if not numeros_rango:
        # Rangos cualitativos ("Negativo"...); "No indicado" nunca está en un informe
        return bool(rango.strip()) and rango.strip().lower() in texto_lower
    return all(float(n.replace(",", ".")) in numeros_texto for n in numeros_rango)


def separar_valores_sin_rango(resultado: ResultadoAnalitica, texto_analitica: str) -> list[str]:
    """
    Pasa a valores_sin_rango los valores clasificados como normales o alterados cuyo rango
    de referencia no aparece en el documento: solo vale el rango que fija el laboratorio.

    Returns:
        Nombres de los parámetros que se han movido.
    """
    numeros_texto = _numeros_en(texto_analitica)
    texto_lower = texto_analitica.lower()
    movidos = []

    for lista in (resultado.valores_alterados, resultado.valores_normales):
        conservados = []
        for valor in lista:
            if _rango_aparece_en_texto(valor.rango_normal, numeros_texto, texto_lower):
                conservados.append(valor)
            else:
                resultado.valores_sin_rango.append(
                    ValorSanguineo(nombre=valor.nombre, valor=valor.valor, rango_normal="No indicado")
                )
                movidos.append(valor.nombre)
        lista[:] = conservados

    return movidos


def corregir_alterados_dentro_de_rango(resultado: ResultadoAnalitica) -> list[str]:
    """
    Pasa a normales los valores que la IA marcó como alterados pero que, según los números
    del rango del informe, están dentro de él.

    Returns:
        Nombres de los parámetros corregidos.
    """
    corregidos = []
    conservados = []
    for valor in resultado.valores_alterados:
        posicion = calcular_posicion(valor.valor, valor.rango_normal)
        if posicion is not None and posicion.estado == "dentro":
            resultado.valores_normales.append(
                ValorSanguineo(nombre=valor.nombre, valor=valor.valor, rango_normal=valor.rango_normal)
            )
            corregidos.append(valor.nombre)
        else:
            conservados.append(valor)
    resultado.valores_alterados[:] = conservados
    return corregidos


def crear_evaluador_analitica():
    """Construye y devuelve la cadena LangChain para análisis de analíticas."""
    modelo_base = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    modelo_estructurado = modelo_base.with_structured_output(ResultadoAnalitica)
    chat_prompt = crear_analitica_prompts()
    cadena_evaluacion = chat_prompt | modelo_estructurado

    return cadena_evaluacion


def evaluar_analitica(texto_analitica: str, analitica_previa: str = None) -> ResultadoAnalitica:
    """
    Evalúa una analítica de sangre y devuelve un análisis estructurado.

    Args:
        texto_analitica: Texto extraído del PDF de la analítica
        analitica_previa: Texto de una analítica anterior para comparación (opcional)

    Returns:
        ResultadoAnalitica: Objeto con el análisis completo estructurado
    """
    try:
        cadena_evaluacion = crear_evaluador_analitica()

        # Construir contexto previo si existe
        if analitica_previa:
            contexto_previo = f"""
**ANALÍTICA ANTERIOR DEL PACIENTE (para comparación de tendencias):**
{analitica_previa}

Por favor, compara los valores actuales con los anteriores e indica si cada parámetro ha mejorado, empeorado o se mantiene estable.
"""
        else:
            contexto_previo = ""

        resultado = cadena_evaluacion.invoke({
            "texto_analitica": texto_analitica,
            "contexto_previo": contexto_previo
        })

        return resultado

    except Exception as e:
        return ResultadoAnalitica(
            nombre_paciente="Error en procesamiento",
            fecha_analitica="No disponible",
            valores_normales=[],
            valores_alterados=[],
            resumen_general=f"Error durante el análisis: {str(e)}. Por favor, verifica que el PDF sea legible.",
            especialistas_recomendados=[],
            recomendaciones=["Verificar que el PDF contiene texto seleccionable y no imágenes escaneadas."],
            nivel_urgencia_global="No determinado"
        )

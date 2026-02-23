from langchain_openai import ChatOpenAI
from models.analitica_model import ResultadoAnalitica
from prompts.analitica_prompts import crear_analitica_prompts


def crear_evaluador_analitica():
    """Construye y devuelve la cadena LangChain para análisis de analíticas."""
    modelo_base = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1
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

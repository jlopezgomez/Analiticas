from pydantic import BaseModel, Field


class ValorSanguineo(BaseModel):
    """Representa un valor dentro del rango normal."""
    nombre: str = Field(description="Nombre del parámetro tal como aparece en el documento.")
    valor: str = Field(description="Valor copiado literalmente del documento, con su unidad.")
    rango_normal: str = Field(description="Rango de referencia copiado literalmente del documento, o 'No indicado' si no aparece.")


class ValorAlterado(BaseModel):
    """Representa un valor fuera del rango normal."""
    nombre: str = Field(description="Nombre del parámetro tal como aparece en el documento.")
    valor: str = Field(description="Valor copiado literalmente del documento, con su unidad.")
    rango_normal: str = Field(description="Rango de referencia copiado literalmente del documento, o 'No indicado' si no aparece.")
    tipo_alteracion: str = Field(description="'Alto' o 'Bajo' según corresponda.")
    que_es: str = Field(
        default="",
        description="Qué es este parámetro en una frase corta y con palabras de todos los días. Ej: 'Un tipo de defensa de la sangre que ayuda a combatir alergias e infecciones.'"
    )
    interpretacion: str = Field(description="Qué significa tenerlo así, en 1-2 frases sencillas, sin palabras médicas.")
    posible_causa: str = Field(description="Causas habituales, explicadas con palabras sencillas.")
    nivel_urgencia: str = Field(description="'Leve', 'Moderado' o 'Urgente'.")


class ResultadoAnalitica(BaseModel):
    """Modelo completo del análisis de una analítica de sangre."""
    texto_legible: bool = Field(
        default=True,
        description="False si el texto no es una analítica de sangre o está demasiado dañado para leer sus valores con seguridad."
    )
    nombre_paciente: str = Field(description="Nombre del paciente extraído del documento, o 'No indicado' si no aparece.")
    fecha_analitica: str = Field(description="Fecha de la analítica extraída del documento, o 'No indicada' si no aparece.")
    valores_normales: list[ValorSanguineo] = Field(description="Lista de valores dentro del rango normal.")
    valores_alterados: list[ValorAlterado] = Field(description="Lista de valores fuera del rango normal.")
    valores_sin_rango: list[ValorSanguineo] = Field(
        default_factory=list,
        description="Valores que el documento muestra SIN rango de referencia. No se clasifican como normales ni alterados; rango_normal = 'No indicado'."
    )
    resumen_general: str = Field(description="Resumen del estado general en 3-4 frases sencillas, sin palabras médicas.")
    explicacion_sencilla: str = Field(
        default="",
        description=(
            "Explicación final 'En pocas palabras', como se lo contaría un médico de familia a un paciente: "
            "4-6 frases cortas y sencillas pero precisas. Nombra cada valor fuera de lo normal por su nombre, "
            "con su cifra y lo normal según el informe, y explica qué es en palabras sencillas. "
            "No uses expresiones vagas ('un par de', 'algunas defensas', 'un poco') ni digas si es grave o no: "
            "eso lo valora el médico. Termina diciendo qué hacer ahora."
        )
    )
    especialistas_recomendados: list[str] = Field(description="Lista de especialistas a consultar según las alteraciones encontradas.")
    recomendaciones: list[str] = Field(description="Lista de recomendaciones generales de estilo de vida o seguimiento.")
    nivel_urgencia_global: str = Field(description="Nivel de urgencia global: 'Normal', 'Seguimiento recomendado' o 'Consultar pronto'.")

from pydantic import BaseModel, Field


class ValorSanguineo(BaseModel):
    """Representa un valor dentro del rango normal."""
    nombre: str = Field(description="Nombre del parámetro analizado.")
    valor: str = Field(description="Valor obtenido con su unidad.")
    rango_normal: str = Field(description="Rango de referencia normal.")


class ValorAlterado(BaseModel):
    """Representa un valor fuera del rango normal."""
    nombre: str = Field(description="Nombre del parámetro alterado.")
    valor: str = Field(description="Valor obtenido con su unidad.")
    rango_normal: str = Field(description="Rango de referencia normal.")
    tipo_alteracion: str = Field(description="'Alto' o 'Bajo' según corresponda.")
    interpretacion: str = Field(description="Explicación clara en lenguaje simple para el paciente.")
    posible_causa: str = Field(description="Posibles causas comunes de esta alteración.")
    nivel_urgencia: str = Field(description="'Leve', 'Moderado' o 'Urgente'.")


class ResultadoAnalitica(BaseModel):
    """Modelo completo del análisis de una analítica de sangre."""
    nombre_paciente: str = Field(description="Nombre del paciente extraído del documento.")
    fecha_analitica: str = Field(description="Fecha de la analítica extraída del documento.")
    valores_normales: list[ValorSanguineo] = Field(description="Lista de valores dentro del rango normal.")
    valores_alterados: list[ValorAlterado] = Field(description="Lista de valores fuera del rango normal.")
    resumen_general: str = Field(description="Resumen ejecutivo del estado general de salud en lenguaje simple.")
    especialistas_recomendados: list[str] = Field(description="Lista de especialistas a consultar según las alteraciones encontradas.")
    recomendaciones: list[str] = Field(description="Lista de recomendaciones generales de estilo de vida o seguimiento.")
    nivel_urgencia_global: str = Field(description="Nivel de urgencia global: 'Normal', 'Seguimiento recomendado' o 'Consultar pronto'.")

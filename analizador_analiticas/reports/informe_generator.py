from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from models.analitica_model import ResultadoAnalitica


# Paleta de colores médica
COLOR_AZUL = colors.HexColor("#1a73e8")
COLOR_VERDE = colors.HexColor("#34a853")
COLOR_AMARILLO = colors.HexColor("#f9ab00")
COLOR_ROJO = colors.HexColor("#ea4335")
COLOR_GRIS_CLARO = colors.HexColor("#f8f9fa")
COLOR_GRIS = colors.HexColor("#5f6368")
COLOR_OSCURO = colors.HexColor("#202124")


def obtener_color_urgencia(nivel: str):
    """Devuelve el color correspondiente al nivel de urgencia."""
    nivel_lower = nivel.lower()
    if "urgente" in nivel_lower or "pronto" in nivel_lower:
        return COLOR_ROJO
    elif "moderado" in nivel_lower or "seguimiento" in nivel_lower:
        return COLOR_AMARILLO
    else:
        return COLOR_VERDE


def generar_informe_pdf(resultado: ResultadoAnalitica) -> bytes:
    """
    Genera un informe PDF profesional con los resultados del análisis.

    Args:
        resultado: Objeto ResultadoAnalitica con el análisis completo

    Returns:
        bytes: Contenido del PDF generado
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    # Estilos personalizados
    estilo_titulo = ParagraphStyle(
        "Titulo",
        parent=styles["Title"],
        fontSize=22,
        textColor=COLOR_AZUL,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold"
    )
    estilo_subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=styles["Normal"],
        fontSize=11,
        textColor=COLOR_GRIS,
        spaceAfter=4,
        alignment=TA_CENTER
    )
    estilo_seccion = ParagraphStyle(
        "Seccion",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=COLOR_AZUL,
        spaceBefore=16,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    estilo_normal = ParagraphStyle(
        "Normal2",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_OSCURO,
        spaceAfter=4,
        leading=14,
        alignment=TA_JUSTIFY
    )
    estilo_item = ParagraphStyle(
        "Item",
        parent=styles["Normal"],
        fontSize=10,
        textColor=COLOR_OSCURO,
        spaceAfter=3,
        leftIndent=12,
        leading=14
    )
    estilo_advertencia = ParagraphStyle(
        "Advertencia",
        parent=styles["Normal"],
        fontSize=9,
        textColor=COLOR_GRIS,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName="Helvetica-Oblique"
    )

    contenido = []

    # ── CABECERA ──────────────────────────────────────────────────────────────
    contenido.append(Paragraph("Informe de Analítica de Sangre", estilo_titulo))
    contenido.append(Paragraph("Análisis generado con Inteligencia Artificial", estilo_subtitulo))
    contenido.append(HRFlowable(width="100%", thickness=2, color=COLOR_AZUL, spaceAfter=12))

    # ── DATOS DEL PACIENTE ────────────────────────────────────────────────────
    color_urgencia = obtener_color_urgencia(resultado.nivel_urgencia_global)
    datos_paciente = [
        ["Paciente", resultado.nombre_paciente, "Fecha analítica", resultado.fecha_analitica],
        ["Estado general", resultado.nivel_urgencia_global, "Fecha informe", datetime.now().strftime("%d/%m/%Y")],
    ]
    tabla_paciente = Table(datos_paciente, colWidths=[3.5 * cm, 7.5 * cm, 3.5 * cm, 3.5 * cm])
    tabla_paciente.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLOR_AZUL),
        ("BACKGROUND", (2, 0), (2, -1), COLOR_AZUL),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (1, 1), (1, 1), color_urgencia),
        ("TEXTCOLOR", (1, 1), (1, 1), colors.white),
        ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [COLOR_GRIS_CLARO, colors.white]),
        ("ROWBACKGROUNDS", (3, 0), (3, -1), [COLOR_GRIS_CLARO, colors.white]),
    ]))
    contenido.append(tabla_paciente)
    contenido.append(Spacer(1, 12))

    # ── RESUMEN GENERAL ───────────────────────────────────────────────────────
    contenido.append(Paragraph("Resumen General", estilo_seccion))
    contenido.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_AZUL, spaceAfter=8))
    contenido.append(Paragraph(resultado.resumen_general, estilo_normal))

    # ── VALORES ALTERADOS ─────────────────────────────────────────────────────
    if resultado.valores_alterados:
        contenido.append(Paragraph("Valores Alterados", estilo_seccion))
        contenido.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_ROJO, spaceAfter=8))

        for valor in resultado.valores_alterados:
            color_val = obtener_color_urgencia(valor.nivel_urgencia)

            encabezado = [[
                Paragraph(f"<b>{valor.nombre}</b>", ParagraphStyle("H", fontSize=11, textColor=colors.white, fontName="Helvetica-Bold")),
                Paragraph(f"Valor: {valor.valor}", ParagraphStyle("V", fontSize=10, textColor=colors.white)),
                Paragraph(f"Referencia: {valor.rango_normal}", ParagraphStyle("R", fontSize=10, textColor=colors.white)),
                Paragraph(f"{valor.tipo_alteracion} · {valor.nivel_urgencia}", ParagraphStyle("U", fontSize=10, textColor=colors.white, fontName="Helvetica-Bold")),
            ]]
            t_enc = Table(encabezado, colWidths=[5 * cm, 4 * cm, 4.5 * cm, 4.5 * cm])
            t_enc.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), color_val),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            contenido.append(t_enc)

            detalle = [
                [Paragraph("<b>¿Qué significa?</b>", estilo_item), Paragraph(valor.interpretacion, estilo_normal)],
                [Paragraph("<b>Posible causa:</b>", estilo_item), Paragraph(valor.posible_causa, estilo_normal)],
            ]
            t_det = Table(detalle, colWidths=[4 * cm, 14 * cm])
            t_det.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_GRIS_CLARO),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.white),
            ]))
            contenido.append(t_det)
            contenido.append(Spacer(1, 8))

    # ── VALORES NORMALES ──────────────────────────────────────────────────────
    if resultado.valores_normales:
        contenido.append(Paragraph("Valores en Rango Normal", estilo_seccion))
        contenido.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_VERDE, spaceAfter=8))

        datos_tabla = [["Parámetro", "Valor obtenido", "Rango de referencia"]]
        for valor in resultado.valores_normales:
            datos_tabla.append([valor.nombre, valor.valor, valor.rango_normal])

        tabla_normales = Table(datos_tabla, colWidths=[6 * cm, 5 * cm, 7 * cm])
        tabla_normales.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_VERDE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_GRIS_CLARO, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ]))
        contenido.append(tabla_normales)

    # ── ESPECIALISTAS RECOMENDADOS ────────────────────────────────────────────
    if resultado.especialistas_recomendados:
        contenido.append(Paragraph("Especialistas Recomendados", estilo_seccion))
        contenido.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_AZUL, spaceAfter=8))
        for especialista in resultado.especialistas_recomendados:
            contenido.append(Paragraph(f"• {especialista}", estilo_item))

    # ── RECOMENDACIONES ───────────────────────────────────────────────────────
    if resultado.recomendaciones:
        contenido.append(Paragraph("Recomendaciones de Seguimiento", estilo_seccion))
        contenido.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_AZUL, spaceAfter=8))
        for rec in resultado.recomendaciones:
            contenido.append(Paragraph(f"• {rec}", estilo_item))

    # ── AVISO LEGAL ───────────────────────────────────────────────────────────
    contenido.append(Spacer(1, 20))
    contenido.append(HRFlowable(width="100%", thickness=1, color=COLOR_GRIS, spaceAfter=8))
    contenido.append(Paragraph(
        "AVISO IMPORTANTE: Este informe ha sido generado por inteligencia artificial con fines informativos. "
        "No sustituye en ningún caso el diagnóstico médico profesional. "
        "Consulte siempre con su médico para la interpretación de sus resultados y cualquier decisión sobre su salud.",
        estilo_advertencia
    ))

    doc.build(contenido)
    return buffer.getvalue()

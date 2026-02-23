import PyPDF2
from io import BytesIO


def extraer_texto_pdf(archivo_pdf) -> str:
    """
    Extrae el texto de un archivo PDF subido por el usuario.

    Args:
        archivo_pdf: Archivo PDF subido mediante st.file_uploader

    Returns:
        str: Texto extraído del PDF o mensaje de error
    """
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(archivo_pdf.read()))
        texto_completo = ""

        for numero_pagina, pagina in enumerate(pdf_reader.pages, 1):
            texto_pagina = pagina.extract_text()
            if texto_pagina and texto_pagina.strip():
                texto_completo += f"\n--- PÁGINA {numero_pagina} ---\n"
                texto_completo += texto_pagina + "\n"

        texto_completo = texto_completo.strip()

        if not texto_completo:
            return "Error: El PDF parece estar vacío o contener solo imágenes escaneadas."

        return texto_completo

    except Exception as e:
        return f"Error al procesar el archivo PDF: {str(e)}"

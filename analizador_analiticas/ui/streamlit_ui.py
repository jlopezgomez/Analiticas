import streamlit as st
from services.pdf_processor import extraer_texto_pdf
from services.ocr_processor import extraer_texto_imagen, abrir_imagen
from services.analitica_evaluator import (
    evaluar_analitica, descartar_valores_no_presentes, separar_valores_sin_rango,
    corregir_alterados_dentro_de_rango, PATRON_NUMERO
)
from services.rango_referencia import (
    calcular_posicion, describir_posicion, esta_cerca_del_limite, limpiar_valor, frase_valor
)
from reports.informe_generator import generar_informe_pdf
from models.analitica_model import ResultadoAnalitica

# Una analítica real tiene muchos números; con menos de estos, la lectura ha fallado
MIN_NUMEROS_LEGIBLES = 6
# Más fotos alargan mucho la lectura y el análisis; una analítica rara vez pasa de unas pocas páginas
MAX_FOTOS = 6

# Streamlit no deja cambiar el texto del botón de subida ("Upload", en inglés), así que se cambia con CSS.
# Va acotado por la clase st-key-<key> que Streamlit pone a cada widget con key.
ESTILOS_SUBIDA = """
<style>
[data-testid="stFileUploaderDropzoneInstructions"] { display: none; }

/* Solo el botón de subir/añadir: la "X" de quitar un archivo es kind="minimal" y se deja como está */
[data-testid="stFileUploaderDropzone"] button:not([kind="minimal"]) > * { display: none; }
[data-testid="stFileUploaderDropzone"] button:not([kind="minimal"]) { justify-content: center; }
[data-testid="stFileUploaderDropzone"] button:not([kind="minimal"])::after { font-size: 1rem; font-weight: 600; }
.st-key-analitica_pdf [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"])::after { content: "📄 Elegir PDF"; }
.st-key-analitica_previa [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"])::after { content: "📄 Elegir PDF anterior"; }
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"])::after { content: "📷 Hacer foto"; }
/* Con alguna foto ya puesta, el botón sirve para añadir la siguiente página */
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] button[aria-label="Add files"]::after { content: "📷 Añadir otra página"; }

/* El botón de foto, grande y llamativo para que se vea a la primera en el móvil */
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] {
    padding: 0; min-height: 0; border: none; background: transparent;
}
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] > span,
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"]) { width: 100%; }
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"]) {
    min-height: 3.5rem; background: #ff4b4b; border-color: #ff4b4b; color: white; border-radius: 0.5rem;
}
.st-key-analitica_foto [data-testid="stFileUploaderDropzone"] button:not([kind="minimal"])::after { font-size: 1.15rem; }
</style>
"""


def main():
    st.set_page_config(
        page_title="Analizador de Analíticas de Sangre",
        page_icon="🩸",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(ESTILOS_SUBIDA, unsafe_allow_html=True)

    st.title("🩸 Analizador de Analíticas de Sangre con IA")
    st.markdown("""
    **Interpreta tus resultados de laboratorio de forma clara y sencilla**

    Sube tu analítica en PDF o haz una foto con tu móvil y la inteligencia artificial te explicará
    qué significan tus valores, detectará anomalías y te orientará sobre los próximos pasos.
    """)

    st.info(
        "⚕️ **Aviso médico:** Esta herramienta tiene fines informativos y no sustituye "
        "la consulta con un profesional de la salud. Consulta siempre a tu médico.",
        icon="ℹ️"
    )

    st.divider()

    col_entrada, col_resultado = st.columns([1, 1], gap="large")

    with col_entrada:
        procesar_entrada()

    with col_resultado:
        mostrar_area_resultados()


def procesar_entrada():
    st.header("📂 Datos de Entrada")

    tab_pdf, tab_camara = st.tabs(["📄 Subir PDF", "📷 Hacer Foto"])

    archivo_analitica = None
    imagenes_analitica = []

    with tab_pdf:
        st.markdown("**Sube tu analítica en formato PDF**")
        archivo_analitica = st.file_uploader(
            "Selecciona el archivo PDF:",
            type=["pdf"],
            key="analitica_pdf",
            help="El PDF debe tener texto seleccionable, no imágenes escaneadas."
        )
        if archivo_analitica:
            st.success(f"✅ Archivo cargado: {archivo_analitica.name}")
            st.caption(f"📄 Tamaño: {archivo_analitica.size:,} bytes")

    with tab_camara:
        st.markdown(
            "**Cómo hacer la foto:**\n"
            "1. Pulsa el botón rojo **📷 Hacer foto**.\n"
            "2. En el menú que aparece, elige **Hacer foto** (iPhone) o **Cámara** (Android).\n"
            "3. ¿Tu analítica tiene más páginas? Vuelve a pulsar el botón y haz una foto de cada una: "
            "se analizarán todas juntas."
        )
        st.caption("💡 Consejos: móvil en vertical, buena luz, sin reflejos, la hoja plana y el texto enfocado.")
        imagenes_subidas = st.file_uploader(
            "Fotos de tu analítica:",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="analitica_foto",
            help="También puedes elegir fotos que ya tengas en la galería.",
            label_visibility="collapsed"
        )

        imagen_webcam = None
        # Un toggle y no un expander: el expander monta la cámara aunque esté cerrado y pide permiso al cargar
        if st.toggle("💻 Usar la cámara del ordenador (webcam)", key="usar_webcam"):
            imagen_webcam = st.camera_input(
                "Capturar analítica",
                key="analitica_camara",
                help="Apunta la cámara a tu analítica y asegúrate de que el texto sea legible."
            )

        imagenes_analitica = list(imagenes_subidas or [])
        if imagen_webcam:
            imagenes_analitica.append(imagen_webcam)

        if len(imagenes_analitica) > MAX_FOTOS:
            st.warning(f"⚠️ Solo se analizarán las primeras {MAX_FOTOS} fotos.")
            imagenes_analitica = imagenes_analitica[:MAX_FOTOS]

        if imagenes_analitica:
            st.success(
                f"✅ {len(imagenes_analitica)} foto(s) cargada(s). Revisa que el texto se lea bien "
                "y que la foto esté derecha: si no, pulsa ↻ Girar."
            )
            giros = st.session_state.setdefault("giros", {})
            columnas = st.columns(min(len(imagenes_analitica), 3))
            for i, imagen in enumerate(imagenes_analitica):
                clave = id_foto(imagen)
                with columnas[i % len(columnas)]:
                    if st.button("↻ Girar", key=f"girar_{clave}", use_container_width=True):
                        giros[clave] = (giros.get(clave, 0) + 90) % 360
                    st.image(abrir_imagen(imagen, giros.get(clave, 0)), caption=f"Foto {i + 1}")

    st.markdown("---")

    archivo_analitica_previa = None
    with st.expander("📊 Comparar con analítica anterior (opcional)"):
        st.markdown("Sube una analítica anterior en PDF para detectar tendencias en tus valores.")
        archivo_analitica_previa = st.file_uploader(
            "Analítica anterior (PDF):",
            type=["pdf"],
            key="analitica_previa",
            help="Opcional: para comparar la evolución de tus valores a lo largo del tiempo."
        )
        if archivo_analitica_previa:
            st.success(f"✅ Analítica previa cargada: {archivo_analitica_previa.name}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        analizar = st.button(
            "🔬 Analizar Analítica",
            type="primary",
            use_container_width=True
        )

    with col2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            st.rerun()

    st.session_state["archivo_analitica"] = archivo_analitica
    st.session_state["imagenes_analitica"] = imagenes_analitica
    st.session_state["archivo_analitica_previa"] = archivo_analitica_previa
    st.session_state["analizar"] = analizar


def mostrar_area_resultados():
    st.header("📋 Resultados del Análisis")

    if st.session_state.get("analizar", False):
        archivo = st.session_state.get("archivo_analitica")
        imagenes = st.session_state.get("imagenes_analitica") or []
        archivo_previo = st.session_state.get("archivo_analitica_previa")

        if archivo is None and not imagenes:
            st.error("⚠️ Por favor sube un PDF o haz una foto de tu analítica.")
            return

        procesar_analisis(archivo, imagenes, archivo_previo)
    else:
        st.info("""
        👆 **¿Cómo usar esta herramienta?**

        1. Elige cómo introducir tu analítica:
           - 📄 **PDF**: sube el archivo directamente
           - 📷 **Fotos**: haz una foto de cada página con el móvil (puedes añadir varias)
        2. (Opcional) Sube una analítica anterior para comparar tendencias
        3. Haz clic en **Analizar Analítica**
        4. Aquí verás la interpretación completa

        **💡 Consejos para mejores resultados:**
        - PDF: usa archivos con texto seleccionable
        - Foto: buena iluminación, sin reflejos y texto enfocado
        - El informe final es descargable en PDF
        """)


def id_foto(imagen) -> str:
    """Identificador estable de una foto subida, para recordar cuánto la ha girado el usuario."""
    return getattr(imagen, "file_id", None) or f"{getattr(imagen, 'name', 'foto')}-{len(imagen.getvalue())}"


def leer_fotos(imagenes, estado, barra) -> str:
    """Lee todas las fotos con OCR y junta su texto, marcando de qué foto viene cada parte."""
    giros = st.session_state.get("giros", {})
    textos = []
    for i, imagen in enumerate(imagenes, start=1):
        estado.text(f"📷 Leyendo foto {i} de {len(imagenes)}...")
        barra.progress(5 + int(25 * i / len(imagenes)))
        texto = extraer_texto_imagen(imagen, giros.get(id_foto(imagen), 0))
        if texto.startswith("Error"):
            st.warning(f"⚠️ Foto {i}: {texto.removeprefix('Error: ')} Se analizarán las demás.")
            continue
        textos.append(f"--- FOTO {i} ---\n{texto}")

    if not textos:
        return "Error: No se pudo leer ninguna de las fotos. Repítelas con más luz, sin reflejos y el texto enfocado."
    return "\n\n".join(textos)


def procesar_analisis(archivo_analitica=None, imagenes_analitica=None, archivo_previo=None):
    with st.spinner("🔬 Procesando analítica..."):
        barra = st.progress(0)
        estado = st.empty()

        if archivo_analitica is not None:
            estado.text("📄 Extrayendo texto del PDF...")
            barra.progress(20)
            texto_analitica = extraer_texto_pdf(archivo_analitica)
        else:
            texto_analitica = leer_fotos(imagenes_analitica, estado, barra)

        if texto_analitica.startswith("Error"):
            st.error(f"❌ {texto_analitica}")
            return

        with st.expander("🔎 Ver texto leído del documento"):
            st.caption("Esto es lo que la aplicación ha conseguido leer. El análisis se basa solo en este texto.")
            st.text(texto_analitica)

        if len(PATRON_NUMERO.findall(texto_analitica)) < MIN_NUMEROS_LEGIBLES:
            estado.empty()
            barra.empty()
            st.error(
                "❌ **No se ha podido leer bien la analítica.** Apenas se reconocen valores en el documento. "
                "Si es una foto, repítela con más luz, sin reflejos, la hoja plana y el texto enfocado."
            )
            return

        texto_previo = None
        if archivo_previo is not None:
            estado.text("📄 Procesando analítica anterior...")
            barra.progress(35)
            texto_previo = extraer_texto_pdf(archivo_previo)
            if texto_previo.startswith("Error"):
                st.warning("⚠️ No se pudo procesar la analítica anterior. Continuando sin comparación.")
                texto_previo = None

        estado.text("🤖 Analizando resultados con IA...")
        barra.progress(60)
        resultado = evaluar_analitica(texto_analitica, texto_previo)

        if resultado.nivel_urgencia_global == "No determinado":
            estado.empty()
            barra.empty()
            mostrar_error_analisis(resultado.resumen_general)
            return

        descartados = descartar_valores_no_presentes(resultado, texto_analitica)
        sin_rango_movidos = separar_valores_sin_rango(resultado, texto_analitica)
        corregir_alterados_dentro_de_rango(resultado)

        hay_valores = resultado.valores_alterados or resultado.valores_normales or resultado.valores_sin_rango
        if not resultado.texto_legible or not hay_valores:
            estado.empty()
            barra.empty()
            st.error(
                "❌ **No se han podido identificar valores fiables en el documento.** "
                "Si es una foto, repítela con más luz, sin reflejos, la hoja plana y el texto enfocado. "
                "Puedes revisar arriba el texto que se ha leído."
            )
            return

        if descartados:
            st.warning(
                f"⚠️ Se han descartado {len(descartados)} valores porque no aparecen en el documento "
                f"({', '.join(descartados)}). El resumen podría estar incompleto: si es una foto, "
                "prueba a repetirla con mejor calidad."
            )

        if sin_rango_movidos:
            st.info(
                f"ℹ️ {len(sin_rango_movidos)} valores no tienen rango de referencia en el informe "
                f"({', '.join(sin_rango_movidos)}), así que no se valoran como normales ni alterados. "
                "El resumen podría mencionarlos: consulta su interpretación con tu médico."
            )

        estado.text("📝 Generando informe...")
        barra.progress(85)
        pdf_bytes = generar_informe_pdf(resultado)

        barra.progress(100)
        estado.empty()
        barra.empty()

        mostrar_resultados(resultado, pdf_bytes)


def mostrar_error_analisis(detalle: str):
    detalle_lower = detalle.lower()
    if "api_key" in detalle_lower or "credentials" in detalle_lower or "401" in detalle_lower:
        st.error(
            "❌ **No se pudo analizar:** la aplicación no tiene configurada una clave de OpenAI válida. "
            "Si eres el administrador, revisa `OPENAI_API_KEY` en los Secrets de la app."
        )
    else:
        st.error("❌ **No se pudo analizar la analítica.** Inténtalo de nuevo en unos minutos.")
    with st.expander("Ver detalle técnico"):
        st.code(detalle)


def _barra_rango_html(posicion) -> str:
    """Barra con la zona del rango del informe en verde y un punto donde cae el valor."""
    if posicion.minimo is not None and posicion.maximo is not None:
        margen = (posicion.maximo - posicion.minimo) * 0.5 or 1
        inicio, fin = posicion.minimo - margen, posicion.maximo + margen
    elif posicion.maximo is not None:
        inicio, fin = 0, posicion.maximo * 1.5 or 1
    else:
        inicio, fin = posicion.minimo * 0.5, posicion.minimo * 2 or 1

    inicio = min(inicio, posicion.valor)
    fin = max(fin, posicion.valor)

    def pct(x):
        return max(0.0, min(100.0, (x - inicio) / (fin - inicio) * 100))

    zona_ini = pct(posicion.minimo) if posicion.minimo is not None else 0
    zona_fin = pct(posicion.maximo) if posicion.maximo is not None else 100
    punto = pct(posicion.valor)

    if posicion.estado == "dentro":
        color = "#1e8e3e"
    elif esta_cerca_del_limite(posicion):
        color = "#f29900"
    else:
        color = "#d93025"

    return f"""
<div style="position:relative;height:14px;margin:6px 0 4px;border-radius:7px;background:rgba(128,128,128,0.18);">
  <div style="position:absolute;left:{zona_ini:.1f}%;width:{zona_fin - zona_ini:.1f}%;height:100%;
              border-radius:7px;background:rgba(30,142,62,0.35);"></div>
  <div style="position:absolute;left:calc({punto:.1f}% - 7px);top:-2px;width:14px;height:18px;
              border-radius:4px;background:{color};border:2px solid white;"></div>
</div>"""


def mostrar_comparacion_rango(valor: str, rango: str):
    """Muestra tu valor frente al rango del informe: cifras, barra y cuánto se aleja."""
    st.markdown(f"Tu valor: **{limpiar_valor(valor)}** · Lo normal según tu laboratorio: **{rango}**")
    posicion = calcular_posicion(valor, rango)
    if posicion is None:
        return
    st.markdown(_barra_rango_html(posicion), unsafe_allow_html=True)
    st.caption(describir_posicion(posicion))


def mostrar_resultados(resultado: ResultadoAnalitica, pdf_bytes: bytes):
    st.subheader("🏥 Estado General")

    nivel = resultado.nivel_urgencia_global.lower()
    if "normal" in nivel:
        st.success(f"✅ **{resultado.nivel_urgencia_global}** — Tus valores están dentro de los rangos esperados.")
        color_badge = "🟢"
    elif "seguimiento" in nivel:
        st.warning(f"⚠️ **{resultado.nivel_urgencia_global}** — Algunos valores requieren atención. Consulta a tu médico.")
        color_badge = "🟡"
    else:
        st.error(f"🔴 **{resultado.nivel_urgencia_global}** — Se detectaron valores que requieren atención médica próxima.")
        color_badge = "🔴"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 Paciente", resultado.nombre_paciente)
    with col2:
        st.metric("📅 Fecha analítica", resultado.fecha_analitica)
    with col3:
        st.metric("🔍 Estado", f"{color_badge} {resultado.nivel_urgencia_global}")

    st.divider()

    st.subheader("📝 Resumen de tu Analítica")
    st.info(resultado.resumen_general)

    st.divider()

    if resultado.valores_alterados:
        st.subheader(f"⚠️ Valores fuera de lo normal ({len(resultado.valores_alterados)})")
        for valor in resultado.valores_alterados:
            urgencia = valor.nivel_urgencia.lower()
            if "urgente" in urgencia:
                icono = "🔴"
                expander_color = "🔴"
            elif "moderado" in urgencia:
                icono = "🟡"
                expander_color = "🟡"
            else:
                icono = "🟠"
                expander_color = "🟠"

            posicion = calcular_posicion(valor.valor, valor.rango_normal)
            direccion = "Más alto de lo normal" if valor.tipo_alteracion.lower().startswith("alt") else "Más bajo de lo normal"
            cerca = " · muy cerca del límite" if posicion is not None and esta_cerca_del_limite(posicion) else ""

            with st.expander(f"{icono} **{valor.nombre}** — {limpiar_valor(valor.valor)} · {direccion}{cerca}"):
                if valor.que_es:
                    st.markdown(f"**¿Qué es?** {valor.que_es}")
                mostrar_comparacion_rango(valor.valor, valor.rango_normal)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**¿Qué significa para ti?**")
                    st.write(valor.interpretacion)
                with col_b:
                    st.markdown("**¿Por qué puede pasar?**")
                    st.write(valor.posible_causa)
                st.caption(f"Importancia: {expander_color} {valor.nivel_urgencia}")
    else:
        st.success("✅ No se detectaron valores fuera de rango.")

    if resultado.valores_normales:
        with st.expander(f"✅ Ver valores normales ({len(resultado.valores_normales)})"):
            for valor in resultado.valores_normales:
                st.markdown(f"**{valor.nombre}**")
                mostrar_comparacion_rango(valor.valor, valor.rango_normal)

    if resultado.valores_sin_rango:
        with st.expander(f"❔ Valores sin rango de referencia en el informe ({len(resultado.valores_sin_rango)})"):
            st.caption(
                "El laboratorio no indica un rango para estos valores, así que la aplicación no dice "
                "si son normales o no. Consulta su interpretación con tu médico."
            )
            for valor in resultado.valores_sin_rango:
                st.markdown(f"**{valor.nombre}:** {limpiar_valor(valor.valor)}")

    st.divider()

    col_esp, col_rec = st.columns(2)

    with col_esp:
        st.subheader("👨‍⚕️ ¿A qué médico ir?")
        if resultado.especialistas_recomendados:
            for esp in resultado.especialistas_recomendados:
                st.markdown(f"• {esp}")
        else:
            st.success("No se requiere consulta especializada por el momento.")

    with col_rec:
        st.subheader("💡 Recomendaciones")
        if resultado.recomendaciones:
            for rec in resultado.recomendaciones:
                st.markdown(f"• {rec}")

    st.divider()
    st.subheader("🗣️ En pocas palabras")

    if resultado.valores_alterados:
        lineas = [f"Tienes **{len(resultado.valores_alterados)} valores fuera de lo normal**:"]
        for valor in resultado.valores_alterados:
            lineas.append(f"- **{valor.nombre}**: {frase_valor(valor.valor, valor.rango_normal)}")
    else:
        lineas = ["**Todos los valores con rango en el informe están dentro de lo normal.**"]
    if resultado.valores_normales:
        lineas.append(f"\n{len(resultado.valores_normales)} valores están dentro de lo normal.")
    if resultado.valores_sin_rango:
        lineas.append(f"\n{len(resultado.valores_sin_rango)} valores no tienen rango en el informe: consúltalos con tu médico.")
    st.markdown("\n".join(lineas))

    if resultado.explicacion_sencilla:
        st.success(resultado.explicacion_sencilla)

    st.divider()

    st.subheader("📥 Descargar Informe")
    st.download_button(
        label="📄 Descargar Informe en PDF",
        data=pdf_bytes,
        file_name=f"informe_analitica_{resultado.nombre_paciente.replace(' ', '_')}.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True
    )

    st.caption("⚕️ Recuerda: este informe es orientativo. Consulta siempre con tu médico para una interpretación profesional.")

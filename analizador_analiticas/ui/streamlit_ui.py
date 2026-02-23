import streamlit as st
from services.pdf_processor import extraer_texto_pdf
from services.ocr_processor import extraer_texto_imagen
from services.analitica_evaluator import evaluar_analitica
from reports.informe_generator import generar_informe_pdf
from models.analitica_model import ResultadoAnalitica


def main():
    st.set_page_config(
        page_title="Analizador de Analíticas de Sangre",
        page_icon="🩸",
        layout="wide",
        initial_sidebar_state="expanded"
    )

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
    imagen_analitica = None

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
        st.markdown("**Haz una foto a tu analítica con la cámara**")
        st.caption("💡 Consejos: buena iluminación, sin reflejos, texto enfocado y la hoja plana.")
        imagen_analitica = st.camera_input(
            "Capturar analítica",
            key="analitica_camara",
            help="Apunta la cámara a tu analítica y asegúrate de que el texto sea legible."
        )
        if imagen_analitica:
            st.success("✅ Foto capturada correctamente.")

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
    st.session_state["imagen_analitica"] = imagen_analitica
    st.session_state["archivo_analitica_previa"] = archivo_analitica_previa
    st.session_state["analizar"] = analizar


def mostrar_area_resultados():
    st.header("📋 Resultados del Análisis")

    if st.session_state.get("analizar", False):
        archivo = st.session_state.get("archivo_analitica")
        imagen = st.session_state.get("imagen_analitica")
        archivo_previo = st.session_state.get("archivo_analitica_previa")

        if archivo is None and imagen is None:
            st.error("⚠️ Por favor sube un PDF o haz una foto de tu analítica.")
            return

        procesar_analisis(archivo, imagen, archivo_previo)
    else:
        st.info("""
        👆 **¿Cómo usar esta herramienta?**

        1. Elige cómo introducir tu analítica:
           - 📄 **PDF**: sube el archivo directamente
           - 📷 **Foto**: usa la cámara de tu móvil o webcam
        2. (Opcional) Sube una analítica anterior para comparar tendencias
        3. Haz clic en **Analizar Analítica**
        4. Aquí verás la interpretación completa

        **💡 Consejos para mejores resultados:**
        - PDF: usa archivos con texto seleccionable
        - Foto: buena iluminación, sin reflejos y texto enfocado
        - El informe final es descargable en PDF
        """)


def procesar_analisis(archivo_analitica=None, imagen_analitica=None, archivo_previo=None):
    with st.spinner("🔬 Procesando analítica..."):
        barra = st.progress(0)
        estado = st.empty()

        if archivo_analitica is not None:
            estado.text("📄 Extrayendo texto del PDF...")
            barra.progress(20)
            texto_analitica = extraer_texto_pdf(archivo_analitica)
        else:
            estado.text("📷 Procesando imagen con OCR...")
            barra.progress(20)
            texto_analitica = extraer_texto_imagen(imagen_analitica)

        if texto_analitica.startswith("Error"):
            st.error(f"❌ {texto_analitica}")
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

        estado.text("📝 Generando informe...")
        barra.progress(85)
        pdf_bytes = generar_informe_pdf(resultado)

        barra.progress(100)
        estado.empty()
        barra.empty()

        mostrar_resultados(resultado, pdf_bytes)


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
        st.subheader(f"⚠️ Valores Alterados ({len(resultado.valores_alterados)})")
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

            with st.expander(f"{icono} **{valor.nombre}** — {valor.valor} (Referencia: {valor.rango_normal}) · {valor.tipo_alteracion}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("**¿Qué significa?**")
                    st.write(valor.interpretacion)
                with col_b:
                    st.markdown("**Posible causa:**")
                    st.write(valor.posible_causa)
                st.caption(f"Nivel de urgencia: {expander_color} {valor.nivel_urgencia}")
    else:
        st.success("✅ No se detectaron valores fuera de rango.")

    if resultado.valores_normales:
        with st.expander(f"✅ Ver valores en rango normal ({len(resultado.valores_normales)})"):
            for valor in resultado.valores_normales:
                st.markdown(f"**{valor.nombre}:** {valor.valor} *(Referencia: {valor.rango_normal})*")

    st.divider()

    col_esp, col_rec = st.columns(2)

    with col_esp:
        st.subheader("👨‍⚕️ Especialistas Recomendados")
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

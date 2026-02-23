# 🩸 Analizador de Analíticas de Sangre con IA

Herramienta que interpreta analíticas de sangre en PDF usando inteligencia artificial, explica los valores alterados en lenguaje sencillo y genera un informe descargable.

## Funcionalidades

- Extracción automática de valores desde PDF
- Detección e interpretación de anomalías en lenguaje simple
- Comparación con analíticas anteriores para detectar tendencias
- Sugerencia de especialistas según los resultados
- Generación de informe PDF descargable

## Instalación

```bash
# 1. Clonar o descargar el proyecto
cd analizador_analiticas

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar la API key de OpenAI
# Crea un archivo .env en la raíz del proyecto con:
echo "OPENAI_API_KEY=tu_api_key_aqui" > .env

# 4. Ejecutar la aplicación
streamlit run main.py
```

## Estructura del proyecto

```
analizador_analiticas/
├── main.py                          # Punto de entrada
├── requirements.txt                 # Dependencias
├── models/
│   └── analitica_model.py           # Modelos Pydantic
├── services/
│   ├── pdf_processor.py             # Extracción de texto PDF
│   └── analitica_evaluator.py       # Lógica de análisis con LangChain
├── prompts/
│   └── analitica_prompts.py         # Prompts especializados
├── reports/
│   └── informe_generator.py         # Generador de informe PDF
└── ui/
    └── streamlit_ui.py              # Interfaz de usuario
```

## Variables de entorno

Crea un archivo `.env` en la raíz con:

```
OPENAI_API_KEY=tu_api_key_aqui
```

## Aviso importante

Esta herramienta tiene fines informativos únicamente. No sustituye el diagnóstico médico profesional. Consulta siempre con tu médico para la interpretación de tus resultados.

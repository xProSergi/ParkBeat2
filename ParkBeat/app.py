import streamlit as st
import pandas as pd
import numpy as np
import base64
from datetime import datetime, date, time, timedelta
import plotly.graph_objects as go
from predict import load_model_artifacts  # Solo para obtener listas de atracciones/zonas
import warnings
import os
import requests
import json

warnings.filterwarnings('ignore')

# Configurar URL de la API (puedes usar variable de entorno o hardcodear)
API_URL = os.getenv('API_URL', 'https://TU_API_ID.execute-api.eu-west-3.amazonaws.com/prod/predict')

def predict_wait_time_api(input_dict):
    """Llama a la API de Lambda para obtener predicción"""
    try:
        response = requests.post(
            API_URL,
            json=input_dict,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        resultado = response.json()
        
        # Adaptar formato si es necesario (API Gateway a veces envuelve en 'body')
        if isinstance(resultado, dict) and 'body' in resultado:
            resultado = json.loads(resultado['body'])
        
        return resultado
    except requests.exceptions.Timeout:
        st.error("⏱️ Timeout: La API tardó demasiado en responder. Intenta de nuevo.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al llamar a la API: {str(e)}")
        st.info("💡 Verifica que la URL de la API sea correcta y que API Gateway esté desplegado.")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        return None

def get_base64_image(image_path):
    """Convierte una imagen a base64"""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

st.set_page_config(
    page_title="ParkBeat — Predicción Parque Warner",
    page_icon="img/logoParklytics.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Overrides */
    html, body, #root, .stApp {
        margin: 0 !important;
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Main content container */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Hero Section */
    .hero-container {
        position: relative;
        width: 100%;
        overflow: hidden;
        margin: 0;
        padding: 0;
    }
    
    .hero-content {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        text-align: center;
        width: 100%;
        padding: 0 1rem;
        z-index: 2;
    }
    
    .hero-title {
        font-size: 4.5rem;
        font-weight: 800;
        margin: 0;
        color: #FF8C00;
        text-shadow: 0 4px 12px rgba(0,0,0,0.9);
        line-height: 1.1;
    }
    
    .hero-subtitle {
        font-size: 3rem;
        margin: 2rem 0 0;
        color: #FFD54F;
        font-weight: 700;
        text-shadow: 0 4px 18px rgba(0,0,0,0.85);
        line-height: 1.4;
        letter-spacing: 0.5px;
    }
    
    /* Card Styles */
    .card {
        background-color: var(--background-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid var(--border-color);
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .hero-title {
            font-size: 3rem;
        }
        .hero-subtitle {
            font-size: 1.8rem;
            margin-top: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

def render_hero():
    try:
        hero_image_path = os.path.join("img", "fotoBatman.jpg")
        if os.path.exists(hero_image_path):
            hero_image = get_base64_image(hero_image_path)

            st.markdown(f"""
            <style>
                .hero-container {{
                    position: relative;
                    width: 100%;
                    height: 600px;
                    background: linear-gradient(rgba(0,0,0,0.7), rgba(0,0,0,0.4)), 
                                url("data:image/jpg;base64,{hero_image}") no-repeat center center;
                    background-size: cover;
                    overflow: hidden;
                }}
                
                .hero-title {{
                    font-size: 4.5rem;
                    font-weight: 800;
                    margin: 0;
                    color: #FF8C00 !important;
                    text-shadow: 0 4px 12px rgba(0,0,0,0.9);
                    line-height: 1.1;
                }}
                
                .hero-subtitle {{
                    font-size: 3rem;
                    margin: 2rem 0 0;
                    color: #FFD54F !important;
                    font-weight: 700;
                    text-shadow: 0 4px 18px rgba(0,0,0,0.85);
                    line-height: 1.4;
                    letter-spacing: 0.5px;
                }}
                
                @media (max-width: 768px) {{
                    .hero-container {{
                        height: 400px;
                    }}
                    .hero-title {{
                        font-size: 3rem;
                        color: #FF8C00 !important;
                    }}
                    .hero-subtitle {{
                        font-size: 1.8rem;
                        margin-top: 1rem;
                        color: #FFD54F !important;
                    }}
                }}
            </style>
            
            <div class="hero-container">
                <div class="hero-content">
                    <h1 class="hero-title">ParkBeat</h1>
                    <p class="hero-subtitle">Predicción inteligente de tiempos de espera en Parque Warner</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <h1 style="color: #FF8C00 !important; margin: 0; font-size: 3rem; text-shadow: 0 4px 12px rgba(0,0,0,0.9);">
                    ParkBeat
                </h1>
                <p style="color: #FFD54F !important; margin: 1rem 0 0; font-size: 2rem; font-weight: 700; text-shadow: 0 4px 14px rgba(0,0,0,0.85);">
                    Predicción inteligente de tiempos de espera en Parque Warner
                </p>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Error al cargar la imagen: {e}")

def render_sidebar():
    with st.sidebar:
        st.title("🎢 ParkBeat")
        st.markdown("---")
        
        try:
            logo_path = os.path.join("img", "logoParklytics.png")
            if os.path.exists(logo_path):
                logo_image = get_base64_image(logo_path)
                st.markdown(f"""
                <div style="text-align: center; margin: 1rem 0;">
                    <img src="data:image/png;base64,{logo_image}" width="150" style="border-radius: 10px;">
                </div>
                """, unsafe_allow_html=True)
        except:
            pass
        
        st.markdown("### 📍 Navegación")
        
        menu_option = st.radio(
            "",
            ["Inicio", "🤔 ¿Qué es ParkBeat?", "💡 ¿Por qué este proyecto?", "📊 Acerca de los datos"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if menu_option == "🤔 ¿Qué es ParkBeat?":
            st.markdown("""
            ### 🤔 ¿Qué es ParkBeat?
            
            **ParkBeat** es una plataforma de predicción inteligente de tiempos de espera para atracciones en **Parque Warner Madrid**.
            
            **Características principales:**
            
            ✅ **Predicciones precisas** basadas en datos históricos  
            🌤️ **Factores meteorológicos** incluidos en el modelo  
            ⏰ **Análisis temporal** por fecha y hora específicas  
            🎢 **Cobertura completa** de todas las atracciones  
            
            **Objetivo:** Ayudar a los visitantes a planificar mejor su día en el parque y maximizar su experiencia.
            """)
            
        elif menu_option == "💡 ¿Por qué este proyecto?":
            st.markdown("""
            ### 💡 ¿Por qué este proyecto?
    
            Soy un apasionado de los parques temáticos desde que tengo memoria, y mejorar la experiencia del visitante, especialmente en aspectos como los tiempos de espera, es lo que realmente me inspira.  
            Desde 2007 (primera vez que visité el parque), Parque Warner ha sido una parte fundamental de mi vida. Podría decirse que he crecido junto a él, y con el tiempo, mi amor por el parque se ha fusionado con mi pasión por el análisis de datos, lo que ha dado lugar a la creación de ParkBeat.
    
            **Las tecnologías que he utilizado son las siguientes:**
    
            - 🤖 **Machine Learning** con Python  
            - 📊 **Análisis de datos** con Pandas y NumPy  
            - 📈 **Visualización** con Plotly  
            - 🚀 **Despliegue** con Streamlit  
            - ☁️ **Modelos en producción** con AWS Lambda
            """)
            
        elif menu_option == "📊 Acerca de los datos":
            st.markdown("""
            ### 📊 Acerca de los datos
            
            **Fuente de datos:**
            
            📥 - **Histórico** de tiempos de espera reales (Ingesta de datos mediante API Queue-Times) 
            🌦️ - **Datos meteorológicos** en tiempo real  
            🎢 - **Información** específica de cada atracción  
          
            
            **Procesamiento:**
            
            1. **Limpieza** de datos inconsistentes  
            2. **Transformación** de variables temporales  
            3. **Feature engineering** para factores relevantes  
            4. **Normalización** de escalas  
            5. **Validación** cruzada del modelo  
            
            **Precisión del modelo:** >85% en predicciones
            """)
        
        st.markdown("---")
        
        st.markdown("### 📧 Contacto")
        st.markdown("""
        **Desarrollador:** Sergio López  
        **Versión:** 1.0  
        **Estado:** En producción  

        🔗 [LinkedIn](https://www.linkedin.com/in/sergio-lopez-dev/)         
        📁 [Repositorio](https://github.com/xProSergi/ParkBeat) 
        """)

def main():
    render_sidebar()
    
    render_hero()

    st.markdown("""
    <div style="background: #fff8e6; color: #5c3d00; padding: 1rem; border-radius: 12px; 
                border-left: 4px solid #ffc107; margin-bottom: 2rem; margin-top: 3rem;">
        <strong>⚠️ Aviso:</strong> Esta aplicación es independiente y educativa. 
        No está afiliada a Parque Warner.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    ## 🎯 Bienvenido a ParkBeat
    
    Predice los tiempos de espera en las atracciones del Parque Warner Madrid con precisión. 
    Simplemente selecciona una atracción, la fecha y la hora de tu visita, y te mostraremos una 
    estimación del tiempo de espera esperado.
    """)
    
    # Cargar modelo SOLO para obtener listas de atracciones/zonas
    with st.spinner("Cargando modelo y datos..."):
        try:
            artifacts = load_model_artifacts()
            if not artifacts or "error" in str(artifacts).lower():
                st.error("❌ Error al cargar el modelo. Por favor, verifica los archivos del modelo.")
                st.stop()
                
            df = artifacts.get("df_processed", pd.DataFrame())
            if df.empty:
                st.error("❌ No se encontraron datos de entrenamiento.")
                st.stop()
                
        except Exception as e:
            st.error(f"❌ Error al cargar el modelo: {str(e)}")
            st.stop()

    @st.cache_data
    def get_attractions():
        return sorted(df["atraccion"].dropna().astype(str).unique().tolist())

    @st.cache_data
    def get_zones():
        return sorted(df["zona"].dropna().astype(str).unique().tolist())

    def get_zone_for_attraction(attraction):
        row = df[df["atraccion"] == attraction]
        return row["zona"].iloc[0] if not row.empty else ""

    atracciones = get_attractions()
    zonas = get_zones()

    st.markdown("## ⚙️ Configura tu predicción")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container():
            st.markdown("### 🎢 Selecciona una atracción")
            atraccion_seleccionada = st.selectbox(
                "Elige una atracción de la lista",
                options=atracciones,
                index=0,
                help="Selecciona la atracción que deseas consultar",
                key="attraction_select"
            )
            
            zona_auto = get_zone_for_attraction(atraccion_seleccionada)
            if zona_auto:
                st.info(f"📍 **Zona:** {zona_auto}")

    with col2:
        with st.container():
            st.markdown("### 📅 Fecha y hora de visita")
            
            fecha_seleccionada = st.date_input(
                "Selecciona la fecha",
                value=date.today(),
                min_value=date.today(),
                format="DD/MM/YYYY",
                key="date_input"
            )
            
            hora_seleccionada = st.time_input(
                "Hora de la visita",
                value=time(14, 0), 
                step=timedelta(minutes=15),
                key="time_input"
            )
            
            dia_semana_es = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                "Thursday": "Jueves", "Friday": "Viernes", 
                "Saturday": "Sábado", "Sunday": "Domingo"
            }
            dia_nombre = fecha_seleccionada.strftime("%A")
            es_fin_semana = fecha_seleccionada.weekday() >= 5
            st.info(f"📆 **Día:** {dia_semana_es.get(dia_nombre, dia_nombre)} - {'Fin de semana' if es_fin_semana else 'Día laborable'}")

    with st.expander("🌤️ Configurar condiciones meteorológicas (opcional)", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            temperatura = st.slider(
                "Temperatura (°C)", 
                min_value=-5, 
                max_value=45, 
                value=22,
                help="Temperatura en grados Celsius",
                key="temp_slider"
            )
            
        with col2:
            humedad = st.slider(
                "Humedad (%)", 
                min_value=0, 
                max_value=100, 
                value=60,
                key="humidity_slider"
            )

        sensacion_termica = st.slider(
            "Sensación térmica (°C)", 
            min_value=-10, 
            max_value=50, 
            value=22,
            key="feels_like_slider"
        )

        codigo_clima = st.selectbox(
            "Condición meteorológica",
            options=[1, 2, 3, 4, 5],
            index=2,
            format_func=lambda x: {
                1: "☀️ Soleado - Excelente",
                2: "⛅ Parcialmente nublado - Bueno",
                3: "☁️ Nublado - Normal",
                4: "🌧️ Lluvia ligera - Malo",
                5: "⛈️ Lluvia fuerte/Tormenta - Muy malo"
            }[x],
            key="weather_select"
        )

    predecir = st.button(
        "🚀 Calcular tiempo de espera",
        type="primary",
        use_container_width=True,
        key="predict_button_main"
    )

    if predecir:
        hora_str = hora_seleccionada.strftime("%H:%M:%S")
        fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")
        
        input_data = {
            "atraccion": atraccion_seleccionada,
            "zona": zona_auto,
            "fecha": fecha_str,
            "hora": hora_str,
            "temperatura": temperatura,
            "humedad": humedad,
            "sensacion_termica": sensacion_termica,
            "codigo_clima": codigo_clima
        }

        with st.spinner("🔮 Calculando predicción..."):
            try:
                resultado = predict_wait_time_api(input_data)
                
                if resultado is None:
                    st.error("❌ No se pudo obtener la predicción. Verifica la conexión con la API.")
                    st.stop()
                
                minutos_pred = resultado.get("minutos_predichos", 0)
                
                if minutos_pred < 15:
                    gradient = "linear-gradient(135deg, #16a085 0%, #2ecc71 100%)"
                    emoji, nivel = "🟢", "Bajo"
                elif minutos_pred < 30:
                    gradient = "linear-gradient(135deg, #f6d365 0%, #fda085 100%)"
                    emoji, nivel = "🟡", "Moderado"
                elif minutos_pred < 60:
                    gradient = "linear-gradient(135deg, #f7971e 0%, #ffd200 100%)"
                    emoji, nivel = "🟠", "Alto"
                else:
                    gradient = "linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)"
                    emoji, nivel = "🔴", "Muy Alto"

                st.markdown("## 📊 Resultados de la predicción")
                
                st.markdown(f"""
                <div style="
                    background-color: var(--background-color);
                    border: 2px solid var(--border-color);
                    border-radius: 15px;
                    padding: 2rem;
                    margin: 1rem 0;
                    box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                ">
                    <div style="
                        text-align: center;
                        padding: 1.5rem 1rem;
                    ">
                        <div style="
                            font-size: 1.2rem;
                            color: var(--text-color);
                            margin-bottom: 0.5rem;
                            font-weight: 500;
                        ">
                            {emoji} Tiempo de espera estimado
                        </div>
                        <div style="
                            font-size: 4rem;
                            font-weight: 800;
                            margin: 0.5rem 0;
                            background: {gradient};
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                            background-clip: text;
                        ">
                            {minutos_pred:.0f} min
                        </div>
                        <div style="
                            font-size: 1.2rem;
                            color: var(--text-color);
                            opacity: 0.9;
                            margin-top: 0.5rem;
                        ">
                            {nivel} • {atraccion_seleccionada}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                tab1, tab2, tab3 = st.tabs(["📝 Información", "🔍 Contexto", "💡 Recomendaciones"])

                with tab1:
                    st.markdown("### 📝 Información de la predicción")
                    info_cols = st.columns(2)
                    
                    with info_cols[0]:
                        st.markdown("#### 📅 Fecha y hora")
                        dia_semana_result = resultado.get('dia_semana', dia_semana_es.get(dia_nombre, 'N/A'))
                        st.markdown(f"""
                        <div style="
                            background-color: var(--background-color);
                            border: 1px solid var(--border-color);
                            border-radius: 12px;
                            padding: 1.25rem;
                            margin: 0.5rem 0;
                        ">
                            <p style="color: var(--text-color); margin: 0.5rem 0;">
                                <strong>Día de la semana:</strong> {dia_semana_result}<br>
                                <strong>Día del mes:</strong> {resultado.get('dia_mes', fecha_seleccionada.day)}<br>
                                <strong>Hora seleccionada:</strong> {hora_seleccionada.strftime('%H:%M')}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with info_cols[1]:
                        weather_emoji = {
                            1: '☀️ Soleado',
                            2: '⛅ Parcial',
                            3: '☁️ Nublado',
                            4: '🌧️ Lluvia',
                            5: '⛈️ Tormenta'
                        }.get(codigo_clima, 'N/A')
                        
                        st.markdown("#### 🌦️ Condiciones")
                        st.markdown(f"""
                        <div style="
                            background-color: var(--background-color);
                            border: 1px solid var(--border-color);
                            border-radius: 12px;
                            padding: 1.25rem;
                            margin: 0.5rem 0;
                        ">
                            <p style="color: var(--text-color); margin: 0.5rem 0;">
                                <strong>Temperatura:</strong> {temperatura}°C<br>
                                <strong>Humedad:</strong> {humedad}%<br>
                                <strong>Sensación térmica:</strong> {sensacion_termica}°C<br>
                                <strong>Condición:</strong> {weather_emoji}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

                with tab2:
                    st.markdown("### 🔍 Contexto")
                    
                    context_items = [
                        ("📅 Fin de semana", resultado.get('es_fin_de_semana', es_fin_semana)),
                        ("🌉 Es puente", resultado.get('es_puente', False)),
                        ("🔥 Hora pico", resultado.get('es_hora_pico', False)),
                        ("🌿 Hora valle", resultado.get('es_hora_valle', False))
                    ]
                    
                    cols = st.columns(2)
                    for i, (label, value) in enumerate(context_items):
                        with cols[i % 2]:
                            st.markdown(f"""
                            <div style="
                                background-color: var(--background-color);
                                border: 1px solid var(--border-color);
                                border-radius: 12px;
                                padding: 1rem;
                                margin: 0.5rem 0;
                            ">
                                <div style="
                                    display: flex;
                                    justify-content: space-between;
                                    align-items: center;
                                ">
                                    <span style="color: var(--text-color);">{label}</span>
                                    <span style="
                                        color: {'#16a085' if value else 'var(--text-color)'};
                                        font-weight: 600;
                                        opacity: {1 if value else 0.7};
                                    ">
                                        {'Sí' if value else 'No'}
                                    </span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown("### 📊 Comparación de predicciones")
                    valores = {
                        "Predicción Final": minutos_pred,
                        "Modelo Base": resultado.get('prediccion_raw', resultado.get('prediccion_base', minutos_pred)),
                        "P75 Histórico": resultado.get('p75_historico', 0),
                        "Mediana": resultado.get('median_historico', 0)
                    }
                    
                    # Filtrar valores válidos
                    valores = {k: v for k, v in valores.items() if v > 0}
                    
                    if valores:
                        fig = go.Figure(go.Bar(
                            x=list(valores.keys()),
                            y=list(valores.values()),
                            text=[f"{v:.1f} min" for v in valores.values()],
                            textposition='auto',
                            marker_color=['#6c63ff', '#4facfe', '#43e97b', '#f6d365'][:len(valores)]
                        ))
                        
                        fig.update_layout(
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=400,
                            margin=dict(t=20, b=20, l=20, r=20),
                            yaxis_title="Minutos",
                            xaxis_title="",
                            showlegend=False,
                            font=dict(color='var(--text-color)'),
                            xaxis=dict(tickfont=dict(color='var(--text-color)')),
                            yaxis=dict(gridcolor='var(--border-color)')
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    st.markdown("### 💡 Recomendaciones")
                    
                    recommendations = []
                    
                    if minutos_pred < 15:
                        recommendations.append(("✅", "Excelente momento", 
                            f"El tiempo de espera es bajo ({minutos_pred:.1f} min). Aprovecha para subir ahora."))
                    elif minutos_pred < 30:
                        recommendations.append(("👍", "Buen momento", 
                            f"El tiempo de espera es moderado ({minutos_pred:.1f} min). Un buen momento para hacer cola."))
                    elif minutos_pred < 60:
                        recommendations.append(("⚠️", "Tiempo de espera alto", 
                            f"El tiempo de espera es alto ({minutos_pred:.1f} min). Considera planificar para otro momento o usar acceso rápido si está disponible."))
                    else:
                        recommendations.append(("🚫", "Tiempo de espera muy alto", 
                            f"El tiempo de espera es muy alto ({minutos_pred:.1f} min). Te recomendamos cambiar de atracción o volver en otro momento."))
                    
                    if resultado.get('es_hora_pico'):
                        recommendations.append(("⏰", "Hora pico", 
                            "Estás en horario de mayor afluencia (11:00-16:00). Las esperas suelen ser más largas."))
                    
                    if resultado.get('es_fin_de_semana', es_fin_semana):
                        recommendations.append(("📅", "Fin de semana", 
                            "Los fines de semana suelen tener más visitantes. Si puedes, considera visitar entre semana."))
                    
                    for emoji, title, text in recommendations:
                        with st.expander(f"{emoji} {title}", expanded=True):
                            st.markdown(f"<div style='padding: 0.5rem 0; color: var(--text-color);'>{text}</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"❌ Error al realizar la predicción: {str(e)}")
                st.exception(e)  

    if not predecir:
        st.markdown("""
        ## 🎯 ¿Cómo funciona?
        
        1. **Selecciona una atracción** de la lista desplegable
        2. **Elige la fecha y hora** de tu visita
        3. **Ajusta las condiciones meteorológicas** si lo deseas
        4. Haz clic en **Calcular tiempo de espera**
        
        ¡Obtendrás una predicción precisa basada en datos históricos y condiciones actuales!
        
        ### 📈 Estadísticas rápidas
        """)
      
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: var(--text-color); opacity: 0.7; padding: 1.5rem 0;">
        🎢 ParkBeat — Predicción de tiempos de espera en Parque Warner<br>
        <small>Desarrollado con ❤️ por Sergio López | v1.0</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

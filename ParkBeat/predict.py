# ====================================================
# SCRIPT DE PREDICCIÓN - USO DEL MODELO ENTRENADO
# ====================================================

import pandas as pd
import numpy as np
import joblib
from datetime import datetime

def load_model_artifacts():
    """Carga todos los artefactos necesarios para hacer predicciones"""
    model = joblib.load("models/xgb_model_professional.pkl")
    scaler = joblib.load("models/xgb_scaler_professional.pkl")
    encoding_maps = joblib.load("models/xgb_encoding_professional.pkl")
    columnas_entrenamiento = joblib.load("models/xgb_columns_professional.pkl")
    df_processed = joblib.load("models/df_processed.pkl")
    
    # Cargar históricos
    hist_mes = joblib.load("models/hist_mes.pkl")
    hist_hora = joblib.load("models/hist_hora.pkl")
    hist_dia_semana = joblib.load("models/hist_dia_semana.pkl")
    hist_mes_dia = joblib.load("models/hist_mes_dia.pkl")
    hist_hora_dia = joblib.load("models/hist_hora_dia.pkl")
    hist_mes_hora = joblib.load("models/hist_mes_hora.pkl")
    
    return {
        "model": model,
        "scaler": scaler,
        "encoding_maps": encoding_maps,
        "columnas_entrenamiento": columnas_entrenamiento,
        "df_processed": df_processed,
        "hist_mes": hist_mes,
        "hist_hora": hist_hora,
        "hist_dia_semana": hist_dia_semana,
        "hist_mes_dia": hist_mes_dia,
        "hist_hora_dia": hist_hora_dia,
        "hist_mes_hora": hist_mes_hora
    }

def parse_hora(hora_str):
    """Parsea la hora a formato numérico"""
    try:
        if pd.isna(hora_str):
            return np.nan
        if isinstance(hora_str, (int, float)):
            return int(hora_str)
        s = str(hora_str).strip()
        if ":" in s:
            parts = s.split(":")
            hora = int(float(parts[0]))
            minuto = int(float(parts[1])) if len(parts) > 1 else 0
            return hora + minuto / 60.0
        return int(float(s))
    except:
        return np.nan

def get_temporada(mes):
    """Determina la temporada del año"""
    if mes in [7, 8]:
        return 3  # Muy Alta
    elif mes in [10]:
        return 3  # Muy Alta
    elif mes in [4, 5, 6, 12]:
        return 2  # Alta
    elif mes in [3, 9, 11]:
        return 1  # Media
    else:
        return 0  # Baja

def es_festivo_espana(fecha):
    """Detecta festivos en España"""
    mes = fecha.month
    dia = fecha.day
    if mes == 1 and dia == 1: return 1  # Año Nuevo
    if mes == 1 and dia == 6: return 1  # Reyes
    if mes == 5 and dia == 1: return 1  # Día del Trabajo
    if mes == 10 and dia == 12: return 1  # Día de la Hispanidad
    if mes == 11 and dia == 1: return 1  # Todos los Santos
    if mes == 12 and dia == 6: return 1  # Constitución
    if mes == 12 and dia == 8: return 1  # Inmaculada
    if mes == 12 and dia == 25: return 1  # Navidad
    return 0

def es_puente(fecha):
    """Detecta si un día es parte de un puente (festivo + fin de semana cercano)"""
    if es_festivo_espana(fecha):
        return 1
    dia_anterior = fecha - pd.Timedelta(days=1)
    dia_siguiente = fecha + pd.Timedelta(days=1)
    if fecha.weekday() == 4 and es_festivo_espana(dia_siguiente):  # Viernes antes de festivo
        return 1
    if fecha.weekday() == 0 and es_festivo_espana(dia_anterior):  # Lunes después de festivo
        return 1
    if fecha.weekday() == 6 and es_festivo_espana(dia_anterior):  # Domingo después de festivo (sábado)
        return 1
    return 0

def prepare_input_for_prediction(input_dict, artifacts):
    """Prepara un input para predicción aplicando todo el feature engineering"""
    df_train = artifacts["df_processed"]
    scaler = artifacts["scaler"]
    encoding_maps = artifacts["encoding_maps"]
    columnas_entrenamiento = artifacts["columnas_entrenamiento"]
    hist_mes = artifacts["hist_mes"]
    hist_hora = artifacts["hist_hora"]
    hist_dia_semana = artifacts["hist_dia_semana"]
    hist_mes_dia = artifacts["hist_mes_dia"]
    hist_hora_dia = artifacts["hist_hora_dia"]
    hist_mes_hora = artifacts["hist_mes_hora"]
    
    # Parsear fecha
    fecha = pd.to_datetime(input_dict["fecha"], errors="coerce")
    if pd.isna(fecha):
        fecha = pd.Timestamp.now()
    
    # Parsear hora
    hora_str = input_dict.get("hora", "12:00:00")
    hora = parse_hora(hora_str)
    if pd.isna(hora):
        hora = 12.0
    
    # Features temporales
    mes = fecha.month
    dia_mes = fecha.day
    dia_semana_num = fecha.weekday()
    semana_año = fecha.isocalendar().week
    trimestre = fecha.quarter
    año = fecha.year
    
    # Días de semana
    es_lunes = 1 if dia_semana_num == 0 else 0
    es_martes = 1 if dia_semana_num == 1 else 0
    es_miercoles = 1 if dia_semana_num == 2 else 0
    es_jueves = 1 if dia_semana_num == 3 else 0
    es_viernes = 1 if dia_semana_num == 4 else 0
    es_sabado = 1 if dia_semana_num == 5 else 0
    es_domingo = 1 if dia_semana_num == 6 else 0
    es_fin_de_semana = 1 if dia_semana_num in [5, 6] else 0
    es_dia_laborable = 1 if dia_semana_num in [0, 1, 2, 3, 4] else 0
    
    # Features de HORA DEL DÍA
    hora_int = int(hora)
    es_hora_apertura = 1 if (hora_int >= 10 and hora_int < 11) else 0
    es_hora_pico = 1 if (hora_int >= 11 and hora_int <= 16) else 0
    es_hora_valle_manana = 1 if hora_int < 10 else 0
    es_hora_valle_tarde = 1 if hora_int > 18 else 0
    es_hora_valle = 1 if (es_hora_valle_manana or es_hora_valle_tarde) else 0
    
    # Features de PUENTES/FESTIVOS
    es_festivo_val = es_festivo_espana(fecha)
    es_puente_val = es_puente(fecha)
    
    # Interacciones con hora y puentes
    hora_apertura_fin_semana = es_hora_apertura * es_fin_de_semana
    hora_pico_puente = es_hora_pico * es_puente_val
    puente_fin_semana = es_puente_val * es_fin_de_semana
    
    # Meses
    es_mes_dict = {i: 1 if mes == i else 0 for i in range(1, 13)}
    
    # Temporada
    temporada = get_temporada(mes)
    
    # Features cíclicas
    hora_sin = np.sin(2 * np.pi * hora / 24)
    hora_cos = np.cos(2 * np.pi * hora / 24)
    mes_sin = np.sin(2 * np.pi * mes / 12)
    mes_cos = np.cos(2 * np.pi * mes / 12)
    dia_semana_sin = np.sin(2 * np.pi * dia_semana_num / 7)
    dia_semana_cos = np.cos(2 * np.pi * dia_semana_num / 7)
    dia_mes_sin = np.sin(2 * np.pi * dia_mes / 31)
    dia_mes_cos = np.cos(2 * np.pi * dia_mes / 31)
    semana_año_sin = np.sin(2 * np.pi * semana_año / 52)
    semana_año_cos = np.cos(2 * np.pi * semana_año / 52)
    
    # Interacciones
    hora_mes = hora * mes
    hora_dia_semana = hora * dia_semana_num
    mes_dia_semana = mes * dia_semana_num
    fin_semana_mes = es_fin_de_semana * mes
    temporada_dia_semana = temporada * dia_semana_num
    
    # Clima
    temperatura = input_dict.get("temperatura", df_train["temperatura"].median() if "temperatura" in df_train.columns else 20)
    humedad = input_dict.get("humedad", df_train["humedad"].median() if "humedad" in df_train.columns else 60)
    sensacion_termica = input_dict.get("sensacion_termica", temperatura)
    codigo_clima = input_dict.get("codigo_clima", 3)
    es_buen_clima = 1 if codigo_clima in [1, 2, 3] else 0
    es_mal_clima = 1 if codigo_clima > 3 else 0
    
    # Atracción y zona
    atraccion = input_dict.get("atraccion", "")
    zona = input_dict.get("zona", "")
    
    # Features históricas
    global_median = df_train["tiempo_espera"].median()
    global_mean = df_train["tiempo_espera"].mean()
    
    hist_mes_row = hist_mes[(hist_mes["atraccion"] == atraccion) & (hist_mes["mes"] == mes)]
    hist_hora_row = hist_hora[(hist_hora["atraccion"] == atraccion) & (hist_hora["hora"] == int(hora))]
    hist_dia_row = hist_dia_semana[(hist_dia_semana["atraccion"] == atraccion) & (hist_dia_semana["dia_semana_num"] == dia_semana_num)]
    hist_mes_dia_row = hist_mes_dia[(hist_mes_dia["atraccion"] == atraccion) & (hist_mes_dia["mes"] == mes) & (hist_mes_dia["dia_semana_num"] == dia_semana_num)]
    hist_hora_dia_row = hist_hora_dia[(hist_hora_dia["atraccion"] == atraccion) & (hist_hora_dia["hora"] == int(hora)) & (hist_hora_dia["dia_semana_num"] == dia_semana_num)]
    hist_mes_hora_row = hist_mes_hora[(hist_mes_hora["atraccion"] == atraccion) & (hist_mes_hora["mes"] == mes) & (hist_mes_hora["hora"] == int(hora))]
    
    count_mes = hist_mes_row["count_mes"].values[0] if not hist_mes_row.empty else 0
    mean_mes = hist_mes_row["mean_mes"].values[0] if not hist_mes_row.empty else global_mean
    median_mes = hist_mes_row["median_mes"].values[0] if not hist_mes_row.empty else global_median
    std_mes = hist_mes_row["std_mes"].values[0] if not hist_mes_row.empty else df_train["tiempo_espera"].std()
    p75_mes = hist_mes_row["p75_mes"].values[0] if not hist_mes_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    p90_mes = hist_mes_row["p90_mes"].values[0] if not hist_mes_row.empty else np.percentile(df_train["tiempo_espera"], 90)
    p95_mes = hist_mes_row["p95_mes"].values[0] if not hist_mes_row.empty else np.percentile(df_train["tiempo_espera"], 95)
    
    count_hora = hist_hora_row["count_hora"].values[0] if not hist_hora_row.empty else 0
    mean_hora = hist_hora_row["mean_hora"].values[0] if not hist_hora_row.empty else global_mean
    median_hora = hist_hora_row["median_hora"].values[0] if not hist_hora_row.empty else global_median
    std_hora = hist_hora_row["std_hora"].values[0] if not hist_hora_row.empty else df_train["tiempo_espera"].std()
    p75_hora = hist_hora_row["p75_hora"].values[0] if not hist_hora_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    p90_hora = hist_hora_row["p90_hora"].values[0] if not hist_hora_row.empty else np.percentile(df_train["tiempo_espera"], 90)
    
    count_dia = hist_dia_row["count_dia"].values[0] if not hist_dia_row.empty else 0
    mean_dia = hist_dia_row["mean_dia"].values[0] if not hist_dia_row.empty else global_mean
    median_dia = hist_dia_row["median_dia"].values[0] if not hist_dia_row.empty else global_median
    std_dia = hist_dia_row["std_dia"].values[0] if not hist_dia_row.empty else df_train["tiempo_espera"].std()
    p75_dia = hist_dia_row["p75_dia"].values[0] if not hist_dia_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    p90_dia = hist_dia_row["p90_dia"].values[0] if not hist_dia_row.empty else np.percentile(df_train["tiempo_espera"], 90)
    
    count_mes_dia = hist_mes_dia_row["count_mes_dia"].values[0] if not hist_mes_dia_row.empty else 0
    mean_mes_dia = hist_mes_dia_row["mean_mes_dia"].values[0] if not hist_mes_dia_row.empty else global_mean
    median_mes_dia = hist_mes_dia_row["median_mes_dia"].values[0] if not hist_mes_dia_row.empty else global_median
    p75_mes_dia = hist_mes_dia_row["p75_mes_dia"].values[0] if not hist_mes_dia_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    p90_mes_dia = hist_mes_dia_row["p90_mes_dia"].values[0] if not hist_mes_dia_row.empty else np.percentile(df_train["tiempo_espera"], 90)
    
    count_hora_dia = hist_hora_dia_row["count_hora_dia"].values[0] if not hist_hora_dia_row.empty else 0
    mean_hora_dia = hist_hora_dia_row["mean_hora_dia"].values[0] if not hist_hora_dia_row.empty else global_mean
    median_hora_dia = hist_hora_dia_row["median_hora_dia"].values[0] if not hist_hora_dia_row.empty else global_median
    p75_hora_dia = hist_hora_dia_row["p75_hora_dia"].values[0] if not hist_hora_dia_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    
    count_mes_hora = hist_mes_hora_row["count_mes_hora"].values[0] if not hist_mes_hora_row.empty else 0
    mean_mes_hora = hist_mes_hora_row["mean_mes_hora"].values[0] if not hist_mes_hora_row.empty else global_mean
    median_mes_hora = hist_mes_hora_row["median_mes_hora"].values[0] if not hist_mes_hora_row.empty else global_median
    p75_mes_hora = hist_mes_hora_row["p75_mes_hora"].values[0] if not hist_mes_hora_row.empty else np.percentile(df_train["tiempo_espera"], 75)
    
    # Flags especiales
    is_batman_octubre = 1 if ("Batman" in atraccion and mes == 10) else 0
    is_octubre = 1 if mes == 10 else 0
    is_noviembre = 1 if mes == 11 else 0
    is_octubre_fin_semana = 1 if (mes == 10 and es_fin_de_semana == 1) else 0
    is_noviembre_fin_semana = 1 if (mes == 11 and es_fin_de_semana == 1) else 0
    
    # Encoding categórico
    zona_enc = encoding_maps.get("zona", {}).get(zona, global_mean) if "zona" in encoding_maps else global_mean
    atraccion_enc = encoding_maps.get("atraccion", {}).get(atraccion, global_mean) if "atraccion" in encoding_maps else global_mean
    
    # Construir el vector de features
    feature_dict = {
        "hora": hora,
        "mes": mes,
        "dia_mes": dia_mes,
        "dia_semana_num": dia_semana_num,
        "semana_año": semana_año,
        "trimestre": trimestre,
        "año": año,
        "es_lunes": es_lunes,
        "es_martes": es_martes,
        "es_miercoles": es_miercoles,
        "es_jueves": es_jueves,
        "es_viernes": es_viernes,
        "es_sabado": es_sabado,
        "es_domingo": es_domingo,
        "es_fin_de_semana": es_fin_de_semana,
        "es_dia_laborable": es_dia_laborable,
        **{f"es_mes_{i}": es_mes_dict[i] for i in range(1, 13)},
        "temporada": temporada,
        "hora_sin": hora_sin,
        "hora_cos": hora_cos,
        "mes_sin": mes_sin,
        "mes_cos": mes_cos,
        "dia_semana_sin": dia_semana_sin,
        "dia_semana_cos": dia_semana_cos,
        "dia_mes_sin": dia_mes_sin,
        "dia_mes_cos": dia_mes_cos,
        "semana_año_sin": semana_año_sin,
        "semana_año_cos": semana_año_cos,
        "hora_mes": hora_mes,
        "hora_dia_semana": hora_dia_semana,
        "mes_dia_semana": mes_dia_semana,
        "fin_semana_mes": fin_semana_mes,
        "temporada_dia_semana": temporada_dia_semana,
        "temperatura": temperatura,
        "humedad": humedad,
        "sensacion_termica": sensacion_termica,
        "codigo_clima": codigo_clima,
        "es_buen_clima": es_buen_clima,
        "es_mal_clima": es_mal_clima,
        "count_mes": count_mes,
        "mean_mes": mean_mes,
        "median_mes": median_mes,
        "std_mes": std_mes,
        "p75_mes": p75_mes,
        "p90_mes": p90_mes,
        "p95_mes": p95_mes,
        "count_hora": count_hora,
        "mean_hora": mean_hora,
        "median_hora": median_hora,
        "std_hora": std_hora,
        "p75_hora": p75_hora,
        "p90_hora": p90_hora,
        "count_dia": count_dia,
        "mean_dia": mean_dia,
        "median_dia": median_dia,
        "std_dia": std_dia,
        "p75_dia": p75_dia,
        "p90_dia": p90_dia,
        "count_mes_dia": count_mes_dia,
        "mean_mes_dia": mean_mes_dia,
        "median_mes_dia": median_mes_dia,
        "p75_mes_dia": p75_mes_dia,
        "p90_mes_dia": p90_mes_dia,
        "count_hora_dia": count_hora_dia,
        "mean_hora_dia": mean_hora_dia,
        "median_hora_dia": median_hora_dia,
        "p75_hora_dia": p75_hora_dia,
        "count_mes_hora": count_mes_hora,
        "mean_mes_hora": mean_mes_hora,
        "median_mes_hora": median_mes_hora,
        "p75_mes_hora": p75_mes_hora,
        "is_batman_octubre": is_batman_octubre,
        "is_octubre": is_octubre,
        "is_noviembre": is_noviembre,
        "is_octubre_fin_semana": is_octubre_fin_semana,
        "is_noviembre_fin_semana": is_noviembre_fin_semana,
        "hora_int": hora_int,
        "es_hora_apertura": es_hora_apertura,
        "es_hora_pico": es_hora_pico,
        "es_hora_valle_manana": es_hora_valle_manana,
        "es_hora_valle_tarde": es_hora_valle_tarde,
        "es_hora_valle": es_hora_valle,
        "es_festivo": es_festivo_val,
        "es_puente": es_puente_val,
        "hora_apertura_fin_semana": hora_apertura_fin_semana,
        "hora_pico_puente": hora_pico_puente,
        "puente_fin_semana": puente_fin_semana,
        "zona_enc": zona_enc,
        "atraccion_enc": atraccion_enc,
    }
    
    # Añadir frecuencias si existen
    if "zona_freq" in columnas_entrenamiento:
        zona_freq_map = df_train["zona"].value_counts().to_dict() if "zona" in df_train.columns else {}
        feature_dict["zona_freq"] = zona_freq_map.get(zona, 0)
    if "atraccion_freq" in columnas_entrenamiento:
        atraccion_freq_map = df_train["atraccion"].value_counts().to_dict() if "atraccion" in df_train.columns else {}
        feature_dict["atraccion_freq"] = atraccion_freq_map.get(atraccion, 0)
    
    # Crear DataFrame y asegurar el mismo orden de columnas
    df_features = pd.DataFrame([feature_dict])
    
    # Asegurar que todas las columnas estén presentes
    for col in columnas_entrenamiento:
        if col not in df_features.columns:
            df_features[col] = 0
    
    # Reordenar columnas
    df_features = df_features[columnas_entrenamiento]
    
    # Escalar
    X_scaled = scaler.transform(df_features)
    
    return X_scaled

def predict_wait_time(input_dict, artifacts=None):
    """
    Función principal para predecir tiempo de espera.
    
    Args:
        input_dict: Diccionario con los datos de entrada:
            - fecha: "YYYY-MM-DD"
            - hora: "HH:MM:SS" o "HH:MM"
            - atraccion: nombre de la atracción
            - zona: zona del parque
            - temperatura: temperatura en grados
            - humedad: humedad relativa
            - sensacion_termica: sensación térmica
            - codigo_clima: código del clima (1-5)
        artifacts: Diccionario con los artefactos del modelo (opcional, se cargan si no se proporciona)
    
    Returns:
        Diccionario con la predicción y detalles
    """
    if artifacts is None:
        artifacts = load_model_artifacts()
    
    model = artifacts["model"]
    df_train = artifacts["df_processed"]
    
    # Predicción base del modelo (ESTA ES LA CLAVE - tiene hora, día del mes, etc.)
    X_pred = prepare_input_for_prediction(input_dict, artifacts)
    pred_base = float(model.predict(X_pred)[0])
    
    # Extraer información del input
    fecha = pd.to_datetime(input_dict["fecha"], errors="coerce")
    if pd.isna(fecha):
        fecha = pd.Timestamp.now()
    
    mes = fecha.month
    dia_mes = fecha.day
    dia_semana = fecha.weekday()
    es_fin_de_semana = 1 if dia_semana in [5, 6] else 0
    atr = input_dict.get("atraccion", "")
    
    # Parsear hora para obtener hora exacta
    hora_str = input_dict.get("hora", "12:00:00")
    hora = parse_hora(hora_str)
    if pd.isna(hora):
        hora = 12.0
    hora_int = int(hora)
    
    # Usar históricos pre-calculados para verificar existencia, luego buscar en df_train
    hist_mes = artifacts["hist_mes"]
    hist_hora = artifacts["hist_hora"]
    hist_dia_semana = artifacts["hist_dia_semana"]
    hist_mes_dia = artifacts["hist_mes_dia"]
    hist_hora_dia = artifacts["hist_hora_dia"]
    hist_mes_hora = artifacts["hist_mes_hora"]
    global_median = df_train["tiempo_espera"].median()
    
    # Verificar existencia en históricos pre-calculados
    tiene_mes_hora_dia = not hist_mes_hora[(hist_mes_hora["atraccion"] == atr) & (hist_mes_hora["mes"] == mes) & (hist_mes_hora["hora"] == hora_int)].empty and \
                         not hist_mes_dia[(hist_mes_dia["atraccion"] == atr) & (hist_mes_dia["mes"] == mes) & (hist_mes_dia["dia_semana_num"] == dia_semana)].empty
    tiene_hora_dia = not hist_hora_dia[(hist_hora_dia["atraccion"] == atr) & (hist_hora_dia["hora"] == hora_int) & (hist_hora_dia["dia_semana_num"] == dia_semana)].empty
    tiene_mes_hora = not hist_mes_hora[(hist_mes_hora["atraccion"] == atr) & (hist_mes_hora["mes"] == mes) & (hist_mes_hora["hora"] == hora_int)].empty
    tiene_hora = not hist_hora[(hist_hora["atraccion"] == atr) & (hist_hora["hora"] == hora_int)].empty
    
    # Si no hay datos exactos por hora, buscar en rango cercano
    if not tiene_hora and hora_int > 0:
        for h in [hora_int-1, hora_int+1]:
            if 0 <= h < 24:
                if not hist_hora[(hist_hora["atraccion"] == atr) & (hist_hora["hora"] == h)].empty:
                    hora_int = h
                    tiene_hora = True
                    break
    
    # PRIORIZAR históricos que incluyen HORA - buscar directamente en df_train
    if tiene_mes_hora_dia:
        # Lo más específico: mes + hora + día de semana
        hist_ref = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes) & (df_train["hora"].astype(int) == hora_int) & (df_train["dia_semana_num"] == dia_semana)]
        especificidad = "mes_hora_dia"
    elif tiene_hora_dia:
        # Hora + día de semana
        hist_ref = df_train[(df_train["atraccion"] == atr) & (df_train["hora"].astype(int) == hora_int) & (df_train["dia_semana_num"] == dia_semana)]
        especificidad = "hora_dia"
    elif tiene_mes_hora:
        # Mes + hora
        hist_ref = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes) & (df_train["hora"].astype(int) == hora_int)]
        especificidad = "mes_hora"
    elif tiene_hora:
        # Solo hora (muy importante para variación horaria)
        hist_ref = df_train[(df_train["atraccion"] == atr) & (df_train["hora"].astype(int) == hora_int)]
        especificidad = "hora"
    else:
        # Buscar sin hora
        hist_mes_dia_ref = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes) & (df_train["dia_semana_num"] == dia_semana)]
        hist_dia_ref = df_train[(df_train["atraccion"] == atr) & (df_train["dia_semana_num"] == dia_semana)]
        hist_mes_ref = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes)]
        
        if not hist_mes_dia_ref.empty:
            hist_ref = hist_mes_dia_ref
            especificidad = "mes_dia"
        elif not hist_dia_ref.empty:
            hist_ref = hist_dia_ref
            especificidad = "dia"
        elif not hist_mes_ref.empty:
            hist_ref = hist_mes_ref
            especificidad = "mes"
        else:
            hist_ref = pd.DataFrame()
            especificidad = "global"
    
    # Calcular estadísticas del histórico más específico disponible
    if not hist_ref.empty:
        p75_hist = hist_ref["tiempo_espera"].quantile(0.75)
        median_hist = hist_ref["tiempo_espera"].median()
        p90_hist = hist_ref["tiempo_espera"].quantile(0.90)
        count_hist = len(hist_ref)
    else:
        p75_hist = global_median
        median_hist = global_median
        p90_hist = global_median
        count_hist = 0
    
    # Determinar tipo de hora del día
    es_hora_apertura = (hora_int >= 10 and hora_int < 11)
    es_hora_pico = (hora_int >= 11 and hora_int <= 16)
    es_hora_valle = (hora_int < 10 or hora_int > 18)
    
    # Detectar puente/festivo
    es_puente_val = es_puente(fecha)
    
    # PRIORIZAR históricos por hora - si tenemos datos específicos por hora, usarlos directamente
    # Si tenemos histórico por hora específica, usarlo como base principal
    if especificidad in ["mes_hora_dia", "hora_dia", "mes_hora", "hora"]:
        # Tenemos datos por hora - usar histórico como base y ajustar con modelo
        if not hist_ref.empty:
            # Usar percentil 50 (mediana) o 75 según contexto
            if es_hora_apertura:
                # Hora de apertura: usar percentil más bajo (25 o mediana)
                hist_base = hist_ref["tiempo_espera"].quantile(0.25) if len(hist_ref) > 10 else median_hist
                peso_historico = 0.80  # Más peso al histórico en apertura
                peso_modelo = 0.20
            elif es_hora_pico:
                # Hora pico: usar percentil 75
                hist_base = p75_hist
                # DETECTAR HISTÓRICOS SOSPECHOSAMENTE BAJOS
                # Si el histórico es muy bajo para hora pico, buscar alternativas
                if p75_hist < 15 and count_hist < 20:  # Histórico sospechosamente bajo
                    # Buscar histórico menos específico pero más confiable
                    hist_mes_dia_alt = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes) & (df_train["dia_semana_num"] == dia_semana)]
                    hist_mes_alt = df_train[(df_train["atraccion"] == atr) & (df_train["mes"] == mes)]
                    
                    if not hist_mes_dia_alt.empty:
                        p75_alt = hist_mes_dia_alt["tiempo_espera"].quantile(0.75)
                        if p75_alt > p75_hist:
                            hist_base = p75_alt
                            especificidad = "mes_dia_fallback"
                    elif not hist_mes_alt.empty:
                        p75_alt = hist_mes_alt["tiempo_espera"].quantile(0.75)
                        if p75_alt > p75_hist:
                            hist_base = p75_alt
                            especificidad = "mes_fallback"
                    
                    # Si aún es bajo, confiar más en el modelo
                    if hist_base < 15:
                        peso_historico = 0.30
                        peso_modelo = 0.70
                    else:
                        peso_historico = 0.50
                        peso_modelo = 0.50
                else:
                    peso_historico = 0.70
                    peso_modelo = 0.30
            else:
                # Hora valle: usar mediana
                hist_base = median_hist
                peso_historico = 0.75
                peso_modelo = 0.25
        else:
            hist_base = median_hist
            peso_historico = 0.60
            peso_modelo = 0.40
    else:
        # No tenemos datos por hora - usar modelo más y ajustar con histórico general
        hist_base = p75_hist if es_hora_pico else median_hist
        peso_historico = 0.40
        peso_modelo = 0.60
    
    # Calcular predicción base combinada
    pred_combinada = pred_base * peso_modelo + hist_base * peso_historico
    
    # AJUSTES ESPECIALES POR CONTEXTO
    if es_hora_apertura:
        # HORA DE APERTURA: Reducir significativamente (el parque acaba de abrir)
        if es_fin_de_semana:
            minutos_final = pred_combinada * 0.50  # Reducción del 50% en fin de semana
        else:
            minutos_final = pred_combinada * 0.60  # Reducción del 40% en laborable
        ajuste = f"apertura_{especificidad}"
    elif "Batman" in atr and mes == 10:
        # Batman octubre: boost especial más agresivo, especialmente en fin de semana
        if es_fin_de_semana:
            # Fin de semana en octubre (sábado o domingo) - boost muy agresivo
            if es_hora_pico:
                # Hora pico + fin de semana + octubre = máximo boost
                # Si el histórico es sospechosamente bajo, confiar más en el modelo base
                if p75_hist < 15 or hist_base < 15:
                    # Histórico bajo: usar modelo base con boost agresivo
                    minutos_final = max(pred_base * 1.50, pred_combinada * 1.40, 25.0)  # Mínimo 25 minutos
                else:
                    # Histórico confiable: combinar modelo e histórico
                    minutos_final = max(pred_combinada * 1.30, p75_hist * 1.25, hist_base * 1.35, pred_base * 1.25)
            else:
                # Fin de semana pero no hora pico
                if hist_base < 10:
                    minutos_final = max(pred_base * 1.30, pred_combinada * 1.20, 15.0)
                else:
                    minutos_final = max(pred_combinada * 1.20, hist_base * 1.25)
        else:
            # Día laborable en octubre
            if es_hora_pico:
                if hist_base < 15:
                    minutos_final = max(pred_base * 1.35, pred_combinada * 1.25, 20.0)
                else:
                    minutos_final = max(pred_combinada * 1.15, hist_base * 1.20)
            else:
                minutos_final = max(pred_combinada * 1.10, hist_base * 1.15)
        ajuste = f"batman_octubre_{'fin_semana' if es_fin_de_semana else 'laborable'}_{especificidad}"
    elif es_puente_val:
        # PUENTE: Aumentar afluencia (especialmente si es fin de semana)
        if es_fin_de_semana:
            minutos_final = pred_combinada * 1.15
        else:
            minutos_final = pred_combinada * 1.10
        ajuste = f"puente_{especificidad}"
    elif mes == 10 and dia_semana == 6:  # Octubre Domingo
        if es_hora_pico:
            minutos_final = pred_combinada * 1.10
        else:
            minutos_final = pred_combinada
        ajuste = f"octubre_domingo_{especificidad}"
    elif mes == 11 and dia_semana == 6:  # Noviembre Domingo
        if es_hora_pico:
            minutos_final = pred_combinada * 1.08
        else:
            minutos_final = pred_combinada
        ajuste = f"noviembre_domingo_{especificidad}"
    elif es_hora_pico:
        # Hora pico en general
        minutos_final = pred_combinada * 1.05
        ajuste = f"hora_pico_{especificidad}"
    elif es_hora_valle:
        # Hora valle - menos afluencia
        minutos_final = pred_combinada * 0.90
        ajuste = f"hora_valle_{especificidad}"
    elif es_fin_de_semana:
        minutos_final = pred_combinada
        ajuste = f"fin_semana_{especificidad}"
    else:
        minutos_final = pred_combinada
        ajuste = f"laborable_{especificidad}"
    
    # Asegurar límites razonables
    minutos_final = max(5, min(180, minutos_final))
    
    return {
        "minutos_predichos": round(minutos_final, 1),
        "prediccion_base": round(pred_base, 1),
        "p75_historico": round(p75_hist, 1),
        "median_historico": round(median_hist, 1),
        "ajuste_aplicado": ajuste,
        "especificidad_historico": especificidad,
        "hora": round(hora, 2),
        "hora_int": hora_int,
        "es_hora_apertura": es_hora_apertura,
        "es_hora_pico": es_hora_pico,
        "es_hora_valle": es_hora_valle,
        "es_puente": bool(es_puente_val),
        "es_batman_octubre": ("Batman" in atr and mes == 10),
        "mes": mes,
        "dia_mes": dia_mes,
        "dia_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dia_semana],
        "es_fin_de_semana": bool(es_fin_de_semana),
        "count_historico": count_hist
    }

# Ejemplo de uso
if __name__ == "__main__":
    print("=" * 70)
    print("🎯 EJEMPLO DE PREDICCIÓN")
    print("=" * 70)
    
    # Cargar artefactos una vez
    artifacts = load_model_artifacts()
    
    # Ejemplos de predicción
    tests = [
        {
            "name": "Batman Octubre Sábado",
            "input": {
                "temperatura": 22,
                "humedad": 60,
                "sensacion_termica": 22,
                "codigo_clima": 3,
                "hora": "12:15:00",
                "zona": "DC Super Heroes World",
                "atraccion": "Batman Gotham City Escape",
                "fecha": "2025-10-25"
            }
        },
        {
            "name": "Batman Octubre Domingo",
            "input": {
                "temperatura": 22,
                "humedad": 60,
                "sensacion_termica": 22,
                "codigo_clima": 3,
                "hora": "12:15:00",
                "zona": "DC Super Heroes World",
                "atraccion": "Batman Gotham City Escape",
                "fecha": "2025-10-26"
            }
        },
        {
            "name": "Batman Noviembre Sábado",
            "input": {
                "temperatura": 22,
                "humedad": 60,
                "sensacion_termica": 22,
                "codigo_clima": 3,
                "hora": "12:15:00",
                "zona": "DC Super Heroes World",
                "atraccion": "Batman Gotham City Escape",
                "fecha": "2025-11-01"
            }
        },
        {
            "name": "Batman Noviembre Domingo",
            "input": {
                "temperatura": 22,
                "humedad": 60,
                "sensacion_termica": 22,
                "codigo_clima": 3,
                "hora": "12:15:00",
                "zona": "DC Super Heroes World",
                "atraccion": "Batman Gotham City Escape",
                "fecha": "2025-11-02"
            }
        }
    ]
    
    for test in tests:
        res = predict_wait_time(test["input"], artifacts)
        print(f"\n🎯 {test['name']}:")
        print(f"   📅 Fecha: {test['input']['fecha']} ({res['dia_semana']}, día {res['dia_mes']})")
        print(f"   🕐 Hora: {test['input']['hora']} (hora pico: {res['es_hora_pico']})")
        print(f"   ⏱️  Predicción: {res['minutos_predichos']} minutos")
        print(f"   🔢 Base modelo: {res['prediccion_base']} minutos")
        print(f"   📊 P75 histórico: {res['p75_historico']} minutos")
        print(f"   🎯 Ajuste: {res['ajuste_aplicado']}")
        print(f"   📈 Especificidad: {res['especificidad_historico']}")
    
    # Test adicional: mostrar cómo cambia con diferentes horas
    print("\n" + "=" * 70)
    print("🕐 TEST DE VARIACIÓN POR HORA (Mismo día)")
    print("=" * 70)
    
    test_horas = [
        {"hora": "10:00:00", "name": "10:00 (Valle)"},
        {"hora": "12:00:00", "name": "12:00 (Pico)"},
        {"hora": "15:00:00", "name": "15:00 (Pico)"},
        {"hora": "18:00:00", "name": "18:00 (Valle)"},
        {"hora": "20:00:00", "name": "20:00 (Valle)"}
    ]
    
    for test_hora in test_horas:
        input_test = {
            "temperatura": 22,
            "humedad": 60,
            "sensacion_termica": 22,
            "codigo_clima": 3,
            "hora": test_hora["hora"],
            "zona": "DC Super Heroes World",
            "atraccion": "Batman Gotham City Escape",
            "fecha": "2025-11-02"  # Domingo
        }
        res = predict_wait_time(input_test, artifacts)
        print(f"\n🕐 {test_hora['name']}:")
        print(f"   ⏱️  Predicción: {res['minutos_predichos']} min (Base: {res['prediccion_base']:.1f} min)")
        print(f"   📊 Histórico: {res['p75_historico']:.1f} min ({res['especificidad_historico']})")
    
    # Test adicional: mostrar cómo cambia con diferentes días del mes
    print("\n" + "=" * 70)
    print("📅 TEST DE VARIACIÓN POR DÍA DEL MES (Mismo mes y día de semana)")
    print("=" * 70)
    
    test_dias = [
        {"fecha": "2025-11-02", "name": "Domingo 2 Nov"},
        {"fecha": "2025-11-09", "name": "Domingo 9 Nov"},
        {"fecha": "2025-11-16", "name": "Domingo 16 Nov"},
        {"fecha": "2025-11-23", "name": "Domingo 23 Nov"},
        {"fecha": "2025-11-30", "name": "Domingo 30 Nov"}
    ]
    
    for test_dia in test_dias:
        input_test = {
            "temperatura": 22,
            "humedad": 60,
            "sensacion_termica": 22,
            "codigo_clima": 3,
            "hora": "12:00:00",
            "zona": "DC Super Heroes World",
            "atraccion": "Batman Gotham City Escape",
            "fecha": test_dia["fecha"]
        }
        res = predict_wait_time(input_test, artifacts)
        print(f"\n📅 {test_dia['name']} (día {res['dia_mes']}):")
        print(f"   ⏱️  Predicción: {res['minutos_predichos']} min (Base: {res['prediccion_base']:.1f} min)")
        print(f"   📊 Histórico: {res['p75_historico']:.1f} min ({res['especificidad_historico']})")


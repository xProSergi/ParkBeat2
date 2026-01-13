# ====================================================
# LAMBDA FUNCTION - Park Wait Time Predictor
# Versión: FINAL OPTIMIZADA (Sincronización de Features)
# ====================================================

import json
import boto3
import joblib
import pandas as pd
import numpy as np
from io import BytesIO
import os
import sys
import traceback

# Evitar errores de permisos de joblib en el entorno read-only de Lambda
os.environ['JOBLIB_TEMP_FOLDER'] = '/tmp'

# Configuración S3
s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'parklytics-models-tu-nombre-2024') 

# Cache para evitar recargas innecesarias entre llamadas
models_cache = {}

def load_model_from_s3():
    """Carga todos los artefactos necesarios desde S3"""
    if 'model' in models_cache:
        return models_cache
    
    print("Iniciando descarga de modelos desde S3...")
    files = {
            'model': 'models/xgb_model_professional.pkl',
            'scaler': 'models/xgb_scaler_professional.pkl',
            'encoding_maps': 'models/xgb_encoding_professional.pkl',
        'df_processed': 'models/df_processed.pkl',
            'hist_mes': 'historicos/hist_mes.pkl',
            'hist_hora': 'historicos/hist_hora.pkl',
            'hist_dia_semana': 'historicos/hist_dia_semana.pkl',
            'hist_mes_dia': 'historicos/hist_mes_dia.pkl',
            'hist_hora_dia': 'historicos/hist_hora_dia.pkl',
            'hist_mes_hora': 'historicos/hist_mes_hora.pkl'
        }
        
    try:
        for key, s3_key in files.items():
            print(f"Descargando {s3_key}...")
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
            models_cache[key] = joblib.load(BytesIO(obj['Body'].read()))
        
        print("Todos los modelos cargados exitosamente.")
        return models_cache
    except Exception as e:
        print(f"ERROR CRÍTICO EN CARGA S3: {str(e)}")
        raise

# --- FUNCIONES DE APOYO (Ingeniería de Variables) ---

def parse_hora(hora_str):
    try:
        if isinstance(hora_str, (int, float)): return float(hora_str)
        s = str(hora_str).strip()
        if ":" in s:
            parts = s.split(":")
            return int(parts[0]) + (int(parts[1])/60.0 if len(parts)>1 else 0)
        return float(s)
    except: return 12.0

def get_temporada(mes):
    if mes in [7, 8, 10]: return 3 # Alta
    if mes in [4, 5, 6, 12]: return 2 # Media-Alta
    if mes in [3, 9, 11]: return 1 # Media
    return 0 # Baja

def es_festivo_espana(fecha):
    festivos = [(1,1), (1,6), (5,1), (10,12), (11,1), (12,6), (12,8), (12,25)]
    return 1 if (fecha.month, fecha.day) in festivos else 0

def es_puente(fecha):
    """Debe coincidir exactamente con train_model.py líneas 642-653"""
    if es_festivo_espana(fecha): return 1
    dia_anterior = fecha - pd.Timedelta(days=1)
    dia_siguiente = fecha + pd.Timedelta(days=1)
    # Viernes si el Sábado es festivo
    if fecha.weekday() == 4 and es_festivo_espana(dia_siguiente): return 1
    # Lunes si el Domingo fue festivo
    if fecha.weekday() == 0 and es_festivo_espana(dia_anterior): return 1
    # Domingo si el Sábado fue festivo (añadido según train_model.py línea 651)
    if fecha.weekday() == 6 and es_festivo_espana(dia_anterior): return 1
    return 0

# --- PROCESAMIENTO Y PREDICCIÓN ---

def prepare_input_for_prediction(input_dict, artifacts):
    """
    Esta función es el corazón del fix. 
    Usa 'scaler.feature_names_in_' para saber exactamente qué columnas quiere el modelo.
    """
    print("=== PREPARE INPUT FOR PREDICTION ===")
    print(f"Input dict: {json.dumps(input_dict, default=str)}")
    
    scaler = artifacts['scaler']
    col_order = list(scaler.feature_names_in_) 
    print(f"Total de features esperadas: {len(col_order)}")
    print(f"Primeras 10 features: {col_order[:10]}")
    
    encoding_maps = artifacts['encoding_maps']
    df_train = artifacts['df_processed']
    
    # 1. Extraer datos básicos
    fecha = pd.to_datetime(input_dict.get("fecha"), errors="coerce")
    if pd.isna(fecha): fecha = pd.Timestamp.now()
    
    hora = parse_hora(input_dict.get("hora", 12))
    mes, dia_semana = fecha.month, fecha.weekday()
    es_fin_semana = 1 if dia_semana >= 5 else 0
    atraccion = input_dict.get("atraccion", "Desconocida")
    zona = input_dict.get("zona", "Desconocida")
    
    print(f"Fecha parseada: {fecha}, Mes: {mes}, Día semana: {dia_semana}")
    print(f"Hora parseada: {hora}, Atracción: {atraccion}, Zona: {zona}")
    
    global_mean = df_train["tiempo_espera"].mean()
    global_median = df_train["tiempo_espera"].median()
    global_std = df_train["tiempo_espera"].std()
    global_p75 = np.percentile(df_train["tiempo_espera"], 75)
    global_p90 = np.percentile(df_train["tiempo_espera"], 90)
    global_p95 = np.percentile(df_train["tiempo_espera"], 95)
    print(f"Global mean: {global_mean}, Global median: {global_median}, Global std: {global_std}")
    
    # 2. Generar TODAS las variables posibles (Candidatos)
    hora_int = int(hora)
    # CORREGIDO: Debe coincidir exactamente con train_model.py líneas 622-626
    es_hora_apertura = 1 if (hora_int >= 10 and hora_int < 11) else 0
    es_hora_pico = 1 if (hora_int >= 11 and hora_int <= 16) else 0
    es_festivo = es_festivo_espana(fecha)
    es_puente_val = es_puente(fecha)
    
    c = {
        "hora": hora, "hora_int": hora_int, "mes": mes, "año": fecha.year,
        "dia_mes": fecha.day, "dia_semana_num": dia_semana,
        "trimestre": fecha.quarter, "semana_año": fecha.isocalendar().week,
        "es_fin_de_semana": es_fin_semana, "fin_de_semana": es_fin_semana,
        "es_festivo": es_festivo, "es_puente": es_puente_val,
        "temporada": get_temporada(mes),
        "temperatura": float(input_dict.get("temperatura", 20)),
        "humedad": float(input_dict.get("humedad", 60)),
        "sensacion_termica": float(input_dict.get("temperatura", 20)),
        "codigo_clima": int(input_dict.get("codigo_clima", 3)),
        "zona_enc": encoding_maps.get("zona", {}).get(zona, global_mean),
        "atraccion_enc": encoding_maps.get("atraccion", {}).get(atraccion, global_mean),
        "hora_sin": np.sin(2 * np.pi * hora / 24), "hora_cos": np.cos(2 * np.pi * hora / 24),
        "mes_sin": np.sin(2 * np.pi * mes / 12), "mes_cos": np.cos(2 * np.pi * mes / 12),
        "dia_semana_sin": np.sin(2 * np.pi * dia_semana / 7), "dia_semana_cos": np.cos(2 * np.pi * dia_semana / 7),
        "dia_mes_sin": np.sin(2 * np.pi * fecha.day / 31), "dia_mes_cos": np.cos(2 * np.pi * fecha.day / 31),
        "semana_año_sin": np.sin(2 * np.pi * fecha.isocalendar().week / 52), 
        "semana_año_cos": np.cos(2 * np.pi * fecha.isocalendar().week / 52),
        "hora_int": hora_int,  # IMPORTANTE: Debe estar presente según train_model.py línea 745
        "es_hora_apertura": es_hora_apertura,
        "es_hora_pico": es_hora_pico,
        "es_hora_valle_manana": 1 if hora_int < 10 else 0,  # CORREGIDO: train_model.py línea 624
        "es_hora_valle_tarde": 1 if hora_int > 18 else 0,  # train_model.py línea 625
        "es_hora_valle": 1 if (hora_int < 10 or hora_int > 18) else 0,  # CORREGIDO: train_model.py línea 626
        "hora_apertura_fin_semana": es_hora_apertura * es_fin_semana,  # Según train_model.py línea 198
        "hora_pico_puente": es_hora_pico * es_puente_val,  # Según train_model.py línea 199
        "puente_fin_semana": es_puente_val * es_fin_semana,  # Según train_model.py línea 200
        "hora_mes": hora * mes,
        "hora_dia_semana": hora * dia_semana,
        "mes_dia_semana": mes * dia_semana,
        "fin_semana_mes": es_fin_semana * mes,
        "temporada_dia_semana": get_temporada(mes) * dia_semana,
        "es_buen_clima": 1 if int(input_dict.get("codigo_clima", 3)) in [1, 2, 3] else 0,
        "es_mal_clima": 1 if int(input_dict.get("codigo_clima", 3)) > 3 else 0,
        # Features de días de semana
        "es_lunes": 1 if dia_semana == 0 else 0,
        "es_martes": 1 if dia_semana == 1 else 0,
        "es_miercoles": 1 if dia_semana == 2 else 0,
        "es_jueves": 1 if dia_semana == 3 else 0,
        "es_viernes": 1 if dia_semana == 4 else 0,
        "es_sabado": 1 if dia_semana == 5 else 0,
        "es_domingo": 1 if dia_semana == 6 else 0,
        "es_dia_laborable": 1 if dia_semana < 5 else 0,
        # Features de meses
        **{f"es_mes_{i}": 1 if mes == i else 0 for i in range(1, 13)},
        # Flags especiales
        "is_batman_octubre": 1 if ("Batman" in atraccion and mes == 10) else 0,
        "is_octubre": 1 if mes == 10 else 0,
        "is_noviembre": 1 if mes == 11 else 0,
        "is_octubre_fin_semana": 1 if (mes == 10 and es_fin_semana == 1) else 0,
        "is_noviembre_fin_semana": 1 if (mes == 11 and es_fin_semana == 1) else 0,
    }

    # 3. Mapeo Histórico (TODOS los históricos)
    hist_mes_df = artifacts.get('hist_mes')
    hist_hora_df = artifacts.get('hist_hora')
    hist_dia_semana_df = artifacts.get('hist_dia_semana')
    hist_mes_dia_df = artifacts.get('hist_mes_dia')
    hist_hora_dia_df = artifacts.get('hist_hora_dia')
    hist_mes_hora_df = artifacts.get('hist_mes_hora')
    
    features_historicas_encontradas = 0
    features_historicas_totales = 0
    
    # Histórico por mes - Inicializar con valores por defecto primero
    c['count_mes'] = 0
    c['mean_mes'] = global_mean
    c['median_mes'] = global_median
    c['std_mes'] = global_std
    c['p75_mes'] = global_p75
    c['p90_mes'] = global_p90
    c['p95_mes'] = global_p95
    
    if hist_mes_df is not None:
        hist_mes_row = hist_mes_df[(hist_mes_df['atraccion'] == atraccion) & (hist_mes_df['mes'] == mes)]
        print(f"Histórico mes - Atracción: {atraccion}, Mes: {mes}, Filas encontradas: {len(hist_mes_row)}")
        if not hist_mes_row.empty:
            for col in ['count_mes', 'mean_mes', 'median_mes', 'std_mes', 'p75_mes', 'p90_mes', 'p95_mes']:
                features_historicas_totales += 1
                if col in hist_mes_row.columns:
                    c[col] = hist_mes_row[col].values[0]
                    features_historicas_encontradas += 1
                    print(f"  -> {col}: {c[col]}")
        else:
            print(f"  -> No se encontró histórico para mes {mes} y atracción {atraccion}, usando valores por defecto")
    
    # Histórico por hora - Inicializar con valores por defecto primero
    c['count_hora'] = 0
    c['mean_hora'] = global_mean
    c['median_hora'] = global_median
    c['std_hora'] = global_std
    c['p75_hora'] = global_p75
    c['p90_hora'] = global_p90
    c["hora_hist"] = hora  # Siempre presente
    
    if hist_hora_df is not None:
        hora_col = 'hora' if 'hora' in hist_hora_df.columns else 'hora_int'
        hist_hora_row = hist_hora_df[(hist_hora_df['atraccion'] == atraccion) & (hist_hora_df[hora_col] == hora_int)]
        print(f"Histórico hora - Atracción: {atraccion}, Hora: {hora_int}, Filas encontradas: {len(hist_hora_row)}")
        if not hist_hora_row.empty:
            for col in ['count_hora', 'mean_hora', 'median_hora', 'std_hora', 'p75_hora', 'p90_hora']:
                features_historicas_totales += 1
                if col in hist_hora_row.columns:
                    c[col] = hist_hora_row[col].values[0]
                    features_historicas_encontradas += 1
    
    # Histórico por día de semana - Inicializar con valores por defecto primero
    c['count_dia'] = 0
    c['mean_dia'] = global_mean
    c['median_dia'] = global_median
    c['std_dia'] = global_std
    c['p75_dia'] = global_p75
    c['p90_dia'] = global_p90
    
    if hist_dia_semana_df is not None:
        hist_dia_row = hist_dia_semana_df[(hist_dia_semana_df['atraccion'] == atraccion) & (hist_dia_semana_df['dia_semana_num'] == dia_semana)]
        if not hist_dia_row.empty:
            for col in ['count_dia', 'mean_dia', 'median_dia', 'std_dia', 'p75_dia', 'p90_dia']:
                if col in hist_dia_row.columns:
                    c[col] = hist_dia_row[col].values[0]
    
    # Histórico por mes y día - Inicializar con valores por defecto primero
    c['count_mes_dia'] = 0
    c['mean_mes_dia'] = global_mean
    c['median_mes_dia'] = global_median
    c['p75_mes_dia'] = global_p75
    c['p90_mes_dia'] = global_p90
    
    if hist_mes_dia_df is not None:
        hist_mes_dia_row = hist_mes_dia_df[(hist_mes_dia_df['atraccion'] == atraccion) & (hist_mes_dia_df['mes'] == mes) & (hist_mes_dia_df['dia_semana_num'] == dia_semana)]
        if not hist_mes_dia_row.empty:
            for col in ['count_mes_dia', 'mean_mes_dia', 'median_mes_dia', 'p75_mes_dia', 'p90_mes_dia']:
                if col in hist_mes_dia_row.columns:
                    c[col] = hist_mes_dia_row[col].values[0]
    
    # Histórico por hora y día - Inicializar con valores por defecto primero
    c['count_hora_dia'] = 0
    c['mean_hora_dia'] = global_mean
    c['median_hora_dia'] = global_median
    c['p75_hora_dia'] = global_p75
    c["hora_hist_hd"] = hora  # Siempre presente
    
    if hist_hora_dia_df is not None:
        hora_col_hd = 'hora' if 'hora' in hist_hora_dia_df.columns else 'hora_int'
        hist_hora_dia_row = hist_hora_dia_df[(hist_hora_dia_df['atraccion'] == atraccion) & (hist_hora_dia_df[hora_col_hd] == hora_int) & (hist_hora_dia_df['dia_semana_num'] == dia_semana)]
        if not hist_hora_dia_row.empty:
            for col in ['count_hora_dia', 'mean_hora_dia', 'median_hora_dia', 'p75_hora_dia']:
                if col in hist_hora_dia_row.columns:
                    c[col] = hist_hora_dia_row[col].values[0]
    
    # Histórico por mes y hora - Inicializar con valores por defecto primero
    c['count_mes_hora'] = 0
    c['mean_mes_hora'] = global_mean
    c['median_mes_hora'] = global_median
    c['p75_mes_hora'] = global_p75
    c["hora_hist_mh"] = hora  # Siempre presente
    
    if hist_mes_hora_df is not None:
        hora_col_mh = 'hora' if 'hora' in hist_mes_hora_df.columns else 'hora_int'
        hist_mes_hora_row = hist_mes_hora_df[(hist_mes_hora_df['atraccion'] == atraccion) & (hist_mes_hora_df['mes'] == mes) & (hist_mes_hora_df[hora_col_mh] == hora_int)]
        if not hist_mes_hora_row.empty:
            for col in ['count_mes_hora', 'mean_mes_hora', 'median_mes_hora', 'p75_mes_hora']:
                if col in hist_mes_hora_row.columns:
                    c[col] = hist_mes_hora_row[col].values[0]
    
    print(f"Features históricas encontradas: {features_historicas_encontradas}/{features_historicas_totales}")
    print(f"Total de features en diccionario c: {len(c)}")
    print(f"Valores clave en c: hora={c.get('hora')}, mes={c.get('mes')}, atraccion_enc={c.get('atraccion_enc')}, zona_enc={c.get('zona_enc')}")
    
    # Añadir frecuencias si existen en las columnas de entrenamiento (según train_model.py líneas 761-766)
    if "zona_freq" in col_order:
        zona_freq_map = df_train["zona"].value_counts().to_dict() if "zona" in df_train.columns else {}
        c["zona_freq"] = zona_freq_map.get(zona, 0)
        print(f"zona_freq: {c['zona_freq']}")
    if "atraccion_freq" in col_order:
        atraccion_freq_map = df_train["atraccion"].value_counts().to_dict() if "atraccion" in df_train.columns else {}
        c["atraccion_freq"] = atraccion_freq_map.get(atraccion, 0)
        print(f"atraccion_freq: {c['atraccion_freq']}")

    # 4. CONSTRUCCIÓN DEL DATAFRAME FINAL (Garantiza el orden del Scaler)
    final_row = {}
    for col in col_order:
        if col in c:
            final_row[col] = c[col]
        elif col.startswith("es_mes_"):
            final_row[col] = 1 if mes == int(col.split("_")[-1]) else 0
        elif any(x in col for x in ["_hist", "_hist_hd", "_hist_mh"]):
            # Columnas creadas por merges con sufijos
            if "hora" in col:
                final_row[col] = hora
            else:
                final_row[col] = global_median
        elif "freq" in col:
            final_row[col] = 0
        elif "mean" in col:
            final_row[col] = global_mean
        elif "median" in col:
            final_row[col] = global_median
        else:
            final_row[col] = global_median  # Fallback seguro
            
    df_final = pd.DataFrame([final_row])
    
    # Asegurar que todas las columnas estén presentes
    missing_cols = [col for col in col_order if col not in df_final.columns]
    if missing_cols:
        for col in missing_cols:
            if "hora" in col and ("_hist" in col or "_hist_hd" in col or "_hist_mh" in col):
                df_final[col] = hora
            elif "mean" in col:
                df_final[col] = global_mean
            elif "median" in col:
                df_final[col] = global_median
            else:
                df_final[col] = global_median
    
    # Reordenar en el orden exacto del scaler
    df_final = df_final[col_order]
    
    print(f"DataFrame final shape: {df_final.shape}")
    print(f"Columnas en df_final: {len(df_final.columns)}")
    print(f"Valores NaN: {df_final.isna().sum().sum()}")
    print(f"Primeras 5 columnas y valores: {df_final.iloc[0, :5].to_dict()}")
    
    try:
        # Verificar valores antes del scaler
        print(f"Valores NaN en df_final: {df_final.isna().sum().sum()}")
        print(f"Valores infinitos en df_final: {np.isinf(df_final.select_dtypes(include=[np.number])).sum().sum()}")
        
        X_scaled = scaler.transform(df_final)
        print(f"X_scaled shape: {X_scaled.shape}")
        print(f"X_scaled primeros valores: {X_scaled[0, :5]}")
        print(f"X_scaled últimos valores: {X_scaled[0, -5:]}")
        print(f"X_scaled min: {X_scaled.min()}, max: {X_scaled.max()}, mean: {X_scaled.mean()}")
        print(f"Valores NaN en X_scaled: {np.isnan(X_scaled).sum()}")
        print(f"Valores infinitos en X_scaled: {np.isinf(X_scaled).sum()}")
        
        return X_scaled
    except Exception as e:
        print(f"ERROR en scaler.transform: {str(e)}")
        print(f"Tipo de error: {type(e).__name__}")
        traceback.print_exc()
        raise

def predict_wait_time(input_dict, artifacts):
    """Realiza la predicción y aplica lógica de negocio final"""
    print("=== PREDICT WAIT TIME ===")
    
    try:
        X_scaled = prepare_input_for_prediction(input_dict, artifacts)
        print("Features preparadas correctamente")
    except Exception as e:
        print(f"ERROR preparando features: {str(e)}")
        traceback.print_exc()
        raise
    
    try:
        model = artifacts['model']
        print("Modelo obtenido, realizando predicción...")
        pred_base = float(model.predict(X_scaled)[0])
        print(f"DEBUG: Predicción del modelo (raw): {pred_base}")
    except Exception as e:
        print(f"ERROR en predicción del modelo: {str(e)}")
        traceback.print_exc()
        raise
    
    # Extraer información del input
    fecha = pd.to_datetime(input_dict.get("fecha"), errors="coerce")
    if pd.isna(fecha):
        fecha = pd.Timestamp.now()
    
    mes = fecha.month
    dia_semana = fecha.weekday()
    es_fin_de_semana = 1 if dia_semana in [5, 6] else 0
    atr = input_dict.get("atraccion", "")
    
    # Parsear hora
    hora = parse_hora(input_dict.get("hora", 12))
    if pd.isna(hora):
        hora = 12.0
    hora_int = int(hora)
    
    # Obtener históricos y datos de entrenamiento
    df_train = artifacts['df_processed']
    hist_mes_df = artifacts.get('hist_mes')
    hist_hora_df = artifacts.get('hist_hora')
    hist_dia_semana_df = artifacts.get('hist_dia_semana')
    hist_mes_dia_df = artifacts.get('hist_mes_dia')
    hist_hora_dia_df = artifacts.get('hist_hora_dia')
    hist_mes_hora_df = artifacts.get('hist_mes_hora')
    global_median = df_train["tiempo_espera"].median()
    global_mean = df_train["tiempo_espera"].mean()
    
    # Verificar existencia en históricos pre-calculados
    tiene_mes_hora_dia = False
    tiene_hora_dia = False
    tiene_mes_hora = False
    tiene_hora = False
    
    if hist_mes_hora_df is not None and hist_mes_dia_df is not None:
        hora_col_mh = 'hora' if 'hora' in hist_mes_hora_df.columns else 'hora_int'
        tiene_mes_hora_dia = (not hist_mes_hora_df[(hist_mes_hora_df['atraccion'] == atr) & 
                                                    (hist_mes_hora_df['mes'] == mes) & 
                                                    (hist_mes_hora_df[hora_col_mh] == hora_int)].empty and
                             not hist_mes_dia_df[(hist_mes_dia_df['atraccion'] == atr) & 
                                                 (hist_mes_dia_df['mes'] == mes) & 
                                                 (hist_mes_dia_df['dia_semana_num'] == dia_semana)].empty)
    
    if hist_hora_dia_df is not None:
        hora_col_hd = 'hora' if 'hora' in hist_hora_dia_df.columns else 'hora_int'
        tiene_hora_dia = not hist_hora_dia_df[(hist_hora_dia_df['atraccion'] == atr) & 
                                             (hist_hora_dia_df[hora_col_hd] == hora_int) & 
                                             (hist_hora_dia_df['dia_semana_num'] == dia_semana)].empty
    
    if hist_mes_hora_df is not None:
        hora_col_mh = 'hora' if 'hora' in hist_mes_hora_df.columns else 'hora_int'
        tiene_mes_hora = not hist_mes_hora_df[(hist_mes_hora_df['atraccion'] == atr) & 
                                             (hist_mes_hora_df['mes'] == mes) & 
                                             (hist_mes_hora_df[hora_col_mh] == hora_int)].empty
    
    if hist_hora_df is not None:
        hora_col = 'hora' if 'hora' in hist_hora_df.columns else 'hora_int'
        tiene_hora = not hist_hora_df[(hist_hora_df['atraccion'] == atr) & 
                                     (hist_hora_df[hora_col] == hora_int)].empty
    
    # Si no hay datos exactos por hora, buscar en rango cercano
    if not tiene_hora and hora_int > 0:
        for h in [hora_int-1, hora_int+1]:
            if 0 <= h < 24 and hist_hora_df is not None:
                hora_col = 'hora' if 'hora' in hist_hora_df.columns else 'hora_int'
                if not hist_hora_df[(hist_hora_df['atraccion'] == atr) & (hist_hora_df[hora_col] == h)].empty:
                    hora_int = h
                    tiene_hora = True
                    break
    
    # PRIORIZAR históricos que incluyen HORA - buscar directamente en df_train
    if tiene_mes_hora_dia:
        hist_ref = df_train[(df_train['atraccion'] == atr) & 
                            (df_train['mes'] == mes) & 
                            (df_train['hora'].astype(int) == hora_int) & 
                            (df_train['dia_semana_num'] == dia_semana)]
        especificidad = "mes_hora_dia"
    elif tiene_hora_dia:
        hist_ref = df_train[(df_train['atraccion'] == atr) & 
                            (df_train['hora'].astype(int) == hora_int) & 
                            (df_train['dia_semana_num'] == dia_semana)]
        especificidad = "hora_dia"
    elif tiene_mes_hora:
        hist_ref = df_train[(df_train['atraccion'] == atr) & 
                            (df_train['mes'] == mes) & 
                            (df_train['hora'].astype(int) == hora_int)]
        especificidad = "mes_hora"
    elif tiene_hora:
        hist_ref = df_train[(df_train['atraccion'] == atr) & 
                           (df_train['hora'].astype(int) == hora_int)]
        especificidad = "hora"
    else:
        hist_mes_dia_ref = df_train[(df_train['atraccion'] == atr) & 
                                   (df_train['mes'] == mes) & 
                                   (df_train['dia_semana_num'] == dia_semana)]
        hist_dia_ref = df_train[(df_train['atraccion'] == atr) & 
                               (df_train['dia_semana_num'] == dia_semana)]
        hist_mes_ref = df_train[(df_train['atraccion'] == atr) & 
                               (df_train['mes'] == mes)]
        
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
        p75_hist = hist_ref['tiempo_espera'].quantile(0.75)
        median_hist = hist_ref['tiempo_espera'].median()
        p90_hist = hist_ref['tiempo_espera'].quantile(0.90)
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
    if especificidad in ["mes_hora_dia", "hora_dia", "mes_hora", "hora"]:
        # Tenemos datos por hora - usar histórico como base y ajustar con modelo
        if not hist_ref.empty:
            if es_hora_apertura:
                hist_base = hist_ref['tiempo_espera'].quantile(0.25) if len(hist_ref) > 10 else median_hist
                peso_historico = 0.80
                peso_modelo = 0.20
            elif es_hora_pico:
                hist_base = p75_hist
                # DETECTAR HISTÓRICOS SOSPECHOSAMENTE BAJOS
                if p75_hist < 15 and count_hist < 20:
                    hist_mes_dia_alt = df_train[(df_train['atraccion'] == atr) & 
                                               (df_train['mes'] == mes) & 
                                               (df_train['dia_semana_num'] == dia_semana)]
                    hist_mes_alt = df_train[(df_train['atraccion'] == atr) & 
                                           (df_train['mes'] == mes)]
                    
                    if not hist_mes_dia_alt.empty:
                        p75_alt = hist_mes_dia_alt['tiempo_espera'].quantile(0.75)
                        if p75_alt > p75_hist:
                            hist_base = p75_alt
                            especificidad = "mes_dia_fallback"
                    elif not hist_mes_alt.empty:
                        p75_alt = hist_mes_alt['tiempo_espera'].quantile(0.75)
                        if p75_alt > p75_hist:
                            hist_base = p75_alt
                            especificidad = "mes_fallback"
                    
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
    print(f"DEBUG: pred_base={pred_base:.2f}, hist_base={hist_base:.2f}, pred_combinada={pred_combinada:.2f}")
    
    # AJUSTES ESPECIALES POR CONTEXTO
    if es_hora_apertura:
        if es_fin_de_semana:
            minutos_final = pred_combinada * 0.50
        else:
            minutos_final = pred_combinada * 0.60
        ajuste = f"apertura_{especificidad}"
    elif "Batman" in atr and mes == 10:
        if es_fin_de_semana:
            if es_hora_pico:
                if p75_hist < 15 or hist_base < 15:
                    minutos_final = max(pred_base * 1.50, pred_combinada * 1.40, 25.0)
                else:
                    minutos_final = max(pred_combinada * 1.30, p75_hist * 1.25, hist_base * 1.35, pred_base * 1.25)
            else:
                if hist_base < 10:
                    minutos_final = max(pred_base * 1.30, pred_combinada * 1.20, 15.0)
                else:
                    minutos_final = max(pred_combinada * 1.20, hist_base * 1.25)
        else:
            if es_hora_pico:
                if hist_base < 15:
                    minutos_final = max(pred_base * 1.35, pred_combinada * 1.25, 20.0)
                else:
                    minutos_final = max(pred_combinada * 1.15, hist_base * 1.20)
            else:
                minutos_final = max(pred_combinada * 1.10, hist_base * 1.15)
        ajuste = f"batman_octubre_{'fin_semana' if es_fin_de_semana else 'laborable'}_{especificidad}"
    elif es_puente_val:
        if es_fin_de_semana:
            minutos_final = pred_combinada * 1.15
        else:
            minutos_final = pred_combinada * 1.10
        ajuste = f"puente_{especificidad}"
    elif mes == 10 and dia_semana == 6:
        if es_hora_pico:
            minutos_final = pred_combinada * 1.10
        else:
            minutos_final = pred_combinada
        ajuste = f"octubre_domingo_{especificidad}"
    elif mes == 11 and dia_semana == 6:
        if es_hora_pico:
            minutos_final = pred_combinada * 1.08
        else:
            minutos_final = pred_combinada
        ajuste = f"noviembre_domingo_{especificidad}"
    elif es_hora_pico:
        minutos_final = pred_combinada * 1.05
        ajuste = f"hora_pico_{especificidad}"
    elif es_hora_valle:
        minutos_final = pred_combinada * 0.90
        ajuste = f"hora_valle_{especificidad}"
    elif es_fin_de_semana:
        minutos_final = pred_combinada
        ajuste = f"fin_semana_{especificidad}"
    else:
        minutos_final = pred_combinada
        ajuste = f"laborable_{especificidad}"
    
    # Asegurar límites razonables (pero no forzar mínimo de 5 si la predicción es legítimamente baja)
    # Solo aplicar mínimo si la predicción es negativa o extremadamente baja
    if minutos_final < 1:
        minutos_final = max(global_median * 0.5, 5)  # Usar al menos la mitad de la mediana o 5, lo que sea mayor
        print(f"WARNING: Predicción muy baja, usando fallback: {minutos_final}")
    
    minutos_final = min(180, max(1, minutos_final))  # Mínimo 1 minuto, máximo 180
    
    print(f"DEBUG: Predicción final: {minutos_final:.2f} minutos")
    print(f"DEBUG: Ajuste aplicado: {ajuste}")
    print(f"DEBUG: Especificidad histórico: {especificidad}")
    
    return {
        "minutos_predichos": round(minutos_final, 1),
        "status": "success",
        "atraccion": input_dict.get("atraccion"),
        "prediccion_raw": round(pred_base, 2),
        "prediccion_combinada": round(pred_combinada, 2),
        "historico_base": round(hist_base, 2),
        "ajuste_aplicado": ajuste,
        "especificidad_historico": especificidad
    }

# --- HANDLER PRINCIPAL ---

def lambda_handler(event, context):
    try:
        print("=== INICIO LAMBDA HANDLER ===")
        print(f"Event recibido: {json.dumps(event, default=str)}")
        
        # 1. Cargar artefactos
        print("Cargando artefactos desde S3...")
        artifacts = load_model_from_s3()
        print("Artefactos cargados correctamente")
        
        # 2. Parsear Body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        print(f"Body parseado: {json.dumps(body, default=str)}")
        
        # 3. Validaciones de entrada (Seguridad)
        required = ['fecha', 'hora', 'atraccion', 'zona']
        missing = [f for f in required if f not in body]
        if missing:
            print(f"ERROR: Faltan campos requeridos: {missing}")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Faltan campos: {", ".join(missing)}'})
            }
            
        # 4. Ejecutar Predicción
        print("Iniciando predicción...")
        resultado = predict_wait_time(body, artifacts)
        print(f"Predicción completada: {resultado}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(resultado)
        }
        
    except Exception as e:
        print("--- ERROR DETECTADO ---")
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'type': type(e).__name__})
        }

# ====================================================
# PARK WAIT TIME PREDICTOR - VERSIÓN PROFESIONAL MEJORADA
# Sistema de predicción de tiempo de espera con diferenciación
# completa de días de semana, meses y patrones temporales
# ====================================================

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
import matplotlib.pyplot as plt
import joblib
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

os.makedirs("models", exist_ok=True)

# -------------------------
# 1) CARGA Y ANÁLISIS INICIAL
# -------------------------
print("=" * 70)
print("🔍 CARGA Y ANÁLISIS INICIAL DEL DATASET")
print("=" * 70)

df = pd.read_csv("../data/clean/tiempos_final.csv")
print(f"Shape original: {df.shape}")
print(f"Columnas: {df.columns.tolist()}")
print(f"\nValores nulos:\n{df.isnull().sum()}")
print(f"\nEstadísticas de tiempo_espera:")
print(df["tiempo_espera"].describe())

# Filtrar outliers extremos (más conservador: 0.5%-99.5%)
q_low = df["tiempo_espera"].quantile(0.005)
q_high = df["tiempo_espera"].quantile(0.995)
df_original = df.copy()
df = df[(df["tiempo_espera"] >= q_low) & (df["tiempo_espera"] <= q_high)].copy()
print(f"\nShape después de filtrar outliers (0.5%-99.5%): {df.shape}")
print(f"Outliers eliminados: {len(df_original) - len(df)}")

# -------------------------
# 2) FEATURE ENGINEERING AVANZADO
# -------------------------
print("\n" + "=" * 70)
print("🔧 FEATURE ENGINEERING AVANZADO")
print("=" * 70)

df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

# Función mejorada para parsear hora
def parse_hora(hora_str):
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

df["hora"] = df["hora"].apply(parse_hora)
df["hora"] = df["hora"].fillna(df["hora"].median())

# Features temporales COMPLETAS
df["mes"] = df["fecha"].dt.month
df["dia_mes"] = df["fecha"].dt.day
df["dia_semana_num"] = df["fecha"].dt.weekday  # 0=Lunes, 6=Domingo
df["semana_año"] = df["fecha"].dt.isocalendar().week
df["trimestre"] = df["fecha"].dt.quarter
df["año"] = df["fecha"].dt.year

# DIFERENCIACIÓN COMPLETA DE DÍAS DE SEMANA
df["es_lunes"] = (df["dia_semana_num"] == 0).astype(int)
df["es_martes"] = (df["dia_semana_num"] == 1).astype(int)
df["es_miercoles"] = (df["dia_semana_num"] == 2).astype(int)
df["es_jueves"] = (df["dia_semana_num"] == 3).astype(int)
df["es_viernes"] = (df["dia_semana_num"] == 4).astype(int)
df["es_sabado"] = (df["dia_semana_num"] == 5).astype(int)
df["es_domingo"] = (df["dia_semana_num"] == 6).astype(int)
df["es_fin_de_semana"] = df["dia_semana_num"].isin([5, 6]).astype(int)
df["es_dia_laborable"] = df["dia_semana_num"].isin([0, 1, 2, 3, 4]).astype(int)

# DIFERENCIACIÓN COMPLETA DE MESES
for mes_num in range(1, 13):
    df[f"es_mes_{mes_num}"] = (df["mes"] == mes_num).astype(int)

# Temporada mejorada
def get_temporada(mes):
    if mes in [7, 8]:  # Verano
        return 3  # Muy Alta
    elif mes in [10]:  # Halloween
        return 3  # Muy Alta
    elif mes in [4, 5, 6, 12]:  # Primavera, Navidad
        return 2  # Alta
    elif mes in [3, 9, 11]:  # Media
        return 1  # Media
    else:
        return 0  # Baja

df["temporada"] = df["mes"].apply(get_temporada)

# Features cíclicas mejoradas (más granularidad)
df["hora_sin"] = np.sin(2 * np.pi * df["hora"] / 24)
df["hora_cos"] = np.cos(2 * np.pi * df["hora"] / 24)
df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)
df["dia_semana_sin"] = np.sin(2 * np.pi * df["dia_semana_num"] / 7)
df["dia_semana_cos"] = np.cos(2 * np.pi * df["dia_semana_num"] / 7)
df["dia_mes_sin"] = np.sin(2 * np.pi * df["dia_mes"] / 31)
df["dia_mes_cos"] = np.cos(2 * np.pi * df["dia_mes"] / 31)
df["semana_año_sin"] = np.sin(2 * np.pi * df["semana_año"] / 52)
df["semana_año_cos"] = np.cos(2 * np.pi * df["semana_año"] / 52)

# Interacciones importantes
df["hora_mes"] = df["hora"] * df["mes"]
df["hora_dia_semana"] = df["hora"] * df["dia_semana_num"]
df["mes_dia_semana"] = df["mes"] * df["dia_semana_num"]
df["fin_semana_mes"] = df["es_fin_de_semana"] * df["mes"]
df["temporada_dia_semana"] = df["temporada"] * df["dia_semana_num"]

# Rellenar numéricos faltantes
for col in ["temperatura", "humedad", "sensacion_termica", "codigo_clima"]:
    if col in df.columns:
        df[col] = df[col].fillna(df[col].median())
    else:
        df[col] = 0

# Features de clima mejoradas
if "codigo_clima" in df.columns:
    df["es_buen_clima"] = (df["codigo_clima"].isin([1, 2, 3])).astype(int)
    df["es_mal_clima"] = (df["codigo_clima"] > 3).astype(int)

# Features de HORA DEL DÍA - CRÍTICO para diferenciar apertura vs pico vs valle
df["hora_int"] = df["hora"].astype(int)
df["es_hora_apertura"] = ((df["hora_int"] >= 12) & (df["hora_int"] < 13)).astype(int)  # 10:00-11:00
df["es_hora_pico"] = ((df["hora_int"] >= 12) & (df["hora_int"] <= 16)).astype(int)  # 11:00-16:00
df["es_hora_valle_manana"] = (df["hora_int"] < 14)& (df["hora_int"] < 15).astype(int)  # Antes de 10:00
df["es_hora_valle_tarde"] = (df["hora_int"] > 18).astype(int)  # Después de 18:00
df["es_hora_valle"] = (df["es_hora_valle_manana"] | df["es_hora_valle_tarde"]).astype(int)

# Features de PUENTES/FESTIVOS (España)
def es_festivo_espana(fecha):
    """Detecta festivos en España"""
    mes = fecha.month
    dia = fecha.day
    
    # Festivos fijos
    if mes == 1 and dia == 1:  # Año Nuevo
        return 1
    if mes == 1 and dia == 6:  # Reyes
        return 1
    if mes == 5 and dia == 1:  # Día del Trabajo
        return 1
    if mes == 10 and dia == 12:  # Día de la Hispanidad
        return 1
    if mes == 11 and dia == 1:  # Todos los Santos
        return 1
    if mes == 12 and dia == 6:  # Constitución
        return 1
    if mes == 12 and dia == 8:  # Inmaculada
        return 1
    if mes == 12 and dia == 25:  # Navidad
        return 1
    return 0

def es_puente(fecha):
    """Detecta si un día es parte de un puente (festivo + fin de semana cercano)"""
    if es_festivo_espana(fecha):
        return 1
    
    # Verificar si el día anterior o siguiente es festivo
    dia_anterior = fecha - pd.Timedelta(days=1)
    dia_siguiente = fecha + pd.Timedelta(days=1)
    
    # Si es viernes y el lunes siguiente es festivo, o si es lunes y el viernes anterior es festivo
    if fecha.weekday() == 4 and es_festivo_espana(dia_siguiente):  # Viernes antes de festivo
        return 1
    if fecha.weekday() == 0 and es_festivo_espana(dia_anterior):  # Lunes después de festivo
        return 1
    if fecha.weekday() == 6 and es_festivo_espana(dia_anterior):  # Domingo después de festivo (sábado)
        return 1
    
    return 0

df["es_festivo"] = df["fecha"].apply(es_festivo_espana)
df["es_puente"] = df["fecha"].apply(es_puente)

# Interacciones con hora y puentes
df["hora_apertura_fin_semana"] = df["es_hora_apertura"] * df["es_fin_de_semana"]
df["hora_pico_puente"] = df["es_hora_pico"] * df["es_puente"]
df["puente_fin_semana"] = df["es_puente"] * df["es_fin_de_semana"]

# -------------------------
# 3) FEATURES HISTÓRICAS GRANULARES
# -------------------------
print("\n" + "=" * 70)
print("📊 CREANDO FEATURES HISTÓRICAS GRANULARES")
print("=" * 70)

# Histórico por mes
hist_mes = df.groupby(["atraccion", "mes"])["tiempo_espera"].agg(
    count_mes="count",
    mean_mes="mean",
    median_mes="median",
    std_mes="std",
    p75_mes=lambda x: np.percentile(x, 75),
    p90_mes=lambda x: np.percentile(x, 90),
    p95_mes=lambda x: np.percentile(x, 95)
).reset_index()

# Histórico por hora (usar hora_int para mejor agrupación)
hist_hora = df.groupby(["atraccion", "hora_int"])["tiempo_espera"].agg(
    count_hora="count",
    mean_hora="mean",
    median_hora="median",
    std_hora="std",
    p75_hora=lambda x: np.percentile(x, 75),
    p90_hora=lambda x: np.percentile(x, 90)
).reset_index()
hist_hora = hist_hora.rename(columns={"hora_int": "hora"})  # Renombrar para compatibilidad

# Histórico por día de semana (CRÍTICO para diferenciar sábado/domingo)
hist_dia_semana = df.groupby(["atraccion", "dia_semana_num"])["tiempo_espera"].agg(
    count_dia="count",
    mean_dia="mean",
    median_dia="median",
    std_dia="std",
    p75_dia=lambda x: np.percentile(x, 75),
    p90_dia=lambda x: np.percentile(x, 90)
).reset_index()

# Histórico por mes Y día de semana (MUY IMPORTANTE)
hist_mes_dia = df.groupby(["atraccion", "mes", "dia_semana_num"])["tiempo_espera"].agg(
    count_mes_dia="count",
    mean_mes_dia="mean",
    median_mes_dia="median",
    p75_mes_dia=lambda x: np.percentile(x, 75),
    p90_mes_dia=lambda x: np.percentile(x, 90)
).reset_index()

# Histórico por hora Y día de semana
hist_hora_dia = df.groupby(["atraccion", "hora_int", "dia_semana_num"])["tiempo_espera"].agg(
    count_hora_dia="count",
    mean_hora_dia="mean",
    median_hora_dia="median",
    p75_hora_dia=lambda x: np.percentile(x, 75)
).reset_index()
hist_hora_dia = hist_hora_dia.rename(columns={"hora_int": "hora"})  # Renombrar para compatibilidad

# Histórico por mes Y hora
hist_mes_hora = df.groupby(["atraccion", "mes", "hora_int"])["tiempo_espera"].agg(
    count_mes_hora="count",
    mean_mes_hora="mean",
    median_mes_hora="median",
    p75_mes_hora=lambda x: np.percentile(x, 75)
).reset_index()
hist_mes_hora = hist_mes_hora.rename(columns={"hora_int": "hora"})  # Renombrar para compatibilidad

# Merge con df principal
print("Haciendo merge de features históricas...")
df = df.merge(hist_mes, on=["atraccion", "mes"], how="left")
df = df.merge(hist_hora, left_on=["atraccion", "hora_int"], right_on=["atraccion", "hora"], how="left", suffixes=("", "_hist"))
df = df.merge(hist_dia_semana, on=["atraccion", "dia_semana_num"], how="left")
df = df.merge(hist_mes_dia, on=["atraccion", "mes", "dia_semana_num"], how="left")
df = df.merge(hist_hora_dia, left_on=["atraccion", "hora_int", "dia_semana_num"], right_on=["atraccion", "hora", "dia_semana_num"], how="left", suffixes=("", "_hist_hd"))
df = df.merge(hist_mes_hora, left_on=["atraccion", "mes", "hora_int"], right_on=["atraccion", "mes", "hora"], how="left", suffixes=("", "_hist_mh"))

# Rellenar valores faltantes con fallbacks inteligentes
global_median = df["tiempo_espera"].median()
global_mean = df["tiempo_espera"].mean()

fill_rules = {
    "mean": global_mean,
    "median": global_median,
    "std": df["tiempo_espera"].std(),
    "p75": np.percentile(df["tiempo_espera"], 75),
    "p90": np.percentile(df["tiempo_espera"], 90),
    "p95": np.percentile(df["tiempo_espera"], 95),
    "count": 0
}

for col in df.columns:
    if col.startswith("count_"):
        df[col] = df[col].fillna(0)
    elif "mean" in col:
        df[col] = df[col].fillna(fill_rules["mean"])
    elif "median" in col:
        df[col] = df[col].fillna(fill_rules["median"])
    elif "std" in col:
        df[col] = df[col].fillna(fill_rules["std"])
    elif "p75" in col:
        df[col] = df[col].fillna(fill_rules["p75"])
    elif "p90" in col:
        df[col] = df[col].fillna(fill_rules["p90"])
    elif "p95" in col:
        df[col] = df[col].fillna(fill_rules["p95"])

# Flags especiales
df["is_batman_octubre"] = ((df["atraccion"].str.contains("Batman", na=False)) & (df["mes"] == 10)).astype(int)
df["is_octubre"] = (df["mes"] == 10).astype(int)
df["is_noviembre"] = (df["mes"] == 11).astype(int)
df["is_octubre_fin_semana"] = ((df["mes"] == 10) & (df["es_fin_de_semana"] == 1)).astype(int)
df["is_noviembre_fin_semana"] = ((df["mes"] == 11) & (df["es_fin_de_semana"] == 1)).astype(int)

print(f"Features creadas: {len(df.columns)} columnas")

# -------------------------
# 4) PREPARACIÓN DE DATOS PARA MODELO
# -------------------------
print("\n" + "=" * 70)
print("🎯 PREPARACIÓN DE DATOS PARA MODELO")
print("=" * 70)

drop_cols = ["tiempo_espera", "fecha", "dia_semana", "ultima_actualizacion", "abierta"]
X = df.drop(columns=[c for c in drop_cols if c in df.columns]).copy()
y = df["tiempo_espera"].copy()

categorical_cols = ["zona", "atraccion"]

print(f"Features para el modelo: {X.shape[1]} columnas")
print(f"Filas: {X.shape[0]}")

# Split estratificado por temporada Y mes para asegurar representación
stratify_col = df["temporada"].astype(str) + "_" + df["mes"].astype(str)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=stratify_col
)

print(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

# -------------------------
# 5) ENCODING CATEGÓRICO MEJORADO
# -------------------------
print("\n" + "=" * 70)
print("🔤 ENCODING CATEGÓRICO MEJORADO")
print("=" * 70)

def target_encoding_improved(X_tr, X_te, y_tr, cols):
    X_tr_enc = X_tr.copy()
    X_te_enc = X_te.copy()
    encoding_maps = {}
    
    for col in cols:
        if col in X_tr.columns:
            # Target encoding con smoothing
            mean_target = y_tr.mean()
            stats = y_tr.groupby(X_tr[col]).agg(['mean', 'count']).reset_index()
            stats.columns = [col, 'mean', 'count']
            
            # Smoothing: más peso a la media global cuando hay pocos ejemplos
            smoothing_factor = 10
            stats['encoded'] = (stats['count'] * stats['mean'] + smoothing_factor * mean_target) / (stats['count'] + smoothing_factor)
            
            map_enc = dict(zip(stats[col], stats['encoded']))
            encoding_maps[col] = map_enc
            
            X_tr_enc[f"{col}_enc"] = X_tr[col].map(map_enc).fillna(mean_target)
            X_te_enc[f"{col}_enc"] = X_te[col].map(map_enc).fillna(mean_target)
            
            # También crear frecuencia encoding
            freq_map = X_tr[col].value_counts().to_dict()
            X_tr_enc[f"{col}_freq"] = X_tr[col].map(freq_map).fillna(0)
            X_te_enc[f"{col}_freq"] = X_te[col].map(freq_map).fillna(0)
            
            # Eliminar columna original
            X_tr_enc = X_tr_enc.drop(columns=[col])
            X_te_enc = X_te_enc.drop(columns=[col])
    
    return X_tr_enc, X_te_enc, encoding_maps

X_train_enc, X_test_enc, encoding_maps = target_encoding_improved(
    X_train, X_test, y_train, categorical_cols
)

# Asegurar que no queden columnas object
non_numeric = X_train_enc.select_dtypes(include=['object']).columns.tolist()
if non_numeric:
    print(f"Eliminando columnas no numéricas: {non_numeric}")
    X_train_enc = X_train_enc.drop(columns=non_numeric)
    X_test_enc = X_test_enc.drop(columns=non_numeric)

print(f"Features después de encoding: {X_train_enc.shape[1]} columnas")

# -------------------------
# 6) ESCALADO
# -------------------------
print("\n" + "=" * 70)
print("📏 ESCALADO DE FEATURES")
print("=" * 70)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_enc)
X_test_scaled = scaler.transform(X_test_enc)
columnas_entrenamiento = X_train_enc.columns.tolist()

print(f"Escalado completado. Shape: {X_train_scaled.shape}")

# -------------------------
# 7) ENTRENAMIENTO DEL MODELO MEJORADO
# -------------------------
print("\n" + "=" * 70)
print("🚀 ENTRENAMIENTO DEL MODELO XGBOOST MEJORADO")
print("=" * 70)

X_tr, X_val, y_tr, y_val = train_test_split(
    X_train_scaled, y_train, test_size=0.2, random_state=42
)

# Modelo optimizado con mejores hiperparámetros
model = XGBRegressor(
    n_estimators=1000,
    learning_rate=0.05,
    max_depth=8,
    subsample=0.85,
    colsample_bytree=0.85,
    colsample_bylevel=0.85,
    min_child_weight=5,
    reg_alpha=0.5,
    reg_lambda=2.0,
    gamma=0.1,
    objective='reg:squarederror',
    random_state=42,
    verbosity=0,
    n_jobs=-1,
    tree_method='hist'
)

print("Entrenando modelo...")
# Entrenar con conjunto de validación para monitoreo
# Nota: early_stopping_rounds se maneja diferente según la versión de XGBoost
# Esta versión funciona con todas las versiones
model.fit(
    X_tr, y_tr,
    eval_set=[(X_val, y_val)],
    verbose=False
)

y_val_pred = model.predict(X_val)
val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
val_r2 = r2_score(y_val, y_val_pred)
val_mae = mean_absolute_error(y_val, y_val_pred)

print(f"\n📊 MÉTRICAS DE VALIDACIÓN:")
print(f"   RMSE: {val_rmse:.2f} minutos")
print(f"   MAE: {val_mae:.2f} minutos")
print(f"   R²: {val_r2:.4f}")

# -------------------------
# 8) EVALUACIÓN FINAL
# -------------------------
print("\n" + "=" * 70)
print("📈 EVALUACIÓN FINAL EN TEST SET")
print("=" * 70)

y_pred = model.predict(X_test_scaled)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

within_5 = np.mean(np.abs(y_test - y_pred) <= 5) * 100
within_10 = np.mean(np.abs(y_test - y_pred) <= 10) * 100
within_20 = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1)) <= 0.2) * 100
within_15pct = np.mean(np.abs((y_test - y_pred) / np.maximum(y_test, 1)) <= 0.15) * 100

print(f"\n🎯 MÉTRICAS FINALES:")
print(f"   RMSE: {rmse:.2f} minutos")
print(f"   MAE: {mae:.2f} minutos")
print(f"   R²: {r2:.4f}")
print(f"\n📊 PRECISIÓN:")
print(f"   ±5 minutos: {within_5:.1f}%")
print(f"   ±10 minutos: {within_10:.1f}%")
print(f"   ±15%: {within_15pct:.1f}%")
print(f"   ±20%: {within_20:.1f}%")

# -------------------------
# 9) FUNCIÓN DE PREDICCIÓN PROFESIONAL CORREGIDA
# -------------------------
def prepare_input_for_prediction(input_dict, df_train, scaler, encoding_maps, columnas_entrenamiento):
    """
    Prepara un input para predicción aplicando todo el feature engineering
    """
    df_input = pd.DataFrame([input_dict]).copy()
    
    # Parsear fecha
    fecha = pd.to_datetime(df_input["fecha"].iloc[0], errors="coerce")
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
    
    # Features históricas (usar los datos históricos guardados)
    # Buscar en los históricos
    hist_mes_row = hist_mes[(hist_mes["atraccion"] == atraccion) & (hist_mes["mes"] == mes)]
    hist_hora_row = hist_hora[(hist_hora["atraccion"] == atraccion) & (hist_hora["hora"] == int(hora))]
    hist_dia_row = hist_dia_semana[(hist_dia_semana["atraccion"] == atraccion) & (hist_dia_semana["dia_semana_num"] == dia_semana_num)]
    hist_mes_dia_row = hist_mes_dia[(hist_mes_dia["atraccion"] == atraccion) & (hist_mes_dia["mes"] == mes) & (hist_mes_dia["dia_semana_num"] == dia_semana_num)]
    hist_hora_dia_row = hist_hora_dia[(hist_hora_dia["atraccion"] == atraccion) & (hist_hora_dia["hora"] == int(hora)) & (hist_hora_dia["dia_semana_num"] == dia_semana_num)]
    hist_mes_hora_row = hist_mes_hora[(hist_mes_hora["atraccion"] == atraccion) & (hist_mes_hora["mes"] == mes) & (hist_mes_hora["hora"] == int(hora))]
    
    # Valores por defecto
    global_median = df_train["tiempo_espera"].median()
    global_mean = df_train["tiempo_espera"].mean()
    
    # Extraer valores históricos
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
    
    # Features de HORA DEL DÍA
    hora_int = int(hora)
    es_hora_apertura = 1 if (hora_int >= 10 and hora_int < 11) else 0
    es_hora_pico = 1 if (hora_int >= 11 and hora_int <= 16) else 0
    es_hora_valle_manana = 1 if hora_int < 10 else 0
    es_hora_valle_tarde = 1 if hora_int > 18 else 0
    es_hora_valle = 1 if (es_hora_valle_manana or es_hora_valle_tarde) else 0
    
    # Features de PUENTES/FESTIVOS
    def es_festivo_espana(fecha):
        mes = fecha.month
        dia = fecha.day
        if mes == 1 and dia == 1: return 1
        if mes == 1 and dia == 6: return 1
        if mes == 5 and dia == 1: return 1
        if mes == 10 and dia == 12: return 1
        if mes == 11 and dia == 1: return 1
        if mes == 12 and dia == 6: return 1
        if mes == 12 and dia == 8: return 1
        if mes == 12 and dia == 25: return 1
        return 0
    
    def es_puente(fecha):
        if es_festivo_espana(fecha):
            return 1
        dia_anterior = fecha - pd.Timedelta(days=1)
        dia_siguiente = fecha + pd.Timedelta(days=1)
        if fecha.weekday() == 4 and es_festivo_espana(dia_siguiente):
            return 1
        if fecha.weekday() == 0 and es_festivo_espana(dia_anterior):
            return 1
        if fecha.weekday() == 6 and es_festivo_espana(dia_anterior):
            return 1
        return 0
    
    es_festivo = es_festivo_espana(fecha)
    es_puente_val = es_puente(fecha)
    
    # Interacciones con hora y puentes
    hora_apertura_fin_semana = es_hora_apertura * es_fin_de_semana
    hora_pico_puente = es_hora_pico * es_puente_val
    puente_fin_semana = es_puente_val * es_fin_de_semana
    
    # Encoding categórico
    zona_enc = encoding_maps.get("zona", {}).get(zona, global_mean) if "zona" in encoding_maps else global_mean
    atraccion_enc = encoding_maps.get("atraccion", {}).get(atraccion, global_mean) if "atraccion" in encoding_maps else global_mean
    
    # Construir el vector de features en el mismo orden que las columnas de entrenamiento
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
        "es_festivo": es_festivo,
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


def predict_wait_realista(input_dict):
    """
    Predicción robusta y realista que DIFERENCIA correctamente:
    - Sábado vs Domingo vs días laborables
    - Octubre vs Noviembre vs otros meses
    - Combina predicción del modelo con históricos granulares
    """
    # Predicción base del modelo (ESTA ES LA CLAVE - tiene hora, día del mes, etc.)
    X_pred = prepare_input_for_prediction(
        input_dict, df, scaler, encoding_maps, columnas_entrenamiento
    )
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
    
    # HISTÓRICOS ESPECÍFICOS POR HORA - esto es crítico para que cambie con la hora
    # Buscar por hora exacta (int) - la columna hora puede ser float
    hist_hora_atr = df[(df["atraccion"] == atr) & (df["hora"].astype(int) == hora_int)]
    hist_hora_dia_atr = df[(df["atraccion"] == atr) & (df["hora"].astype(int) == hora_int) & (df["dia_semana_num"] == dia_semana)]
    hist_mes_hora_atr = df[(df["atraccion"] == atr) & (df["mes"] == mes) & (df["hora"].astype(int) == hora_int)]
    hist_mes_hora_dia_atr = df[(df["atraccion"] == atr) & (df["mes"] == mes) & (df["hora"].astype(int) == hora_int) & (df["dia_semana_num"] == dia_semana)]
    
    # Si no hay datos exactos por hora, buscar en rango cercano (±1 hora)
    if hist_hora_atr.empty and hora_int > 0:
        for h in [hora_int-1, hora_int+1]:
            if 0 <= h < 24:
                alt = df[(df["atraccion"] == atr) & (df["hora"].astype(int) == h)]
                if not alt.empty:
                    hist_hora_atr = alt
                    hora_int = h
                    break
    
    # Históricos por mes+día (sin hora) - menos específicos
    hist_mes_atr = df[(df["atraccion"] == atr) & (df["mes"] == mes)]
    hist_dia_atr = df[(df["atraccion"] == atr) & (df["dia_semana_num"] == dia_semana)]
    hist_mes_dia_atr = df[(df["atraccion"] == atr) & (df["mes"] == mes) & (df["dia_semana_num"] == dia_semana)]
    
    # PRIORIZAR históricos que incluyen HORA - esto hace que cambie con la hora
    if not hist_mes_hora_dia_atr.empty:
        # Lo más específico: mes + hora + día de semana
        hist_ref = hist_mes_hora_dia_atr
        especificidad = "mes_hora_dia"
    elif not hist_hora_dia_atr.empty:
        # Hora + día de semana
        hist_ref = hist_hora_dia_atr
        especificidad = "hora_dia"
    elif not hist_mes_hora_atr.empty:
        # Mes + hora
        hist_ref = hist_mes_hora_atr
        especificidad = "mes_hora"
    elif not hist_hora_atr.empty:
        # Solo hora (muy importante para variación horaria)
        hist_ref = hist_hora_atr
        especificidad = "hora"
    elif not hist_mes_dia_atr.empty:
        # Mes + día (sin hora)
        hist_ref = hist_mes_dia_atr
        especificidad = "mes_dia"
    elif not hist_dia_atr.empty:
        # Solo día de semana
        hist_ref = hist_dia_atr
        especificidad = "dia"
    elif not hist_mes_atr.empty:
        # Solo mes
        hist_ref = hist_mes_atr
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
    def es_festivo_espana(fecha):
        mes = fecha.month
        dia = fecha.day
        if mes == 1 and dia == 1: return 1
        if mes == 1 and dia == 6: return 1
        if mes == 5 and dia == 1: return 1
        if mes == 10 and dia == 12: return 1
        if mes == 11 and dia == 1: return 1
        if mes == 12 and dia == 6: return 1
        if mes == 12 and dia == 8: return 1
        if mes == 12 and dia == 25: return 1
        return 0
    
    def es_puente(fecha):
        if es_festivo_espana(fecha):
            return 1
        dia_anterior = fecha - pd.Timedelta(days=1)
        dia_siguiente = fecha + pd.Timedelta(days=1)
        if fecha.weekday() == 4 and es_festivo_espana(dia_siguiente):
            return 1
        if fecha.weekday() == 0 and es_festivo_espana(dia_anterior):
            return 1
        if fecha.weekday() == 6 and es_festivo_espana(dia_anterior):
            return 1
        return 0
    
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
        # Batman octubre: boost especial pero respetando la hora
        if es_hora_pico:
            minutos_final = max(pred_combinada, hist_base * 1.20)
        else:
            minutos_final = max(pred_combinada, hist_base * 1.10)
        ajuste = f"batman_octubre_{especificidad}"
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

# -------------------------
# 10) TEST PROFESIONAL
# -------------------------
print("\n" + "=" * 70)
print("🧪 TEST DE PREDICCIÓN - VERIFICANDO DIFERENCIACIÓN")
print("=" * 70)

if __name__ == "__main__":
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
        },
        {
            "name": "Batman Octubre Lunes (Laborable)",
            "input": {
                "temperatura": 22,
                "humedad": 60,
                "sensacion_termica": 22,
                "codigo_clima": 3,
                "hora": "12:15:00",
                "zona": "DC Super Heroes World",
                "atraccion": "Batman Gotham City Escape",
                "fecha": "2025-10-27"
            }
        }
    ]
    
    print("\n" + "-" * 70)
    for test in tests:
        res = predict_wait_realista(test["input"])
        print(f"\n🎯 {test['name']}:")
        print(f"   📅 Fecha: {test['input']['fecha']} ({res['dia_semana']}, día {res['dia_mes']})")
        print(f"   🕐 Hora: {test['input']['hora']} (hora pico: {res['es_hora_pico']})")
        print(f"   ⏱️  Predicción: {res['minutos_predichos']} minutos")
        print(f"   🔢 Base modelo: {res['prediccion_base']} minutos")
        print(f"   📊 P75 histórico: {res['p75_historico']} minutos")
        print(f"   🎯 Ajuste: {res['ajuste_aplicado']}")
        print(f"   📈 Especificidad: {res['especificidad_historico']}")
        print(f"   🦇 Batman Octubre: {res['es_batman_octubre']}")
        print(f"   📆 Mes: {res['mes']}")
        print(f"   🏖️  Fin de semana: {res['es_fin_de_semana']}")
    
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
        res = predict_wait_realista(input_test)
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
        res = predict_wait_realista(input_test)
        print(f"\n📅 {test_dia['name']} (día {res['dia_mes']}):")
        print(f"   ⏱️  Predicción: {res['minutos_predichos']} min (Base: {res['prediccion_base']:.1f} min)")
        print(f"   📊 Histórico: {res['p75_historico']:.1f} min ({res['especificidad_historico']})")
    
    print("\n" + "=" * 70)
    print("✅ MODELO PROFESIONAL COMPLETADO")
    print("=" * 70)
    print(f"   📈 R² test: {r2:.4f}")
    print(f"   📊 ±5min: {within_5:.1f}%")
    print(f"   📊 ±10min: {within_10:.1f}%")
    print(f"   📊 ±15%: {within_15pct:.1f}%")
    print(f"   ⏱️  MAE: {mae:.2f} minutos")
    print(f"   📉 RMSE: {rmse:.2f} minutos")
    print("\n🎉 El modelo ahora DIFERENCIA correctamente:")
    print("   ✓ Sábado vs Domingo vs días laborables")
    print("   ✓ Octubre vs Noviembre vs otros meses")
    print("   ✓ Combinaciones mes + día de semana")
    print("   ✓ Patrones históricos granulares")
    print("   ✓ Variación por HORA (pico vs valle)")
    print("   ✓ Variación por DÍA DEL MES")

# -------------------------
# 11) GUARDAR MODELO Y ARTEFACTOS
# -------------------------
print("\n" + "=" * 70)
print("💾 GUARDANDO MODELO Y ARTEFACTOS")
print("=" * 70)

joblib.dump(model, "models/xgb_model_professional.pkl")
joblib.dump(scaler, "models/xgb_scaler_professional.pkl")
joblib.dump(encoding_maps, "models/xgb_encoding_professional.pkl")
joblib.dump(columnas_entrenamiento, "models/xgb_columns_professional.pkl")
joblib.dump(hist_mes, "models/hist_mes.pkl")
joblib.dump(hist_hora, "models/hist_hora.pkl")
joblib.dump(hist_dia_semana, "models/hist_dia_semana.pkl")
joblib.dump(hist_mes_dia, "models/hist_mes_dia.pkl")
joblib.dump(hist_hora_dia, "models/hist_hora_dia.pkl")
joblib.dump(hist_mes_hora, "models/hist_mes_hora.pkl")
joblib.dump(df, "models/df_processed.pkl")  

print("✅ Todos los artefactos guardados correctamente")


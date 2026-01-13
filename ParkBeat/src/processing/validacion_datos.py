# 2.4_validacion_calidad.py
import pandas as pd
import numpy as np
import os

# Ruta base del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

input_path = os.path.join(BASE_DIR, "../../data/clean/queue_times_weather.csv")
output_path = os.path.join(BASE_DIR, "../../data/clean/")

# Asegurarse de que existe la carpeta de salida
os.makedirs(output_path, exist_ok=True)

# Cargar dataset de la fase anterior
df = pd.read_csv(input_path)

# -----------------------
# 1️⃣ Revisar duplicados
# -----------------------
duplicados = df.duplicated(subset=['fecha', 'hora', 'atraccion'], keep='first').sum()
df = df.drop_duplicates(subset=['fecha', 'hora', 'atraccion'], keep='first')

# -----------------------
# 2️⃣ Revisar valores nulos
# -----------------------
nulos = df.isnull().sum()

# Imputación de valores nulos
df['tiempo_espera'] = df['tiempo_espera'].fillna(df['tiempo_espera'].median())
df['temperatura'] = df['temperatura'].fillna(df['temperatura'].median())
df['humedad'] = df['humedad'].fillna(df['humedad'].median())
df['codigo_clima'] = df['codigo_clima'].fillna('Desconocido')

# -----------------------
# 3️⃣ Tipos de datos
# -----------------------
df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S', errors='coerce').dt.hour
df['tiempo_espera'] = df['tiempo_espera'].astype(float)
df['temperatura'] = df['temperatura'].astype(float)
df['humedad'] = df['humedad'].astype(float)
df['codigo_clima'] = df['codigo_clima'].astype(str)

# -----------------------
# 4️⃣ Rangos válidos
# -----------------------
df = df[(df['tiempo_espera'] >= 0) &
        (df['temperatura'].between(-10, 45)) &
        (df['humedad'].between(0, 100))]


# -----------------------
# 6️⃣ Generar informe de calidad
# -----------------------
informe = pd.DataFrame({
    'Columna': df.columns,
    'Nulos': df.isnull().sum().values,
    'Duplicados eliminados': [duplicados if col=='tiempo_espera' else 0 for col in df.columns]
    
})

informe.to_csv(os.path.join(output_path, "informe_calidad.csv"), index=False)

# -----------------------
# 7️⃣ Guardar dataset limpio
# -----------------------
df.to_csv(os.path.join(output_path, "queue_times_clean.csv"), index=False)

# -----------------------
# ✅ Mensajes
# -----------------------
print("✅ Validación y limpieza completadas.")
print(f"Duplicados eliminados: {duplicados}")
print(f"Dataset limpio guardado en: {os.path.join(output_path, 'queue_times_clean.csv')}")
print(f"Informe de calidad guardado en: {os.path.join(output_path, 'informe_calidad.csv')}")

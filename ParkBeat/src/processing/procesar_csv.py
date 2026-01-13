import pandas as pd
from pathlib import Path

# 📂 Ruta donde están los CSV originales
raw_path = Path("data/raw/queue_times")

# 📂 Ruta de salida final
output_path = Path("data/processed/queue_times_all_enriched.csv")

# 🔍 Buscar todos los archivos que empiecen por 'queue_times_'
csv_files = sorted(raw_path.glob("queue_times_*.csv"))

if not csv_files:
    raise FileNotFoundError("❌ No se encontraron archivos 'queue_times_*.csv' en data/raw/queue_times")

print(f"📄 Se encontraron {len(csv_files)} archivos CSV para combinar.\n")

# 📦 Lista para ir acumulando los DataFrames
dataframes = []

for csv_file in csv_files:
    print(f"➡️ Procesando {csv_file.name} ...")

    try:
        df = pd.read_csv(csv_file)

        # --- Aseguramos que las columnas esperadas existan ---
        if "ultima_actualizacion" not in df.columns:
            raise KeyError(f"El archivo {csv_file.name} no tiene la columna 'ultima_actualizacion'.")

        # Convertir a datetime
        df["ultima_actualizacion"] = pd.to_datetime(df["ultima_actualizacion"], errors="coerce", utc=True)

        # Añadir columnas nuevas si no existen
        if "fecha" not in df.columns:
            df["fecha"] = df["ultima_actualizacion"].dt.date

        if "hora" not in df.columns:
            df["hora"] = df["ultima_actualizacion"].dt.strftime("%H:%M")

        if "dia_semana" not in df.columns:
            df["dia_semana"] = df["ultima_actualizacion"].dt.day_name(locale="es_ES")

        # Crear columnas derivadas
        df["timestamp"] = df["ultima_actualizacion"].dt.tz_localize(None)
        df["mes"] = df["ultima_actualizacion"].dt.month
        df["fin_de_semana"] = df["ultima_actualizacion"].dt.dayofweek >= 5

        # --- LIMPIEZA: eliminar zonas no deseadas ---
        df = df[~df["zona"].isin(["Halloween", "Warner Beach"])]

        # Aseguramos el orden de columnas
        columnas_finales = [
            "zona", "atraccion", "tiempo_espera", "abierta",
            "ultima_actualizacion", "fecha", "hora", "dia_semana",
            "timestamp", "mes", "fin_de_semana"
        ]
        for col in columnas_finales:
            if col not in df.columns:
                df[col] = None  # si falta alguna, la rellenamos

        df = df[columnas_finales]

        dataframes.append(df)

    except Exception as e:
        print(f"⚠️ Error procesando {csv_file.name}: {e}\n")

# 🧩 Unir todos los DataFrames en uno solo
if dataframes:
    df_final = pd.concat(dataframes, ignore_index=True)

    # 🔍 Filtramos filas vacías o sin zona
    df_final = df_final.dropna(subset=["zona"])
    df_final = df_final[df_final["zona"].str.strip() != ""]

    # Guardamos el archivo final
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_path, index=False, encoding="utf-8")

    print(f"\n✅ Archivo final guardado en: {output_path}")
    print(f"📊 Filas totales después de limpieza: {len(df_final)}")
    print(f"🧹 Eliminadas zonas no deseadas: Halloween, Warner Beach")

else:
    print("❌ No se pudo generar el CSV final (ningún archivo válido).")

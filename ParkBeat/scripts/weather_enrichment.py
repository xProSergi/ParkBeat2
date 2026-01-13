import os
import pandas as pd
from datetime import datetime
import requests

PROCESSED_DIR = "data/processed"
ENRICHED_FILE = os.path.join(PROCESSED_DIR, "queue_times_enriched.csv")
LAT, LON = 40.2068, -3.6128

df = pd.read_csv(ENRICHED_FILE)

# Crear columnas si no existen
for col in ["temperatura", "humedad", "sensacion_termica", "codigo_clima"]:
    if col not in df.columns:
        df[col] = pd.NA

# Filtrar solo filas que faltan datos de clima
df_missing = df[df["temperatura"].isna()]

# Cache interna
weather_cache = {}

def get_weather_for_hour(date_str, hour_str):
    """Devuelve clima (temperatura, humedad, sensación, código) usando cache y solicitudes por hora"""
    key = (date_str, hour_str)
    if key in weather_cache:
        return weather_cache[key]

    try:
        date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        hour = int(str(hour_str).split(":")[0])
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={LAT}&longitude={LON}"
            f"&hourly=temperature_2m,relative_humidity_2m,apparent_temperature,weathercode"
            f"&start_date={date}&end_date={date}&timezone=Europe/Madrid"
        )
        response = requests.get(url)
        data = response.json()
        temps = data["hourly"]["temperature_2m"]
        hums = data["hourly"]["relative_humidity_2m"]
        feels = data["hourly"]["apparent_temperature"]
        codes = data["hourly"]["weathercode"]
        hours = data["hourly"]["time"]

        for i, t in enumerate(hours):
            if f"T{hour:02d}:00" in t:
                weather_cache[key] = (temps[i], hums[i], feels[i], codes[i])
                return weather_cache[key]
    except:
        weather_cache[key] = (None, None, None, None)
        return weather_cache[key]

# Asignar clima solo a filas faltantes
for idx, row in df_missing.iterrows():
    fecha, hora = row["fecha"], row["hora"]
    df.loc[idx, ["temperatura","humedad","sensacion_termica","codigo_clima"]] = get_weather_for_hour(fecha, hora)

df.to_csv(ENRICHED_FILE, index=False, encoding="utf-8-sig")
print(f"✅ Weather enrichment completado → {ENRICHED_FILE}")

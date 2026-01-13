import pandas as pd
import requests
from datetime import datetime
import os

# Coordenadas del Parque Warner Madrid
LAT, LON = 40.2068, -3.6128

INPUT_PATH = "data/processed/queue_times_all_enriched.csv"
OUTPUT_PATH = "data/clean/queue_times_weather.csv"

def get_weather_for_time(date_str, hour_str):
    """
    Consulta la API de Open-Meteo para obtener datos de clima por hora.
    Devuelve un diccionario con temperatura, humedad, etc.
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        hour = int(hour_str.split(":")[0])

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
        weather_codes = data["hourly"]["weathercode"]
        hours = data["hourly"]["time"]

        # Buscar la hora más cercana
        for i, t in enumerate(hours):
            if f"T{hour:02d}:00" in t:
                return {
                    "temperatura": temps[i],
                    "humedad": hums[i],
                    "sensacion_termica": feels[i],
                    "codigo_clima": weather_codes[i],
                }

        return {"temperatura": None, "humedad": None, "sensacion_termica": None, "codigo_clima": None}

    except Exception as e:
        print(f"Error obteniendo clima para {date_str} {hour_str}: {e}")
        return {"temperatura": None, "humedad": None, "sensacion_termica": None, "codigo_clima": None}


def enrich_with_weather(df):
    """
    Añade columnas meteorológicas al DataFrame.
    """
    weather_data = df.apply(lambda row: get_weather_for_time(row["fecha"], row["hora"]), axis=1)
    weather_df = pd.DataFrame(list(weather_data))
    df = pd.concat([df, weather_df], axis=1)
    return df


def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(f"❌ No se encontró {INPUT_PATH}. Ejecuta enriquecer_features_datos.py primero.")
    
    df = pd.read_csv(INPUT_PATH)
    print(f"🌤️ Enriqueciendo {len(df)} registros con datos meteorológicos...")

    df_weather = enrich_with_weather(df)
    df_weather.to_csv(OUTPUT_PATH, index=False)

    print(f"✅ Archivo final guardado en {OUTPUT_PATH}")
    print(df_weather.head())


if __name__ == "__main__":
    main()

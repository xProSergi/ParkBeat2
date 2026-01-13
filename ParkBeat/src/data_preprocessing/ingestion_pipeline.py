import pandas as pd
import os
from datetime import datetime

RAW_INPUT = "data/raw/queue_times_new.csv"  # Aquí llegan los nuevos datos (cada 15 min)
PROCESSED_PATH = "data/processed/queue_times_all_enriched.csv"

def load_new_data():
    """Carga los nuevos registros obtenidos desde la API."""
    if not os.path.exists(RAW_INPUT):
        print("⚠️ No hay nuevos datos.")
        return pd.DataFrame()

    df_new = pd.read_csv(RAW_INPUT)

    # 🧹 Quitar timestamp si existe
    if "timestamp" in df_new.columns:
        df_new = df_new.drop(columns=["timestamp"])

    return df_new

def append_unique_records(df_new):
    """Agrega los nuevos registros al CSV procesado, evitando duplicados."""
    if os.path.exists(PROCESSED_PATH):
        df_existing = pd.read_csv(PROCESSED_PATH)
        combined = pd.concat([df_existing, df_new], ignore_index=True)

        # 🔍 Eliminar duplicados por fecha, hora, atraccion
        combined = combined.drop_duplicates(subset=["fecha", "hora", "atraccion"], keep="last")
    else:
        combined = df_new.drop_duplicates(subset=["fecha", "hora", "atraccion"], keep="last")

    # Guardar CSV limpio
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    combined.to_csv(PROCESSED_PATH, index=False)
    print(f"✅ Archivo actualizado: {len(combined)} registros guardados en {PROCESSED_PATH}")

def main():
    df_new = load_new_data()
    if df_new.empty:
        print("✅ No hay datos nuevos que procesar.")
        return

    append_unique_records(df_new)

if __name__ == "__main__":
    main()

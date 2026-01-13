import pandas as pd
import os
import glob

# === RUTAS ===
INPUT_DIR = "data/raw/queue_times"
OUTPUT_PATH = "data/clean/queue_times_enriched.csv"

def add_time_features(df):
    """Añade columnas derivadas de tiempo si no existen."""
    if 'fecha' not in df.columns or 'hora' not in df.columns:
        # Crear fecha y hora desde 'ultima_actualizacion'
        df['ultima_actualizacion'] = pd.to_datetime(df['ultima_actualizacion'], errors='coerce')
        df['fecha'] = df['ultima_actualizacion'].dt.date
        df['hora'] = df['ultima_actualizacion'].dt.time

    if 'dia_semana' not in df.columns:
        df['dia_semana'] = pd.to_datetime(df['fecha']).dt.day_name()

    # Crear timestamp unificado
    df['timestamp'] = pd.to_datetime(df['fecha'].astype(str) + ' ' + df['hora'].astype(str), errors='coerce')
    df['mes'] = df['timestamp'].dt.month_name()
    df['fin_de_semana'] = df['dia_semana'].isin(['Saturday', 'Sunday'])

    return df


def main():
    # Buscar todos los CSV dentro de la carpeta
    csv_files = glob.glob(os.path.join(INPUT_DIR, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"❌ No se encontraron archivos CSV en {INPUT_DIR}")

    print(f"📂 {len(csv_files)} archivos detectados en {INPUT_DIR}")

    # Leer y concatenar todos los CSV
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)

    # Añadir las columnas de tiempo si faltan
    df = add_time_features(df)

    # Guardar resultado
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')

    print(f"✅ Archivo enriquecido guardado en {OUTPUT_PATH} ({len(df)} filas)")
    print(df.head())

if __name__ == "__main__":
    main()

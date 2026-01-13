import pandas as pd
import glob
import os

# 🗂 Ruta de los CSV crudos
RAW_PATH = "data/raw/queue_times"
CLEAN_PATH = "data/clean/"

def load_and_merge_raw_data():
    """Carga y combina todos los CSVs generados por la ingesta."""
    csv_files = glob.glob(os.path.join(RAW_PATH, "*.csv"))
    if not csv_files:
        raise FileNotFoundError("❌ No se encontraron CSVs en data/raw/. Ejecuta primero ingestion.py")
    
    dfs = [pd.read_csv(file) for file in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    print(f"✅ CSVs combinados: {len(csv_files)} archivos, {len(df)} filas totales")
    return df

def clean_unwanted_zones(df):
    """Elimina zonas no relevantes como 'Halloween' y 'Warner Beach'."""
    zones_to_remove = ["Halloween", "Warner Beach"]
    initial_rows = len(df)
    df = df[~df['zona'].isin(zones_to_remove)]
    print(f"🧹 Filtradas zonas no deseadas ({zones_to_remove}): {initial_rows - len(df)} filas eliminadas")
    return df

def main():
    os.makedirs(CLEAN_PATH, exist_ok=True)
    df = load_and_merge_raw_data()
    df = clean_unwanted_zones(df)
    output_file = os.path.join(CLEAN_PATH, "queue_times_preclean.csv")
    df.to_csv(output_file, index=False)
    print(f"💾 Archivo guardado en {output_file}")

if __name__ == "__main__":
    main()

import os
import pandas as pd

PROCESSED_DIR = "data/processed"
ENRICHED_FILE = os.path.join(PROCESSED_DIR, "queue_times_enriched.csv")
FINAL_CSV = os.path.join("data", "clean", "tiempos_final.csv")
os.makedirs(os.path.dirname(FINAL_CSV), exist_ok=True)

df_pipeline = pd.read_csv(ENRICHED_FILE)

# Asignar temporada según mes
def get_temporada(mes):
    if mes in [7,8]:
        return "alta"
    elif mes in [12,1,2]:
        return "media"
    else:
        return "baja"

df_pipeline['temporada'] = df_pipeline['mes'].apply(get_temporada)

# Combinar con CSV final histórico
if os.path.exists(FINAL_CSV):
    df_final_hist = pd.read_csv(FINAL_CSV)
    df_combined = pd.concat([df_final_hist, df_pipeline], ignore_index=True)
else:
    df_combined = df_pipeline

# Limpiar duplicados y nulos
df_combined = df_combined.drop_duplicates(subset=["fecha","hora","atraccion"], keep="last")
df_combined = df_combined.dropna(subset=["zona","atraccion","tiempo_espera","fecha","hora"])

df_combined.to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")
print(f"✅ CSV final actualizado → {FINAL_CSV} ({len(df_combined)} filas)")

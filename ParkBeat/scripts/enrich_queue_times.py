import os
import pandas as pd

PROCESSED_DIR = "data/processed"
COMBINED_FILE = os.path.join(PROCESSED_DIR, "queue_times_all_enriched.csv")
ENRICHED_FILE = os.path.join(PROCESSED_DIR, "queue_times_enriched.csv")

df = pd.read_csv(COMBINED_FILE)

# Añadir columnas de tiempo derivadas
df['hora'] = df['hora'].astype(str)
df['dia_semana'] = pd.to_datetime(df['fecha']).dt.day_name()
df['mes'] = pd.to_datetime(df['fecha']).dt.month
df['fin_de_semana'] = df['dia_semana'].isin(['Saturday','Sunday'])

df = df.drop_duplicates(subset=["fecha","hora","atraccion"], keep="last")

df.to_csv(ENRICHED_FILE, index=False, encoding='utf-8-sig')
print(f"✅ Enrich finalizado ({len(df)} filas) → {ENRICHED_FILE}")

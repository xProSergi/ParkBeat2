import os
import pandas as pd

PROCESSED_DIR = "data/processed"
PRECLEAN_FILE = os.path.join(PROCESSED_DIR, "queue_times_preclean.csv")
COMBINED_FILE = os.path.join(PROCESSED_DIR, "queue_times_all_enriched.csv")
TIEMPOS_FINAL = os.path.join("data", "clean", "tiempos_final.csv")
os.makedirs(os.path.dirname(TIEMPOS_FINAL), exist_ok=True)

df_new = pd.read_csv(PRECLEAN_FILE)

# Combinar con histórico del pipeline
if os.path.exists(COMBINED_FILE):
    df_existing = pd.read_csv(COMBINED_FILE)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
else:
    df_combined = df_new

df_combined = df_combined.drop_duplicates(subset=["fecha","hora","atraccion"], keep="last")

# Combinar con tiempos_final.csv para mantener histórico real
if os.path.exists(TIEMPOS_FINAL):
    df_final_hist = pd.read_csv(TIEMPOS_FINAL)
    df_combined = pd.concat([df_final_hist, df_combined], ignore_index=True)
    df_combined = df_combined.drop_duplicates(subset=["fecha","hora","atraccion"], keep="last")

df_combined.to_csv(COMBINED_FILE, index=False, encoding="utf-8-sig")
print(f"✅ Combine finalizado ({len(df_combined)} filas) → {COMBINED_FILE}")

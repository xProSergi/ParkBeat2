import os
import pandas as pd

RAW_DIR = os.path.join("data", "raw", "queue_times")
PROCESSED_DIR = os.path.join("data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)
PRECLEAN_FILE = os.path.join(PROCESSED_DIR, "queue_times_preclean.csv")

csvs = [os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR) if f.endswith(".csv")]
if not csvs:
    print("❌ No hay CSVs para preclean")
    exit()

df = pd.concat([pd.read_csv(f) for f in csvs], ignore_index=True)
df = df.dropna(subset=["fecha","hora","atraccion"])
# df = df[df["abierta"] == True]  # solo abiertas
df = df.drop(columns=["timestamp"], errors='ignore')
df = df.drop_duplicates(subset=["fecha","hora","atraccion"])

df.to_csv(PRECLEAN_FILE, index=False, encoding="utf-8-sig")
print(f"✅ Preclean completado ({len(df)} filas) → {PRECLEAN_FILE}")

import pandas as pd
from pathlib import Path

input_file = Path("data/processed/queue_times_all_enriched.csv")
output_file = Path("data/processed/queue_times_all_enriched.parquet")

df = pd.read_csv(input_file)
df.to_parquet(output_file, index=False)

print(f"✅ Archivo Parquet generado en: {output_file}")

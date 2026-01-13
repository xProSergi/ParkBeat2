import pandas as pd

# Cargar dataset
df = pd.read_csv("data/tiempos.csv")

# Filtrar: mantener solo los registros donde o bien la atracción está abierta,
# o si está cerrada pero con tiempo distinto de 0 (casos raros)
df = df[~((df['tiempo_espera'] == 0) & (df['abierta'] == False))]

# Guardar versión limpia
df.to_csv("data/tiempos_clean.csv", index=False)

print(f"✅ Dataset limpio guardado ({len(df)} filas)")

import pandas as pd

# 1. Cargar dataset existente
df = pd.read_csv("data/tiempos_clean.csv")

# 2. Convertir fecha a datetime
df['fecha'] = pd.to_datetime(df['fecha'])

# 3. Clasificar temporada solo por mes
def clasificar_temporada(row):
    mes = row['fecha'].month

    if mes in [3, 11]:
        return 'baja'
    elif mes in [4, 5, 9, 12]:
        return 'media'
    elif mes in [6, 7, 8, 10]:
        return 'alta'
    else:
        return 'baja'

df['temporada'] = df.apply(clasificar_temporada, axis=1)

# 4. Guardar
df.to_csv("data/tiempos_final.csv", index=False)

print("✅ Columna 'temporada' añadida correctamente (solo por mes).")
print(df[['fecha', 'temporada']].head(15))

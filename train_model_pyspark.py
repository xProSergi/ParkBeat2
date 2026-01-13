from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import *
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.regression import GBTRegressor
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
import joblib
import pandas as pd
import numpy as np
import warnings
import os
import sys
import math
warnings.filterwarnings('ignore')

# ====================================================
# 1) INICIALIZAR SPARK SESSION
# ====================================================
print("=" * 70)
print("🚀 INICIALIZANDO SPARK SESSION")
print("=" * 70)

python_executable = sys.executable  # Usa el Python actual
os.environ['PYSPARK_PYTHON'] = python_executable
os.environ['PYSPARK_DRIVER_PYTHON'] = python_executable

spark = SparkSession.builder \
    .appName("ParkWaitTimePredictor") \
    .master("local[*]") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
    .config("spark.driver.memory", "4g") \
    .config("spark.executor.memory", "4g") \
    .config("spark.sql.shuffle.partitions", "200") \
    .config("spark.pyspark.python", python_executable) \
    .config("spark.pyspark.driver.python", python_executable) \
    .getOrCreate()

print("✅ Spark Session inicializada")

# ====================================================
# 2) CARGA DE DATOS
# ====================================================
print("\n" + "=" * 70)
print("📥 CARGA DE DATOS")
print("=" * 70)

# Opción 1: Desde local
df = spark.read.csv(
    "ParkBeat/data/clean/tiempos_final.csv",
    header=True,
    inferSchema=True
)

# Opción 2: Desde S3 (descomentar cuando esté en S3)
# df = spark.read.csv(
#     "s3://parklytics-data/raw/tiempos_final.csv",
#     header=True,
#     inferSchema=True
# )

print(f"✅ Datos cargados: {df.count()} filas, {len(df.columns)} columnas")
df.printSchema()

# Estadísticas básicas
print("\n📊 Estadísticas de tiempo_espera:")
df.select("tiempo_espera").describe().show()

# ====================================================
# 3) FILTRADO DE OUTLIERS
# ====================================================
print("\n" + "=" * 70)
print("🔧 FILTRANDO OUTLIERS")
print("=" * 70)

# Calcular percentiles
stats = df.select(
    F.expr("percentile_approx(tiempo_espera, 0.005)").alias("q_low"),
    F.expr("percentile_approx(tiempo_espera, 0.995)").alias("q_high")
).collect()[0]

q_low = stats["q_low"]
q_high = stats["q_high"]

df_original_count = df.count()
df = df.filter(
    (F.col("tiempo_espera") >= q_low) & 
    (F.col("tiempo_espera") <= q_high)
)

print(f"✅ Shape después de filtrar: {df.count()} filas")
print(f"Outliers eliminados: {df_original_count - df.count()}")

# ====================================================
# 4) FUNCIONES UDF
# ====================================================
print("\n" + "=" * 70)
print("🔧 CREANDO FUNCIONES UDF")
print("=" * 70)

def parse_hora_udf(hora_str):
    """Parsear hora a float"""
    try:
        if hora_str is None:
            return 12.0
        if isinstance(hora_str, (int, float)):
            return float(hora_str)
        s = str(hora_str).strip()
        if ":" in s:
            parts = s.split(":")
            hora = int(float(parts[0]))
            minuto = int(float(parts[1])) if len(parts) > 1 else 0
            return hora + minuto / 60.0
        return float(s)
    except:
        return 12.0

def get_temporada_udf(mes):
    """Determina la temporada del año"""
    if mes in [7, 8]:
        return 3  # Muy Alta
    elif mes == 10:
        return 3  # Muy Alta
    elif mes in [4, 5, 6, 12]:
        return 2  # Alta
    elif mes in [3, 9, 11]:
        return 1  # Media
    else:
        return 0  # Baja

def es_festivo_espana_udf(fecha):
    """Detecta festivos en España"""
    try:
        if fecha is None:
            return 0
        mes = fecha.month
        dia = fecha.day
        if mes == 1 and dia == 1: return 1  # Año Nuevo
        if mes == 1 and dia == 6: return 1  # Reyes
        if mes == 5 and dia == 1: return 1  # Día del Trabajo
        if mes == 10 and dia == 12: return 1  # Día de la Hispanidad
        if mes == 11 and dia == 1: return 1  # Todos los Santos
        if mes == 12 and dia == 6: return 1  # Constitución
        if mes == 12 and dia == 8: return 1  # Inmaculada
        if mes == 12 and dia == 25: return 1  # Navidad
        return 0
    except:
        return 0

# Registrar UDFs
parse_hora = F.udf(parse_hora_udf, DoubleType())
get_temporada = F.udf(get_temporada_udf, IntegerType())
es_festivo_espana = F.udf(es_festivo_espana_udf, IntegerType())

print("✅ UDFs creadas")

# ====================================================
# 5) FEATURE ENGINEERING COMPLETO
# ====================================================
print("\n" + "=" * 70)
print("🔧 FEATURE ENGINEERING COMPLETO")
print("=" * 70)

# Convertir fecha
df = df.withColumn("fecha", F.to_date("fecha", "yyyy-MM-dd"))

# Parsear hora
df = df.withColumn("hora", parse_hora("hora"))
median_hora = df.select(F.percentile_approx("hora", 0.5).alias("median")).collect()[0]["median"]
df = df.fillna({"hora": median_hora})

# Features temporales
df = df.withColumn("mes", F.month("fecha")) \
       .withColumn("dia_mes", F.dayofmonth("fecha")) \
       .withColumn("dia_semana_num", F.dayofweek("fecha") - 1) \
       .withColumn("semana_año", F.weekofyear("fecha")) \
       .withColumn("trimestre", F.quarter("fecha")) \
       .withColumn("año", F.year("fecha"))

# Días de semana
df = df.withColumn("es_lunes", (F.col("dia_semana_num") == 0).cast("int")) \
       .withColumn("es_martes", (F.col("dia_semana_num") == 1).cast("int")) \
       .withColumn("es_miercoles", (F.col("dia_semana_num") == 2).cast("int")) \
       .withColumn("es_jueves", (F.col("dia_semana_num") == 3).cast("int")) \
       .withColumn("es_viernes", (F.col("dia_semana_num") == 4).cast("int")) \
       .withColumn("es_sabado", (F.col("dia_semana_num") == 5).cast("int")) \
       .withColumn("es_domingo", (F.col("dia_semana_num") == 6).cast("int")) \
       .withColumn("es_fin_de_semana", F.col("dia_semana_num").isin([5, 6]).cast("int")) \
       .withColumn("es_dia_laborable", F.col("dia_semana_num").isin([0, 1, 2, 3, 4]).cast("int"))

# Meses
for mes_num in range(1, 13):
    df = df.withColumn(f"es_mes_{mes_num}", (F.col("mes") == mes_num).cast("int"))

# Temporada
df = df.withColumn("temporada", get_temporada("mes"))

# Features cíclicas
pi_value = math.pi
df = df.withColumn("hora_sin", F.sin(F.lit(2 * pi_value) * F.col("hora") / 24)) \
       .withColumn("hora_cos", F.cos(F.lit(2 * pi_value) * F.col("hora") / 24)) \
       .withColumn("mes_sin", F.sin(F.lit(2 * pi_value) * F.col("mes") / 12)) \
       .withColumn("mes_cos", F.cos(F.lit(2 * pi_value) * F.col("mes") / 12)) \
       .withColumn("dia_semana_sin", F.sin(F.lit(2 * pi_value) * F.col("dia_semana_num") / 7)) \
       .withColumn("dia_semana_cos", F.cos(F.lit(2 * pi_value) * F.col("dia_semana_num") / 7)) \
       .withColumn("dia_mes_sin", F.sin(F.lit(2 * pi_value) * F.col("dia_mes") / 31)) \
       .withColumn("dia_mes_cos", F.cos(F.lit(2 * pi_value) * F.col("dia_mes") / 31)) \
       .withColumn("semana_año_sin", F.sin(F.lit(2 * pi_value) * F.col("semana_año") / 52)) \
       .withColumn("semana_año_cos", F.cos(F.lit(2 * pi_value) * F.col("semana_año") / 52))

# Interacciones
df = df.withColumn("hora_mes", F.col("hora") * F.col("mes")) \
       .withColumn("hora_dia_semana", F.col("hora") * F.col("dia_semana_num")) \
       .withColumn("mes_dia_semana", F.col("mes") * F.col("dia_semana_num")) \
       .withColumn("fin_semana_mes", F.col("es_fin_de_semana") * F.col("mes")) \
       .withColumn("temporada_dia_semana", F.col("temporada") * F.col("dia_semana_num"))

# Rellenar numéricos faltantes
for col in ["temperatura", "humedad", "sensacion_termica", "codigo_clima"]:
    if col in df.columns:
        median_val = df.select(F.percentile_approx(col, 0.5).alias("median")).collect()[0]["median"]
        df = df.fillna({col: median_val})
    else:
        df = df.withColumn(col, F.lit(0))

# Features de clima
if "codigo_clima" in df.columns:
    df = df.withColumn("es_buen_clima", F.col("codigo_clima").isin([1, 2, 3]).cast("int")) \
           .withColumn("es_mal_clima", (F.col("codigo_clima") > 3).cast("int"))

# Features de hora del día
df = df.withColumn("hora_int", F.col("hora").cast("int")) \
       .withColumn("es_hora_apertura", ((F.col("hora_int") >= 10) & (F.col("hora_int") < 11)).cast("int")) \
       .withColumn("es_hora_pico", ((F.col("hora_int") >= 11) & (F.col("hora_int") <= 16)).cast("int")) \
       .withColumn("es_hora_valle_manana", (F.col("hora_int") < 10).cast("int")) \
       .withColumn("es_hora_valle_tarde", (F.col("hora_int") > 18).cast("int")) \
       .withColumn("es_hora_valle", ((F.col("es_hora_valle_manana") == 1) | (F.col("es_hora_valle_tarde") == 1)).cast("int"))

# Festivos y puentes
df = df.withColumn("es_festivo", es_festivo_espana("fecha"))

# Flags especiales
df = df.withColumn("is_batman_octubre", 
                   (F.col("atraccion").contains("Batman") & (F.col("mes") == 10)).cast("int")) \
       .withColumn("is_octubre", (F.col("mes") == 10).cast("int")) \
       .withColumn("is_noviembre", (F.col("mes") == 11).cast("int")) \
       .withColumn("is_octubre_fin_semana", ((F.col("mes") == 10) & (F.col("es_fin_de_semana") == 1)).cast("int")) \
       .withColumn("is_noviembre_fin_semana", ((F.col("mes") == 11) & (F.col("es_fin_de_semana") == 1)).cast("int"))

print(f"✅ Features creadas: {len(df.columns)} columnas")

# ====================================================
# 6) FEATURES HISTÓRICAS GRANULARES
# ====================================================
print("\n" + "=" * 70)
print("📊 CREANDO FEATURES HISTÓRICAS GRANULARES")
print("=" * 70)

# Histórico por mes
hist_mes = df.groupBy("atraccion", "mes") \
    .agg(
        F.count("*").alias("count_mes"),
        F.mean("tiempo_espera").alias("mean_mes"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_mes"),
        F.stddev("tiempo_espera").alias("std_mes"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_mes"),
        F.expr("percentile_approx(tiempo_espera, 0.90)").alias("p90_mes"),
        F.expr("percentile_approx(tiempo_espera, 0.95)").alias("p95_mes")
    )

# Histórico por hora
hist_hora = df.groupBy("atraccion", "hora_int") \
    .agg(
        F.count("*").alias("count_hora"),
        F.mean("tiempo_espera").alias("mean_hora"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_hora"),
        F.stddev("tiempo_espera").alias("std_hora"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_hora"),
        F.expr("percentile_approx(tiempo_espera, 0.90)").alias("p90_hora")
    )

# Histórico por día de semana
hist_dia_semana = df.groupBy("atraccion", "dia_semana_num") \
    .agg(
        F.count("*").alias("count_dia"),
        F.mean("tiempo_espera").alias("mean_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_dia"),
        F.stddev("tiempo_espera").alias("std_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.90)").alias("p90_dia")
    )

# Histórico por mes Y día de semana
hist_mes_dia = df.groupBy("atraccion", "mes", "dia_semana_num") \
    .agg(
        F.count("*").alias("count_mes_dia"),
        F.mean("tiempo_espera").alias("mean_mes_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_mes_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_mes_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.90)").alias("p90_mes_dia")
    )

# Histórico por hora Y día de semana
hist_hora_dia = df.groupBy("atraccion", "hora_int", "dia_semana_num") \
    .agg(
        F.count("*").alias("count_hora_dia"),
        F.mean("tiempo_espera").alias("mean_hora_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_hora_dia"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_hora_dia")
    )

# Histórico por mes Y hora
hist_mes_hora = df.groupBy("atraccion", "mes", "hora_int") \
    .agg(
        F.count("*").alias("count_mes_hora"),
        F.mean("tiempo_espera").alias("mean_mes_hora"),
        F.expr("percentile_approx(tiempo_espera, 0.5)").alias("median_mes_hora"),
        F.expr("percentile_approx(tiempo_espera, 0.75)").alias("p75_mes_hora")
    )

# Cachear históricos
hist_mes = hist_mes.cache()
hist_hora = hist_hora.cache()
hist_dia_semana = hist_dia_semana.cache()
hist_mes_dia = hist_mes_dia.cache()
hist_hora_dia = hist_hora_dia.cache()
hist_mes_hora = hist_mes_hora.cache()

print("✅ Históricos calculados")

# Merge con df principal
print("Haciendo merge de features históricas...")
df = df.join(hist_mes, on=["atraccion", "mes"], how="left")
df = df.join(hist_hora, on=["atraccion", "hora_int"], how="left")
df = df.join(hist_dia_semana, on=["atraccion", "dia_semana_num"], how="left")
df = df.join(hist_mes_dia, on=["atraccion", "mes", "dia_semana_num"], how="left")
df = df.join(hist_hora_dia, on=["atraccion", "hora_int", "dia_semana_num"], how="left")
df = df.join(hist_mes_hora, on=["atraccion", "mes", "hora_int"], how="left")

# Rellenar valores faltantes
global_stats = df.select(
    F.mean("tiempo_espera").alias("global_mean"),
    F.expr("percentile_approx(tiempo_espera, 0.5)").alias("global_median"),
    F.stddev("tiempo_espera").alias("global_std"),
    F.expr("percentile_approx(tiempo_espera, 0.75)").alias("global_p75"),
    F.expr("percentile_approx(tiempo_espera, 0.90)").alias("global_p90"),
    F.expr("percentile_approx(tiempo_espera, 0.95)").alias("global_p95")
).collect()[0]

fill_values = {
    "mean": global_stats["global_mean"],
    "median": global_stats["global_median"],
    "std": global_stats["global_std"],
    "p75": global_stats["global_p75"],
    "p90": global_stats["global_p90"],
    "p95": global_stats["global_p95"]
}

# Aplicar fillna
for col in df.columns:
    if col.startswith("count_"):
        df = df.fillna({col: 0})
    elif "mean" in col:
        df = df.fillna({col: fill_values["mean"]})
    elif "median" in col:
        df = df.fillna({col: fill_values["median"]})
    elif "std" in col:
        df = df.fillna({col: fill_values["std"]})
    elif "p75" in col:
        df = df.fillna({col: fill_values["p75"]})
    elif "p90" in col:
        df = df.fillna({col: fill_values["p90"]})
    elif "p95" in col:
        df = df.fillna({col: fill_values["p95"]})

print(f"✅ Features finales: {len(df.columns)} columnas")

# ====================================================
# 7) ENCODING CATEGÓRICO
# ====================================================
print("\n" + "=" * 70)
print("🔤 ENCODING CATEGÓRICO")
print("=" * 70)

# Target encoding para zona y atraccion
categorical_cols = ["zona", "atraccion"]
encoding_maps = {}

for col in categorical_cols:
    if col in df.columns:
        # Calcular target encoding
        target_enc = df.groupBy(col) \
            .agg(F.mean("tiempo_espera").alias(f"{col}_enc")) \
            .cache()
        
        # Convertir a diccionario para guardar
        target_enc_pd = target_enc.toPandas()
        encoding_maps[col] = dict(zip(target_enc_pd[col], target_enc_pd[f"{col}_enc"]))
        
        # Join con df
        df = df.join(target_enc, on=col, how="left")
        
        # Rellenar con media global
        global_mean = fill_values["mean"]
        df = df.fillna({f"{col}_enc": global_mean})
        
        # Frecuencia encoding
        freq_enc = df.groupBy(col) \
            .agg(F.count("*").alias(f"{col}_freq")) \
            .cache()
        
        df = df.join(freq_enc, on=col, how="left")
        df = df.fillna({f"{col}_freq": 0})

print("✅ Encoding categórico completado")

# ====================================================
# 8) PREPARACIÓN PARA MODELO
# ====================================================
print("\n" + "=" * 70)
print("🎯 PREPARACIÓN DE DATOS PARA MODELO")
print("=" * 70)

# Seleccionar features (excluir target y columnas no útiles)
drop_cols = ["tiempo_espera", "fecha", "atraccion", "zona"]
feature_cols = [c for c in df.columns if c not in drop_cols]

# Separar en train/test
train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)

print(f"✅ Train: {train_df.count()}, Test: {test_df.count()}")

# Cachear
train_df = train_df.cache()
test_df = test_df.cache()

# ====================================================
# 9) ENTRENAMIENTO DEL MODELO
# ====================================================
print("\n" + "=" * 70)
print("🚀 ENTRENAMIENTO DEL MODELO (GBT)")
print("=" * 70)

# Seleccionar solo columnas numéricas
numeric_cols = [c for c in feature_cols 
                if train_df.schema[c].dataType in [IntegerType(), DoubleType(), FloatType(), LongType()]]

print(f"Features numéricas: {len(numeric_cols)}")

# VectorAssembler
assembler = VectorAssembler(inputCols=numeric_cols, outputCol="features")

# Escalador
scaler = StandardScaler(inputCol="features", outputCol="scaledFeatures")

# Modelo GBT (similar a XGBoost)
gbt = GBTRegressor(
    featuresCol="scaledFeatures",
    labelCol="tiempo_espera",
    maxIter=100,
    maxDepth=8,
    stepSize=0.05,
    seed=42
)

# Pipeline
pipeline = Pipeline(stages=[assembler, scaler, gbt])

print("Entrenando modelo...")
model = pipeline.fit(train_df)

print("✅ Modelo entrenado")

# ====================================================
# 10) EVALUACIÓN
# ====================================================
print("\n" + "=" * 70)
print("📈 EVALUACIÓN")
print("=" * 70)

# Predicciones
predictions = model.transform(test_df)

# Evaluador
evaluator = RegressionEvaluator(
    labelCol="tiempo_espera",
    predictionCol="prediction",
    metricName="rmse"
)

rmse = evaluator.evaluate(predictions)
print(f"✅ RMSE: {rmse:.2f} minutos")

# Más métricas
mae_eval = RegressionEvaluator(labelCol="tiempo_espera", predictionCol="prediction", metricName="mae")
r2_eval = RegressionEvaluator(labelCol="tiempo_espera", predictionCol="prediction", metricName="r2")

mae = mae_eval.evaluate(predictions)
r2 = r2_eval.evaluate(predictions)

print(f"✅ MAE: {mae:.2f} minutos")
print(f"✅ R²: {r2:.4f}")

# ====================================================
# 11) GUARDAR MODELO Y ARTEFACTOS
# ====================================================
print("\n" + "=" * 70)
print("💾 GUARDANDO MODELO Y ARTEFACTOS")
print("=" * 70)

import os
os.makedirs("ParkBeat/models", exist_ok=True)

# Guardar modelo Spark (opcional, para uso con Spark)
# NOTA: En Windows puede fallar por problemas con Hadoop nativo
# No es necesario para Lambda, así que lo comentamos o manejamos el error
model_path = "../models/spark_model"
try:
    model.write().overwrite().save(model_path)
    print(f"✅ Modelo Spark guardado en: {model_path}")
except Exception as e:
    print(f"⚠️ No se pudo guardar modelo Spark (problema conocido en Windows): {str(e)}")
    print("   Esto es normal y no afecta - Lambda usará tu modelo XGBoost existente")

# Convertir históricos a pandas y guardar como joblib
print("Convirtiendo históricos a pandas...")
hist_mes_pd = hist_mes.toPandas()
hist_hora_pd = hist_hora.toPandas()
hist_dia_semana_pd = hist_dia_semana.toPandas()
hist_mes_dia_pd = hist_mes_dia.toPandas()
hist_hora_dia_pd = hist_hora_dia.toPandas()
hist_mes_hora_pd = hist_mes_hora.toPandas()

# Guardar históricos
joblib.dump(hist_mes_pd, "ParkBeat/models/hist_mes.pkl")
joblib.dump(hist_hora_pd, "ParkBeat/models/hist_hora.pkl")
joblib.dump(hist_dia_semana_pd, "ParkBeat/models/hist_dia_semana.pkl")
joblib.dump(hist_mes_dia_pd, "ParkBeat/models/hist_mes_dia.pkl")
joblib.dump(hist_hora_dia_pd, "ParkBeat/models/hist_hora_dia.pkl")
joblib.dump(hist_mes_hora_pd, "ParkBeat/models/hist_mes_hora.pkl")
print("✅ Históricos guardados")

# Guardar encoding maps
joblib.dump(encoding_maps, "ParkBeat/models/xgb_encoding_professional.pkl")
print("✅ Encoding maps guardados")

# Guardar columnas de entrenamiento
joblib.dump(numeric_cols, "ParkBeat/models/xgb_columns_professional.pkl")
print("✅ Columnas guardadas")

# Guardar df procesado (muestra pequeña para referencia)
df_sample = df.limit(1000).toPandas()
joblib.dump(df_sample, "ParkBeat/models/df_processed.pkl")
print("✅ DataFrame procesado guardado")

# NOTA: Para usar en Lambda, necesitarás convertir el modelo Spark a formato compatible
# Opción 1: Usar tu modelo pandas/XGBoost existente
# Opción 2: Convertir modelo Spark (más complejo)

print("\n" + "=" * 70)
print("✅ ENTRENAMIENTO COMPLETADO")
print("=" * 70)
print("\n📝 NOTA: Para usar en Lambda, usa tu modelo XGBoost existente")
print("   o convierte este modelo Spark a formato compatible")

# Cerrar Spark
spark.stop()
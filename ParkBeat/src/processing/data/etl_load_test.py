import os
from pyspark.sql import SparkSession

# --- Configuración de entorno ---
os.environ["JAVA_HOME"] = "C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.17.10-hotspot"
os.environ["SPARK_HOME"] = "C:\\dev\\spark\\spark-3.5.1-bin-hadoop3"
os.environ["HADOOP_HOME"] = "C:\\dev\\spark\\spark-3.5.1-bin-hadoop3"

# --- Crear SparkSession ---
spark = SparkSession.builder \
    .appName("Parklytics_ETL_Load_Test") \
    .master("local[*]") \
    .getOrCreate()

print("✅ SparkSession creada correctamente.")
print(f"Versión de Spark: {spark.version}\n")

# --- Ruta del dataset ---
data_path = "C:/Parklytics/src/processing/data/raw/data.csv"

# --- Lectura del CSV ---
df = spark.read.csv(data_path, header=True, inferSchema=True)

print("📄 Datos cargados desde CSV:")
df.show()

print("🧱 Esquema del DataFrame:")
df.printSchema()

# --- Estadísticas básicas ---
print("📊 Descripción estadística:")
df.describe().show()

# --- Finalizar sesión ---
spark.stop()
print("\n✅ Proceso completado con éxito.")

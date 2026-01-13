import os
import sys

# 1. Configurar variables de entorno (Ajusta la ruta a donde pongas tu carpeta hadoop)
os.environ['HADOOP_HOME'] = r'C:\hadoop' 
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

from pyspark.sql import SparkSession

try:
    # 2. Intentar crear la sesión
    spark = SparkSession.builder \
        .appName("PruebaWindows") \
        .config("spark.driver.host", "localhost") \
        .getOrCreate()
        
    print("✅ PySpark instalado y sesión creada correctamente")

except Exception as e:
    print(f"❌ Error al iniciar PySpark: {e}")
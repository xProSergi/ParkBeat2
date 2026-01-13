# ====================================================
# Script para crear package de Lambda (SOLO CÓDIGO)
# ====================================================
# Este script crea un paquete pequeño solo con el código Lambda
# Las dependencias pesadas deben estar en un Lambda Layer separado
# Ejecuta primero: python scripts/create_lambda_layer.py

import os
import shutil
import zipfile
from pathlib import Path

# Directorios
PROJECT_DIR = Path('.')
LAMBDA_DIR = PROJECT_DIR / 'lambda_deployment'
LAMBDA_ZIP = PROJECT_DIR / 'lambda_function.zip'

# Limpiar directorio anterior
if LAMBDA_DIR.exists():
    print("🧹 Limpiando directorio anterior...")
    shutil.rmtree(LAMBDA_DIR)

# Crear directorio
LAMBDA_DIR.mkdir(exist_ok=True)
print(f"📁 Directorio creado: {LAMBDA_DIR}")

# Copiar lambda_function.py
print("📋 Copiando lambda_function.py...")
if not (PROJECT_DIR / 'lambda_function.py').exists():
    print("❌ ERROR: No se encontró lambda_function.py")
    print("   Asegúrate de estar en el directorio raíz del proyecto")
    exit(1)

shutil.copy(PROJECT_DIR / 'lambda_function.py', LAMBDA_DIR / 'lambda_function.py')
print("   ✅ lambda_function.py copiado")

# NOTA: NO instalamos dependencias aquí porque estarán en el Layer
# boto3 ya está disponible en el runtime de Lambda, no necesita instalarse

# Crear ZIP (solo con el código, sin dependencias)
print("\n📦 Creando ZIP (solo código)...")
if LAMBDA_ZIP.exists():
    LAMBDA_ZIP.unlink()

with zipfile.ZipFile(LAMBDA_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Agregar lambda_function.py en la raíz del ZIP
    zipf.write(LAMBDA_DIR / 'lambda_function.py', 'lambda_function.py')

# Verificar tamaño
size_mb = LAMBDA_ZIP.stat().st_size / (1024 * 1024)
print(f"✅ ZIP creado: {LAMBDA_ZIP}")
print(f"   Tamaño: {size_mb:.2f} MB")

if size_mb < 1:
    print("   ✅ Tamaño óptimo (muy pequeño, perfecto para Lambda)")

print("\n📋 IMPORTANTE - Configuración en Lambda:")
print("   1. Sube este ZIP a tu función Lambda")
print("   2. Asegúrate de tener un Layer con las dependencias:")
print("      - pandas, numpy, scikit-learn, xgboost, joblib")
print("   3. En la configuración de la función Lambda:")
print("      - Ve a 'Layers' > 'Add a layer'")
print("      - Selecciona tu Layer con las dependencias")
print("   4. Handler: lambda_function.lambda_handler")

print("\n✅ Package listo para subir a Lambda")
print("   Recuerda: Las dependencias deben estar en un Layer separado")

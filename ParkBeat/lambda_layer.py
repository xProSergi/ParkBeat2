import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Directorios
PROJECT_DIR = Path('.')
LAYER_DIR = PROJECT_DIR / 'lambda_layer'
LAYER_PYTHON_DIR = LAYER_DIR / 'python'
LAYER_ZIP = PROJECT_DIR / 'lambda_layer.zip'

# Limpiar directorio anterior
if LAYER_DIR.exists():
    print("🧹 Limpiando directorio anterior...")
    shutil.rmtree(LAYER_DIR)

# Crear estructura de directorios para Layer
# IMPORTANTE: Lambda Layers requiere la estructura python/lib/python3.x/site-packages/
LAYER_PYTHON_DIR.mkdir(parents=True, exist_ok=True)
print(f"📁 Directorio creado: {LAYER_PYTHON_DIR}")

# Dependencias pesadas para el Layer
# boto3 NO se incluye porque ya está disponible en Lambda runtime
dependencies = [
    'pandas>=1.5.0',
    'numpy>=1.23.0',
    'scikit-learn>=1.2.0',
    'xgboost>=1.7.0',
    'joblib>=1.2.0'
]

print("\n📦 Instalando dependencias en el Layer...")
print("   Esto puede tardar varios minutos...")

# Instalar dependencias en el directorio python/
for dep in dependencies:
    print(f"  Instalando {dep}...")
    subprocess.run([
        'pip', 'install', dep, 
        '-t', str(LAYER_PYTHON_DIR), 
        '--quiet',
        '--no-cache-dir'
    ], check=True)

print("\n✅ Dependencias instaladas")

# Verificar que joblib esté instalado
joblib_path = LAYER_PYTHON_DIR / 'joblib'
if not joblib_path.exists():
    print("⚠️ joblib no encontrado, reinstalando...")
    subprocess.run([
        'pip', 'install', 'joblib>=1.2.0', 
        '-t', str(LAYER_PYTHON_DIR), 
        '--upgrade', 
        '--no-cache-dir'
    ], check=True)

# Crear ZIP del Layer
# IMPORTANTE: El ZIP debe contener la carpeta 'python/' en la raíz
print("\n📦 Creando ZIP del Layer...")
if LAYER_ZIP.exists():
    LAYER_ZIP.unlink()

with zipfile.ZipFile(LAYER_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Agregar todo el contenido de python/ manteniendo la estructura
    for root, dirs, files in os.walk(LAYER_PYTHON_DIR):
        # Excluir __pycache__ y .pyc
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith('.pyc'):
                continue
            file_path = Path(root) / file
            # Mantener estructura: python/lib/python3.x/site-packages/...
            arcname = file_path.relative_to(LAYER_DIR)
            zipf.write(file_path, arcname)

# Verificar tamaño
size_mb = LAYER_ZIP.stat().st_size / (1024 * 1024)
print(f"✅ Layer ZIP creado: {LAYER_ZIP}")
print(f"   Tamaño: {size_mb:.2f} MB")

# Verificar tamaño descomprimido aproximado
uncompressed_size = sum(
    f.stat().st_size for f in LAYER_PYTHON_DIR.rglob('*') if f.is_file()
) / (1024 * 1024)
print(f"   Tamaño descomprimido (aprox): {uncompressed_size:.2f} MB")

if size_mb > 50:
    print("\n⚠️ ADVERTENCIA: El Layer ZIP es mayor a 50MB")
    print("   Necesitarás subirlo a S3 primero y luego crear el Layer desde S3")

if uncompressed_size > 250:
    print("\n⚠️ ADVERTENCIA: El Layer descomprimido excede 250MB")
    print("   Considera dividir en múltiples Layers o optimizar dependencias")

print("\n📋 PRÓXIMOS PASOS:")
print("   1. Sube lambda_layer.zip a S3:")
print("      aws s3 cp lambda_layer.zip s3://tu-bucket/lambda_layer.zip")
print("   2. Crea el Layer desde la consola AWS Lambda:")
print("      - Ve a Layers > Create layer")
print("      - Selecciona 'Upload a file from Amazon S3'")
print("      - Ingresa la URL de S3")
print("      - Compatible con: Python 3.9, 3.10, 3.11")
print("   3. O usa AWS CLI:")
print("      aws lambda publish-layer-version \\")
print("        --layer-name parklytics-dependencies \\")
print("        --zip-file fileb://lambda_layer.zip \\")
print("        --compatible-runtimes python3.9 python3.10 python3.11")

print("\n✅ Layer listo para subir a AWS")

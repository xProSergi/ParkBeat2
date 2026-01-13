# ====================================================
# Script para crear Layer de XGBoost MÍNIMO
# ====================================================
# Solo incluye los archivos esenciales necesarios para Lambda
# Usa XGBoost 1.3.0 (más antiguo pero más ligero)

import os
import sys
import shutil
import subprocess
import zipfile
from pathlib import Path

# Configurar codificación UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Directorios
PROJECT_DIR = Path('.')
TEMP_DIR = PROJECT_DIR / 'lambda_layers' / 'xgboost-temp'
LAYER_DIR = PROJECT_DIR / 'lambda_layers' / 'layer-xgboost-minimo'
LAYER_PYTHON_DIR = LAYER_DIR / 'python'
LAYER_ZIP = PROJECT_DIR / 'layer-xgboost-minimo.zip'

print("🚀 Creando Layer de XGBoost MÍNIMO")
print("   Usando version 1.3.0 (muy ligera)")
print("   Solo archivos esenciales para Lambda\n")

# Limpiar directorios anteriores
for dir_to_clean in [TEMP_DIR, LAYER_DIR]:
    if dir_to_clean.exists():
        print(f"🧹 Limpiando {dir_to_clean.name}...")
        shutil.rmtree(dir_to_clean)

# Crear estructura temporal
TEMP_PYTHON_DIR = TEMP_DIR / 'python'
TEMP_PYTHON_DIR.mkdir(parents=True, exist_ok=True)

# Crear estructura final
LAYER_PYTHON_DIR.mkdir(parents=True, exist_ok=True)
print(f"📁 Directorio creado: {LAYER_PYTHON_DIR}")

# Instalar XGBoost 1.3.0 en directorio temporal
print("\n📥 Instalando XGBoost 1.3.0 en directorio temporal...")
print("   Esto nos permitirá seleccionar solo los archivos esenciales")

try:
    # Intentar instalar versión antigua y ligera
    subprocess.run([
        'pip', 'install', 'xgboost==1.3.3',  # Versión estable y ligera
        '-t', str(TEMP_PYTHON_DIR),
        '--no-deps',  # NO instalar dependencias
        '--no-cache-dir'
    ], check=True, capture_output=True)
    
    print("   ✅ XGBoost 1.3.3 instalado")
except subprocess.CalledProcessError:
    print("   ⚠️ Error instalando 1.3.3, intentando 1.5.0...")
    try:
        subprocess.run([
            'pip', 'install', 'xgboost==1.5.0',
            '-t', str(TEMP_PYTHON_DIR),
            '--no-deps',
            '--no-cache-dir'
        ], check=True)
        print("   ✅ XGBoost 1.5.0 instalado")
    except subprocess.CalledProcessError:
        print("   ❌ Error instalando XGBoost")
        sys.exit(1)

# Encontrar directorio xgboost
xgboost_temp_dir = TEMP_PYTHON_DIR / 'xgboost'
if not xgboost_temp_dir.exists():
    print("   ❌ Directorio xgboost no encontrado después de instalar")
    sys.exit(1)

print("\n📋 Seleccionando solo archivos esenciales...")

# Crear directorio xgboost en Layer final
xgboost_layer_dir = LAYER_PYTHON_DIR / 'xgboost'
xgboost_layer_dir.mkdir(parents=True, exist_ok=True)

# Archivos y directorios ESENCIALES para XGBoost
essential_items = [
    # Archivos Python principales
    '__init__.py',
    'core.py',
    'sklearn.py',
    'callback.py',
    'compat.py',
    'dmlc-core.py',
    'rabit.py',
    'training.py',
    'plotting.py',
    
    # Directorios esenciales
    'core',
    'sklearn',
    'callback',
    'compat',
    'plotting',
    'training',
]

# Copiar solo archivos esenciales
copied_size = 0
copied_files = 0

for item_name in essential_items:
    source = xgboost_temp_dir / item_name
    if source.exists():
        if source.is_file():
            dest = xgboost_layer_dir / item_name
            shutil.copy2(source, dest)
            copied_size += source.stat().st_size
            copied_files += 1
            print(f"   ✅ Copiado: {item_name}")
        elif source.is_dir():
            dest = xgboost_layer_dir / item_name
            shutil.copytree(source, dest, dirs_exist_ok=True)
            dir_size = sum(f.stat().st_size for f in source.rglob('*') if f.is_file())
            copied_size += dir_size
            copied_files += sum(1 for _ in source.rglob('*') if _.is_file())
            print(f"   ✅ Copiado directorio: {item_name} ({dir_size / (1024*1024):.2f} MB)")

# Copiar directorio lib (contiene el binario .so)
lib_dir_source = xgboost_temp_dir / 'lib'
lib_dir_dest = xgboost_layer_dir / 'lib'
if lib_dir_source.exists():
    lib_dir_dest.mkdir(exist_ok=True)
    
    # Solo copiar archivos .so (binarios de Linux)
    for so_file in lib_dir_source.glob('*.so*'):
        # En Windows puede haber .dll, pero necesitamos .so para Lambda
        # Si no hay .so, copiamos todo pero luego limpiaremos
        shutil.copy2(so_file, lib_dir_dest / so_file.name)
        copied_size += so_file.stat().st_size
        copied_files += 1
        print(f"   ✅ Copiado binario: {so_file.name} ({so_file.stat().st_size / (1024*1024):.2f} MB)")
    
    # También copiar .dylib si existe (para compatibilidad)
    for dylib_file in lib_dir_source.glob('*.dylib*'):
        shutil.copy2(dylib_file, lib_dir_dest / dylib_file.name)
        copied_size += dylib_file.stat().st_size
        copied_files += 1
        print(f"   ✅ Copiado binario: {dylib_file.name}")

# Copiar archivos de configuración si existen
config_files = ['VERSION', 'SHORT_VERSION']
for config_file in config_files:
    source = xgboost_temp_dir / config_file
    if source.exists():
        shutil.copy2(source, xgboost_layer_dir / config_file)
        copied_size += source.stat().st_size
        copied_files += 1

# Copiar .dist-info mínimo
for dist_info in TEMP_PYTHON_DIR.glob('*.dist-info'):
    if dist_info.is_dir():
        dest_dist_info = LAYER_PYTHON_DIR / dist_info.name
        dest_dist_info.mkdir(exist_ok=True)
        
        # Solo copiar archivos esenciales
        essential_info_files = ['METADATA', 'RECORD', 'top_level.txt', 'WHEEL']
        for info_file in essential_info_files:
            source_file = dist_info / info_file
            if source_file.exists():
                shutil.copy2(source_file, dest_dist_info / info_file)
                copied_size += source_file.stat().st_size

print(f"\n✅ Archivos esenciales copiados")
print(f"   📄 Archivos: {copied_files}")
print(f"   📊 Tamaño: {copied_size / (1024*1024):.2f} MB")

# Limpiar archivos innecesarios del directorio final
print("\n🧹 Limpiando archivos innecesarios...")
removed_size = 0

# Eliminar __pycache__ y .pyc
for pycache_dir in LAYER_PYTHON_DIR.rglob('__pycache__'):
    size = sum(f.stat().st_size for f in pycache_dir.rglob('*') if f.is_file())
    shutil.rmtree(pycache_dir)
    removed_size += size

for pyc_file in LAYER_PYTHON_DIR.rglob('*.pyc'):
    size = pyc_file.stat().st_size
    pyc_file.unlink()
    removed_size += size

# Eliminar archivos innecesarios
for ext in ['.md', '.txt', '.html', '.css', '.js', '.jpg', '.png', '.svg', '.pdf', '.ipynb', '.rst']:
    for file_path in LAYER_PYTHON_DIR.rglob(f'*{ext}'):
        if file_path.is_file() and file_path.name not in ['METADATA', 'RECORD', 'top_level.txt', 'WHEEL']:
            size = file_path.stat().st_size
            file_path.unlink()
            removed_size += size

print(f"   📉 Eliminados: {removed_size / (1024*1024):.2f} MB")

# Verificar tamaño final
total_size = sum(
    f.stat().st_size for f in LAYER_PYTHON_DIR.rglob('*') if f.is_file()
)
total_size_mb = total_size / (1024 * 1024)

print(f"\n📊 Tamaño final descomprimido: {total_size_mb:.2f} MB")

if total_size_mb > 250:
    print(f"\n❌ ADVERTENCIA: Aún excede 250 MB")
    print(f"   El problema puede ser que estás en Windows y se están incluyendo binarios de Windows")
    print(f"   SOLUCIÓN: Crea el Layer en un sistema Linux o usa Docker")
    print(f"\n   Alternativamente, combina todos los Layers en uno solo:")
    print(f"   - Crea un Layer único con todas las dependencias")
    print(f"   - Esto evita duplicar archivos comunes")
else:
    print(f"   ✅ Tamaño OK (bajo 250 MB)")

# Crear ZIP
print(f"\n📦 Creando ZIP...")
if LAYER_ZIP.exists():
    LAYER_ZIP.unlink()

with zipfile.ZipFile(LAYER_ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
    files_count = 0
    for root, dirs, files in os.walk(LAYER_PYTHON_DIR):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                continue
            file_path = Path(root) / file
            arcname = file_path.relative_to(LAYER_DIR)
            zipf.write(file_path, arcname)
            files_count += 1

zip_size_mb = LAYER_ZIP.stat().st_size / (1024 * 1024)
print(f"✅ ZIP creado: {LAYER_ZIP.name}")
print(f"   📦 Tamaño comprimido: {zip_size_mb:.2f} MB")
print(f"   📊 Tamaño descomprimido: {total_size_mb:.2f} MB")
print(f"   📄 Archivos: {files_count}")

# Limpiar directorio temporal
print(f"\n🧹 Limpiando directorio temporal...")
if TEMP_DIR.exists():
    shutil.rmtree(TEMP_DIR)

# Resumen
print(f"\n{'='*60}")
print("✅ RESUMEN")
print(f"{'='*60}")
print(f"📦 Archivo: {LAYER_ZIP.name}")
print(f"📊 Tamaño comprimido: {zip_size_mb:.2f} MB")
print(f"📊 Tamaño descomprimido: {total_size_mb:.2f} MB")

if total_size_mb > 250:
    print(f"\n❌ PROBLEMA: Aún excede 250 MB")
    print(f"\n💡 SOLUCIONES:")
    print(f"   1. Crear el Layer en Linux (recomendado):")
    print(f"      - Usa una máquina Linux o Docker")
    print(f"      - Ejecuta este mismo script en Linux")
    print(f"      - Los binarios .so serán más pequeños")
    print(f"\n   2. Combinar todos los Layers en uno solo:")
    print(f"      - Crea un Layer único con todas las dependencias")
    print(f"      - Evita duplicar archivos comunes")
    print(f"      - Ejecuta: python scripts/crear_layer_combinado.py")
    print(f"\n   3. Usar Container Image en lugar de Layers:")
    print(f"      - Lambda Container Images permiten hasta 10 GB")
    print(f"      - Requiere Docker pero es más flexible")
else:
    print(f"\n✅ Layer mínimo creado exitosamente")
    print(f"   Tamaño: {total_size_mb:.2f} MB (bajo 250 MB)")
    
    print(f"\n📋 PRÓXIMOS PASOS:")
    print(f"   1. Verificar tamaño total:")
    print(f"      python scripts/verificar_tamano_layers.py")
    print(f"   2. Subir a S3:")
    print(f"      aws s3 cp {LAYER_ZIP.name} s3://tu-bucket/layers/{LAYER_ZIP.name}")
    print(f"   3. Crear Layer en Lambda:")
    print(f"      aws lambda publish-layer-version \\")
    print(f"        --layer-name parkbeat-xgboost \\")
    print(f"        --content S3Bucket=tu-bucket,S3Key=layers/{LAYER_ZIP.name} \\")
    print(f"        --compatible-runtimes python3.9 python3.10 python3.11 \\")
    print(f"        --compatible-architectures x86_64")

print(f"\n{'='*60}")

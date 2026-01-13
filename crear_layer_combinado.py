# ====================================================
# Script para crear UN SOLO Layer con TODAS las dependencias
# ====================================================
# Solución cuando múltiples Layers exceden 250 MB
# Un Layer combinado puede ser más eficiente al compartir dependencias

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
LAYER_DIR = PROJECT_DIR / 'lambda_layers' / 'layer-combinado'
LAYER_PYTHON_DIR = LAYER_DIR / 'python'
LAYER_ZIP = PROJECT_DIR / 'layer-combinado.zip'

print("🚀 Creando Layer COMBINADO con todas las dependencias")
print("   Esto evita duplicar dependencias comunes\n")

# Limpiar directorio anterior
if LAYER_DIR.exists():
    print("🧹 Limpiando directorio anterior...")
    shutil.rmtree(LAYER_DIR)

# Crear estructura
LAYER_PYTHON_DIR.mkdir(parents=True, exist_ok=True)
print(f"📁 Directorio creado: {LAYER_PYTHON_DIR}")

# Dependencias combinadas
# IMPORTANTE: Instalar en orden para que las dependencias se resuelvan correctamente
# Versiones más antiguas y ligeras que funcionan mejor
dependencies = [
    'numpy==1.21.6',          # Versión estable y ligera
    'pandas==1.3.5',          # Versión estable
    'scipy==1.7.3',           # Versión estable
    'scikit-learn==1.0.2',    # Versión estable
    'joblib==1.1.0',          # Versión estable
    'xgboost==1.5.0',         # Versión estable y ligera
]

print("\n📥 Instalando dependencias combinadas...")
print("   Esto puede tardar varios minutos...")
print("   Versiones optimizadas para reducir tamaño\n")

# Instalar dependencias en orden
for i, dep in enumerate(dependencies, 1):
    print(f"   [{i}/{len(dependencies)}] Instalando {dep}...")
    try:
        result = subprocess.run([
            'pip', 'install', dep,
            '-t', str(LAYER_PYTHON_DIR),
            '--no-cache-dir',
            '--quiet'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Si falla, mostrar el error
            print(f"      ⚠️ Error: {result.stderr[:100] if result.stderr else 'Error desconocido'}")
            raise subprocess.CalledProcessError(result.returncode, 'pip', result.stderr)
        print(f"      ✅ {dep} instalado")
    except subprocess.CalledProcessError as e:
        print(f"      ⚠️ Error instalando {dep}, continuando...")
        # Continuar aunque haya errores (algunas dependencias pueden ya estar instaladas)

print("\n✅ Dependencias instaladas")

# Función para limpiar agresivamente
def clean_aggressive(directory):
    """Elimina TODOS los archivos innecesarios"""
    removed_size = 0
    
    print("\n🧹 Limpiando archivos innecesarios...")
    
    # Eliminar directorios innecesarios
    dirs_to_remove = [
        '**/doc', '**/docs', '**/demo', '**/demos', '**/examples', '**/example',
        '**/sample', '**/samples', '**/tests', '**/test', '**/testing',
        '**/benchmark', '**/jvm-packages', '**/R-package', '**/python-package',
        '**/src', '**/include', '**/data', '**/datasets'
    ]
    
    for pattern in dirs_to_remove:
        for dir_path in directory.rglob(pattern.replace('**/', '')):
            if dir_path.exists() and dir_path.is_dir():
                try:
                    size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    shutil.rmtree(dir_path)
                    removed_size += size
                except:
                    pass
    
    # Eliminar archivos innecesarios
    file_patterns = ['*.md', '*.txt', 'LICENSE*', 'README*', 'CHANGELOG*',
                    '*.html', '*.css', '*.js', '*.map', '*.jpg', '*.jpeg',
                    '*.png', '*.gif', '*.svg', '*.pdf', '*.ipynb', '*.rst']
    
    for pattern in file_patterns:
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                # Mantener archivos esenciales de .dist-info
                if file_path.name in ['METADATA', 'RECORD', 'top_level.txt', 'WHEEL']:
                    continue
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    removed_size += size
                except:
                    pass
    
    # Eliminar __pycache__ y .pyc
    for pycache_dir in directory.rglob('__pycache__'):
        try:
            size = sum(f.stat().st_size for f in pycache_dir.rglob('*') if f.is_file())
            shutil.rmtree(pycache_dir)
            removed_size += size
        except:
            pass
    
    for pyc_file in directory.rglob('*.pyc'):
        try:
            size = pyc_file.stat().st_size
            pyc_file.unlink()
            removed_size += size
        except:
            pass
    
    # Eliminar binarios de Windows/Mac si estás en Windows (mantener solo Linux .so)
    if sys.platform == 'win32':
        for dll_file in directory.rglob('*.dll'):
            try:
                size = dll_file.stat().st_size
                dll_file.unlink()
                removed_size += size
            except:
                pass
        for dylib_file in directory.rglob('*.dylib'):
            try:
                size = dylib_file.stat().st_size
                dylib_file.unlink()
                removed_size += size
            except:
                pass
    
    return removed_size / (1024 * 1024)

# Limpiar
removed_mb = clean_aggressive(LAYER_PYTHON_DIR)
print(f"   📉 Eliminados: {removed_mb:.2f} MB")

# Verificar tamaño
total_size = sum(
    f.stat().st_size for f in LAYER_PYTHON_DIR.rglob('*') if f.is_file()
)
total_size_mb = total_size / (1024 * 1024)

print(f"\n📊 Tamaño descomprimido: {total_size_mb:.2f} MB")

if total_size_mb > 250:
    print(f"\n❌ ADVERTENCIA: Excede 250 MB")
    print(f"   Problema: Estás en Windows y se están incluyendo binarios de Windows")
    print(f"   SOLUCIÓN: Crea el Layer en Linux o usa versiones más antiguas")
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

# Resumen
print(f"\n{'='*60}")
print("✅ RESUMEN")
print(f"{'='*60}")
print(f"📦 Archivo: {LAYER_ZIP.name}")
print(f"📊 Tamaño comprimido: {zip_size_mb:.2f} MB")
print(f"📊 Tamaño descomprimido: {total_size_mb:.2f} MB")

if total_size_mb > 250:
    print(f"\n❌ PROBLEMA: Excede 250 MB")
    print(f"\n💡 MEJOR SOLUCIÓN: Crear el Layer en Linux")
    print(f"   En Windows, pip instala binarios de Windows (.dll) que son grandes")
    print(f"   Lambda necesita binarios de Linux (.so) que son más pequeños")
    print(f"\n   Opciones:")
    print(f"   1. Usar versiones más antiguas y ligeras")
    print(f"      Edita este script y cambia las versiones a más antiguas")
    print(f"\n   2. Usar el script crear_layer_simple.sh:")
    print(f"      bash scripts/crear_layer_simple.sh")
    print(f"\n   3. Usar una máquina Linux o EC2 instance")
else:
    print(f"\n✅ Layer combinado creado exitosamente")
    print(f"\n📋 VENTAJAS:")
    print(f"   - Un solo Layer en lugar de 3")
    print(f"   - Sin duplicación de dependencias")
    print(f"   - Más fácil de gestionar")
    print(f"\n📋 PRÓXIMOS PASOS:")
    print(f"   1. Subir a S3:")
    print(f"      aws s3 cp {LAYER_ZIP.name} s3://tu-bucket/layers/{LAYER_ZIP.name}")
    print(f"   2. Crear Layer en Lambda:")
    print(f"      aws lambda publish-layer-version \\")
    print(f"        --layer-name parkbeat-dependencies \\")
    print(f"        --content S3Bucket=tu-bucket,S3Key=layers/{LAYER_ZIP.name} \\")
    print(f"        --compatible-runtimes python3.9 python3.10 python3.11 \\")
    print(f"        --compatible-architectures x86_64")
    print(f"   3. Agregar SOLO este Layer a tu función Lambda")

print(f"\n{'='*60}")

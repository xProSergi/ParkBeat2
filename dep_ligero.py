# ====================================================
# Script para crear UN SOLO Layer LIGERO con TODAS las dependencias
# Versión con librerías más antiguas pero más ligeras
# Incluye: pandas, numpy, scipy, xgboost, joblib
# ====================================================

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

# Detectar versión de Python
python_version = sys.version_info
python_version_str = f"{python_version.major}.{python_version.minor}"
print(f"🐍 Python detectado: {python_version.major}.{python_version.minor}.{python_version.micro}")

# Directorios
PROJECT_DIR = Path('.')
LAYER_DIR = PROJECT_DIR / 'lambda_layers' / 'layer-completo-ligero'
LAYER_PYTHON_DIR = LAYER_DIR / 'python'
LAYER_ZIP = PROJECT_DIR / 'layer-completo-ligero.zip'

print("🚀 Creando Layer COMPLETO LIGERO con todas las dependencias")
print("   Versiones compatibles con tu versión de Python")
print("   Incluye: pandas, numpy, scipy, xgboost, joblib\n")

# Limpiar directorio anterior
if LAYER_DIR.exists():
    print("🧹 Limpiando directorio anterior...")
    shutil.rmtree(LAYER_DIR)

# Crear estructura
LAYER_PYTHON_DIR.mkdir(parents=True, exist_ok=True)
print(f"📁 Directorio creado: {LAYER_PYTHON_DIR}")

# Dependencias según versión de Python
# Python 3.11+ requiere versiones más nuevas
if python_version.major == 3 and python_version.minor >= 11:
    print("📋 Usando versiones compatibles con Python 3.11+")
    dependencies = [
        'numpy==1.23.5',          # Compatible con Python 3.11
        'pandas==1.5.3',           # Compatible con Python 3.11 y numpy 1.23
        'scipy==1.9.3',            # Compatible con Python 3.11 y numpy 1.23
        'joblib==1.2.0',           # Compatible con Python 3.11
        'xgboost==1.7.6',          # Compatible con Python 3.11
    ]
elif python_version.major == 3 and python_version.minor >= 10:
    print("📋 Usando versiones compatibles con Python 3.10")
    dependencies = [
        'numpy==1.22.4',          # Compatible con Python 3.10
        'pandas==1.4.4',          # Compatible con Python 3.10
        'scipy==1.9.3',           # Compatible con Python 3.10
        'joblib==1.1.0',          # Compatible con Python 3.10
        'xgboost==1.6.2',         # Compatible con Python 3.10
    ]
else:
    print("📋 Usando versiones compatibles con Python 3.9")
    dependencies = [
        'numpy==1.21.6',          # Compatible con Python 3.9
        'pandas==1.3.5',          # Compatible con Python 3.9
        'scipy==1.7.3',           # Compatible con Python 3.9
        'joblib==1.1.0',          # Compatible con Python 3.9
        'xgboost==1.5.0',         # Compatible con Python 3.9
    ]

print("\n📥 Instalando dependencias LIGERAS...")
print("   Versiones más antiguas para reducir tamaño")
print("   Esto puede tardar varios minutos...\n")

# Instalar dependencias en orden
failed_deps = []
for i, dep in enumerate(dependencies, 1):
    print(f"   [{i}/{len(dependencies)}] Instalando {dep}...")
    try:
        # Intentar primero con --only-binary para evitar compilación
        result = subprocess.run([
            'pip', 'install', dep,
            '-t', str(LAYER_PYTHON_DIR),
            '--no-cache-dir',
            '--only-binary=:all:',
            '--quiet'
        ], capture_output=True, text=True, timeout=600)
        
        # Si falla con --only-binary, intentar sin esa opción (permitir compilación)
        if result.returncode != 0:
            print(f"      ⚠️ No hay wheel disponible, intentando con compilación...")
            result = subprocess.run([
                'pip', 'install', dep,
                '-t', str(LAYER_PYTHON_DIR),
                '--no-cache-dir',
                '--quiet'
            ], capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            error_msg = result.stderr[:300] if result.stderr else 'Error desconocido'
            print(f"      ❌ Error: {error_msg}")
            failed_deps.append(dep)
            continue
        
        print(f"      ✅ {dep} instalado")
    except subprocess.TimeoutExpired:
        print(f"      ⚠️ Timeout instalando {dep}")
        failed_deps.append(dep)
    except Exception as e:
        print(f"      ❌ Error instalando {dep}: {str(e)[:100]}")
        failed_deps.append(dep)

if failed_deps:
    print(f"\n⚠️ ADVERTENCIA: No se pudieron instalar las siguientes dependencias:")
    for dep in failed_deps:
        print(f"   - {dep}")
    print(f"\n💡 Esto puede pasar si:")
    print(f"   1. No hay wheels disponibles para tu plataforma")
    print(f"   2. Faltan compiladores (en Windows, instala Visual Studio Build Tools)")
    print(f"   3. La versión no es compatible con tu Python")

print("\n✅ Proceso de instalación completado")

# Verificar qué dependencias se instalaron correctamente
print("\n📋 Verificando dependencias instaladas:")
installed_deps = {}
for dep_name in ['numpy', 'pandas', 'scipy', 'joblib', 'xgboost']:
    dep_dir = LAYER_PYTHON_DIR / dep_name
    if dep_dir.exists():
        installed_deps[dep_name] = True
        print(f"   ✅ {dep_name}: Instalado")
    else:
        installed_deps[dep_name] = False
        print(f"   ❌ {dep_name}: NO instalado")

# Si pandas no está instalado, intentar instalarlo de nuevo con una versión más reciente
if not installed_deps.get('pandas', False):
    print("\n🔄 Intentando instalar pandas con versión más reciente...")
    try:
        # Intentar con pandas 1.5.3 que tiene wheels para Python 3.11 en Windows
        result = subprocess.run([
            'pip', 'install', 'pandas==1.5.3',
            '-t', str(LAYER_PYTHON_DIR),
            '--no-cache-dir',
            '--only-binary=:all:',
            '--quiet'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("   ✅ pandas 1.5.3 instalado correctamente")
            installed_deps['pandas'] = True
        else:
            # Intentar sin --only-binary
            print("   🔄 Intentando sin restricción de wheels...")
            result = subprocess.run([
                'pip', 'install', 'pandas==1.5.3',
                '-t', str(LAYER_PYTHON_DIR),
                '--no-cache-dir',
                '--quiet'
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print("   ✅ pandas 1.5.3 instalado correctamente")
                installed_deps['pandas'] = True
            else:
                print(f"   ❌ Error instalando pandas: {result.stderr[:200] if result.stderr else 'Error desconocido'}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")

if not all(installed_deps.values()):
    missing = [dep for dep, installed in installed_deps.items() if not installed]
    print(f"\n⚠️ ADVERTENCIA: Faltan dependencias: {', '.join(missing)}")
    print(f"   El Layer se creará pero puede no funcionar correctamente en Lambda")
    print(f"   Considera crear el Layer en Linux/WSL donde hay más wheels disponibles")

# Función para limpiar agresivamente (misma que el script optimizado)
def clean_aggressive(directory):
    """Elimina TODOS los archivos innecesarios para reducir tamaño"""
    removed_size = 0
    removed_files = 0
    
    print("\n🧹 Limpiando archivos innecesarios agresivamente...")
    
    # Eliminar directorios innecesarios
    dirs_to_remove = [
        'doc', 'docs', 'demo', 'demos', 'examples', 'example',
        'sample', 'samples', 'tests', 'test', 'testing',
        'benchmark', 'jvm-packages', 'R-package', 'python-package',
        'src', 'include', 'data', 'datasets', 'notebooks', 'notebook',
        'benchmarks', 'bench', 'tools', 'util', 'utils'
    ]
    
    for dir_name in dirs_to_remove:
        for dir_path in directory.rglob(dir_name):
            if dir_path.exists() and dir_path.is_dir():
                try:
                    size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    shutil.rmtree(dir_path)
                    removed_size += size
                    removed_files += 1
                except:
                    pass
    
    # Eliminar archivos innecesarios
    file_patterns = [
        '*.md', '*.txt', 'LICENSE*', 'README*', 'CHANGELOG*', 'HISTORY*',
        '*.html', '*.css', '*.js', '*.map', '*.jpg', '*.jpeg',
        '*.png', '*.gif', '*.svg', '*.pdf', '*.ipynb', '*.rst',
        '*.pyx', '*.pxd', '*.pxi', '*.c', '*.h', '*.cpp', '*.hpp',
        '*.cmake', 'CMakeLists.txt', 'setup.py', '*.egg-info'
    ]
    
    for pattern in file_patterns:
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                if file_path.parent.name.endswith('.dist-info'):
                    if file_path.name in ['METADATA', 'RECORD', 'top_level.txt', 'WHEEL']:
                        continue
                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    removed_size += size
                    removed_files += 1
                except:
                    pass
    
    # Eliminar __pycache__ y .pyc
    for pycache_dir in directory.rglob('__pycache__'):
        try:
            size = sum(f.stat().st_size for f in pycache_dir.rglob('*') if f.is_file())
            shutil.rmtree(pycache_dir)
            removed_size += size
            removed_files += 1
        except:
            pass
    
    for pyc_file in directory.rglob('*.pyc'):
        try:
            size = pyc_file.stat().st_size
            pyc_file.unlink()
            removed_size += size
            removed_files += 1
        except:
            pass
    
    # Eliminar binarios de Windows/Mac
    if sys.platform == 'win32':
        for dll_file in directory.rglob('*.dll'):
            try:
                size = dll_file.stat().st_size
                dll_file.unlink()
                removed_size += size
                removed_files += 1
            except:
                pass
        for dylib_file in directory.rglob('*.dylib'):
            try:
                size = dylib_file.stat().st_size
                dylib_file.unlink()
                removed_size += size
                removed_files += 1
            except:
                pass
    
    # Optimización especial para pandas
    pandas_dir = directory / 'pandas'
    if pandas_dir.exists():
        for locale_dir in pandas_dir.rglob('locale'):
            if locale_dir.exists() and locale_dir.is_dir():
                en_us_dir = locale_dir / 'en_US'
                if en_us_dir.exists():
                    for item in locale_dir.iterdir():
                        if item.name != 'en_US' and item.is_dir():
                            try:
                                size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                                shutil.rmtree(item)
                                removed_size += size
                            except:
                                pass
    
    # Optimización especial para xgboost
    xgboost_dir = directory / 'xgboost'
    if xgboost_dir.exists():
        for item in ['doc', 'docs', 'demo', 'demos', 'examples', 'tests', 'test']:
            item_path = xgboost_dir / item
            if item_path.exists() and item_path.is_dir():
                try:
                    size = sum(f.stat().st_size for f in item_path.rglob('*') if f.is_file())
                    shutil.rmtree(item_path)
                    removed_size += size
                except:
                    pass
    
    return removed_size / (1024 * 1024), removed_files

# Limpiar
removed_mb, removed_files = clean_aggressive(LAYER_PYTHON_DIR)
print(f"   📉 Eliminados: {removed_mb:.2f} MB en {removed_files} archivos/directorios")

# Verificar tamaño
total_size = sum(
    f.stat().st_size for f in LAYER_PYTHON_DIR.rglob('*') if f.is_file()
)
total_size_mb = total_size / (1024 * 1024)

print(f"\n📊 Tamaño descomprimido: {total_size_mb:.2f} MB")

# Verificar dependencias instaladas
print("\n📋 Dependencias instaladas:")
for dep_name in ['numpy', 'pandas', 'scipy', 'joblib', 'xgboost']:
    dep_dir = LAYER_PYTHON_DIR / dep_name
    if dep_dir.exists():
        dep_size = sum(f.stat().st_size for f in dep_dir.rglob('*') if f.is_file()) / (1024 * 1024)
        print(f"   ✅ {dep_name}: {dep_size:.2f} MB")
    else:
        print(f"   ❌ {dep_name}: NO encontrado")

if total_size_mb > 250:
    print(f"\n❌ ADVERTENCIA: Aún excede 250 MB ({total_size_mb:.2f} MB)")
    print(f"   Esto puede pasar si estás en Windows (binarios .dll más grandes)")
    print(f"   SOLUCIÓN: Crear el Layer en Linux o usar Docker/EC2")
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
print(f"📉 Espacio liberado: {removed_mb:.2f} MB")

if total_size_mb > 250:
    print(f"\n❌ PROBLEMA: Aún excede 250 MB")
    print(f"\n💡 SOLUCIÓN DEFINITIVA:")
    print(f"   Crear el Layer en Linux (no Windows)")
    print(f"   Windows instala binarios .dll que son más grandes")
    print(f"   Lambda necesita binarios .so de Linux")
    print(f"\n   Opciones:")
    print(f"   1. Usar WSL (Windows Subsystem for Linux)")
    print(f"   2. Usar Docker con imagen de Amazon Linux 2")
    print(f"   3. Usar una EC2 instance con Amazon Linux 2")
else:
    print(f"\n✅ Layer ligero creado exitosamente")
    print(f"\n📋 PRÓXIMOS PASOS:")
    print(f"   1. Subir a S3:")
    print(f"      aws s3 cp {LAYER_ZIP.name} s3://tu-bucket/layers/{LAYER_ZIP.name} --region eu-west-3")
    print(f"\n   2. Crear Layer en Lambda:")
    print(f"      aws lambda publish-layer-version \\")
    print(f"        --layer-name parklytics-completo \\")
    print(f"        --content S3Bucket=tu-bucket,S3Key=layers/{LAYER_ZIP.name} \\")
    print(f"        --compatible-runtimes python3.9 python3.10 python3.11 \\")
    print(f"        --compatible-architectures x86_64")
    print(f"\n   3. En tu función Lambda:")
    print(f"      - Elimina las capas antiguas (scipy_layer, xgboostmin, layer-joblib)")
    print(f"      - Agrega SOLO esta nueva capa (parklytics-completo)")
    print(f"      - Prueba la función")

print(f"\n{'='*60}")

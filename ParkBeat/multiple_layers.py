import os
import shutil
import subprocess
import zipfile
from pathlib import Path

# Directorios
PROJECT_DIR = Path('.')
BASE_LAYER_DIR = PROJECT_DIR / 'lambda_layers'

# Limpiar directorio anterior
if BASE_LAYER_DIR.exists():
    print("🧹 Limpiando directorios anteriores...")
    shutil.rmtree(BASE_LAYER_DIR)

BASE_LAYER_DIR.mkdir(exist_ok=True)

# Definir Layers separados
# Estrategia: Dividir por tamaño y dependencias
layers_config = {
    'layer-numpy-pandas': {
        'dependencies': ['numpy==1.24.3', 'pandas==1.5.3'],
        'description': 'NumPy y Pandas para procesamiento de datos'
    },
    'layer-sklearn': {
        'dependencies': ['scikit-learn==1.3.0', 'joblib==1.3.2'],
        'description': 'Scikit-learn y Joblib para machine learning'
    },
    'layer-xgboost': {
        'dependencies': ['xgboost==1.7.6'],
        'description': 'XGBoost para modelos avanzados'
    }
}

def clean_unnecessary_files(directory):
    """Elimina archivos innecesarios para reducir el tamaño"""
    removed_size = 0
    
    # Patrones a eliminar
    patterns = [
        '**/test', '**/tests', '**/testing', '**/__pycache__',
        '**/*.pyc', '**/*.pyo', '**/*.pyd',
        '**/docs', '**/doc', '**/*.md', '**/*.txt',
        '**/README*', '**/LICENSE*', '**/CHANGELOG*',
        '**/examples', '**/example', '**/samples',
        '**/*.ipynb', '**/data', '**/datasets',
        '**/*.egg-info'
    ]
    
    extensions = ['.html', '.css', '.js', '.map', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf']
    
    for pattern in patterns:
        for path in directory.rglob(pattern):
            if path.is_file():
                removed_size += path.stat().st_size
                path.unlink()
            elif path.is_dir():
                try:
                    removed_size += sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                    shutil.rmtree(path)
                except:
                    pass
    
    for ext in extensions:
        for path in directory.rglob(f'*{ext}'):
            if path.is_file():
                removed_size += path.stat().st_size
                path.unlink()
    
    # Limpiar .dist-info
    for dist_info in directory.rglob('*.dist-info'):
        if dist_info.is_dir():
            for item in dist_info.iterdir():
                if item.name not in ['METADATA', 'RECORD', 'top_level.txt', 'WHEEL']:
                    if item.is_file():
                        removed_size += item.stat().st_size
                        item.unlink()
                    elif item.is_dir():
                        try:
                            removed_size += sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                            shutil.rmtree(item)
                        except:
                            pass
    
    return removed_size / (1024 * 1024)  # Retornar MB eliminados

def create_layer(layer_name, dependencies, description):
    """Crea un Layer individual"""
    print(f"\n{'='*60}")
    print(f"📦 Creando Layer: {layer_name}")
    print(f"   Descripción: {description}")
    print(f"   Dependencias: {', '.join(dependencies)}")
    print(f"{'='*60}")
    
    layer_dir = BASE_LAYER_DIR / layer_name
    python_dir = layer_dir / 'python'
    python_dir.mkdir(parents=True, exist_ok=True)
    
    # Instalar dependencias
    print(f"\n📥 Instalando dependencias...")
    subprocess.run([
        'pip', 'install'] + dependencies + [
        '-t', str(python_dir),
        '--quiet',
        '--no-cache-dir'
    ], check=True)
    
    # Limpiar archivos innecesarios
    print(f"🧹 Limpiando archivos innecesarios...")
    removed_mb = clean_unnecessary_files(python_dir)
    print(f"   ✅ Eliminados {removed_mb:.2f} MB")
    
    # Verificar tamaño
    total_size = sum(
        f.stat().st_size for f in python_dir.rglob('*') if f.is_file()
    )
    total_size_mb = total_size / (1024 * 1024)
    print(f"   📊 Tamaño descomprimido: {total_size_mb:.2f} MB")
    
    if total_size_mb > 250:
        print(f"\n❌ ERROR: Layer {layer_name} excede 250 MB")
        print(f"   Considera usar versiones más antiguas o dividir más")
        return None
    
    # Crear ZIP
    layer_zip = PROJECT_DIR / f'{layer_name}.zip'
    if layer_zip.exists():
        layer_zip.unlink()
    
    print(f"📦 Creando ZIP...")
    with zipfile.ZipFile(layer_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        files_count = 0
        for root, dirs, files in os.walk(python_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith(('.pyc', '.pyo')):
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(layer_dir)
                zipf.write(file_path, arcname)
                files_count += 1
    
    zip_size_mb = layer_zip.stat().st_size / (1024 * 1024)
    print(f"   ✅ ZIP creado: {layer_zip.name}")
    print(f"   📦 Tamaño comprimido: {zip_size_mb:.2f} MB")
    print(f"   📊 Tamaño descomprimido: {total_size_mb:.2f} MB")
    print(f"   📄 Archivos: {files_count}")
    
    return {
        'name': layer_name,
        'zip_file': layer_zip,
        'size_mb': total_size_mb,
        'zip_size_mb': zip_size_mb
    }

# Crear todos los Layers
print("🚀 Creando múltiples Lambda Layers")
print("   Esto dividirá las dependencias en varios Layers más pequeños\n")

created_layers = []
for layer_name, config in layers_config.items():
    layer_info = create_layer(
        layer_name,
        config['dependencies'],
        config['description']
    )
    if layer_info:
        created_layers.append(layer_info)

# Resumen
print(f"\n{'='*60}")
print("✅ RESUMEN DE LAYERS CREADOS")
print(f"{'='*60}")

total_size = 0
for layer in created_layers:
    print(f"\n📦 {layer['name']}.zip")
    print(f"   Tamaño comprimido: {layer['zip_size_mb']:.2f} MB")
    print(f"   Tamaño descomprimido: {layer['size_mb']:.2f} MB")
    total_size += layer['size_mb']

print(f"\n📊 Tamaño total descomprimido: {total_size:.2f} MB")
print(f"   ✅ Todos los Layers están bajo el límite de 250 MB")

print(f"\n📋 PRÓXIMOS PASOS:")
print(f"   1. Sube cada Layer a S3:")
for layer in created_layers:
    print(f"      aws s3 cp {layer['zip_file'].name} s3://tu-bucket/layers/{layer['zip_file'].name}")
print(f"\n   2. Crea los Layers en Lambda (desde consola o CLI):")
for layer in created_layers:
    print(f"      aws lambda publish-layer-version \\")
    print(f"        --layer-name {layer['name']} \\")
    print(f"        --content S3Bucket=tu-bucket,S3Key=layers/{layer['zip_file'].name} \\")
    print(f"        --compatible-runtimes python3.9 python3.10 python3.11")
print(f"\n   3. Agrega TODOS los Layers a tu función Lambda:")
print(f"      - Ve a tu función Lambda > Layers > Add a layer")
print(f"      - Agrega cada uno de los {len(created_layers)} Layers")
print(f"      - El orden no importa, Lambda los combina automáticamente")

print(f"\n✅ {len(created_layers)} Layers creados exitosamente")

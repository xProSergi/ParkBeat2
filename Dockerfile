# Dockerfile para Lambda Container Image con XGBoost
# IMPORTANTE: Lambda requiere arquitectura x86_64 (amd64)
# NO usar --platform aquí, se especifica en el comando docker build
FROM public.ecr.aws/lambda/python:3.11

# Copiar función Lambda
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Instalar dependencias (SIN límite de tamaño con Container Images)
# IMPORTANTE: Los modelos fueron entrenados con numpy 2.0+, necesitamos numpy 2.0+
# Permitir que pip resuelva dependencias automáticamente para encontrar pandas compatible
RUN pip install --no-cache-dir --only-binary=:all: \
    "numpy>=2.0.0" \
    "pandas>=2.2.3" \
    "scipy>=1.11.0" \
    "scikit-learn>=1.3.0" \
    "joblib>=1.3.2" \
    "xgboost>=1.7.6" \
    boto3

# Comando por defecto (Lambda lo sobrescribirá automáticamente)
CMD [ "lambda_function.lambda_handler" ]


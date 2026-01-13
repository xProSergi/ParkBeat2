# Script para recrear integracion completa desde cero
# Elimina y recrea metodo POST e integracion

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$FUNCTION_NAME = "parkbeat-predictor"
$STAGE_NAME = "prod"

Write-Host ""
Write-Host "=== RECREANDO INTEGRACION COMPLETA ===" -ForegroundColor Yellow
Write-Host ""

# 1. Obtener API ID mas reciente
Write-Host "[1/6] Obteniendo API..." -ForegroundColor Cyan
$allApis = aws apigateway get-rest-apis --region $AWS_REGION --output json | ConvertFrom-Json
$matchingApis = $allApis.items | Where-Object { $_.name -eq $API_NAME } | Sort-Object createdDate -Descending
$apiId = $matchingApis[0].id
Write-Host "   API ID: $apiId" -ForegroundColor Green
Write-Host ""

# 2. Obtener Lambda ARN
Write-Host "[2/6] Obteniendo Lambda ARN..." -ForegroundColor Cyan
$functionArn = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text
Write-Host "   Lambda ARN: $functionArn" -ForegroundColor Green
Write-Host ""

# 3. Obtener Resource ID
Write-Host "[3/6] Obteniendo Resource ID..." -ForegroundColor Cyan
$resources = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --output json | ConvertFrom-Json
$predictResource = $resources.items | Where-Object { $_.path -eq "/predict" }
$predictId = $predictResource.id
Write-Host "   Resource ID: $predictId" -ForegroundColor Green
Write-Host ""

# 4. Eliminar metodo POST si existe (para recrearlo limpio)
Write-Host "[4/6] Eliminando metodo POST existente..." -ForegroundColor Cyan
try {
    aws apigateway delete-method --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION 2>&1 | Out-Null
    Write-Host "   Metodo POST eliminado" -ForegroundColor Green
} catch {
    Write-Host "   Metodo POST no existia (OK)" -ForegroundColor Yellow
}
Write-Host ""

# 5. Crear metodo POST desde cero
Write-Host "[5/6] Creando metodo POST desde cero..." -ForegroundColor Cyan
aws apigateway put-method `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --authorization-type NONE `
    --region $AWS_REGION 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Metodo POST creado" -ForegroundColor Green
} else {
    Write-Host "   ERROR al crear metodo POST" -ForegroundColor Red
    exit 1
}

# Configurar metodo response ANTES de la integracion
Write-Host "   Configurando metodo response..." -ForegroundColor Cyan
aws apigateway put-method-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":false}' `
    --region $AWS_REGION 2>&1 | Out-Null
Write-Host "   Metodo response configurado" -ForegroundColor Green

# Crear integracion Lambda
Write-Host "   Creando integracion Lambda..." -ForegroundColor Cyan
$integrationUri = "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${functionArn}/invocations"

aws apigateway put-integration `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --region $AWS_REGION 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Integracion Lambda creada" -ForegroundColor Green
} else {
    Write-Host "   ERROR al crear integracion" -ForegroundColor Red
    exit 1
}

# Configurar integration response
Write-Host "   Configurando integration response..." -ForegroundColor Cyan
aws apigateway put-integration-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' `
    --region $AWS_REGION 2>&1 | Out-Null
Write-Host "   Integration response configurado" -ForegroundColor Green
Write-Host ""

# 6. Verificar integracion antes de deploy
Write-Host "[6/6] Verificando integracion..." -ForegroundColor Cyan
$integrationCheck = aws apigateway get-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION --output json 2>$null | ConvertFrom-Json

if ($integrationCheck -and $integrationCheck.type -eq "AWS_PROXY") {
    Write-Host "   Integracion verificada: OK" -ForegroundColor Green
    Write-Host "   Tipo: $($integrationCheck.type)" -ForegroundColor Cyan
    Write-Host "   URI: $($integrationCheck.uri)" -ForegroundColor Cyan
} else {
    Write-Host "   ERROR: Integracion no esta correctamente configurada" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Crear deployment
Write-Host "Creando deployment..." -ForegroundColor Cyan
$deploymentResult = aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name $STAGE_NAME `
    --region $AWS_REGION `
    --description "Deployment completo - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" `
    --output json 2>&1

if ($LASTEXITCODE -eq 0) {
    $deployment = $deploymentResult | ConvertFrom-Json
    Write-Host "   Deployment creado exitosamente!" -ForegroundColor Green
    Write-Host "   Deployment ID: $($deployment.id)" -ForegroundColor Cyan
} else {
    $errorMsg = $deploymentResult | Out-String
    Write-Host "   ERROR al crear deployment:" -ForegroundColor Red
    Write-Host $errorMsg -ForegroundColor Red
    
    # Intentar obtener mas informacion
    Write-Host ""
    Write-Host "Verificando estado actual..." -ForegroundColor Yellow
    $methodCheck = aws apigateway get-method --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION --output json 2>$null
    if ($methodCheck) {
        Write-Host "   Metodo POST existe" -ForegroundColor Green
    } else {
        Write-Host "   Metodo POST NO existe" -ForegroundColor Red
    }
    
    $integrationCheck2 = aws apigateway get-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION --output json 2>$null
    if ($integrationCheck2) {
        Write-Host "   Integracion existe" -ForegroundColor Green
    } else {
        Write-Host "   Integracion NO existe" -ForegroundColor Red
    }
    
    exit 1
}
Write-Host ""

# Mostrar URL final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host "=== COMPLETADO ===" -ForegroundColor Green
Write-Host "URL: $apiUrl" -ForegroundColor Yellow
Write-Host ""

# Guardar URL
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8 -NoNewline
Write-Host "URL guardada en api_url.txt" -ForegroundColor Green
Write-Host ""

Write-Host "Prueba de nuevo tu script Python" -ForegroundColor Cyan
Write-Host ""

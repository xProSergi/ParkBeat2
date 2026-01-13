# Script completo: Corregir integracion y crear deployment
# Soluciona el error "No integration defined for method"

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$FUNCTION_NAME = "parkbeat-predictor"
$STAGE_NAME = "prod"

Write-Host ""
Write-Host "=== CORRIGIENDO INTEGRACION Y CREANDO DEPLOYMENT ===" -ForegroundColor Yellow
Write-Host ""

# 1. Obtener API ID mas reciente
Write-Host "[1/5] Obteniendo API mas reciente..." -ForegroundColor Cyan
$allApis = aws apigateway get-rest-apis --region $AWS_REGION --output json | ConvertFrom-Json
$matchingApis = $allApis.items | Where-Object { $_.name -eq $API_NAME } | Sort-Object createdDate -Descending
$apiId = $matchingApis[0].id
Write-Host "   API ID: $apiId" -ForegroundColor Green
Write-Host ""

# 2. Obtener Lambda ARN
Write-Host "[2/5] Obteniendo Lambda ARN..." -ForegroundColor Cyan
$functionArn = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text
Write-Host "   Lambda ARN: $functionArn" -ForegroundColor Green
Write-Host ""

# 3. Obtener Resource ID de /predict
Write-Host "[3/5] Obteniendo Resource ID..." -ForegroundColor Cyan
$resources = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --output json | ConvertFrom-Json
$predictResource = $resources.items | Where-Object { $_.path -eq "/predict" }

if (-not $predictResource) {
    Write-Host "   ERROR: Recurso /predict no encontrado" -ForegroundColor Red
    exit 1
}

$predictId = $predictResource.id
Write-Host "   Resource ID: $predictId" -ForegroundColor Green
Write-Host ""

# 4. Verificar y corregir metodo POST
Write-Host "[4/5] Verificando y corrigiendo metodo POST..." -ForegroundColor Cyan

# Verificar si existe metodo POST
$hasPost = $predictResource.resourceMethods.PSObject.Properties.Name -contains "POST"

if (-not $hasPost) {
    Write-Host "   Creando metodo POST..." -ForegroundColor Yellow
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
} else {
    Write-Host "   Metodo POST ya existe" -ForegroundColor Green
}

# Verificar integracion
Write-Host "   Verificando integracion..." -ForegroundColor Cyan
$integration = aws apigateway get-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION --output json 2>$null | ConvertFrom-Json

if (-not $integration -or $integration.type -ne "AWS_PROXY") {
    Write-Host "   Configurando integracion Lambda..." -ForegroundColor Yellow
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
        Write-Host "   Integracion configurada correctamente" -ForegroundColor Green
    } else {
        Write-Host "   ERROR al configurar integracion" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "   Integracion ya esta configurada: OK" -ForegroundColor Green
}

# Verificar metodo response
Write-Host "   Verificando metodo response..." -ForegroundColor Cyan
try {
    $methodResponse = aws apigateway get-method-response --rest-api-id $apiId --resource-id $predictId --http-method POST --status-code 200 --region $AWS_REGION 2>$null
    if (-not $methodResponse) {
        Write-Host "   Configurando metodo response..." -ForegroundColor Yellow
        aws apigateway put-method-response `
            --rest-api-id $apiId `
            --resource-id $predictId `
            --http-method POST `
            --status-code 200 `
            --response-parameters '{"method.response.header.Access-Control-Allow-Origin":false}' `
            --region $AWS_REGION 2>&1 | Out-Null
        Write-Host "   Metodo response configurado" -ForegroundColor Green
    }
} catch {
    Write-Host "   Configurando metodo response..." -ForegroundColor Yellow
    aws apigateway put-method-response `
        --rest-api-id $apiId `
        --resource-id $predictId `
        --http-method POST `
        --status-code 200 `
        --response-parameters '{"method.response.header.Access-Control-Allow-Origin":false}' `
        --region $AWS_REGION 2>&1 | Out-Null
}

# Verificar integration response
Write-Host "   Verificando integration response..." -ForegroundColor Cyan
try {
    $integrationResponse = aws apigateway get-integration-response --rest-api-id $apiId --resource-id $predictId --http-method POST --status-code 200 --region $AWS_REGION 2>$null
    if (-not $integrationResponse) {
        Write-Host "   Configurando integration response..." -ForegroundColor Yellow
        aws apigateway put-integration-response `
            --rest-api-id $apiId `
            --resource-id $predictId `
            --http-method POST `
            --status-code 200 `
            --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' `
            --region $AWS_REGION 2>&1 | Out-Null
        Write-Host "   Integration response configurado" -ForegroundColor Green
    }
} catch {
    Write-Host "   Configurando integration response..." -ForegroundColor Yellow
    aws apigateway put-integration-response `
        --rest-api-id $apiId `
        --resource-id $predictId `
        --http-method POST `
        --status-code 200 `
        --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' `
        --region $AWS_REGION 2>&1 | Out-Null
}

Write-Host ""

# 5. Crear deployment
Write-Host "[5/5] Creando deployment..." -ForegroundColor Cyan
$deploymentResult = aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name $STAGE_NAME `
    --region $AWS_REGION `
    --description "Initial deployment - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" `
    --output json 2>&1

if ($LASTEXITCODE -eq 0) {
    $deployment = $deploymentResult | ConvertFrom-Json
    Write-Host "   Deployment creado exitosamente!" -ForegroundColor Green
    Write-Host "   Deployment ID: $($deployment.id)" -ForegroundColor Cyan
} else {
    $errorMsg = $deploymentResult | Out-String
    if ($errorMsg -match "already exists") {
        Write-Host "   Deployment ya existe, forzando actualizacion..." -ForegroundColor Yellow
        $deploymentResult = aws apigateway create-deployment `
            --rest-api-id $apiId `
            --stage-name $STAGE_NAME `
            --region $AWS_REGION `
            --description "Update - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $deployment = $deploymentResult | ConvertFrom-Json
            Write-Host "   Deployment actualizado!" -ForegroundColor Green
        } else {
            Write-Host "   ERROR:" -ForegroundColor Red
            Write-Host $errorMsg -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "   ERROR:" -ForegroundColor Red
        Write-Host $errorMsg -ForegroundColor Red
        exit 1
    }
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

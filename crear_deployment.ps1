# Script para crear deployment de API Gateway
# Soluciona el error 403 cuando no hay deployments

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$STAGE_NAME = "prod"

Write-Host ""
Write-Host "=== CREANDO DEPLOYMENT DE API GATEWAY ===" -ForegroundColor Yellow
Write-Host ""

# 1. Obtener API ID mas reciente
Write-Host "[1/3] Obteniendo API mas reciente..." -ForegroundColor Cyan
$allApis = aws apigateway get-rest-apis --region $AWS_REGION --output json | ConvertFrom-Json
$matchingApis = $allApis.items | Where-Object { $_.name -eq $API_NAME } | Sort-Object createdDate -Descending

if ($matchingApis.Count -eq 0) {
    Write-Host "ERROR: No se encontro API '$API_NAME'" -ForegroundColor Red
    exit 1
}

$apiId = $matchingApis[0].id
Write-Host "   API ID: $apiId" -ForegroundColor Green
Write-Host ""

# 2. Verificar si el stage existe
Write-Host "[2/3] Verificando stage..." -ForegroundColor Cyan
try {
    $stage = aws apigateway get-stage --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION 2>$null
    if ($stage) {
        Write-Host "   Stage '$STAGE_NAME' existe" -ForegroundColor Green
    } else {
        Write-Host "   Stage '$STAGE_NAME' no existe, se creara automaticamente" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   Stage no existe, se creara automaticamente" -ForegroundColor Yellow
}
Write-Host ""

# 3. Crear deployment
Write-Host "[3/3] Creando deployment..." -ForegroundColor Cyan
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
    Write-Host "   Fecha: $($deployment.createdDate)" -ForegroundColor Cyan
} else {
    $errorMsg = $deploymentResult | Out-String
    if ($errorMsg -match "already exists") {
        Write-Host "   Deployment ya existe, forzando actualizacion..." -ForegroundColor Yellow
        
        # Forzar nuevo deployment
        $deploymentResult = aws apigateway create-deployment `
            --rest-api-id $apiId `
            --stage-name $STAGE_NAME `
            --region $AWS_REGION `
            --description "Update deployment - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $deployment = $deploymentResult | ConvertFrom-Json
            Write-Host "   Deployment actualizado!" -ForegroundColor Green
            Write-Host "   Deployment ID: $($deployment.id)" -ForegroundColor Cyan
        } else {
            Write-Host "   ERROR al crear deployment:" -ForegroundColor Red
            Write-Host $errorMsg -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "   ERROR al crear deployment:" -ForegroundColor Red
        Write-Host $errorMsg -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Verificar stage
Write-Host "Verificando stage final..." -ForegroundColor Cyan
$finalStage = aws apigateway get-stage --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION --output json 2>$null | ConvertFrom-Json
if ($finalStage) {
    Write-Host "   Stage '$STAGE_NAME' activo" -ForegroundColor Green
    Write-Host "   Deployment ID del stage: $($finalStage.deploymentId)" -ForegroundColor Cyan
} else {
    Write-Host "   WARNING: No se pudo verificar stage" -ForegroundColor Yellow
}
Write-Host ""

# Mostrar URL final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host "=== DEPLOYMENT COMPLETADO ===" -ForegroundColor Green
Write-Host "URL: $apiUrl" -ForegroundColor Yellow
Write-Host ""

# Guardar URL
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8 -NoNewline
Write-Host "URL guardada en api_url.txt" -ForegroundColor Green
Write-Host ""

Write-Host "Prueba de nuevo tu script Python" -ForegroundColor Cyan
Write-Host ""

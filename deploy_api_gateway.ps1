# 🚀 Script para crear API Gateway completo automáticamente
# Ahorra ~1 hora de trabajo manual

$AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "eu-west-3" }
$API_NAME = if ($env:API_NAME) { $env:API_NAME } else { "parkbeat-api" }
$FUNCTION_NAME = if ($env:FUNCTION_NAME) { $env:FUNCTION_NAME } else { "parkbeat-predictor" }
$STAGE_NAME = if ($env:STAGE_NAME) { $env:STAGE_NAME } else { "prod" }

Write-Host ""
Write-Host "Creando API Gateway completo..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Region: $AWS_REGION"
Write-Host "API Name: $API_NAME"
Write-Host "Function: $FUNCTION_NAME"
Write-Host "Stage: $STAGE_NAME"
Write-Host ""

# Verificar que Lambda existe
Write-Host "Verificando que Lambda existe..." -ForegroundColor Cyan
$lambdaExists = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>$null
if (-not $lambdaExists) {
    Write-Host "ERROR: Lambda function '$FUNCTION_NAME' no existe" -ForegroundColor Red
    Write-Host "   Crea la funcion Lambda primero con deploy_completo.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "   Lambda function existe" -ForegroundColor Green
Write-Host ""

# 1. Crear REST API
Write-Host "[1/12] Creando REST API..." -ForegroundColor Cyan
$apiId = aws apigateway create-rest-api `
    --name $API_NAME `
    --region $AWS_REGION `
    --endpoint-configuration types=REGIONAL `
    --query 'id' --output text 2>$null

if (-not $apiId) {
    # Intentar obtener API existente
    $apiId = aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='$API_NAME'].id" --output text 2>$null
    if ($apiId) {
        $apiId = $apiId.Split("`n")[0].Trim()
        Write-Host "   API ya existe, usando existente" -ForegroundColor Yellow
    }
}

if (-not $apiId) {
    Write-Host "   Error creando API" -ForegroundColor Red
    exit 1
}

Write-Host "   API ID: $apiId" -ForegroundColor Green
Write-Host ""

# 2. Obtener Root Resource ID
Write-Host "[2/12] Obteniendo Root Resource..." -ForegroundColor Cyan
$rootId = aws apigateway get-resources `
    --rest-api-id $apiId `
    --region $AWS_REGION `
    --query 'items[?path==`/`].id' --output text

Write-Host "   Root ID: $rootId" -ForegroundColor Green
Write-Host ""

# 3. Crear recurso /predict
Write-Host "[3/12] Creando recurso /predict..." -ForegroundColor Cyan
$predictId = aws apigateway get-resources `
    --rest-api-id $apiId `
    --region $AWS_REGION `
    --query "items[?path=='/predict'].id" --output text

if (-not $predictId) {
    $predictId = aws apigateway create-resource `
        --rest-api-id $apiId `
        --parent-id $rootId `
        --path-part predict `
        --region $AWS_REGION `
        --query 'id' --output text
    Write-Host "   Resource /predict creado: $predictId" -ForegroundColor Green
} else {
    Write-Host "   Resource /predict ya existe: $predictId" -ForegroundColor Yellow
}
Write-Host ""

# 4. Obtener ARN de Lambda
Write-Host "[4/12] Obteniendo ARN de Lambda..." -ForegroundColor Cyan
$functionArn = aws lambda get-function `
    --function-name $FUNCTION_NAME `
    --region $AWS_REGION `
    --query 'Configuration.FunctionArn' --output text

Write-Host "   Lambda ARN: $functionArn" -ForegroundColor Green
Write-Host ""

# 5. Dar permiso a API Gateway para invocar Lambda
Write-Host "[5/12] Configurando permisos Lambda..." -ForegroundColor Cyan
$accountId = ($functionArn -split ':')[4]
$sourceArn = "arn:aws:execute-api:${AWS_REGION}:${accountId}:${apiId}/*/*"

$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"
aws lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id $statementId `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn $sourceArn `
    --region $AWS_REGION 2>$null | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Permiso agregado" -ForegroundColor Green
} else {
    Write-Host "   Permiso ya existe (OK)" -ForegroundColor Yellow
}
Write-Host ""

# 6. Crear método POST
Write-Host "[6/12] Creando método POST..." -ForegroundColor Cyan
aws apigateway put-method `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --authorization-type NONE `
    --region $AWS_REGION 2>$null | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Metodo POST creado" -ForegroundColor Green
} else {
    Write-Host "   Metodo POST ya existe (OK)" -ForegroundColor Yellow
}
Write-Host ""

# 7. Configurar integración Lambda
Write-Host "[7/12] Configurando integración Lambda..." -ForegroundColor Cyan
$integrationUri = "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${functionArn}/invocations"

aws apigateway put-integration `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --type AWS_PROXY `
    --integration-http-method POST `
    --uri $integrationUri `
    --region $AWS_REGION 2>$null | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Integracion Lambda configurada" -ForegroundColor Green
} else {
    Write-Host "   Integracion ya existe (OK)" -ForegroundColor Yellow
}
Write-Host ""

# 8. Configurar respuesta 200
Write-Host "[8/12] Configurando respuesta 200..." -ForegroundColor Cyan
aws apigateway put-method-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":false}' `
    --region $AWS_REGION 2>$null | Out-Null

Write-Host "   Respuesta 200 configurada" -ForegroundColor Green
Write-Host ""

# 9. Configurar integración response con CORS
Write-Host "[9/12] Configurando CORS en integración..." -ForegroundColor Cyan
aws apigateway put-integration-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method POST `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' `
    --region $AWS_REGION 2>$null | Out-Null

Write-Host "   CORS configurado" -ForegroundColor Green
Write-Host ""

# 10. Crear método OPTIONS para CORS preflight
Write-Host "[10/12] Configurando método OPTIONS para CORS..." -ForegroundColor Cyan
aws apigateway put-method `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method OPTIONS `
    --authorization-type NONE `
    --region $AWS_REGION 2>$null | Out-Null

aws apigateway put-integration `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method OPTIONS `
    --type MOCK `
    --request-templates '{"application/json":"{\"statusCode\":200}"}' `
    --region $AWS_REGION 2>$null | Out-Null

aws apigateway put-method-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method OPTIONS `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":false,"method.response.header.Access-Control-Allow-Methods":false,"method.response.header.Access-Control-Allow-Origin":false}' `
    --region $AWS_REGION 2>$null | Out-Null

aws apigateway put-integration-response `
    --rest-api-id $apiId `
    --resource-id $predictId `
    --http-method OPTIONS `
    --status-code 200 `
    --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'POST,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' `
    --region $AWS_REGION 2>$null | Out-Null

Write-Host "   CORS completamente configurado" -ForegroundColor Green
Write-Host ""

# 11. Deploy API
Write-Host "[11/12] Desplegando API..." -ForegroundColor Cyan
$deploymentId = aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name $STAGE_NAME `
    --region $AWS_REGION `
    --query 'id' --output text 2>$null

if ($deploymentId) {
    Write-Host "   API desplegada en stage: $STAGE_NAME" -ForegroundColor Green
} else {
    Write-Host "   Deployment ya existe, actualizando..." -ForegroundColor Yellow
    # Forzar nuevo deployment
    aws apigateway create-deployment `
        --rest-api-id $apiId `
        --stage-name $STAGE_NAME `
        --region $AWS_REGION `
        --description "Update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 2>$null | Out-Null
    Write-Host "   API actualizada" -ForegroundColor Green
}
Write-Host ""

# 12. Mostrar información final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"

Write-Host "============================================================" -ForegroundColor Green
Write-Host "API GATEWAY COMPLETAMENTE CONFIGURADO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "URL del endpoint:" -ForegroundColor Cyan
Write-Host "   $apiUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test rapido:" -ForegroundColor Cyan
Write-Host "   `$test = @{"
Write-Host "     fecha = '2025-10-25'"
Write-Host "     hora = '12:00'"
Write-Host "     atraccion = 'Batman Gotham City Escape'"
Write-Host "     zona = 'DC Super Heroes World'"
Write-Host "     temperatura = 22"
Write-Host "     humedad = 60"
Write-Host "     codigo_clima = 3"
Write-Host "   } | ConvertTo-Json"
Write-Host ""
Write-Host "   `$test | Out-File test-api.json -Encoding utf8"
Write-Host "   Invoke-WebRequest -Uri '$apiUrl' -Method POST -Body (Get-Content test-api.json -Raw) -ContentType 'application/json' | Select-Object -ExpandProperty Content"
Write-Host ""
Write-Host "Guarda esta URL para modificar app.py:" -ForegroundColor Cyan
Write-Host "   $apiUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "COSTOS:" -ForegroundColor Cyan
Write-Host "   - API Gateway: 1M requests gratis/mes (12 meses)"
Write-Host "   - Despues: ~`$3.50/1M requests"
Write-Host "   - Total: `$0/mes (free tier) OK"
Write-Host ""

# Guardar URL en archivo
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8
Write-Host "URL guardada en: api_url.txt" -ForegroundColor Green
Write-Host ""

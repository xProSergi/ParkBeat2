# --------------------------------------------------
# 🚀 Script completo de API Gateway + Lambda
# --------------------------------------------------

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$FUNCTION_NAME = "parkbeat-predictor"
$STAGE_NAME = "prod"

Write-Host "=== Iniciando deploy API Gateway ===" -ForegroundColor Green

# 1️⃣ Verificar que Lambda existe
try {
    $lambda = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --output text
    Write-Host "Lambda encontrada: $FUNCTION_NAME" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Lambda $FUNCTION_NAME no encontrada" -ForegroundColor Red
    exit 1
}

# 2️⃣ Crear o obtener REST API
$apiId = aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='$API_NAME'].id" --output text
if (-not $apiId) {
    $apiId = aws apigateway create-rest-api --name $API_NAME --region $AWS_REGION --query 'id' --output text
    Write-Host "API creada: $apiId" -ForegroundColor Green
} else {
    Write-Host "API existente: $apiId" -ForegroundColor Yellow
}

# 3️⃣ Obtener Root Resource ID
$rootId = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --query 'items[?path==`/`].id' --output text
Write-Host "Root resource ID: $rootId" -ForegroundColor Green

# 4️⃣ Crear recurso /predict si no existe
$predictId = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --query "items[?path=='/predict'].id" --output text
if (-not $predictId) {
    $predictId = aws apigateway create-resource --rest-api-id $apiId --parent-id $rootId --path-part predict --region $AWS_REGION --query 'id' --output text
    Write-Host "/predict creado: $predictId" -ForegroundColor Green
} else {
    Write-Host "/predict ya existe: $predictId" -ForegroundColor Yellow
}

# 5️⃣ Configurar método POST
aws apigateway put-method --rest-api-id $apiId --resource-id $predictId --http-method POST --authorization-type NONE --region $AWS_REGION | Out-Null
Write-Host "POST method configurado" -ForegroundColor Green

# 6️⃣ Configurar integración Lambda
$functionArn = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text
$integrationUri = "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${functionArn}/invocations"
aws apigateway put-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --type AWS_PROXY --integration-http-method POST --uri $integrationUri --region $AWS_REGION | Out-Null
Write-Host "Integración Lambda configurada" -ForegroundColor Green

# 7️⃣ Borra permisos antiguos
try {
    $statements = aws lambda get-policy --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Policy' --output text | ConvertFrom-Json
    foreach ($s in $statements.Statement) {
        if ($s.Principal.Service -eq "apigateway.amazonaws.com") {
            aws lambda remove-permission --function-name $FUNCTION_NAME --statement-id $s.Sid --region $AWS_REGION | Out-Null
            Write-Host "Permiso viejo borrado: $($s.Sid)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "No hay permisos antiguos de API Gateway" -ForegroundColor Cyan
}

# 8️⃣ Agregar permiso correcto
$accountId = ($functionArn -split ':')[4]
$sourceArn = "arn:aws:execute-api:${AWS_REGION}:${accountId}:${apiId}/*/POST/predict"
$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"
aws lambda add-permission --function-name $FUNCTION_NAME --statement-id $statementId --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn $sourceArn --region $AWS_REGION | Out-Null
Write-Host "Permiso Lambda agregado" -ForegroundColor Green

# 9️⃣ Deploy API
$deploymentId = aws apigateway create-deployment --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION --query 'id' --output text
Write-Host "API desplegada en stage $STAGE_NAME" -ForegroundColor Green

#  🔗 URL final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host "==================================================" -ForegroundColor Green
Write-Host "API LISTA: $apiUrl" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Green

# Guardar URL en archivo
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8

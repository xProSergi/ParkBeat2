# 🚀 Script completo para desplegar API Gateway y conectar con Lambda
# Ahorra tiempo y evita errores de IDs múltiples

$AWS_REGION     = if ($env:AWS_REGION) { $env:AWS_REGION } else { "eu-west-3" }
$API_NAME       = if ($env:API_NAME) { $env:API_NAME } else { "parkbeat-api" }
$FUNCTION_NAME  = if ($env:FUNCTION_NAME) { $env:FUNCTION_NAME } else { "parkbeat-predictor" }
$STAGE_NAME     = if ($env:STAGE_NAME) { $env:STAGE_NAME } else { "prod" }

Write-Host "`n=== Iniciando deploy API Gateway ===" -ForegroundColor Green
Write-Host "Region: $AWS_REGION"
Write-Host "API Name: $API_NAME"
Write-Host "Lambda Function: $FUNCTION_NAME"
Write-Host "Stage: $STAGE_NAME`n"

# 1️⃣ Verificar que Lambda existe
Write-Host "[1/12] Verificando Lambda..." -ForegroundColor Cyan
try {
    $lambda = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --output text
    Write-Host "Lambda encontrada: $FUNCTION_NAME" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Lambda function '$FUNCTION_NAME' no existe. Crea la función primero." -ForegroundColor Red
    exit 1
}

# 2️⃣ Obtener o crear REST API
Write-Host "[2/12] Creando o usando API existente..." -ForegroundColor Cyan
$apiId = aws apigateway create-rest-api --name $API_NAME --region $AWS_REGION --endpoint-configuration types=REGIONAL --query 'id' --output text 2>$null

if (-not $apiId) {
    $apiId = aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='$API_NAME'].id" --output text
    $apiId = $apiId.Split(" ")[0].Trim()
    Write-Host "API existente encontrada: $apiId" -ForegroundColor Yellow
} else {
    Write-Host "API creada: $apiId" -ForegroundColor Green
}

# 3️⃣ Obtener Root Resource ID
$rootId = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --query "items[?path=='/'].id" --output text
$rootId = $rootId.Split(" ")[0].Trim()
Write-Host "Root Resource ID: $rootId" -ForegroundColor Green

# 4️⃣ Crear recurso /predict
$predictId = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --query "items[?path=='/predict'].id" --output text
if (-not $predictId) {
    $predictId = aws apigateway create-resource --rest-api-id $apiId --parent-id $rootId --path-part predict --region $AWS_REGION --query 'id' --output text
    Write-Host "/predict creado: $predictId" -ForegroundColor Green
} else {
    $predictId = $predictId.Split(" ")[0].Trim()
    Write-Host "/predict ya existe: $predictId" -ForegroundColor Yellow
}

# 5️⃣ Obtener ARN de Lambda
$functionArn = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text
Write-Host "Lambda ARN: $functionArn" -ForegroundColor Green

# 6️⃣ Permitir que API Gateway invoque Lambda
$accountId = ($functionArn -split ':')[4]
$sourceArn = "arn:aws:execute-api:${AWS_REGION}:${accountId}:${apiId}/*/POST/predict"
$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"

try {
    aws lambda add-permission --function-name $FUNCTION_NAME --statement-id $statementId --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn $sourceArn --region $AWS_REGION
    Write-Host "Permiso Lambda agregado" -ForegroundColor Green
} catch {
    Write-Host "Permiso Lambda ya existe (OK)" -ForegroundColor Yellow
}

# 7️⃣ Crear método POST
aws apigateway put-method --rest-api-id $apiId --resource-id $predictId --http-method POST --authorization-type NONE --region $AWS_REGION
Write-Host "Método POST creado" -ForegroundColor Green

# 8️⃣ Configurar integración Lambda
$integrationUri = "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${functionArn}/invocations"
aws apigateway put-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --type AWS_PROXY --integration-http-method POST --uri $integrationUri --region $AWS_REGION
Write-Host "Integración Lambda configurada" -ForegroundColor Green

# 9️⃣ Configurar método OPTIONS para CORS
aws apigateway put-method --rest-api-id $apiId --resource-id $predictId --http-method OPTIONS --authorization-type NONE --region $AWS_REGION
aws apigateway put-integration --rest-api-id $apiId --resource-id $predictId --http-method OPTIONS --type MOCK --request-templates '{"application/json":"{\"statusCode\":200}"}' --region $AWS_REGION
aws apigateway put-method-response --rest-api-id $apiId --resource-id $predictId --http-method OPTIONS --status-code 200 --response-parameters '{"method.response.header.Access-Control-Allow-Headers":false,"method.response.header.Access-Control-Allow-Methods":false,"method.response.header.Access-Control-Allow-Origin":false}' --region $AWS_REGION
aws apigateway put-integration-response --rest-api-id $apiId --resource-id $predictId --http-method OPTIONS --status-code 200 --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"Content-Type,X-Amz-Date,Authorization,X-Api-Key","method.response.header.Access-Control-Allow-Methods":"POST,OPTIONS","method.response.header.Access-Control-Allow-Origin":"*"}' --region $AWS_REGION
Write-Host "CORS configurado" -ForegroundColor Green

# 🔟 Deploy API
$deploymentId = aws apigateway create-deployment --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION --query 'id' --output text 2>$null
if ($deploymentId) {
    Write-Host "API desplegada en stage: $STAGE_NAME" -ForegroundColor Green
} else {
    aws apigateway create-deployment --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION --description "Update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-Null
    Write-Host "API actualizada en stage: $STAGE_NAME" -ForegroundColor Green
}

# 11️⃣ Mostrar URL final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host "`n=== API LISTA ===" -ForegroundColor Green
Write-Host "Endpoint: $apiUrl" -ForegroundColor Yellow

# 12️⃣ Guardar URL en archivo
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8
Write-Host "URL guardada en api_url.txt" -ForegroundColor Green

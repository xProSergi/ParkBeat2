# 🔧 Script para corregir error 403 en API Gateway
# Ejecuta este script si recibes "Forbidden" al llamar a la API

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$FUNCTION_NAME = "parkbeat-predictor"
$STAGE_NAME = "prod"

Write-Host ""
Write-Host "=== Corrigiendo Error 403 ===" -ForegroundColor Yellow
Write-Host ""

# 1. Obtener API ID
Write-Host "[1/4] Obteniendo API ID..." -ForegroundColor Cyan
$apiIdRaw = aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='$API_NAME'].id" --output text
if (-not $apiIdRaw) {
    Write-Host "ERROR: API '$API_NAME' no encontrada" -ForegroundColor Red
    exit 1
}
# Limpiar espacios y tomar solo el primer ID
$apiId = ($apiIdRaw -split '\s+')[0].Trim()
Write-Host "   API ID: $apiId" -ForegroundColor Green

# 2. Obtener Account ID
Write-Host "[2/4] Obteniendo Account ID..." -ForegroundColor Cyan
$accountId = (aws sts get-caller-identity --query Account --output text).Trim()
Write-Host "   Account ID: $accountId" -ForegroundColor Green

# 3. Eliminar permisos antiguos
Write-Host "[3/4] Eliminando permisos antiguos..." -ForegroundColor Cyan
try {
    $policy = aws lambda get-policy --function-name $FUNCTION_NAME --region $AWS_REGION 2>$null
    if ($policy) {
        $policyObj = $policy | ConvertFrom-Json
        $statements = ($policyObj.Policy | ConvertFrom-Json).Statement
        $removed = 0
        foreach ($stmt in $statements) {
            if ($stmt.Principal.Service -eq "apigateway.amazonaws.com") {
                aws lambda remove-permission --function-name $FUNCTION_NAME --statement-id $stmt.Sid --region $AWS_REGION 2>$null | Out-Null
                $removed++
            }
        }
        if ($removed -gt 0) {
            Write-Host "   $removed permiso(s) antiguo(s) eliminado(s)" -ForegroundColor Green
        } else {
            Write-Host "   No hay permisos antiguos" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "   No hay política existente (OK)" -ForegroundColor Yellow
}

# 4. Agregar permiso correcto
Write-Host "[4/4] Agregando permiso correcto..." -ForegroundColor Cyan
$sourceArn = "arn:aws:execute-api:${AWS_REGION}:${accountId}:${apiId}/*/*"
$statementId = "apigateway-invoke-$(Get-Date -Format 'yyyyMMddHHmmss')"

aws lambda add-permission `
    --function-name $FUNCTION_NAME `
    --statement-id $statementId `
    --action lambda:InvokeFunction `
    --principal apigateway.amazonaws.com `
    --source-arn $sourceArn `
    --region $AWS_REGION 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   Permiso agregado correctamente" -ForegroundColor Green
} else {
    Write-Host "   Error agregando permiso (puede que ya exista)" -ForegroundColor Yellow
}

# 5. Forzar nuevo deployment
Write-Host ""
Write-Host "[5/5] Forzando nuevo deployment..." -ForegroundColor Cyan
aws apigateway create-deployment `
    --rest-api-id $apiId `
    --stage-name $STAGE_NAME `
    --region $AWS_REGION `
    --description "Fix 403 error - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 2>&1 | Out-Null

Write-Host "   Deployment completado" -ForegroundColor Green

# Mostrar URL (asegurarse de que apiId no tenga espacios)
$apiId = $apiId.Trim()
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host ""
Write-Host "=== CORRECCION COMPLETADA ===" -ForegroundColor Green
Write-Host "URL: $apiUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Prueba de nuevo tu script Python" -ForegroundColor Cyan
Write-Host ""

# Guardar URL en archivo
$apiUrl | Out-File -FilePath "api_url.txt" -Encoding utf8 -NoNewline
Write-Host "URL guardada en api_url.txt" -ForegroundColor Green
Write-Host ""

# Script de diagnostico completo para API Gateway
# Identifica el problema del error 403

$AWS_REGION = "eu-west-3"
$API_NAME = "parkbeat-api"
$FUNCTION_NAME = "parkbeat-predictor"
$STAGE_NAME = "prod"

Write-Host ""
Write-Host "=== DIAGNOSTICO COMPLETO API GATEWAY ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Lambda
Write-Host "[1/6] Verificando Lambda..." -ForegroundColor Yellow
try {
    $lambda = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION 2>$null
    if ($lambda) {
        Write-Host "   Lambda existe: $FUNCTION_NAME" -ForegroundColor Green
        $functionArn = aws lambda get-function --function-name $FUNCTION_NAME --region $AWS_REGION --query 'Configuration.FunctionArn' --output text
        Write-Host "   Lambda ARN: $functionArn" -ForegroundColor Green
    } else {
        Write-Host "   ERROR: Lambda no existe" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "   ERROR: No se pudo verificar Lambda" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Listar todas las APIs
Write-Host "[2/6] Listando todas las APIs..." -ForegroundColor Yellow
$allApis = aws apigateway get-rest-apis --region $AWS_REGION --output json | ConvertFrom-Json
Write-Host "   Total de APIs encontradas: $($allApis.items.Count)" -ForegroundColor Cyan
foreach ($api in $allApis.items) {
    if ($api.name -eq $API_NAME) {
        Write-Host "   -> API: $($api.name) | ID: $($api.id) | Creada: $($api.createdDate)" -ForegroundColor Green
    }
}
Write-Host ""

# 3. Obtener API ID correcto (el mas reciente)
Write-Host "[3/6] Seleccionando API mas reciente..." -ForegroundColor Yellow
$matchingApis = $allApis.items | Where-Object { $_.name -eq $API_NAME } | Sort-Object createdDate -Descending
if ($matchingApis.Count -eq 0) {
    Write-Host "   ERROR: No se encontro API con nombre '$API_NAME'" -ForegroundColor Red
    exit 1
}
$apiId = $matchingApis[0].id
Write-Host "   Usando API ID: $apiId" -ForegroundColor Green
Write-Host ""

# 4. Verificar recursos y metodos
Write-Host "[4/6] Verificando recursos y metodos..." -ForegroundColor Yellow
$resources = aws apigateway get-resources --rest-api-id $apiId --region $AWS_REGION --output json | ConvertFrom-Json
$predictResource = $resources.items | Where-Object { $_.path -eq "/predict" }
if ($predictResource) {
    Write-Host "   Recurso /predict encontrado: $($predictResource.id)" -ForegroundColor Green
    $predictId = $predictResource.id
    
    # Verificar metodos
    if ($predictResource.resourceMethods) {
        Write-Host "   Metodos configurados:" -ForegroundColor Cyan
        foreach ($method in $predictResource.resourceMethods.PSObject.Properties.Name) {
            Write-Host "     - $method" -ForegroundColor Yellow
        }
        
        # Verificar metodo POST
        if ($predictResource.resourceMethods.POST) {
            Write-Host "   Metodo POST: OK" -ForegroundColor Green
            
            # Verificar integracion
            $integration = aws apigateway get-integration --rest-api-id $apiId --resource-id $predictId --http-method POST --region $AWS_REGION --output json 2>$null | ConvertFrom-Json
            if ($integration) {
                Write-Host "   Integracion tipo: $($integration.type)" -ForegroundColor Green
                Write-Host "   Integration URI: $($integration.uri)" -ForegroundColor Cyan
            } else {
                Write-Host "   ERROR: No hay integracion configurada" -ForegroundColor Red
            }
        } else {
            Write-Host "   ERROR: Metodo POST no existe" -ForegroundColor Red
        }
    } else {
        Write-Host "   ERROR: No hay metodos configurados" -ForegroundColor Red
    }
} else {
    Write-Host "   ERROR: Recurso /predict no encontrado" -ForegroundColor Red
}
Write-Host ""

# 5. Verificar permisos de Lambda
Write-Host "[5/6] Verificando permisos de Lambda..." -ForegroundColor Yellow
try {
    $policy = aws lambda get-policy --function-name $FUNCTION_NAME --region $AWS_REGION --output json 2>$null | ConvertFrom-Json
    if ($policy) {
        $policyObj = $policy.Policy | ConvertFrom-Json
        $apiGatewayPerms = $policyObj.Statement | Where-Object { $_.Principal.Service -eq "apigateway.amazonaws.com" }
        
        if ($apiGatewayPerms) {
            Write-Host "   Permisos de API Gateway encontrados:" -ForegroundColor Green
            foreach ($perm in $apiGatewayPerms) {
                Write-Host "     Statement ID: $($perm.Sid)" -ForegroundColor Cyan
                Write-Host "     Source ARN: $($perm.Condition.ArnLike.'AWS:SourceArn')" -ForegroundColor Cyan
                
                # Verificar si el source-arn coincide
                $accountId = ($functionArn -split ':')[4]
                $expectedArn = "arn:aws:execute-api:${AWS_REGION}:${accountId}:${apiId}/*/*"
                $actualArn = $perm.Condition.ArnLike.'AWS:SourceArn'
                
                if ($actualArn -eq $expectedArn) {
                    Write-Host "     -> Source ARN CORRECTO" -ForegroundColor Green
                } else {
                    Write-Host "     -> Source ARN INCORRECTO" -ForegroundColor Red
                    Write-Host "        Esperado: $expectedArn" -ForegroundColor Yellow
                    Write-Host "        Actual:   $actualArn" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "   ERROR: No hay permisos de API Gateway" -ForegroundColor Red
        }
    } else {
        Write-Host "   ERROR: No hay politica de permisos" -ForegroundColor Red
    }
} catch {
    Write-Host "   ERROR: No se pudo obtener politica" -ForegroundColor Red
}
Write-Host ""

# 6. Verificar deployment
Write-Host "[6/6] Verificando deployment..." -ForegroundColor Yellow
$deployments = aws apigateway get-deployments --rest-api-id $apiId --region $AWS_REGION --output json | ConvertFrom-Json
if ($deployments.items.Count -gt 0) {
    $latestDeployment = $deployments.items | Sort-Object createdDate -Descending | Select-Object -First 1
    Write-Host "   Ultimo deployment: $($latestDeployment.id)" -ForegroundColor Green
    Write-Host "   Fecha: $($latestDeployment.createdDate)" -ForegroundColor Cyan
    
    # Verificar stage
    $stage = aws apigateway get-stage --rest-api-id $apiId --stage-name $STAGE_NAME --region $AWS_REGION --output json 2>$null | ConvertFrom-Json
    if ($stage) {
        Write-Host "   Stage '$STAGE_NAME' existe" -ForegroundColor Green
        Write-Host "   Deployment ID del stage: $($stage.deploymentId)" -ForegroundColor Cyan
        
        if ($stage.deploymentId -eq $latestDeployment.id) {
            Write-Host "   -> Stage apunta al deployment mas reciente: OK" -ForegroundColor Green
        } else {
            Write-Host "   -> WARNING: Stage NO apunta al deployment mas reciente" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ERROR: Stage '$STAGE_NAME' no existe" -ForegroundColor Red
    }
} else {
    Write-Host "   ERROR: No hay deployments" -ForegroundColor Red
}
Write-Host ""

# Mostrar URL final
$apiUrl = "https://${apiId}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}/predict"
Write-Host "=== RESUMEN ===" -ForegroundColor Green
Write-Host "URL de la API: $apiUrl" -ForegroundColor Yellow
Write-Host ""
Write-Host "Si todo esta OK pero sigue dando 403, ejecuta:" -ForegroundColor Cyan
Write-Host "  .\fix_403_error.ps1" -ForegroundColor Yellow
Write-Host ""

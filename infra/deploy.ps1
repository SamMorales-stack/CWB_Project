# Provision Azure resources and deploy the SJ Planner Agent container.
#
# Required environment variables (set before running):
#   $env:APP_NAME                unique short name, e.g. sjplanner-sm7k3x
#   $env:LOCATION                Azure region, e.g. eastasia
#   $env:AZURE_OPENAI_API_KEY    API key from Azure AI Foundry
#   $env:AZURE_OPENAI_ENDPOINT   e.g. https://<resource>.cognitiveservices.azure.com/
#   $env:PG_ADMIN_PASSWORD       Postgres admin password (16+ chars)

$ErrorActionPreference = "Stop"

$RG        = "$env:APP_NAME-rg"
$ACR       = ($env:APP_NAME -replace '[-_]', '') + "acr"
$ENV_NAME  = "$env:APP_NAME-env"
$PG_SERVER = "$env:APP_NAME-pg"
$PG_DB     = "planner"
$PG_ADMIN  = "planneradmin"
$IMAGE_TAG = (Get-Date -Format "yyyyMMddHHmmss")

Write-Host "==> Resource group" -ForegroundColor Cyan
az group create --name $RG --location $env:LOCATION --output none

Write-Host "==> Container Registry (Basic)" -ForegroundColor Cyan
az acr create --resource-group $RG --name $ACR --sku Basic --admin-enabled true --output none

Write-Host "==> Build image in ACR (cloud build - no local Docker needed)" -ForegroundColor Cyan
az acr build --registry $ACR --image "sjplanner:$IMAGE_TAG" --file Dockerfile .

$ACR_LOGIN_SERVER = (az acr show --name $ACR --query loginServer -o tsv)
$ACR_USERNAME     = (az acr credential show --name $ACR --query username -o tsv)
$ACR_PASSWORD     = (az acr credential show --name $ACR --query 'passwords[0].value' -o tsv)

Write-Host "==> Postgres Flexible Server (Burstable B1ms)" -ForegroundColor Cyan
try {
    az postgres flexible-server create `
        --resource-group $RG `
        --name $PG_SERVER `
        --location $env:LOCATION `
        --admin-user $PG_ADMIN `
        --admin-password $env:PG_ADMIN_PASSWORD `
        --sku-name Standard_B1ms `
        --tier Burstable `
        --storage-size 32 `
        --version 16 `
        --public-access 0.0.0.0 `
        --yes `
        --output none
} catch {
    Write-Host "  [Postgres server already exists, continuing]" -ForegroundColor Yellow
}

try {
    az postgres flexible-server db create `
        --resource-group $RG `
        --server-name $PG_SERVER `
        --database-name $PG_DB `
        --output none
} catch {
    Write-Host "  [Database already exists, continuing]" -ForegroundColor Yellow
}

$PG_HOST      = "${PG_SERVER}.postgres.database.azure.com"
$DATABASE_URL = "postgresql+psycopg://${PG_ADMIN}:$($env:PG_ADMIN_PASSWORD)@${PG_HOST}:5432/${PG_DB}?sslmode=require"

Write-Host "==> Container Apps environment" -ForegroundColor Cyan
try {
    az containerapp env create `
        --resource-group $RG `
        --name $ENV_NAME `
        --location $env:LOCATION `
        --output none
} catch {
    Write-Host "  [Container Apps environment already exists, continuing]" -ForegroundColor Yellow
}

Write-Host "==> Container App" -ForegroundColor Cyan
$ErrorActionPreference = "SilentlyContinue"
$APP_EXISTS = az containerapp show --resource-group $RG --name $env:APP_NAME --query name -o tsv 2>$null
$ErrorActionPreference = "Stop"

if ($APP_EXISTS) {
    Write-Host "  [Updating existing app]" -ForegroundColor Yellow
    az containerapp update `
        --resource-group $RG `
        --name $env:APP_NAME `
        --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" `
        --output none
} else {
    az containerapp create `
        --resource-group $RG `
        --name $env:APP_NAME `
        --environment $ENV_NAME `
        --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" `
        --registry-server $ACR_LOGIN_SERVER `
        --registry-username $ACR_USERNAME `
        --registry-password $ACR_PASSWORD `
        --target-port 8501 `
        --ingress external `
        --min-replicas 1 `
        --max-replicas 1 `
        --secrets "pg-url=$DATABASE_URL" "aoai-key=$($env:AZURE_OPENAI_API_KEY)" `
        --env-vars `
            "DATABASE_URL=secretref:pg-url" `
            "AZURE_OPENAI_API_KEY=secretref:aoai-key" `
            "AZURE_OPENAI_ENDPOINT=$($env:AZURE_OPENAI_ENDPOINT)" `
            "AZURE_OPENAI_API_VERSION=2024-12-01-preview" `
            "AZURE_OPENAI_DEPLOYMENT_MAIN=gpt-4o" `
            "AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4.1-nano" `
        --output none
}

$URL = (az containerapp show --resource-group $RG --name $env:APP_NAME --query 'properties.configuration.ingress.fqdn' -o tsv)

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Live URL: https://$URL" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "Add this URL to README.md and the submission portal."

#!/usr/bin/env bash
# Provision Azure resources and deploy the SJ Planner Agent container.
#
# Required environment variables (set before running):
#   APP_NAME            unique short name, e.g. sjplanner-sm7k3x
#   LOCATION            Azure region, e.g. eastasia  (match your subscription's allowed regions)
#   AOAI_ENDPOINT       https://<resource>.openai.azure.com/
#   AOAI_KEY            Azure OpenAI API key
#   PG_ADMIN_PASSWORD   Postgres admin password (16+ chars, mixed case + digit + symbol)
#
# Usage: export the vars above, then run ./infra/deploy.sh
# Idempotent: re-running pushes a new image and updates the Container App.

set -euo pipefail

: "${APP_NAME:?must set APP_NAME}"
: "${LOCATION:?must set LOCATION}"
: "${AOAI_ENDPOINT:?must set AOAI_ENDPOINT}"
: "${AOAI_KEY:?must set AOAI_KEY}"
: "${PG_ADMIN_PASSWORD:?must set PG_ADMIN_PASSWORD}"

RG="${APP_NAME}-rg"
ACR="${APP_NAME//[-_]/}acr"     # ACR names cannot have dashes
ENV_NAME="${APP_NAME}-env"
PG_SERVER="${APP_NAME}-pg"
PG_DB="planner"
PG_ADMIN="planneradmin"
IMAGE_TAG="$(date +%Y%m%d%H%M%S)"

echo "==> Resource group"
az group create --name "$RG" --location "$LOCATION" --output none

echo "==> Container Registry (Basic)"
az acr create \
    --resource-group "$RG" --name "$ACR" \
    --sku Basic --admin-enabled true \
    --output none

echo "==> Build and push image via ACR"
az acr build \
    --registry "$ACR" \
    --image "sjplanner:${IMAGE_TAG}" \
    .

echo "==> Postgres Flexible Server (Burstable B1ms)"
az postgres flexible-server create \
    --resource-group "$RG" \
    --name "$PG_SERVER" \
    --location "$LOCATION" \
    --admin-user "$PG_ADMIN" \
    --admin-password "$PG_ADMIN_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 16 \
    --public-access 0.0.0.0 \
    --yes \
    --output none || echo "[postgres already exists, continuing]"

az postgres flexible-server db create \
    --resource-group "$RG" \
    --server-name "$PG_SERVER" \
    --database-name "$PG_DB" \
    --output none || echo "[db already exists, continuing]"

PG_HOST="${PG_SERVER}.postgres.database.azure.com"
DATABASE_URL="postgresql+psycopg://${PG_ADMIN}:${PG_ADMIN_PASSWORD}@${PG_HOST}:5432/${PG_DB}?sslmode=require"

echo "==> Container Apps environment"
az containerapp env create \
    --resource-group "$RG" \
    --name "$ENV_NAME" \
    --location "$LOCATION" \
    --output none || echo "[env already exists, continuing]"

ACR_LOGIN_SERVER="$(az acr show --name "$ACR" --query loginServer -o tsv)"
ACR_USERNAME="$(az acr credential show --name "$ACR" --query username -o tsv)"
ACR_PASSWORD="$(az acr credential show --name "$ACR" --query 'passwords[0].value' -o tsv)"

echo "==> Container App"
if az containerapp show --resource-group "$RG" --name "$APP_NAME" &>/dev/null; then
    echo "  [updating existing app]"
    az containerapp update \
        --resource-group "$RG" \
        --name "$APP_NAME" \
        --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" \
        --output none
else
    az containerapp create \
        --resource-group "$RG" \
        --name "$APP_NAME" \
        --environment "$ENV_NAME" \
        --image "${ACR_LOGIN_SERVER}/sjplanner:${IMAGE_TAG}" \
        --registry-server "$ACR_LOGIN_SERVER" \
        --registry-username "$ACR_USERNAME" \
        --registry-password "$ACR_PASSWORD" \
        --target-port 8501 \
        --ingress external \
        --min-replicas 1 \
        --max-replicas 1 \
        --secrets "pg-url=$DATABASE_URL" "aoai-key=$AOAI_KEY" \
        --env-vars \
            "DATABASE_URL=secretref:pg-url" \
            "AZURE_OPENAI_ENDPOINT=$AOAI_ENDPOINT" \
            "AZURE_OPENAI_API_KEY=secretref:aoai-key" \
            "AZURE_OPENAI_API_VERSION=2024-08-01-preview" \
            "AZURE_OPENAI_DEPLOYMENT_MAIN=gpt-4o" \
            "AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini" \
        --output none
fi

URL="$(az containerapp show \
    --resource-group "$RG" \
    --name "$APP_NAME" \
    --query 'properties.configuration.ingress.fqdn' -o tsv)"

echo ""
echo "============================================"
echo "  Live URL: https://${URL}"
echo "============================================"
echo "Add this URL to README.md and the submission portal."

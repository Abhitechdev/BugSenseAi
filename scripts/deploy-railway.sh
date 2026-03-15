#!/bin/bash
# Railway Deployment Script for BugSense AI
# Usage: ./scripts/deploy-railway.sh [environment]

set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="BugSense AI"
FRONTEND_SERVICE="frontend"
BACKEND_SERVICE="backend"
POSTGRES_SERVICE="postgres"
REDIS_SERVICE="redis"
CHROMADB_SERVICE="chromadb"

echo "🚀 Deploying BugSense AI to Railway..."
echo "Environment: $ENVIRONMENT"
echo "Project: $PROJECT_NAME"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "   npm install -g @railway/cli"
    exit 1
fi

# Check if logged in to Railway
if ! railway auth status &> /dev/null; then
    echo "❌ Not logged in to Railway. Please run: railway login"
    exit 1
fi

echo "✅ Railway CLI authenticated"

# Function to create service if it doesn't exist
create_service_if_not_exists() {
    local service_name=$1
    local service_type=$2
    local dockerfile_path=$3
    
    if ! railway service list | grep -q "$service_name"; then
        echo "➕ Creating service: $service_name"
        if [ "$service_type" = "docker" ]; then
            railway add --service "$service_name" --source docker --dockerfile "$dockerfile_path"
        else
            railway add --service "$service_name" --source "$service_type"
        fi
    else
        echo "✅ Service exists: $service_name"
    fi
}

# Function to set environment variables
set_env_vars() {
    local service_name=$1
    shift
    local env_vars=("$@")
    
    echo "🔧 Setting environment variables for $service_name"
    for var in "${env_vars[@]}"; do
        railway variables set "$var" --service "$service_name"
    done
}

# Create or switch to project
echo "📋 Checking project: $PROJECT_NAME"
if ! railway project list | grep -q "$PROJECT_NAME"; then
    echo "➕ Creating project: $PROJECT_NAME"
    railway init "$PROJECT_NAME"
else
    echo "✅ Project exists: $PROJECT_NAME"
    railway switch "$PROJECT_NAME"
fi

# 1. Create database services
echo "🗄️  Setting up database services..."
create_service_if_not_exists "$POSTGRES_SERVICE" "postgres" ""
create_service_if_not_exists "$REDIS_SERVICE" "redis" ""

# 2. Create ChromaDB service
echo "🧠 Setting up ChromaDB service..."
create_service_if_not_exists "$CHROMADB_SERVICE" "docker" "/backend/Dockerfile"
# Note: This would need to be configured manually for ChromaDB image

# 3. Create backend service
echo "⚙️  Setting up backend service..."
create_service_if_not_exists "$BACKEND_SERVICE" "docker" "/backend/Dockerfile"

# Backend environment variables
BACKEND_ENV_VARS=(
    "APP_NAME=BugSense AI"
    "APP_ENV=$ENVIRONMENT"
    "DEBUG=false"
    "SECRET_KEY=\$(openssl rand -base64 32)"
    "BACKEND_HOST=0.0.0.0"
    "CORS_ORIGINS=https://*.up.railway.app"
    "DATABASE_URL=\${{Postgres.DATABASE_URL}}"
    "REDIS_URL=\${{Redis.REDIS_URL}}"
    "CHROMA_HOST=chromadb.railway.internal"
    "CHROMA_PORT=8000"
    "AI_PROVIDER=nvidia"
    "NVIDIA_API_KEY=your-nvidia-api-key-here"
    "AI_MODEL=meta/llama-3.3-70b-instruct"
    "RATE_LIMIT_PER_MINUTE=30"
    "ANALYSIS_RATE_LIMIT_PER_MINUTE=10"
    "HISTORY_RATE_LIMIT_PER_MINUTE=30"
    "HEALTH_RATE_LIMIT_PER_MINUTE=120"
    "MAX_REQUEST_BODY_BYTES=262144"
)

set_env_vars "$BACKEND_SERVICE" "${BACKEND_ENV_VARS[@]}"

# 4. Create frontend service
echo "🌐 Setting up frontend service..."
create_service_if_not_exists "$FRONTEND_SERVICE" "docker" "/frontend/Dockerfile"

# Frontend environment variables
FRONTEND_ENV_VARS=(
    "NEXT_PUBLIC_API_URL=https://$BACKEND_SERVICE.up.railway.app"
    "NEXT_PUBLIC_APP_NAME=BugSense AI"
)

set_env_vars "$FRONTEND_SERVICE" "${FRONTEND_ENV_VARS[@]}"

# Deploy services
echo "🚀 Deploying services..."
railway deploy --service "$BACKEND_SERVICE"
railway deploy --service "$FRONTEND_SERVICE"

# Wait for deployment
echo "⏳ Waiting for deployment to complete..."
sleep 30

# Get service URLs
BACKEND_URL=$(railway variables get RAILWAY_PUBLIC_DOMAIN --service "$BACKEND_SERVICE" 2>/dev/null || echo "pending")
FRONTEND_URL=$(railway variables get RAILWAY_PUBLIC_DOMAIN --service "$FRONTEND_SERVICE" 2>/dev/null || echo "pending")

echo "✅ Deployment completed!"
echo ""
echo "📊 Service URLs:"
echo "   Backend: https://$BACKEND_SERVICE.up.railway.app"
echo "   Frontend: https://$FRONTEND_URL"
echo ""
echo "🔍 Health Checks:"
echo "   Backend Health: https://$BACKEND_SERVICE.up.railway.app/health"
echo "   All Dependencies: https://$BACKEND_SERVICE.up.railway.app/health/dependencies"
echo ""
echo "📝 Next Steps:"
echo "   1. Set your NVIDIA_API_KEY in the backend service variables"
echo "   2. Update CORS_ORIGINS to your specific frontend domain"
echo "   3. Configure ChromaDB service with the correct Docker image"
echo "   4. Test the application at your frontend URL"
echo ""
echo "🔧 Manual Configuration Required:"
echo "   - Set NVIDIA_API_KEY: railway variables set NVIDIA_API_KEY=your-key --service $BACKEND_SERVICE"
echo "   - Update CORS: railway variables set CORS_ORIGINS=https://your-frontend.up.railway.app --service $BACKEND_SERVICE"
echo "   - Configure ChromaDB: Set image to 'chromadb/chroma:latest' and add volume"
# Deploy BugSense AI on Railway

This project is an isolated monorepo with a `frontend` service and a `backend` service.

Based on current Railway docs:
- isolated monorepos should use a root directory per service
- public URLs are created from each service's Networking settings
- private service-to-service traffic should use `*.railway.internal`
- volumes are required for persistent service data such as Chroma storage

Official references:
- https://docs.railway.com/guides/monorepo
- https://docs.railway.com/tutorials/deploying-a-monorepo
- https://docs.railway.com/networking/domains
- https://docs.railway.com/guides/private-networking
- https://docs.railway.com/guides/redis
- https://docs.railway.com/volumes/reference

## Recommended topology

Create one Railway project with five services:

1. `frontend`
2. `backend`
3. `postgres`
4. `redis`
5. `chromadb`

## Step by step

### 1. Create the Railway project

1. Open Railway and create a new empty project.
2. Rename the project to `BugSense AI`.

### 2. Add the database services

1. Add a PostgreSQL service from the Railway template marketplace.
2. Add a Redis service from the Railway template marketplace.

Railway will expose connection variables for these services automatically.

### 3. Add the ChromaDB service

1. Create a new empty service.
2. In Service Settings, set the service source to Docker Image.
3. Use the image `chromadb/chroma:latest`.
4. Add these variables to the service:

```env
IS_PERSISTENT=TRUE
```

5. Attach a volume to the service and mount it at:

```text
/chroma/chroma
```

6. Rename the service to `chromadb`.
7. Do not generate a public domain for this service.

The backend will reach it over Railway private networking at `chromadb.railway.internal:8000`.

### 4. Add the backend service

1. Create a new empty service.
2. Connect the GitHub repo `Abhitechdev/BugSenseAi`.
3. In Service Settings, set:

```text
Root Directory: /backend
```

4. Railway should detect the Dockerfile in `/backend`.
5. Add these variables to the backend service:

```env
APP_NAME=BugSense AI
APP_ENV=production
DEBUG=false
SECRET_KEY=generate-a-long-random-secret
BACKEND_HOST=0.0.0.0
CORS_ORIGINS=https://<your-frontend-domain>
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CHROMA_HOST=chromadb.railway.internal
CHROMA_PORT=8000
AI_PROVIDER=nvidia
NVIDIA_API_KEY=your-rotated-nvidia-key
AI_MODEL=meta/llama-3.3-70b-instruct
RATE_LIMIT_PER_MINUTE=30
```

If Railway names the database services differently in your project, use the reference variables from those actual service names in the Variables UI.

Railway Postgres exposes a plain `postgresql://...` connection string. The backend normalizes that to `postgresql+asyncpg://...` automatically for SQLAlchemy async usage, so you can keep the variable exactly as `DATABASE_URL=${{Postgres.DATABASE_URL}}`.

The backend also allows Railway public app domains via a default CORS regex. Keep `CORS_ORIGINS` for your final frontend/custom domain, but Railway preview or generated `*.up.railway.app` domains will still work during deployment.

6. Deploy the backend service.
7. After the first successful deploy, open Networking and click Generate Domain.
8. Copy the generated backend public URL. You will need it for the frontend.

### 5. Add the frontend service

1. Create another empty service.
2. Connect the same GitHub repo.
3. In Service Settings, set:

```text
Root Directory: /frontend
```

4. Add this variable:

```env
NEXT_PUBLIC_API_URL=https://<your-backend-domain>
```

5. Deploy the frontend service.
6. Open Networking and click Generate Domain.
7. Copy the generated frontend public URL.

### 6. Update backend CORS to the real frontend URL

1. Go back to the backend service Variables tab.
2. Set:

```env
CORS_ORIGINS=https://<your-frontend-domain>
```

3. Redeploy the backend.

### 7. Verify the deployment

Check these URLs:

1. Frontend:

```text
https://<your-frontend-domain>
```

2. Backend health:

```text
https://<your-backend-domain>/health
```

Expected backend response:

```json
{"status":"healthy","env":"production"}
```

### 8. Test the real app flow

1. Open the frontend URL.
2. Paste a sample runtime error.
3. Submit analysis.
4. Confirm the frontend can talk to the backend.
5. Check the backend logs if requests fail.

## Notes

- Railway public domains are for browser access.
- `railway.internal` domains are for service-to-service access inside the Railway project.
- The frontend needs the backend public URL because browsers cannot reach Railway private domains.
- Chroma is optional for first deploy because the backend degrades gracefully if it cannot connect, but deploy it if you want similarity search.

## Updated for Production Readiness (March 2026)

### Security Enhancements

The latest deployment includes comprehensive security improvements:

1. **Input Validation**: Enhanced spam pattern detection with stricter validation rules
2. **Audit Logging**: Sensitive data filtering to prevent logging of API keys and secrets
3. **Rate Limiting**: Tightened limits for production environments
4. **Security Headers**: Automatic security headers middleware
5. **Request Size Limits**: Protection against large payload attacks

### Production Configuration

For production deployment, use these additional environment variables:

```env
# Security
DEBUG=false
SECRET_KEY=your-super-secret-production-key-here
MAX_REQUEST_BODY_BYTES=262144

# Rate Limiting (Production)
RATE_LIMIT_PER_MINUTE=30
ANALYSIS_RATE_LIMIT_PER_MINUTE=10
HISTORY_RATE_LIMIT_PER_MINUTE=30
HEALTH_RATE_LIMIT_PER_MINUTE=120

# CORS (Production)
CORS_ORIGINS=https://your-frontend-domain.com
CORS_ORIGIN_REGEX=r"https://.*\.up\.railway\.app"

# Trusted Hosts
TRUSTED_HOSTS=your-frontend-domain.com,*.railway.app,*.railway.internal

# AI Provider (Production)
AI_PROVIDER=nvidia
NVIDIA_API_KEY=your-production-nvidia-api-key
AI_MODEL=meta/llama-3.3-70b-instruct

# Database (Production)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Production)
REDIS_URL=${{Redis.REDIS_URL}}

# ChromaDB (Production)
CHROMA_HOST=chromadb.railway.internal
CHROMA_PORT=8000

# Optional: Cloudflare Turnstile
TURNSTILE_SECRET_KEY=your-turnstile-secret-key
TURNSTILE_ENABLED=true
```

### Health Check Endpoints

The application now provides comprehensive health check endpoints:

- `/health` - Basic health check
- `/health/db` - Database connectivity
- `/health/cache` - Redis cache status
- `/health/vector` - ChromaDB vector database
- `/health/ai` - AI provider connectivity
- `/health/dependencies` - All external dependencies

### Monitoring and Observability

The application includes structured logging with sensitive data filtering and comprehensive audit logging for all requests. Use Railway's built-in monitoring or integrate with external monitoring services.

### Rollback Strategy

Railway supports easy rollback through the dashboard:
1. Go to your service
2. Click on "Deployments"
3. Select a previous deployment
4. Click "Rollback"

### Troubleshooting

Common issues and solutions:

1. **Database Connection Issues**: Ensure `DATABASE_URL` is correctly set and PostgreSQL service is running
2. **Redis Connection Issues**: Verify `REDIS_URL` and Redis service status
3. **AI Provider Issues**: Check `NVIDIA_API_KEY` and network connectivity
4. **CORS Issues**: Verify `CORS_ORIGINS` includes your frontend domain
5. **Rate Limiting**: Adjust rate limit variables if legitimate requests are being blocked

### Performance Optimization

For optimal performance in production:

1. **Database**: Enable connection pooling and monitor query performance
2. **Redis**: Monitor memory usage and cache hit rates
3. **AI Provider**: Monitor response times and implement caching where appropriate
4. **Frontend**: Enable static asset caching and CDN usage

### Security Best Practices

1. **Secrets Management**: Use Railway's secret management for all sensitive data
2. **Environment Isolation**: Use separate Railway projects for staging and production
3. **Access Control**: Limit access to Railway dashboard and repository
4. **Regular Updates**: Keep dependencies updated and monitor for security vulnerabilities
5. **Backup Strategy**: Implement regular database backups using Railway's backup features

# BugSense AI - Backup and Restore Procedures

This document outlines the procedures for backing up and restoring BugSense AI data, including database backups, configuration exports, and key rotation.

## Table of Contents

1. [Database Backup and Restore](#database-backup-and-restore)
2. [Configuration Backup](#configuration-backup)
3. [AI Provider Key Rotation](#ai-provider-key-rotation)
4. [Railway Environment Variables](#railway-environment-variables)
5. [Redis Cache Backup](#redis-cache-backup)
6. [ChromaDB Vector Database](#chromadb-vector-database)
7. [Disaster Recovery](#disaster-recovery)

## Database Backup and Restore

### PostgreSQL Database

#### Automated Backups (Recommended)

Set up automated daily backups using `pg_dump`:

```bash
# Create backup script
cat > /usr/local/bin/backup-database.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/backups/database"
mkdir -p $BACKUP_DIR

# Database connection details
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="bugsense_db"
DB_USER="bugsense"

# Create backup
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    --verbose --clean --if-exists --create --format=custom \
    -f "$BACKUP_DIR/bugsense_db_$DATE.backup"

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/bugsense_db_$DATE.backup s3://your-backup-bucket/
EOF

chmod +x /usr/local/bin/backup-database.sh

# Set up cron job for daily backups at 2 AM
echo "0 2 * * * /usr/local/bin/backup-database.sh" | crontab -
```

#### Manual Backup

```bash
# Create a backup
pg_dump -h localhost -U bugsense -d bugsense_db --format=custom --file=bugsense_backup_$(date +%Y%m%d).backup

# Create a SQL dump
pg_dump -h localhost -U bugsense -d bugsense_db --format=plain --file=bugsense_backup_$(date +%Y%m%d).sql
```

#### Restore Database

```bash
# Restore from custom format backup
pg_restore -h localhost -U bugsense -d bugsense_db --clean --if-exists bugsense_backup.backup

# Restore from SQL dump
psql -h localhost -U bugsense -d bugsense_db -f bugsense_backup.sql
```

### Railway Database Backup

If using Railway's managed PostgreSQL:

```bash
# Get database connection info from Railway dashboard
# Use pg_dump with the provided connection string
pg_dump "$DATABASE_URL" --format=custom --file=bugsense_railway_backup.backup

# Restore to Railway
pg_restore -d "$DATABASE_URL" --clean --if-exists bugsense_railway_backup.backup
```

## Configuration Backup

### Environment Variables

Backup all environment variables used by the application:

```bash
# Create environment backup
cat > /backups/env-backup-$(date +%Y%m%d).env << 'EOF'
# BugSense AI Environment Variables Backup
# Generated on: $(date)

# Application
APP_NAME=BugSense AI
APP_ENV=production
DEBUG=false
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://bugsense:password@localhost:5432/bugsense_db

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Providers (backup only the keys you use)
NVIDIA_API_KEY=your-nvidia-key
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENROUTER_API_KEY=your-openrouter-key

# AI Configuration
AI_PROVIDER=nvidia
AI_MODEL=meta/llama-3.3-70b-instruct

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# Turnstile
TURNSTILE_SECRET_KEY=your-turnstile-secret
TURNSTILE_ALLOWED_HOSTNAMES=localhost,127.0.0.1,*.up.railway.app

# CORS and Security
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
TRUSTED_HOSTS=localhost,127.0.0.1,*.yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
ANALYSIS_RATE_LIMIT_PER_MINUTE=10
HISTORY_RATE_LIMIT_PER_MINUTE=30
EOF
```

### Docker Configuration

Backup Docker-related files:

```bash
# Backup Docker configuration
tar -czf /backups/docker-config-$(date +%Y%m%d).tar.gz \
    docker-compose.yml \
    Dockerfile \
    .dockerignore \
    backend/Dockerfile \
    frontend/Dockerfile
```

## AI Provider Key Rotation

### Key Rotation Procedure

1. **Generate New Keys**: Create new API keys from your AI provider dashboard
2. **Update Environment**: Update the environment variables with new keys
3. **Test Configuration**: Verify the new keys work before removing old ones
4. **Revoke Old Keys**: Once confirmed working, revoke the old keys

### Automated Key Rotation Script

```bash
#!/bin/bash
# rotate-keys.sh

set -e

echo "Starting AI provider key rotation..."

# Function to test AI provider connectivity
test_provider() {
    local provider=$1
    local key_var=$2
    local key_value=$3
    
    echo "Testing $provider with new key..."
    
    # Set temporary environment
    export AI_PROVIDER=$provider
    export $key_var=$key_value
    
    # Test connectivity (this would call your AI service ping method)
    python3 -c "
from app.services.ai_service import ai_service
import asyncio
import os
os.environ['AI_PROVIDER'] = '$provider'
os.environ['$key_var'] = '$key_value'
async def test():
    result = await ai_service.ping()
    print(f'Provider $provider: {'✓' if result else '✗'}')
    return result
asyncio.run(test())
"
}

# Example rotation for OpenAI
if [ "$1" = "openai" ]; then
    echo "Rotating OpenAI keys..."
    
    # Get new key from secure storage or input
    read -sp "Enter new OpenAI API key: " NEW_OPENAI_KEY
    echo
    
    # Test new key
    if test_provider "openai" "OPENAI_API_KEY" "$NEW_OPENAI_KEY"; then
        echo "New OpenAI key is valid!"
        
        # Update environment (this would be done via your deployment system)
        # For Railway: railway variables set OPENAI_API_KEY="$NEW_OPENAI_KEY"
        
        echo "Please update your deployment environment with the new key"
        echo "Then restart your application"
    else
        echo "New OpenAI key is invalid!"
        exit 1
    fi
fi

echo "Key rotation completed successfully!"
```

## Railway Environment Variables

### Export Environment Variables

```bash
# Export all Railway environment variables
railway variables list --json > railway-env-backup-$(date +%Y%m%d).json

# Export specific variables
railway variables get SECRET_KEY AI_PROVIDER NVIDIA_API_KEY > critical-vars.txt
```

### Import Environment Variables

```bash
# Import from JSON backup
railway variables import --file railway-env-backup.json

# Set individual variables
railway variables set SECRET_KEY="new-secret-key"
railway variables set AI_PROVIDER="nvidia"
```

### Environment Variable Template

Create a template for new environments:

```env
# .env.template - Template for BugSense AI environment variables

# Application Configuration
APP_NAME=BugSense AI
APP_ENV=production
DEBUG=false
SECRET_KEY=CHANGE_ME_TO_A_SECURE_RANDOM_STRING

# Database Configuration
DATABASE_URL=postgresql://bugsense:CHANGE_ME@localhost:5432/bugsense_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# AI Provider Configuration (choose one)
AI_PROVIDER=nvidia  # or gemini, openai, anthropic, openrouter
AI_MODEL=meta/llama-3.3-70b-instruct

# AI Provider Keys (only set the one you're using)
NVIDIA_API_KEY=CHANGE_ME
GEMINI_API_KEY=CHANGE_ME
OPENAI_API_KEY=CHANGE_ME
ANTHROPIC_API_KEY=CHANGE_ME
OPENROUTER_API_KEY=CHANGE_ME

# ChromaDB Configuration
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# Cloudflare Turnstile
TURNSTILE_SECRET_KEY=CHANGE_ME
TURNSTILE_ALLOWED_HOSTNAMES=localhost,127.0.0.1,*.yourdomain.com

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
CORS_ORIGIN_REGEX=https://.*\.yourdomain\.com

# Trusted Hosts
TRUSTED_HOSTS=localhost,127.0.0.1,*.yourdomain.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=30
ANALYSIS_RATE_LIMIT_PER_MINUTE=10
HISTORY_RATE_LIMIT_PER_MINUTE=30
HISTORY_MUTATION_RATE_LIMIT_PER_MINUTE=5
HEALTH_RATE_LIMIT_PER_MINUTE=120

# Request Size Limits
MAX_REQUEST_BODY_BYTES=262144
```

## Redis Cache Backup

### Redis Backup Script

```bash
#!/bin/bash
# backup-redis.sh

REDIS_HOST="localhost"
REDIS_PORT="6379"
BACKUP_DIR="/backups/redis"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p $BACKUP_DIR

# Create Redis backup using BGSAVE
redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE

# Wait for backup to complete
while [ $(redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE) -eq $(redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE) ]; do
    sleep 1
done

# Copy RDB file
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# Optional: Create AOF backup
redis-cli -h $REDIS_HOST -p $REDIS_PORT BGREWRITEAOF

echo "Redis backup completed: $BACKUP_DIR/redis_backup_$DATE.rdb"
```

### Redis Restore

```bash
# Stop Redis
sudo systemctl stop redis

# Restore RDB file
cp /backups/redis/redis_backup.rdb /var/lib/redis/dump.rdb

# Set permissions
sudo chown redis:redis /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis
```

## ChromaDB Vector Database

### ChromaDB Backup

ChromaDB stores data in a persistent directory. To back up:

```bash
# Backup ChromaDB data directory
CHROMA_DATA_DIR="/app/chroma_data"
BACKUP_DIR="/backups/chromadb"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

tar -czf $BACKUP_DIR/chromadb_backup_$DATE.tar.gz $CHROMA_DATA_DIR

# For Railway deployment, you might need to use volumes or external storage
```

### ChromaDB Restore

```bash
# Restore ChromaDB data
tar -xzf /backups/chromadb/chromadb_backup.tar.gz -C /app/

# Ensure proper permissions
chown -R app:app /app/chroma_data
```

## Disaster Recovery

### Complete System Recovery

1. **Restore Database**:
   ```bash
   # Restore PostgreSQL database
   pg_restore -h localhost -U bugsense -d bugsense_db --clean --if-exists backup_file.backup
   
   # Verify data integrity
   psql -h localhost -U bugsense -d bugsense_db -c "SELECT COUNT(*) FROM error_analysis;"
   ```

2. **Restore Configuration**:
   ```bash
   # Restore environment variables
   railway variables import --file railway-env-backup.json
   
   # Verify configuration
   railway variables list
   ```

3. **Restore Cache**:
   ```bash
   # Restore Redis data
   cp /backups/redis/redis_backup.rdb /var/lib/redis/dump.rdb
   systemctl restart redis
   ```

4. **Restore Vector Database**:
   ```bash
   # Restore ChromaDB data
   tar -xzf /backups/chromadb/chromadb_backup.tar.gz -C /app/
   ```

5. **Restart Application**:
   ```bash
   # Restart all services
   railway restart
   
   # Verify health
   curl https://your-app.up.railway.app/health
   ```

### Recovery Testing

Regularly test your recovery procedures:

```bash
#!/bin/bash
# test-recovery.sh

echo "Testing disaster recovery procedures..."

# Test 1: Database backup integrity
echo "1. Testing database backup..."
pg_restore --list /backups/database/bugsense_db_*.backup | head -5

# Test 2: Configuration backup
echo "2. Testing configuration backup..."
if [ -f "/backups/env-backup-*.env" ]; then
    echo "✓ Environment backup exists"
else
    echo "✗ Environment backup missing"
fi

# Test 3: Redis backup
echo "3. Testing Redis backup..."
if [ -f "/backups/redis/redis_backup_*.rdb" ]; then
    echo "✓ Redis backup exists"
else
    echo "✗ Redis backup missing"
fi

# Test 4: Application health check
echo "4. Testing application health..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://your-app.up.railway.app/health)
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✓ Application is healthy"
else
    echo "✗ Application health check failed (status: $HTTP_STATUS)"
fi

echo "Recovery testing completed."
```

### Recovery Runbook

Create a recovery runbook for emergency situations:

```markdown
# BugSense AI Disaster Recovery Runbook

## Emergency Contacts
- Primary: [Your Name] - [Phone] - [Email]
- Secondary: [Backup Contact] - [Phone] - [Email]

## Recovery Priority
1. Database restoration (P0 - Critical)
2. Application configuration (P1 - High)
3. Cache restoration (P2 - Medium)
4. Vector database restoration (P3 - Low)

## Recovery Steps

### Step 1: Assess Damage
- [ ] Check application status
- [ ] Identify affected components
- [ ] Determine recovery priority

### Step 2: Database Recovery
- [ ] Restore from latest backup
- [ ] Verify data integrity
- [ ] Test database connectivity

### Step 3: Application Recovery
- [ ] Restore environment variables
- [ ] Deploy latest code
- [ ] Verify application startup

### Step 4: Cache Recovery
- [ ] Restore Redis data
- [ ] Verify cache functionality

### Step 5: Vector Database Recovery
- [ ] Restore ChromaDB data
- [ ] Verify vector search functionality

### Step 6: Validation
- [ ] Run health checks
- [ ] Test core functionality
- [ ] Monitor for issues

## Escalation
If recovery fails:
1. Contact infrastructure team
2. Check backup integrity
3. Consider alternative recovery methods
4. Document incident for post-mortem
```

## Backup Schedule

| Component | Frequency | Retention | Storage Location |
|-----------|-----------|-----------|------------------|
| Database | Daily | 30 days | Local + Cloud |
| Configuration | Weekly | 12 months | Version Control |
| Redis Cache | Daily | 7 days | Local |
| ChromaDB | Weekly | 30 days | Local + Cloud |
| Docker Config | On Change | Indefinite | Version Control |

## Monitoring and Alerts

Set up monitoring for backup success:

```bash
# Monitor backup completion
#!/bin/bash
# monitor-backups.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d)

# Check if today's backups exist
if [ ! -f "$BACKUP_DIR/database/bugsense_db_$DATE.backup" ]; then
    echo "ALERT: Database backup missing for $DATE"
    # Send alert (email, Slack, etc.)
fi

if [ ! -f "$BACKUP_DIR/redis/redis_backup_$DATE.rdb" ]; then
    echo "ALERT: Redis backup missing for $DATE"
fi

# Check backup file sizes (ensure they're not empty)
DB_SIZE=$(stat -f%z "$BACKUP_DIR/database/bugsense_db_$DATE.backup" 2>/dev/null || stat -c%s "$BACKUP_DIR/database/bugsense_db_$DATE.backup" 2>/dev/null)
if [ "$DB_SIZE" -lt 1000 ]; then
    echo "ALERT: Database backup file is suspiciously small"
fi
```

This comprehensive backup and restore documentation ensures your BugSense AI application can be recovered quickly and reliably in case of any issues.
# Basset Hound - Production Deployment Guide

**Version**: 2.0.0  
**Last Updated**: 2026-05-07  
**Status**: Production Ready

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Fresh Deployment](#fresh-deployment)
3. [Configuration](#configuration)
4. [Database Setup](#database-setup)
5. [Monitoring Setup](#monitoring-setup)
6. [Integrations](#integrations)
7. [SSL/TLS Setup](#ssltls-setup)
8. [Scaling](#scaling)
9. [Backup & Restore](#backup--restore)
10. [Rollback Procedures](#rollback-procedures)
11. [Troubleshooting](#troubleshooting)
12. [Performance Tuning](#performance-tuning)
13. [Security Hardening](#security-hardening)
14. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

**Minimum (Small Deployments)**
- CPU: 2 cores
- Memory: 4GB RAM
- Storage: 50GB SSD
- OS: Ubuntu 20.04+, CentOS 8+, or similar

**Recommended (Production)**
- CPU: 4+ cores
- Memory: 8GB+ RAM
- Storage: 200GB+ SSD (RAID-1 recommended)
- OS: Ubuntu 22.04 LTS or CentOS 8+
- Network: 1Gbps connection

**Large Scale (10M+ entities)**
- CPU: 8+ cores
- Memory: 32GB+ RAM
- Storage: 500GB+ SSD (dedicated Neo4j disk)
- OS: Ubuntu 22.04 LTS
- Network: 10Gbps connection
- Database: Enterprise Neo4j cluster

### Required Software

```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y \
  docker.io \
  docker-compose \
  git \
  curl \
  wget \
  htop \
  nginx

# CentOS/RHEL
sudo yum install -y \
  docker \
  docker-compose \
  git \
  curl \
  wget \
  htop \
  nginx

# Verify installations
docker --version      # Docker 24.0+
docker-compose --version  # 2.20+
git --version         # 2.30+
```

### User & Directory Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash basset
sudo usermod -aG docker basset

# Create data directories
sudo mkdir -p /opt/basset-hound/{data,logs,backups,projects}
sudo chown -R basset:basset /opt/basset-hound
sudo chmod 755 /opt/basset-hound
```

---

## Fresh Deployment

### Step 1: Clone Repository

```bash
# As basset user
sudo su - basset

# Clone repository
cd /opt
git clone https://github.com/yourusername/basset-hound.git
cd basset-hound

# Verify directory structure
ls -la
# Expected: api/, basset_mcp/, docs/, frontend/, nginx/, tests/, docker-compose.yml, etc.
```

### Step 2: Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit for production
nano .env
```

See [Configuration](#configuration) section for detailed setup.

### Step 3: Build Docker Images

```bash
# Build all images
docker compose build --no-cache

# Verify images
docker images | grep basset
# Should show: basset_api, basset_nginx, etc.
```

### Step 4: Initialize Database

```bash
# Start only Neo4j first (gives it time to initialize)
docker compose up -d neo4j

# Wait for Neo4j to be ready (check logs)
docker compose logs neo4j | grep "Started"

# Verify Neo4j connection
curl -u neo4j:neo4jbasset http://localhost:7474 | head -20
```

### Step 5: Start All Services

```bash
# Start all services
docker compose up -d

# Monitor startup logs
docker compose logs -f

# Wait for all services to be healthy
docker compose ps
# Should show all services with "healthy" status
```

### Step 6: Verify Installation

```bash
# Check health endpoint
curl http://localhost:8080/health

# Should return:
# {"status":"healthy","timestamp":"2026-05-07T...","version":"2.0.0"}

# Access web interface
curl http://localhost:8080/ | head -50

# Check API documentation
curl http://localhost:8080/docs | grep "openapi"
```

### Step 7: Initial Data Setup

```bash
# Create first project
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production",
    "description": "Main production project"
  }'

# Seed default platforms (optional)
curl -X POST http://localhost:8080/api/v1/platforms/seed \
  -H "Content-Type: application/json"

# Verify data
curl http://localhost:8080/api/v1/projects
```

---

## Configuration

### Environment Variables (.env)

**Neo4j Database**
```bash
# Connection
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password_here

# Memory (adjust based on available RAM)
NEO4J_dbms_memory_heap_max__size=4G
NEO4J_server_memory_pagecache_size=2G
```

**Application Settings**
```bash
# Server
DEBUG=false
HOST=0.0.0.0
PORT=8000
APP_VERSION=2.0.0

# Authentication (enable in production)
AUTH_ENABLED=true
SECRET_KEY=generate_strong_key_with_openssl

# CORS (restrict in production)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

**File Storage**
```bash
PROJECTS_DIRECTORY=/opt/basset-hound/data/projects
MAX_UPLOAD_SIZE_MB=500
BACKUP_DIRECTORY=/opt/basset-hound/backups
```

**Integrations**
```bash
# basset-verify
BASSET_VERIFY_URL=http://basset-verify:8001
BASSET_VERIFY_ENABLED=true
BASSET_VERIFY_TIMEOUT=10

# basset-hound-browser
BASSET_BROWSER_WS_URL=ws://browser:8765
BASSET_BROWSER_ENABLED=true

# cletus
CLETUS_BASE_URL=http://cletus:9000
CLETUS_ENABLED=true
```

**Monitoring**
```bash
# Prometheus
PROMETHEUS_ENABLED=true
PROMETHEUS_SCRAPE_INTERVAL=15s

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
STRUCTURED_LOGGING=true
```

### Secrets Management

**Using Docker Secrets** (Swarm mode)

```bash
# Create secrets
echo "your_secure_password" | docker secret create neo4j_password -
echo "your_jwt_secret" | docker secret create app_secret -

# Reference in docker-compose.yml
secrets:
  neo4j_password:
    external: true
  app_secret:
    external: true
```

**Using Environment Files**

```bash
# Create .env.production
cat > .env.production <<EOF
DEBUG=false
NEO4J_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 64)
EOF

# Use during startup
docker compose --env-file .env.production up -d

# Secure the file
chmod 600 .env.production
```

**Using Vault** (Enterprise)

```bash
# See docker-compose.yml for Vault integration
# Requires vault-agent sidecar in containers

# Fetch secrets from Vault
vault kv get secret/basset-hound
```

---

## Database Setup

### Neo4j Configuration

**Initial Setup**

```bash
# Connect to Neo4j
docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset

# Change default password
:password
# Enter new password twice

# Exit
:exit
```

**Performance Tuning**

```bash
# Update docker-compose.yml environment variables
NEO4j_dbms_memory_heap_max__size=8G          # 50% of RAM
NEO4J_server_memory_pagecache_size=2G        # Remaining RAM

# Enable query cache
NEO4J_server_cache_node_cache_enabled=true
NEO4J_server_cache_relationship_cache_enabled=true

# Optimize transactions
NEO4J_transactions_memory_pageCache_warmupEnable=true
```

**Database Initialization**

```cypher
-- Create indexes for common queries
CREATE INDEX entity_type_idx FOR (e:Entity) ON (e.entity_type);
CREATE INDEX project_id_idx FOR (e:Entity) ON (e.project_id);
CREATE INDEX identifier_idx FOR (d:Data) ON (d.identifier);
CREATE INDEX timestamp_idx FOR (e:Entity) ON (e.created_at);

-- Create constraints for uniqueness
CREATE CONSTRAINT entity_id_unique FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT platform_id_unique FOR (p:Platform) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT project_id_unique FOR (p:Project) REQUIRE p.id IS UNIQUE;

-- Verify
SHOW INDEXES;
SHOW CONSTRAINTS;
```

**Seeding Default Platforms**

```bash
# Run seeding via API
curl -X POST http://localhost:8080/api/v1/platforms/seed \
  -H "Content-Type: application/json"

# Or manually via Neo4j shell
docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  < seed_platforms.cypher
```

### Backup Strategy

**Automated Backups**

```bash
# Add to crontab (daily at 2 AM)
crontab -e

# Add line:
0 2 * * * /opt/basset-hound/scripts/backup.sh

# Backup script
#!/bin/bash
set -e
BACKUP_DIR="/opt/basset-hound/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/neo4j_backup_$TIMESTAMP.dump"

mkdir -p "$BACKUP_DIR"

# Create backup
docker exec neo4j_osint_db \
  neo4j-admin database dump neo4j "$BACKUP_FILE" \
  --neo4j-conf=/etc/neo4j/neo4j.conf

# Compress
gzip "$BACKUP_FILE"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "neo4j_backup_*.dump.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

---

## Monitoring Setup

### Prometheus Configuration

**Default Metrics**

```yaml
# prometheus.yml (included in docker-compose.yml)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'basset-api'
    static_configs:
      - targets: ['basset_api:8000']
    metrics_path: '/metrics'

  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7474']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']  # nginx-prometheus-exporter
```

**Key Metrics**

```
# Request metrics
basset_request_count{method,path,status}
basset_request_latency_seconds{method,path}

# Entity metrics
basset_entity_count{project}
basset_relationship_count{project}

# Database metrics
basset_neo4j_query_latency_seconds
neo4j_instance_is_leader
neo4j_instance_store_size

# Cache metrics
basset_cache_hits_total
basset_cache_misses_total

# Job metrics
celery_task_duration_seconds{task}
celery_task_failed_total
```

### Grafana Dashboards

**Access**
```
URL: http://localhost:3000
User: admin
Password: admin (change immediately!)
```

**Default Dashboards**
1. **System Overview**: CPU, memory, disk usage
2. **API Performance**: Request latency, throughput
3. **Database Performance**: Query times, connection counts
4. **Entity Analytics**: Entity growth, relationship trends
5. **Error Tracking**: Error rates, exception types

**Create Custom Dashboard**

```bash
# Via API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d @dashboard.json
```

### Alerting Rules

**Alert Configuration** (prometheus/rules.yml)

```yaml
groups:
  - name: basset_hound
    rules:
      # API Availability
      - alert: APIDown
        expr: up{job="basset-api"} == 0
        for: 2m
        annotations:
          summary: "Basset API is down"

      # High Error Rate
      - alert: HighErrorRate
        expr: rate(basset_request_count{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      # Database Connection
      - alert: Neo4jDown
        expr: up{job="neo4j"} == 0
        for: 1m
        annotations:
          summary: "Neo4j is unreachable"

      # Memory Usage
      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        annotations:
          summary: "Container memory usage > 90%"

      # Disk Space
      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes < 0.1
        for: 10m
        annotations:
          summary: "Disk space < 10%"
```

**Notification Channels**

```bash
# Email
curl -X POST http://localhost:3000/api/alert-notifications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Alert",
    "type": "email",
    "settings": {
      "addresses": "ops@example.com"
    }
  }'

# Slack
curl -X POST http://localhost:3000/api/alert-notifications \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slack Alert",
    "type": "slack",
    "settings": {
      "url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    }
  }'
```

---

## Integrations

### basset-verify Integration

**Installation**

```bash
# Clone repository
cd /opt
git clone https://github.com/yourusername/basset-verify.git
cd basset-verify

# Start service
docker compose up -d

# Verify running
curl http://localhost:8001/health
```

**Configuration in basset-hound**

```bash
# .env
BASSET_VERIFY_URL=http://basset-verify:8001
BASSET_VERIFY_ENABLED=true
BASSET_VERIFY_TIMEOUT=10

# Or update docker-compose.yml
services:
  basset-verify:
    build: ../basset-verify
    container_name: basset_verify
    networks:
      - basset-hound
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
```

**Testing**

```bash
# Email verification
curl -X POST http://localhost:8080/api/v1/verify/email \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Phone verification
curl -X POST http://localhost:8080/api/v1/verify/phone \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1234567890"}'
```

### basset-hound-browser Integration

**Installation**

```bash
# Clone Chrome extension
cd /opt
git clone https://github.com/yourusername/basset-hound-browser.git
cd basset-hound-browser

# Build extension
npm install
npm run build

# Load in Chrome
# 1. Go to chrome://extensions
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select the dist/ folder
```

**WebSocket Bridge Configuration**

```bash
# .env in basset-hound
BASSET_BROWSER_WS_URL=ws://localhost:8765
BASSET_BROWSER_ENABLED=true

# Browser extension config
# Set basset-hound API URL to your server:
# http://your-domain.com:8080/

# Or via environment
export BASSET_HOUND_URL=https://your-domain.com
export BASSET_BROWSER_TOKEN=your-token-here
```

**Testing Connection**

```bash
# Check WebSocket endpoint
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  http://localhost:8080/ws/browser

# Monitor browser actions
docker compose logs -f basset_api | grep "browser"
```

### cletus Integration

**Installation**

```bash
# Clone repository
cd /opt
git clone https://github.com/yourusername/cletus.git
cd cletus

# Start service
docker compose up -d

# Verify
curl http://localhost:9000/health
```

**Configuration**

```bash
# .env
CLETUS_BASE_URL=http://cletus:9000
CLETUS_ENABLED=true
CLETUS_API_KEY=your-api-key

# docker-compose.yml
services:
  cletus:
    build: ../cletus
    container_name: cletus_service
    networks:
      - basset-hound
    environment:
      - API_KEY=your-api-key
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
```

**Testing**

```bash
# Get news feed
curl http://localhost:8080/api/v1/cletus/feed \
  -H "X-Project-ID: your-project-id"

# Monitor cletus integration
docker compose logs cletus_service
```

---

## SSL/TLS Setup

### Self-Signed Certificate (Development)

```bash
# Generate private key and certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 -keyout /opt/basset-hound/nginx/server.key \
  -out /opt/basset-hound/nginx/server.crt -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Org/CN=localhost"

# Verify
openssl x509 -in /opt/basset-hound/nginx/server.crt -text -noout
```

### Let's Encrypt Certificate (Production)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate (requires domain and DNS access)
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com

# Verify
ls -la /etc/letsencrypt/live/your-domain.com/

# Update nginx configuration
nano /opt/basset-hound/nginx/nginx.conf
```

**nginx.conf for SSL**

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # HSTS header (15768000 seconds = 6 months)
    add_header Strict-Transport-Security "max-age=15768000; includeSubDomains" always;

    # Redirect HTTP to HTTPS
    location / {
        proxy_pass http://basset_api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

**Auto-Renewal**

```bash
# Test renewal
sudo certbot renew --dry-run

# Set up cron job (auto-renewal)
# Usually auto-configured, but verify:
ls -la /etc/cron.d/certbot

# Manual renewal
sudo certbot renew --force-renewal

# Reload nginx after renewal
sudo systemctl reload nginx
```

---

## Scaling

### Horizontal Scaling (Multiple API Servers)

**Docker Compose Scale**

```bash
# Scale API servers to 3 instances
docker compose up -d --scale basset_api=3

# Nginx will automatically load-balance
docker compose logs nginx | grep upstream
```

**Load Balancer Configuration**

```nginx
# In nginx/nginx.conf
upstream basset_api {
    least_conn;  # Connection-based load balancing
    server basset_api:8000 max_fails=3 fail_timeout=30s;
    server basset_api_2:8000 max_fails=3 fail_timeout=30s;
    server basset_api_3:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    location / {
        proxy_pass http://basset_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### Vertical Scaling (Increased Resources)

```bash
# Update docker-compose.yml
services:
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_max__size=16G  # Increase from 4G
      - NEO4J_server_memory_pagecache_size=8G  # Increase from 2G

  redis:
    command: redis-server --maxmemory 1gb  # Increase from 256mb

# Restart services
docker compose up -d neo4j redis
```

### Database Clustering (Enterprise)

**Neo4j Cluster Setup**

```yaml
# docker-compose.yml for 3-node cluster
services:
  neo4j_1:
    image: neo4j:5.28-enterprise
    environment:
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_server_discovery_advertised__address=neo4j_1:5000
      - NEO4J_server_cluster_advertised__address=neo4j_1:6000
      - NEO4J_server_cluster_raft_advertised__address=neo4j_1:7000
      - NEO4J_server_cluster_initial__members=neo4j_1,neo4j_2,neo4j_3
  
  neo4j_2:
    image: neo4j:5.28-enterprise
    environment:
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_server_discovery_advertised__address=neo4j_2:5000
      - NEO4J_server_cluster_advertised__address=neo4j_2:6000
      - NEO4J_server_cluster_raft_advertised__address=neo4j_2:7000
      - NEO4J_server_cluster_initial__members=neo4j_1,neo4j_2,neo4j_3
  
  neo4j_3:
    image: neo4j:5.28-enterprise
    environment:
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_server_discovery_advertised__address=neo4j_3:5000
      - NEO4J_server_cluster_advertised__address=neo4j_3:6000
      - NEO4J_server_cluster_raft_advertised__address=neo4j_3:7000
      - NEO4J_server_cluster_initial__members=neo4j_1,neo4j_2,neo4j_3
```

---

## Backup & Restore

### Creating Backups

**Full Database Backup**

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/opt/basset-hound/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/neo4j_$TIMESTAMP.dump"

mkdir -p "$BACKUP_DIR"

# Backup Neo4j
docker exec neo4j_osint_db neo4j-admin database dump neo4j "$DB_BACKUP"

# Compress
gzip "$DB_BACKUP"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$TIMESTAMP.tar.gz" \
  /opt/basset-hound/.env \
  /opt/basset-hound/docker-compose.yml \
  /opt/basset-hound/nginx/nginx.conf

# Backup projects directory
tar -czf "$BACKUP_DIR/projects_$TIMESTAMP.tar.gz" \
  /opt/basset-hound/data/projects

# Remove old backups (keep 30 days)
find "$BACKUP_DIR" -name "neo4j_*.dump.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DB_BACKUP.gz"
```

**Automated Backups (Cron)**

```bash
# Add to crontab
crontab -e

# Add these lines:
# Daily backup at 2 AM
0 2 * * * /opt/basset-hound/scripts/backup.sh >> /var/log/basset-backup.log 2>&1

# Weekly full backup at 1 AM Sunday
0 1 * * 0 /opt/basset-hound/scripts/backup-full.sh >> /var/log/basset-backup-full.log 2>&1
```

### Restoring from Backup

**Neo4j Restore**

```bash
# 1. Stop services
docker compose down

# 2. Remove current database
docker volume rm basset-hound_neo4j_data

# 3. Extract backup
gunzip /opt/basset-hound/backups/neo4j_20260507_020000.dump.gz

# 4. Restore database
docker compose up -d neo4j
docker exec neo4j_osint_db neo4j-admin database load neo4j \
  /var/lib/neo4j/backups/neo4j_20260507_020000.dump

# 5. Restart services
docker compose up -d
```

**Projects Restore**

```bash
# Extract projects backup
tar -xzf /opt/basset-hound/backups/projects_20260507_020000.tar.gz \
  -C /opt/basset-hound/

# Verify
ls -la /opt/basset-hound/data/projects
```

---

## Rollback Procedures

### Rollback to Previous Version

**Docker Image Rollback**

```bash
# 1. Check version history
docker images | grep basset

# 2. Use previous image
docker compose down

# 3. Update docker-compose.yml with previous version
# Change: image: basset_api:latest
# To: image: basset_api:v1.9.0

# 4. Restart services
docker compose up -d

# 5. Monitor logs
docker compose logs -f basset_api
```

**Database Rollback**

```bash
# If schema was changed in new version:

# 1. Restore database from backup
# See "Restoring from Backup" section

# 2. Verify data integrity
curl http://localhost:8080/api/v1/health

# 3. Run data migration rollback scripts (if available)
docker exec neo4j_osint_db cypher-shell < rollback_schema.cypher
```

**Configuration Rollback**

```bash
# 1. Restore previous .env
cp /opt/basset-hound/backups/config_*.tar.gz /tmp/
cd /tmp
tar -xzf config_*.tar.gz

# 2. Copy restored files
cp .env /opt/basset-hound/
cp docker-compose.yml /opt/basset-hound/

# 3. Restart services
cd /opt/basset-hound
docker compose restart
```

---

## Troubleshooting

### Service Won't Start

```bash
# 1. Check logs
docker compose logs basset_api

# 2. Verify configuration
docker compose config

# 3. Check port availability
lsof -i :8080  # Should be empty
lsof -i :7687  # Neo4j port

# 4. Check disk space
df -h /opt/basset-hound

# 5. Restart Docker daemon
sudo systemctl restart docker
```

### High Memory Usage

```bash
# 1. Check container memory
docker stats

# 2. Increase limits in docker-compose.yml
services:
  basset_api:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G

# 3. Check Neo4j heap settings
docker exec neo4j_osint_db jcmd $(docker exec neo4j_osint_db pidof java) \
  VM.native_memory summary

# 4. Reduce cache size (if applicable)
REDIS_MAXMEMORY=512mb
```

### Database Connection Issues

```bash
# 1. Test Neo4j connection
docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset

# 2. Check network connectivity
docker network ls
docker network inspect basset-hound

# 3. Verify credentials in .env
echo $NEO4J_URI
echo $NEO4J_USER

# 4. Restart Neo4j
docker compose restart neo4j

# 5. Check Neo4j logs
docker compose logs neo4j | grep -i error
```

### API Returning 500 Errors

```bash
# 1. Check API logs
docker compose logs basset_api | tail -50

# 2. Enable debug mode
export DEBUG=true
docker compose restart basset_api

# 3. Check database queries
docker exec -it neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset
> CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Queries') YIELD attributes
> RETURN attributes;

# 4. Check request payload
curl -v http://localhost:8080/api/v1/projects 2>&1 | grep -A20 "< HTTP"
```

### WebSocket Connection Fails

```bash
# 1. Test WebSocket endpoint
websocat ws://localhost:8080/ws/suggestions/test-project

# 2. Check nginx proxy config
grep -A10 "location /ws" /opt/basset-hound/nginx/nginx.conf

# 3. Verify WebSocket settings in nginx
# Should include:
# proxy_http_version 1.1;
# proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

# 4. Monitor WebSocket traffic
docker compose logs -f nginx | grep ws
```

---

## Performance Tuning

### Database Optimization

**Query Performance**

```cypher
-- Create indexes for common queries
CREATE INDEX ON :Entity(entity_type);
CREATE INDEX ON :Entity(project_id);
CREATE INDEX ON :Relationship(project_id);
CREATE INDEX ON :Data(identifier);

-- Monitor query performance
PROFILE MATCH (e:Entity) WHERE e.project_id = "proj_123" RETURN e;

-- Check index usage
:schema
```

**Memory Configuration**

```bash
# Update docker-compose.yml
services:
  neo4j:
    environment:
      # Allocate 50% of available RAM to heap
      NEO4J_dbms_memory_heap_max__size=8G
      
      # Allocate remaining to page cache
      NEO4J_server_memory_pagecache_size=4G
      
      # Enable native memory tracking
      NEO4J_server_jvm_additional="-XX:+UnlockDiagnosticVMOptions -XX:+PrintNativeNMTStatistics"
```

### API Performance

**Caching Strategy**

```bash
# Enable Redis caching in .env
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600  # 1 hour
CACHE_MAX_SIZE=100mb

# Monitor cache hit rate
curl http://localhost:8080/metrics | grep cache_hits
```

**Request Optimization**

```bash
# Enable request compression
gzip on;
gzip_types application/json text/plain;
gzip_min_length 1000;

# In nginx.conf
```

### System Tuning

**File Descriptor Limits**

```bash
# Check current limits
ulimit -n

# Increase permanently
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Apply immediately
ulimit -n 65535
```

**Network Tuning**

```bash
# Optimize network stack
sudo sysctl -w net.core.somaxconn=65535
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=65535
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"

# Persist changes
echo "net.core.somaxconn=65535" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Phase 8 Performance Optimizations

**Query Optimization (Stream 1)**

```bash
# Enable query caching and batch operations
export CACHE_ENABLED=true
export REDIS_URL=redis://localhost:6379/0
export CACHE_TTL_QUERY=60  # 60 second TTL for query results

# Configure Neo4j indexes (automatically created on startup)
# Indexes include: Person.email, Person.phone, Relationship.type, etc.
# Verify indexes with:
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8080/api/v1/indexes

# Monitor query performance
curl http://localhost:8080/api/v1/metrics/performance
```

**Caching Layer Optimization (Stream 2)**

```bash
# Configure Redis memory settings
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor cache effectiveness
curl http://localhost:8080/api/v1/cache/hit-rate

# Expected: 60%+ hit rate across system
# List endpoints: 70%
# Search endpoints: 50%
# Graph queries: 60%

# Warm cache on startup (optional)
curl -X POST http://localhost:8080/api/v1/cache/warm

# Clear cache if needed
curl -X POST http://localhost:8080/api/v1/cache/clear
```

**Frontend Optimization (Stream 3)**

```bash
# Rebuild frontend with code splitting (if source available)
cd frontend/
npm run build:prod

# Expected bundle sizes:
# main.js: ~150KB (gzipped)
# vendor.js: ~140KB (gzipped)
# Total: ~290KB (was 500KB)

# Verify with Lighthouse
npm run lighthouse

# Expected Lighthouse score: 90+
```

**Search Index Optimization (Stream 4)**

```bash
# Full-text search is automatically enabled
# Verify search endpoints:
curl 'http://localhost:8080/api/v1/search/full-text?q=test' | jq '.meta.response_time_ms'

# Expected latency: <200ms p99

# Monitor search performance
curl http://localhost:8080/api/v1/metrics/search

# Rebuild indexes if corrupted
curl -X POST http://localhost:8080/api/v1/search/index/build
```

**ML Analytics Setup (Stream 5, Optional)**

```bash
# Enable ML analytics (feature flag)
export ENABLE_ML_ANALYTICS=true
export ML_MODEL_PATH=/opt/basset-hound/models/

# Download/train models (one-time setup)
python scripts/setup_ml_models.py

# Verify models are loaded
curl http://localhost:8080/api/v1/ml/models/status

# Test duplicate detection
curl 'http://localhost:8080/api/v1/ml/duplicates?entity_id=ent_123'

# Expected inference time: <100ms
```

**Real-Time Collaboration (Stream 6, Optional)**

```bash
# Enable WebSocket collaboration
export ENABLE_COLLABORATION=true
export WEBSOCKET_ENABLED=true
export MAX_CONCURRENT_CONNECTIONS=500

# Monitor WebSocket connections
curl http://localhost:8080/api/v1/collaboration/presence?project_id=proj_123

# Check activity feed
curl http://localhost:8080/api/v1/collaboration/activity?project_id=proj_123
```

**Plugin System (Stream 7, Optional)**

```bash
# Enable plugin system
export ENABLE_PLUGINS=true
export PLUGIN_SANDBOX_ENABLED=true
export PLUGIN_MAX_SIZE_MB=5

# List available plugins
curl http://localhost:8080/api/v1/plugins

# Built-in plugins should include:
# - sankey (entity flow)
# - timeline (temporal relationships)
# - heatmap (activity frequency)
# - network-stats (centrality metrics)
```

**Data Export (Stream 8)**

```bash
# Enable exports
export ENABLE_EXPORT=true
export EXPORT_MAX_SIZE_MB=100

# Test exports
curl -X POST http://localhost:8080/api/v1/projects/proj_123/export/csv \
  -H "Content-Type: application/json" \
  -d '{}' > test_export.csv

# Expected: <1s for 10K entities, <50s for 1M entities
```

**Performance Monitoring Dashboard**

```bash
# Access monitoring endpoints
curl http://localhost:8080/api/v1/metrics/performance  # Overall stats
curl http://localhost:8080/api/v1/metrics/latency      # Latency distribution
curl http://localhost:8080/api/v1/metrics/throughput   # Request throughput
curl http://localhost:8080/api/v1/metrics/database     # Database metrics
curl http://localhost:8080/api/v1/metrics/memory       # Memory usage

# Grafana dashboards (if enabled)
# - Performance Dashboard: latency, throughput, error rates
# - Cache Dashboard: hit rates, eviction patterns
# - Search Dashboard: query latency, index usage
# - ML Dashboard: inference times, model accuracy
```

**Performance Tuning Recommendations**

```
Target Metrics (After Phase 8):
├─ Query Latency p99: <100ms ✅
├─ Cache Hit Rate: 60%+ ✅
├─ API Throughput: 2000+ req/s ✅
├─ Bundle Size (gzipped): <300KB ✅
├─ FCP (First Paint): <2s ✅
└─ Lighthouse Score: 90+ ✅

If metrics are below targets:
├─ Increase Redis maxmemory
├─ Adjust TTL settings based on data volatility
├─ Add more backend instances behind load balancer
├─ Enable Neo4j Enterprise clustering (for 1M+ entities)
└─ Monitor and alert on key metrics
```

---

## Security Hardening

### Authentication & Authorization

**Enable JWT Authentication**

```bash
# Update .env
AUTH_ENABLED=true
SECRET_KEY=$(openssl rand -base64 64)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Restart services
docker compose up -d
```

**Create API Tokens**

```bash
# Via API endpoint
curl -X POST http://localhost:8080/api/v1/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "secure_password"
  }'

# Use token in requests
curl http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Network Security

**Firewall Configuration**

```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8080/tcp    # API (temporary, remove in production)

# Check firewall
sudo ufw status
```

**VPN/Bastion Host**

```bash
# Restrict API access to VPN only
# In nginx.conf
location /api/ {
    # Allow only VPN subnet
    allow 10.0.0.0/8;
    allow 172.16.0.0/12;
    deny all;
    proxy_pass http://basset_api:8000;
}
```

### Data Protection

**Encryption at Rest**

```bash
# Enable LUKS encryption for data volume
sudo cryptsetup luksFormat /dev/sdX

# Mount encrypted volume
sudo cryptsetup luksOpen /dev/sdX neo4j_data
sudo mkfs.ext4 /dev/mapper/neo4j_data
sudo mount /dev/mapper/neo4j_data /opt/basset-hound/data

# Update fstab
echo "/dev/mapper/neo4j_data /opt/basset-hound/data ext4 defaults 0 0" | \
  sudo tee -a /etc/fstab
```

**Encryption in Transit**

```bash
# All traffic via HTTPS (see SSL/TLS Setup)
# Internal service communication (optional)
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL dbms.cluster.routing.getServers() YIELD servers RETURN servers;"
```

### Audit & Compliance

**Enable Audit Logging**

```bash
# Enable in .env
AUDIT_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=90

# Monitor audit logs
docker compose logs basset_api | grep "AUDIT"
```

**Log Aggregation**

```bash
# Send logs to centralized system (ELK Stack)
docker compose up -d filebeat logstash elasticsearch kibana

# Or use Splunk, DataDog, etc.
# Configure in docker-compose.yml
services:
  basset_api:
    logging:
      driver: "splunk"
      options:
        splunk-token: "YOUR_TOKEN"
        splunk-url: "https://your-splunk.example.com:8088"
```

---

## Maintenance

### Regular Tasks

**Daily**
```bash
# Monitor system health
docker compose ps

# Check logs for errors
docker compose logs --since 24h | grep ERROR

# Monitor disk usage
df -h /opt/basset-hound
```

**Weekly**
```bash
# Create backup
/opt/basset-hound/scripts/backup.sh

# Review Grafana dashboards
open http://localhost:3000

# Check Prometheus alerts
curl http://localhost:9090/api/v1/alerts
```

**Monthly**
```bash
# Update dependencies
cd /opt/basset-hound
git pull
docker compose build --no-cache

# Test backup restoration
/opt/basset-hound/scripts/restore-test.sh

# Review security logs
docker compose logs --since 720h | grep -i "security\|auth\|failed"

# Capacity planning
docker stats
df -h
```

**Quarterly**
```bash
# Major version upgrades
cd /opt/basset-hound
git checkout tags/v2.1.0

# Run migrations
docker compose exec basset_api python -m api.migrations.run

# Test rollback procedures

# Review disaster recovery plan
```

### Log Management

**Rotation**

```bash
# docker-compose.yml
services:
  basset_api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"
```

**Archival**

```bash
# Archive old logs monthly
tar -czf /opt/basset-hound/backups/logs_$(date +%Y%m).tar.gz \
  /var/lib/docker/containers/*/*/stdout*
```

### Database Maintenance

```bash
# Vacuum (cleanup deleted nodes)
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL apoc.periodic.iterate('MATCH (n) WHERE n.deleted = true RETURN n', 'DETACH DELETE n', {batchSize:10000})"

# Analyze database
docker exec neo4j_osint_db cypher-shell -u neo4j -p neo4jbasset \
  "CALL db.stats.retrieve('graph') YIELD section, key, value RETURN section, key, value"
```

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 2.0.0 | 2026-05-07 | Production release: UI, monitoring, integrations |
| 1.9.0 | 2026-04-30 | LaTeX PDF reporting system |
| 1.8.0 | 2026-04-15 | Browser integration (Stream 8) |
| 1.7.0 | 2026-04-01 | Platform accounts architecture |

---

**Last Updated**: 2026-05-07  
**Status**: Production Ready  
**Support**: See README.md for contact information

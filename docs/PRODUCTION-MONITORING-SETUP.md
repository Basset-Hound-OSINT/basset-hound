# Basset Hound Production Monitoring Setup

**Version**: 2.0  
**Date**: 2026-05-19  
**Purpose**: Configure monitoring, alerting, and observability for production deployment  
**Audience**: DevOps Engineers, SREs, Monitoring Engineers

---

## Table of Contents

1. [Monitoring Architecture](#monitoring-architecture)
2. [Prometheus Configuration](#prometheus-configuration)
3. [Grafana Dashboards](#grafana-dashboards)
4. [Alert Rules](#alert-rules)
5. [Log Aggregation](#log-aggregation)
6. [Health Checks](#health-checks)
7. [Performance Baselines](#performance-baselines)
8. [Troubleshooting](#troubleshooting)

---

## Monitoring Architecture

### Overview

```
┌────────────────────────────────────────────────────┐
│         Application Layer (FastAPI Backend)         │
│              Exposes /metrics endpoint               │
└────────────────┬─────────────────────────────────────┘
                 │ (HTTP scrape every 15s)
                 ↓
┌────────────────────────────────────────────────────┐
│              Prometheus (Metrics DB)                 │
│           Scrapes: /metrics, /neo4j/metrics         │
└────────────────┬─────────────────────────────────────┘
                 │ (PromQL queries)
     ┌───────────┴───────────┐
     ↓                       ↓
┌──────────────┐      ┌──────────────────┐
│   Grafana    │      │ Alert Manager    │
│ (Dashboards) │      │ (Notifications)  │
└──────────────┘      └────────┬─────────┘
                               │ (Slack/Email/PagerDuty)
                               ↓
                        Notifications
```

### Metrics Sources

| Source | Type | Interval | Metrics |
|--------|------|----------|---------|
| FastAPI | HTTP | 15s | Request rate, latency, errors, cache |
| Neo4j | Cypher | 30s | Query times, pool utilization |
| Redis | Protocol | 30s | Memory, operations/sec, evictions |
| Docker | API | 60s | CPU, memory, I/O per container |
| Nginx | HTTP | 15s | Request rate, status codes |
| System | Node Exporter | 15s | CPU, memory, disk, network |

---

## Prometheus Configuration

### Setup Instructions

#### Step 1: Verify Prometheus Container

```bash
# Check if Prometheus is in docker-compose.yml
grep -A 10 "prometheus:" docker-compose.yml

# Expected output:
# prometheus:
#   image: prom/prometheus:latest
#   ports:
#     - "9090:3000"
#   volumes:
#     - ./prometheus.yml:/etc/prometheus/prometheus.yml
#     - prometheus_data:/prometheus
```

#### Step 2: Create prometheus.yml

```yaml
# prometheus.yml

global:
  scrape_interval: 15s          # Default scrape interval
  evaluation_interval: 15s       # How often to evaluate alert rules
  external_labels:
    environment: 'production'
    cluster: 'basset-hound'

# Alert manager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# Load rules once and periodically evaluate them
rule_files:
  - "alert_rules.yml"
  - "recording_rules.yml"

# Scrape configurations
scrape_configs:
  # FastAPI Backend
  - job_name: 'api'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    metrics_path: '/metrics'
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'api-primary'

  # Neo4j Database
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j:7687']
    scrape_interval: 30s
    scheme: 'http'
    metrics_path: '/metrics'
    
  # Redis Cache
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s

  # Nginx Reverse Proxy
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:8080']
    metrics_path: '/nginx_status'
    scrape_interval: 15s

  # Docker Containers (via cAdvisor)
  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/api/v1/container_metrics'

  # System Metrics (Node Exporter)
  - job_name: 'system'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s
```

#### Step 3: Start Prometheus

```bash
# Verify configuration
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml

# Restart Prometheus
docker-compose restart prometheus

# Access Prometheus UI
curl http://localhost:9090/
# Browse to: http://your-server:9090
```

### Key Prometheus Queries

```promql
# API Request Rate (requests per second)
rate(http_requests_total[5m])

# Error Rate (percentage)
rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100

# API Latency P99 (milliseconds)
histogram_quantile(0.99, http_request_duration_seconds_bucket) * 1000

# Cache Hit Rate (percentage)
rate(cache_hits_total[5m]) / rate(cache_requests_total[5m]) * 100

# Database Query Time (milliseconds)
histogram_quantile(0.99, neo4j_query_duration_ms_bucket)

# Neo4j Connection Pool Utilization (percentage)
neo4j_connections_active / neo4j_connections_max * 100

# Redis Memory Usage (bytes)
redis_memory_used_bytes

# Docker Container Memory (bytes)
container_memory_usage_bytes{name=~"basset.*"}

# System CPU Usage (percentage)
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

---

## Grafana Dashboards

### Setup Instructions

#### Step 1: Access Grafana

```bash
# Grafana runs on port 3000
# Access: http://your-server:3000

# Default credentials
Username: admin
Password: admin

# Change password on first login!
```

#### Step 2: Add Prometheus Data Source

1. **Menu** → **Connections** → **Data Sources**
2. **Add data source** → **Prometheus**
3. **URL**: `http://prometheus:9090`
4. **Save & test** → "Data source is working"

#### Step 3: Create Main Dashboard

**Dashboard Name**: "Basset Hound - Production Overview"

**Panels to Add**:

### Panel 1: Request Rate (Graph)

```
Title: API Request Rate
Query: rate(http_requests_total[5m])
Y-axis: req/s
Alert: Target >3 req/s ✓
```

### Panel 2: Error Rate (Gauge)

```
Title: Error Rate
Query: rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100
Y-axis: %
Thresholds:
  - Green: 0-0.1%
  - Yellow: 0.1-1%
  - Red: >1%
Alert: >1%
```

### Panel 3: API Latency (Graph)

```
Title: API Latency (P99)
Query: histogram_quantile(0.99, http_request_duration_seconds_bucket) * 1000
Y-axis: ms
Alert: >200ms warning, >500ms critical
Target: <100ms
```

### Panel 4: Cache Hit Rate (Gauge)

```
Title: Cache Hit Rate
Query: rate(cache_hits_total[5m]) / rate(cache_requests_total[5m]) * 100
Y-axis: %
Thresholds:
  - Green: >60%
  - Yellow: 40-60%
  - Red: <40%
Alert: <40%
```

### Panel 5: Database Latency (Graph)

```
Title: Database Query Latency (P99)
Query: histogram_quantile(0.99, neo4j_query_duration_ms_bucket)
Y-axis: ms
Alert: >150ms
Target: <100ms
```

### Panel 6: Connection Pool Usage (Gauge)

```
Title: Neo4j Connection Pool
Query: neo4j_connections_active / neo4j_connections_max * 100
Y-axis: %
Thresholds:
  - Green: <60%
  - Yellow: 60-80%
  - Red: >80%
Alert: >80%
```

### Panel 7: Container Memory (Graph)

```
Title: Memory Usage by Container
Query: container_memory_usage_bytes{name=~"basset.*"} / 1024 / 1024 / 1024
Y-axis: GB
Alert: API >2GB, Redis >500MB
```

### Panel 8: Container CPU (Graph)

```
Title: CPU Usage by Container
Query: rate(container_cpu_usage_seconds_total{name=~"basset.*"}[5m]) * 100
Y-axis: %
Alert: Any container >50%
```

### Panel 9: Active Connections (Stat)

```
Title: Active Services
Query: up{job=~"api|neo4j|redis|nginx"}
Display: "Active: X/5"
Alert: Any service down
```

### Panel 10: Error Log Rate (Graph)

```
Title: Application Errors per Minute
Query: rate(log_errors_total[1m])
Y-axis: errors/min
Alert: >1 error/min
```

---

## Alert Rules

### Configuration File: alert_rules.yml

```yaml
groups:
  - name: basset_hound_alerts
    interval: 15s
    rules:
      # API Health Alerts
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100 > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate ({{ $value | humanizePercentage }})"
          description: "Error rate >1% for 5+ minutes. Check API logs immediately."

      - alert: HighLatency
        expr: histogram_quantile(0.99, http_request_duration_seconds_bucket) * 1000 > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency ({{ $value | humanizeDuration }})"
          description: "P99 latency >500ms. Check database performance."

      - alert: LowThroughput
        expr: rate(http_requests_total[5m]) < 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low API throughput ({{ $value | humanize }} req/s)"
          description: "Throughput <3 req/s for 5+ minutes."

      # Cache Alerts
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / rate(cache_requests_total[5m]) * 100 < 40
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate ({{ $value | humanizePercentage }})"
          description: "Cache hit rate <40%. Check Redis and cache invalidation."

      - alert: RedisCacheDown
        expr: redis_up == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Redis cache unavailable"
          description: "Cache layer down for 2+ minutes. API using database directly."

      # Database Alerts
      - alert: DatabaseSlowQueries
        expr: histogram_quantile(0.99, neo4j_query_duration_ms_bucket) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries ({{ $value | humanizeDuration }})"
          description: "Database P99 latency >1 second. Check query optimization."

      - alert: ConnectionPoolExhaustion
        expr: neo4j_connections_active / neo4j_connections_max * 100 > 80
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Neo4j connection pool near capacity ({{ $value | humanizePercentage }})"
          description: "Pool utilization >80%. Increase pool size or optimize queries."

      - alert: DatabaseDown
        expr: neo4j_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Neo4j database unavailable"
          description: "Database down for 1+ minute. Service degraded."

      # Memory Alerts
      - alert: APIHighMemory
        expr: container_memory_usage_bytes{name="basset-hound-api"} / 1024 / 1024 / 1024 > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API high memory usage ({{ $value | humanize }} GB)"
          description: "API memory >3GB. Check for leaks or large operations."

      - alert: APIOutOfMemory
        expr: container_memory_usage_bytes{name="basset-hound-api"} / 1024 / 1024 / 1024 > 4
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API memory critical ({{ $value | humanize }} GB)"
          description: "API approaching memory limit. Restart may be imminent."

      - alert: RedisHighMemory
        expr: redis_memory_used_bytes / redis_memory_max_bytes * 100 > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis high memory usage ({{ $value | humanizePercentage }})"
          description: "Redis >80% capacity. Evictions starting, cache effectiveness reduced."

      # Service Health Alerts
      - alert: ServiceDown
        expr: up{job=~"api|neo4j|redis|nginx"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} service down"
          description: "{{ $labels.job }} has been unavailable for 1+ minute."

      - alert: ServiceRestartLoop
        expr: increase(container_last_seen{name=~"basset.*"}[5m]) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.name }} restarting repeatedly"
          description: "Container has restarted 2+ times in 5 minutes. Check logs."

      # Application-Specific Alerts
      - alert: ExportOperationTimeout
        expr: rate(export_timeouts_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Export operations timing out"
          description: "Export operations >10% timeout rate. Check database load."

      - alert: MLAnalyticsSlowResponse
        expr: histogram_quantile(0.95, ml_request_duration_ms_bucket) > 30000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "ML analytics slow ({{ $value | humanizeDuration }})"
          description: "ML operations taking >30 seconds. Check resource availability."

      - alert: WebSocketConnectionFailure
        expr: rate(websocket_connection_errors_total[5m]) > 0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "WebSocket connection failures detected"
          description: "Real-time collaboration features may be affected."
```

### Alert Manager Configuration

```yaml
# alertmanager.yml

global:
  resolve_timeout: 5m

# Slack integration
slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#basset-hound-alerts'
    send_resolved: true
    color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
    title: 'Alert: {{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

# Email integration
email_configs:
  - to: 'devops@your-company.com'
    from: 'prometheus-alerts@your-company.com'
    smarthost: 'smtp.gmail.com:587'
    auth_username: 'alerts@your-company.com'
    auth_password: '{{ env "SMTP_PASSWORD" }}'
    headers:
      Subject: '[{{ .GroupLabels.severity }}] {{ .GroupLabels.alertname }}'

# PagerDuty integration
pagerduty_configs:
  - service_key: '{{ env "PAGERDUTY_KEY" }}'

# Routing rules
route:
  receiver: 'default'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    # Critical alerts → Page on-call
    - match:
        severity: critical
      receiver: 'pagerduty'
      repeat_interval: 5m
    
    # Warning alerts → Slack
    - match:
        severity: warning
      receiver: 'slack'
      repeat_interval: 30m
    
    # Info alerts → Log only
    - match:
        severity: info
      receiver: 'null'
      repeat_interval: 1h
```

### Testing Alerts

```bash
# Generate test alerts
docker-compose exec prometheus bash -c '
cat > /tmp/test_alerts.yml << "EOF"
groups:
  - name: test
    rules:
      - alert: TestAlert
        expr: "1"
        for: 10s
EOF

# Add to Prometheus
curl -X POST http://localhost:9090/-/reload
'

# Verify alerts firing
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.severity=="critical")'
```

---

## Log Aggregation

### ELK Stack Setup (Optional)

For centralized logging, deploy Elasticsearch-Logstash-Kibana:

```yaml
# In docker-compose.yml

elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
  ports:
    - "9200:9200"
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data

logstash:
  image: docker.elastic.co/logstash/logstash:8.0.0
  volumes:
    - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  ports:
    - "5000:5000/udp"

kibana:
  image: docker.elastic.co/kibana/kibana:8.0.0
  ports:
    - "5601:5601"
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

### Log Collection from FastAPI

```python
# In api/utils/logger.py

import logging
from pythonjsonlogger import jsonlogger

# JSON logging to stdout (Logstash will collect)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### Kibana Queries for Troubleshooting

```
# Find all errors in last hour
type: api AND level: ERROR AND @timestamp > now-1h

# Find slow queries (>1 second)
type: query AND duration_ms > 1000

# Find failed exports
type: export AND status: failed

# Find WebSocket disconnections
type: websocket AND event: disconnect
```

---

## Health Checks

### API Health Endpoint

The system exposes a health check endpoint that should be monitored:

```bash
# Basic health check
curl http://localhost:8080/health
# Response: {"status": "healthy", "timestamp": "...", "services": {...}}

# With options for granularity
curl http://localhost:8080/health?detailed=true
# Includes individual service statuses
```

### Docker Health Checks

Update docker-compose.yml:

```yaml
api:
  image: basset-hound:latest
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 40s

neo4j:
  image: neo4j:5.26
  healthcheck:
    test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "$NEO4J_PASSWORD", "RETURN 1"]
    interval: 10s
    timeout: 5s
    retries: 3

redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 3
```

### Liveness & Readiness Probes (Kubernetes)

If using Kubernetes:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: basset-hound-api
spec:
  containers:
  - name: api
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3

    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
```

---

## Performance Baselines

### Baseline Establishment

Run the system for 24 hours in production and capture baselines:

```python
# scripts/establish_baselines.py

import json
from datetime import datetime, timedelta
import subprocess

baselines = {
    'api_latency_p99_ms': [],
    'error_rate_percent': [],
    'cache_hit_rate_percent': [],
    'db_latency_p99_ms': [],
    'throughput_rps': [],
    'memory_usage_gb': [],
}

# Collect metrics every 15 minutes for 24 hours
for i in range(96):  # 96 * 15min = 24 hours
    print(f"Collection {i+1}/96...")
    
    metrics = json.loads(subprocess.run(
        ['curl', '-s', 'http://localhost:8080/api/v1/metrics'],
        capture_output=True, text=True
    ).stdout)
    
    baselines['api_latency_p99_ms'].append(metrics['latency_p99'])
    baselines['error_rate_percent'].append(metrics['error_rate'] * 100)
    baselines['cache_hit_rate_percent'].append(metrics['cache_hit_rate'] * 100)
    baselines['db_latency_p99_ms'].append(metrics['db_latency_p99'])
    baselines['throughput_rps'].append(metrics['throughput'])
    
    import time
    time.sleep(900)  # Wait 15 minutes

# Calculate statistics
results = {}
for key, values in baselines.items():
    results[key] = {
        'min': min(values),
        'max': max(values),
        'avg': sum(values) / len(values),
        'p50': sorted(values)[len(values)//2],
        'p95': sorted(values)[int(len(values)*0.95)],
        'p99': sorted(values)[int(len(values)*0.99)],
    }

# Save baselines
with open('performance-baselines-production.json', 'w') as f:
    json.dump(results, f, indent=2)

# Display results
for metric, stats in results.items():
    print(f"\n{metric}:")
    print(f"  Avg: {stats['avg']:.2f}")
    print(f"  P95: {stats['p95']:.2f}")
    print(f"  P99: {stats['p99']:.2f}")
```

### Baseline Thresholds

Use established baselines to set alert thresholds:

```json
{
  "api_latency_p99_ms": {
    "baseline": 85,
    "warning": 150,
    "critical": 300
  },
  "error_rate_percent": {
    "baseline": 0.05,
    "warning": 0.5,
    "critical": 2
  },
  "cache_hit_rate_percent": {
    "baseline": 65,
    "warning": 40,
    "critical": 20
  },
  "throughput_rps": {
    "baseline": 3.8,
    "warning": 2.5,
    "critical": 1.5
  }
}
```

---

## Troubleshooting

### Issue 1: No Metrics Being Collected

**Symptoms**: Prometheus shows "No target found" for some jobs

**Diagnosis**:

```bash
# Check if services are exposing metrics
curl http://localhost:8000/metrics | head -10
curl http://neo4j:7687/metrics | head -10
curl http://redis:6379/INFO | head -10

# Check Prometheus scrape logs
docker-compose logs prometheus | grep scrape_failed
```

**Solution**:

```bash
# Ensure /metrics endpoint is implemented in FastAPI
# Verify docker-compose.yml target addresses are correct
# Check firewall rules allow metric scrape ports

# Restart Prometheus
docker-compose restart prometheus
```

### Issue 2: Alert Not Firing

**Symptoms**: Alert condition met but no notification

**Diagnosis**:

```bash
# Check AlertManager is running
curl http://localhost:9093

# Test the alert rule
docker-compose exec prometheus promtool check rules alert_rules.yml

# Check Alert Manager config
curl http://localhost:9093/api/v1/alerts
```

**Solution**:

```bash
# Verify alert rule syntax is correct
# Ensure AlertManager is receiving alerts from Prometheus
# Check notification channel configuration (Slack webhook, email, etc.)

# Test Slack webhook
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from Prometheus"}' \
  YOUR_SLACK_WEBHOOK_URL
```

### Issue 3: High False Positive Alerts

**Symptoms**: Alerts triggering for brief spikes (false positives)

**Solution**:

```yaml
# Increase "for" duration to require sustained condition

- alert: HighErrorRate
  expr: rate(http_errors_total[5m]) / rate(http_requests_total[5m]) * 100 > 1
  for: 5m  # Changed from 1m to 5m
  labels:
    severity: critical
```

---

## Summary

This monitoring setup provides:

✅ **Real-time metrics** via Prometheus  
✅ **Visual dashboards** via Grafana  
✅ **Automated alerts** via Alert Manager  
✅ **Centralized logging** via ELK stack  
✅ **Performance trending** via baselines  
✅ **Incident response** automation  

---

**Setup Complete Checklist**:
- [ ] Prometheus scraping metrics from all services
- [ ] Grafana dashboards created and displaying data
- [ ] Alert rules loaded and evaluating
- [ ] Slack/Email notifications working
- [ ] Performance baselines established
- [ ] Team trained on monitoring system

---

**Document Status**: Final  
**Last Updated**: 2026-05-19  
**Owner**: DevOps / SRE Team

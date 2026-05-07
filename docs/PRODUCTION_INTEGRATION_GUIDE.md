# Production Integration Guide: basset-hound + basset-verify

## Overview

This guide covers how to set up and deploy basset-hound with basset-verify integration in production. The integration provides identifier verification capabilities (email, phone, crypto addresses, domains, IPs, URLs, usernames) to the basset-hound OSINT platform.

**Version**: Phase 7.3 (Production Ready)  
**Last Updated**: 2026-05-06

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      basset-hound                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (port 8000)                          │  │
│  │  - 12 MCP verification tools                         │  │
│  │  - Entity management                                 │  │
│  │  - Relationship tracking                             │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                                                  │
│           └─────────────────┬──────────────────────────┐    │
│                             │                          │    │
│  ┌────────────────────────────────┐      ┌──────────────────┐
│  │ basset-verify Client           │      │ Local Fallback   │
│  │ (graceful degradation)         │      │ Verification     │
│  └────────────────────────────────┘      └──────────────────┘
└─────────────────────────────────────────────────────────────┘
           │ HTTP
           │ (port 8001)
┌──────────▼────────────────────────────────────────────────────┐
│                   basset-verify                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (port 8001)                            │  │
│  │  - Email verification                                  │  │
│  │  - Phone number verification                           │  │
│  │  - Crypto address verification + poisoning detection   │  │
│  │  - Domain verification                                 │  │
│  │  - IP address verification                             │  │
│  │  - URL verification                                    │  │
│  │  - Username verification                               │  │
│  │  - Batch verification (up to 100 items)               │  │
│  │  - Caching layer                                       │  │
│  │  - Rate limiting                                       │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

1. Docker and Docker Compose
2. Both repositories cloned:
   - `/home/devel/basset-hound`
   - `/home/devel/basset-verify`

### 1. Deploy with Docker Compose (Recommended)

```bash
# Navigate to basset-hound directory
cd /home/devel/basset-hound

# Start all services (includes basset-verify)
docker-compose up -d

# Verify all services are healthy
docker-compose ps
# All should show "healthy" or "running"

# Check logs
docker-compose logs -f basset_api
docker-compose logs -f basset_verify
```

### 2. Verify Integration

```bash
# Check basset-verify is accessible
curl http://localhost:8001/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2026-05-06T10:00:00Z"
# }

# Check basset-hound is running
curl http://localhost:8080/health
```

### 3. Run E2E Tests

```bash
# Run production integration tests
pytest tests/production/test_e2e_production.py -v

# Run with coverage
pytest tests/production/test_e2e_production.py --cov=api --cov=basset_mcp --cov-report=html

# Run specific test class
pytest tests/production/test_e2e_production.py::TestVerificationToolsDelegation -v
```

## Configuration

### Environment Variables

Configure basset-verify integration via environment variables:

```bash
# Required
BASSET_VERIFY_URL=http://basset_verify:8001
BASSET_VERIFY_ENABLED=true

# Optional (with defaults)
BASSET_VERIFY_TIMEOUT=10.0  # Seconds (5-30 recommended)
```

### In Docker Compose

The `docker-compose.yml` includes basset-verify configuration:

```yaml
basset_api:
  environment:
    - BASSET_VERIFY_URL=http://basset_verify:8001
    - BASSET_VERIFY_TIMEOUT=10.0
    - BASSET_VERIFY_ENABLED=true
```

### In .env File

Create or update `.env`:

```
# basset-verify integration
BASSET_VERIFY_URL=http://localhost:8001
BASSET_VERIFY_TIMEOUT=10.0
BASSET_VERIFY_ENABLED=true
```

### In Python Code

Access configuration programmatically:

```python
from api.config import get_settings

settings = get_settings()
print(settings.basset_verify_url)      # http://basset_verify:8001
print(settings.basset_verify_timeout)  # 10.0
print(settings.basset_verify_enabled)  # True
```

## Integration Points

### 1. BassetVerifyClient

The main client for communicating with basset-verify:

```python
from api.clients.basset_verify_client import BassetVerifyClient

client = BassetVerifyClient(
    base_url="http://basset_verify:8001",
    timeout=10.0
)

# Verify an email
result = await client.verify_email("user@example.com")
print(result.status)      # "valid", "invalid", "plausible", etc.
print(result.confidence)  # 0.0 to 1.0
print(result.details)     # Additional verification details
```

### 2. MCP Verification Tools

The 12 MCP tools delegate to basset-verify:

1. **get_verification_types** - Get supported types and levels
2. **verify_email** - Verify email addresses
3. **verify_phone** - Verify phone numbers
4. **verify_crypto** - Verify crypto addresses (all chains)
5. **verify_domain** - Verify domain names
6. **verify_ip** - Verify IP addresses (IPv4/IPv6)
7. **verify_url** - Verify URLs
8. **verify_username** - Verify usernames
9. **verify_identifier** - Generic identifier verification
10. **batch_verify** - Verify multiple identifiers
11. **get_crypto_matches** - Find all crypto address matches
12. **get_supported_cryptocurrencies** - List supported chains

### 3. VerificationService

Local verification service with fallback:

```python
from api.services.verification_service import VerificationService

service = VerificationService()
result = await service.verify_email("user@example.com")
```

## Graceful Fallback

When basset-verify is unavailable, the system gracefully degrades:

1. **Status**: Results show `verification_unavailable`
2. **Confidence**: Set to 0.0
3. **Warnings**: Include message about unavailable service
4. **Allows Override**: Set to True for manual verification
5. **Local Fallback**: Uses VerificationService for basic validation

Example response when service is unavailable:

```json
{
  "identifier_type": "email",
  "identifier_value": "user@example.com",
  "status": "verification_unavailable",
  "verification_level": "none",
  "is_valid": null,
  "confidence": 0.0,
  "warnings": ["basset-verify service is unavailable"],
  "errors": [],
  "allows_override": true,
  "override_hint": "Verification service unavailable. Manual verification recommended."
}
```

## Performance Expectations

### Single Verification Latency

- **Format validation**: < 100ms
- **Network verification**: 100-500ms
- **External API verification**: 500-2000ms
- **With caching**: 10-50ms for cached results

### Batch Verification (5 items)

- **Format level**: < 500ms
- **Network level**: 500-2000ms
- **External API level**: 2-5 seconds

### Throughput

- **Requests per second**: 100+
- **Concurrent connections**: 50+
- **Rate limit**: 60 requests/minute per IP (configurable)

### Timeout Configuration

Recommended timeout settings:

- **Development**: 5 seconds
- **Production**: 10 seconds
- **High-latency networks**: 15-20 seconds

## Troubleshooting

### Issue: basset-verify service unreachable

**Symptoms**: "Connection refused" or "Timeout" errors

**Solutions**:

1. Verify service is running:
   ```bash
   docker ps | grep basset_verify
   ```

2. Check service logs:
   ```bash
   docker logs basset_verify
   ```

3. Verify network connectivity:
   ```bash
   docker exec basset_api curl http://basset_verify:8001/health
   ```

4. Check configuration:
   ```bash
   docker exec basset_api python -c "from api.config import get_settings; s = get_settings(); print(f'URL: {s.basset_verify_url}, Timeout: {s.basset_verify_timeout}')"
   ```

### Issue: High latency or timeouts

**Symptoms**: Verification requests taking > 2 seconds or timing out

**Solutions**:

1. Increase timeout:
   ```bash
   BASSET_VERIFY_TIMEOUT=15.0 docker-compose up
   ```

2. Check system resources:
   ```bash
   docker stats basset_verify
   ```

3. Check basset-verify logs:
   ```bash
   docker logs -f basset_verify
   ```

4. Monitor network:
   ```bash
   docker exec basset_api curl -w "@curl-format.txt" http://basset_verify:8001/health
   ```

### Issue: Intermittent failures

**Symptoms**: Some requests succeed, others fail

**Solutions**:

1. Check service health:
   ```bash
   curl http://localhost:8001/health
   ```

2. Review error logs:
   ```bash
   docker logs basset_verify | grep ERROR
   docker logs basset_api | grep ERROR
   ```

3. Check Redis (if used):
   ```bash
   docker exec redis redis-cli ping
   ```

4. Restart services:
   ```bash
   docker-compose restart basset_verify
   docker-compose restart basset_api
   ```

### Issue: High error rates (> 5%)

**Symptoms**: Many requests returning errors

**Solutions**:

1. Check basset-verify health:
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/docs  # OpenAPI docs
   ```

2. Review recent logs:
   ```bash
   docker logs --tail 100 basset_verify
   ```

3. Check external dependencies:
   - DNS servers (if doing DNS verification)
   - External APIs (for extended verification)
   - Network connectivity

4. Scale up if needed:
   ```bash
   docker-compose up -d --scale basset_verify=2
   ```

## Disabling Integration

To disable basset-verify and fall back to local verification:

### Option 1: Environment Variable

```bash
BASSET_VERIFY_ENABLED=false docker-compose up
```

### Option 2: .env File

```
BASSET_VERIFY_ENABLED=false
```

### Option 3: Code

```python
from api.config import Settings, get_settings

# Modify settings
settings = get_settings()
settings.basset_verify_enabled = False
```

### Impact

- Verification will use local VerificationService
- Format validation still works
- Network-level verification unavailable
- Results marked as `verification_unavailable`
- No API calls to external services

## Monitoring Integration Health

### Health Check Endpoint

```bash
curl http://localhost:8001/health

# Response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "timestamp": "2026-05-06T10:00:00Z"
# }
```

### Metrics Endpoint

```bash
curl http://localhost:8001/metrics

# Shows Prometheus-style metrics
```

### Log Monitoring

```bash
# Follow basset-verify logs
docker logs -f basset_verify

# Follow basset-hound logs
docker logs -f basset_api

# Filter for errors
docker logs basset_verify | grep ERROR
docker logs basset_api | grep "basset-verify"
```

### Monitoring Checklist

- [ ] Health checks returning status="healthy"
- [ ] Response latency < 2 seconds
- [ ] Error rate < 5%
- [ ] No connection timeouts in logs
- [ ] No rate limit exceeded errors
- [ ] Graceful fallback working when service unavailable

## Common Issues and Solutions

### CORS Errors

**Problem**: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution**: Already configured in basset-verify, but verify:

```python
# basset-verify config
BASSET_CORS_ALLOWED_ORIGINS="*"  # Or specific origins in production
```

### Rate Limiting

**Problem**: "Too many requests" (429 status)

**Solution**: Configure rate limits:

```bash
BASSET_RATELIMIT_REQUESTS_PER_MINUTE=60
BASSET_RATELIMIT_BURST_SIZE=10
```

### Memory Issues

**Problem**: Services running out of memory

**Solution**: Configure memory limits in docker-compose.yml:

```yaml
basset_verify:
  deploy:
    resources:
      limits:
        memory: 512M
```

### DNS Resolution

**Problem**: DNS verification failing

**Solution**: Check DNS configuration:

```bash
BASSET_DNS_TIMEOUT=5.0
BASSET_DNS_CACHE_TTL=3600
BASSET_DNS_SERVERS="8.8.8.8,8.8.4.4,1.1.1.1"
```

## Security Considerations

### 1. Network Security

- Use internal Docker network (default)
- Don't expose basset-verify on public internet
- Use firewall rules to restrict access

### 2. API Keys (if implemented)

- Store securely in environment variables
- Never log sensitive keys
- Rotate regularly

### 3. Data Privacy

- basset-verify doesn't store verification data
- Results stored in basset-hound database only
- Configure `BASSET_SECURITY_NO_IDENTIFIER_LOGGING=true`

### 4. Rate Limiting

- Enabled by default (60 req/min per IP)
- Adjust as needed for your use case
- Monitor for abuse patterns

## Performance Tuning

### Optimization Steps

1. **Use caching**:
   ```bash
   BASSET_DNS_CACHE_TTL=3600
   CACHE_ENABLED=true
   ```

2. **Increase timeout for slow networks**:
   ```bash
   BASSET_VERIFY_TIMEOUT=15.0
   ```

3. **Increase worker processes**:
   ```yaml
   basset_verify:
     environment:
       - BASSET_SERVER_WORKERS=8
   ```

4. **Use batch verification**:
   ```python
   # More efficient than individual calls
   items = [{"value": "...", "type": "email"}, ...]
   result = await client.batch_verify(items)
   ```

5. **Monitor resource usage**:
   ```bash
   docker stats basset_verify
   docker stats basset_api
   ```

## Testing Integration

### Unit Tests

```bash
# Run basset-verify unit tests
cd /home/devel/basset-verify
pytest tests/ -v

# Run basset-hound integration tests
cd /home/devel/basset-hound
pytest tests/integration/ -v
```

### Integration Tests

```bash
# Run production E2E tests
pytest tests/production/test_e2e_production.py -v

# Run with coverage
pytest tests/production/test_e2e_production.py --cov --cov-report=html

# Run specific test
pytest tests/production/test_e2e_production.py::TestVerificationToolsDelegation::test_email_verification_delegation -v
```

### Manual Testing

```bash
# Test email verification
curl -X POST http://localhost:8001/verify/email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "level": "format"}'

# Test batch verification
curl -X POST http://localhost:8001/verify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"value": "test@example.com", "type": "email"},
      {"value": "example.com", "type": "domain"}
    ],
    "level": "format"
  }'

# Test crypto verification
curl -X POST http://localhost:8001/verify/crypto \
  -H "Content-Type: application/json" \
  -d '{"address": "0x742d35Cc6634C0532925a3b844Bc9e7595f42bB"}'
```

## Upgrade and Maintenance

### Upgrading basset-verify

```bash
cd /home/devel/basset-verify

# Pull latest changes
git pull origin main

# Rebuild image
docker-compose build --no-cache basset_verify

# Restart service
docker-compose restart basset_verify

# Verify health
curl http://localhost:8001/health
```

### Upgrading basset-hound

```bash
cd /home/devel/basset-hound

# Pull latest changes
git pull origin main

# Rebuild image
docker-compose build --no-cache basset_api

# Restart service
docker-compose restart basset_api

# Verify health
curl http://localhost:8080/health
```

### Database Migrations

If basset-hound schema changes:

```bash
docker-compose exec basset_api python -m alembic upgrade head
```

## Support and Resources

### Documentation

- basset-hound: `/home/devel/basset-hound/docs/`
- basset-verify: `/home/devel/basset-verify/README.md`

### API Documentation

- basset-verify OpenAPI: http://localhost:8001/docs
- basset-hound OpenAPI: http://localhost:8080/docs

### Monitoring

Production dashboards (if configured):
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

### Logs

```bash
# Tail all logs
docker-compose logs -f

# Specific service
docker-compose logs -f basset_verify
docker-compose logs -f basset_api

# Filter by keyword
docker logs -f basset_verify | grep ERROR
docker logs -f basset_api | grep verify
```

## Version History

### Phase 7.3 (2026-05-06) - Production Ready

- Full basset-verify integration
- 12 MCP verification tools delegation
- Graceful fallback mechanism
- E2E production tests
- Monitoring and observability
- Comprehensive documentation

## FAQ

**Q: Does basset-verify store data?**  
A: No, basset-verify is stateless. Results are returned but not stored. Storage is in basset-hound only.

**Q: What happens if basset-verify is down?**  
A: System gracefully degrades with "verification_unavailable" status. Users can manually override results.

**Q: Can I use it without basset-verify?**  
A: Yes, disable with `BASSET_VERIFY_ENABLED=false`. Local verification still works for basic format checks.

**Q: What's the recommended timeout?**  
A: 10 seconds for production. Use 15-20 seconds if on high-latency networks.

**Q: How many concurrent users can it handle?**  
A: Typically 100+ RPS with proper resource allocation. Scale docker containers as needed.

**Q: How do I monitor performance?**  
A: Use `/health`, `/metrics` endpoints and docker stats. Set up Prometheus/Grafana if needed.

## Next Steps

1. Deploy with Docker Compose (see Quick Start)
2. Run E2E tests to verify integration
3. Configure monitoring and alerting
4. Set up production logging
5. Plan backup and disaster recovery

---

**For issues or questions, contact the development team or refer to the main README files in each repository.**

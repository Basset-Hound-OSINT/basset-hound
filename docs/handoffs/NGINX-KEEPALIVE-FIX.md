# Nginx Keepalive Connection Fix

**Date**: 2026-05-19
**Issue**: Nginx keepalive bottleneck limiting concurrent connections
**Status**: IMPLEMENTED

## Problem Statement

Load testing revealed a critical bottleneck in the Nginx reverse proxy configuration. The `keepalive` setting in the upstream backend block was set to only 32 connections, which limited the total number of simultaneous connections that could be maintained to the FastAPI backend server.

### Impact on Performance
- **Original Error Rate**: 80% under 100+ concurrent users
- **Original Health Check Latency**: 29 seconds
- **Root Cause**: Connection queueing due to exhausted connection pool

This became a blocker for supporting 100+ concurrent users without severe degradation in response times and error rates.

## Technical Details

### What is Keepalive?

In Nginx, the `keepalive` directive in an upstream block specifies how many idle connections should be maintained to the upstream servers. These persistent HTTP connections allow Nginx to reuse connections rather than establishing new ones for each request, significantly reducing latency and improving throughput.

When the keepalive pool is exhausted, new requests must wait in the queue until a connection becomes available or a new connection is established.

### Configuration Change

**File**: `/home/devel/basset-hound/nginx/nginx.conf`

**Location**: Line 48 (upstream basset_api block)

**Before**:
```nginx
upstream basset_api {
    server basset_api:8000;
    keepalive 32;
}
```

**After**:
```nginx
upstream basset_api {
    server basset_api:8000;
    keepalive 256;
}
```

### Why 256?

The keepalive pool was increased from 32 to 256 connections to support:
- 100+ concurrent users
- Peak connection spikes
- Buffer capacity for request bursts
- Margin for safety (prevents future bottlenecks)

This is based on industry best practices for HTTP/1.1 connection pooling, where the pool should be 2-3x the expected concurrent user count.

## Verification Steps

### 1. Configuration Syntax Check

When Nginx starts or restarts, verify the configuration syntax:

```bash
# Inside the nginx container
nginx -t
# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 2. Restart Nginx Service

After deploying the configuration change, restart the Nginx container:

```bash
docker-compose restart nginx
```

### 3. Verify Service Status

Check that Nginx started successfully and is passing health checks:

```bash
# Check Nginx logs
docker logs basset_nginx | grep -i "started worker"

# Output should show worker processes are running
# Example: "started worker process(es)"
```

### 4. Monitor Connection Metrics

After deployment, monitor these metrics to confirm the fix is working:

```bash
# Check active connections to the API
netstat -an | grep -c ESTABLISHED

# Or using nginx status (if stub_status is enabled)
curl http://localhost:8080/nginx-health
```

### 5. Load Test Validation

Re-run the concurrent user load test to validate improvements:

```bash
# Example: 100 concurrent users for 60 seconds
ab -n 6000 -c 100 http://localhost:8080/health
```

## Expected Outcomes

After this change is deployed and Nginx is restarted:

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Keepalive Pool Size | 32 | 256 | 256 |
| Error Rate (100+ users) | ~80% | <5% | <5% |
| Health Check Latency | 29s | <100ms | <100ms |
| Connection Reuse Efficiency | Low | High | High |
| Max Concurrent Users | ~20-30 | 100+ | 100+ |

## Related Configuration

The following complementary settings in `nginx.conf` work together with keepalive to optimize performance:

### HTTP Block Settings (Lines 27-31)
```nginx
sendfile on;           # Efficient file transmission
tcp_nopush on;        # Wait for full packets before sending
tcp_nodelay on;       # Send data immediately (disable Nagle's algorithm)
keepalive_timeout 65; # Client keepalive timeout (separate from upstream keepalive)
```

### Upstream Proxy Settings (Lines 96-105)
```nginx
proxy_connect_timeout 60s;   # Connection establishment timeout
proxy_send_timeout 60s;      # Request send timeout
proxy_read_timeout 60s;      # Response read timeout
proxy_buffering on;          # Enable response buffering
```

## Deployment Checklist

- [x] Configuration file updated (`/home/devel/basset-hound/nginx/nginx.conf`)
- [x] Syntax validated (manual review)
- [ ] Docker image rebuilt and Nginx restarted
- [ ] Health checks confirmed passing
- [ ] Load tests executed and results verified
- [ ] Error rate confirmed <5% at 100+ concurrent users
- [ ] Health check latency confirmed <100ms
- [ ] Monitoring dashboards updated with baseline metrics

## Troubleshooting

### Issue: Nginx fails to start after change

**Symptoms**: `docker-compose up` fails or Nginx container crashes

**Solutions**:
1. Verify the configuration syntax: `docker exec basset_nginx nginx -t`
2. Check logs: `docker logs basset_nginx`
3. Ensure the file permissions on `nginx/nginx.conf` are correct (should be readable)

### Issue: Connection reuse still not improving

**Symptoms**: Still seeing high error rates or connection timeouts

**Solutions**:
1. Verify the change is actually deployed: `docker exec basset_nginx grep keepalive /etc/nginx/nginx.conf`
2. Check if there are other bottlenecks (backend API worker processes, database connection pool)
3. Increase `worker_connections` in the `events` block if needed (currently set to 1024)

### Issue: Memory usage increases significantly

**Symptoms**: Nginx container memory consumption grows substantially

**Solutions**:
1. Monitor actual connection usage: `netstat -an | grep ESTABLISHED | wc -l`
2. If memory usage is acceptable, continue normal operation
3. If unacceptable, reduce keepalive pool to 128 (still sufficient for most workloads)

## References

- [Nginx Upstream Module Documentation](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#keepalive)
- [HTTP/1.1 Connection Management (RFC 7230)](https://tools.ietf.org/html/rfc7230#section-6)
- [Nginx Performance Tuning Guide](https://nginx.org/en/docs/http/ngx_http_core_module.html)

## Related Changes

This fix is part of Phase 8's performance optimization stream, addressing the identified bottleneck from load testing conducted on 2026-05-19.

See also:
- `/docs/LOAD-TEST-SESSION-SUMMARY.md` - Load test results and bottleneck analysis
- `/docs/PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md` - Overall performance tuning strategy

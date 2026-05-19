# Connection Pool Tuning Guide

**Phase 8: Connection Pool Optimization**

This guide explains how to configure and optimize connection pools for Neo4j and Redis in Basset Hound to support 1000+ concurrent connections with <1% timeout rate.

## Overview

Connection pooling is critical for high-performance database operations. When properly configured, connection pools:
- Reuse established connections to reduce overhead
- Handle connection failures gracefully with automatic retry logic
- Maintain pool health through keepalive mechanisms
- Support thousands of concurrent requests with minimal timeouts

### Default Configuration

Basset Hound Phase 8 includes optimized connection pool defaults:

| Parameter | Service | Default | Purpose |
|-----------|---------|---------|---------|
| `pool_size` | Neo4j | 50 | Supports 1000+ concurrent connections |
| `connection_lifetime` | Neo4j | 3600s | Recycles connections after 1 hour |
| `max_retry_time` | Neo4j | 60s | Retry timeout for transient failures |
| `socket_keepalive` | Redis | True | Detects and removes dead connections |
| `max_connections` | Redis | 100 | Optimized for 1000+ concurrent clients |
| `health_check_interval` | Redis | 30s | Maintains pool health automatically |

## Neo4j Connection Pool Tuning

### Configuration

The Neo4j connection pool is configured via environment variables:

```bash
# Pool size: number of connections to maintain
NEO4J_POOL_SIZE=50

# Connection lifetime: maximum age of a connection in seconds
# Prevents stale connection issues (default 1 hour)
NEO4J_CONNECTION_LIFETIME=3600

# Max retry time: timeout for handling transient failures
NEO4J_MAX_RETRY_TIME=60

# Connection timeout: timeout for acquiring a connection
NEO4J_CONNECTION_TIMEOUT=30
```

### Sizing the Pool

**Pool Size** determines how many simultaneous connections can be created. For concurrent request handling:

- **Small deployment (1-10 concurrent requests)**: Pool size 10-20
- **Medium deployment (10-100 concurrent requests)**: Pool size 30-50
- **Large deployment (100-1000+ concurrent requests)**: Pool size 50-100

Default is **50**, optimized for 1000+ concurrent connections.

### Monitoring Pool Health

Neo4j provides built-in monitoring through the `/health` endpoint:

```bash
curl http://localhost:8000/health | jq '.services.neo4j'
```

Response includes:
- `status`: "connected" or "disconnected"
- `latency_ms`: Query latency in milliseconds
- `pool_size`: Current pool size configuration
- `connection_lifetime_seconds`: Connection lifetime setting

### Best Practices for Neo4j

1. **Set appropriate pool size**: Rule of thumb is pool_size = (max_concurrent_connections / 100) + 10
2. **Use connection lifetime**: Prevents stale connections from accumulating (set to 1-2 hours)
3. **Monitor latency**: Watch for increasing latency as indicator of pool exhaustion
4. **Enable retry logic**: Set `max_retry_time` to handle transient failures automatically
5. **Connection timeouts**: Set acquisition timeout to 30-60 seconds (prevents hanging requests)

### Troubleshooting Neo4j Connection Issues

**Problem**: "Too many connections" errors
- **Solution**: Increase `NEO4J_POOL_SIZE` incrementally (by 10) until timeout rate drops below 1%
- **Monitor**: Track `latency_ms` in health endpoint to verify improvement

**Problem**: Stale connection errors
- **Solution**: Set `NEO4J_CONNECTION_LIFETIME` to 3600-7200 seconds to recycle old connections
- **Check**: Verify connection age in Neo4j browser with: `CALL dbms.listConnections()`

**Problem**: Intermittent "ServiceUnavailable" errors
- **Solution**: Increase `NEO4J_MAX_RETRY_TIME` to 60+ seconds for transient failure recovery
- **Monitor**: Watch logs for "transient error" patterns

## Redis Connection Pool Tuning

### Configuration

The Redis connection pool is configured via environment variables:

```bash
# Maximum connections in the pool
# Default 100 is optimized for 1000+ concurrent clients
REDIS_MAX_CONNECTIONS=100

# Enable TCP keepalive to detect dead connections
# Prevents "dead connection" issues in long-lived pools
REDIS_SOCKET_KEEPALIVE=true

# Health check interval in seconds
# Automatically pings Redis to maintain pool health
REDIS_HEALTH_CHECK_INTERVAL=30
```

### Sizing the Pool

Redis pool size should be sized based on:
- Number of concurrent application processes
- Redis query distribution (bursty vs. steady)
- Network latency to Redis

Recommended sizing:

- **Single application instance**: 50-100 connections
- **Multiple instances (3-5)**: 100-200 total (20-40 per instance)
- **High-concurrency deployment**: 200-300 connections (scale proportionally)

Default is **100**, optimized for single instance with 1000+ concurrent requests.

### Socket Keepalive

`REDIS_SOCKET_KEEPALIVE=true` enables TCP keepalive on all Redis connections:

**Benefits**:
- Detects dead connections (network failures, Redis restarts)
- Removes stale connections automatically
- Reduces "connection reset" errors

**Trade-off**: Minimal overhead (one TCP keepalive packet every 30+ seconds per idle connection)

### Health Check Interval

`REDIS_HEALTH_CHECK_INTERVAL=30` automatically tests each pooled connection:

**How it works**:
- Every 30 seconds, the pool pings each idle connection
- Dead connections are detected and removed
- New connections are created as needed

**Trade-off**: Small overhead (one PING command per connection per 30 seconds) for significant reliability gain

### Monitoring Pool Health

Monitor Redis health via the `/health` endpoint:

```bash
curl http://localhost:8000/health | jq '.services.redis'
```

Response includes:
- `status`: "connected" or "disconnected"
- `latency_ms`: Redis operation latency
- `pool_size`: Current pool size configuration
- `socket_keepalive`: Whether keepalive is enabled

### Best Practices for Redis

1. **Enable socket keepalive**: Always set `REDIS_SOCKET_KEEPALIVE=true` for production
2. **Set appropriate pool size**: Start with 100, monitor latency, scale up if needed
3. **Health checks**: Set interval to 30 seconds (prevents hanging connections)
4. **Monitor memory**: Use `redis-cli INFO memory` to check Redis memory usage
5. **Connection timeouts**: Ensure your Redis client has appropriate timeouts (5-10 seconds)

### Troubleshooting Redis Connection Issues

**Problem**: "Connection pool exhausted" errors
- **Solution**: Increase `REDIS_MAX_CONNECTIONS` incrementally
- **Monitor**: Check `redis-cli --stat` for connection count

**Problem**: Intermittent "Connection refused" or "Connection reset" errors
- **Solution**: Enable `REDIS_SOCKET_KEEPALIVE=true` and reduce `REDIS_HEALTH_CHECK_INTERVAL` to 15-20 seconds
- **Monitor**: Watch Redis logs for connection drops

**Problem**: High memory usage in Redis
- **Solution**: Reduce pool size or increase Redis instance memory
- **Monitor**: Use `redis-cli INFO memory` to track memory usage

**Problem**: Slow cache performance with high latency
- **Solution**: Verify connection pool isn't exhausted, increase pool size if latency_ms > 100
- **Monitor**: Use `SLOWLOG GET 10` in Redis to identify slow operations

## Combined Neo4j + Redis Configuration

For optimal performance with both databases, use complementary sizing:

### Development (single machine)
```bash
# Neo4j
NEO4J_POOL_SIZE=20
NEO4J_CONNECTION_LIFETIME=3600
NEO4J_MAX_RETRY_TIME=30

# Redis
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_KEEPALIVE=true
REDIS_HEALTH_CHECK_INTERVAL=30
```

### Production (1000+ concurrent)
```bash
# Neo4j
NEO4J_POOL_SIZE=50
NEO4J_CONNECTION_LIFETIME=3600
NEO4J_MAX_RETRY_TIME=60
NEO4J_CONNECTION_TIMEOUT=30

# Redis
REDIS_MAX_CONNECTIONS=100
REDIS_SOCKET_KEEPALIVE=true
REDIS_HEALTH_CHECK_INTERVAL=30
```

### High-Load (multi-instance cluster)
```bash
# Neo4j (with connection pooling)
NEO4J_POOL_SIZE=100
NEO4J_CONNECTION_LIFETIME=1800
NEO4J_MAX_RETRY_TIME=60
NEO4J_CONNECTION_TIMEOUT=30

# Redis (multiple instances, each with)
REDIS_MAX_CONNECTIONS=150
REDIS_SOCKET_KEEPALIVE=true
REDIS_HEALTH_CHECK_INTERVAL=20
```

## Performance Tuning Workflow

### 1. Baseline Measurement

First, establish baseline metrics:

```bash
# Check current health
curl http://localhost:8000/health | jq '.connection_pools'

# Sample output:
# {
#   "neo4j_pool_size": 50,
#   "redis_pool_size": 100,
#   "optimization_status": "optimized for 1000+ concurrent connections with <1% timeout rate"
# }
```

### 2. Load Testing

Run load tests to identify bottlenecks:

```bash
# Use provided load testing scripts
python load_testing_script_v2.py --concurrent 1000 --duration 60

# Monitor connection pools during test:
watch -n 1 'curl -s http://localhost:8000/health | jq ".services"'
```

### 3. Identify Timeouts

If timeout rate > 1%, increase pool sizes:

```bash
# Increase Neo4j pool size
NEO4J_POOL_SIZE=75

# Or increase Redis pool size
REDIS_MAX_CONNECTIONS=150
```

### 4. Monitor Improvements

Verify timeout rate dropped below 1%:

```bash
# Check application logs for timeout errors
grep -i "timeout\|pool.*exhausted" logs/api.log | wc -l
```

### 5. Optimize Further

If performance still needs improvement:
- Increase health check frequency (reduce `REDIS_HEALTH_CHECK_INTERVAL`)
- Reduce connection lifetime (`NEO4J_CONNECTION_LIFETIME`)
- Check database query performance (add indexes if needed)
- Monitor network latency to databases

## Metrics and Monitoring

### Key Metrics to Track

1. **Connection Pool Exhaustion Rate**: Percentage of requests that couldn't get a connection
2. **Connection Latency**: Time to acquire a connection from the pool
3. **Query Latency**: End-to-end query time (includes pool acquisition)
4. **Dead Connection Rate**: How many connections fail due to network issues
5. **Pool Utilization**: Average number of active connections vs. pool size

### Prometheus Integration

Basset Hound exports pool metrics to Prometheus:

```
# Neo4j pool metrics
neo4j_connection_pool_size
neo4j_connection_pool_active
neo4j_connection_pool_idle
neo4j_connection_acquisition_time_ms

# Redis pool metrics
redis_connection_pool_size
redis_connection_pool_active
redis_connection_pool_idle
redis_connection_acquisition_time_ms
```

Query example (showing pool utilization):

```promql
# Redis pool utilization percentage
(redis_connection_pool_active / redis_connection_pool_size) * 100
```

### Grafana Dashboard

Create a Grafana dashboard to visualize:
- Pool utilization over time
- Connection acquisition latency
- Error rate (timeout vs. success)
- Service latency breakdown

## Deployment Sizing Reference

### AWS RDS/Neo4j Cloud

For managed databases, consider:
- Database instance size and network bandwidth
- Multi-AZ failover (may need larger pool for failover recovery)
- Connection limit on database side (Neo4j Cloud has per-instance limits)

```bash
# Neo4j Cloud (5-10 connections per app instance)
NEO4J_POOL_SIZE=50

# RDS Redis (consider multi-AZ and replication)
REDIS_MAX_CONNECTIONS=100
```

### Docker/Kubernetes

In Kubernetes with horizontal scaling:

```yaml
env:
  - name: NEO4J_POOL_SIZE
    value: "50"  # per pod
  - name: REDIS_MAX_CONNECTIONS
    value: "100"  # per pod
```

For N pods, total connections = N × pool_size (can cause database overload if not managed).

**Best practice**: Use a shared connection pool proxy (PgBouncer for PostgreSQL, similar tools for Neo4j/Redis) or implement dynamic pool sizing based on cluster size.

## Troubleshooting Checklist

- [ ] Connection pool size appropriate for concurrent load (rule: size = concurrent_requests / 20 + 10)
- [ ] Socket keepalive enabled for Redis (prevents stale connections)
- [ ] Health checks configured to maintain pool (interval = 20-30 seconds)
- [ ] Connection timeouts set to 30-60 seconds (prevents indefinite hangs)
- [ ] Latency monitored via `/health` endpoint (target <100ms for Neo4j, <50ms for Redis)
- [ ] Timeout error rate tracked (target <1% with optimized settings)
- [ ] Load testing performed to validate settings
- [ ] Database logs reviewed for connection-related warnings
- [ ] Network latency measured between application and databases
- [ ] Database resource limits checked (CPU, memory, connections)

## Additional Resources

- **Neo4j Documentation**: https://neo4j.com/docs/python-manual/current/
- **Redis-py Documentation**: https://redis-py.readthedocs.io/
- **Connection Pool Theory**: https://en.wikipedia.org/wiki/Connection_pool
- **Basset Hound Performance Metrics**: [Performance Metrics Documentation](./PERFORMANCE-METRICS.md)
- **Load Testing**: [Load Testing Guide](../load_testing_script_v2.py)

## Summary

Connection pool optimization is essential for supporting high-concurrency workloads:

1. **Neo4j**: Size pool to 50-100 based on concurrent load, recycle connections every 1-2 hours
2. **Redis**: Size pool to 100+ with keepalive enabled for long-lived connections
3. **Monitor**: Track latency and timeout rate via `/health` endpoint
4. **Scale**: Increase pool sizes incrementally if timeout rate exceeds 1%
5. **Test**: Validate settings with load testing before production deployment

With proper tuning, Basset Hound can reliably support 1000+ concurrent connections with <1% timeout rate.

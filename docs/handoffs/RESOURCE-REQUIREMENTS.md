# Resource Requirements for Basset Hound
## Infrastructure & Scaling Plan (Phases 2-4)

**Date**: 2026-05-19  
**Planning Horizon**: 12 weeks (Phases 2-4)  
**Target Growth**: 100 → 10,000+ concurrent users

---

## Executive Summary

This document outlines infrastructure requirements to support Basset Hound's growth from 100 concurrent users (Phase 1) to 10,000+ concurrent users (Phase 3+). Resource requirements are specified for three scaling tiers, with detailed breakdown of compute, database, storage, and network resources.

---

## 1. Compute Requirements

### 1.1 Current State (Production Day 1)

**Configuration**:
- **API Instances**: 1 x 1vCPU, 1GB RAM
- **Database**: 1 x 4vCPU, 8GB RAM
- **Cache**: 1 x 1vCPU, 2GB RAM
- **Load Balancer**: 1 x 1vCPU, 1GB RAM
- **Total**: 7vCPU, 12GB RAM

**Supports**: 100-200 concurrent users

### 1.2 Phase 2 (Frontend Optimization) - Week 4

**No additional compute required**

- Caching layer improvements reduce backend load
- Same infrastructure sufficient
- **Cost Impact**: ~$0 (existing infrastructure)

### 1.3 Phase 3 (Backend Scaling) - Week 8

**Target**: 10,000+ concurrent users (100+ req/s)

**Recommended Configuration**:
```
API Layer:
  - 4-6 instances x 2vCPU, 2GB RAM each
  - Load balancer: 2vCPU, 2GB RAM (HA pair)
  Total: 10-14vCPU, 10-14GB RAM

Database:
  - Primary: 8vCPU, 16GB RAM
  - Replica 1: 8vCPU, 16GB RAM
  - Replica 2: 4vCPU, 8GB RAM
  Total: 20vCPU, 40GB RAM

Cache Layer:
  - 3 x Redis instances (cluster): 2vCPU, 4GB RAM each
  Total: 6vCPU, 12GB RAM

Monitoring:
  - Prometheus: 2vCPU, 4GB RAM
  - Grafana: 1vCPU, 1GB RAM
  Total: 3vCPU, 5GB RAM

Overall Phase 3: 39-43vCPU, 67-71GB RAM
```

**Cost Estimate** (AWS EC2 pricing, US East):
- **Compute**: ~$3,500-4,500/month
- **Database Storage**: ~$500/month
- **Network**: ~$200-300/month
- **Total**: ~$4,200-5,300/month

### 1.4 Phase 4 (Feature Expansion) - Week 12

**No additional compute**

- Feature expansion uses existing resources
- Optimize utilization, not scale
- **Cost Impact**: ~$0 (same infrastructure)

### 1.5 Scaling Decision Points

| Concurrent Users | Phase | Action |
|---|---|---|
| 100-200 | Phase 1 | Current configuration |
| 200-500 | Phase 2 | Monitor, no changes needed |
| 500-2,000 | Phase 3 Early | Add 2 API instances |
| 2,000-5,000 | Phase 3 Mid | Add 2 more API instances (4 total) |
| 5,000-10,000 | Phase 3 Late | Add 2 more API instances (6 total) |
| 10,000+ | Phase 4 | Database replication + sharding |

---

## 2. Database Resources

### 2.1 Current Database Size

**Metrics**:
- **Total Nodes**: 100,000+ entities
- **Total Relationships**: 500,000+
- **Database Size**: ~50GB
- **Indexes**: 10 (full-text + BTREE)
- **Write QPS**: <50 req/s
- **Read QPS**: <200 req/s

### 2.2 Database Growth Projections

| Phase | Users | Entities | Relationships | DB Size | Growth Rate |
|---|---|---|---|---|---|
| **Phase 1** | 100-200 | 100K | 500K | 50GB | Baseline |
| **Phase 2** | 200-500 | 150K | 750K | 65GB | +30% |
| **Phase 3** | 1000-10K | 500K | 2.5M | 150GB | +130% |
| **Phase 4** | 10K+ | 1M+ | 5M+ | 300GB+ | +100% |

### 2.3 Storage Requirements

**Neo4j Storage Breakdown** (Phase 3, 500K entities):
```
Index storage (30% of total):     45GB
Node data (40% of total):         60GB
Relationship data (20% of total): 30GB
Transaction logs (10% of total):  15GB
─────────────────────────────────
Total:                           150GB
```

**Headroom**: Plan for 200GB total storage (33% overhead for growth)

### 2.4 Memory Requirements

**Neo4j Heap Configuration**:
| Phase | Users | Recommended Heap | Pagecache | Total Memory |
|---|---|---|---|---|
| Phase 1 | 200 | 4GB | 2GB | 8GB |
| Phase 2 | 500 | 6GB | 3GB | 10GB |
| Phase 3 | 10K | 12GB | 6GB | 18GB |
| Phase 4 | 50K+ | 16GB | 8GB | 24GB |

**Calculation**:
- Heap: 1GB per 250K entities
- Pagecache: 50% of heap
- OS buffer: 2GB minimum

### 2.5 Backup Requirements

**Backup Strategy**:
| Item | Frequency | Retention | Storage |
|------|-----------|-----------|---------|
| **Daily backup** | Daily @ 2 AM | 30 days | 50GB × 30 = 1.5TB |
| **Weekly backup** | Weekly @ 2 AM Sunday | 12 weeks | 50GB × 12 = 600GB |
| **Monthly backup** | Monthly @ 1st | 12 months | 50GB × 12 = 600GB |
| **Offsite copy** | Same as backups | 30 days | AWS S3: ~$500/month |

**Total Backup Storage**: ~2.7TB (growing to 6.5TB by Phase 4)

---

## 3. Cache Resources

### 3.1 Redis Cluster Configuration

**Phase 1-2** (Single instance):
```
Memory limit:  2GB
Max memory policy: allkeys-lru
Persistence: RDB (hourly snapshots)
Eviction: LRU when full
```

**Phase 3** (Cluster):
```
Nodes:           3 (primary mode)
Memory per node: 4GB
Total memory:    12GB
Replication:     1 replica per shard
Failover:        Automatic
Persistence:     AOF + RDB
```

**Cache Breakdown** (Phase 3):
```
Entity cache (40%):           4.8GB
Search results (20%):         2.4GB
Session data (15%):           1.8GB
Transitive relationships (15%): 1.8GB
Miscellaneous (10%):          1.2GB
─────────────────────────────
Total:                        12GB
```

### 3.2 Cache Hit Rate Targets

| Phase | Hit Rate Target | Improvement |
|---|---|---|
| Phase 1 | 60% | Baseline |
| Phase 2 | 70% | +10% (frontend caching) |
| Phase 3 | 85%+ | +15% (cluster + warming) |
| Phase 4 | 90%+ | +5% (intelligent invalidation) |

---

## 4. Storage Requirements

### 4.1 Disk Space Allocation

**Production Server** (300GB total):
```
Operating System:      20GB
Application Code:      5GB
Neo4j Data:           150GB (growing to 300GB)
Neo4j Logs:           10GB (rotating)
Redis Data:           15GB
Application Logs:     30GB (rotating)
Backups (local):      50GB (recent backups only)
─────────────────────
Total:               280GB (20% headroom)
```

**Growth Plan**:
- Monitor usage weekly
- Alert at 80% capacity
- Expand before hitting 90%
- Projected timeline: Every 6 months in Phase 3-4

### 4.2 Log Storage

**Log Retention & Storage**:
| Log Type | Retention | Daily Volume | Storage |
|---|---|---|---|
| Application logs | 30 days | 2GB | 60GB |
| Access logs | 90 days | 1GB | 90GB |
| Query logs | 30 days | 500MB | 15GB |
| Audit logs | 1 year | 500MB | 182GB |
| Error logs | 30 days | 200MB | 6GB |

**Total Log Storage**: ~350GB (growing)

**Recommendation**: Use ELK stack or cloud logging service (AWS CloudWatch, DataDog, etc.)

---

## 5. Network Resources

### 5.1 Bandwidth Estimation

**Phase 1** (200 users):
- Average request size: 50KB
- Response size: 100KB
- Throughput: 3 req/s
- Bandwidth: 150 KB/s = 1.2 Mbps average, 12 Mbps peak

**Phase 3** (10,000 users):
- Average request size: 50KB
- Response size: 100KB
- Throughput: 100 req/s
- Bandwidth: 5 MB/s = 40 Mbps average, 200 Mbps peak

**Network Sizing**:
| Phase | Average | Peak | Recommended Link |
|---|---|---|---|
| Phase 1 | 1.2 Mbps | 12 Mbps | 100 Mbps |
| Phase 2 | 2 Mbps | 20 Mbps | 100 Mbps |
| Phase 3 | 40 Mbps | 200 Mbps | 1000 Mbps |
| Phase 4 | 100 Mbps | 500 Mbps | 1000 Mbps |

**Cost** (AWS Direct Connect, 1000 Mbps):
- Commitment: $0.30/Gbps/hour
- Monthly: ~$2,160/month

### 5.2 CDN for Static Content

**Recommendation**: CloudFront or equivalent for:
- JavaScript bundles (290KB gzip, served to all users)
- CSS stylesheets (50KB gzip)
- Images (100KB average per entity)
- Font files (100KB)

**Cost**: ~$50-200/month (depends on traffic)

---

## 6. Disaster Recovery Infrastructure

### 6.1 Backup Infrastructure

**Requirement**:
- **Primary backup**: Local NAS (2-3 days of backups)
- **Secondary backup**: AWS S3 with versioning
- **Tertiary backup**: Tape archive (1+ year retention)

**Cost Estimate**:
| Component | Monthly Cost |
|---|---|
| Local NAS (10TB) | $200 (amortized) |
| AWS S3 storage (2TB) | $50 |
| S3 transfer | $50 |
| Tape archive | $100 |
| **Total** | **$400** |

### 6.2 Disaster Recovery Site

**Optional** (for Tier 1 SLA):
- Standby database replica in different region
- Automatic failover capability
- Data sync latency: <1 second

**Cost**: $3,000-5,000/month (additional infrastructure)

---

## 7. Monitoring Infrastructure

### 7.1 Monitoring Stack

**Components**:
- **Prometheus**: 2vCPU, 4GB RAM, 100GB storage
- **Grafana**: 1vCPU, 1GB RAM
- **Alertmanager**: 1vCPU, 1GB RAM
- **Log aggregation** (ELK/DataDog): Varies

**Cost Estimate** (self-hosted):
- Compute: $400-600/month
- Storage: $100-200/month
- **Total**: $500-800/month

**Alternative** (SaaS like DataDog):
- **Cost**: $1,000-2,000/month (depending on scale)

### 7.2 Metrics Collection

**Required Metrics**:
- Application metrics: 10,000+ time series
- System metrics: 1,000+ time series
- Database metrics: 500+ time series
- **Total**: ~11,500 time series

**Storage**: ~200GB for 1-year retention at typical compression

---

## 8. Security Infrastructure

### 8.1 SSL/TLS Certificates

**Provider**: Let's Encrypt (free) or commercial CA (~$100-500/year)

**Management**:
- Automatic renewal (certbot)
- Multi-domain certificate for: api.domain, www.domain, etc.

### 8.2 DDoS Protection

**Optional services**:
- **Cloudflare**: $20-200/month
- **AWS Shield**: $3,000/month
- **Akamai/Imperva**: $5,000+/month

**Recommendation**: Use Cloudflare for Phase 2+

---

## 9. Development & Testing Infrastructure

### 9.1 Staging Environment

**Requirement**: Near-parity with production

**Configuration**:
- 2 API instances (vs 4-6 in prod)
- 1 database replica
- 1 cache instance
- Same monitoring stack

**Cost**: ~50% of production (~$2,000-2,500/month)

### 9.2 Development & CI/CD

**Infrastructure**:
- **CI/CD Server** (Jenkins/GitLab Runner): 2vCPU, 4GB RAM (~$200/month)
- **Artifact storage** (Docker registry): 100GB (~$50/month)
- **Test databases**: 2 instances (~$400/month)

**Cost**: ~$650/month

---

## 10. Summary by Phase

### Total Cost of Ownership

**Phase 1 (Current)**:
```
Production Compute:        $800
Database:                  $500
Cache:                     $200
Storage:                   $200
Networking:                $200
Monitoring:                $400
Staging:                   $400
CI/CD:                     $650
─────────────────────────
Monthly Total:           $3,750
Quarterly:              $11,250
```

**Phase 2** (Week 4):
```
Same as Phase 1 + monitoring upgrades
Monthly: $4,000 (+$250 for ELK/DataDog)
```

**Phase 3** (Week 8):
```
Production Compute:      $3,500
Database (replicas):     $1,500
Cache (cluster):         $400
Storage:                 $300
Networking:              $2,200 (CDN + 1G link)
Monitoring:              $1,000
Staging:                 $2,000
CI/CD:                   $650
Backup/DR:               $400
─────────────────────────
Monthly Total:          $11,950
Quarterly:              $35,850
```

**Phase 4** (Week 12):
```
Additional feature infrastructure
GraphQL caching:         $200
ML infrastructure:       $500 (vector DB)
Advanced search:         $300 (elasticsearch)
─────────────────────────
Monthly Total:          $12,950
Quarterly:              $38,850
```

---

## 11. Procurement Timeline

### Immediate (Before Production)
- [ ] Production environment finalized
- [ ] SSL certificates obtained
- [ ] Monitoring tools configured
- [ ] Backup infrastructure tested

### Phase 2 (Week 2-4)
- [ ] Monitor resource utilization
- [ ] Plan Phase 3 infrastructure
- [ ] Order additional hardware if on-premises

### Phase 3 (Week 5-8)
- [ ] Procure additional compute resources
- [ ] Deploy read replicas
- [ ] Deploy Redis cluster
- [ ] Implement load balancing

### Phase 4 (Week 9-12)
- [ ] ML infrastructure (if needed)
- [ ] Advanced search engines (optional)
- [ ] Enhanced monitoring (optional)

---

## 12. Vendor Recommendations

### Cloud Provider
- **AWS**: Most flexible, pay-as-you-go pricing
- **GCP**: Good for machine learning workloads
- **Azure**: Good for enterprise deployments
- **Recommendation**: AWS for phases 2-3, consider multi-cloud by Phase 4

### Database Service
- **AWS RDS for Neo4j**: Managed service (~$1,000+/month)
- **Self-hosted Neo4j**: More control, lower cost (~$500/month)
- **Recommendation**: Self-hosted for cost, managed for operational simplicity

### Cache Service
- **AWS ElastiCache**: ~$300-500/month
- **Self-hosted Redis**: ~$100-200/month
- **Recommendation**: ElastiCache for Phase 3+ (operational overhead reduction)

### Log Aggregation
- **AWS CloudWatch**: $1/GB ingested (~$500-1000/month)
- **DataDog**: $10-20 per host (~$1000+/month)
- **ELK Stack**: Self-hosted (~$500/month infrastructure)
- **Recommendation**: DataDog for Phase 3+ (comprehensive features)

---

## 13. Capacity Planning Worksheet

**Instructions**: Fill in your specific requirements

```
Current Production (Today):
┌─────────────────────────────────────────────────────────┐
│ Concurrent Users:           [____]                      │
│ Database Size:              [____] GB                   │
│ Peak Throughput:            [____] req/s                │
│ Cache Hit Rate:             [____]%                     │
└─────────────────────────────────────────────────────────┘

Phase 3 Target (Week 8):
┌─────────────────────────────────────────────────────────┐
│ Concurrent Users:           [____] (target: 10,000)    │
│ Expected Database Size:      [____] GB                  │
│ Peak Throughput Target:      [____] req/s (target: 100)│
│ Cache Hit Rate Target:       [____]% (target: 85%)     │
│ Infrastructure Cost Budget:  $[____]/month              │
└─────────────────────────────────────────────────────────┘

Risk Factors:
┌─────────────────────────────────────────────────────────┐
│ Growth faster than expected:         Yes / No           │
│ Significant spike events planned:     Yes / No           │
│ International expansion needed:       Yes / No           │
│ Redundancy requirements (99.99%?):    Yes / No           │
└─────────────────────────────────────────────────────────┘
```

---

## References

- AWS Pricing Calculator
- GCP Pricing Calculator
- Neo4j Capacity Planning Guide
- Redis Memory Optimization
- Nginx Load Balancer Sizing
- Database Backup Best Practices

---

**Owner**: DevOps / Infrastructure Team  
**Last Updated**: 2026-05-19  
**Next Review**: Phase 2 kickoff (Week 2)  
**Approval Required**: CTO, Finance

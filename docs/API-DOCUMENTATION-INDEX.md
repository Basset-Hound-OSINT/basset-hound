# Basset Hound API Documentation Index

**Last Updated**: 2026-05-19  
**Version**: 3.0.0

This index provides a comprehensive guide to all API documentation for Basset Hound. Use this page to find the right documentation for your use case.

---

## Quick Navigation

### For API Users

- **Getting Started**: [API-REFERENCE-COMPREHENSIVE.md](#api-reference-comprehensive) - Start here
- **Integration**: [INTEGRATION-GUIDE.md](#integration-guide) - How to integrate with the API
- **Webhooks**: [WEBHOOK-DOCUMENTATION.md](#webhook-documentation) - Receive real-time events
- **Troubleshooting**: [API-TROUBLESHOOTING.md](#api-troubleshooting) - Common issues and solutions

### For DevOps/Operations

- **Deployment**: [DEPLOYMENT-CHECKLIST.md](./DEPLOYMENT-CHECKLIST.md) - Pre-production verification
- **Database**: [DATABASE-OPTIMIZATION.md](./DATABASE-OPTIMIZATION.md) - Performance tuning
- **Connections**: [CONNECTION-POOL-TUNING.md](./CONNECTION-POOL-TUNING.md) - Connection pool optimization
- **Health**: [API-REFERENCE-COMPREHENSIVE.md#getting-started](#api-reference-comprehensive) - Health endpoints

### For Developers

- **API Changelog**: [API-CHANGELOG.md](#api-changelog) - Version history and breaking changes
- **Architecture**: [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- **Code Examples**: [INTEGRATION-GUIDE.md#code-examples](#integration-guide) - Python, JavaScript, cURL

---

## Documentation by Purpose

### 1. Understanding the API

| Document | Purpose | Audience |
|----------|---------|----------|
| [API-REFERENCE-COMPREHENSIVE.md](#api-reference-comprehensive) | Complete endpoint reference with examples | All |
| [API-CHANGELOG.md](#api-changelog) | Version history, breaking changes, migration | Developers |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design and integration points | Architects, DevOps |

### 2. Using the API

| Document | Purpose | Audience |
|----------|---------|----------|
| [INTEGRATION-GUIDE.md](#integration-guide) | How to build clients and integrate | Developers |
| [WEBHOOK-DOCUMENTATION.md](#webhook-documentation) | Event subscriptions and webhooks | Developers |
| [Code Examples](#integration-guide) | Copy-paste ready examples | Developers |

### 3. Troubleshooting

| Document | Purpose | Audience |
|----------|---------|----------|
| [API-TROUBLESHOOTING.md](#api-troubleshooting) | Common issues and solutions | All |
| [API-REFERENCE-COMPREHENSIVE.md#error-handling](#api-reference-comprehensive) | Error codes and meanings | Developers |

### 4. Operations

| Document | Purpose | Audience |
|----------|---------|----------|
| [DEPLOYMENT-CHECKLIST.md](./DEPLOYMENT-CHECKLIST.md) | Pre-deployment verification | DevOps, Ops |
| [DATABASE-OPTIMIZATION.md](./DATABASE-OPTIMIZATION.md) | Database tuning for performance | DevOps |
| [CONNECTION-POOL-TUNING.md](./CONNECTION-POOL-TUNING.md) | Connection pool settings | DevOps |
| [DEPLOYMENT-RUNBOOK.md](./DEPLOYMENT-RUNBOOK.md) | Step-by-step deployment | DevOps |

---

## Document Details

### API-REFERENCE-COMPREHENSIVE.md
**File**: `/home/devel/basset-hound/docs/API-REFERENCE-COMPREHENSIVE.md`

**Size**: ~50 KB  
**Sections**: 20+

**Contents**:
- Overview and key features
- Getting started (5 minute quickstart)
- Authentication (JWT tokens, login flow, token refresh)
- Rate limiting (limits, headers, handling)
- Error handling (HTTP codes, error codes, responses)
- Response formats (success, error, list responses)
- 50+ complete endpoint specifications with:
  - HTTP method and path
  - Request parameters and body
  - Response examples
  - Error codes
  - Authentication requirements
- Common patterns and examples
- Troubleshooting basics

**Best For**:
- Learning the API structure
- Finding specific endpoint documentation
- Understanding authentication and rate limiting
- Copy-paste ready request examples

**Example Usage**:
```
Q: How do I create an entity?
A: See "Create Entity" section in API-REFERENCE-COMPREHENSIVE.md
```

---

### INTEGRATION-GUIDE.md
**File**: `/home/devel/basset-hound/docs/INTEGRATION-GUIDE.md`

**Size**: ~40 KB  
**Sections**: 15+

**Contents**:
- Quick start (authentication, first request)
- Token management (login, refresh, validation)
- HTTP client setup for:
  - cURL
  - Python (requests)
  - JavaScript (fetch, axios)
- Request/response patterns
- Error handling with retry logic
- Pagination patterns
- Filtering and sorting
- Rate limiting strategies
- WebSocket integration (JavaScript & Python)
- Webhook integration (receiving events)
- Complete Python client implementation
- Best practices (error handling, connection pooling, caching)

**Best For**:
- Building API clients
- Integrating with external systems
- Understanding API patterns
- Copy-paste working code

**Example Usage**:
```
Q: How do I implement exponential backoff for rate limits?
A: See "Implement Backoff Strategy" in INTEGRATION-GUIDE.md
```

---

### WEBHOOK-DOCUMENTATION.md
**File**: `/home/devel/basset-hound/docs/WEBHOOK-DOCUMENTATION.md`

**Size**: ~35 KB  
**Sections**: 10+

**Contents**:
- Overview and use cases
- Available webhook events (9 event types)
- Creating webhook subscriptions
- Webhook format (headers, body, response)
- Delivery and retry policy (exponential backoff)
- Security (HMAC-SHA256 signature verification)
- Testing webhooks
- Managing webhooks (CRUD operations)
- Complete working examples:
  - Slack integration
  - Database logging
  - Deduplication processing
- Troubleshooting

**Best For**:
- Setting up webhook receivers
- Integrating with external services (Slack, databases)
- Understanding event-driven architecture
- Testing webhooks locally

**Example Usage**:
```
Q: How do I verify webhook signatures?
A: See "Security" section in WEBHOOK-DOCUMENTATION.md
```

---

### API-TROUBLESHOOTING.md
**File**: `/home/devel/basset-hound/docs/API-TROUBLESHOOTING.md`

**Size**: ~40 KB  
**Sections**: 15+

**Contents**:
- Quick diagnostic commands
- Common issues with solutions:
  - Authentication (401, 403 errors)
  - Entity not found (404 errors)
  - Rate limiting (429 errors)
  - Performance issues (slow queries)
  - Connection issues (timeouts, pool exhaustion)
  - Database issues (Neo4j connection, timeouts)
  - Data issues (empty results, duplicates)
  - Request issues (400, 422 errors)
  - WebSocket issues
  - Cache issues
- Debug techniques (debug mode, logging, verbose cURL)
- Performance profiling
- Getting help resources

**Best For**:
- Fixing API integration issues
- Diagnosing performance problems
- Understanding error messages
- Debugging integration problems

**Example Usage**:
```
Q: I'm getting 429 Too Many Requests errors
A: See "Rate Limiting" section in API-TROUBLESHOOTING.md
```

---

### API-CHANGELOG.md
**File**: `/home/devel/basset-hound/docs/API-CHANGELOG.md`

**Size**: ~25 KB  
**Sections**: 10+

**Contents**:
- Version history (v1.0.0, v2.0.0, v3.0.0)
- API evolution timeline
- Growth metrics
- Breaking changes (none between v2.0 and v3.0)
- Migration guides:
  - From v2.0.0 to v3.0.0 (step-by-step)
  - From v1.0.0 to v3.0.0
- Deprecated features
- Version support matrix
- Release notes by version

**Best For**:
- Understanding API versions
- Migrating from older versions
- Planning upgrades
- Understanding feature timeline

**Example Usage**:
```
Q: What broke between v2.0 and v3.0?
A: See "Breaking Changes" section in API-CHANGELOG.md
```

---

## Feature Matrix

### By Endpoint Category

| Category | Count | Docs | Examples |
|----------|-------|------|----------|
| Authentication | 4 | API-REFERENCE | INTEGRATION-GUIDE |
| Projects | 7 | API-REFERENCE | INTEGRATION-GUIDE |
| Entities | 7 | API-REFERENCE | INTEGRATION-GUIDE |
| Relationships | 5 | API-REFERENCE | API-REFERENCE |
| Search | 3 | API-REFERENCE | INTEGRATION-GUIDE |
| Export | 5 | API-REFERENCE | INTEGRATION-GUIDE |
| Webhooks | 8 | WEBHOOK-DOCUMENTATION | WEBHOOK-DOCUMENTATION |
| WebSocket | 5 | API-REFERENCE | INTEGRATION-GUIDE |
| Analytics | 12 | API-REFERENCE | - |
| Graph | 20 | API-REFERENCE | - |
| Import | 5 | API-REFERENCE | INTEGRATION-GUIDE |
| ML/Suggestions | 12 | API-REFERENCE | - |
| Cache | 8 | API-REFERENCE | - |
| Data Quality | 10 | API-REFERENCE | - |
| Deduplication | 12 | API-REFERENCE | WEBHOOK-DOCUMENTATION |
| Other | 354+ | API-REFERENCE | - |
| **TOTAL** | **404+** | | |

---

## Reading Paths

### Path 1: Complete Beginner

1. Start: API-REFERENCE-COMPREHENSIVE.md (#Overview)
2. Quickstart: API-REFERENCE-COMPREHENSIVE.md (#Getting-Started)
3. Learn: INTEGRATION-GUIDE.md (#Quick-Start)
4. Build: INTEGRATION-GUIDE.md (#Code-Examples)
5. Fix: API-TROUBLESHOOTING.md (as needed)

**Time**: 2-3 hours to be productive

---

### Path 2: Experienced Developer (Integrating)

1. Start: INTEGRATION-GUIDE.md (#Quick-Start)
2. Reference: API-REFERENCE-COMPREHENSIVE.md (lookup endpoints)
3. Advanced: WEBHOOK-DOCUMENTATION.md (if using webhooks)
4. Problems: API-TROUBLESHOOTING.md (as needed)

**Time**: 30 minutes to 1 hour

---

### Path 3: DevOps/Operations

1. Start: DEPLOYMENT-CHECKLIST.md
2. Learn: DATABASE-OPTIMIZATION.md & CONNECTION-POOL-TUNING.md
3. Reference: API-REFERENCE-COMPREHENSIVE.md (#Health-Check)
4. Monitor: API-TROUBLESHOOTING.md (#Performance-Issues)

**Time**: 1-2 hours

---

### Path 4: Migrating from v2.0

1. Start: API-CHANGELOG.md (#Migrating-from-Version-200)
2. Reference: API-REFERENCE-COMPREHENSIVE.md (new endpoints)
3. Fix: API-TROUBLESHOOTING.md (compatibility issues)

**Time**: 1-2 hours

---

## Related Documentation

### Architecture & Design

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System design
- [ARCHITECTURE-INTEGRATION.md](./ARCHITECTURE-INTEGRATION.md) - Integration patterns

### Deployment & Operations

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [DEPLOYMENT-CHECKLIST.md](./DEPLOYMENT-CHECKLIST.md) - Pre-deployment
- [DEPLOYMENT-RUNBOOK.md](./DEPLOYMENT-RUNBOOK.md) - Step-by-step
- [DATABASE-OPTIMIZATION.md](./DATABASE-OPTIMIZATION.md) - DB tuning
- [CONNECTION-POOL-TUNING.md](./CONNECTION-POOL-TUNING.md) - Connections

### Implementation Details

- [PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md](./PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md)
- [GZIP_COMPRESSION_IMPLEMENTATION.md](./GZIP_COMPRESSION_IMPLEMENTATION.md)
- [WEBSOCKET-PRODUCTION-GUIDE.md](./WEBSOCKET-PRODUCTION-GUIDE.md)

### Advanced Features

- [ADVANCED_SEARCH_IMPLEMENTATION.md](./ADVANCED_SEARCH_IMPLEMENTATION.md)
- [FRONTEND-INTEGRATION.md](./FRONTEND-INTEGRATION.md)

---

## Document Map

```
docs/
├── API-DOCUMENTATION-INDEX.md (this file)
├── API-REFERENCE-COMPREHENSIVE.md ← START HERE
├── INTEGRATION-GUIDE.md
├── WEBHOOK-DOCUMENTATION.md
├── API-TROUBLESHOOTING.md
├── API-CHANGELOG.md
├── DEPLOYMENT-CHECKLIST.md
├── DATABASE-OPTIMIZATION.md
├── CONNECTION-POOL-TUNING.md
└── [other documentation files...]
```

---

## Quick Links

### Endpoints by Feature

- **Authentication**: `/auth/login`, `/auth/refresh`, `/auth/validate`, `/auth/me`
- **Projects**: `/projects`, `/projects/{id}`, `/projects/{id}/entities`
- **Search**: `/projects/{id}/search/advanced`, `/projects/{id}/search/autocomplete`
- **Export**: `/projects/{id}/export/json`, `/export/csv`, `/export/graphml`
- **WebSocket**: `/projects/{id}/ws`
- **Webhooks**: `/projects/{id}/webhooks`
- **Analytics**: `/projects/{id}/analytics/*`
- **Graph**: `/path/{e1}/{e2}`, `/centrality/{id}`, `/clusters`
- **ML**: `/entities/{id}/suggestions`, `/duplicates`, `/merge`
- **Status**: `/health`, `/api/info`

---

## API at a Glance

| Metric | Value |
|--------|-------|
| Total Endpoints | 404+ |
| Routers | 54 |
| Authentication | JWT tokens |
| Rate Limit | 100 req/min |
| Response Compression | GZIP (60-70% reduction) |
| Cache Hit Rate | 60%+ |
| Query Latency (p99) | <100ms |
| Supported Formats | JSON, CSV, GraphML, PDF, Markdown |
| Real-time Support | WebSocket, Webhooks |
| Concurrent Connections | 1000+ |
| Uptime Target | 99.9% |

---

## Support

### Documentation Issues

If you find missing, unclear, or incorrect documentation:
1. Check if it's covered in another document
2. Review API-TROUBLESHOOTING.md
3. Contact support@basset-hound.com

### API Issues

If you encounter API errors:
1. Check API-TROUBLESHOOTING.md
2. Review error code in API-REFERENCE-COMPREHENSIVE.md
3. Enable debug logging (DEBUG=true)
4. Contact support with error details and logs

---

## Feedback

Help us improve documentation by:
- Reporting unclear sections
- Suggesting examples
- Providing use case documentation
- Contributing code snippets

---

**Last Updated**: 2026-05-19  
**Version**: 3.0.0  
**Status**: Production Ready

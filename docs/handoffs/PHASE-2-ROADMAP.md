# Phase 2: Frontend Optimization Roadmap
## Weeks 2-4 (Post-Production Deployment)

**Date**: 2026-05-19  
**Duration**: 3 weeks  
**Target**: -700ms additional latency reduction  
**Start**: Week of 2026-05-27 (Week 2 post-deployment)  
**Expected Completion**: Week of 2026-06-16 (Week 4)

---

## Executive Summary

Phase 2 focuses on frontend performance optimization, building on Phase 1's quick wins (-520ms). By optimizing DOM operations, moving expensive algorithms to the backend, implementing caching, and lazy loading, we expect an additional -700ms latency reduction (P99: 7140ms → 6440ms).

**Key Focus**:
- DOM Reflow Optimization (-150ms)
- Transitive Relationship Optimization (-400ms backend API)
- Frontend Caching Layer (-100ms)
- Additional Optimizations (-50ms)

---

## Success Criteria

### Primary Metrics
| Metric | Current (Phase 1) | Target (Phase 2) | Improvement |
|--------|---|---|---|
| **P99 Latency** | 7140ms | 6440ms | -700ms |
| **P95 Latency** | 5200ms | 4700ms | -500ms |
| **P50 Latency** | 2800ms | 2400ms | -400ms |
| **First Contentful Paint** | 2.2s | 1.8s | -400ms |
| **Time to Interactive** | 3.5s | 2.8s | -700ms |
| **Largest Contentful Paint** | 2.8s | 2.2s | -600ms |

### Secondary Metrics
| Metric | Target |
|--------|--------|
| **Bundle Size** | Maintain <300KB gzip |
| **Lighthouse Score** | 92+ (maintain) |
| **Cache Hit Rate** | >65% |
| **Database Queries/sec** | <200 (maintain) |

---

## 1. DOM Reflow Optimization (-150ms)

### 1.1 DocumentFragment Batching

**Problem**: Current code updates DOM one node at a time, triggering reflows for each update.

**Solution**: Use DocumentFragment to batch DOM operations.

**Files to Modify**:
- `/home/devel/basset-hound/static/js/graph-renderer.js`
- `/home/devel/basset-hound/static/js/relationship-manager.js`
- `/home/devel/basset-hound/static/js/entity-list.js`

**Implementation**:
```javascript
// BEFORE (triggers 100 reflows)
entities.forEach(entity => {
  const div = document.createElement('div');
  div.innerHTML = entity.name;
  container.appendChild(div);  // Reflow!
});

// AFTER (single reflow)
const fragment = document.createDocumentFragment();
entities.forEach(entity => {
  const div = document.createElement('div');
  div.innerHTML = entity.name;
  fragment.appendChild(div);  // No reflow
});
container.appendChild(fragment);  // Single reflow
```

**Expected Improvement**: -50ms

**Effort**: 4 hours  
**Priority**: P0 (highest)

### 1.2 Lazy Load Below-Fold Content

**Problem**: Dashboard loads all relationship cards immediately, even if not visible.

**Solution**: Implement Intersection Observer for lazy loading.

**Files to Modify**:
- `/home/devel/basset-hound/static/js/dashboard.js`
- `/home/devel/basset-hound/static/js/relationship-card.js`

**Implementation**:
```javascript
// Create intersection observer for lazy loading
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      loadContent(entry.target);
      observer.unobserve(entry.target);
    }
  });
}, { rootMargin: '100px' });  // Load 100px before visible

// Observe all cards
document.querySelectorAll('.lazy-card').forEach(card => {
  observer.observe(card);
});
```

**Expected Improvement**: -60ms

**Effort**: 6 hours  
**Priority**: P0 (highest)

### 1.3 Virtual Scrolling for Large Lists

**Problem**: Rendering 10,000+ entities in a single list causes lag.

**Solution**: Implement virtual scrolling (only render visible rows).

**Files to Modify**:
- `/home/devel/basset-hound/static/js/entity-list.js`
- `/home/devel/basset-hound/static/js/search-results.js`

**Library**: Use `infinite-scroll` library or custom implementation

**Implementation**:
```javascript
// Virtual scrolling example
class VirtualList {
  constructor(container, items, itemHeight) {
    this.container = container;
    this.items = items;
    this.itemHeight = itemHeight;
    this.visibleRange = this.calculateVisibleRange();
    this.render();
    this.container.addEventListener('scroll', () => this.onScroll());
  }
  
  calculateVisibleRange() {
    const scrollTop = this.container.scrollTop;
    const visibleHeight = this.container.clientHeight;
    const startIndex = Math.floor(scrollTop / this.itemHeight);
    const endIndex = startIndex + Math.ceil(visibleHeight / this.itemHeight);
    return [startIndex, endIndex];
  }
  
  render() {
    const [start, end] = this.visibleRange;
    const fragment = document.createDocumentFragment();
    
    for (let i = start; i < end && i < this.items.length; i++) {
      const row = this.createRow(this.items[i], i);
      fragment.appendChild(row);
    }
    
    this.container.innerHTML = '';
    this.container.appendChild(fragment);
  }
  
  onScroll() {
    this.visibleRange = this.calculateVisibleRange();
    this.render();
  }
}
```

**Expected Improvement**: -40ms

**Effort**: 8 hours  
**Priority**: P1 (high)

### 1.4 CSS Containment

**Problem**: CSS recalculation cascades across entire DOM.

**Solution**: Add `contain: layout style paint` to key components.

**Files to Modify**:
- `/home/devel/basset-hound/static/css/dashboard.css`
- `/home/devel/basset-hound/static/css/graph.css`
- `/home/devel/basset-hound/static/css/cards.css`

**Implementation**:
```css
/* graph-renderer.css */
.graph-container {
  contain: layout style paint;
  /* Tells browser this container is isolated */
}

.entity-card {
  contain: content;
  /* Even stricter: no layout effects outside */
}

.relationship-item {
  contain: paint;
  /* Only visual effects are contained */
}
```

**Expected Improvement**: -20ms

**Effort**: 2 hours  
**Priority**: P1 (high)

---

## 2. Transitive Relationship Optimization (-400ms)

### 2.1 Problem Analysis

**Current Approach**: Frontend loads all entities, then computes transitive closure (O(N²) algorithm).
- 10,000 entities = 100M comparisons
- Takes 4-6 seconds
- Blocking the main thread

**Solution**: Move to backend API endpoint.

### 2.2 New Backend Endpoint

**File**: `/home/devel/basset-hound/api/routers/relationships.py`

**Endpoint**: `GET /api/v1/relationships/transitive`

```python
@router.get("/api/v1/relationships/transitive")
async def get_transitive_relationships(
    entity_id: str,
    max_depth: int = 3,
    project_id: str = Query(...),
    cache_ttl: int = 300  # 5 minute cache
):
    """
    Get all entities reachable from a given entity through relationships.
    
    Params:
        entity_id: Starting entity
        max_depth: Maximum relationship depth (default 3)
        project_id: Project to search within
        cache_ttl: Cache result for N seconds
    
    Returns:
        {
            "source": "entity_id",
            "depth": 3,
            "transitive_entities": [...],
            "paths": [
                {"source": "A", "target": "C", "path": ["A->B", "B->C"]}
            ],
            "cached": false,
            "execution_time_ms": 125
        }
    """
    
    # Check cache first
    cache_key = f"transitive:{project_id}:{entity_id}:{max_depth}"
    cached = await cache_service.get(cache_key)
    if cached:
        return {"...": "...", "cached": True}
    
    # Cypher query (backend handles O(N²) efficiently)
    start_time = time.time()
    
    query = """
    MATCH (start:Entity {id: $entity_id})
    CALL apoc.path.expandConfig(start, {
        relationshipFilter: "RELATES_TO",
        maxLevel: $max_depth,
        uniqueness: "NODE_GLOBAL"
    })
    YIELD path, node
    WITH DISTINCT node
    RETURN COLLECT(node) as entities
    """
    
    result = await neo4j_service.query(query, {
        "entity_id": entity_id,
        "max_depth": max_depth
    })
    
    execution_time = (time.time() - start_time) * 1000
    
    # Cache the result
    await cache_service.set(cache_key, result, ttl=cache_ttl)
    
    return {
        "source": entity_id,
        "depth": max_depth,
        "transitive_entities": result,
        "cached": False,
        "execution_time_ms": execution_time
    }
```

**Expected Backend Response Time**: 100-200ms

**Effort**: 4 hours  
**Priority**: P0 (highest)

### 2.3 Frontend Integration

**File**: `/home/devel/basset-hound/static/js/relationship-manager.js`

```javascript
// OLD: Compute in frontend (4-6 seconds)
function computeTransitiveRelationships(startEntity, allEntities) {
  const visited = new Set();
  const queue = [startEntity];
  
  while (queue.length > 0) {
    const current = queue.shift();
    if (visited.has(current.id)) continue;
    visited.add(current.id);
    
    // Find all entities connected to current
    const related = allEntities.filter(e => isConnected(current, e));
    queue.push(...related);
  }
  
  return Array.from(visited);
}

// NEW: Call backend API (100-200ms)
async function getTransitiveRelationships(entityId, maxDepth = 3) {
  const response = await fetch(
    `/api/v1/relationships/transitive?entity_id=${entityId}&max_depth=${maxDepth}`,
    { method: 'GET' }
  );
  
  const data = await response.json();
  console.log(`Backend computed in ${data.execution_time_ms}ms (cached: ${data.cached})`);
  
  return data.transitive_entities;
}

// Usage
const transitive = await getTransitiveRelationships(entityId);
displayRelationshipGraph(transitive);
```

**Expected Improvement**: -400ms (4-6 seconds → 100-200ms)

**Effort**: 2 hours  
**Priority**: P0 (highest)

### 2.4 Cache Invalidation Strategy

**Cache Key**: `transitive:{project_id}:{entity_id}:{max_depth}`

**Invalidation Triggers**:
1. When entity is updated → Invalidate all entries with that entity_id
2. When relationship is added/deleted → Invalidate related entities
3. TTL expiry → 5 minutes default

**Implementation**:
```python
# In entity_service.py
async def update_entity(entity_id, updates):
    # Update entity
    result = await neo4j_service.update(entity_id, updates)
    
    # Invalidate transitive relationship cache
    await cache_service.delete_pattern(f"transitive:*:{entity_id}:*")
    
    return result
```

**Effort**: 2 hours  
**Priority**: P0 (highest)

---

## 3. Frontend Caching Layer (-100ms)

### 3.1 SessionStorage Cache

**Problem**: Same entities requested repeatedly within a session.

**Solution**: Implement sessionStorage cache with 5-30 minute TTL.

**File**: `/home/devel/basset-hound/static/js/cache-manager.js`

**Implementation**:
```javascript
class FrontendCacheManager {
  constructor() {
    this.cache = {};
    this.ttls = {};
    this.initFromSessionStorage();
  }
  
  initFromSessionStorage() {
    const stored = sessionStorage.getItem('basset_cache');
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        this.cache = parsed.data;
        this.ttls = parsed.ttls;
        this.cleanExpired();
      } catch (e) {
        console.error('Failed to load cache from storage', e);
      }
    }
  }
  
  set(key, value, ttl_seconds = 300) {
    this.cache[key] = value;
    this.ttls[key] = Date.now() + (ttl_seconds * 1000);
    this.saveToSessionStorage();
  }
  
  get(key) {
    if (!this.cache[key]) return null;
    
    // Check TTL
    if (this.ttls[key] && Date.now() > this.ttls[key]) {
      delete this.cache[key];
      delete this.ttls[key];
      this.saveToSessionStorage();
      return null;
    }
    
    return this.cache[key];
  }
  
  cleanExpired() {
    const now = Date.now();
    Object.keys(this.ttls).forEach(key => {
      if (now > this.ttls[key]) {
        delete this.cache[key];
        delete this.ttls[key];
      }
    });
  }
  
  saveToSessionStorage() {
    sessionStorage.setItem('basset_cache', JSON.stringify({
      data: this.cache,
      ttls: this.ttls
    }));
  }
  
  invalidate(pattern) {
    // Invalidate by pattern (e.g., "entity:123:*")
    const regex = new RegExp(pattern);
    Object.keys(this.cache).forEach(key => {
      if (regex.test(key)) {
        delete this.cache[key];
        delete this.ttls[key];
      }
    });
    this.saveToSessionStorage();
  }
}

// Global instance
const cacheManager = new FrontendCacheManager();

// Usage
async function getEntity(entityId) {
  const cached = cacheManager.get(`entity:${entityId}`);
  if (cached) return cached;
  
  const response = await fetch(`/api/v1/entities/${entityId}`);
  const data = await response.json();
  
  cacheManager.set(`entity:${entityId}`, data, 600);  // 10 min TTL
  return data;
}
```

**Cache Strategy**:
| Data Type | TTL | Size Limit |
|-----------|-----|-----------|
| Entity profiles | 10 min | 1MB |
| Search results | 5 min | 500KB |
| Relationship data | 5 min | 500KB |
| User preferences | Session | 100KB |
| Autocomplete | Session | 500KB |

**Expected Improvement**: -50ms

**Effort**: 6 hours  
**Priority**: P1 (high)

### 3.2 Cache Invalidation on Changes

**File**: `/home/devel/basset-hound/static/js/entity-manager.js`

```javascript
// After creating/updating/deleting entity
async function updateEntity(entityId, changes) {
  const response = await fetch(`/api/v1/entities/${entityId}`, {
    method: 'PATCH',
    body: JSON.stringify(changes)
  });
  
  const data = await response.json();
  
  // Invalidate cache
  cacheManager.invalidate(`entity:${entityId}:*`);
  cacheManager.invalidate(`relationships:*:${entityId}:*`);
  cacheManager.invalidate(`search:*`);  // Invalidate all searches
  
  return data;
}
```

**Effort**: 2 hours  
**Priority**: P1 (high)

---

## 4. Additional Optimizations (-50ms)

### 4.1 Lazy Load Marked.js

**Problem**: Markdown rendering library (60KB) loads even when not needed.

**Solution**: Load marked.js only when markdown content is first encountered.

**File**: `/home/devel/basset-hound/static/js/markdown-renderer.js`

```javascript
let markedLoaded = false;

async function renderMarkdown(content) {
  // Lazy load marked.js on first use
  if (!markedLoaded) {
    await loadScript('/static/lib/marked.min.js');
    markedLoaded = true;
  }
  
  return window.marked(content);
}
```

**Expected Improvement**: -20ms (per first markdown render)

**Effort**: 1 hour  
**Priority**: P2 (medium)

### 4.2 Code Splitting by Dashboard Module

**Problem**: All dashboard modules load in single bundle.

**Solution**: Use Webpack code splitting for route-based bundles.

**File**: `webpack.config.js`

```javascript
module.exports = {
  mode: 'production',
  entry: './static/js/main.js',
  output: {
    path: __dirname + '/static/dist',
    filename: '[name].[contenthash].js',
    chunkFilename: '[name].[contenthash].js'
  },
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        // Vendor code
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
          reuseExistingChunk: true
        },
        // Common code
        common: {
          minChunks: 2,
          priority: 5,
          reuseExistingChunk: true
        }
      }
    }
  }
};
```

**Route-based Code Splitting**:
```javascript
// Use dynamic imports for routes
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Settings = React.lazy(() => import('./pages/Settings'));
const Admin = React.lazy(() => import('./pages/Admin'));

export const routes = [
  { path: '/dashboard', component: Dashboard },
  { path: '/settings', component: Settings },
  { path: '/admin', component: Admin }
];
```

**Expected Improvement**: -15ms

**Effort**: 4 hours  
**Priority**: P2 (medium)

### 4.3 Service Worker for Offline Support

**Problem**: No offline support for previously loaded pages.

**Solution**: Register service worker for offline caching.

**File**: `/home/devel/basset-hound/static/js/service-worker.js`

```javascript
const CACHE_NAME = 'basset-hound-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/static/css/main.css',
  '/static/js/main.js',
  '/api/v1/projects',  // Example: cache some API responses
];

// Install event - pre-cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).then(response => {
        // Cache successful responses
        if (response.ok && event.request.method === 'GET') {
          const cache = caches.open(CACHE_NAME);
          cache.then(c => c.put(event.request, response.clone()));
        }
        return response;
      }).catch(() => {
        // Offline fallback
        return caches.match('/offline.html');
      });
    })
  );
});
```

**Registration** (in main.js):
```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/js/service-worker.js')
    .then(reg => console.log('Service Worker registered'))
    .catch(err => console.error('Service Worker registration failed'));
}
```

**Expected Improvement**: -15ms (improves repeat visits)

**Effort**: 3 hours  
**Priority**: P2 (medium)

---

## Project Timeline

### Week 2 (May 27 - Jun 2)

**Sprint Goals**: DOM optimization + transitive relationship backend API

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | DocumentFragment implementation | 4h | Frontend |
| Tue | Intersection Observer lazy loading | 6h | Frontend |
| Wed | Transitive relationship API endpoint | 4h | Backend |
| Thu | Frontend integration + testing | 2h | Frontend |
| Fri | Performance testing + optimization | 2h | DevOps |

**Expected Gains**: -550ms

### Week 3 (Jun 3 - Jun 9)

**Sprint Goals**: Caching layer + virtual scrolling

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | SessionStorage cache manager | 6h | Frontend |
| Tue | Cache invalidation strategies | 2h | Frontend |
| Wed | Virtual scrolling implementation | 8h | Frontend |
| Thu | CSS containment optimization | 2h | Frontend |
| Fri | Performance testing + bug fixes | 4h | QA |

**Expected Gains**: -150ms (cumulative: -700ms)

### Week 4 (Jun 10 - Jun 16)

**Sprint Goals**: Additional optimizations + comprehensive testing

| Day | Task | Effort | Owner |
|-----|------|--------|-------|
| Mon | Lazy load marked.js | 1h | Frontend |
| Tue | Code splitting configuration | 4h | Frontend |
| Wed | Service Worker implementation | 3h | Frontend |
| Thu | Comprehensive testing | 4h | QA |
| Fri | Performance validation + docs | 2h | DevOps |

**Expected Gains**: -50ms (cumulative: -700ms)

---

## Dependencies & Prerequisites

### Required
- [ ] Phase 1 complete and deployed
- [ ] Performance baseline from Phase 1
- [ ] Backend Neo4j APOC library installed (for path queries)
- [ ] Redis cache operational
- [ ] Development environment set up

### Infrastructure
- [ ] Webpack configured for code splitting
- [ ] Service Worker capable browser support (>95%)
- [ ] Session storage available in all target browsers
- [ ] Enough disk space for additional caches

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| **Transitive query slow** | Medium | High | Use APOC library + caching, fallback to frontend |
| **Cache coherency issues** | Low | High | Implement explicit invalidation + TTL |
| **Virtual scrolling bugs** | Medium | Medium | Extensive testing + gradual rollout |
| **Service Worker issues** | Low | Medium | Feature flag + monitoring |
| **DOM optimization breaks layout** | Medium | High | Comprehensive testing + gradual rollout |

---

## Success Metrics & Validation

### Performance Benchmarks
```bash
# Run before/after latency test
npm run benchmark

# Expected output:
# Before: P99 = 7140ms, P95 = 5200ms
# After:  P99 = 6440ms, P95 = 4700ms
# Improvement: -700ms P99, -500ms P95
```

### Lighthouse Score Maintenance
```bash
npm run lighthouse

# Expected score: 92+
# Ensure bundle size < 300KB gzip
# Ensure FCP < 2.0s
```

### Database Query Metrics
```bash
# Verify backend optimization
curl http://localhost:8080/api/v1/metrics

# Expected:
# - Query latency p99: <100ms
# - Cache hit rate: >65%
# - Transitive API response: <200ms
```

---

## Deliverables

### Code Changes
- [ ] DocumentFragment optimization in graph-renderer.js
- [ ] Intersection Observer lazy loading implementation
- [ ] Virtual scrolling in entity-list.js
- [ ] CSS containment rules
- [ ] Transitive relationship API endpoint
- [ ] Frontend caching layer
- [ ] Code splitting configuration
- [ ] Service Worker implementation

### Documentation
- [ ] Phase 2 completion summary
- [ ] Performance improvements breakdown
- [ ] New API endpoints documentation
- [ ] Caching strategy guide
- [ ] Frontend optimization best practices

### Testing
- [ ] Unit tests for all new components
- [ ] Integration tests for caching layer
- [ ] Performance regression tests
- [ ] E2E tests for lazy loading
- [ ] Load testing (validate P99 < 6440ms)

---

## Post-Phase 2 Review

**Evaluation Criteria**:
1. ✅ P99 latency < 6440ms (target -700ms from Phase 1)
2. ✅ All smoke tests passing
3. ✅ Zero performance regressions
4. ✅ Cache hit rate > 65%
5. ✅ Lighthouse score 92+
6. ✅ Documentation complete

**Next Phase Gates**:
- [ ] Phase 2 metrics validated by QA
- [ ] Performance improvements peer reviewed
- [ ] All tests passing (95%+ coverage)
- [ ] Go/No-Go decision for Phase 3

---

## Resources & References

### Internal Docs
- PHASE-1-ROADMAP.md (Previous phase results)
- PHASE-8-COMPLETION-SUMMARY.md (Current features)
- PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md (Techniques)

### External Resources
- MDN: Web Performance
- Webpack Code Splitting Guide
- React Lazy Loading
- Neo4j APOC Documentation
- Service Worker API

---

**Owner**: Frontend Team  
**Last Updated**: 2026-05-19  
**Status**: Ready for Planning & Estimation  
**Next Review**: Start of Week 2 (2026-05-27)

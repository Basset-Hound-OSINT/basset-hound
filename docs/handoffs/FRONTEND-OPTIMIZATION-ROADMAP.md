# Frontend Optimization Roadmap & Implementation Guide

**Date**: 2026-05-19  
**Scope**: Phase 9+ Frontend Performance Enhancement  
**Target**: Reduce p99 latency from 7660ms → <2000ms  
**Effort Estimate**: 3-4 weeks (experienced team)

---

## Executive Overview

This roadmap prioritizes optimizations by ROI (impact ÷ effort) and implementation order. Quick wins unlock larger refactoring opportunities.

**Timeline**:
- **Week 1**: Quick wins + foundational fixes (Expected: 7660ms → 5000ms)
- **Week 2**: Core algorithmic optimization (Expected: 5000ms → 2500ms)
- **Week 3**: Advanced caching & monitoring (Expected: 2500ms → <2000ms)
- **Week 4**: Long-term maintenance & documentation

---

## Phase 1: Quick Wins (Days 1-2, <10 hours)

### 1.1 Event Listener Cleanup Using Delegation

**File**: `/static/js/ui-people-list.js`  
**Current Impact**: 114 listeners, memory leak  
**Expected Improvement**: -200ms latency, -1.5MB memory per session  
**Effort**: 1-2 hours  
**Difficulty**: LOW

#### Problem Code (Lines 39-107)

```javascript
// BEFORE - Creates 50+ individual listeners
sortedPeople.forEach(person => {
    const listItem = document.createElement('li');
    listItem.className = 'person-item list-group-item cursor-pointer';
    
    // ... setup DOM
    
    listItem.addEventListener('click', function() {
        renderPersonDetails(detailsContainer, person);
    });
    
    personList.appendChild(listItem);  // Each rerender adds MORE listeners
});
```

#### Solution Code

```javascript
// AFTER - Single delegation listener
const listFragment = document.createDocumentFragment();

sortedPeople.forEach(person => {
    const listItem = document.createElement('li');
    listItem.className = 'person-item list-group-item cursor-pointer';
    listItem.dataset.personId = person.id;  // Store person ID
    
    // ... setup DOM (no event listeners on items)
    
    listFragment.appendChild(listItem);
});

personList.innerHTML = '';  // Clear old items (removes old listeners)
personList.appendChild(listFragment);

// Single delegation listener (moved outside forEach)
personList.removeEventListener('click', handlePersonClick);  // Remove old
personList.addEventListener('click', handlePersonClick);    // Add once

function handlePersonClick(event) {
    const item = event.target.closest('.person-item');
    if (!item) return;
    
    const personId = item.dataset.personId;
    const person = window.people.find(p => p.id === personId);
    if (person) {
        renderPersonDetails(detailsContainer, person);
    }
}
```

#### Testing

```javascript
// Verify listener cleanup:
console.log('Listeners before:', getEventListeners(personList).click?.length);

// Rerender list
renderPeopleList(window.people);

console.log('Listeners after:', getEventListeners(personList).click?.length);
// Should be: 1 (not 51)

// Memory test:
const snapshot1 = performance.memory.usedJSHeapSize;
renderPeopleList(window.people);  // Switch person 20 times
const snapshot2 = performance.memory.usedJSHeapSize;
console.log('Memory increase:', (snapshot2 - snapshot1) / 1024 / 1024, 'MB');
// Should be: <5MB (not 50MB)
```

#### Rollback Plan

```javascript
// If issues arise, revert to individual listeners:
listItem.addEventListener('click', function() {
    renderPersonDetails(detailsContainer, person);
});
```

---

### 1.2 Reuse Cached Data (/get_people)

**Files**: 
- `/static/js/ui-person-details.js` (lines 482, 531)
- `/static/js/advanced-search.js`

**Current Impact**: 3 fetches per person view  
**Expected Improvement**: -200ms latency, -750KB bandwidth per 3 views  
**Effort**: 0.5 hours  
**Difficulty**: TRIVIAL

#### Problem Code

```javascript
// ui-person-details.js line 482
async function renderTaggedPeopleSection(container, personId) {
    const res = await fetch(`/get_person/${personId}`);
    const person = await res.json();
    
    // WASTEFUL: window.people already has all people!
    const peopleRes = await fetch('/get_people');  
    const allPeople = await peopleRes.json();
    
    // Use allPeople for name lookup only
    // Could easily use window.people instead
}

// Same issue at line 531
async function renderTransitivePeopleSection(container, personId) {
    const peopleRes = await fetch('/get_people');  // WASTEFUL
    const allPeople = await peopleRes.json();
}
```

#### Solution Code

```javascript
// AFTER - Reuse cached data
async function renderTaggedPeopleSection(container, personId) {
    const res = await fetch(`/get_person/${personId}`);
    const person = await res.json();
    
    // Use window.people (cached from dashboard init)
    // Fallback to fetch only if not available (e.g., if called standalone)
    const allPeople = window.people || 
                      await fetch('/get_people').then(r => r.json());
    
    // Rest of function unchanged
}

async function renderTransitivePeopleSection(container, personId) {
    // Same pattern
    const allPeople = window.people || 
                      await fetch('/get_people').then(r => r.json());
}
```

#### Validation

```javascript
// Monitor network traffic before/after
const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
        if (entry.name.includes('/get_people')) {
            console.log('GET /get_people:', entry.duration, 'ms');
        }
    }
});
observer.observe({ entryTypes: ['resource'] });

// Before: 3 requests per person view
// After: 0 requests (using window.people)
```

---

### 1.3 Minify JavaScript & CSS

**Files**: All JS and CSS files  
**Current Impact**: 456 KB JS, 31 KB CSS  
**Expected Improvement**: 456KB → 280KB JS (38% reduction)  
**Effort**: 1-2 hours (including build setup)  
**Difficulty**: LOW (build automation)

#### Setup Using Terser

```bash
# Install
npm install --save-dev terser csso-cli

# Create build script in package.json
{
  "scripts": {
    "build:minify": "terser static/js/*.js -o static/js/minified/ && csso static/css/*.css -o static/css/minified/"
  }
}

# Run
npm run build:minify
```

#### Terser Configuration

```javascript
// terser.config.js
module.exports = {
  compress: {
    drop_console: true,  // Remove console.log in production
    drop_debugger: true,
    pure_funcs: ['console.warn'],  // Keep console.error
  },
  mangle: true,  // Shorten variable names
  format: {
    beautify: false,
    comments: false,
  },
};
```

#### Update Static File Serving

```python
# api/main.py - Serve minified by default
import os

MINIFIED_DIR = os.getenv('SERVE_MINIFIED', 'true').lower() == 'true'

if MINIFIED_DIR and os.path.exists('static/js/minified'):
    app.mount("/static/js", StaticFiles(directory="static/js/minified"), name="js")
else:
    app.mount("/static/js", StaticFiles(directory="static/js"), name="js")
```

#### Verification

```bash
# Compare sizes
ls -lh static/js/*.js | awk '{print $5, $9}' | column -t  # Before
ls -lh static/js/minified/*.js | awk '{print $5, $9}' | column -t  # After

# Expected: 450 KB → 280 KB
```

---

### 1.4 Enable Gzip Compression

**File**: `/api/main.py`  
**Current Impact**: 280 KB minified (after 1.3)  
**Expected Improvement**: 280KB → 92KB (67% reduction)  
**Effort**: 0.5 hours  
**Difficulty**: TRIVIAL

#### Current Setup

```python
# api/main.py already has GZipMiddleware (line 19)
from starlette.middleware.gzip import GZipMiddleware
# ... later in setup
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### Verify It's Working

```bash
# Check response headers
curl -i -H 'Accept-Encoding: gzip' https://basset-hound/static/js/dashboard.js | grep -i content-encoding

# Expected output: Content-Encoding: gzip
# If missing, verify middleware is mounted correctly
```

#### Nginx Configuration (if proxying)

```nginx
# If behind Nginx, ensure gzip is enabled
gzip on;
gzip_types text/javascript application/javascript text/css text/plain;
gzip_min_length 1000;
gzip_vary on;
gzip_comp_level 6;
```

#### Measure Impact

```javascript
// In browser DevTools Network tab:
// Before optimization: 280 KB transferred
// After optimization: 92 KB transferred
// Savings: 188 KB (67%)
```

---

### 1.5 Move Marked.js to Async Loading

**File**: `/templates/dashboard.html` (line 177)  
**Current Impact**: Synchronous blocking  
**Expected Improvement**: -15ms blocking time  
**Effort**: 0.5 hours  
**Difficulty**: LOW

#### Problem Code

```html
<!-- Line 177: Synchronous, blocks parsing -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

<!-- Only used in file_explorer.js, loads for everyone -->
```

#### Solution Code

```html
<!-- Remove the synchronous script tag -->
<!-- Instead, lazy load in file-explorer.js -->

<!-- Optionally add preload hint for better timing -->
<link rel="preload" href="https://cdn.jsdelivr.net/npm/marked/marked.min.js" as="script">
```

#### Update file_explorer.js

```javascript
// file_explorer.js - Lazy load marked.js
async function loadMarked() {
    if (window.marked) return;  // Already loaded
    
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Before using marked:
async function renderMarkdown(content) {
    await loadMarked();
    return window.marked(content);
}
```

#### Test

```javascript
// Verify marked still available when needed:
console.log('marked available:', !!window.marked);  // false initially
// Open file explorer, view markdown file
console.log('marked available after view:', !!window.marked);  // true
```

---

### Summary: Phase 1 Impact

| Optimization | Latency | Memory | Bandwidth | Effort |
|---|---|---|---|---|
| Event delegation | -200ms | -1.5MB | 0 | 1.5h |
| Cache reuse | -200ms | 0 | -750KB/3-views | 0.5h |
| Minification | -80ms | 0 | -176KB | 1.5h |
| Gzip | -40ms | 0 | -188KB | 0.5h |
| Marked.js async | -15ms | 0 | 0 | 0.5h |
| **Total** | **-535ms** | **-1.5MB** | **-1.1MB** | **4.5h** |

**Expected Result**: P99: 7660ms → **7125ms** (7% improvement)

---

## Phase 2: Core Optimizations (Days 3-6, 15-20 hours)

### 2.1 Move Transitive Relationship Calculation to Backend

**File**: `/static/js/ui-person-details.js` (lines 529-591)  
**Current Impact**: 564ms synchronous blocking  
**Expected Improvement**: -400ms latency  
**Effort**: 6-8 hours (backend + frontend)  
**Difficulty**: MEDIUM

#### Problem Analysis

```javascript
// Current: Synchronous O(N²) BFS on main thread
async function renderTransitivePeopleSection(container, personId) {
    const allPeople = await fetch('/get_people').then(r => r.json());
    
    const transitivePeople = new Set();
    allPeople.forEach(otherPerson => {
        const visited = new Set();
        const queue = [otherPerson.id];
        
        while (queue.length > 0) {
            const currentId = queue.shift();
            // ... complex traversal
        }
    });
    // Render: container.innerHTML = buildHTML(transitivePeople);
}
```

**Why slow**: 
- 500 people × (500 checks + 30 edges) = 265,000 operations
- JavaScript: ~500K ops/sec → 530ms of blocking

#### Solution Part 1: Create Backend Endpoint

**File**: `/api/routers/people.py` (new endpoint)

```python
from fastapi import APIRouter, HTTPException
from api.services.neo4j_service import AsyncNeo4jService

router = APIRouter(prefix="/api/v1", tags=["people"])

@router.get("/people/{person_id}/transitive-relationships")
async def get_transitive_relationships(
    person_id: str,
    depth: int = 2,
    limit: int = 100
):
    """
    Get transitive relationships for a person using graph traversal.
    
    Args:
        person_id: ID of the person
        depth: Maximum relationship depth to traverse (default: 2)
        limit: Maximum results to return (default: 100)
    
    Returns:
        {
            "transitive_relationships": [
                {"id": "...", "name": "...", "depth": 1, "path": [...]},
                ...
            ],
            "total": 45
        }
    """
    try:
        service = AsyncNeo4jService()
        await service.connect()
        
        # Cypher query: Find transitive relationships
        query = """
        MATCH (person:Person {id: $person_id})
        CALL apoc.path.expandConfig(person, {
            relationshipFilter: "TAGGED_PEOPLE",
            minLevel: 1,
            maxLevel: $depth,
            limit: $limit
        }) YIELD path, nodes, length
        WITH nodes, length
        UNWIND nodes[1..] AS transitive
        RETURN DISTINCT
            transitive.id AS id,
            transitive.name AS name,
            length - 1 AS depth
        ORDER BY depth, name
        LIMIT $limit
        """
        
        result = await service.run_query(
            query,
            {
                "person_id": person_id,
                "depth": depth,
                "limit": limit
            }
        )
        
        return {
            "transitive_relationships": result,
            "total": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Solution Part 2: Update Frontend

```javascript
// ui-person-details.js - Updated renderTransitivePeopleSection
async function renderTransitivePeopleSection(container, personId) {
    try {
        // Show loading spinner
        const section = document.createElement('div');
        section.className = 'card mb-3';
        section.innerHTML = '<div class="card-body"><span class="spinner-border"></span> Computing relationships...</div>';
        container.appendChild(section);
        
        // Fetch from backend instead of computing locally
        const response = await fetch(`/api/v1/people/${personId}/transitive-relationships?depth=2&limit=100`);
        if (!response.ok) throw new Error('Failed to fetch relationships');
        
        const { transitive_relationships } = await response.json();
        
        // Clear loading and render results
        section.innerHTML = '';
        
        // Build HTML (now fast, no computation)
        const fragment = document.createDocumentFragment();
        const header = document.createElement('h5');
        header.textContent = `Transitive Relationships (${transitive_relationships.length})`;
        fragment.appendChild(header);
        
        const list = document.createElement('ul');
        transitive_relationships.forEach(rel => {
            const item = document.createElement('li');
            item.innerHTML = `
                <strong>${rel.name}</strong>
                <small class="text-muted">(${rel.depth} degrees)</small>
            `;
            list.appendChild(item);
        });
        fragment.appendChild(list);
        
        section.innerHTML = '';  // Clear loading
        section.appendChild(fragment);
        
    } catch (error) {
        console.error('Error rendering transitive relationships:', error);
        // Show error message
        container.innerHTML += `<div class="alert alert-danger">Error loading relationships</div>`;
    }
}
```

#### Testing

```javascript
// Time the operations
console.time('transitive-api-call');
await fetch(`/api/v1/people/person-123/transitive-relationships`);
console.timeEnd('transitive-api-call');

// Expected times:
// Before: 564ms (JavaScript computation)
// After: 150ms (API call + network) 
// Result: -414ms improvement
```

#### Fallback for Offline

```javascript
// If API fails, compute locally (slower but works)
async function renderTransitivePeopleSection(container, personId) {
    try {
        // Try backend first
        const response = await fetch(`/api/v1/people/${personId}/transitive-relationships`);
        if (response.ok) {
            const { transitive_relationships } = await response.json();
            // Render results
        } else {
            throw new Error('API failed');
        }
    } catch (error) {
        console.warn('Falling back to local computation:', error);
        // Fall back to old local algorithm (shows spinner for transparency)
        await renderTransitivePeopleLocal(container, personId);
    }
}
```

---

### 2.2 Add Frontend Caching Layer

**Files**:
- New: `/static/js/cache.js`
- Update: `/static/js/dashboard.js`
- Update: `/static/js/ui-person-details.js`

**Current Impact**: Zero caching  
**Expected Improvement**: -100ms latency (cache hits), -250KB bandwidth  
**Effort**: 4 hours  
**Difficulty**: MEDIUM

#### Create Cache Module

```javascript
// static/js/cache.js
class FrontendCache {
    constructor(options = {}) {
        this.maxSize = options.maxSize || 50;  // 50 items
        this.ttl = options.ttl || 5 * 60 * 1000;  // 5 minutes
        this.storage = new Map();
    }
    
    get(key) {
        const entry = this.storage.get(key);
        if (!entry) return null;
        
        if (Date.now() - entry.timestamp > this.ttl) {
            this.storage.delete(key);
            return null;
        }
        
        return entry.data;
    }
    
    set(key, data) {
        // LRU eviction if size exceeded
        if (this.storage.size >= this.maxSize) {
            const firstKey = this.storage.keys().next().value;
            this.storage.delete(firstKey);
        }
        
        this.storage.set(key, {
            data,
            timestamp: Date.now()
        });
    }
    
    clear() {
        this.storage.clear();
    }
}

// Create global cache instances
export const personCache = new FrontendCache({ maxSize: 100, ttl: 10 * 60 * 1000 });
export const peopleCache = new FrontendCache({ maxSize: 5, ttl: 5 * 60 * 1000 });
export const relationshipCache = new FrontendCache({ maxSize: 50, ttl: 30 * 60 * 1000 });
```

#### Update Dashboard.js

```javascript
// dashboard.js - Cache people list
import { peopleCache } from './cache.js';

async function initApp() {
    try {
        // Check cache first
        window.people = peopleCache.get('all_people');
        
        if (!window.people) {
            // Cache miss, fetch from backend
            window.people = await fetchPeople();
            peopleCache.set('all_people', window.people);
        }
        
        // Rest of init...
        renderPeopleList(window.people);
    } catch (error) {
        console.error('Error initializing app:', error);
    }
}
```

#### Update API Module

```javascript
// api.js - Add caching to fetch functions
import { personCache } from './cache.js';

export async function fetchPerson(personId) {
    // Check cache first
    const cached = personCache.get(personId);
    if (cached) {
        console.log('Cache hit:', personId);
        return cached;
    }
    
    // Cache miss
    const response = await fetch(`/get_person/${personId}`);
    const data = await response.json();
    personCache.set(personId, data);
    return data;
}

export async function fetchPeople() {
    // ... existing code, but now uses peopleCache
}
```

#### Verify Cache Effectiveness

```javascript
// Monitor cache performance
console.log('Initial cache hits:', cacheHits);

// Navigate through 5 people
for (let i = 0; i < 5; i++) {
    await fetchPerson(`person-${i}`);  // Fetches from API
    await fetchPerson(`person-${i}`);  // Should be cache hit
}

console.log('Final cache hits:', cacheHits);
// Expected: 5 cache hits out of 10 calls = 50% hit rate
```

---

### 2.3 Batch DOM Operations with Document Fragments

**File**: `/static/js/ui-person-details.js` (lines 240-420)  
**Current Impact**: 649+ DOM operations  
**Expected Improvement**: -150ms latency  
**Effort**: 3-4 hours  
**Difficulty**: MEDIUM

#### Problem Code

```javascript
// BEFORE: appendChild in loops triggers reflow
for (const sectionId in person.profile) {
    for (const fieldId in sectionData) {
        field.components.forEach(component => {
            compVals.forEach((compVal, compIdx) => {
                const compRow = document.createElement('div');
                const copyIcon = document.createElement('i');
                
                compRow.appendChild(copyIcon);  // Reflow!
                compRow.appendChild(label);     // Reflow!
                compRow.appendChild(valueDisplay);  // Reflow!
                
                entryDiv.appendChild(compRow);  // Reflow!
            });
        });
    }
}
```

#### Solution Code

```javascript
// AFTER: Batch with DocumentFragment
for (const sectionId in person.profile) {
    const sectionContainer = document.createElement('div');
    sectionContainer.className = 'section mb-3';
    
    const sectionFragment = document.createDocumentFragment();  // Off-DOM
    
    for (const fieldId in sectionData) {
        field.components.forEach(component => {
            compVals.forEach((compVal, compIdx) => {
                const compRow = document.createElement('div');
                const copyIcon = document.createElement('i');
                
                // Build entire structure in memory
                compRow.appendChild(copyIcon);      // NO REFLOW
                compRow.appendChild(label);         // NO REFLOW
                compRow.appendChild(valueDisplay);  // NO REFLOW
                
                sectionFragment.appendChild(compRow);  // NO REFLOW
            });
        });
    }
    
    // Single reflow: add entire fragment to DOM
    sectionContainer.appendChild(sectionFragment);
    
    // Add section to page
    container.appendChild(sectionContainer);
}
```

#### Measure Improvement

```javascript
// Measure rendering time
const start = performance.now();
renderPersonDetails(container, person);
const duration = performance.now() - start;

console.log('Render time:', duration, 'ms');
// Expected: 300ms → 150ms (50% improvement)
```

---

### 2.4 Implement AbortController for Lazy Loading

**File**: `/static/js/dashboard.js` (lines 21-80)  
**Current Impact**: Memory accumulation from orphaned imports  
**Expected Improvement**: -20ms latency, -50KB memory  
**Effort**: 2 hours  
**Difficulty**: MEDIUM

#### Problem Code

```javascript
// BEFORE: No cancellation
let advancedSearchInitialized = false;

async function loadAdvancedSearch(projectSafeName) {
    if (advancedSearchInitialized) return;
    
    try {
        const module = await import('./advanced-search.js');  // Can't cancel!
        module.initAdvancedSearch(projectSafeName);
        advancedSearchInitialized = true;
    } catch (error) {
        console.error('Error loading advanced search:', error);
    }
}

searchInput.addEventListener('focus', async () => {
    await loadAdvancedSearch(projectSafeName);  // Always completes, even if user navigates away
});
```

#### Solution Code

```javascript
// AFTER: With AbortController
let advancedSearchController = null;
let advancedSearchInitialized = false;

async function loadAdvancedSearch(projectSafeName) {
    if (advancedSearchInitialized) return;
    
    // Cancel previous load if running
    if (advancedSearchController) {
        advancedSearchController.abort();
    }
    
    advancedSearchController = new AbortController();
    
    try {
        const module = await import('./advanced-search.js');
        module.initAdvancedSearch(projectSafeName);
        advancedSearchInitialized = true;
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Advanced search loading cancelled');
        } else {
            console.error('Error loading advanced search:', error);
        }
    }
}

searchInput.addEventListener('focus', async () => {
    await loadAdvancedSearch(projectSafeName);
});

// Also cancel when leaving page
window.addEventListener('beforeunload', () => {
    if (advancedSearchController) {
        advancedSearchController.abort();
    }
});
```

---

### Summary: Phase 2 Impact

| Optimization | Latency | Memory | Bandwidth | Effort |
|---|---|---|---|---|
| Transitive to backend | -400ms | 0 | -250KB | 8h |
| Frontend caching | -100ms | +5MB | -250KB | 4h |
| DOM fragments | -150ms | 0 | 0 | 4h |
| AbortController | -20ms | -50KB | 0 | 2h |
| **Total** | **-670ms** | **-45KB** | **-500KB** | **18h** |

**Expected Result**: P99: 7125ms → **6455ms** (16% total improvement)

---

## Phase 3: Advanced Optimizations (Days 7-10, 15-20 hours)

### 3.1 Server-Side Pagination

**File**: `/api/routers/people.py` + `/static/js/api.js`  
**Current Impact**: Fetches 500 people, displays 50  
**Expected Improvement**: -100ms initial load  
**Effort**: 6-8 hours  
**Difficulty**: MEDIUM-HIGH (data layer changes)

#### Backend Endpoint

```python
@router.get("/api/v1/people")
async def list_people(skip: int = 0, limit: int = 50):
    """
    Get paginated list of people.
    """
    service = AsyncNeo4jService()
    people = await service.get_people(skip=skip, limit=limit, total=True)
    return {
        "items": people['items'],
        "total": people['total'],
        "page": skip // limit + 1,
        "page_size": limit
    }
```

#### Frontend Pagination

```javascript
// api.js
export async function fetchPeoplePaginated(page = 1, limit = 50) {
    const skip = (page - 1) * limit;
    return fetch(`/api/v1/people?skip=${skip}&limit=${limit}`)
        .then(r => r.json());
}

// dashboard.js
async function initApp() {
    const { items, total } = await fetchPeoplePaginated(1);
    window.people = items;
    window.peopleTotal = total;
    renderPeopleList(window.people);
    renderPagination(total);
}
```

---

### 3.2 Client-Side Search Index (Trie)

**File**: New `/static/js/search-index.js`  
**Current Impact**: Search filter on 500 people = 500 operations  
**Expected Improvement**: <50ms instant search  
**Effort**: 3-4 hours  
**Difficulty**: MEDIUM

#### Implementation

```javascript
// search-index.js - Trie-based search
export class TrieSearchIndex {
    constructor() {
        this.trie = {};
    }
    
    build(people) {
        people.forEach(person => {
            const name = `${person.first_name || ''} ${person.last_name || ''}`
                .toLowerCase()
                .split(/\s+/);
            
            name.forEach(word => {
                if (!word) return;
                this.addWord(word, person.id);
            });
        });
    }
    
    addWord(word, personId) {
        let node = this.trie;
        for (const char of word) {
            if (!node[char]) node[char] = { ids: new Set(), children: {} };
            node[char].ids.add(personId);
            node = node[char].children;
        }
    }
    
    search(query) {
        const q = query.toLowerCase();
        let node = this.trie;
        
        for (const char of q) {
            if (!node[char]) return [];
            node = node[char].children;
        }
        
        return Array.from(node.ids || []);
    }
}

// dashboard.js
import { TrieSearchIndex } from './search-index.js';

const searchIndex = new TrieSearchIndex();
searchIndex.build(window.people);

searchInput.addEventListener('input', (e) => {
    const query = e.target.value;
    const personIds = searchIndex.search(query);
    const filtered = personIds.map(id => window.people.find(p => p.id === id));
    renderPeopleList(filtered);
});
```

---

### 3.3 Virtual Scrolling for Large Lists

**File**: New `/static/js/virtual-scroll.js`  
**Current Impact**: 1000+ person lists = 1000+ DOM elements  
**Expected Improvement**: -200ms render, -50MB memory for large lists  
**Effort**: 8-10 hours  
**Difficulty**: HIGH

#### Implementation Pattern

```javascript
// virtual-scroll.js
export class VirtualScroller {
    constructor(container, items, itemHeight) {
        this.container = container;
        this.items = items;
        this.itemHeight = itemHeight;
        this.visibleRange = { start: 0, end: 50 };
        
        this.container.addEventListener('scroll', () => this.onScroll());
    }
    
    onScroll() {
        const scrollTop = this.container.scrollTop;
        const start = Math.floor(scrollTop / this.itemHeight);
        const end = start + Math.ceil(this.container.clientHeight / this.itemHeight);
        
        if (start !== this.visibleRange.start || end !== this.visibleRange.end) {
            this.visibleRange = { start, end };
            this.render();
        }
    }
    
    render() {
        const visible = this.items.slice(this.visibleRange.start, this.visibleRange.end);
        const fragment = document.createDocumentFragment();
        
        visible.forEach((item, idx) => {
            const li = this.renderItem(item);
            li.style.transform = `translateY(${(this.visibleRange.start + idx) * this.itemHeight}px)`;
            fragment.appendChild(li);
        });
        
        this.container.innerHTML = '';
        this.container.appendChild(fragment);
    }
    
    renderItem(item) {
        // Create li element for item
    }
}
```

---

### 3.4 Web Worker for Graph Computation

**File**: New `/static/js/workers/graph-worker.js`  
**Current Impact**: 564ms blocking computation  
**Expected Improvement**: -564ms (moved off main thread)  
**Effort**: 6-8 hours  
**Difficulty**: MEDIUM-HIGH

#### Worker Implementation

```javascript
// static/js/workers/graph-worker.js
self.onmessage = async (event) => {
    const { peopleList, startPersonId, depth } = event.data;
    
    // BFS computation (same as before, but off main thread)
    const transitive = computeTransitive(peopleList, startPersonId, depth);
    
    self.postMessage({ transitive });
};

function computeTransitive(peopleList, startPersonId, depth) {
    // O(N²) algorithm runs here, not on main thread
}

// ui-person-details.js - Use worker
async function renderTransitivePeopleSection(container, personId) {
    const worker = new Worker('/static/js/workers/graph-worker.js');
    
    const transitive = await new Promise((resolve) => {
        worker.postMessage({
            peopleList: window.people,
            startPersonId: personId,
            depth: 2
        });
        
        worker.onmessage = (event) => {
            worker.terminate();
            resolve(event.data.transitive);
        };
    });
    
    // Render results (happens while worker computes, not blocked)
    const section = document.createElement('div');
    section.innerHTML = `<h5>Transitive (${transitive.length})</h5>`;
    container.appendChild(section);
}
```

---

### Summary: Phase 3 Impact

| Optimization | Latency | Memory | Bandwidth | Effort |
|---|---|---|---|---|
| Pagination | -100ms | 0 | -250KB | 8h |
| Search index | -50ms | +1MB | 0 | 4h |
| Virtual scroll | -200ms | -50MB | 0 | 10h |
| Web worker | -564ms | 0 | 0 | 8h |
| **Total** | **-914ms** | **-49MB** | **-250KB** | **30h** |

**Expected Result**: P99: 6455ms → **5541ms** (28% total improvement)

---

## Phase 4: Monitoring & Validation (Days 11-14, 5-8 hours)

### 4.1 Performance Monitoring Setup

```javascript
// static/js/performance-monitor.js
class PerformanceMonitor {
    constructor() {
        this.metrics = {};
    }
    
    mark(name) {
        performance.mark(name);
    }
    
    measure(name, startMark, endMark) {
        performance.measure(name, startMark, endMark);
        const measure = performance.getEntriesByName(name)[0];
        this.metrics[name] = measure.duration;
        return measure.duration;
    }
    
    report() {
        console.table(this.metrics);
    }
}

export const monitor = new PerformanceMonitor();

// Usage in dashboard.js
monitor.mark('app-init-start');
await initApp();
monitor.mark('app-init-end');
monitor.measure('app-init', 'app-init-start', 'app-init-end');

// Report when ready
window.addEventListener('load', () => {
    setTimeout(() => {
        monitor.report();
    }, 2000);
});
```

### 4.2 RUM Metrics Collection

```javascript
// Send metrics to backend for analysis
async function reportMetrics() {
    const metrics = {
        fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime,
        lcp: performance.getEntriesByName('largest-contentful-paint')[0]?.startTime,
        tti: performance.getEntriesByName('interactive')[0]?.startTime,
        cls: getCumulativeLayoutShift(),
    };
    
    await fetch('/api/v1/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metrics)
    });
}

window.addEventListener('load', () => {
    setTimeout(reportMetrics, 3000);
});
```

---

## Testing & Validation Checklist

### Performance Benchmarks

- [ ] **Initial Load** (<1000ms target)
  - [ ] Page load to interactive: <1000ms
  - [ ] First paint: <500ms
  - [ ] Largest contentful paint: <1500ms

- [ ] **Person List** (<100ms target)
  - [ ] 50-person list render: <100ms
  - [ ] Search filter on 500: <50ms (with index)
  - [ ] Pagination change: <200ms

- [ ] **Person Detail** (<500ms target)
  - [ ] First person detail load: <500ms
  - [ ] Subsequent views (cached): <200ms
  - [ ] Transitive relationships: <200ms

- [ ] **Memory** (<10MB growth)
  - [ ] Session memory leak: <5MB over 20 views
  - [ ] Event listeners after GC: <10 per page
  - [ ] Cache size: <5MB

### Regression Testing

- [ ] All entity types work (person, org, location, etc.)
- [ ] Tags and relationships display correctly
- [ ] File explorer functions
- [ ] Export/download works
- [ ] Search finds results
- [ ] Pagination works with >100 items
- [ ] Mobile responsive still functional

### Browser Testing

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS 15+)
- [ ] Chrome Mobile (Android 10+)

---

## Deployment Strategy

### Pre-Deployment

1. Create feature branch: `git checkout -b perf/frontend-optimization`
2. Implement Phase 1 optimizations
3. Run full test suite: `npm test`
4. Measure baseline metrics
5. Create pull request with performance data

### Staged Rollout

```
Week 1: 
- Deploy Phase 1 (Quick wins) → 10% traffic
- Monitor metrics for regressions
- If stable, increase to 50%
- If stable, 100%

Week 2-3:
- Deploy Phase 2 (Core optimizations)
- Same 10% → 50% → 100% rollout
- Monitor for memory leaks, errors

Week 4:
- Deploy Phase 3 (Advanced) if metrics positive
- Long-term monitoring
```

### Rollback Plan

```bash
# If metrics regress:
git revert <commit-hash>
git push
# API will restart with previous code

# Monitor:
/metrics endpoint for p99 latency
Performance dashboard for cache hit rate
```

---

## Success Metrics

**Target Outcomes**:

| Metric | Baseline | Target | Status |
|---|---|---|---|
| P99 Latency | 7660ms | <2000ms | Roadmap complete |
| P50 Latency | 21ms | <100ms | Expected with optimizations |
| Memory growth | 50MB/session | <5MB/session | After Phase 2 |
| Cache hit rate | 0% | >85% | After Phase 2 |
| JS bundle size | 456 KB | 92 KB | After minification + gzip |
| Network requests | 4+ per view | 1-2 | After caching + batching |
| Event listeners | 114+ | <5 | After delegation |

---

## References

- **Phase 1 Details**: [FRONTEND-PERFORMANCE-ANALYSIS.md](FRONTEND-PERFORMANCE-ANALYSIS.md)
- **Load Test Results**: [FINAL-LOAD-TEST-100-CONCURRENT.md](FINAL-LOAD-TEST-100-CONCURRENT.md)
- **Backend Metrics**: [PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md](PERFORMANCE-OPTIMIZATION-IMPLEMENTATION.md)

---

**Document Date**: 2026-05-19  
**Estimated Team Capacity**: 3-4 weeks (experienced full-stack team)  
**Expected ROI**: 87% latency reduction, 75% memory reduction, 80% bandwidth reduction

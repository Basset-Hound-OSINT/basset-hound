# Basset Hound - Complete API Reference

**Version**: 2.0.0  
**Last Updated**: 2026-05-07  
**Base URL**: `http://localhost:8080/api/v1` (development)

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Entity Endpoints](#entity-endpoints)
5. [Relationship Endpoints](#relationship-endpoints)
6. [Orphan Data Endpoints](#orphan-data-endpoints)
7. [Search Endpoints](#search-endpoints)
8. [Suggestion Endpoints](#suggestion-endpoints)
9. [Graph Analysis Endpoints](#graph-analysis-endpoints)
10. [Platform Endpoints](#platform-endpoints)
11. [Report Endpoints](#report-endpoints)
12. [Verification Endpoints](#verification-endpoints)
13. [Webhook Endpoints](#webhook-endpoints)
14. [WebSocket Endpoints](#websocket-endpoints)
15. **[Phase 8 New Features](#phase-8-new-features)** (50+ endpoints)
    - [Cache Management Endpoints](#cache-management-endpoints)
    - [ML Analytics Endpoints](#ml-analytics-endpoints)
    - [Real-Time Collaboration Endpoints](#real-time-collaboration-endpoints)
    - [Plugin System Endpoints](#plugin-system-endpoints)
    - [Export Endpoints](#export-endpoints)
    - [Performance Metrics Endpoints](#performance-metrics-endpoints)
16. [Administrative Endpoints](#administrative-endpoints)
17. [Error Codes](#error-codes)

---

## Overview

### API Features

- **50+ Endpoints** for complete OSINT platform management
- **HATEOAS Compliance** with self-documenting links
- **Pagination Support** with limit/offset parameters
- **Filtering** by multiple criteria
- **Sorting** by any field
- **Response Compression** (gzip)
- **Request Validation** via Pydantic
- **Rate Limiting** (100 req/min per IP)

### Response Format

All responses are JSON with consistent structure:

```json
{
  "status": "success|error",
  "data": {...},
  "meta": {
    "timestamp": "2026-05-07T12:00:00Z",
    "version": "2.0.0",
    "request_id": "req_abc123"
  },
  "links": {
    "self": "/api/v1/projects/proj_123",
    "next": "/api/v1/projects?page=2",
    "prev": "/api/v1/projects?page=1"
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Entity with ID 'ent_xyz' not found",
    "details": {
      "entity_id": "ent_xyz",
      "project_id": "proj_123"
    }
  },
  "meta": {
    "timestamp": "2026-05-07T12:00:00Z",
    "request_id": "req_def456"
  }
}
```

---

## Authentication

### Development Mode (Default)

No authentication required. All endpoints are public.

```bash
curl http://localhost:8080/api/v1/projects
```

### Production Mode

**Enable Authentication**

```bash
# Set in .env
AUTH_ENABLED=true
SECRET_KEY=your_secure_key_here
```

**Obtain Token**

```bash
# Login endpoint
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Use Token**

```bash
# Add to request headers
curl http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### Token Refresh

```bash
POST /auth/refresh
Authorization: Bearer {current_token}

# Returns new token
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "expires_in": 86400
}
```

---

## Rate Limiting

### Limits

- **100 requests per minute** per IP address
- **1000 requests per hour** per IP address
- **Burst allowance**: 20 simultaneous requests

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1725340800
```

### Rate Limit Response

When exceeded (429 Too Many Requests):

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "retry_after": 45
  }
}
```

---

## Entity Endpoints

### List Projects

```
GET /projects
```

**Parameters**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| limit | integer | No | 20 | Items per page (max 100) |
| offset | integer | No | 0 | Pagination offset |
| sort | string | No | -created_at | Sort by field, prefix with `-` for descending |

**Example**

```bash
curl 'http://localhost:8080/api/v1/projects?limit=10&offset=0&sort=-created_at'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": [
    {
      "id": "proj_123",
      "name": "Threat Intelligence",
      "description": "Active threat tracking",
      "created_at": "2026-05-01T10:00:00Z",
      "entity_count": 1250,
      "relationship_count": 3450,
      "links": {
        "self": "/api/v1/projects/proj_123",
        "entities": "/api/v1/projects/proj_123/entities",
        "search": "/api/v1/projects/proj_123/search/advanced"
      }
    }
  ],
  "meta": {
    "total_count": 42,
    "page": 1,
    "page_size": 10,
    "total_pages": 5
  }
}
```

### Create Project

```
POST /projects
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "Investigation 2026-05",
  "description": "May 2026 threat investigation",
  "owner": "analyst_001",
  "tags": ["threat", "2026", "active"]
}
```

**Response (201 Created)**

```json
{
  "status": "success",
  "data": {
    "id": "proj_abc789",
    "name": "Investigation 2026-05",
    "created_at": "2026-05-07T12:00:00Z",
    "entity_count": 0,
    "links": {
      "self": "/api/v1/projects/proj_abc789"
    }
  }
}
```

### Get Project

```
GET /projects/{project_id}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "id": "proj_123",
    "name": "Threat Intelligence",
    "description": "Active threat tracking",
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-07T11:30:00Z",
    "entity_count": 1250,
    "relationship_count": 3450,
    "orphan_data_count": 45,
    "statistics": {
      "entities_by_type": {
        "Person": 800,
        "Organization": 250,
        "Platform": 150,
        "Location": 50
      },
      "relationships_by_type": {
        "WORKS_FOR": 1200,
        "KNOWS": 800,
        "OWNS": 600
      }
    }
  }
}
```

### Update Project

```
PUT /projects/{project_id}
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "Updated Project Name",
  "description": "Updated description",
  "tags": ["tag1", "tag2"]
}
```

**Response (200 OK)**

### Delete Project

```
DELETE /projects/{project_id}
```

**Response (204 No Content)**

---

## Entity Endpoints

### List Entities

```
GET /projects/{project_id}/entities
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_type | string | No | Filter: PERSON, ORGANIZATION, PLATFORM, LOCATION, GROUP, GOVERNMENT, SOCK_PUPPET |
| limit | integer | No | Items per page (default 20, max 100) |
| offset | integer | No | Pagination offset |
| sort | string | No | Sort by field |
| search | string | No | Quick text search |

**Example**

```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/entities?entity_type=PERSON&limit=50&sort=name'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": [
    {
      "id": "ent_001",
      "type": "PERSON",
      "name": "John Doe",
      "attributes": {
        "email": "john@example.com",
        "phone": "+1234567890",
        "location": "New York, USA"
      },
      "relationships_count": 23,
      "created_at": "2026-05-01T10:00:00Z",
      "updated_at": "2026-05-07T11:30:00Z",
      "links": {
        "self": "/api/v1/projects/proj_123/entities/ent_001",
        "relationships": "/api/v1/projects/proj_123/entities/ent_001/relationships",
        "suggestions": "/api/v1/projects/proj_123/entities/ent_001/suggestions"
      }
    }
  ],
  "meta": {
    "total_count": 1250,
    "page": 1,
    "page_size": 20
  }
}
```

### Create Entity

```
POST /projects/{project_id}/entities
Content-Type: application/json
```

**Request Body**

```json
{
  "type": "PERSON",
  "name": "Jane Smith",
  "attributes": {
    "email": "jane@example.com",
    "phone": "+9876543210",
    "location": "San Francisco, USA",
    "social_media": [
      {
        "platform": "Twitter",
        "username": "@janesmith"
      },
      {
        "platform": "LinkedIn",
        "username": "jane-smith-123"
      }
    ]
  },
  "tags": ["suspect", "high-priority"],
  "source": "data-breach-x"
}
```

**Response (201 Created)**

```json
{
  "status": "success",
  "data": {
    "id": "ent_new123",
    "type": "PERSON",
    "name": "Jane Smith",
    "created_at": "2026-05-07T12:00:00Z",
    "links": {
      "self": "/api/v1/projects/proj_123/entities/ent_new123"
    }
  }
}
```

### Get Entity

```
GET /projects/{project_id}/entities/{entity_id}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "id": "ent_001",
    "type": "PERSON",
    "name": "John Doe",
    "attributes": {
      "email": "john@example.com",
      "phone": "+1234567890",
      "location": "New York, USA",
      "aliases": ["Johnny D", "J. Doe"]
    },
    "relationships": [
      {
        "id": "rel_001",
        "type": "WORKS_FOR",
        "target_entity": {
          "id": "ent_002",
          "name": "Acme Corp"
        },
        "properties": {
          "title": "Senior Developer",
          "start_date": "2020-01-15"
        }
      }
    ],
    "data_items": [
      {
        "id": "data_001",
        "type": "EMAIL",
        "value": "john@example.com",
        "confidence": 0.95,
        "source": "data-breach-2024"
      }
    ],
    "timeline": [
      {
        "date": "2026-05-01T10:00:00Z",
        "event": "Entity created",
        "user": "analyst_001"
      }
    ],
    "created_at": "2026-05-01T10:00:00Z",
    "updated_at": "2026-05-07T11:30:00Z"
  }
}
```

### Update Entity

```
PUT /projects/{project_id}/entities/{entity_id}
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "Updated Name",
  "attributes": {
    "email": "newemail@example.com"
  },
  "tags": ["updated-tag"]
}
```

**Response (200 OK)**

### Delete Entity

```
DELETE /projects/{project_id}/entities/{entity_id}
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| cascade | boolean | true | Delete related entities |

**Response (204 No Content)**

---

## Relationship Endpoints

### List Relationships

```
GET /projects/{project_id}/relationships
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| entity_id | string | Filter by entity |
| relationship_type | string | Filter by type (WORKS_FOR, KNOWS, FAMILY, etc.) |
| limit | integer | Items per page (default 20) |
| offset | integer | Pagination offset |

**Example**

```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/relationships?entity_id=ent_001&relationship_type=WORKS_FOR'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": [
    {
      "id": "rel_001",
      "source": "ent_001",
      "target": "ent_002",
      "type": "WORKS_FOR",
      "properties": {
        "title": "Senior Developer",
        "start_date": "2020-01-15",
        "end_date": null,
        "confidence": 0.99
      },
      "created_at": "2026-05-01T10:00:00Z"
    }
  ]
}
```

### Create Relationship

```
POST /projects/{project_id}/relationships
Content-Type: application/json
```

**Request Body**

```json
{
  "source_entity_id": "ent_001",
  "target_entity_id": "ent_002",
  "relationship_type": "WORKS_FOR",
  "properties": {
    "title": "Senior Developer",
    "start_date": "2020-01-15",
    "confidence": 0.95
  },
  "bidirectional": false,
  "source": "analyst_observation",
  "confidence_level": "HIGH"
}
```

**Response (201 Created)**

```json
{
  "status": "success",
  "data": {
    "id": "rel_new456",
    "source": "ent_001",
    "target": "ent_002",
    "type": "WORKS_FOR",
    "created_at": "2026-05-07T12:00:00Z"
  }
}
```

### Get Relationship

```
GET /projects/{project_id}/relationships/{relationship_id}
```

### Update Relationship

```
PUT /projects/{project_id}/relationships/{relationship_id}
Content-Type: application/json
```

**Request Body**

```json
{
  "properties": {
    "title": "Lead Developer",
    "confidence": 0.98
  }
}
```

### Delete Relationship

```
DELETE /projects/{project_id}/relationships/{relationship_id}
```

---

## Orphan Data Endpoints

### List Orphan Data

```
GET /projects/{project_id}/orphan-data
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| identifier_type | string | EMAIL, PHONE, USERNAME, DOMAIN, IP, CRYPTO, FILE |
| status | string | PENDING, LINKED, DISMISSED, ARCHIVED |
| limit | integer | Items per page (default 20) |
| offset | integer | Pagination offset |

**Example**

```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/orphan-data?status=PENDING&limit=50'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": [
    {
      "id": "orphan_001",
      "identifier_type": "EMAIL",
      "identifier_value": "unknown@example.com",
      "status": "PENDING",
      "confidence": 0.65,
      "source": "data-breach-x",
      "metadata": {
        "found_date": "2026-05-01",
        "breach_name": "Breach XYZ"
      },
      "suggestions": [
        {
          "entity_id": "ent_001",
          "confidence": 0.78,
          "reason": "Email pattern matches"
        }
      ],
      "created_at": "2026-05-01T10:00:00Z",
      "links": {
        "self": "/api/v1/projects/proj_123/orphan-data/orphan_001",
        "suggestions": "/api/v1/projects/proj_123/orphan-data/orphan_001/suggestions"
      }
    }
  ]
}
```

### Create Orphan Data

```
POST /projects/{project_id}/orphan-data
Content-Type: application/json
```

**Request Body**

```json
{
  "identifier_type": "EMAIL",
  "identifier_value": "suspicious@example.com",
  "source": "data-breach-2024",
  "metadata": {
    "breach_name": "Breach ABC",
    "found_date": "2026-05-01",
    "confidence": "high"
  },
  "tags": ["breach-2024", "investigate"]
}
```

**Response (201 Created)**

```json
{
  "status": "success",
  "data": {
    "id": "orphan_new789",
    "identifier_type": "EMAIL",
    "identifier_value": "suspicious@example.com",
    "status": "PENDING",
    "created_at": "2026-05-07T12:00:00Z"
  }
}
```

### Get Orphan Suggestions

```
GET /projects/{project_id}/orphan-data/{orphan_id}/suggestions
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| confidence_level | string | ALL | HIGH, MEDIUM, LOW |
| limit | integer | 20 | Max suggestions to return |

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "orphan_id": "orphan_001",
    "suggestions": [
      {
        "entity_id": "ent_001",
        "entity_name": "John Doe",
        "entity_type": "PERSON",
        "confidence": 0.92,
        "match_reasons": [
          "Email domain matches",
          "Name pattern matches",
          "Location overlap"
        ],
        "matching_fields": [
          "email",
          "location"
        ]
      }
    ],
    "total_suggestions": 1
  }
}
```

### Link Orphan to Entity

```
POST /projects/{project_id}/orphan-data/{orphan_id}/link/{entity_id}
Content-Type: application/json
```

**Request Body**

```json
{
  "reason": "Confirmed by analyst",
  "confidence": 0.99,
  "notes": "Email verified through OSINT"
}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "orphan_id": "orphan_001",
    "entity_id": "ent_001",
    "status": "LINKED",
    "linked_at": "2026-05-07T12:00:00Z",
    "data_item": {
      "id": "data_new001",
      "type": "EMAIL",
      "value": "john@example.com"
    }
  }
}
```

---

## Search Endpoints

### Advanced Search

```
GET /projects/{project_id}/search/advanced
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Boolean search query |
| entity_type | string | No | Filter by entity type |
| limit | integer | No | Results per page (default 20, max 100) |
| offset | integer | No | Pagination offset |

**Query Syntax**

```
# Boolean operators
AND, OR, NOT

# Field-specific
email:john@example.com
name:John*
location:"New York"

# Exact match
"exact phrase"

# Wildcards
name:John*    (ends with any)
name:*Doe     (starts with any)
phone:555?    (single char)

# Ranges
confidence:[0.8 TO 1.0]
created_at:[2026-05-01 TO 2026-05-07]
```

**Example Queries**

```bash
# Find all Johns who work for Acme
curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced?query=name:John+AND+organization:Acme'

# Find suspicious emails
curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced?query=email:*@suspicious.com+AND+tag:suspect'

# Complex query
curl 'http://localhost:8080/api/v1/projects/proj_123/search/advanced?query=(name:John+OR+email:john*)+AND+NOT+status:cleared'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "query": "name:John* AND organization:Acme",
    "results": [
      {
        "id": "ent_001",
        "type": "PERSON",
        "name": "John Doe",
        "score": 0.98,
        "highlights": {
          "name": "<em>John</em> Doe",
          "organization": "<em>Acme</em> Corp"
        }
      }
    ]
  },
  "meta": {
    "total_results": 1,
    "query_time_ms": 145,
    "suggestion": "Did you mean: 'name:John* AND organization:Acme Corp'"
  }
}
```

### Saved Search

```
POST /projects/{project_id}/saved-searches
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "High-value targets",
  "description": "Organizations with 50+ employees",
  "query": "type:ORGANIZATION AND employee_count:[50 TO *]",
  "tags": ["targets", "analysis"],
  "alert_enabled": true,
  "alert_frequency": "DAILY"
}
```

---

## Suggestion Endpoints

### Get Entity Suggestions

```
GET /projects/{project_id}/entities/{entity_id}/suggestions
```

**Parameters**

| Name | Type | Default | Description |
|------|------|---------|-------------|
| confidence_level | string | ALL | HIGH, MEDIUM, LOW |
| suggestion_type | string | ALL | DUPLICATE, RELATED, MERGE |
| limit | integer | 20 | Max suggestions |

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_001",
    "suggestions": [
      {
        "id": "sugg_001",
        "type": "DUPLICATE",
        "target_entity": {
          "id": "ent_002",
          "name": "Jane Smith",
          "type": "PERSON"
        },
        "confidence": 0.95,
        "reasons": [
          "Same email address",
          "Identical phone number",
          "Same location and workplace"
        ],
        "recommendation": "MERGE",
        "created_at": "2026-05-07T10:00:00Z"
      }
    ]
  }
}
```

### Dismiss Suggestion

```
POST /projects/{project_id}/suggestions/{suggestion_id}/dismiss
Content-Type: application/json
```

**Request Body**

```json
{
  "reason": "NOT_A_MATCH",
  "notes": "Different person with same name",
  "dismissed_by": "analyst_001"
}
```

**Response (200 OK)**

### Merge Entities (Accept Suggestion)

```
POST /projects/{project_id}/suggestions/{suggestion_id}/accept
Content-Type: application/json
```

**Request Body**

```json
{
  "keep_entity_id": "ent_001",
  "reason": "Confirmed duplicate",
  "merge_strategy": "KEEP_PRIMARY",
  "merged_by": "analyst_001"
}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "merged_entity_id": "ent_001",
    "archived_entity_id": "ent_002",
    "relationships_merged": 45,
    "data_items_merged": 12,
    "merged_at": "2026-05-07T12:00:00Z"
  }
}
```

---

## Graph Analysis Endpoints

### Find Shortest Path

```
GET /projects/{project_id}/graph/paths/shortest
```

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| source_id | string | Yes | Starting entity ID |
| target_id | string | Yes | Ending entity ID |
| max_depth | integer | No | Maximum path length (default 5) |
| relationship_types | string | No | Comma-separated filter |

**Example**

```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/graph/paths/shortest?source_id=ent_001&target_id=ent_050&max_depth=6'
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "paths": [
      {
        "length": 3,
        "nodes": [
          {
            "id": "ent_001",
            "name": "John Doe",
            "type": "PERSON"
          },
          {
            "id": "ent_010",
            "name": "Acme Corp",
            "type": "ORGANIZATION"
          },
          {
            "id": "ent_050",
            "name": "Jane Smith",
            "type": "PERSON"
          }
        ],
        "relationships": [
          {
            "source": "ent_001",
            "target": "ent_010",
            "type": "WORKS_FOR"
          },
          {
            "source": "ent_010",
            "target": "ent_050",
            "type": "OWNS"
          }
        ]
      }
    ]
  }
}
```

### Centrality Analysis

```
GET /projects/{project_id}/graph/analytics/centrality
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| algorithm | string | BETWEENNESS, CLOSENESS, DEGREE, EIGENVECTOR |
| limit | integer | Top N results (default 20) |

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "algorithm": "BETWEENNESS",
    "results": [
      {
        "entity_id": "ent_001",
        "entity_name": "John Doe",
        "score": 0.85,
        "rank": 1,
        "influence": "HIGH",
        "adjacent_entities": 45
      }
    ]
  }
}
```

### Community Detection

```
GET /projects/{project_id}/graph/analytics/communities
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "communities": [
      {
        "id": "community_1",
        "size": 125,
        "density": 0.72,
        "members": ["ent_001", "ent_010", "ent_020"],
        "description": "Acme Corp employees cluster"
      }
    ],
    "modularity": 0.65
  }
}
```

---

## Platform Endpoints

### List Platforms

```
GET /platforms
```

**Parameters**

| Name | Type | Description |
|------|------|-------------|
| limit | integer | Items per page |
| offset | integer | Pagination offset |
| search | string | Filter by name |

**Response (200 OK)**

```json
{
  "status": "success",
  "data": [
    {
      "id": "platform_twitter",
      "name": "Twitter",
      "domain": "twitter.com",
      "platform_type": "SOCIAL_MEDIA",
      "account_fields": [
        {
          "id": "username",
          "label": "Username",
          "type": "text",
          "required": true
        },
        {
          "id": "followers",
          "label": "Followers",
          "type": "number",
          "required": false
        }
      ],
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

### Create Platform

```
POST /platforms
Content-Type: application/json
```

**Request Body**

```json
{
  "name": "Custom Forum",
  "domain": "customforum.com",
  "platform_type": "FORUM",
  "account_fields": [
    {
      "id": "username",
      "label": "Username",
      "type": "text",
      "required": true
    },
    {
      "id": "user_id",
      "label": "User ID",
      "type": "text",
      "required": true
    }
  ]
}
```

### Seed Default Platforms

```
POST /platforms/seed
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "platforms_created": 70,
    "platforms_updated": 5
  }
}
```

---

## Report Endpoints

### Generate Report

```
POST /projects/{project_id}/reports/generate
Content-Type: application/json
```

**Request Body**

```json
{
  "format": "PDF",
  "template": "FULL_PROFILE",
  "title": "Investigation Report - May 2026",
  "entities": ["ent_001", "ent_010"],
  "include_sections": [
    "ENTITY_PROFILE",
    "RELATIONSHIPS",
    "TIMELINE",
    "STATISTICS"
  ],
  "include_graph": true
}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "report_id": "rpt_001",
    "filename": "Investigation_Report_May_2026.pdf",
    "size_kb": 1250,
    "generated_at": "2026-05-07T12:00:00Z",
    "download_url": "/api/v1/projects/proj_123/reports/rpt_001/download"
  }
}
```

### Download Report

```
GET /projects/{project_id}/reports/{report_id}/download
```

**Response (200 OK)**

File download (Content-Type: application/pdf)

---

## Verification Endpoints

### Verify Email

```
POST /verify/email
Content-Type: application/json
```

**Request Body**

```json
{
  "email": "user@example.com",
  "project_id": "proj_123"
}
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "email": "user@example.com",
    "is_valid": true,
    "is_deliverable": true,
    "has_breaches": 1,
    "breaches": ["Breach XYZ"],
    "verification_source": "basset-verify"
  }
}
```

### Verify Phone

```
POST /verify/phone
Content-Type: application/json
```

**Request Body**

```json
{
  "phone": "+1234567890",
  "project_id": "proj_123"
}
```

---

## Webhook Endpoints

### Create Webhook

```
POST /webhooks
Content-Type: application/json
```

**Request Body**

```json
{
  "url": "https://your-server.com/webhooks/basset",
  "events": [
    "entity.created",
    "entity.updated",
    "suggestion.generated",
    "report.completed"
  ],
  "active": true
}
```

### List Webhooks

```
GET /webhooks
```

### Update Webhook

```
PUT /webhooks/{webhook_id}
Content-Type: application/json
```

### Delete Webhook

```
DELETE /webhooks/{webhook_id}
```

---

## WebSocket Endpoints

### Suggestions WebSocket

```
WS /ws/suggestions/{project_id}
```

**Connect**

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/suggestions/proj_123');

ws.onopen = () => {
  console.log('Connected to suggestions stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event_type);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

**Events**

| Event | Payload |
|-------|---------|
| suggestion_generated | `{entity_id, suggestion_count, confidence_levels}` |
| suggestion_dismissed | `{suggestion_id, entity_id}` |
| suggestion_accepted | `{suggestion_id, merge_result}` |
| batch_processed | `{total, accepted, dismissed}` |

### Project Activity WebSocket

```
WS /ws/projects/{project_id}
```

**Events**

- `entity_created`
- `entity_updated`
- `entity_deleted`
- `relationship_created`
- `relationship_deleted`
- `import_started`
- `import_completed`

---

## Phase 8 New Features

Phase 8 introduces 50+ new endpoints across 6 major feature areas. These endpoints are optional and controlled by feature flags in `.env`.

### Cache Management Endpoints

**View Cache Statistics**

```
GET /api/v1/cache/stats
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "hit_rate": 0.62,
    "miss_rate": 0.38,
    "total_requests": 10000,
    "total_hits": 6200,
    "total_misses": 3800,
    "memory_used_mb": 85,
    "memory_limit_mb": 256,
    "entries_count": 450,
    "entries_max": 1000,
    "avg_hit_latency_ms": 0.5,
    "avg_miss_latency_ms": 45
  }
}
```

**Clear All Cache**

```
POST /api/v1/cache/clear
```

**Clear Specific Cache Key**

```
POST /api/v1/cache/clear/{key}
```

**Get Cache Hit Rate**

```
GET /api/v1/cache/hit-rate
```

**Warm Cache with Common Queries**

```
POST /api/v1/cache/warm
```

**List Cached Keys**

```
GET /api/v1/cache/keys?pattern=entity:*
```

### ML Analytics Endpoints

**Find Duplicate Entities**

```
GET /api/v1/ml/duplicates?entity_id={id}&confidence_threshold=0.75&limit=10
```

**Response**

```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_123",
    "duplicates": [
      {
        "id": "ent_456",
        "name": "John Smith",
        "similarity": 0.92,
        "reason": "Same email domain and name similarity"
      }
    ]
  }
}
```

**Merge Duplicate Entities**

```
POST /api/v1/ml/duplicates/merge
Content-Type: application/json

{
  "source_id": "ent_456",
  "target_id": "ent_123",
  "strategy": "merge_fields"
}
```

**Predict Link Relationships**

```
GET /api/v1/ml/link-prediction?entity_id={id}&top_k=10
```

**Accept Predicted Link**

```
POST /api/v1/ml/link-prediction/accept
Content-Type: application/json

{
  "source_id": "ent_123",
  "target_id": "ent_456",
  "relationship_type": "KNOWS",
  "confidence": 0.85
}
```

**Detect Communities**

```
GET /api/v1/ml/communities?project_id={id}&algorithm=louvain&min_size=3
```

**Detect Anomalies**

```
GET /api/v1/ml/anomalies?project_id={id}&threshold=0.7
```

**Extract ML Features**

```
POST /api/v1/ml/features/extract
Content-Type: application/json

{
  "entity_id": "ent_123",
  "feature_types": ["similarity", "embeddings", "network"]
}
```

**Get ML Model Status**

```
GET /api/v1/ml/models/status
```

### Real-Time Collaboration Endpoints

**Get Active Users in Project**

```
GET /api/v1/collaboration/presence?project_id={id}
```

**Response**

```json
{
  "status": "success",
  "data": {
    "active_users": [
      {
        "user_id": "usr_123",
        "name": "John Doe",
        "status": "online",
        "viewing_entity": "ent_456",
        "last_action": "2026-05-07T12:00:00Z"
      }
    ]
  }
}
```

**Get Activity Feed**

```
GET /api/v1/collaboration/activity?project_id={id}&limit=50&offset=0
```

**Archive Old Activity**

```
POST /api/v1/collaboration/activity/archive
Content-Type: application/json

{
  "project_id": "proj_123",
  "older_than_minutes": 5
}
```

**List Merge Conflicts**

```
GET /api/v1/collaboration/conflicts?project_id={id}
```

**Resolve Conflict**

```
POST /api/v1/collaboration/conflicts/resolve
Content-Type: application/json

{
  "conflict_id": "conflict_123",
  "resolution": "merge"
}
```

**WebSocket Real-Time Sync**

```
WebSocket /ws/sync/{project_id}
```

Message format:
```json
{
  "type": "entity_updated",
  "entity_id": "ent_123",
  "changes": {
    "fields": {"email": "new@example.com"}
  },
  "user_id": "usr_456",
  "timestamp": "2026-05-07T12:00:00Z"
}
```

**Undo Operation (Collaborative)**

```
POST /api/v1/collaboration/undo
Content-Type: application/json

{
  "project_id": "proj_123",
  "operation_id": "op_789"
}
```

### Plugin System Endpoints

**List Available Plugins**

```
GET /api/v1/plugins
```

**Upload Custom Plugin**

```
POST /api/v1/plugins/upload
Content-Type: multipart/form-data

file: plugin.zip (max 5MB)
```

**Get Plugin Information**

```
GET /api/v1/plugins/{plugin_id}
```

**Install Plugin**

```
POST /api/v1/plugins/{plugin_id}/install
```

**Uninstall Plugin**

```
DELETE /api/v1/plugins/{plugin_id}
```

**Get Plugin Data**

```
GET /api/v1/plugins/{plugin_id}/data?start_date={date}&entity_type={type}
```

### Export Endpoints

**Export as GraphML**

```
POST /api/v1/projects/{project_id}/export/graphml
Content-Type: application/json

{
  "entity_types": ["Person"],
  "tags": ["VIP"],
  "include_properties": true
}
```

**Export as CSV**

```
POST /api/v1/projects/{project_id}/export/csv
Content-Type: application/json

{
  "filters": {
    "created_after": "2026-01-01",
    "entity_types": ["Person"]
  },
  "fields": ["id", "name", "email"],
  "page": 1,
  "limit": 1000
}
```

**Export as JSON**

```
POST /api/v1/projects/{project_id}/export/json
Content-Type: application/json

{
  "include_entities": true,
  "include_relationships": true
}
```

**Export as GeoJSON**

```
POST /api/v1/projects/{project_id}/export/geojson
Content-Type: application/json

{
  "entity_type": "Location"
}
```

**Export as PDF Report**

```
POST /api/v1/projects/{project_id}/export/pdf
Content-Type: application/json

{
  "title": "Investigation Report",
  "include_charts": true,
  "include_metrics": true
}
```

**Export Full Database Dump**

```
POST /api/v1/projects/{project_id}/export/database
Content-Type: application/json

{
  "encrypt": true,
  "password": "secure_password",
  "compression": "gzip"
}
```

### Performance Metrics Endpoints

**Get Overall Performance Metrics**

```
GET /api/v1/metrics/performance
```

**Response**

```json
{
  "status": "success",
  "data": {
    "cpu_usage_percent": 25.5,
    "memory_usage_mb": 450,
    "memory_available_mb": 8192,
    "open_connections": 45,
    "requests_per_second": 150,
    "avg_response_time_ms": 45,
    "p95_response_time_ms": 95,
    "p99_response_time_ms": 120,
    "cache_hit_rate": 0.62,
    "api_errors_per_minute": 2,
    "database_queries_per_minute": 200,
    "uptime_minutes": 45280
  }
}
```

**Get Latency Distribution**

```
GET /api/v1/metrics/latency
```

**Get Request Throughput**

```
GET /api/v1/metrics/throughput
```

**Get Database Metrics**

```
GET /api/v1/metrics/database
```

**Get Memory Usage Statistics**

```
GET /api/v1/metrics/memory
```

**Get Query Performance Analysis**

```
GET /api/v1/queries/slow?limit=20
```

**Analyze Query Execution Plan**

```
POST /api/v1/queries/analyze
Content-Type: application/json

{
  "query": "MATCH (p:Person) RETURN p LIMIT 10"
}
```

**List Database Indexes**

```
GET /api/v1/indexes
```

**Analyze Index Usage**

```
POST /api/v1/indexes/analyze
```

### Search Optimization Endpoints

**Full-Text Search with Advanced Operators**

```
GET /api/v1/search/full-text?q=query&limit=20
```

**Advanced Faceted Search**

```
GET /api/v1/search/advanced?entity_type=Person&tags=VIP&created_after=2026-01-01
```

**Entity Autocomplete**

```
GET /api/v1/search/autocomplete?q=john&limit=10
```

**Did You Mean (Fuzzy)**

```
GET /api/v1/search/did-you-mean?q=jon+smith
```

**Search Analytics**

```
GET /api/v1/search/analytics?days=30
```

**Rebuild Search Indexes**

```
POST /api/v1/search/index/build
```

**Get Available Facets**

```
GET /api/v1/search/facets
```

**Save Search for Later**

```
POST /api/v1/search/save
Content-Type: application/json

{
  "name": "My Search",
  "query": "...",
  "filters": {...}
}
```

---

## Administrative Endpoints

### Health Check

```
GET /health
```

**Response (200 OK)**

```json
{
  "status": "healthy",
  "services": {
    "api": "healthy",
    "neo4j": "healthy",
    "redis": "healthy",
    "mcp": "healthy"
  },
  "version": "2.0.0",
  "timestamp": "2026-05-07T12:00:00Z"
}
```

### Prometheus Metrics

```
GET /metrics
```

**Response (200 OK)**

Plain text Prometheus format:

```
# HELP basset_request_count Total HTTP requests
# TYPE basset_request_count counter
basset_request_count{method="GET",path="/api/v1/projects",status="200"} 1250

# HELP basset_entity_count Total entities
# TYPE basset_entity_count gauge
basset_entity_count{project="proj_123"} 1250
```

### System Statistics

```
GET /admin/statistics
```

**Response (200 OK)**

```json
{
  "status": "success",
  "data": {
    "total_projects": 42,
    "total_entities": 125000,
    "total_relationships": 450000,
    "total_orphan_data": 5000,
    "database_size_gb": 25.3,
    "cache_hit_rate": 0.78,
    "api_requests_today": 15000,
    "average_response_time_ms": 145
  }
}
```

---

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| INVALID_REQUEST | 400 | Malformed request |
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Duplicate resource |
| VALIDATION_ERROR | 422 | Invalid data format |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service down |
| DATABASE_ERROR | 500 | Database error |
| ENTITY_NOT_FOUND | 404 | Entity does not exist |
| PROJECT_NOT_FOUND | 404 | Project does not exist |
| RELATIONSHIP_NOT_FOUND | 404 | Relationship does not exist |
| ORPHAN_NOT_FOUND | 404 | Orphan data not found |
| INVALID_ENTITY_TYPE | 400 | Invalid entity type |
| DUPLICATE_ENTITY | 409 | Entity already exists |
| CANNOT_DELETE_ENTITY | 400 | Entity has dependencies |

---

**Last Updated**: 2026-05-07  
**Version**: 2.0.0

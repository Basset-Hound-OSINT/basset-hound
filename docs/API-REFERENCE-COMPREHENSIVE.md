# Basset Hound - Comprehensive API Reference

**Version**: 3.0.0  
**Last Updated**: 2026-05-19  
**Base URL**: `http://localhost:8080/api/v1` (development)  
**Production URL**: `https://api.basset-hound.com/api/v1` (when deployed)

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Rate Limiting](#rate-limiting)
5. [Error Handling](#error-handling)
6. [Response Format](#response-format)
7. **Core Features (API Endpoints)**
   - [Authentication Endpoints](#authentication-endpoints)
   - [Projects Management](#projects-management)
   - [Entities Management](#entities-management)
   - [Relationships Management](#relationships-management)
   - [Search Endpoints](#search-endpoints)
   - [Export & Reports](#export--reports)
   - [Webhooks](#webhooks)
   - [WebSocket (Real-time)](#websocket-real-time)
   - [Analytics](#analytics)
   - [Graph Analysis](#graph-analysis)
   - [Import/Export Data](#importexport-data)
   - [ML & Suggestions](#ml--suggestions)
   - [Cache Management](#cache-management)
   - [Deduplication](#deduplication)
   - [Data Quality](#data-quality)
   - [Verification](#verification)
   - [Audit Logging](#audit-logging)
   - [Advanced Features](#advanced-features)
8. [Common Patterns](#common-patterns)
9. [Examples](#examples)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Basset Hound API provides comprehensive REST endpoints for OSINT investigation management with **404+ endpoints** across **54 routers**. The API is built with FastAPI and provides:

- **Security**: JWT authentication, token refresh, permission scopes
- **Performance**: Response compression (60-70% bandwidth reduction), caching with 60%+ hit rate
- **Scalability**: Connection pooling, request timeout handling, multi-worker support
- **Reliability**: Comprehensive error handling, audit logging, health checks
- **Integration**: WebSocket for real-time collaboration, webhooks for external integrations
- **Analytics**: Search analytics, query suggestions, performance tracking
- **ML Features**: Duplicate detection, link prediction, entity suggestions

### Key Features

| Feature | Details |
|---------|---------|
| **Total Endpoints** | 404+ endpoints across 54 routers |
| **Authentication** | JWT tokens with refresh, token validation, scoped access |
| **Rate Limiting** | 100 req/min per IP, 1000 req/hour, 20 burst concurrent |
| **Response Compression** | GZIP (60-70% reduction for large responses) |
| **Caching** | Redis-backed with 60%+ hit rate on repeat queries |
| **WebSocket** | Real-time collaboration, live updates, heartbeat monitoring |
| **Pagination** | Limit/offset with configurable page sizes |
| **Filtering** | Advanced filters, full-text search, fuzzy matching |
| **Export Formats** | JSON, CSV, GraphML, PDF, Markdown |
| **Query Response Time** | <100ms (99th percentile) |

---

## Getting Started

### 1. Check API Health

```bash
curl -s http://localhost:8080/health | jq
```

**Response (200 OK)**
```json
{
  "status": "healthy",
  "version": "3.0.0",
  "services": {
    "neo4j": {
      "status": "connected",
      "latency_ms": 2,
      "pool_size": 150
    },
    "redis": {
      "status": "connected",
      "latency_ms": 1,
      "pool_size": 100
    }
  },
  "uptime_seconds": 3600
}
```

### 2. Authenticate (Production Only)

In development, authentication is disabled. In production:

```bash
# Step 1: Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_secure_password"
  }'

# Response includes access_token and refresh_token
# {
#   "access_token": "eyJhbGc...",
#   "refresh_token": "eyJhbGc...",
#   "token_type": "bearer",
#   "expires_in": 1800
# }

# Step 2: Use token in requests
curl http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer eyJhbGc..."
```

### 3. List Projects

```bash
curl -s http://localhost:8080/api/v1/projects | jq '.[] | {id, name, created_at}'
```

### 4. Create a Project

```bash
curl -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Investigation 2026-05"
  }'
```

---

## Authentication

### Development Mode (Default)

No authentication required. All endpoints are publicly accessible.

```bash
# No Authorization header needed
curl http://localhost:8080/api/v1/projects
```

### Production Mode

Enable with `AUTH_ENABLED=true` in `.env`

#### Login Endpoint

```
POST /auth/login
Content-Type: application/json
```

**Request**
```json
{
  "username": "analyst_001",
  "password": "SecurePassword123!"
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Token Format

All JWT tokens contain:
- **Access Token**: 30 minutes validity, used for API requests
- **Refresh Token**: 7 days validity, used to obtain new access tokens
- **Scopes**: Permission scopes (read:projects, write:projects, etc.)

#### Using Tokens

```bash
# Add to Authorization header
curl http://localhost:8080/api/v1/projects \
  -H "Authorization: Bearer {access_token}"

# Or use in JavaScript/Python
headers = {
  "Authorization": f"Bearer {access_token}"
}
```

#### Token Refresh

When access token expires (optional, before expiration):

```
POST /auth/refresh
Content-Type: application/json
```

**Request**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### Token Validation

```
POST /auth/validate
Content-Type: application/json
Authorization: Bearer {token}
```

**Response (200 OK)**
```json
{
  "valid": true,
  "user_id": "user_123",
  "username": "analyst_001",
  "scopes": ["read:projects", "write:projects", "read:entities", "write:entities"],
  "expires_in": 1234
}
```

---

## Rate Limiting

### Limits

- **Per Minute**: 100 requests per IP per minute
- **Per Hour**: 1000 requests per IP per hour
- **Burst**: 20 simultaneous concurrent requests

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1725340800
```

Where:
- `Limit`: Maximum requests per minute
- `Remaining`: Requests left in current minute
- `Reset`: Unix timestamp when limit resets

### Handling Rate Limits

When rate limited (HTTP 429):

```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

**Best Practices**:
1. Check `X-RateLimit-Remaining` header
2. Implement exponential backoff for retries
3. Use `Retry-After` header to wait before retrying
4. Batch requests when possible

```python
# Python example with retry logic
import requests
import time

def api_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retrying in {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "value",
      "context": "additional context"
    }
  },
  "meta": {
    "timestamp": "2026-05-19T12:00:00Z",
    "request_id": "req_abc123",
    "path": "/api/v1/projects/proj_123/entities"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Details |
|------|---------|---------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 204 | No Content | Request successful, no response body |
| 400 | Bad Request | Invalid request parameters or body |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated but not authorized for this resource |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Resource already exists or state conflict |
| 422 | Unprocessable Entity | Request validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error occurred |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Request timeout (>30 seconds) |

### Common Error Codes

| Code | HTTP | Meaning | Resolution |
|------|------|---------|-----------|
| ENTITY_NOT_FOUND | 404 | Entity ID does not exist | Verify entity ID is correct |
| PROJECT_NOT_FOUND | 404 | Project ID does not exist | List projects to find correct ID |
| INVALID_REQUEST | 400 | Request body/params invalid | Check request format and required fields |
| AUTHENTICATION_FAILED | 401 | Invalid credentials | Verify username and password |
| TOKEN_EXPIRED | 401 | JWT token expired | Refresh token using /auth/refresh |
| PERMISSION_DENIED | 403 | Insufficient permissions | Contact admin for access grant |
| DUPLICATE_ENTITY | 409 | Entity already exists | Use update endpoint instead |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests | Wait before retrying |
| DATABASE_ERROR | 500 | Neo4j connection failed | Check database health at /health |
| REQUEST_TIMEOUT | 504 | Request exceeded 30s timeout | Try again with simpler query |

---

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": {
    "id": "entity_123",
    "name": "John Doe",
    "type": "Person",
    "created_at": "2026-05-01T10:30:00Z"
  },
  "meta": {
    "timestamp": "2026-05-19T12:00:00Z",
    "version": "3.0.0",
    "request_id": "req_xyz789"
  }
}
```

### List Response with Pagination

```json
{
  "status": "success",
  "data": [
    {
      "id": "entity_001",
      "name": "Entity 1"
    },
    {
      "id": "entity_002",
      "name": "Entity 2"
    }
  ],
  "meta": {
    "total_count": 1250,
    "limit": 10,
    "offset": 0,
    "page": 1,
    "page_size": 10,
    "total_pages": 125,
    "timestamp": "2026-05-19T12:00:00Z"
  }
}
```

### Pagination Parameters

All list endpoints support:

```
GET /api/v1/projects/{project_id}/entities?limit=20&offset=40&sort=-created_at
```

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| limit | integer | 20 | 100 | Items per page |
| offset | integer | 0 | - | Pagination offset |
| sort | string | -created_at | - | Sort field (prefix with - for desc) |
| filter | string | - | - | Filter expression |
| search | string | - | - | Full-text search query |

---

## Authentication Endpoints

### Login

```
POST /auth/login
Content-Type: application/json
```

**Request**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error (401 Unauthorized)**
```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid username or password"
  }
}
```

---

### Refresh Token

```
POST /auth/refresh
Content-Type: application/json
```

**Request**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### Validate Token

```
POST /auth/validate
Authorization: Bearer {token}
```

**Response (200 OK)**
```json
{
  "valid": true,
  "user_id": "user_123",
  "username": "admin",
  "scopes": ["admin"],
  "expires_in": 1234
}
```

---

### Get Current User Info

```
GET /auth/me
Authorization: Bearer {token}
```

**Response (200 OK)**
```json
{
  "user_id": "user_123",
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "scopes": ["admin"],
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

## Projects Management

### List Projects

```
GET /projects
Authorization: Bearer {token} (production only)
```

**Query Parameters**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| limit | integer | 20 | Items per page |
| offset | integer | 0 | Pagination offset |
| sort | string | -created_at | Sort field |

**Example**
```bash
curl 'http://localhost:8080/api/v1/projects?limit=10&offset=0'
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": "proj_001",
      "name": "Operation Midnight",
      "safe_name": "operation_midnight",
      "description": "Active investigation",
      "created_at": "2026-01-15T10:30:00Z",
      "entity_count": 1250,
      "relationship_count": 3450,
      "orphan_data_count": 45
    }
  ],
  "meta": {
    "total_count": 42,
    "limit": 10,
    "offset": 0,
    "total_pages": 5
  }
}
```

---

### Create Project

```
POST /projects
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "name": "Investigation 2026-05",
  "description": "May threat intelligence"
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "id": "proj_abc123",
    "name": "Investigation 2026-05",
    "safe_name": "investigation_2026_05",
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

**Error (400 Bad Request)**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Project name is required",
    "details": {
      "field": "name",
      "constraint": "required"
    }
  }
}
```

---

### Get Project

```
GET /projects/{project_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "proj_001",
    "name": "Operation Midnight",
    "description": "Active investigation",
    "created_at": "2026-01-15T10:30:00Z",
    "entity_count": 1250,
    "relationship_count": 3450,
    "orphan_data_count": 45,
    "statistics": {
      "entities_by_type": {
        "Person": 800,
        "Organization": 250,
        "Platform": 150,
        "Location": 50
      }
    }
  }
}
```

---

### Update Project

```
PUT /projects/{project_id}
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "name": "Updated Project Name",
  "description": "Updated description"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "proj_001",
    "name": "Updated Project Name",
    "description": "Updated description"
  }
}
```

---

### Delete Project

```
DELETE /projects/{project_id}
Authorization: Bearer {token} (production only)
```

**Response (204 No Content)**
```
(empty response body)
```

---

## Entities Management

### List Entities

```
GET /projects/{project_id}/entities
Authorization: Bearer {token} (production only)
```

**Query Parameters**
| Name | Type | Description |
|------|------|-------------|
| limit | integer | Items per page (default 20, max 100) |
| offset | integer | Pagination offset |
| type | string | Filter by entity type (Person, Organization, etc.) |
| search | string | Full-text search query |
| sort | string | Sort field (e.g., -created_at, name) |

**Example**
```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/entities?limit=20&type=Person&search=john'
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": "ent_001",
      "name": "John Doe",
      "type": "Person",
      "metadata": {
        "aliases": ["J. Doe", "JD"],
        "locations": ["New York", "Los Angeles"]
      },
      "created_at": "2026-01-15T10:30:00Z",
      "updated_at": "2026-05-19T12:00:00Z"
    }
  ],
  "meta": {
    "total_count": 1250,
    "limit": 20,
    "offset": 0
  }
}
```

---

### Create Entity

```
POST /projects/{project_id}/entities
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "name": "John Doe",
  "type": "Person",
  "metadata": {
    "aliases": ["J. Doe"],
    "email": "john@example.com",
    "phone": "+1-555-0100"
  }
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "id": "ent_abc123",
    "name": "John Doe",
    "type": "Person",
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### Get Entity

```
GET /projects/{project_id}/entities/{entity_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "ent_001",
    "name": "John Doe",
    "type": "Person",
    "metadata": {
      "aliases": ["J. Doe"],
      "email": "john@example.com",
      "phone": "+1-555-0100",
      "bio": "Senior investigator"
    },
    "created_at": "2026-01-15T10:30:00Z",
    "updated_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### Update Entity

```
PUT /projects/{project_id}/entities/{entity_id}
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "name": "John Smith Doe",
  "metadata": {
    "aliases": ["J. Doe", "JSD"],
    "email": "john.doe@example.com"
  }
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "ent_001",
    "name": "John Smith Doe",
    "updated_at": "2026-05-19T12:05:00Z"
  }
}
```

---

### Delete Entity

```
DELETE /projects/{project_id}/entities/{entity_id}
Authorization: Bearer {token} (production only)
```

**Response (204 No Content)**
```
(empty response body)
```

---

## Relationships Management

### List Relationships

```
GET /projects/{project_id}/relationships
Authorization: Bearer {token} (production only)
```

**Query Parameters**
| Name | Type | Description |
|------|------|-------------|
| type | string | Filter by relationship type (e.g., KNOWS, WORKS_FOR) |
| limit | integer | Items per page |
| offset | integer | Pagination offset |

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": "rel_001",
      "source_id": "ent_001",
      "source_name": "John Doe",
      "target_id": "ent_002",
      "target_name": "Jane Smith",
      "type": "KNOWS",
      "properties": {
        "since": "2025-01-01",
        "strength": "strong"
      },
      "created_at": "2026-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "total_count": 3450
  }
}
```

---

### Create Relationship

```
POST /projects/{project_id}/relationships
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "source_id": "ent_001",
  "target_id": "ent_002",
  "type": "KNOWS",
  "properties": {
    "since": "2025-01-01",
    "strength": "strong"
  }
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "id": "rel_new123",
    "source_id": "ent_001",
    "target_id": "ent_002",
    "type": "KNOWS",
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### Get Relationship

```
GET /projects/{project_id}/relationships/{relationship_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "rel_001",
    "source_id": "ent_001",
    "source_name": "John Doe",
    "target_id": "ent_002",
    "target_name": "Jane Smith",
    "type": "KNOWS",
    "properties": {
      "since": "2025-01-01",
      "strength": "strong"
    },
    "created_at": "2026-01-15T10:30:00Z"
  }
}
```

---

### Update Relationship

```
PUT /projects/{project_id}/relationships/{relationship_id}
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "type": "CLOSE_KNOWS",
  "properties": {
    "since": "2024-01-01",
    "strength": "very_strong"
  }
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "id": "rel_001",
    "type": "CLOSE_KNOWS",
    "updated_at": "2026-05-19T12:05:00Z"
  }
}
```

---

### Delete Relationship

```
DELETE /projects/{project_id}/relationships/{relationship_id}
Authorization: Bearer {token} (production only)
```

**Response (204 No Content)**
```
(empty response body)
```

---

## Search Endpoints

### Advanced Search

```
POST /projects/{project_id}/search/advanced
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "query": "john email:*@example.com",
  "limit": 20,
  "offset": 0,
  "filters": {
    "type": "Person",
    "created_after": "2026-01-01T00:00:00Z"
  },
  "highlight": true
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": "ent_001",
      "name": "John Doe",
      "type": "Person",
      "score": 0.95,
      "highlights": {
        "name": "John Doe",
        "metadata": ["john@example.com"]
      }
    }
  ],
  "meta": {
    "total_count": 45,
    "query_time_ms": 28
  }
}
```

---

### Autocomplete

```
GET /projects/{project_id}/search/autocomplete?q={query}&limit={limit}
Authorization: Bearer {token} (production only)
```

**Query Parameters**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| q | string | - | Search query (min 1 char) |
| limit | integer | 10 | Max suggestions (max 50) |
| type | string | - | Filter by type (Person, Organization, etc.) |

**Example**
```bash
curl 'http://localhost:8080/api/v1/projects/proj_123/search/autocomplete?q=john&limit=10'
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "id": "ent_001",
      "name": "John Doe",
      "type": "Person"
    },
    {
      "id": "ent_002",
      "name": "John Smith",
      "type": "Person"
    }
  ]
}
```

---

## Export & Reports

### Export as JSON

```
GET /projects/{project_id}/export/json
Authorization: Bearer {token} (production only)
```

**Response (200 OK) - Content-Type: application/json**

Returns complete project data as JSON:
```json
{
  "project": {
    "id": "proj_001",
    "name": "Operation Midnight"
  },
  "entities": [...],
  "relationships": [...],
  "export_date": "2026-05-19T12:00:00Z"
}
```

---

### Export as CSV

```
GET /projects/{project_id}/export/csv
Authorization: Bearer {token} (production only)
```

**Response (200 OK) - Content-Type: text/csv**

Returns CSV data:
```
id,name,type,created_at
ent_001,John Doe,Person,2026-01-15T10:30:00Z
ent_002,Jane Smith,Person,2026-01-16T11:00:00Z
```

---

### Export as GraphML

```
GET /projects/{project_id}/export/graphml
Authorization: Bearer {token} (production only)
```

**Response (200 OK) - Content-Type: application/xml**

Returns GraphML format for graph visualization tools.

---

### Generate Report

```
POST /projects/{project_id}/reports
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "title": "Threat Assessment Report",
  "format": "pdf",
  "include_sections": [
    "summary",
    "entities",
    "relationships",
    "timeline",
    "statistics"
  ],
  "filters": {
    "type": "Person",
    "relationship_count_min": 5
  }
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "report_id": "rpt_123",
    "title": "Threat Assessment Report",
    "format": "pdf",
    "url": "/api/v1/projects/proj_001/reports/rpt_123/download",
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

---

## Webhooks

### Create Webhook

```
POST /projects/{project_id}/webhooks
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["entity.created", "entity.updated", "relationship.created"],
  "secret": "webhook_secret_key"
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "webhook_id": "wh_123",
    "url": "https://your-server.com/webhook",
    "events": ["entity.created", "entity.updated", "relationship.created"],
    "active": true,
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### List Webhooks

```
GET /projects/{project_id}/webhooks
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "webhook_id": "wh_123",
      "url": "https://your-server.com/webhook",
      "events": ["entity.created"],
      "active": true,
      "last_triggered": "2026-05-19T11:30:00Z"
    }
  ]
}
```

---

### Update Webhook

```
PUT /projects/{project_id}/webhooks/{webhook_id}
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "events": ["entity.created", "entity.updated", "entity.deleted"],
  "active": true
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "webhook_id": "wh_123",
    "events": ["entity.created", "entity.updated", "entity.deleted"]
  }
}
```

---

### Delete Webhook

```
DELETE /projects/{project_id}/webhooks/{webhook_id}
Authorization: Bearer {token} (production only)
```

**Response (204 No Content)**
```
(empty response body)
```

---

## WebSocket (Real-time)

### Connect to WebSocket

```
WS /projects/{project_id}/ws?token={jwt_token}
```

**Example (JavaScript)**
```javascript
const ws = new WebSocket('ws://localhost:8080/api/v1/projects/proj_123/ws?token=YOUR_JWT');

ws.onopen = () => {
  console.log('Connected to WebSocket');
  
  // Subscribe to entity updates
  ws.send(JSON.stringify({
    type: 'subscribe',
    event: 'entity.updated',
    filters: { type: 'Person' }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
  
  // Handle different message types
  switch(message.type) {
    case 'entity.created':
      console.log('New entity:', message.data);
      break;
    case 'entity.updated':
      console.log('Updated entity:', message.data);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from WebSocket');
};
```

**Available Events**:
- `entity.created`
- `entity.updated`
- `entity.deleted`
- `relationship.created`
- `relationship.updated`
- `relationship.deleted`
- `project.updated`
- `heartbeat`

---

## Analytics

### Record Search Event

```
POST /projects/{project_id}/analytics/search
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "query": "john email:*@example.com",
  "result_count": 42,
  "response_time_ms": 28
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "event_id": "evt_123",
    "recorded_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### Get Analytics Summary

```
GET /projects/{project_id}/analytics/summary
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "total_searches": 1250,
    "unique_queries": 480,
    "avg_response_time_ms": 42,
    "queries_with_zero_results": 15,
    "top_queries": [
      {
        "query": "john email:*@example.com",
        "count": 45,
        "avg_response_time_ms": 28
      }
    ]
  }
}
```

---

## Graph Analysis

### Find Shortest Path

```
GET /path/{entity1_id}/{entity2_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "path": [
      "ent_001",
      "ent_003",
      "ent_005",
      "ent_002"
    ],
    "distance": 3,
    "relationships": [
      {
        "from": "ent_001",
        "to": "ent_003",
        "type": "KNOWS"
      }
    ]
  }
}
```

---

### Get Centrality Metrics

```
GET /path/{entity_id}/centrality
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_001",
    "name": "John Doe",
    "betweenness_centrality": 0.45,
    "closeness_centrality": 0.78,
    "degree_centrality": 0.92,
    "importance_score": 0.71
  }
}
```

---

## Import/Export Data

### Import from CSV

```
POST /projects/{project_id}/import/csv
Content-Type: multipart/form-data
Authorization: Bearer {token} (production only)
```

**Request** (multipart/form-data)
```
file: <CSV file>
mapping: {"name_col": "Name", "type_col": "Type", "email_col": "Email"}
```

**Response (202 Accepted)**
```json
{
  "status": "success",
  "data": {
    "import_id": "imp_123",
    "status": "processing",
    "rows_queued": 1250,
    "url": "/api/v1/imports/imp_123"
  }
}
```

---

### Check Import Status

```
GET /imports/{import_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "import_id": "imp_123",
    "status": "completed",
    "total_rows": 1250,
    "imported_rows": 1245,
    "failed_rows": 5,
    "errors": [
      {
        "row": 10,
        "error": "Invalid email format"
      }
    ]
  }
}
```

---

## ML & Suggestions

### Get Entity Suggestions

```
GET /projects/{project_id}/entities/{entity_id}/suggestions
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_001",
    "suggestions": [
      {
        "suggestion_id": "sug_001",
        "type": "link",
        "target_entity_id": "ent_003",
        "confidence": 0.92,
        "reason": "Similar email pattern"
      },
      {
        "suggestion_id": "sug_002",
        "type": "relationship",
        "target_entity_id": "ent_005",
        "relationship_type": "KNOWS",
        "confidence": 0.78,
        "reason": "Co-occurrence in 5 documents"
      }
    ]
  }
}
```

---

### Accept Suggestion

```
POST /projects/{project_id}/suggestions/{suggestion_id}/accept
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "suggestion_id": "sug_001",
    "action": "link_created",
    "result_id": "ent_merged_123"
  }
}
```

---

## Cache Management

### Get Cache Stats

```
GET /cache/stats
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "total_keys": 12450,
    "memory_used_mb": 245,
    "hit_rate": 0.623,
    "eviction_count": 450,
    "backend": "redis",
    "ttl_average_seconds": 3600
  }
}
```

---

### Clear Cache

```
POST /cache/clear
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "keys_deleted": 12450
  }
}
```

---

## Deduplication

### Find Duplicate Entities

```
POST /projects/{project_id}/deduplication/find
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "entity_ids": ["ent_001", "ent_002", "ent_003"],
  "threshold": 0.85
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "duplicates": [
      {
        "entities": ["ent_001", "ent_003"],
        "similarity": 0.92,
        "reason": "Same email, similar names"
      }
    ]
  }
}
```

---

### Merge Entities

```
POST /projects/{project_id}/entities/merge
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "source_id": "ent_001",
  "target_id": "ent_003",
  "strategy": "merge_all_data"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "merged_entity_id": "ent_001",
    "deleted_entity_id": "ent_003",
    "relationships_updated": 25
  }
}
```

---

## Data Quality

### Score Entity Quality

```
POST /projects/{project_id}/data-quality/score
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "entity_id": "ent_001"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_001",
    "overall_score": 0.87,
    "completeness": 0.92,
    "accuracy": 0.85,
    "consistency": 0.79,
    "timeliness": 0.88,
    "recommendations": [
      "Add phone number for better completeness",
      "Verify email address with primary source"
    ]
  }
}
```

---

## Verification

### Verify Email

```
POST /projects/{project_id}/verify/email
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "email": "john@example.com"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "email": "john@example.com",
    "valid": true,
    "smtp_valid": true,
    "domain_valid": true,
    "disposable": false,
    "confidence": 0.99
  }
}
```

---

### Verify Crypto Address

```
POST /projects/{project_id}/verify/crypto
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "address": "1A1z7agoat2cC15tWjT3FWxLLzwGMuXpWH",
  "currency": "bitcoin"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "address": "1A1z7agoat2cC15tWjT3FWxLLzwGMuXpWH",
    "currency": "bitcoin",
    "valid": true,
    "balance": "2.5",
    "transaction_count": 125,
    "first_seen": "2020-01-15T10:30:00Z"
  }
}
```

---

## Audit Logging

### Get Audit Log

```
GET /projects/{project_id}/audit?limit=20&offset=0&type=entity.created
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "log_id": "log_001",
      "timestamp": "2026-05-19T12:00:00Z",
      "user_id": "user_123",
      "action": "entity.created",
      "resource_type": "entity",
      "resource_id": "ent_001",
      "changes": {
        "name": "John Doe",
        "type": "Person"
      }
    }
  ],
  "meta": {
    "total_count": 5420
  }
}
```

---

## Advanced Features

### Timeline Visualization

```
GET /projects/{project_id}/timeline/entity/{entity_id}
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "entity_id": "ent_001",
    "timeline": [
      {
        "date": "2025-01-15",
        "event": "Profile created",
        "count": 1
      },
      {
        "date": "2025-06-20",
        "event": "Email updated",
        "count": 1
      }
    ]
  }
}
```

---

### Cross-Project Entity Linking

```
POST /cross-project/link
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "source_project_id": "proj_001",
  "source_entity_id": "ent_001",
  "target_project_id": "proj_002",
  "target_entity_id": "ent_123"
}
```

**Response (201 Created)**
```json
{
  "status": "success",
  "data": {
    "link_id": "xpj_link_123",
    "created_at": "2026-05-19T12:00:00Z"
  }
}
```

---

### Platform Management

```
GET /platforms
Authorization: Bearer {token} (production only)
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": [
    {
      "platform_id": "plt_001",
      "name": "Twitter",
      "type": "social_media",
      "icon_url": "/icons/twitter.svg",
      "category": "Social Media"
    },
    {
      "platform_id": "plt_002",
      "name": "LinkedIn",
      "type": "professional",
      "icon_url": "/icons/linkedin.svg",
      "category": "Professional Network"
    }
  ]
}
```

---

### Browser Automation Integration

```
POST /browser/actions/screenshot
Content-Type: application/json
Authorization: Bearer {token} (production only)
```

**Request**
```json
{
  "url": "https://example.com/profile/john-doe",
  "full_page": true,
  "wait_for_selector": ".profile-loaded"
}
```

**Response (200 OK)**
```json
{
  "status": "success",
  "data": {
    "screenshot_url": "/api/v1/files/screenshot_123.png",
    "page_title": "John Doe - Example.com",
    "page_content": "..."
  }
}
```

---

## Common Patterns

### Pagination Pattern

```python
import requests

def paginate_all_entities(project_id, page_size=50):
    """Fetch all entities using pagination."""
    url = f"http://localhost:8080/api/v1/projects/{project_id}/entities"
    offset = 0
    
    while True:
        response = requests.get(url, params={
            'limit': page_size,
            'offset': offset
        })
        
        data = response.json()['data']
        if not data:
            break
        
        for item in data:
            yield item
        
        offset += page_size
```

---

### Error Handling Pattern

```python
def safe_api_call(url, method='GET', **kwargs):
    """Make API call with error handling."""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print(f"Rate limited, retry after {e.response.headers.get('Retry-After')}s")
        elif e.response.status_code == 401:
            print("Authentication failed")
        else:
            print(f"API error: {e.response.json()}")
    except Exception as e:
        print(f"Error: {e}")
```

---

### Batch Processing Pattern

```python
def batch_create_entities(project_id, entities, batch_size=100):
    """Create entities in batches to avoid rate limits."""
    url = f"http://localhost:8080/api/v1/projects/{project_id}/entities"
    
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i+batch_size]
        for entity in batch:
            response = requests.post(url, json=entity)
            if response.status_code == 201:
                print(f"Created entity {entity['name']}")
            elif response.status_code == 429:
                time.sleep(60)  # Wait and retry
```

---

## Examples

### Example 1: Complete Investigation Flow

```bash
# 1. Create a new project
PROJECT=$(curl -s -X POST http://localhost:8080/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Investigation 2026-05"}' | jq -r '.data.id')

echo "Created project: $PROJECT"

# 2. Add entities
ENTITY1=$(curl -s -X POST http://localhost:8080/api/v1/projects/$PROJECT/entities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "type": "Person",
    "metadata": {"email": "john@example.com"}
  }' | jq -r '.data.id')

ENTITY2=$(curl -s -X POST http://localhost:8080/api/v1/projects/$PROJECT/entities \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tech Corp",
    "type": "Organization",
    "metadata": {"website": "techcorp.com"}
  }' | jq -r '.data.id')

# 3. Create relationship
curl -s -X POST http://localhost:8080/api/v1/projects/$PROJECT/relationships \
  -H "Content-Type: application/json" \
  -d "{
    \"source_id\": \"$ENTITY1\",
    \"target_id\": \"$ENTITY2\",
    \"type\": \"WORKS_FOR\"
  }"

# 4. Search
curl -s "http://localhost:8080/api/v1/projects/$PROJECT/search/advanced" \
  -H "Content-Type: application/json" \
  -d '{"query": "john"}' | jq '.data'

# 5. Export
curl -s "http://localhost:8080/api/v1/projects/$PROJECT/export/json" > export.json
```

---

### Example 2: Python Client

```python
import requests
from typing import List, Dict

class BassetHoundClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}' if token else None
        }
    
    def list_projects(self) -> List[Dict]:
        """Get all projects."""
        response = requests.get(
            f'{self.base_url}/projects',
            headers=self.headers
        )
        return response.json()['data']
    
    def create_entity(self, project_id: str, name: str, entity_type: str) -> Dict:
        """Create an entity."""
        response = requests.post(
            f'{self.base_url}/projects/{project_id}/entities',
            headers=self.headers,
            json={'name': name, 'type': entity_type}
        )
        return response.json()['data']
    
    def search(self, project_id: str, query: str) -> List[Dict]:
        """Search entities."""
        response = requests.post(
            f'{self.base_url}/projects/{project_id}/search/advanced',
            headers=self.headers,
            json={'query': query}
        )
        return response.json()['data']

# Usage
client = BassetHoundClient('http://localhost:8080/api/v1')
projects = client.list_projects()
print(f"Found {len(projects)} projects")
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Missing/invalid token | Check token in Authorization header |
| 404 Not Found | Wrong endpoint or ID | Verify path and use /projects to list IDs |
| 429 Rate Limited | Too many requests | Implement backoff, check X-RateLimit-Remaining |
| 500 Server Error | Internal error | Check /health endpoint, review logs |
| 504 Timeout | Request >30s | Simplify query or use pagination |
| Empty response | Query returned 0 results | Verify search parameters and filters |

---

### Debug Mode

Enable detailed error messages:

```bash
curl -v http://localhost:8080/api/v1/projects \
  -H "X-Debug: true"
```

---

### Performance Issues

1. **Check cache hit rate**: `GET /cache/stats`
2. **Monitor query time**: Search analytics show query performance
3. **Review connection pool**: `GET /health` shows pool status
4. **Check database**: `GET /health` shows Neo4j latency

---

### Getting Help

- API Documentation: `/docs` (Swagger UI)
- Alternative docs: `/redoc` (ReDoc)
- OpenAPI spec: `/openapi.json`
- Status: `/health` (service health)
- Contact: support@basset-hound.com

---

**Last Updated**: 2026-05-19  
**Version**: 3.0.0  
**Status**: Production Ready

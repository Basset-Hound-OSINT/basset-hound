# Security Gaps to Fix - Phase 8 Production Deployment

**Priority:** BLOCKING
**Date Identified:** 2026-05-19
**Impact:** Medium to Critical Security Issues
**Estimated Total Fix Time:** 1 hour

---

## CRITICAL GAPS

### Gap #1: Missing Authentication on 11 Export Endpoints

**Severity:** CRITICAL ⚠️⚠️⚠️
**Impact:** Unauthorized data export (PII, investigation data, encrypted dumps)
**CVSS Score:** 7.5 (High - Information Disclosure)
**Affected Endpoints:** 11 total

**Files Affected:**
- `/home/devel/basset-hound/api/routers/export.py`

**Issue Description:**
All export endpoints allow unauthenticated access. This means:
- Anyone can download project graphs (GraphML)
- Anyone can export entity data (CSV/JSON)
- Anyone can export location data (GeoJSON)
- Anyone can export reports (PDF, HTML, Markdown, DOCX)
- **CRITICAL:** Anyone can download encrypted database dumps containing ALL data

**Affected Endpoints (11):**
1. `POST /projects/{project_safe_name}/export/report` (lines 300-403)
2. `GET /projects/{project_safe_name}/export/summary/{format}` (lines 406-466)
3. `GET /projects/{project_safe_name}/entities/{entity_id}/export/{format}` (lines 480-546)
4. `GET /projects/{project_safe_name}/export/graphml` (lines 578-617)
5. `GET /projects/{project_safe_name}/export/entities/csv` (lines 620-674)
6. `GET /projects/{project_safe_name}/export/entities/json` (lines 677-731)
7. `GET /projects/{project_safe_name}/export/locations/geojson` (lines 734-779)
8. `POST /projects/{project_safe_name}/export/report-formats` (lines 782-874)
9. **`GET /projects/{project_safe_name}/export/database-dump`** (lines 877-958) ⚠️⚠️⚠️ MOST CRITICAL
10. `POST /export/report` (via ReportExportService)
11. `GET /export/templates` (acceptable - metadata only)

**Current Code Example (INSECURE):**
```python
# Line 590-603
@router.get("/graphml", ...)
async def export_graphml(
    project_safe_name: str,
    neo4j_handler=Depends(get_neo4j_handler)  # ONLY dependency
):
    # NO AUTHENTICATION CHECK
    # ANY USER CAN ACCESS
```

**Required Fix:**
```python
# Add authentication dependency
from api.auth.dependencies import CurrentUser, get_current_user

@router.get("/graphml", ...)
async def export_graphml(
    project_safe_name: str,
    current_user: CurrentUser = Depends(get_current_user),  # ADD THIS
    neo4j_handler=Depends(get_neo4j_handler)
):
    # Now only authenticated users can access
    # TODO: Add project membership check
```

**Fix Scope:**
- Add `current_user: CurrentUser = Depends(get_current_user)` parameter to all 9 export endpoints
- Optional for `GET /export/templates` (metadata only)

**Fix Time:** 30 minutes
**Complexity:** LOW (copy/paste pattern)
**Testing:** Manual - try accessing endpoints with/without auth header

---

### Gap #2: No Project Ownership Verification on Export Endpoints

**Severity:** HIGH ⚠️⚠️
**Impact:** User A can export User B's projects
**CVSS Score:** 6.5 (Medium - Information Disclosure)
**Affected Endpoints:** 9 export endpoints

**Issue Description:**
Even if authentication is added, no project ownership check is performed.
- Authenticated User A can export User B's projects
- No access control beyond "you must be logged in"

**Current Code Example:**
```python
# After adding auth, this is still vulnerable:
async def export_graphml(
    project_safe_name: str,
    current_user: CurrentUser = Depends(get_current_user),  # NEW
    neo4j_handler=Depends(get_neo4j_handler)
):
    service = ExportService(neo4j_handler)
    graphml_data = service.export_graph_graphml(project_safe_name)
    # NO CHECK: Does current_user own this project?
    # VULNERABLE: Any authenticated user can export any project
```

**Required Fix:**
```python
# Add project ownership check
async def export_graphml(
    project_safe_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    neo4j_handler=Depends(get_neo4j_handler)
):
    # Verify user has access to project
    project = neo4j_handler.get_project(project_safe_name)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # TODO: Implement RBAC check
    # if current_user.user_id not in project.members:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    # NOW safe to export
    service = ExportService(neo4j_handler)
    graphml_data = service.export_graph_graphml(project_safe_name)
```

**Fix Time:** 45 minutes
**Complexity:** MEDIUM (requires project membership lookup)
**Blocking:** YES - Cannot deploy without this fix
**Testing:** Manual - create 2 users, verify cross-project export is blocked

---

## MEDIUM-SEVERITY GAPS

### Gap #3: Hardcoded Default Secret Key

**Severity:** MEDIUM ⚠️
**Impact:** If JWT_SECRET_KEY not set, all tokens use weak default secret
**CVSS Score:** 5.0 (Medium - Authentication Weakness)
**File:** `/home/devel/basset-hound/api/auth/jwt.py` (lines 47, 93)

**Issue Description:**
```python
# api/auth/jwt.py line 47
"secret_key": os.getenv("JWT_SECRET_KEY", 
    "development-secret-key-change-in-production"),  # WEAK DEFAULT

# Also in api/config.py line 125
secret_key: str = Field(
    default="development-secret-key-change-in-production",
    description="Secret key for JWT token signing..."
)
```

**Risk:**
- Developers might forget to set JWT_SECRET_KEY
- Token validation could use weak default secret
- Tokens could be forged if defaults are known

**Required Fix:**

Option A (Strict - Recommended):
```python
# api/auth/jwt.py
def get_jwt_config():
    config_secret = os.getenv("JWT_SECRET_KEY")
    if not config_secret:
        raise ValueError(
            "JWT_SECRET_KEY environment variable must be set. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return {
        "secret_key": config_secret,
        ...
    }
```

Option B (Warn but Allow):
```python
# api/auth/jwt.py
def get_jwt_config():
    config_secret = os.getenv("JWT_SECRET_KEY")
    if not config_secret:
        logger.warning(
            "WARNING: JWT_SECRET_KEY not set. Using development default. "
            "NEVER use default in production!"
        )
        config_secret = secrets.token_urlsafe(32)
    return {
        "secret_key": config_secret,
        ...
    }
```

**Fix Time:** 15 minutes
**Complexity:** LOW
**Blocking:** NO (medium issue)
**Testing:** Unit test to verify error is raised if env var not set

---

### Gap #4: Permissive CORS Configuration for Development

**Severity:** MEDIUM ⚠️
**Impact:** Any origin can access the API in development
**File:** `/home/devel/basset-hound/.env`

**Current Configuration:**
```ini
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
```

**Problem:**
- Development default allows all origins
- If deployed to production with these settings, CORS is not restricted
- Opens API to cross-origin attacks from any malicious site

**Required Fix:**

**Development .env (current - acceptable):**
```ini
CORS_ORIGINS=localhost:3000,localhost:8080
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type
```

**Production .env (MUST set):**
```ini
CORS_ORIGINS=https://app.basset-hound.io,https://admin.basset-hound.io
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Authorization,Content-Type
```

**Fix Time:** 10 minutes
**Complexity:** LOW
**Blocking:** NO (development acceptable)
**Testing:** curl with different origins to verify blocking

---

## LOW-SEVERITY GAPS

### Gap #5: Error Messages Leak Context Information

**Severity:** LOW ⚠️
**Impact:** Error messages could reveal system internals to attackers
**File:** Multiple routers

**Examples:**
```python
# From ml_analytics.py line 237
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail=f"Feature extraction failed: {str(e)}"  # Exception details exposed
)

# From graph_format.py line 365
detail=f"Conversion error: {str(e)}"  # Could reveal internal implementation
```

**Should Be:**
```python
# Generic message to client
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Feature extraction failed. Please check request parameters."
)

# Full details go to logs (already done)
logger.error(f"Feature extraction failed: {str(e)}")
```

**Fix Time:** 30 minutes
**Complexity:** LOW (audit + fix)
**Blocking:** NO (low severity)
**Testing:** Check error responses don't contain stack traces or implementation details

---

## SUMMARY TABLE

| Gap ID | Title | Severity | Fix Time | Blocking | Status |
|--------|-------|----------|----------|----------|--------|
| #1 | Missing auth on exports | CRITICAL | 30 min | YES | TO-DO |
| #2 | No project ownership check | HIGH | 45 min | YES | TO-DO |
| #3 | Hardcoded secret key default | MEDIUM | 15 min | NO | TO-DO |
| #4 | Permissive CORS config | MEDIUM | 10 min | NO | TO-DO |
| #5 | Error message leakage | LOW | 30 min | NO | TO-DO |

**Total Fix Time (Blocking):** 75 minutes
**Total Fix Time (All):** 130 minutes (~2 hours)

---

## DEPLOYMENT BLOCKING CHECKLIST

Before deploying Phase 8 to production, must complete:

- [ ] **CRITICAL:** Add `current_user: CurrentUser = Depends(get_current_user)` to all 11 export endpoints
- [ ] **CRITICAL:** Add project membership verification to export endpoints
- [ ] **HIGH:** Verify no cross-user data access is possible
- [ ] **HIGH:** Test export endpoints with different users
- [ ] **MEDIUM:** Set strong JWT_SECRET_KEY in production environment
- [ ] **MEDIUM:** Configure CORS_ORIGINS for production domain
- [ ] **MEDIUM:** Enable AUTH_ENABLED=true
- [ ] **LOW:** Audit error messages don't expose internals
- [ ] **LOW:** Run security scan for any remaining hardcoded values

---

## TESTING PLAN

### Test Case 1: Export Without Authentication (Should Fail)
```bash
# Should return 401 Unauthorized
curl http://localhost:8000/projects/test/export/graphml

# Expected response: {"detail": "Missing authentication credentials"}
```

### Test Case 2: Export With Authentication (Should Succeed)
```bash
# Get token first
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPassword123!"}' \
  | jq -r '.access_token')

# Export should succeed
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/projects/test/export/graphml
```

### Test Case 3: Cross-Project Export (Should Fail)
```bash
# User A tries to export User B's project
# Should return 403 Forbidden after project ownership check added
curl -H "Authorization: Bearer USER_A_TOKEN" \
  http://localhost:8000/projects/user-b-project/export/graphml

# Expected response: {"detail": "Access denied"}
```

---

## ROLL-FORWARD PLAN

If issues discovered during testing:

1. **Rollback:** Revert export.py changes if auth causes issues
2. **Hotfix:** Add auth to only most critical endpoint (database-dump)
3. **Gradual:** Add auth to other endpoints in phases
4. **Monitor:** Watch logs for export failures after fix

---

**Document Status:** READY FOR IMPLEMENTATION
**Last Updated:** 2026-05-19
**Reviewed By:** Claude Security Audit Tool


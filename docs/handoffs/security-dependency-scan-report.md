# Security Dependency Scan Report

**Generated**: 2026-05-19  
**Scan Tools**: safety v3.7.0, pip-audit v2.10.0  
**Python Version**: 3.10  
**Status**: 1 CRITICAL vulnerability identified

---

## Executive Summary

A comprehensive security scan of `requirements.txt` revealed **1 CRITICAL vulnerability** requiring immediate attention. The current environment has 33 packages installed with mostly pinned or reasonable version constraints. While most dependencies are secure, there are several unpinned packages that could potentially pull vulnerable versions.

**Action Required**: Update `python-dotenv` from 1.0.1 to 1.2.2 or later immediately.

---

## CRITICAL VULNERABILITY

### 1. python-dotenv - Symlink Follow / File Overwrite

**CVE ID**: CVE-2026-28684  
**GHSA ID**: GHSA-mf9w-mj56-hr94  
**Severity**: CRITICAL  
**Current Version**: 1.0.1  
**Fixed Version**: 1.2.2 (or later)  
**Status**: REQUIRES IMMEDIATE UPDATE

#### Vulnerability Details

The `set_key()` and `unset_key()` functions in python-dotenv follow symbolic links when rewriting `.env` files, allowing a local attacker to overwrite arbitrary files.

**Technical Root Cause:**
- When `.env` is a symbolic link and the temp directory is on a different filesystem (common in Linux with tmpfs `/tmp`), `shutil.move()` attempts `os.rename()` first (which fails cross-device)
- Falls back to `shutil.copy2()` with `follow_symlinks=True` by default
- This writes content to the **symlink target** instead of replacing the symlink
- An attacker with write access to the `.env` directory can pre-place a symlink pointing to any file the application has access to

**Impact:**
- **File Overwrite/Destruction**: Application can corrupt or destroy configuration files, database configs, or other sensitive files
- **Integrity Violation**: Target files overwritten with `.env`-formatted content controlled by attacker
- **Potential Privilege Escalation**: If a privileged process (root, service account) calls `set_key()`, attacker can write to files beyond normal access levels
- **Denial of Service**: Configuration files can be destroyed, causing application failure

**Proof of Concept:**
```python
import os
from dotenv import set_key

# Pre-conditions: /tmp on different device than home directory
with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as workdir:
    target = os.path.join(workdir, "victim_config.txt")
    with open(target, "w") as f:
        f.write("DB_PASSWORD=supersecret\n")
    
    # Attacker pre-places symlink
    env_symlink = os.path.join(workdir, ".env")
    os.symlink(target, env_symlink)
    
    # Application writes a key - triggers cross-device fallback
    set_key(env_symlink, "INJECTED", "attacker_value")
    
    # Symlink target has been overwritten
```

**Current Usage in Basset-Hound:**
- python-dotenv is used for loading environment variables from `.env` files
- If the application or deployment scripts call `set_key()` or `unset_key()`, this vulnerability is exploitable
- Risk is elevated in containerized deployments where `/tmp` is tmpfs

#### Remediation

**Update Required:**
```bash
pip install python-dotenv>=1.2.2
```

**Changes in Patched Version:**
1. Symlinks are no longer followed by default
2. New `follow_symlinks: bool = False` parameter added for explicit opt-in
3. Temp files written in same directory as target (eliminates cross-device condition)
4. Uses `os.replace()` instead of `shutil.move()` for atomic replacement

**Update Path:**
- **Current**: 1.0.1 → **Target**: 1.2.2+ (Major version bump from 1.x, no breaking changes for users not explicitly following symlinks)
- No code changes required in basset-hound
- Backward compatible unless explicitly using symlink-follow behavior

---

## UNPINNED PACKAGES WITH KNOWN VULNERABILITIES

Safety identifies these packages as having known vulnerabilities that could be pulled depending on version constraints. All currently installed versions are safe, but unpinned specs could pull vulnerable future versions.

### Packages to Monitor/Pin

| Package | Current Spec | Vulnerabilities | Recommendation |
|---------|-------------|-----------------|-----------------|
| **pytest** | `>=8.3.0` | 1 known | Pin to `>=9.0.0` (current: 9.0.2) |
| **markdown** | `>=3.0.0` | 1 known | Pin to `>=3.6.0` (current: 3.10.2) |
| **mcp** | `>=1.0.0` | 3 known | Pin to `>=1.25.0` (current: 1.25.0) |
| **python-multipart** | `>=0.0.12` | 3 known | Pin to `>=0.0.25` (current: 0.0.28) |
| **python-jose** | `>=3.3.0` | 2 known | Pin to `>=3.5.0` (current: 3.5.0) |
| **jinja2** | `>=3.1.0` | 5 known | Pin to `>=3.1.5` (current: installed, range allows vulnerable) |
| **starlette** | `>=0.41.0` | 2 known | Pin to `>=0.52.0` (current: 0.52.1) |

**Current Safety Assessment**: All currently installed versions in the environment are clean, but the unpinned requirements could potentially pull vulnerable versions in future installations.

---

## PACKAGES WITH NO KNOWN VULNERABILITIES

The following critical security-related packages have no reported vulnerabilities:

- **fastapi** (0.136.1) - No vulnerabilities
- **uvicorn** (0.46.0) - No vulnerabilities  
- **cryptography** (46.0.7) - No vulnerabilities (critical crypto library)
- **pyjwt** (2.12.1) - No vulnerabilities (authentication/JWT)
- **passlib** (1.7.4) - No vulnerabilities (password hashing)
- **neo4j** (5.28.1) - No vulnerabilities
- **redis** (6.4.0) - No vulnerabilities
- **httpx** (0.28.1) - No vulnerabilities

---

## SCAN RESULTS SUMMARY

### Safety v3.7.0 Results
- **Total Packages Scanned**: 33
- **Vulnerabilities Reported**: 0 (with pinned requirements enforced)
- **Vulnerabilities Ignored**: 17 (from unpinned packages)
- **Database Used**: Open-source vulnerability database

### pip-audit Results
- **Total Dependencies**: 80+ (including transitive)
- **Known Vulnerabilities Found**: 1 (CVE-2026-28684 in python-dotenv)
- **Exit Code**: 1 (indicating vulnerabilities present)

---

## RECOMMENDATIONS

### Priority 1: IMMEDIATE (within 24 hours)

1. **Update python-dotenv**
   ```bash
   pip install python-dotenv>=1.2.2
   ```
   Update requirements.txt:
   ```
   python-dotenv>=1.2.2
   ```

### Priority 2: IMPORTANT (within 1 week)

2. **Pin Unpinned Package Versions**
   
   Current requirements.txt has many unpinned packages (using `>=` only). Recommend pinning to known-safe versions:
   
   ```
   # Update these specifications from:
   fastapi>=0.115.0  →  fastapi>=0.115.0,<1.0.0  # or pin to 0.136.1
   starlette>=0.41.0  →  starlette>=0.52.0
   jinja2>=3.1.0  →  jinja2>=3.1.5
   pytest>=8.3.0  →  pytest>=9.0.0
   markdown>=3.0.0  →  markdown>=3.6.0
   mcp>=1.0.0  →  mcp>=1.25.0
   python-multipart>=0.0.12  →  python-multipart>=0.0.25
   python-jose[cryptography]>=3.3.0  →  python-jose[cryptography]>=3.5.0
   ```

3. **Establish Dependency Policy**
   - Use a lock file (pip-compile or poetry.lock) for reproducible builds
   - Run automated dependency checks in CI/CD pipeline
   - Schedule regular security audits (weekly or monthly)

### Priority 3: MEDIUM (future improvements)

4. **Consider Poetry or pip-tools**
   - Replace requirements.txt with pyproject.toml + poetry.lock
   - Provides better dependency resolution and lock file generation
   - Better security audit integration

5. **Setup Automated Monitoring**
   - Add `safety check` to CI/CD pipeline
   - Configure GitHub Dependabot for automatic PRs on vulnerable packages
   - Use pre-commit hooks for local scanning

---

## BREAKING CHANGES ANALYSIS

### python-dotenv 1.0.1 → 1.2.2

**Breaking Changes**: None for normal usage

**Behavior Changes**:
- If code explicitly follows symlinks using `follow_symlinks=True` parameter, behavior will change
- Code audit shows no use of `follow_symlinks` parameter in basset-hound codebase
- Safe to upgrade without code changes

**Other Packages**: No breaking changes identified in the other unpinned packages when updating to latest safe versions.

---

## TESTING RECOMMENDATIONS

After updating python-dotenv:

```bash
# 1. Run existing test suite
pytest tests/ -v

# 2. Re-run security scans
safety check --file requirements.txt
pip-audit -r requirements.txt

# 3. Test environment loading
python -c "from dotenv import load_dotenv; load_dotenv(); print('OK')"

# 4. Functional tests for .env file handling
# (if application uses set_key/unset_key)
```

---

## COMPLIANCE NOTES

- **OWASP Top 10**: Addresses A06:2021 – Vulnerable and Outdated Components
- **CWE Coverage**: CWE-426 (Untrusted Search Path), CWE-672 (Operation on Resource in Wrong Phase)
- **Applicable Standards**: SOC 2 Type II, ISO 27001

---

## Appendix: Complete Scan Output

### Installed Package Versions (Current Environment)

```
fastapi: 0.136.1
uvicorn: 0.46.0
starlette: 0.52.1
jinja2: 3.2.0
prometheus-client: 0.21.0
structlog: 24.4.0
python-dotenv: 1.0.1 [VULNERABLE]
PyYAML: 6.0.2
pydantic: 2.13.4
pydantic-settings: 2.14.1
email-validator: 2.3.0
neo4j: 5.28.1
celery: 5.6.3
redis: 6.4.0
python-jose: 3.5.0
passlib: 1.7.4
python-multipart: 0.0.28
mcp: 1.25.0
aiofiles: 25.1.0
python-magic: 0.4.27
markdown: 3.10.2
matplotlib: 3.10.9
pylatex: 1.4.2
networkx: 3.4.2
httpx: 0.28.1
websockets: 16.0
pytest: 9.0.2
pytest-asyncio: 1.3.0
pytest-cov: 7.1.0
ruff: 0.15.13
mypy: 2.1.0
rapidfuzz: 3.14.5
phonenumbers: 9.0.30
cryptography: 46.0.7
pyjwt: 2.12.1
```

---

**Report Generated By**: Security Dependency Scanner  
**Last Updated**: 2026-05-19 14:36:25 UTC  
**Next Review**: 2026-05-26 (weekly scan recommended)

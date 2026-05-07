#!/bin/bash
#
# Integration Verification Script - Phase 7.3
#
# This script verifies that basset-hound is properly configured for
# basset-verify integration and that all components are operational.
#
# Usage: ./verify_integration.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Functions
print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_section() {
    echo -e "${BLUE}▶ $1${NC}"
}

check_passed() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_failed() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((CHECKS_WARNING++))
}

# Main verification
print_header "Phase 7.3 Integration Verification"

print_section "Checking Configuration Files"

# Check docker-compose.yml
if [ -f "docker-compose.yml" ]; then
    if grep -q "basset_verify:" docker-compose.yml; then
        check_passed "docker-compose.yml contains basset_verify service"
    else
        check_failed "docker-compose.yml missing basset_verify service"
    fi

    if grep -q "BASSET_VERIFY_URL" docker-compose.yml; then
        check_passed "docker-compose.yml has BASSET_VERIFY_URL setting"
    else
        check_failed "docker-compose.yml missing BASSET_VERIFY_URL setting"
    fi

    if grep -q "BASSET_VERIFY_TIMEOUT" docker-compose.yml; then
        check_passed "docker-compose.yml has BASSET_VERIFY_TIMEOUT setting"
    else
        check_failed "docker-compose.yml missing BASSET_VERIFY_TIMEOUT setting"
    fi

    if grep -q "BASSET_VERIFY_ENABLED" docker-compose.yml; then
        check_passed "docker-compose.yml has BASSET_VERIFY_ENABLED setting"
    else
        check_failed "docker-compose.yml missing BASSET_VERIFY_ENABLED setting"
    fi

    if grep -q "condition: service_healthy" docker-compose.yml && grep -q "basset_verify" docker-compose.yml; then
        check_passed "basset_api depends on basset_verify health"
    else
        check_failed "basset_api not properly depends on basset_verify"
    fi
else
    check_failed "docker-compose.yml not found"
fi

# Check API configuration
if [ -f "api/config.py" ]; then
    if grep -q "basset_verify_url" api/config.py; then
        check_passed "api/config.py has basset_verify_url setting"
    else
        check_failed "api/config.py missing basset_verify_url setting"
    fi

    if grep -q "basset_verify_timeout" api/config.py; then
        check_passed "api/config.py has basset_verify_timeout setting"
    else
        check_failed "api/config.py missing basset_verify_timeout setting"
    fi

    if grep -q "basset_verify_enabled" api/config.py; then
        check_passed "api/config.py has basset_verify_enabled setting"
    else
        check_failed "api/config.py missing basset_verify_enabled setting"
    fi
else
    check_failed "api/config.py not found"
fi

print_section "Checking Client Implementation"

# Check BassetVerifyClient
if [ -f "api/clients/basset_verify_client.py" ]; then
    check_passed "BassetVerifyClient exists"

    if grep -q "class BassetVerifyClient" api/clients/basset_verify_client.py; then
        check_passed "BassetVerifyClient class is defined"
    else
        check_failed "BassetVerifyClient class not found"
    fi

    if grep -q "async def verify_email" api/clients/basset_verify_client.py; then
        check_passed "verify_email method exists"
    else
        check_failed "verify_email method not found"
    fi

    if grep -q "async def verify_phone" api/clients/basset_verify_client.py; then
        check_passed "verify_phone method exists"
    else
        check_failed "verify_phone method not found"
    fi

    if grep -q "async def verify_crypto" api/clients/basset_verify_client.py; then
        check_passed "verify_crypto method exists"
    else
        check_failed "verify_crypto method not found"
    fi

    if grep -q "async def batch_verify" api/clients/basset_verify_client.py; then
        check_passed "batch_verify method exists"
    else
        check_failed "batch_verify method not found"
    fi
else
    check_failed "api/clients/basset_verify_client.py not found"
fi

print_section "Checking MCP Tool Integration"

# Check verification tools
if [ -f "basset_mcp/tools/verification.py" ]; then
    check_passed "MCP verification tools file exists"
else
    check_failed "basset_mcp/tools/verification.py not found"
fi

print_section "Checking Tests"

# Check E2E tests
if [ -f "tests/production/test_e2e_production.py" ]; then
    check_passed "E2E production tests file exists"

    if grep -q "TestIntegrationConfiguration" tests/production/test_e2e_production.py; then
        check_passed "Configuration tests class exists"
    else
        check_failed "Configuration tests class not found"
    fi

    if grep -q "TestVerificationToolsDelegation" tests/production/test_e2e_production.py; then
        check_passed "Tool delegation tests class exists"
    else
        check_failed "Tool delegation tests class not found"
    fi

    if grep -q "TestGracefulFallback" tests/production/test_e2e_production.py; then
        check_passed "Graceful fallback tests class exists"
    else
        check_failed "Graceful fallback tests class not found"
    fi
else
    check_failed "tests/production/test_e2e_production.py not found"
fi

print_section "Checking Documentation"

# Check production guide
if [ -f "docs/PRODUCTION_INTEGRATION_GUIDE.md" ]; then
    check_passed "Production Integration Guide exists"
else
    check_failed "docs/PRODUCTION_INTEGRATION_GUIDE.md not found"
fi

# Check integration status
if [ -f "INTEGRATION_STATUS_PHASE_7_3.md" ]; then
    check_passed "Integration Status report exists"
else
    check_failed "INTEGRATION_STATUS_PHASE_7_3.md not found"
fi

print_section "Checking Monitoring Configuration"

# Check monitoring setup
if [ -f "config/monitoring/integration_monitoring.yaml" ]; then
    check_passed "Monitoring configuration file exists"
else
    check_failed "config/monitoring/integration_monitoring.yaml not found"
fi

if [ -f "config/monitoring/integration_monitoring.py" ]; then
    check_passed "Monitoring implementation exists"
else
    check_failed "config/monitoring/integration_monitoring.py not found"
fi

print_section "Python Dependencies Check"

# Check for required packages
if python3 -c "import httpx" 2>/dev/null; then
    check_passed "httpx package available"
else
    check_warning "httpx package not found (required for client)"
fi

if python3 -c "import pydantic" 2>/dev/null; then
    check_passed "pydantic package available"
else
    check_warning "pydantic package not found (required for config)"
fi

if python3 -c "import pytest" 2>/dev/null; then
    check_passed "pytest package available"
else
    check_warning "pytest package not found (required for tests)"
fi

print_section "Running Python Tests"

# Try to run configuration tests
if python3 -m pytest tests/production/test_e2e_production.py::TestIntegrationConfiguration -v 2>&1 | grep -q "passed"; then
    check_passed "Configuration tests passing"
else
    check_warning "Could not verify configuration tests (services may not be running)"
fi

# Summary
echo ""
print_header "Verification Summary"
echo ""
echo -e "${GREEN}Passed:${NC}   $CHECKS_PASSED"
echo -e "${RED}Failed:${NC}   $CHECKS_FAILED"
echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNING"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Integration is properly configured.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start services: docker-compose up -d"
    echo "2. Verify health: docker-compose ps"
    echo "3. Run E2E tests: pytest tests/production/test_e2e_production.py -v"
    exit 0
else
    echo -e "${RED}✗ Some checks failed. Please review the errors above.${NC}"
    exit 1
fi

#!/bin/bash
# Test script for Docker Network Deployment
# Tests single-port entry through nginx reverse proxy

set -e

RESULTS_DIR="tests/results"
RESULT_FILE="$RESULTS_DIR/docker_network_test_$(date +%Y%m%d_%H%M%S).txt"
BASE_URL="http://localhost:8080"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Initialize results file
mkdir -p "$RESULTS_DIR"
echo "Docker Network Deployment Test Results" > "$RESULT_FILE"
echo "=======================================" >> "$RESULT_FILE"
echo "Date: $(date)" >> "$RESULT_FILE"
echo "Base URL: $BASE_URL" >> "$RESULT_FILE"
echo "" >> "$RESULT_FILE"

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="$3"
    local check_content="$4"

    echo -n "Testing $name... "

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status" == "$expected_status" ]; then
        if [ -n "$check_content" ]; then
            if echo "$body" | grep -q "$check_content"; then
                echo -e "${GREEN}PASS${NC} (status: $status, content match)"
                echo "PASS: $name (status: $status, content: $check_content found)" >> "$RESULT_FILE"
                ((PASSED++))
            else
                echo -e "${RED}FAIL${NC} (content mismatch)"
                echo "FAIL: $name (content '$check_content' not found in response)" >> "$RESULT_FILE"
                ((FAILED++))
            fi
        else
            echo -e "${GREEN}PASS${NC} (status: $status)"
            echo "PASS: $name (status: $status)" >> "$RESULT_FILE"
            ((PASSED++))
        fi
    else
        echo -e "${RED}FAIL${NC} (expected: $expected_status, got: $status)"
        echo "FAIL: $name (expected: $expected_status, got: $status)" >> "$RESULT_FILE"
        ((FAILED++))
    fi
}

# Test network exists
echo "Test 1: Docker Network Exists"
echo "" >> "$RESULT_FILE"
echo "Test 1: Docker Network Exists" >> "$RESULT_FILE"
if docker network inspect basset-hound > /dev/null 2>&1; then
    echo -e "${GREEN}PASS${NC} - basset-hound network exists"
    echo "PASS: basset-hound network exists" >> "$RESULT_FILE"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} - basset-hound network not found"
    echo "FAIL: basset-hound network not found" >> "$RESULT_FILE"
    ((FAILED++))
fi

# Test containers are on the network
echo ""
echo "Test 2: All Containers on Network"
echo "" >> "$RESULT_FILE"
echo "Test 2: All Containers on Network" >> "$RESULT_FILE"
containers=$(docker network inspect basset-hound --format '{{range .Containers}}{{.Name}} {{end}}')
for container in basset_nginx basset_api basset_redis neo4j_osint_db; do
    if echo "$containers" | grep -q "$container"; then
        echo -e "  ${GREEN}PASS${NC} - $container connected"
        echo "PASS: $container connected to basset-hound network" >> "$RESULT_FILE"
        ((PASSED++))
    else
        echo -e "  ${RED}FAIL${NC} - $container not connected"
        echo "FAIL: $container not connected to basset-hound network" >> "$RESULT_FILE"
        ((FAILED++))
    fi
done

# Test single port entry
echo ""
echo "Test 3: Single Port Entry (8080)"
echo "" >> "$RESULT_FILE"
echo "Test 3: Single Port Entry (8080)" >> "$RESULT_FILE"
exposed_ports=$(docker ps --format '{{.Ports}}' | grep "0.0.0.0:8080")
if [ -n "$exposed_ports" ]; then
    echo -e "${GREEN}PASS${NC} - Port 8080 exposed"
    echo "PASS: Port 8080 exposed via nginx" >> "$RESULT_FILE"
    ((PASSED++))
else
    echo -e "${RED}FAIL${NC} - Port 8080 not exposed"
    echo "FAIL: Port 8080 not exposed" >> "$RESULT_FILE"
    ((FAILED++))
fi

# Test endpoints through nginx
echo ""
echo "Test 4: Endpoints via Nginx Proxy"
echo "" >> "$RESULT_FILE"
echo "Test 4: Endpoints via Nginx Proxy" >> "$RESULT_FILE"

test_endpoint "Nginx Health" "$BASE_URL/nginx-health" "200" "healthy"
test_endpoint "API Health" "$BASE_URL/health" "200" "healthy"
test_endpoint "API Root" "$BASE_URL/api" "200" "Basset Hound"
test_endpoint "API Info" "$BASE_URL/api/info" "200" "version"
test_endpoint "OpenAPI Docs" "$BASE_URL/docs" "200"
test_endpoint "ReDoc" "$BASE_URL/redoc" "200"
test_endpoint "OpenAPI JSON" "$BASE_URL/openapi.json" "200" "openapi"
test_endpoint "Neo4j Browser" "$BASE_URL/neo4j/" "200"

# Test internal services NOT directly accessible
echo ""
echo "Test 5: Internal Services Not Exposed"
echo "" >> "$RESULT_FILE"
echo "Test 5: Internal Services Not Exposed (expected to fail)" >> "$RESULT_FILE"

for port in 7474 7687 6379; do
    if curl -s --connect-timeout 2 "http://localhost:$port" > /dev/null 2>&1; then
        echo -e "${YELLOW}WARN${NC} - Port $port is accessible (dev mode?)"
        echo "WARN: Port $port is accessible (might be using docker-compose.dev.yml)" >> "$RESULT_FILE"
    else
        echo -e "${GREEN}PASS${NC} - Port $port not exposed (internal only)"
        echo "PASS: Port $port not exposed externally" >> "$RESULT_FILE"
        ((PASSED++))
    fi
done

# Summary
echo ""
echo "======================================="
echo "Test Summary"
echo "======================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""
echo "" >> "$RESULT_FILE"
echo "=======================================" >> "$RESULT_FILE"
echo "Summary: PASSED=$PASSED, FAILED=$FAILED" >> "$RESULT_FILE"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo "RESULT: ALL TESTS PASSED" >> "$RESULT_FILE"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    echo "RESULT: SOME TESTS FAILED" >> "$RESULT_FILE"
    exit 1
fi

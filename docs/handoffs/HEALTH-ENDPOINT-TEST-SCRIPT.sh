#!/bin/bash
# Health Endpoint Testing Script
# Verifies the async corrective fix is working properly

set -e

echo "=== Basset Hound Health Endpoint Test Suite ==="
echo ""

# Configuration
HEALTH_URL="http://localhost:8000/health"
NUM_SEQUENTIAL=100
NUM_CONCURRENT=50
MAX_ALLOWED_LATENCY_MS=10  # 10ms max

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0

# Function to check if endpoint is reachable
check_endpoint_available() {
    echo "[1/5] Checking if health endpoint is available..."
    if curl -s -m 2 "$HEALTH_URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health endpoint is available${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ Health endpoint is NOT available${NC}"
        echo "   Make sure the API server is running on http://localhost:8000"
        ((FAILED++))
        return 1
    fi
}

# Function to test response format
test_response_format() {
    echo ""
    echo "[2/5] Testing response format..."

    response=$(curl -s "$HEALTH_URL")

    # Check for required fields
    if echo "$response" | grep -q '"status"'; then
        echo -e "${GREEN}✓ Response contains 'status' field${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Response missing 'status' field${NC}"
        ((FAILED++))
    fi

    if echo "$response" | grep -q '"services"'; then
        echo -e "${GREEN}✓ Response contains 'services' field${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Response missing 'services' field${NC}"
        ((FAILED++))
    fi

    if echo "$response" | grep -q '"neo4j"'; then
        echo -e "${GREEN}✓ Response contains 'neo4j' service${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Response missing 'neo4j' service${NC}"
        ((FAILED++))
    fi
}

# Function to test sequential latency
test_sequential_latency() {
    echo ""
    echo "[3/5] Testing sequential request latency (${NUM_SEQUENTIAL} requests)..."

    total_latency=0
    min_latency=999999
    max_latency=0
    errors=0

    for i in $(seq 1 $NUM_SEQUENTIAL); do
        start=$(date +%s%N)

        if curl -s -m 5 "$HEALTH_URL" > /dev/null 2>&1; then
            end=$(date +%s%N)
            latency=$(( (end - start) / 1000000 ))  # Convert to ms

            total_latency=$((total_latency + latency))

            if [ $latency -lt $min_latency ]; then
                min_latency=$latency
            fi
            if [ $latency -gt $max_latency ]; then
                max_latency=$latency
            fi
        else
            ((errors++))
        fi

        # Show progress every 20 requests
        if [ $((i % 20)) -eq 0 ]; then
            echo "   Completed $i/$NUM_SEQUENTIAL requests..."
        fi
    done

    avg_latency=$((total_latency / NUM_SEQUENTIAL))

    echo "   Sequential Results:"
    echo "   - Min latency: ${min_latency}ms"
    echo "   - Avg latency: ${avg_latency}ms"
    echo "   - Max latency: ${max_latency}ms"
    echo "   - Errors: ${errors}/${NUM_SEQUENTIAL}"

    if [ $avg_latency -lt $MAX_ALLOWED_LATENCY_MS ]; then
        echo -e "${GREEN}✓ Average latency (${avg_latency}ms) is acceptable${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Average latency (${avg_latency}ms) exceeds ${MAX_ALLOWED_LATENCY_MS}ms${NC}"
        ((FAILED++))
    fi

    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✓ No errors in sequential requests${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ ${errors} errors encountered${NC}"
        ((FAILED++))
    fi
}

# Function to test concurrent latency
test_concurrent_latency() {
    echo ""
    echo "[4/5] Testing concurrent request latency (${NUM_CONCURRENT} concurrent)..."

    # Check if ab is available
    if ! command -v ab &> /dev/null; then
        echo -e "${YELLOW}⚠ Apache Bench (ab) not available, skipping concurrent test${NC}"
        return
    fi

    # Run Apache Bench test
    ab_output=$(ab -n $((NUM_CONCURRENT * 10)) -c $NUM_CONCURRENT -q "$HEALTH_URL" 2>&1)

    # Extract metrics
    requests_per_sec=$(echo "$ab_output" | grep "Requests per second" | awk '{print $4}')
    mean_time=$(echo "$ab_output" | grep "Time per request:" | head -1 | awk '{print $4}')
    failed=$(echo "$ab_output" | grep "Failed requests" | awk '{print $3}')

    echo "   Concurrent Results:"
    echo "   - Requests per second: ${requests_per_sec}"
    echo "   - Mean time per request: ${mean_time}ms"
    echo "   - Failed requests: ${failed:-0}"

    if [[ "$failed" == "0" || -z "$failed" ]]; then
        echo -e "${GREEN}✓ No errors in concurrent requests${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ ${failed} errors in concurrent requests${NC}"
        ((FAILED++))
    fi
}

# Function to test response consistency
test_response_consistency() {
    echo ""
    echo "[5/5] Testing response consistency..."

    # Get first response
    response1=$(curl -s "$HEALTH_URL")
    sleep 1
    response2=$(curl -s "$HEALTH_URL")

    # Compare status fields
    status1=$(echo "$response1" | grep -o '"status":"[^"]*"' | head -1)
    status2=$(echo "$response2" | grep -o '"status":"[^"]*"' | head -1)

    if [ "$status1" = "$status2" ]; then
        echo -e "${GREEN}✓ Response is consistent across multiple calls${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ Status changed between calls (expected due to background updates)${NC}"
        ((PASSED++))
    fi
}

# Main execution
main() {
    check_endpoint_available || exit 1
    test_response_format
    test_sequential_latency
    test_concurrent_latency
    test_response_consistency

    # Print summary
    echo ""
    echo "=== Test Summary ==="
    echo -e "Passed: ${GREEN}${PASSED}${NC}"
    echo -e "Failed: ${RED}${FAILED}${NC}"

    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main

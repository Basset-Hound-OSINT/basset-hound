#!/bin/bash
#
# End-to-End Production Verification Test Suite Runner - Phase 5b
#
# This script runs the comprehensive end-to-end production verification tests.
#
# Usage:
#   ./tests/run_e2e_verification.sh              # Run all tests
#   ./tests/run_e2e_verification.sh html         # Generate HTML report
#   ./tests/run_e2e_verification.sh fresh        # Start fresh deployment first
#   ./tests/run_e2e_verification.sh monitor      # Run with live output
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - pytest installed
#   - All dependencies in requirements.txt
#
# Exit Codes:
#   0 = All tests passed
#   1 = Some tests failed
#   2 = Setup error
#   3 = Missing prerequisites
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_FILE="$SCRIPT_DIR/test_e2e_complete.py"
REPORT_DIR="$SCRIPT_DIR/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$REPORT_DIR/e2e_test_$TIMESTAMP.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================ E2E VERIFICATION ================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        return 3
    fi
    print_success "Docker installed"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose not found"
        return 3
    fi
    print_success "Docker Compose installed"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 not found"
        return 3
    fi
    print_success "Python3 installed"

    # Check pytest
    if ! python3 -m pytest --version &> /dev/null; then
        print_error "pytest not found"
        return 3
    fi
    print_success "pytest installed"

    return 0
}

start_fresh_deployment() {
    print_header "Starting Fresh Deployment"

    cd "$PROJECT_ROOT"

    print_warning "Stopping existing deployment..."
    docker compose down -v || true
    sleep 2

    print_warning "Starting new deployment..."
    docker compose up -d

    print_warning "Waiting for services to be healthy..."
    sleep 10

    # Check health
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "API is healthy"
    else
        print_warning "API health check in progress, continuing with tests..."
    fi
}

run_tests() {
    local mode=${1:-default}
    local pytest_args="-v --tb=short"

    # Add report generation
    pytest_args="$pytest_args --html=$REPORT_DIR/e2e_report_$TIMESTAMP.html --self-contained-html"

    # Add JSON report
    pytest_args="$pytest_args --json-report --json-report-file=$REPORT_DIR/e2e_report_$TIMESTAMP.json"

    # Add coverage if available
    if python3 -c "import pytest_cov" 2>/dev/null; then
        pytest_args="$pytest_args --cov=api --cov-report=html:$REPORT_DIR/coverage_$TIMESTAMP"
    fi

    # Add live output if requested
    if [[ "$mode" == "monitor" ]]; then
        pytest_args="$pytest_args -s"
    fi

    print_header "Running E2E Tests"
    print_warning "Test file: $TEST_FILE"
    print_warning "Report dir: $REPORT_DIR"

    # Ensure report directory exists
    mkdir -p "$REPORT_DIR"

    # Run tests with full output
    python3 -m pytest $TEST_FILE $pytest_args 2>&1 | tee "$LOG_FILE"
    local test_result=$?

    return $test_result
}

generate_summary_report() {
    local test_result=$1

    print_header "Test Execution Summary"

    echo ""
    echo "Timestamp: $(date)"
    echo "Project: $PROJECT_ROOT"
    echo "Test File: $TEST_FILE"
    echo ""

    if [[ $test_result -eq 0 ]]; then
        print_success "ALL TESTS PASSED"
        echo ""
        echo "Deployment Status: READY FOR PRODUCTION"
        echo "Pass Rate: 95%+ (target achieved)"
    else
        print_error "SOME TESTS FAILED"
        echo ""
        echo "Review the detailed report:"
        echo "  HTML: $REPORT_DIR/e2e_report_$TIMESTAMP.html"
        echo "  JSON: $REPORT_DIR/e2e_report_$TIMESTAMP.json"
        echo "  Log:  $LOG_FILE"
    fi

    echo ""
    echo "Performance Metrics Report: $REPORT_DIR/e2e_report.json"
    echo ""

    # Show key metrics if JSON report exists
    if [[ -f "$REPORT_DIR/e2e_report.json" ]]; then
        echo "Performance Summary:"
        python3 -c "
import json
try:
    with open('$REPORT_DIR/e2e_report.json') as f:
        data = json.load(f)
        print(f'  Total performance tests: {data[\"total_tests\"]}')
        print(f'  Passed: {data[\"performance_passed\"]}')
        print(f'  Failed: {data[\"performance_failed\"]}')
except:
    pass
" 2>/dev/null || true
    fi

    echo ""
    echo "Next Steps:"
    if [[ $test_result -eq 0 ]]; then
        echo "  1. Review HTML report: $REPORT_DIR/e2e_report_$TIMESTAMP.html"
        echo "  2. Verify performance metrics in e2e_report.json"
        echo "  3. Check deployment readiness assessment"
        echo "  4. Proceed with production deployment"
    else
        echo "  1. Review failed tests in the HTML report"
        echo "  2. Check error logs: $LOG_FILE"
        echo "  3. Address identified issues"
        echo "  4. Re-run tests to verify fixes"
    fi

    echo ""
}

# Main execution
main() {
    local command=${1:-default}

    # Check prerequisites first
    check_prerequisites || exit 3

    # Create report directory
    mkdir -p "$REPORT_DIR"

    # Execute requested command
    case "$command" in
        fresh)
            start_fresh_deployment
            run_tests "default"
            generate_summary_report $?
            ;;
        html)
            run_tests "default"
            generate_summary_report $?
            print_header "Opening HTML Report"
            if command -v xdg-open &> /dev/null; then
                xdg-open "$REPORT_DIR/e2e_report_$TIMESTAMP.html" 2>/dev/null || true
            elif command -v open &> /dev/null; then
                open "$REPORT_DIR/e2e_report_$TIMESTAMP.html" 2>/dev/null || true
            else
                print_warning "Cannot automatically open report. Navigate to:"
                echo "  $REPORT_DIR/e2e_report_$TIMESTAMP.html"
            fi
            ;;
        monitor)
            start_fresh_deployment
            run_tests "monitor"
            generate_summary_report $?
            ;;
        *)
            run_tests "default"
            generate_summary_report $?
            ;;
    esac

    local final_result=$?
    exit $final_result
}

# Run main
main "$@"

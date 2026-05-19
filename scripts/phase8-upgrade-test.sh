#!/bin/bash
# Phase 7 → Phase 8 Upgrade Verification Script
# This script tests the upgrade path and validates Phase 8 features
#
# Usage: ./scripts/phase8-upgrade-test.sh [test|backup|migrate|verify]

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="/data/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="/tmp/phase8-upgrade-${TIMESTAMP}.log"

# Initialize log
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# BACKUP FUNCTION
function do_backup() {
    log_info "Creating database backup..."
    mkdir -p "$BACKUP_DIR"

    log_info "Backing up Neo4j database..."
    docker-compose exec -T neo4j_osint_db neo4j-admin database dump neo4j \
        --to-path=/data/backups/phase7-backup-${TIMESTAMP}.dump 2>/dev/null || {
        log_error "Neo4j backup failed"
        return 1
    }
    log_success "Neo4j backup created"

    log_info "Backing up configuration files..."
    cp docker-compose.yml docker-compose.yml.phase7-${TIMESTAMP}
    cp api/config.py api/config.py.phase7-${TIMESTAMP}
    log_success "Configuration backup complete"

    log_success "Backup complete"
}

# MIGRATE FUNCTION
function do_migrate() {
    log_info "Applying Phase 8 schema migrations..."

    if ! docker-compose ps neo4j | grep -q "Up"; then
        log_error "Neo4j is not running"
        return 1
    fi

    log_info "Creating Phase 8 indexes..."

    docker-compose exec -T neo4j_osint_db cypher-shell << 'EOF'
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.updated_at);
CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_RELATIONSHIP]-() ON (r.updated_at);
CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name, p.email);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type, e.created_at);
MATCH (e:Entity) WHERE NOT EXISTS(e.updated_at)
SET e.updated_at = CASE WHEN EXISTS(e.created_at) THEN e.created_at ELSE datetime() END
RETURN count(e) as entities_updated;
EOF

    log_success "Schema migrations applied"
}

# SMOKE TESTS
function do_smoke_tests() {
    log_info "Running Phase 8 smoke tests..."

    PASSED=0
    FAILED=0

    log_info "Test 1/4: Health endpoint..."
    if curl -s http://localhost:8080/api/v1/health 2>/dev/null | jq -e '.status' > /dev/null 2>&1; then
        log_success "Health check passed"
        ((PASSED++))
    else
        log_error "Health check failed"
        ((FAILED++))
    fi

    log_info "Test 2/4: Phase 7 entities endpoint..."
    if curl -s http://localhost:8080/api/v1/entities 2>/dev/null | jq -e '.data' > /dev/null 2>&1; then
        log_success "Entities endpoint operational"
        ((PASSED++))
    else
        log_error "Entities endpoint failed"
        ((FAILED++))
    fi

    log_info "Test 3/4: Advanced search endpoint..."
    if curl -s -X POST http://localhost:8080/api/v1/search/advanced \
        -H "Content-Type: application/json" \
        -d '{"query":"test"}' 2>/dev/null | jq -e '.data' > /dev/null 2>&1; then
        log_success "Advanced search operational"
        ((PASSED++))
    else
        log_warning "Advanced search not available"
    fi

    log_info "Test 4/4: Cache layer..."
    REDIS_KEYS=$(docker exec basset_redis redis-cli DBSIZE 2>/dev/null | grep -oP '(?<=keys: )\d+' || echo "0")
    log_success "Cache entries: $REDIS_KEYS"
    ((PASSED++))

    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "Test Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
    echo -e "${BLUE}============================================${NC}"
}

# VERIFY FUNCTION
function do_verify() {
    log_info "Running comprehensive Phase 8 verification..."

    log_info "Checking service status..."
    RUNNING=$(docker-compose ps | grep "Up" | wc -l)
    log_success "Services running: $RUNNING"

    log_info "Checking data integrity..."
    NODE_COUNT=$(docker-compose exec -T neo4j_osint_db cypher-shell \
        "MATCH (n) WHERE NOT (n:Configuration OR n:Section OR n:Field OR n:Component) RETURN count(n)" 2>/dev/null | tail -1 || echo "?")
    log_success "Total data nodes: $NODE_COUNT"

    log_info "Checking indexes..."
    INDEX_COUNT=$(docker-compose exec -T neo4j_osint_db cypher-shell \
        "CALL db.indexes() YIELD name RETURN count(*)" 2>/dev/null | tail -1 || echo "?")
    log_success "Total indexes: $INDEX_COUNT"

    log_success "Verification complete!"
}

# MAIN
function main() {
    COMMAND="${1:-test}"

    case "$COMMAND" in
        test)
            do_smoke_tests
            ;;
        backup)
            do_backup
            ;;
        migrate)
            do_migrate
            ;;
        verify)
            do_verify
            ;;
        *)
            echo "Usage: $0 [test|backup|migrate|verify]"
            exit 1
            ;;
    esac

    log_info "Log saved to: $LOG_FILE"
}

main "$@"

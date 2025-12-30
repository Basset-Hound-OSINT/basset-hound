#!/bin/bash
#
# Basset Hound OSINT Platform - Ubuntu 22.04 Native Installation Script
#
# This script installs all dependencies for running Basset Hound natively on Ubuntu 22.04
# including Python 3.12, Neo4j 5.x with GDS plugin, and all required system libraries.
#
# Usage: ./install.sh [--neo4j-password <password>] [--skip-neo4j] [--help]
#
# Options:
#   --neo4j-password <password>  Set Neo4j password (default: neo4jbasset)
#   --skip-neo4j                 Skip Neo4j installation (use existing or Docker)
#   --help                       Show this help message
#

set -e

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-neo4jbasset}"
SKIP_NEO4J=false
REQUIRED_UBUNTU_VERSION="22.04"
PYTHON_VERSION="3.12"
NEO4J_MAJOR_VERSION="5"

# =============================================================================
# Color Output Functions
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}============================================================${NC}"
    echo -e "${BLUE}${BOLD}  $1${NC}"
    echo -e "${BLUE}${BOLD}============================================================${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Helper Functions
# =============================================================================

show_help() {
    cat << EOF
Basset Hound OSINT Platform - Installation Script

Usage: ./install.sh [OPTIONS]

Options:
    --neo4j-password <password>  Set Neo4j password (default: neo4jbasset)
    --skip-neo4j                 Skip Neo4j installation (use existing or Docker)
    --help                       Show this help message

Examples:
    ./install.sh
    ./install.sh --neo4j-password mypassword123
    ./install.sh --skip-neo4j

EOF
    exit 0
}

command_exists() {
    command -v "$1" &> /dev/null
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Please run as a regular user."
        print_info "The script will use sudo when elevated privileges are needed."
        exit 1
    fi
}

# =============================================================================
# Parse Command Line Arguments
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --neo4j-password)
            NEO4J_PASSWORD="$2"
            shift 2
            ;;
        --skip-neo4j)
            SKIP_NEO4J=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# =============================================================================
# System Check
# =============================================================================

check_ubuntu_version() {
    print_step "Checking Ubuntu version..."

    if [[ ! -f /etc/os-release ]]; then
        print_warning "Cannot determine OS version. Proceeding anyway..."
        return
    fi

    source /etc/os-release

    if [[ "$ID" != "ubuntu" ]]; then
        print_warning "This script is designed for Ubuntu. Detected: $ID"
        print_warning "Proceeding anyway, but some steps may fail."
        return
    fi

    if [[ "$VERSION_ID" != "$REQUIRED_UBUNTU_VERSION" ]]; then
        print_warning "This script is optimized for Ubuntu ${REQUIRED_UBUNTU_VERSION}."
        print_warning "Detected: Ubuntu ${VERSION_ID}"
        print_warning "Proceeding anyway, but some steps may require adjustment."
    else
        print_success "Ubuntu ${VERSION_ID} detected"
    fi
}

# =============================================================================
# System Dependencies
# =============================================================================

install_system_dependencies() {
    print_header "Installing System Dependencies"

    print_step "Updating package lists..."
    sudo apt-get update -qq
    print_success "Package lists updated"

    print_step "Installing build essentials and common tools..."
    sudo apt-get install -y \
        build-essential \
        curl \
        wget \
        git \
        gnupg \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        lsb-release \
        unzip \
        jq
    print_success "Build essentials installed"

    print_step "Installing libmagic for python-magic..."
    sudo apt-get install -y libmagic1 libmagic-dev
    print_success "libmagic installed"
}

# =============================================================================
# Python 3.12 Installation
# =============================================================================

install_python() {
    print_header "Installing Python ${PYTHON_VERSION}"

    # Check if Python 3.12 is already installed
    if command_exists python${PYTHON_VERSION}; then
        INSTALLED_VERSION=$(python${PYTHON_VERSION} --version 2>&1 | awk '{print $2}')
        print_info "Python ${INSTALLED_VERSION} is already installed"
    else
        print_step "Adding deadsnakes PPA for Python ${PYTHON_VERSION}..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update -qq
        print_success "deadsnakes PPA added"

        print_step "Installing Python ${PYTHON_VERSION}..."
        sudo apt-get install -y \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-venv \
            python${PYTHON_VERSION}-dev \
            python${PYTHON_VERSION}-distutils
        print_success "Python ${PYTHON_VERSION} installed"
    fi

    # Verify installation
    if command_exists python${PYTHON_VERSION}; then
        PYTHON_PATH=$(which python${PYTHON_VERSION})
        INSTALLED_VERSION=$(python${PYTHON_VERSION} --version 2>&1)
        print_success "Python verified: ${INSTALLED_VERSION} at ${PYTHON_PATH}"
    else
        print_error "Python ${PYTHON_VERSION} installation failed"
        exit 1
    fi
}

# =============================================================================
# Neo4j Installation
# =============================================================================

install_neo4j() {
    if [[ "$SKIP_NEO4J" == "true" ]]; then
        print_header "Skipping Neo4j Installation"
        print_info "Neo4j installation skipped as requested."
        print_info "Make sure Neo4j 5.x is available (e.g., via Docker)."
        return
    fi

    print_header "Installing Neo4j ${NEO4J_MAJOR_VERSION}.x"

    # Check if Neo4j is already installed
    if command_exists neo4j; then
        INSTALLED_VERSION=$(neo4j --version 2>&1 | head -n1)
        print_info "Neo4j is already installed: ${INSTALLED_VERSION}"

        # Check if it's version 5.x
        if [[ "$INSTALLED_VERSION" == *"5."* ]]; then
            print_success "Neo4j 5.x is already installed"
        else
            print_warning "Installed Neo4j version may not be compatible"
            print_warning "Basset Hound requires Neo4j 5.x"
        fi
    else
        print_step "Adding Neo4j GPG key..."
        curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j-archive-keyring.gpg 2>/dev/null || true
        print_success "Neo4j GPG key added"

        print_step "Adding Neo4j repository..."
        echo "deb [signed-by=/usr/share/keyrings/neo4j-archive-keyring.gpg] https://debian.neo4j.com stable ${NEO4J_MAJOR_VERSION}" | sudo tee /etc/apt/sources.list.d/neo4j.list > /dev/null
        print_success "Neo4j repository added"

        print_step "Installing Neo4j..."
        sudo apt-get update -qq
        sudo apt-get install -y neo4j
        print_success "Neo4j installed"
    fi

    # Install Java if not present (Neo4j dependency)
    if ! command_exists java; then
        print_step "Installing OpenJDK 17 (Neo4j requirement)..."
        sudo apt-get install -y openjdk-17-jre-headless
        print_success "OpenJDK 17 installed"
    fi
}

# =============================================================================
# Neo4j GDS Plugin Installation
# =============================================================================

install_neo4j_gds() {
    if [[ "$SKIP_NEO4J" == "true" ]]; then
        print_info "Skipping GDS plugin installation (Neo4j skipped)"
        return
    fi

    print_header "Installing Neo4j GDS Plugin"

    # Determine Neo4j plugins directory
    NEO4J_PLUGINS_DIR="/var/lib/neo4j/plugins"
    NEO4J_CONF_DIR="/etc/neo4j"

    # Check if plugins directory exists
    if [[ ! -d "$NEO4J_PLUGINS_DIR" ]]; then
        print_warning "Neo4j plugins directory not found at $NEO4J_PLUGINS_DIR"
        print_info "Attempting to create..."
        sudo mkdir -p "$NEO4J_PLUGINS_DIR"
    fi

    # Check if GDS is already installed
    GDS_JAR=$(find "$NEO4J_PLUGINS_DIR" -name "neo4j-graph-data-science-*.jar" 2>/dev/null | head -n1)

    if [[ -n "$GDS_JAR" ]]; then
        print_info "GDS plugin already installed: $(basename $GDS_JAR)"
    else
        print_step "Downloading Neo4j GDS plugin..."

        # Get the latest GDS version compatible with Neo4j 5.x
        # GDS 2.x is compatible with Neo4j 5.x
        GDS_VERSION="2.6.4"
        GDS_URL="https://graphdatascience.ninja/neo4j-graph-data-science-${GDS_VERSION}.jar"

        # Download GDS plugin
        sudo wget -q --show-progress -O "${NEO4J_PLUGINS_DIR}/neo4j-graph-data-science-${GDS_VERSION}.jar" "$GDS_URL"

        if [[ -f "${NEO4J_PLUGINS_DIR}/neo4j-graph-data-science-${GDS_VERSION}.jar" ]]; then
            print_success "GDS plugin ${GDS_VERSION} downloaded"
        else
            print_warning "Failed to download GDS plugin. You may need to download it manually."
            print_info "URL: ${GDS_URL}"
            print_info "Destination: ${NEO4J_PLUGINS_DIR}/"
        fi
    fi
}

# =============================================================================
# Neo4j Configuration
# =============================================================================

configure_neo4j() {
    if [[ "$SKIP_NEO4J" == "true" ]]; then
        print_info "Skipping Neo4j configuration (Neo4j skipped)"
        return
    fi

    print_header "Configuring Neo4j"

    NEO4J_CONF="/etc/neo4j/neo4j.conf"

    if [[ ! -f "$NEO4J_CONF" ]]; then
        print_warning "Neo4j configuration file not found at $NEO4J_CONF"
        return
    fi

    # Backup original config if not already backed up
    if [[ ! -f "${NEO4J_CONF}.original" ]]; then
        print_step "Backing up original Neo4j configuration..."
        sudo cp "$NEO4J_CONF" "${NEO4J_CONF}.original"
        print_success "Configuration backed up"
    fi

    print_step "Enabling GDS plugin in Neo4j configuration..."

    # Enable GDS procedures
    if ! grep -q "dbms.security.procedures.unrestricted=gds.*" "$NEO4J_CONF"; then
        echo "" | sudo tee -a "$NEO4J_CONF" > /dev/null
        echo "# Basset Hound - Enable GDS plugin" | sudo tee -a "$NEO4J_CONF" > /dev/null
        echo "dbms.security.procedures.unrestricted=gds.*" | sudo tee -a "$NEO4J_CONF" > /dev/null
        print_success "GDS procedures enabled"
    else
        print_info "GDS procedures already enabled"
    fi

    # Allow GDS procedures to be loaded
    if ! grep -q "dbms.security.procedures.allowlist=gds.*" "$NEO4J_CONF"; then
        echo "dbms.security.procedures.allowlist=gds.*,apoc.*" | sudo tee -a "$NEO4J_CONF" > /dev/null
        print_success "GDS procedures added to allowlist"
    else
        print_info "GDS procedures already in allowlist"
    fi

    print_step "Starting Neo4j service..."
    sudo systemctl enable neo4j
    sudo systemctl restart neo4j

    # Wait for Neo4j to start
    print_info "Waiting for Neo4j to start (this may take 30-60 seconds)..."

    MAX_WAIT=60
    WAITED=0
    while [[ $WAITED -lt $MAX_WAIT ]]; do
        if curl -s http://localhost:7474 > /dev/null 2>&1; then
            break
        fi
        sleep 2
        WAITED=$((WAITED + 2))
        echo -n "."
    done
    echo ""

    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        print_success "Neo4j is running"
    else
        print_warning "Neo4j may not have started yet. Check status with: sudo systemctl status neo4j"
    fi

    # Set Neo4j password
    print_step "Setting Neo4j password..."

    # Try to change the default password
    # Neo4j 5.x uses neo4j-admin for password management
    if command_exists neo4j-admin; then
        # Check if this is a fresh installation (default password is 'neo4j')
        # First, try with default password
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u neo4j:neo4j http://localhost:7474/db/neo4j/tx 2>/dev/null || echo "000")

        if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "401" ]]; then
            # Password might need changing
            print_info "Attempting to set Neo4j password..."

            # Use cypher-shell to change password if available
            if command_exists cypher-shell; then
                echo "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO '${NEO4J_PASSWORD}';" | cypher-shell -u neo4j -p neo4j 2>/dev/null && \
                    print_success "Neo4j password set to: ${NEO4J_PASSWORD}" || \
                    print_info "Password may already be set or Neo4j requires manual password change"
            else
                print_info "cypher-shell not available. You may need to change the password manually."
                print_info "Default credentials: neo4j/neo4j"
                print_info "Open http://localhost:7474 and change password to: ${NEO4J_PASSWORD}"
            fi
        else
            print_info "Neo4j password may already be configured"
        fi
    fi

    print_success "Neo4j configuration complete"
}

# =============================================================================
# Python Virtual Environment
# =============================================================================

setup_python_venv() {
    print_header "Setting Up Python Virtual Environment"

    if [[ -d "$VENV_DIR" ]]; then
        print_info "Virtual environment already exists at ${VENV_DIR}"

        # Check if it's a valid venv
        if [[ -f "${VENV_DIR}/bin/activate" ]]; then
            print_success "Existing virtual environment is valid"
        else
            print_warning "Existing virtual environment appears corrupted. Recreating..."
            rm -rf "$VENV_DIR"
        fi
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        print_step "Creating virtual environment with Python ${PYTHON_VERSION}..."
        python${PYTHON_VERSION} -m venv "$VENV_DIR"
        print_success "Virtual environment created at ${VENV_DIR}"
    fi

    print_step "Activating virtual environment..."
    source "${VENV_DIR}/bin/activate"
    print_success "Virtual environment activated"

    print_step "Upgrading pip..."
    pip install --upgrade pip --quiet
    print_success "pip upgraded"

    print_step "Installing Python requirements..."
    if [[ -f "${SCRIPT_DIR}/requirements.txt" ]]; then
        pip install -r "${SCRIPT_DIR}/requirements.txt" --quiet
        print_success "Python requirements installed"
    else
        print_error "requirements.txt not found at ${SCRIPT_DIR}/requirements.txt"
        exit 1
    fi
}

# =============================================================================
# Create Project Directories
# =============================================================================

create_directories() {
    print_header "Creating Project Directories"

    DIRECTORIES=(
        "${SCRIPT_DIR}/projects"
        "${SCRIPT_DIR}/static"
        "${SCRIPT_DIR}/static/imgs"
        "${SCRIPT_DIR}/static/css"
        "${SCRIPT_DIR}/static/js"
        "${SCRIPT_DIR}/templates"
        "${SCRIPT_DIR}/data"
        "${SCRIPT_DIR}/logs"
        "${SCRIPT_DIR}/exports"
        "${SCRIPT_DIR}/imports"
    )

    for dir in "${DIRECTORIES[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            print_success "Created: ${dir#$SCRIPT_DIR/}"
        else
            print_info "Already exists: ${dir#$SCRIPT_DIR/}"
        fi
    done
}

# =============================================================================
# Create .env file if not exists
# =============================================================================

create_env_file() {
    print_header "Checking Environment Configuration"

    ENV_FILE="${SCRIPT_DIR}/.env"

    if [[ -f "$ENV_FILE" ]]; then
        print_info ".env file already exists"

        # Update NEO4J_PASSWORD if it was specified
        if grep -q "NEO4J_PASSWORD=" "$ENV_FILE"; then
            print_info "Updating NEO4J_PASSWORD in .env..."
            sed -i "s/^NEO4J_PASSWORD=.*/NEO4J_PASSWORD=${NEO4J_PASSWORD}/" "$ENV_FILE"
            print_success "NEO4J_PASSWORD updated"
        fi
    else
        print_step "Creating .env file from template..."

        cat > "$ENV_FILE" << EOF
# Basset Hound Environment Configuration
# Generated by install.sh on $(date)

# =============================================================================
# Neo4j Database
# =============================================================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=${NEO4J_PASSWORD}

# =============================================================================
# Application Settings
# =============================================================================
DEBUG=true
HOST=0.0.0.0
PORT=8000

# =============================================================================
# Authentication (disabled for development)
# =============================================================================
AUTH_ENABLED=false
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "change-this-secret-key-in-production")

# =============================================================================
# Data Configuration
# =============================================================================
DATA_CONFIG_PATH=data_config.yaml

# =============================================================================
# File Storage
# =============================================================================
PROJECTS_DIRECTORY=projects
MAX_UPLOAD_SIZE_MB=100

# =============================================================================
# CORS Settings (permissive for development)
# =============================================================================
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
EOF

        print_success ".env file created"
    fi
}

# =============================================================================
# Verify Installation
# =============================================================================

verify_installation() {
    print_header "Verifying Installation"

    ERRORS=0

    # Check Python
    print_step "Checking Python ${PYTHON_VERSION}..."
    if command_exists python${PYTHON_VERSION}; then
        print_success "Python ${PYTHON_VERSION}: $(python${PYTHON_VERSION} --version)"
    else
        print_error "Python ${PYTHON_VERSION} not found"
        ERRORS=$((ERRORS + 1))
    fi

    # Check virtual environment
    print_step "Checking virtual environment..."
    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        print_success "Virtual environment: ${VENV_DIR}"
    else
        print_error "Virtual environment not found"
        ERRORS=$((ERRORS + 1))
    fi

    # Check Neo4j (if not skipped)
    if [[ "$SKIP_NEO4J" != "true" ]]; then
        print_step "Checking Neo4j..."
        if command_exists neo4j; then
            NEO4J_STATUS=$(sudo systemctl is-active neo4j 2>/dev/null || echo "unknown")
            if [[ "$NEO4J_STATUS" == "active" ]]; then
                print_success "Neo4j: running"
            else
                print_warning "Neo4j: ${NEO4J_STATUS}"
            fi
        else
            print_error "Neo4j not installed"
            ERRORS=$((ERRORS + 1))
        fi

        # Check GDS plugin
        print_step "Checking GDS plugin..."
        GDS_JAR=$(find /var/lib/neo4j/plugins -name "neo4j-graph-data-science-*.jar" 2>/dev/null | head -n1)
        if [[ -n "$GDS_JAR" ]]; then
            print_success "GDS plugin: $(basename $GDS_JAR)"
        else
            print_warning "GDS plugin not found in /var/lib/neo4j/plugins"
        fi
    fi

    # Check libmagic
    print_step "Checking libmagic..."
    if ldconfig -p | grep -q libmagic; then
        print_success "libmagic: installed"
    else
        print_warning "libmagic may not be properly installed"
    fi

    # Check project directories
    print_step "Checking project directories..."
    for dir in projects static data; do
        if [[ -d "${SCRIPT_DIR}/${dir}" ]]; then
            print_success "Directory: ${dir}/"
        else
            print_warning "Directory missing: ${dir}/"
        fi
    done

    return $ERRORS
}

# =============================================================================
# Print Summary
# =============================================================================

print_summary() {
    print_header "Installation Complete!"

    echo -e "${GREEN}${BOLD}Basset Hound OSINT Platform has been installed successfully!${NC}"
    echo ""
    echo -e "${BOLD}Quick Start:${NC}"
    echo ""
    echo "  1. Activate the virtual environment:"
    echo -e "     ${CYAN}source ${VENV_DIR}/bin/activate${NC}"
    echo ""
    echo "  2. Start the FastAPI server:"
    echo -e "     ${CYAN}uvicorn api.main:app --reload --host 0.0.0.0 --port 8000${NC}"
    echo ""
    echo "  3. Access the application:"
    echo -e "     ${CYAN}API Docs:     http://localhost:8000/docs${NC}"
    echo -e "     ${CYAN}Neo4j Browser: http://localhost:7474${NC}"
    echo ""
    echo -e "${BOLD}Neo4j Credentials:${NC}"
    echo "  Username: neo4j"
    echo "  Password: ${NEO4J_PASSWORD}"
    echo ""
    echo -e "${BOLD}Configuration:${NC}"
    echo "  Config file: ${SCRIPT_DIR}/.env"
    echo "  Projects dir: ${SCRIPT_DIR}/projects"
    echo ""

    if [[ "$SKIP_NEO4J" == "true" ]]; then
        echo -e "${YELLOW}${BOLD}Note:${NC} Neo4j installation was skipped."
        echo "  Make sure Neo4j 5.x is available before starting Basset Hound."
        echo "  You can use Docker: docker compose up -d neo4j"
        echo ""
    fi

    echo -e "${BOLD}Useful Commands:${NC}"
    echo "  Check Neo4j status:  sudo systemctl status neo4j"
    echo "  Restart Neo4j:       sudo systemctl restart neo4j"
    echo "  View Neo4j logs:     sudo journalctl -u neo4j -f"
    echo "  Run tests:           pytest tests/ -v"
    echo ""
    echo -e "${BOLD}For more information, see:${NC}"
    echo "  README.md"
    echo "  docs/ROADMAP.md"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "Basset Hound OSINT Platform Installer"

    echo -e "${BOLD}Installation Settings:${NC}"
    echo "  Install directory: ${SCRIPT_DIR}"
    echo "  Python version:    ${PYTHON_VERSION}"
    echo "  Neo4j version:     ${NEO4J_MAJOR_VERSION}.x"
    echo "  Skip Neo4j:        ${SKIP_NEO4J}"
    echo ""

    # Pre-flight checks
    check_root
    check_ubuntu_version

    # Install dependencies
    install_system_dependencies
    install_python

    # Neo4j
    install_neo4j
    install_neo4j_gds
    configure_neo4j

    # Python environment
    setup_python_venv

    # Project setup
    create_directories
    create_env_file

    # Verify and summarize
    verify_installation
    print_summary
}

# Run main function
main "$@"

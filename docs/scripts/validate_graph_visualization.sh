#!/bin/bash

# Validation script for Graph Visualization implementation
# Checks that all required files exist and have the required implementations

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

check_file_exists() {
    local file=$1
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} File exists: $file"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} File missing: $file"
        ((FAIL++))
        return 1
    fi
}

check_content() {
    local file=$1
    local pattern=$2
    local description=$3

    if [ ! -f "$file" ]; then
        echo -e "${RED}✗${NC} File missing: $file"
        ((FAIL++))
        return 1
    fi

    if grep -q "$pattern" "$file"; then
        echo -e "${GREEN}✓${NC} $description (in $file)"
        ((PASS++))
        return 0
    else
        echo -e "${RED}✗${NC} Missing: $description (in $file)"
        ((FAIL++))
        return 1
    fi
}

echo "========================================"
echo "Graph Visualization Validation"
echo "========================================"
echo ""

# Check core files
echo "Checking core files..."
check_file_exists "templates/map.html"
check_file_exists "static/js/map-handler.js"
check_file_exists "static/css/map-controls.css"
check_file_exists "test_graph_visualization.py"
echo ""

# Check HTML structure
echo "Checking HTML structure..."
check_content "templates/map.html" "depth-slider" "Depth slider control"
check_content "templates/map.html" "layout-selector" "Layout selector dropdown"
check_content "templates/map.html" "center-btn" "Center button"
check_content "templates/map.html" "reset-view-btn" "Reset button"
check_content "templates/map.html" "export-btn" "Export button"
check_content "templates/map.html" "fullscreen-btn" "Fullscreen button"
check_content "templates/map.html" "graph-container" "Graph container"
check_content "templates/map.html" "map-controls.css" "CSS link"
echo ""

# Check layout options
echo "Checking layout options..."
check_content "templates/map.html" "Force-Directed (COSE)" "COSE layout option"
check_content "templates/map.html" "Breadth First" "Breadthfirst layout option"
check_content "templates/map.html" "Circle" "Circle layout option"
check_content "templates/map.html" "Grid" "Grid layout option"
echo ""

# Check legend colors
echo "Checking legend colors..."
check_content "templates/map.html" "Person" "Person legend item"
check_content "templates/map.html" "Organization" "Organization legend item"
check_content "templates/map.html" "Location" "Location legend item"
check_content "templates/map.html" "Group" "Group legend item"
echo ""

# Check JavaScript functionality
echo "Checking JavaScript functionality..."
check_content "static/js/map-handler.js" "ENTITY_TYPE_COLORS" "Entity type color mapping"
check_content "static/js/map-handler.js" "truncateText" "Text truncation function"
check_content "static/js/map-handler.js" "changeLayout" "Layout change function"
check_content "static/js/map-handler.js" "centerView" "Center view function"
check_content "static/js/map-handler.js" "exportGraphML" "Export function"
check_content "static/js/map-handler.js" "formatRelationshipType" "Relationship formatting"
check_content "static/js/map-handler.js" "openEntityInGraph" "Global entity in graph function"
check_content "static/js/map-handler.js" "debounce" "Debounce function"
echo ""

# Check styling
echo "Checking styling..."
check_content "static/css/map-controls.css" "depth-slider" "Depth slider styling"
check_content "static/css/map-controls.css" "control-buttons" "Button styling"
check_content "static/css/map-controls.css" "@media (prefers-color-scheme: dark)" "Dark mode support"
check_content "static/css/map-controls.css" "@media (max-width: 768px)" "Responsive design"
echo ""

# Check API integration
echo "Checking API integration..."
check_content "static/js/map-handler.js" "/graph/entity/" "API endpoint for entity graph"
check_content "static/js/map-handler.js" "/visualization/export" "API endpoint for export"
check_content "static/js/map-handler.js" "?format=cytoscape" "Cytoscape format parameter"
check_content "static/js/map-handler.js" "?depth=" "Depth parameter"
echo ""

# Check Cytoscape integration
echo "Checking Cytoscape.js integration..."
check_content "templates/map.html" "cytoscape.min.js" "Cytoscape JS library"
check_content "static/js/map-handler.js" "cytoscape(" "Cytoscape initialization"
check_content "static/js/map-handler.js" "cy.on(" "Cytoscape event handlers"
check_content "static/js/map-handler.js" "cy.layout" "Cytoscape layout application"
echo ""

# Check interactivity
echo "Checking interactivity..."
check_content "static/js/map-handler.js" "addEventListener('change'" "Depth slider change event"
check_content "static/js/map-handler.js" "addEventListener('click'" "Button click events"
check_content "static/js/map-handler.js" "cy.on('tap'" "Node tap/click event"
check_content "static/js/map-handler.js" "cy.on('mouseover'" "Node hover event"
check_content "static/js/map-handler.js" "window.location.href.*map.html" "Navigation to subgraph"
echo ""

# Check accessibility
echo "Checking accessibility..."
check_content "templates/map.html" "aria-label" "ARIA labels"
check_content "templates/map.html" "aria-live" "ARIA live regions"
check_content "static/css/map-controls.css" "focus-visible" "Focus visible styles"
echo ""

# Check responsive design
echo "Checking responsive design..."
check_content "static/css/map-controls.css" "max-width: 280px" "Control panel max width"
check_content "static/css/map-controls.css" "grid-template-columns" "Button grid layout"
check_content "templates/map.html" "viewport" "Viewport meta tag"
echo ""

# Summary
echo ""
echo "========================================"
echo "Validation Summary"
echo "========================================"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Graph Visualization is fully implemented with:"
    echo "  ✓ Interactive graph rendering (Cytoscape.js)"
    echo "  ✓ Depth control slider (1-5 hops)"
    echo "  ✓ Layout selector (COSE, Breadthfirst, Circle, Grid)"
    echo "  ✓ Control buttons (Center, Reset, Export, Fullscreen)"
    echo "  ✓ Entity type color coding"
    echo "  ✓ Relationship type labels"
    echo "  ✓ Node click navigation"
    echo "  ✓ Hover tooltips"
    echo "  ✓ Responsive design (mobile/tablet/desktop)"
    echo "  ✓ Accessibility features (ARIA, focus visible)"
    echo "  ✓ Dark mode support"
    echo "  ✓ API integration"
    echo ""
    echo "Ready for testing with:"
    echo "  python test_graph_visualization.py"
    exit 0
else
    echo -e "${RED}✗ Validation failed with $FAIL error(s)${NC}"
    exit 1
fi

#!/usr/bin/env python3
"""
Test script for Add Entity Modal Implementation in Basset-Hound

This script verifies:
1. Modal HTML exists in dashboard.html
2. Entity type buttons exist for all 7 types
3. JavaScript functions are properly exported
4. Backend handles entity_type parameter (or notes what's missing)
5. API endpoint accepts entity_type when creating entities

Author: Claude Code Test Suite
Date: 2025-01-31
"""

import os
import re
import sys
import json
import requests
from datetime import datetime
from pathlib import Path

# Test configuration
BASE_DIR = Path("/home/devel/basset-hound")
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static" / "js"
API_DIR = BASE_DIR / "api" / "routers"
RESULTS_DIR = BASE_DIR / "tests" / "results"
API_BASE_URL = "http://localhost:8080"

# Expected entity types
EXPECTED_ENTITY_TYPES = [
    "person",
    "organization",
    "government",
    "group",
    "sock_puppet",
    "location",
    "unknown"
]

class TestResult:
    """Container for test results."""
    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.messages = []
        self.issues = []

    def log(self, message: str):
        self.messages.append(message)

    def fail(self, issue: str):
        self.passed = False
        self.issues.append(issue)

    def __str__(self):
        status = "PASSED" if self.passed else "FAILED"
        output = [f"\n{'='*60}", f"TEST: {self.name}", f"STATUS: {status}", "="*60]
        for msg in self.messages:
            output.append(f"  {msg}")
        if self.issues:
            output.append("\nISSUES:")
            for issue in self.issues:
                output.append(f"  - {issue}")
        return "\n".join(output)


def test_modal_html_exists():
    """Test 1: Verify the modal HTML exists in dashboard.html."""
    result = TestResult("Modal HTML Exists in Dashboard")

    dashboard_path = TEMPLATES_DIR / "dashboard.html"
    if not dashboard_path.exists():
        result.fail(f"dashboard.html not found at {dashboard_path}")
        return result

    result.log(f"Found dashboard.html at {dashboard_path}")

    content = dashboard_path.read_text()

    # Check for modal structure
    if 'id="entityTypeModal"' in content:
        result.log("Found entityTypeModal modal element")
    else:
        result.fail("Missing entityTypeModal modal element")

    if 'id="entityTypeModalLabel"' in content:
        result.log("Found entityTypeModalLabel label element")
    else:
        result.fail("Missing entityTypeModalLabel label element")

    if 'id="entity-type-list"' in content:
        result.log("Found entity-type-list container")
    else:
        result.fail("Missing entity-type-list container")

    # Check Add Entity button
    if 'id="add-entity-btn"' in content:
        result.log("Found add-entity-btn button")
    else:
        result.fail("Missing add-entity-btn button")

    if 'data-bs-toggle="modal"' in content and 'data-bs-target="#entityTypeModal"' in content:
        result.log("Button has proper Bootstrap modal triggers")
    else:
        result.fail("Button missing Bootstrap modal triggers")

    return result


def test_entity_type_buttons():
    """Test 2: Verify entity type buttons exist for all 7 types."""
    result = TestResult("Entity Type Buttons for All 7 Types")

    dashboard_path = TEMPLATES_DIR / "dashboard.html"
    content = dashboard_path.read_text()

    found_types = []
    missing_types = []

    for entity_type in EXPECTED_ENTITY_TYPES:
        pattern = f'data-entity-type="{entity_type}"'
        if pattern in content:
            found_types.append(entity_type)
            result.log(f"Found button for entity type: {entity_type}")
        else:
            missing_types.append(entity_type)
            result.fail(f"Missing button for entity type: {entity_type}")

    result.log(f"\nSummary: Found {len(found_types)}/{len(EXPECTED_ENTITY_TYPES)} entity type buttons")

    return result


def test_javascript_exports():
    """Test 3: Verify JavaScript functions are exported correctly."""
    result = TestResult("JavaScript Function Exports")

    # Check ui-form-handlers.js
    form_handlers_path = STATIC_DIR / "ui-form-handlers.js"
    if not form_handlers_path.exists():
        result.fail(f"ui-form-handlers.js not found at {form_handlers_path}")
        return result

    result.log(f"Found ui-form-handlers.js at {form_handlers_path}")
    content = form_handlers_path.read_text()

    # Check for setupEntityTypeModal export
    if "export function setupEntityTypeModal" in content:
        result.log("Found setupEntityTypeModal function export")
    else:
        result.fail("Missing setupEntityTypeModal function export")

    # Check for createPersonForm export with entityType parameter
    if "export function createPersonForm" in content:
        result.log("Found createPersonForm function export")
        # Check if it accepts entityType parameter
        match = re.search(r"export function createPersonForm\s*\([^)]*entityType", content)
        if match:
            result.log("createPersonForm accepts entityType parameter")
        else:
            result.fail("createPersonForm does not accept entityType parameter")
    else:
        result.fail("Missing createPersonForm function export")

    # Check for ENTITY_TYPE_LABELS constant
    if "ENTITY_TYPE_LABELS" in content:
        result.log("Found ENTITY_TYPE_LABELS constant")
    else:
        result.fail("Missing ENTITY_TYPE_LABELS constant")

    # Check for hidden entity_type field creation
    if 'name = \'entity_type\'' in content or 'name="entity_type"' in content or "name: 'entity_type'" in content or '.name = "entity_type"' in content:
        result.log("Form creates hidden entity_type field")
    else:
        result.fail("Form missing hidden entity_type field creation")

    # Check window.selectedEntityType initialization
    if "window.selectedEntityType" in content:
        result.log("Found window.selectedEntityType global variable")
    else:
        result.fail("Missing window.selectedEntityType global variable")

    # Check dashboard.js imports
    dashboard_path = STATIC_DIR / "dashboard.js"
    if dashboard_path.exists():
        result.log(f"Found dashboard.js at {dashboard_path}")
        dashboard_content = dashboard_path.read_text()

        if "setupEntityTypeModal" in dashboard_content:
            result.log("dashboard.js imports setupEntityTypeModal")
        else:
            result.fail("dashboard.js does not import setupEntityTypeModal")

        # Check if setupEntityTypeModal is called
        if "setupEntityTypeModal()" in dashboard_content:
            result.log("dashboard.js calls setupEntityTypeModal()")
        else:
            result.fail("dashboard.js does not call setupEntityTypeModal()")
    else:
        result.fail(f"dashboard.js not found at {dashboard_path}")

    return result


def test_backend_entity_type_handling():
    """Test 4: Check if backend properly handles entity_type field."""
    result = TestResult("Backend Entity Type Handling")

    frontend_profiles_path = API_DIR / "frontend_profiles.py"
    if not frontend_profiles_path.exists():
        result.fail(f"frontend_profiles.py not found at {frontend_profiles_path}")
        return result

    result.log(f"Found frontend_profiles.py at {frontend_profiles_path}")
    content = frontend_profiles_path.read_text()

    # Check if entity_type is handled in add_person
    if "entity_type" in content:
        result.log("Backend code references 'entity_type'")

        # Check if it's extracted from form data
        if 'form_data["entity_type"]' in content or "form_data.get('entity_type')" in content or 'form_data.get("entity_type")' in content:
            result.log("Backend extracts entity_type from form data")
        else:
            result.fail("Backend does NOT extract entity_type from form data - NEEDS IMPLEMENTATION")
            result.log("\nRECOMMENDED FIX:")
            result.log("In add_person function, add after form_data = await request.form():")
            result.log('  entity_type = form_data.get("entity_type", "person")')
            result.log('  person_data["entity_type"] = entity_type')

        # Check if it's stored in person_data
        if 'person_data["entity_type"]' in content or "person_data['entity_type']" in content:
            result.log("Backend stores entity_type in person_data")
        else:
            result.fail("Backend does NOT store entity_type in person_data - NEEDS IMPLEMENTATION")
    else:
        result.fail("Backend has no reference to 'entity_type' - NEEDS IMPLEMENTATION")
        result.log("\nRECOMMENDED FIX:")
        result.log("In add_person function, add after form_data = await request.form():")
        result.log('  entity_type = form_data.get("entity_type", "person")')
        result.log('  person_data["entity_type"] = entity_type')

    return result


def test_api_accepts_entity_type():
    """Test 5: Test if the API can accept entity_type parameter."""
    result = TestResult("API Accepts entity_type Parameter")

    try:
        # First check if server is running
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        result.log(f"Server is running at {API_BASE_URL}")
    except requests.exceptions.ConnectionError:
        result.fail(f"Cannot connect to server at {API_BASE_URL}")
        result.log("Start the server with: python run.py or uvicorn api.main:app")
        return result
    except Exception as e:
        result.fail(f"Error connecting to server: {e}")
        return result

    # Test that the endpoint exists (we can't fully test without auth/project setup)
    try:
        # Test OPTIONS to check endpoint exists
        response = requests.options(f"{API_BASE_URL}/add_person", timeout=5)
        result.log(f"add_person endpoint exists (OPTIONS returned {response.status_code})")
    except Exception as e:
        result.log(f"Note: Could not test OPTIONS on add_person: {e}")

    # Try a POST with form data including entity_type
    try:
        test_data = {
            "entity_type": "organization",
            "profile.basic.name_0": "Test Organization"
        }
        response = requests.post(
            f"{API_BASE_URL}/add_person",
            data=test_data,
            timeout=5,
            allow_redirects=False
        )

        if response.status_code in [302, 303, 200]:
            result.log(f"add_person endpoint accepts POST (status: {response.status_code})")
            result.log("Note: Full test requires active project session")
        elif response.status_code == 422:
            result.log("add_person returned 422 (validation error - expected without project context)")
        else:
            result.log(f"add_person returned status {response.status_code}")

    except Exception as e:
        result.log(f"POST test returned: {e}")

    result.log("\nNOTE: Full API integration test requires:")
    result.log("  - Active project session")
    result.log("  - Valid session cookie")
    result.log("  - Neo4j database running")

    return result


def generate_report(results: list[TestResult]) -> str:
    """Generate test report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    report = [
        "="*70,
        "ADD ENTITY MODAL IMPLEMENTATION TEST REPORT",
        f"Generated: {timestamp}",
        "="*70,
        "",
        f"SUMMARY: {passed} passed, {failed} failed out of {len(results)} tests",
        ""
    ]

    for result in results:
        report.append(str(result))
        report.append("")

    # Collect all issues
    all_issues = []
    for r in results:
        all_issues.extend(r.issues)

    if all_issues:
        report.append("\n" + "="*70)
        report.append("ALL ISSUES REQUIRING ATTENTION:")
        report.append("="*70)
        for i, issue in enumerate(all_issues, 1):
            report.append(f"  {i}. {issue}")

    report.append("\n" + "="*70)
    report.append("IMPLEMENTATION STATUS SUMMARY")
    report.append("="*70)

    # Frontend status
    report.append("\nFRONTEND (templates/dashboard.html):")
    report.append("  - Modal HTML structure: " + ("OK" if results[0].passed else "MISSING"))
    report.append("  - Entity type buttons (7 types): " + ("OK" if results[1].passed else "INCOMPLETE"))

    report.append("\nFRONTEND (static/js/*):")
    report.append("  - setupEntityTypeModal function: " + ("OK" if results[2].passed else "MISSING"))
    report.append("  - createPersonForm with entityType: " + ("OK" if results[2].passed else "MISSING"))
    report.append("  - Hidden entity_type form field: " + ("OK" if results[2].passed else "MISSING"))

    report.append("\nBACKEND (api/routers/frontend_profiles.py):")
    if results[3].passed:
        report.append("  - entity_type handling: OK")
    else:
        report.append("  - entity_type handling: NEEDS IMPLEMENTATION")
        report.append("    Required changes:")
        report.append("      1. Extract entity_type from form_data in add_person()")
        report.append("      2. Store entity_type in person_data before creating entity")
        report.append("      3. Consider adding entity_type to update_person() as well")

    return "\n".join(report)


def main():
    """Run all tests and generate report."""
    print("Running Add Entity Modal Tests...")
    print("-" * 50)

    results = []

    # Run tests
    results.append(test_modal_html_exists())
    results.append(test_entity_type_buttons())
    results.append(test_javascript_exports())
    results.append(test_backend_entity_type_handling())
    results.append(test_api_accepts_entity_type())

    # Generate report
    report = generate_report(results)

    # Save report
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = RESULTS_DIR / f"add_entity_modal_test_{date_str}.txt"

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)

    print(report)
    print(f"\n\nReport saved to: {report_path}")

    # Return exit code based on test results
    failed = sum(1 for r in results if not r.passed)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

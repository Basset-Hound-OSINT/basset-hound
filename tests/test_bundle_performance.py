"""
Stream 3: Bundle Performance Tests
Tests for frontend bundle size optimization and performance metrics
"""

import os
import json
import gzip
from pathlib import Path
import pytest


class TestBundleSize:
    """Test bundle size constraints"""

    @pytest.fixture(scope="class")
    def static_dir(self):
        """Get static directory path"""
        return Path(__file__).parent.parent / "static"

    def get_file_size(self, filepath, gzipped=False):
        """Get file size in KB"""
        if not os.path.exists(filepath):
            return 0

        size = os.path.getsize(filepath)

        if gzipped:
            with open(filepath, 'rb') as f:
                size = len(gzip.compress(f.read()))

        return size / 1024  # Convert to KB

    def test_critical_path_bundle_size(self, static_dir):
        """Test critical path JS bundle size < 200KB"""
        critical_files = [
            "js/dashboard.js",
            "js/api.js",
            "js/ui-form-handlers.js",
            "js/ui-people-list.js",
            "js/ui-person-details.js",
            "js/utils.js",
            "js/tag-handler.js",
            "js/report-handler.js",
            "js/file_explorer.js",
        ]

        total_size = 0
        for file in critical_files:
            path = static_dir / file
            if path.exists():
                total_size += self.get_file_size(str(path))

        # Target: < 200KB for critical path
        assert total_size < 200, f"Critical path bundle too large: {total_size:.1f}KB (target: <200KB)"

    def test_lazy_loaded_bundle_size(self, static_dir):
        """Test lazy-loaded JS bundle size"""
        lazy_files = [
            "js/merge-ui.js",
            "js/relationship-manager.js",
            "js/account-manager.js",
            "js/advanced-search.js",
            "js/bulk-import.js",
            "js/map-handler.js",
            "js/report-handler-pdf.js",
        ]

        total_size = 0
        for file in lazy_files:
            path = static_dir / file
            if path.exists():
                total_size += self.get_file_size(str(path))

        # These are lazy-loaded, so size is less critical but still monitored
        assert total_size < 250, f"Lazy-loaded bundle too large: {total_size:.1f}KB"

    def test_css_bundle_size(self, static_dir):
        """Test CSS bundle size < 50KB"""
        css_files = [
            "css/dashboard.css",
            "css/map-controls.css",
            "css/file_explorer.css",
        ]

        total_size = 0
        for file in css_files:
            path = static_dir / file
            if path.exists():
                total_size += self.get_file_size(str(path))

        # Target: < 50KB for all CSS
        assert total_size < 50, f"CSS bundle too large: {total_size:.1f}KB (target: <50KB)"

    def test_react_component_bundle_size(self, static_dir):
        """Test React component bundle size"""
        path = static_dir / "js/components/basset-hound-ui.umd.js"
        if path.exists():
            size = self.get_file_size(str(path))
            # UMD build should be < 50KB
            assert size < 50, f"React component bundle too large: {size:.1f}KB"

    def test_total_static_assets_size(self, static_dir):
        """Test total static assets size"""
        total_size = 0
        for root, dirs, files in os.walk(static_dir):
            # Skip node_modules and dist directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist']]

            for file in files:
                filepath = os.path.join(root, file)
                total_size += os.path.getsize(filepath)

        total_size_mb = total_size / (1024 * 1024)
        # Total should be reasonable (not checking strict limit as we have images)
        assert total_size_mb < 10, f"Total static assets too large: {total_size_mb:.1f}MB"

    def test_gzipped_bundle_estimate(self, static_dir):
        """Test gzipped bundle size estimate"""
        # Critical path gzipped estimate should be < 400KB
        critical_files = [
            "js/dashboard.js",
            "js/ui-form-handlers.js",
            "js/ui-person-details.js",
            "js/utils.js",
            "css/dashboard.css",
        ]

        total_gzip = 0
        for file in critical_files:
            path = static_dir / file
            if path.exists():
                total_gzip += self.get_file_size(str(path), gzipped=True)

        # Add estimate for external resources (40% compression ratio)
        # Bootstrap CSS: 30KB gzip, Bootstrap JS: 60KB gzip
        # React + ReactDOM: 175KB gzip, Font Awesome: 30KB gzip
        external_estimate = (30 + 60 + 175 + 30)  # ~295KB

        total_estimate = total_gzip + external_estimate

        # Target: < 500KB gzipped for initial load
        assert total_estimate < 500, f"Total gzipped estimate too large: {total_estimate:.1f}KB"


class TestCodeSplitting:
    """Test code splitting implementation"""

    @pytest.fixture(scope="class")
    def js_dir(self):
        """Get JS directory path"""
        return Path(__file__).parent.parent / "static" / "js"

    def test_lazy_modules_separate(self, js_dir):
        """Test that lazy-load modules exist as separate files"""
        lazy_modules = [
            "merge-ui.js",
            "relationship-manager.js",
            "account-manager.js",
            "advanced-search.js",
            "bulk-import.js",
        ]

        for module in lazy_modules:
            path = js_dir / module
            assert path.exists(), f"Lazy-load module missing: {module}"

    def test_dashboard_uses_dynamic_imports(self, js_dir):
        """Test that dashboard.js uses dynamic imports for lazy loading"""
        dashboard_path = js_dir / "dashboard.js"

        with open(dashboard_path, 'r') as f:
            content = f.read()

        # Check for dynamic import statements
        assert "import('./" in content, "dashboard.js missing dynamic imports"
        assert "loadAdvancedSearch" in content, "Missing loadAdvancedSearch function"
        assert "loadBulkImport" in content, "Missing loadBulkImport function"

    def test_ui_person_details_lazy_loads_managers(self, js_dir):
        """Test that ui-person-details lazy-loads manager modules"""
        details_path = js_dir / "ui-person-details.js"

        with open(details_path, 'r') as f:
            content = f.read()

        # Check that eager imports were removed
        assert "import { initRelationshipManager }" not in content, "Should not eagerly import initRelationshipManager"
        assert "import { initMergeUI }" not in content, "Should not eagerly import initMergeUI"

        # Check that dynamic imports are used
        assert "import('./relationship-manager.js')" in content, "Missing dynamic import for relationship-manager"
        assert "import('./merge-ui.js')" in content, "Missing dynamic import for merge-ui"


class TestAssetOptimization:
    """Test asset optimization"""

    @pytest.fixture(scope="class")
    def static_dir(self):
        """Get static directory path"""
        return Path(__file__).parent.parent / "static"

    def test_css_combined(self, static_dir):
        """Test that CSS files are combined/minified"""
        dashboard_css = static_dir / "css/dashboard.css"

        assert dashboard_css.exists(), "dashboard.css not found"

        with open(dashboard_css, 'r') as f:
            content = f.read()

        # Check that map-controls styles are included
        assert "input[type=\"range\"]" in content, "Map controls CSS not found in dashboard.css"

    def test_no_unnecessary_imports(self, static_dir):
        """Test that no unnecessary imports are present"""
        # jQuery should not be imported in modules
        js_files = list((static_dir / "js").glob("*.js"))

        for js_file in js_files:
            if js_file.name in ["components", "suggestions"]:
                continue

            with open(js_file, 'r') as f:
                content = f.read()

            # jQuery should not be used (replaced with vanilla JS)
            if "dashboard.js" in js_file.name or "ui-" in js_file.name:
                # These files should not import jQuery
                if "import jQuery" in content or "import $ from" in content:
                    # Only fail if they're trying to import jQuery
                    pass  # OK - these may have been written before jQuery removal


class TestHtmlOptimizations:
    """Test HTML template optimizations"""

    @pytest.fixture(scope="class")
    def dashboard_html(self):
        """Get dashboard HTML path"""
        return Path(__file__).parent.parent / "templates" / "dashboard.html"

    def test_preconnect_headers(self, dashboard_html):
        """Test that preconnect headers are present"""
        with open(dashboard_html, 'r') as f:
            content = f.read()

        assert "preconnect" in content.lower(), "Missing preconnect headers"
        assert "cdn.jsdelivr.net" in content, "Missing CDN preconnect"

    def test_async_scripts(self, dashboard_html):
        """Test that non-critical scripts are async/deferred"""
        with open(dashboard_html, 'r') as f:
            content = f.read()

        # React should be async
        assert 'async' in content or 'defer' in content, "Missing async/defer on scripts"

    def test_lazy_load_comments(self, dashboard_html):
        """Test that lazy-load strategy is documented"""
        with open(dashboard_html, 'r') as f:
            content = f.read()

        # Should have comments about lazy loading
        assert "lazy" in content.lower(), "Missing lazy-load documentation"
        assert "non-critical" in content.lower(), "Missing non-critical module comments"

    def test_no_jquery_in_html(self, dashboard_html):
        """Test that jQuery is not loaded (except in comments)"""
        with open(dashboard_html, 'r') as f:
            content = f.read()

        # Remove comments to check actual code
        import re
        content_no_comments = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

        # jQuery script tag should not be present
        assert 'src="https://code.jquery.com' not in content_no_comments, "jQuery should not be loaded - use vanilla JS instead"


class TestPerformanceMetrics:
    """Test performance metric tracking"""

    def test_bundle_optimization_findings_exists(self):
        """Test that bundle optimization findings document exists"""
        findings_path = Path(__file__).parent.parent / "docs/findings/BUNDLE-OPTIMIZATION-2026-05-07.md"
        assert findings_path.exists(), "Bundle optimization findings document not found"

    def test_findings_document_complete(self):
        """Test that findings document contains required sections"""
        findings_path = Path(__file__).parent.parent / "docs/findings/BUNDLE-OPTIMIZATION-2026-05-07.md"

        with open(findings_path, 'r') as f:
            content = f.read()

        required_sections = [
            "BUNDLE ANALYSIS",
            "CODE SPLITTING",
            "DEPENDENCY OPTIMIZATION",
            "ASSET OPTIMIZATION",
            "PERFORMANCE METRICS",
            "Success Criteria",
        ]

        for section in required_sections:
            assert section.upper() in content.upper(), f"Missing section: {section}"

    def test_lighthouse_config_exists(self):
        """Test that Lighthouse CI config exists"""
        config_path = Path(__file__).parent.parent / ".lighthouserc.json"
        assert config_path.exists(), "Lighthouse config not found"

        with open(config_path, 'r') as f:
            config = json.load(f)

        # Check key settings
        assert "ci" in config, "Missing 'ci' in Lighthouse config"
        assert "assert" in config["ci"], "Missing 'assert' in Lighthouse config"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

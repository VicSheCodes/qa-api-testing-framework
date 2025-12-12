"""
Test suite for analyzing OpenAPI schema to plan tests

Usage:
Download schema and run discovery
pytest -v tests/schema/test_schema_discovery.py

Run with Allure reporting
pytest tests/schema/test_schema_discovery.py --alluredir=allure-results

Run only specific test
pytest tests/schema/test_schema_discovery.py::TestSchemaDiscovery::test_extract_test_endpoints -v
"""

import pytest
import requests
from conftest import SSL_VERIFY
from config.logger_config import get_test_logger
from constants import (
    OPENAPI_YAML_ENDPOINT,
    SCHEMA_DOWNLOAD_TIMEOUT
)

logger = get_test_logger()


@pytest.mark.schema
@pytest.mark.smoke
class TestSchemaDiscovery:
    """Analyze OpenAPI schema for test planning"""

    def test_yaml_availability(self, base_url):
        """Test OpenAPI YAML endpoint is accessible"""
        from conftest import SSL_VERIFY

        endpoint = f"{base_url}{OPENAPI_YAML_ENDPOINT}"

        response = requests.get(
            endpoint,
            timeout=SCHEMA_DOWNLOAD_TIMEOUT,
            verify=SSL_VERIFY
        )

        assert response.status_code == 200
        assert len(response.text) > 0
        logger.info(f"✓ OpenAPI YAML schema available at {endpoint}")

    def test_schema_structure(self, openapi_schema):
        """Validate OpenAPI schema structure"""
        assert "openapi" in openapi_schema
        assert openapi_schema["openapi"].startswith("3.")
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

        logger.info(f" Valid OpenAPI {openapi_schema['openapi']} schema")

    def test_list_all_endpoints(self, openapi_schema):
        """List all documented endpoints"""
        paths = openapi_schema.get("paths", {})

        logger.info("\n=== ALL DOCUMENTED ENDPOINTS ===")
        for path in sorted(paths.keys()):
            methods = list(paths[path].keys())
            logger.info(f"{path}: {', '.join(methods).upper()}")

        assert len(paths) > 0, "No endpoints found in schema"

    def test_extract_test_endpoints(self, schema_manager):
        """Extract all /api/test/* endpoints"""
        test_endpoints = schema_manager.get_all_test_endpoints()

        logger.info(f"\n=== TEST ENDPOINTS ({len(test_endpoints)}) ===")
        for endpoint in test_endpoints:
            logger.info(f"  - {endpoint}")

        assert len(test_endpoints) == 6, \
            f"Expected 6 test endpoints, found {len(test_endpoints)}"

    def test_authentication_scheme(self, openapi_schema):
        """Verify authentication scheme is documented"""
        components = openapi_schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        assert "bearerAuth" in security_schemes, \
            "Bearer authentication not defined in schema"

        bearer_auth = security_schemes["bearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"

        logger.info("✓ Bearer authentication properly defined")

    def test_schema_version(self, openapi_schema):
        """Log OpenAPI version and API info"""
        openapi_version = openapi_schema.get("openapi", "unknown")
        api_info = openapi_schema.get("info", {})

        logger.info(f"\n=== API INFORMATION ===")
        logger.info(f"OpenAPI Version: {openapi_version}")
        logger.info(f"API Title: {api_info.get('title', 'N/A')}")
        logger.info(f"API Version: {api_info.get('version', 'N/A')}")
        logger.info(f"Description: {api_info.get('description', 'N/A')}")

        assert openapi_version.startswith("3."), \
            f"Expected OpenAPI 3.x, got {openapi_version}"
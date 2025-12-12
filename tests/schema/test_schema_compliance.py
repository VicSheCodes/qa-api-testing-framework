"""
Tests to validate API responses against OpenAPI schema
Validate all endpoints against schema
pytest -v tests/schema/test_schema_compliance.py

Generate Allure report with schema validation
pytest tests/schema/ --alluredir=allure-results
allure generate allure-results --single-file --clean -o reports/allure
"""

import pytest
import requests
from jsonschema import validate, ValidationError
from config.logger_config import get_test_logger
from constants import (
    TEST_ENDPOINT_1, TEST_ENDPOINT_2, TEST_ENDPOINT_3,
    TEST_ENDPOINT_4, TEST_ENDPOINT_5, TEST_ENDPOINT_6,
    HTTP_OK
)
from conftest import SSL_VERIFY

logger = get_test_logger()


@pytest.mark.schema
@pytest.mark.regression
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
class TestSchemaCompliance:
    """
    Validate API responses against OpenAPI schema
    :param endpoint_path: Parametrized test endpoint path
    :param openapi_schema: Fixture providing loaded OpenAPI schema
    :param base_url: Fixture providing base URL of the API server
    :param headers: Fixture providing authorization headers
    """

    def test_endpoint_exists_in_schema(self, endpoint_path, openapi_schema):
        """Verify endpoint is documented in OpenAPI schema"""
        paths = openapi_schema.get("paths", {})

        assert endpoint_path in paths, \
            f"Endpoint {endpoint_path} not found in OpenAPI schema"

        logger.info(f"✓ {endpoint_path} exists in schema")

    def test_endpoint_supports_get_method(self, endpoint_path, openapi_schema):
        """Verify GET method is documented for endpoint"""
        endpoint_spec = openapi_schema["paths"][endpoint_path]

        assert "get" in endpoint_spec, \
            f"GET method not documented for {endpoint_path}"

        logger.info(f"✓ {endpoint_path} supports GET method")

    def test_endpoint_requires_authentication(self, endpoint_path, openapi_schema):
        """Verify endpoint requires Bearer authentication"""
        endpoint_spec = openapi_schema["paths"][endpoint_path]["get"]

        security = endpoint_spec.get("security", [])

        # Check if bearerAuth is required
        has_bearer_auth = any("bearerAuth" in sec for sec in security)

        assert has_bearer_auth, \
            f"Bearer authentication not required for {endpoint_path}"

        logger.info(f"✓ {endpoint_path} requires authentication")

    def test_response_structure_matches_schema(self, base_url, headers,
                                               endpoint_path, openapi_schema):
        """Validate actual response against schema definition"""
        # Make request
        response = requests.get(
            f"{base_url}{endpoint_path}",
            headers=headers,
            verify=SSL_VERIFY
        )

        # Only validate successful responses
        if response.status_code != HTTP_OK:
            pytest.skip(f"Endpoint returned {response.status_code}, skipping schema validation")

        # Get expected schema
        endpoint_spec = openapi_schema["paths"][endpoint_path]["get"]
        response_schema = endpoint_spec["responses"]["200"]["content"]["application/json"]["schema"]

        # Validate response against schema
        try:
            response_json = response.json()
            validate(instance=response_json, schema=response_schema)
            logger.info(f"✓ {endpoint_path} response matches schema")
        except ValidationError as e:
            pytest.fail(f"Schema validation failed: {e.message}")
        except Exception as e:
            pytest.fail(f"Failed to validate schema: {e}")

    def test_response_content_type(self, base_url, headers, endpoint_path, openapi_schema):
        """Verify Content-Type header matches schema"""
        response = requests.get(
            f"{base_url}{endpoint_path}",
            headers=headers,
            verify=SSL_VERIFY
        )

        if response.status_code != HTTP_OK:
            pytest.skip(f"Endpoint returned {response.status_code}")

        # Get expected content type from schema
        endpoint_spec = openapi_schema["paths"][endpoint_path]["get"]
        expected_content_types = list(endpoint_spec["responses"]["200"]["content"].keys())

        actual_content_type = response.headers.get("Content-Type", "").split(";")[0]

        assert actual_content_type in expected_content_types, \
            f"Content-Type mismatch: expected {expected_content_types}, got {actual_content_type}"

        logger.info(f"✓ {endpoint_path} returns correct Content-Type")
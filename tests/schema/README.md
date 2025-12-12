# Schema Validation Tests

## Overview
Tests that validate API responses against OpenAPI schema definitions.

## Running Tests

### Discovery Tests (Analyze Schema)
```bash
# Run all schema discovery tests
pytest -v tests/schema/test_schema_discovery.py

# Run specific discovery test
pytest tests/schema/test_schema_discovery.py::TestSchemaDiscovery::test_extract_test_endpoints -v
```

### Compliance Tests (Validate Responses)
```bash
# Validate all endpoints against schema
pytest -v tests/schema/test_schema_compliance.py

# Test specific endpoint
pytest tests/schema/test_schema_compliance.py -k "test_endpoint_1" -v
```

### Generate reports
```bash
# Run with Allure
pytest tests/schema/ --alluredir=allure-results
allure generate allure-results --clean -o reports/allure
open reports/allure/index.html
```

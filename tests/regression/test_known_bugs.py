import allure
import pytest
import requests
import time
from allure_commons.types import AttachmentType
from conftest import SSL_VERIFY
from constants import (
    REQUEST_TIMEOUT,
    TEST_ENDPOINT_4,
    HTTP_OK,
)

# Specific performance threshold for endpoint 4 (discovered bug)
ENDPOINT_4_PERFORMANCE_THRESHOLD = 2.0  # seconds - stricter than generic 5s


# class TestEndpoint4RegressionBug:
#     """Regression tests for known endpoint 4 performance issue"""
#
#     @allure.story("Regression - Performance Bug")
#     @allure.title("Endpoint 4 should not exceed 2 second response time")
#     @allure.severity(allure.severity_level.NORMAL)
#     @allure.tag("regression", "performance", "endpoint-4")
#     def test_endpoint_4_performance_regression(self, base_url, headers):
#         """Verify endpoint 4 performance issue is fixed"""
#         with allure.step(f"Make request to endpoint 4 with {ENDPOINT_4_PERFORMANCE_THRESHOLD}s threshold"):
#             start_time = time.time()
#             response = requests.get(
#                 f"{base_url}{TEST_ENDPOINT_4}",
#                 headers=headers,
#                 timeout=REQUEST_TIMEOUT,
#                 verify=SSL_VERIFY
#             )
#             response_time = time.time() - start_time
#
#             assert response.status_code == HTTP_OK, f"Expected 200, got {response.status_code}"
#
#             allure.attach(
#                 f"Endpoint 4 Response Time: {response_time:.3f}s\nThreshold: {ENDPOINT_4_PERFORMANCE_THRESHOLD}s\nStatus: {'PASS' if response_time < ENDPOINT_4_PERFORMANCE_THRESHOLD else 'FAIL'}",
#                 name="Performance Metrics",
#                 attachment_type=AttachmentType.TEXT
#             )
#
#             assert response_time < ENDPOINT_4_PERFORMANCE_THRESHOLD, \
#                 f"Endpoint 4 exceeds performance threshold: {response_time:.2f}s > {ENDPOINT_4_PERFORMANCE_THRESHOLD}s (KNOWN BUG)"# Tests for previously found bugs

class TestEP2NonFunctional:
    """Regression: EP2 always returns errors"""
    @allure.title("EP2 should return 200 (currently broken)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.tag("regression", "ep2")
    def test_ep2_functionality(self, base_url, headers):
        response = requests.get(f"{base_url}/api/test/2", headers=headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        assert response.status_code == HTTP_OK, f"EP2 broken: got {response.status_code}"


class TestEP3ColdStart:
    """Regression: EP3 requires warmup after idle"""
    @allure.title("EP3 should not require EP1 warmup")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("regression", "ep3", "coldstart")
    def test_ep3_no_coldstart_required(self, base_url, headers):
        time.sleep(65)  # Idle 60+ seconds
        response = requests.get(f"{base_url}/api/test/3", headers=headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        assert response.status_code == HTTP_OK, f"EP3 requires warmup: got {response.status_code}"


class TestEP5ArtificialDelay:
    """Regression: EP5 has hardcoded 4.3s delay"""
    @allure.title("EP5 should respond in <1s (not 4.3s)")
    @allure.severity(allure.severity_level.TRIVIAL)
    @allure.tag("regression", "ep5", "performance")
    def test_ep5_delay_removed(self, base_url, headers):
        start = time.time()
        response = requests.get(f"{base_url}/api/test/5", headers=headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"EP5 still has delay: {elapsed:.2f}s (should be <1s)"

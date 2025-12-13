import allure
import requests
import time
from allure_commons.types import AttachmentType
from conftest import SSL_VERIFY
from constants import (
    REQUEST_TIMEOUT,
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    HTTP_OK,
)
import pytest

PERFORMANCE_THRESHOLD = 2.5


@pytest.mark.parametrize("endpoint",
                            [TEST_ENDPOINT_1,
                            TEST_ENDPOINT_2,
                            TEST_ENDPOINT_3,
                            TEST_ENDPOINT_4,
                            TEST_ENDPOINT_5,
                            TEST_ENDPOINT_6])
class TestEndpointTimeoutHandling:
    """Test endpoint response time and timeout behavior"""

    @allure.story("Timeout Handling")
    @allure.title("Endpoint responds within acceptable time")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("resilience", "network", "timeout")
    def test_endpoint_timeout_handling(self, base_url, headers, endpoint):
        """Verify endpoint responds within REQUEST_TIMEOUT and performance threshold"""
        with allure.step(f"Make request to {endpoint}"):
            start_time = time.time()
            response = requests.get(
                f"{base_url}{endpoint}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY
            )
            response_time = time.time() - start_time

            assert response.status_code == HTTP_OK, f"Expected 200, got {response.status_code}"
            assert response_time < PERFORMANCE_THRESHOLD, f"Response too slow: {response_time:.2f}s (threshold: {PERFORMANCE_THRESHOLD}s)"

            allure.attach(
                f"Status: {response.status_code}\nResponse Time: {response_time:.3f}s",
                name="Response Details",
                attachment_type=AttachmentType.TEXT
            )
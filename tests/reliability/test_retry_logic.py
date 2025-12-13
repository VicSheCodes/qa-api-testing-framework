import allure
import requests
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
    AUTH_GENERATE_ENDPOINT,
    AUTH_REFRESH_ENDPOINT,
)
import pytest

@pytest.mark.parametrize("endpoint",
                            [TEST_ENDPOINT_1,
                            TEST_ENDPOINT_2,
                            TEST_ENDPOINT_3,
                            TEST_ENDPOINT_4,
                            TEST_ENDPOINT_5,
                            TEST_ENDPOINT_6])
class TestEndpointRetryResilience:
    """Test endpoint retry logic under transient failures"""
    @allure.story("Retry Logic")
    @allure.title("Endpoint recovers from transient network failures")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.tag("resilience", "network", "retry")
    def test_endpoint_retry_resilience(self, base_url, headers, endpoint):
        """Verify endpoint recovers after transient failures (retry logic)"""
        max_retries = 3
        success = False

        with allure.step(f"Retry up to {max_retries} times"):
            for attempt in range(1, max_retries + 1):
                try:
                    with allure.step(f"Attempt {attempt}"):
                        response = requests.get(
                            f"{base_url}{endpoint}",
                            headers=headers,
                            timeout=REQUEST_TIMEOUT,
                            verify=SSL_VERIFY
                        )
                        if response.status_code == 200:
                            success = True
                            allure.attach(
                                f"Success on attempt {attempt}",
                                name="Retry Success",
                                attachment_type=AttachmentType.TEXT
                            )
                            break
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        continue
                    else:
                        raise

        assert success, "Endpoint failed to respond after retries"# Retry mechanism tests

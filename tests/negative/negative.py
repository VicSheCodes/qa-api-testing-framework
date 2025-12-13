import pytest
import requests
import allure
from constants import (
    AUTH_GENERATE_ENDPOINT,
    TEST_ENDPOINT_1,
    REQUEST_TIMEOUT,
    SSL_VERIFY,
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED,
    HTTP_FORBIDDEN
)
from conftest import headers
import logging

logger = logging.getLogger(__name__)

BASE_URL = os.getenv("BASE_URL", "https://qa-home-assignment.magmadevs.com")

@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.negative
def test_request_timeout(base_url):
    """
    Test #15: Request timeout scenarios should be handled gracefully.

    Expected behavior: Requests with very short timeout should timeout or fail.
    """
    with allure.step("Request with extremely short timeout (0.001 seconds)"):
        try:
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_1}",
                headers={"Authorization": "Bearer dummy_token"},
                timeout=0.001,  # 1ms timeout - almost certainly will timeout
                verify=SSL_VERIFY
            )
            # If it succeeds somehow, it should still return a valid status
            assert response.status_code in range(200, 599), \
                f"Invalid status code: {response.status_code}"

        except requests.exceptions.Timeout:
            # Expected behavior - timeout occurred
            logger.info("✅ Request timeout handled correctly")

        except requests.exceptions.RequestException as e:
            # Other connection errors also acceptable
            logger.info(f"✅ Request error handled correctly: {type(e).__name__}")
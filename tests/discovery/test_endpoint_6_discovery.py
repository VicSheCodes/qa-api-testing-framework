"""
# Test EP6
pytest tests/discovery/test_endpoint_6_discovery.py -v -s
"""

import pytest
import requests
import allure
import time
from constants import TEST_ENDPOINT_6, TEST_ENDPOINT_1, TEST_ENDPOINT_3, TEST_ENDPOINT_4, TEST_ENDPOINT_5
from conftest import SSL_VERIFY, _endpoint_results
from config.logger_config import get_test_logger

logger = get_test_logger()

@allure.feature("Endpoint 6 Discovery")
@allure.story("EP6 Basic Behavior Tests")
class TestEndpoint6Discovery:
    """Discover EP6 functionality and behavior patterns"""

    @allure.title("Test EP6 basic response")
    @pytest.mark.parametrize("endpoint_path", [TEST_ENDPOINT_6])
    def test_endpoint_6_basic_get(self, base_url, headers, endpoint_path):
        """Test basic EP6 GET request"""
        endpoint_url = f"{base_url}{endpoint_path}"

        logger.info(f"Testing EP6: {endpoint_url}")
        response = requests.get(endpoint_url, headers=headers, verify=SSL_VERIFY)

        logger.info(f"EP6 Status: {response.status_code}")
        logger.info(f"EP6 Response: {response.text[:200]}")

        allure.attach(
            f"Status: {response.status_code}\nBody: {response.text}",
            name="EP6 Response",
            attachment_type=allure.attachment_type.TEXT
        )

        assert response.status_code in [200, 429, 500, 503], \
            f"Unexpected status code: {response.status_code}"

    @allure.title("Test EP6 rate limit pattern")
    def test_endpoint_6_rate_limit(self, base_url, headers):
        """Test if EP6 has rate limiting"""
        endpoint_url = f"{base_url}{TEST_ENDPOINT_6}"

        logger.info("Testing EP6 rate limit...")
        status_codes = []

        for i in range(1, 21):
            response = requests.get(endpoint_url, headers=headers, verify=SSL_VERIFY)
            status_codes.append(response.status_code)
            logger.info(f"Request {i}: {response.status_code}")

            if response.status_code in [429, 503]:
                logger.info(f"Rate limit hit at request {i}")
                break

            time.sleep(0.5)

        logger.info(f"Status codes: {status_codes}")

        allure.attach(
            f"Request pattern: {status_codes}",
            name="EP6 Rate Limit Pattern",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Test EP6 response structure")
    def test_endpoint_6_response_structure(self, base_url, headers):
        """Verify EP6 returns structured data"""
        endpoint_url = f"{base_url}{TEST_ENDPOINT_6}"

        response = requests.get(endpoint_url, headers=headers, verify=SSL_VERIFY)

        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert "data" in data, "Missing 'data' field"
        assert "status" in data, "Missing 'status' field"
        assert "timestamp" in data, "Missing 'timestamp' field"

        # Validate nested data object
        assert "count" in data["data"]
        assert "id" in data["data"]
        assert "value" in data["data"]

        # Validate types
        assert isinstance(data["data"]["count"], int)
        assert isinstance(data["data"]["id"], int)
        assert isinstance(data["data"]["value"], int)

        logger.info(f"✓ EP6 response structure validated")


        @allure.title("Test cross-endpoint latency comparison")
        def test_cross_endpoint_latency(self, base_url, headers):
            """Compare latency across all working endpoints"""
            endpoints = {
                "EP1": TEST_ENDPOINT_1,
                "EP3": TEST_ENDPOINT_3,
                "EP4": TEST_ENDPOINT_4,
                "EP5": TEST_ENDPOINT_5,
                "EP6": TEST_ENDPOINT_6,
            }

            latencies = {}

            for name, path in endpoints.items():
                url = f"{base_url}{path}"
                start_time = time.time()
                response = requests.get(url, headers=headers, verify=SSL_VERIFY)
                latency = time.time() - start_time

                latencies[name] = latency
                logger.info(f"{name}: {latency:.3f}s ({response.status_code})")

            # Verify EP5 is slowest
            assert latencies["EP5"] > 4.0, "EP5 should have 4+ second delay"

            # Verify others are fast
            fast_endpoints = ["EP1", "EP3", "EP4", "EP6"]
            for ep in fast_endpoints:
                assert latencies[ep] < 1.0, \
                    f"{ep} should be fast (<1s), got {latencies[ep]:.3f}s"

            logger.info(f"✓ Latency comparison: EP5 is intentionally slow")
"""
Tests for discovering the behavior of Endpoint 5 (EP5) in the web service.
Usage:
# Test EP5
pytest tests/discovery/test_endpoint_5_discovery.py -v -s
"""

import pytest
import requests
import allure
import time
from constants import TEST_ENDPOINT_5
from conftest import SSL_VERIFY, _endpoint_results
from config.logger_config import get_test_logger

logger = get_test_logger()


@allure.feature("Endpoint 5 Discovery")
@allure.story("EP5 Basic Behavior Tests")
class TestEndpoint5Discovery:
    """Discover EP5 functionality and behavior patterns"""

    @allure.title("Test EP5 basic response")
    @pytest.mark.parametrize("endpoint_path", [TEST_ENDPOINT_5])
    def test_endpoint_5_basic_get(self, base_url, headers, endpoint_path):
        """Test basic EP5 GET request"""
        endpoint_url = f"{base_url}{endpoint_path}"

        logger.info(f"Testing EP5: {endpoint_url}")
        response = requests.get(endpoint_url, headers=headers, verify=SSL_VERIFY)

        logger.info(f"EP5 Status: {response.status_code}")
        logger.info(f"EP5 Response: {response.text[:200]}")

        allure.attach(
            f"Status: {response.status_code}\nBody: {response.text}",
            name="EP5 Response",
            attachment_type=allure.attachment_type.TEXT
        )

        assert response.status_code in [200, 429, 500, 503], \
            f"Unexpected status code: {response.status_code}"

    @allure.title("Test EP5 rate limit pattern")
    def test_endpoint_5_rate_limit(self, base_url, headers):
        """Test if EP5 has rate limiting"""
        endpoint_url = f"{base_url}{TEST_ENDPOINT_5}"

        logger.info("Testing EP5 rate limit...")
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
            name="EP5 Rate Limit Pattern",
            attachment_type=allure.attachment_type.TEXT
        )


    @allure.title("Test EP5 slow response pattern")
    def test_endpoint_5_consistent_delay(self, base_url, headers):
        """Verify EP5 has consistent ~4s delay"""
        endpoint_url = f"{base_url}{TEST_ENDPOINT_5}"

        logger.info("Testing EP5 consistent delay pattern...")
        latencies = []

        for i in range(5):
            start_time = time.time()
            response = requests.get(endpoint_url, headers=headers, verify=SSL_VERIFY)
            latency = time.time() - start_time

            latencies.append(latency)
            logger.info(f"Request {i+1}: {response.status_code} - {latency:.3f}s")

            assert response.status_code == 200
            assert 4.0 <= latency <= 4.5, \
                f"Expected ~4s delay, got {latency:.3f}s"

        avg_latency = sum(latencies) / len(latencies)
        variance = max(latencies) - min(latencies)

        logger.info(f"Average: {avg_latency:.3f}s, Variance: {variance:.3f}s")

        # Verify consistency (low variance = artificial delay)
        assert variance < 0.5, \
            f"Delay too variable ({variance:.3f}s) - expected artificial delay"

        logger.info(" Confirmed: EP5 has consistent 4-second artificial delay")
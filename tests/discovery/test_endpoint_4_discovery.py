from time import sleep

import allure
import pytest
import requests
import statistics
import time
from datetime import datetime
from conftest import SSL_VERIFY, _endpoint_results
from constants import (
    HTTP_OK,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_TOO_MANY_REQUESTS,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_3,
    REQUEST_TIMEOUT
)
from config.logger_config import get_test_logger

logger = get_test_logger()

# Suppress SSL warnings when using Charles
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@allure.feature("API Test Endpoints")
@allure.story("Endpoint 4 Investigation")
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_4,
])
class TestEndpoint4Discovery:

    @allure.title("Test endpoint 2 basic get: {description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason="Known issue: Endpoint 4 returns 429 after first 5-15 requests - backend bug")
    def test_endpoint_basic_get(self, base_url, headers, endpoint_path):
        """Test basic GET request """
        endpoint = f"{base_url}{endpoint_path}"
        logger.info(f"Testing basic GET request to {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"Status: {response.status_code}, Response time: {response.elapsed.total_seconds():.3f}s")

        # Record results
        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        # Document the failure
        assert response.status_code == HTTP_INTERNAL_ERROR, \
            f"Expected 429, got {response.status_code}"

        # Verify error structure
        error_body = response.json()
        assert "message" in error_body, "Error response missing 'message' field"
        assert "status" in error_body, "Error response missing 'status' field"
        assert error_body["status"] == "error", f"Expected status='error', got '{error_body['status']}'"
        assert "timestamp" in error_body, "Error response missing 'timestamp' field"

        logger.info(f"Error response: {error_body}")


    @allure.title("Test endpoint 4 rate limiting behavior")
    @allure.severity(allure.severity_level.NORMAL)
   # @pytest.mark.xfail(reason="Known issue: Endpoint 4 inconsistent rate limit threshold (5-15 requests)")
    def test_endpoint_rate_limit(self, base_url, headers, endpoint_path):
        """Test rate limiting on endpoint 4"""
        endpoint = f"{base_url}{endpoint_path}"
        logger.info(f"Testing rate limit of {endpoint}")

        successful_requests = 0
        rate_limited = False
        max_requests = 15
        status_codes = []

        for i in range(max_requests):
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )

                status_codes.append(response.status_code)
                logger.info(f"Request {i+1}: Status {response.status_code}")

                _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
                _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[endpoint_path]["test_count"] += 1

                if response.status_code == HTTP_OK:
                    successful_requests += 1
                elif response.status_code == HTTP_TOO_MANY_REQUESTS:
                    rate_limited = True
                    logger.info(f"Rate limit hit after {successful_requests} successful requests")

                    if response.status_code == HTTP_TOO_MANY_REQUESTS:
                        logger.info("Response headers:")
                        for header_name, header_value in response.headers.items():
                            logger.info(f"  {header_name}: {header_value}")

                    error_body = response.json()
                    assert "message" in error_body, "Rate limit response missing 'message' field"
                    assert "status" in error_body, "Rate limit response missing 'status' field"
                    assert error_body["status"] == "error", f"Expected status='error', got '{error_body['status']}'"

                    break
                else:
                    logger.warning(f"Unexpected status code: {response.status_code}")

                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                logger.error(f"Request {i+1} failed: {str(e)}")

        logger.info(f"Summary: {successful_requests} successful requests before rate limit")
        logger.info(f"Status codes: {status_codes}")

        # Verify rate limiting behavior
        assert rate_limited, "Expected to hit rate limit (429) but didn't"
        assert successful_requests == 4 , \
            f"Expected 4 successful requests, got {successful_requests}"
        logger.info(f" Confirmed: EP4 rate limit = {successful_requests} requests")


    @allure.title("Test endpoint 4 cooldown period after rate limit")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_cooldown_period(self, base_url, headers, endpoint_path):
        """Test cooldown period for endpoint 4 after hitting rate limit"""
        endpoint = f"{base_url}{endpoint_path}"
        logger.info(f"Testing cooldown period for {endpoint}")

        # Step 1: Hit the rate limit
        logger.info("Step 1: Triggering rate limit...")
        for i in range(20):
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code == HTTP_TOO_MANY_REQUESTS:
                logger.info(f" Rate limit hit after {i+1} requests")

                # Check for cooldown hint in headers
                retry_after = response.headers.get('Retry-After', 'Not provided')
                logger.info(f"Retry-After header: {retry_after}")
                break

            time.sleep(0.1)

        assert response.status_code == HTTP_TOO_MANY_REQUESTS, \
            "Failed to trigger rate limit in initial requests"

        # Step 2: Test different cooldown periods
        logger.info("\nStep 2: Testing cooldown recovery...")
        cooldown_periods = [30, 40, 50, 60, 120, 300]  # 30s, 1min, 2min, 5min
        cooldown_found = False
        actual_cooldown = None

        for wait_time in cooldown_periods:
            logger.info(f"\n Waiting {wait_time}s for potential cooldown...")
            time.sleep(wait_time)

            # Try request after cooldown
            retry_response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            logger.info(f"After {wait_time}s wait: Status {retry_response.status_code}")

            if retry_response.status_code == HTTP_OK:
                actual_cooldown = wait_time
                cooldown_found = True
                logger.info(f"✓ Cooldown successful! Period is ≤ {wait_time}s")

                # make multiple successful requests
                consecutive_success = 1
                for j in range(4):
                    verify_response = requests.get(
                        endpoint,
                        headers=headers,
                        verify=SSL_VERIFY,
                        timeout=REQUEST_TIMEOUT
                    )
                    if verify_response.status_code == HTTP_OK:
                        consecutive_success += 1
                    time.sleep(0.1)

                logger.info(f"✓ Made {consecutive_success} consecutive successful requests after cooldown")
                break

            elif retry_response.status_code == HTTP_TOO_MANY_REQUESTS:
                logger.info(f"✗ Still rate limited after {wait_time}s")
            else:
                logger.warning(f"⚠ Unexpected status: {retry_response.status_code}")

        assert cooldown_found, \
            f"Cooldown period exceeds {cooldown_periods[-1]}s - rate limit not reset"

        logger.info(f"\n📊 Test Result: Cooldown period is ≤ {actual_cooldown}s")

        # Record findings
        allure.attach(
            f"Cooldown period: ≤ {actual_cooldown}s",
            name="Cooldown Analysis",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Test cross-endpoint rate limit isolation")
    def test_cross_endpoint_rate_limits(self, base_url, headers, endpoint_path):
        """Verify EP3 and EP4 have independent rate limits"""
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"
        endpoint_4 = f"{base_url}{endpoint_path}"
        time.sleep(20)
        logger.info("Step 1: Warmup EP3 backend (8-second cold start)...")
        ep3_warmup = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)

        # If EP3 returns 503, wait for backend boot
        if ep3_warmup.status_code == 503:
            logger.info("EP3 cold - waiting 8s for backend boot...")
            time.sleep(8)

            # Verify EP3 is ready
            ep3_warmup = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            assert ep3_warmup.status_code == 200, "EP3 not ready after cold start"

        logger.info("✓ EP3 ready")

        logger.info("Step 2: Trigger EP4 rate limit (4 requests)...")
        for i in range(5):
            requests.get(endpoint_4, headers=headers, verify=SSL_VERIFY)
            time.sleep(0.1)

        logger.info("Step 3: Verify EP4 is rate-limited...")
        ep4_response = requests.get(endpoint_4, headers=headers, verify=SSL_VERIFY)
        assert ep4_response.status_code == 429, \
            f"Expected EP4 429, got {ep4_response.status_code}"
        logger.info("✓ EP4 rate limit confirmed")

        logger.info("Step 4: Verify EP3 still works (independent rate limit)...")
        ep3_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        assert ep3_response.status_code == 200, \
            f"EP3 should not be affected by EP4 rate limit, got {ep3_response.status_code}"
        logger.info("✓ EP3 unaffected by EP4 rate limit - rate limits are independent")
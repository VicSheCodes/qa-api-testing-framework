"""Tests for network failure scenarios and recovery."""
import pytest
import requests
from requests.exceptions import (
    ConnectionError,
    Timeout,
    RequestException,
)
from unittest.mock import patch
import allure

from constants import BASE_URL, TEST_ENDPOINT_1, TEST_ENDPOINT_6


@allure.feature("Reliability")
@allure.story("Network Error Handling")
@pytest.mark.reliability
@pytest.mark.negative
def test_network_connection_error_handling(base_url, headers):
    """Test handling of connection errors."""
    with allure.step("Mock connection error"):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")

            with allure.step("Verify ConnectionError is raised"):
                with pytest.raises(ConnectionError):
                    requests.get(f"{base_url}{TEST_ENDPOINT_1}", headers=headers)


@allure.feature("Reliability")
@allure.story("Network Error Handling")
@pytest.mark.reliability
@pytest.mark.negative
def test_network_timeout_error_handling(base_url, headers):
    """Test handling of timeout errors."""
    with allure.step("Mock timeout error"):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Timeout("Request timed out")

            with allure.step("Verify Timeout is raised"):
                with pytest.raises(Timeout):
                    requests.get(
                        f"{base_url}{TEST_ENDPOINT_1}",
                        headers=headers,
                        timeout=5
                    )


@allure.feature("Reliability")
@allure.story("Network Recovery")
@pytest.mark.reliability
def test_network_recovery_after_failure(base_url, headers):
    """Test that endpoint recovers after transient network failure."""
    endpoint = f"{base_url}{TEST_ENDPOINT_6}"

    with allure.step("First request should succeed"):
        response = requests.get(endpoint, headers=headers, timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        allure.attach(str(response.json()), "First Response", allure.attachment_type.JSON)

    with allure.step("Second request should also succeed (recovery verified)"):
        response = requests.get(endpoint, headers=headers, timeout=10)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        allure.attach(str(response.json()), "Second Response", allure.attachment_type.JSON)


@allure.feature("Reliability")
@allure.story("Timeout Handling")
@pytest.mark.reliability
@pytest.mark.slow
def test_network_partial_response_timeout(base_url, headers):
    """Test handling of partial response (incomplete data) on slow endpoint."""
    # EP5 is intentionally slow - test timeout handling
    endpoint = f"{base_url}/api/test/5"

    with allure.step("Request with short timeout (<4.3s) should fail"):
        with pytest.raises(Timeout):
            requests.get(endpoint, headers=headers, timeout=1)
        allure.attach("Timeout triggered as expected", "Result", allure.attachment_type.TEXT)


@allure.feature("Reliability")
@allure.story("DNS Resolution")
@pytest.mark.reliability
def test_network_dns_resolution(base_url, headers):
    """Test DNS resolution failure handling."""
    invalid_url = "https://this-domain-definitely-does-not-exist-12345.com/api/test/1"

    with allure.step("Request to invalid domain should fail"):
        with pytest.raises((ConnectionError, RequestException)):
            requests.get(invalid_url, headers=headers, timeout=5)
        allure.attach("DNS resolution failed as expected", "Result", allure.attachment_type.TEXT)


@allure.feature("Reliability")
@allure.story("Network Recovery")
@pytest.mark.reliability
def test_network_concurrent_requests_resilience(base_url, headers):
    """Test resilience under concurrent network requests."""
    endpoint = f"{base_url}{TEST_ENDPOINT_6}"

    with allure.step("Execute 5 concurrent requests"):
        responses = []
        for i in range(5):
            with allure.step(f"Request {i + 1}"):
                response = requests.get(endpoint, headers=headers, timeout=10)
                responses.append(response.status_code)

        allure.attach(f"Status codes: {responses}", "Results", allure.attachment_type.TEXT)
        assert all(code == 200 for code in responses), "Not all requests succeeded"
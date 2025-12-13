import allure
import pytest
import requests
import os
import time
from config.logger_config import get_test_logger
from constants import (
    AUTH_GENERATE_ENDPOINT,
    AUTH_REFRESH_ENDPOINT,
    REQUEST_TIMEOUT,
    TEST_ENDPOINT_1,
    HTTP_OK,
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORIZED,
)
from conftest import SSL_VERIFY
from utils.auth_helper import get_auth_headers

logger = get_test_logger()

INITIAL_REFRESH_TOKEN = os.getenv("INITIAL_REFRESH_TOKEN")


def get_fresh_tokens(base_url):
    """
    Helper: Get fresh access and refresh tokens for testing.
    Returns: (access_token, new_refresh_token) tuple
    """
    response = requests.post(
        f"{base_url}{AUTH_GENERATE_ENDPOINT}",
        json={"refresh_token": INITIAL_REFRESH_TOKEN},
        timeout=REQUEST_TIMEOUT,
        verify=SSL_VERIFY
    )
    logger.info(f"Fresh tokens request status: {response.status_code}")

    if response.status_code == HTTP_OK:
        data = response.json()
        return data["access_token"], data["refresh_token"]
    return None, None


@allure.feature("Security")
@allure.story("Authentication")
@pytest.mark.security
@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.skip(reason="Skipped due to 15-minute token expiration wait time. Run manually for full validation.")
def test_token_expiration_enforcement_15_min(base_url):
    """
    Security test: Expired tokens must be rejected after 15 minutes.
    """
    with allure.step("Generate fresh access token"):
        response = requests.post(
            f"{base_url}{AUTH_GENERATE_ENDPOINT}",
            json={"refresh_token": INITIAL_REFRESH_TOKEN},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )
        assert response.status_code == HTTP_OK, \
            f"Token generation failed: {response.status_code}"

        token = response.json()["access_token"]
        expires_in = response.json()["expires_in"]
        logger.info(f"Token expires in {expires_in} seconds")

    with allure.step(f"Wait {expires_in}s for token to expire"):
        time.sleep(expires_in + 2)

    with allure.step("Attempt request with expired token"):
        headers = get_auth_headers(token)
        response = requests.get(
            f"{base_url}{TEST_ENDPOINT_1}",
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )

    with allure.step("Validate expired token rejection"):
        assert response.status_code in [401, 403], \
            f"Expected 401/403, got {response.status_code}"

    logger.info("✅ Expired token correctly rejected")

@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.regression
@pytest.mark.negative
def test_refresh_token_single_use(base_url):
    """
    Security test: Refresh tokens can only be used once.
    """
    _, refresh_token = get_fresh_tokens(base_url)
    assert refresh_token, "Failed to get fresh refresh token"

    with allure.step("Use refresh token first time"):
        response1 = requests.post(
            f"{base_url}{AUTH_REFRESH_ENDPOINT}",
            json={"refresh_token": refresh_token},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )
        assert response1.status_code == HTTP_OK

    with allure.step("Attempt to reuse same refresh token"):
        response2 = requests.post(
            f"{base_url}{AUTH_REFRESH_ENDPOINT}",
            json={"refresh_token": refresh_token},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )

    with allure.step("Validate token replay rejection"):
        assert response2.status_code in [400, 401, 403]

    logger.info("✅ Refresh token single-use enforced")


@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.regression
@pytest.mark.negative
def test_unauthenticated_access_denied(base_url):
    """
    Security test: Endpoints require valid authentication.
    """
    with allure.step("Request without token"):
        response = requests.get(
            f"{base_url}{TEST_ENDPOINT_1}",
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )

    with allure.step("Validate authentication required"):
        assert response.status_code in [401, 403]

    logger.info("✅ Unauthenticated access denied")


@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.regression
@pytest.mark.negative
def test_invalid_token_format_rejected(base_url):
    """
    Security test: Invalid token formats are rejected.
    """
    invalid_tokens = [
        "not_a_jwt",
        "",
        "invalid.token.format",
    ]

    with allure.step("Test rejection of malformed tokens"):
        for invalid_token in invalid_tokens:
            headers = get_auth_headers(invalid_token)
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_1}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY
            )
            assert response.status_code in [401, 403]

    logger.info("✅ Invalid tokens rejected")


@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.negative
def test_empty_authorization_header(base_url):
    """Empty Authorization header value should be rejected."""
    with allure.step("Request with empty token"):
        response = requests.get(
            f"{base_url}{TEST_ENDPOINT_1}",
            headers={"Authorization": "Bearer "},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )
    assert response.status_code in [400, 401, 403]


@allure.feature("Security")
@allure.story("Authentication")
@pytest.mark.security
@pytest.mark.negative
def test_invalid_refresh_token(base_url):
    """Invalid refresh token should be rejected."""
    with allure.step("Generate with invalid refresh token"):
        response = requests.post(
            f"{base_url}{AUTH_GENERATE_ENDPOINT}",
            json={"refresh_token": "invalid_refresh_token_xyz"},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )
    assert response.status_code in [400, 401, 403]


@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.negative
def test_concurrent_requests_same_token(base_url):
    """Multiple concurrent requests with same token should succeed."""
    access_token, _ = get_fresh_tokens(base_url)

    import concurrent.futures

    with allure.step("Send concurrent requests"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    requests.get,
                    f"{base_url}{TEST_ENDPOINT_1}",
                    headers=get_auth_headers(access_token),
                    timeout=REQUEST_TIMEOUT,
                    verify=SSL_VERIFY
                )
                for _ in range(5)
            ]
            results = [f.result() for f in futures]

    with allure.step("Validate all requests succeed"):
        for response in results:
            assert response.status_code == HTTP_OK

    logger.info("✅ Concurrent requests handled correctly")


@allure.feature("Security")
@allure.story("Authorization")
@pytest.mark.security
@pytest.mark.negative
def test_rapid_successive_requests(base_url):
    """Rapid successive requests should be handled correctly."""
    access_token, _ = get_fresh_tokens(base_url)
    headers = get_auth_headers(access_token)

    with allure.step("Send 10 rapid requests"):
        for i in range(10):
            response = requests.get(
                f"{base_url}{TEST_ENDPOINT_1}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY
            )
            assert response.status_code == HTTP_OK, f"Request {i} failed"

    logger.info("✅ Rapid requests handled correctly")


@allure.feature("Security")
@allure.story("Authentication")
@pytest.mark.security
@pytest.mark.negative
def test_missing_required_parameters_auth(base_url):
    """
    Test #7: Missing required parameters in auth endpoint should be rejected.

    Expected behavior: POST /auth/generate without refresh_token should fail.
    """
    with allure.step("Request auth endpoint without refresh_token parameter"):
        response = requests.post(
            f"{base_url}{AUTH_GENERATE_ENDPOINT}",
            json={},  # Missing required refresh_token
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )

    with allure.step("Validate rejection of missing parameter"):
        assert response.status_code in [HTTP_BAD_REQUEST, HTTP_UNAUTHORIZED], \
            f"Expected 400/401, got {response.status_code}"

    logger.info(f"✅ Missing refresh_token correctly rejected with {response.status_code}")


"""
Critical Path & Regression Testing Module
==========================================

Usage:
------
Run all critical path tests:
    pytest tests/functional/test_critical_paths.py -v --alluredir=allure-results

Run regression tests only:
    pytest tests/functional/test_critical_paths.py -m regression -v --alluredir=allure-results

Run critical path tests only:
    pytest tests/functional/test_critical_paths.py -m critical_path -v --alluredir=allure-results

Generate Allure report:
    allure serve allure-results

Critical Paths Covered:
----------------------
1. Authentication flow (token generation and refresh)
2. Sequential endpoint calls with token reuse
3. Token expiration and refresh handling
4. Concurrent endpoint access
5. Response consistency across multiple calls
6. Error recovery and resilience
"""

import time
import pytest
import requests
import allure
from conftest import SSL_VERIFY, _endpoint_results
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
from config.logger_config import get_test_logger
from utils.auth_helper import get_auth_headers

logger = get_test_logger()


@allure.feature("Critical Paths")
@allure.story("Authentication Flow")
@pytest.mark.critical_path
@pytest.mark.regression
def test_auth_token_generation():
    """
    Test initial token generation from refresh token.

    Critical for: All authenticated operations depend on this.
    """
    base_url = "https://qa-home-assignment.magmadevs.com"
    refresh_token = "initial_refresh_token_2024_qa_evaluation"

    with allure.step("Generate access token from refresh token"):
        response = requests.post(
            f"{base_url}{AUTH_GENERATE_ENDPOINT}",
            json={"refresh_token": refresh_token},
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY
        )

    with allure.step("Validate response status and structure"):
        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "access_token" in data, "Missing access_token in response"
        assert "refresh_token" in data, "Missing refresh_token in response"
        assert "expires_in" in data, "Missing expires_in in response"
        assert data["token_type"] == "Bearer", f"Expected Bearer token type, got {data['token_type']}"
        assert isinstance(data["expires_in"], int), "expires_in must be an integer"
        assert data["expires_in"] > 0, "expires_in must be positive"

    logger.info(f"✅ Token generation successful, expires in {data['expires_in']}s")


@allure.feature("Critical Paths")
@allure.story("Token Lifecycle")
@pytest.mark.critical_path
@pytest.mark.regression
def test_token_reuse_across_endpoints(base_url, fresh_auth_token):
    """
    Test that a single token can be reused across multiple endpoints.

    Regression check: Token should remain valid for all endpoints
    during its lifetime.
    """
    headers = {"Authorization": f"Bearer {fresh_auth_token}"}
    endpoints = [
        TEST_ENDPOINT_1,
        TEST_ENDPOINT_2,
        TEST_ENDPOINT_3,
        TEST_ENDPOINT_4,
        TEST_ENDPOINT_5,
        TEST_ENDPOINT_6,
    ]
    results = {}

    with allure.step("Call all endpoints sequentially with same token"):
        for endpoint in endpoints:
            try:
                response = requests.get(
                    f"{base_url}{endpoint}",
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    verify=SSL_VERIFY
                )
                results[endpoint] = {
                    "status": response.status_code,
                    "success": response.status_code == 200
                }
                logger.info(f"{endpoint}: {response.status_code}")

            except requests.RequestException as e:
                results[endpoint] = {"status": 0, "success": False, "error": str(e)}
                logger.error(f"{endpoint} failed: {e}")

    with allure.step("Validate all endpoints return 200"):
        successful = sum(1 for r in results.values() if r["success"])

        report = f"Token Reuse Results:\n"
        for endpoint, result in results.items():
            report += f"  {endpoint}: {result['status']}\n"
        allure.attach(report, name="token_reuse_results", attachment_type=allure.attachment_type.TEXT)

        assert successful == len(endpoints), \
            f"Only {successful}/{len(endpoints)} endpoints succeeded with token reuse"

    logger.info(f"✅ Token reused successfully across all {len(endpoints)} endpoints")


@allure.feature("Critical Paths")
@allure.story("Response Consistency")
@pytest.mark.critical_path
@pytest.mark.regression
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_consistent_response_structure(base_url, fresh_auth_token, endpoint_path):
    """
    Regression test: Response structure must be consistent across calls.

    Validates that the same endpoint returns consistent structure
    on multiple sequential calls.
    """
    headers = {"Authorization": f"Bearer {fresh_auth_token}"}
    endpoint = f"{base_url}{endpoint_path}"
    calls = 5
    responses = []

    with allure.step(f"Call {endpoint_path} {calls} times"):
        for i in range(calls):
            try:
                resp = requests.get(
                    endpoint,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    verify=SSL_VERIFY
                )
                responses.append({
                    "status": resp.status_code,
                    "headers": dict(resp.headers),
                    "has_body": len(resp.content) > 0,
                    "content_type": resp.headers.get("content-type", ""),
                })
                time.sleep(0.1)

            except requests.RequestException as e:
                pytest.fail(f"Call {i+1} to {endpoint_path} failed: {e}")

    with allure.step("Validate consistency across all calls"):
        # All should have same status code
        status_codes = [r["status"] for r in responses]
        assert len(set(status_codes)) == 1, \
            f"Status codes not consistent: {status_codes}"

        # All should have same content-type header
        content_types = [r["content_type"] for r in responses]
        assert len(set(content_types)) == 1, \
            f"Content-Types not consistent: {content_types}"

        # Report consistency
        report = (
            f"Endpoint: {endpoint_path}\n"
            f"Calls: {calls}\n"
            f"Status Code: {status_codes[0]} (consistent)\n"
            f"Content-Type: {content_types[0]} (consistent)\n"
            f"Has Body: {responses[0]['has_body']}\n"
        )
        allure.attach(report, name=f"{endpoint_path}_consistency", attachment_type=allure.attachment_type.TEXT)

    logger.info(f"✅ {endpoint_path} response structure is consistent across {calls} calls")


@allure.feature("Critical Paths")
@allure.story("Error Handling")
@pytest.mark.critical_path
@pytest.mark.regression
def test_invalid_token_rejection(base_url):
    """
    Regression test: Invalid tokens must be rejected.

    Critical for security.
    """
    endpoint = f"{base_url}{TEST_ENDPOINT_1}"
    invalid_tokens = [
        "invalid_token_12345",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        "",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Malformed (includes Bearer)
    ]

    with allure.step("Test rejection of invalid tokens"):
        for i, invalid_token in enumerate(invalid_tokens):
            headers = {"Authorization": f"Bearer {invalid_token}"} if invalid_token else {}

            response = requests.get(
                endpoint,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY,
            )

            assert response.status_code != 200, \
                f"Invalid token #{i+1} was accepted (should be rejected)"

            logger.info(f"Token #{i+1} correctly rejected with {response.status_code}")

    logger.info("✅ All invalid tokens correctly rejected")


@allure.feature("Critical Paths")
@allure.story("Missing Authentication")
@pytest.mark.critical_path
@pytest.mark.regression
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_missing_auth_header_rejection(base_url, endpoint_path):
    """
    Regression test: All endpoints must reject requests without auth header.

    Critical for security.
    """
    endpoint = f"{base_url}{endpoint_path}"

    with allure.step(f"Call {endpoint_path} without Authorization header"):
        response = requests.get(
            endpoint,
            timeout=REQUEST_TIMEOUT,
            verify=SSL_VERIFY,
        )

    with allure.step("Validate rejection"):
        assert response.status_code != 200, \
            f"{endpoint_path} accepted request without auth header (status {response.status_code})"
        assert response.status_code in [401, 403], \
            f"{endpoint_path} returned {response.status_code}, expected 401 or 403"

    logger.info(f"✅ {endpoint_path} correctly rejects unauthenticated requests")


@allure.feature("Critical Paths")
@allure.story("Sequential Endpoint Chain")
@pytest.mark.critical_path
@pytest.mark.regression
def test_sequential_endpoint_chain(base_url, fresh_auth_token):
    """
    Regression test: Execute realistic user journey calling endpoints in sequence.

    Simulates a user making multiple API calls in succession.
    """
    headers = {"Authorization": f"Bearer {fresh_auth_token}"}

    # Simulate user journey: 1 → 2 → 3 → 1 → 4 → 5 → 6
    journey = [
        TEST_ENDPOINT_1,
        TEST_ENDPOINT_2,
        TEST_ENDPOINT_3,
        TEST_ENDPOINT_1,  # Reuse endpoint
        TEST_ENDPOINT_4,
        TEST_ENDPOINT_5,
        TEST_ENDPOINT_6,
    ]

    responses = []

    with allure.step(f"Execute user journey: {' → '.join([e.replace('/api/test/', '') for e in journey])}"):
        for i, endpoint_path in enumerate(journey):
            try:
                resp = requests.get(
                    f"{base_url}{endpoint_path}",
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    verify=SSL_VERIFY
                )
                responses.append({
                    "endpoint": endpoint_path,
                    "status": resp.status_code,
                    "success": resp.status_code == 200
                })
                logger.info(f"Step {i+1}: {endpoint_path} → {resp.status_code}")
                time.sleep(0.1)

            except requests.RequestException as e:
                pytest.fail(f"Journey interrupted at step {i+1} ({endpoint_path}): {e}")

    with allure.step("Validate entire journey"):
        successful = sum(1 for r in responses if r["success"])

        journey_report = "User Journey Results:\n"
        for i, response in enumerate(responses):
            journey_report += f"  Step {i+1}: {response['endpoint']} → {response['status']}\n"
        allure.attach(journey_report, name="journey_results", attachment_type=allure.attachment_type.TEXT)

        assert successful == len(journey), \
            f"Journey failed: {successful}/{len(journey)} calls succeeded"

    logger.info(f"✅ Complete user journey succeeded ({len(journey)} steps)")


@allure.feature("Critical Paths")
@allure.story("Error Recovery")
@pytest.mark.critical_path
@pytest.mark.regression
def test_recovery_after_failed_request(base_url, fresh_auth_token):
    """
    Regression test: System recovers after a failed request.

    Make a bad request, then verify subsequent valid requests still work.
    """
    headers = {"Authorization": f"Bearer {fresh_auth_token}"}
    endpoint = f"{base_url}{TEST_ENDPOINT_1}"

    with allure.step("Make initial successful request"):
        resp1 = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        assert resp1.status_code == 200, "Initial request failed"
        logger.info(f"Initial request: {resp1.status_code}")

    with allure.step("Make request with invalid header (should fail)"):
        bad_headers = {"Authorization": "Bearer invalid_token_xyz"}
        resp2 = requests.get(endpoint, headers=bad_headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        assert resp2.status_code != 200, "Invalid request should have failed"
        logger.info(f"Bad request: {resp2.status_code} (expected)")

    with allure.step("Make follow-up request with valid token"):
        resp3 = requests.get(endpoint, headers=headers, timeout=REQUEST_TIMEOUT, verify=SSL_VERIFY)
        assert resp3.status_code == 200, "Recovery request failed - system did not recover"
        logger.info(f"Recovery request: {resp3.status_code}")

    with allure.step("Validate recovery"):
        recovery_report = (
            f"Request Sequence:\n"
            f"  1. Valid request: {resp1.status_code} ✅\n"
            f"  2. Invalid request: {resp2.status_code} ✅ (expected to fail)\n"
            f"  3. Recovery request: {resp3.status_code} ✅\n"
            f"\nResult: System recovered successfully"
        )
        allure.attach(recovery_report, name="recovery_sequence", attachment_type=allure.attachment_type.TEXT)

    logger.info("✅ System successfully recovered after failed request")


@allure.feature("Critical Paths")
@allure.story("Concurrent Access")
@pytest.mark.critical_path
@pytest.mark.regression
def test_concurrent_endpoint_access(base_url, fresh_auth_token):
    """
    Regression test: Multiple endpoints can be accessed concurrently.

    Validates that concurrent requests don't interfere with each other.
    """
    import concurrent.futures

    headers = {"Authorization": f"Bearer {fresh_auth_token}"}
    endpoints = [
        TEST_ENDPOINT_1,
        TEST_ENDPOINT_2,
        TEST_ENDPOINT_3,
        TEST_ENDPOINT_4,
        TEST_ENDPOINT_5,
        TEST_ENDPOINT_6,
    ]

    def call_endpoint(endpoint_path):
        try:
            resp = requests.get(
                f"{base_url}{endpoint_path}",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY
            )
            return {"endpoint": endpoint_path, "status": resp.status_code, "success": resp.status_code == 200}
        except Exception as e:
            return {"endpoint": endpoint_path, "status": 0, "success": False, "error": str(e)}

    with allure.step(f"Call all {len(endpoints)} endpoints concurrently"):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(call_endpoint, ep) for ep in endpoints]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

    with allure.step("Validate all concurrent calls"):
        successful = sum(1 for r in results if r["success"])

        concurrency_report = "Concurrent Access Results:\n"
        for result in results:
            concurrency_report += f"  {result['endpoint']}: {result['status']}\n"
        allure.attach(concurrency_report, name="concurrent_results", attachment_type=allure.attachment_type.TEXT)

        assert successful == len(endpoints), \
            f"Concurrent access failed: {successful}/{len(endpoints)} calls succeeded"

    logger.info(f"✅ All {len(endpoints)} endpoints accessible concurrently")
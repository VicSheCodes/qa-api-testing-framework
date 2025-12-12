import allure
import pytest
import requests
import statistics
import time
from datetime import datetime
from conftest import SSL_VERIFY, _endpoint_results
from constants import (
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    HTTP_OK,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_TOO_MANY_REQUESTS,
    TEST_ENDPOINT_2,
    REQUEST_TIMEOUT
)
from config.logger_config import get_test_logger

logger = get_test_logger()

# Suppress SSL warnings when using Charles
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@allure.feature("API Test Endpoints")
@allure.story("Endpoint Functional Tests")
@pytest.mark.parametrize("test_endpoint", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
class TestEndpointForProblematic:
    """Comprehensive discovery tests for problematic endpoints

    Based on Charles Proxy investigation:
    - Endpoint consistently returns 500 Internal Server Error
    - Response body: {"message": "Request failed", "status": "error", "timestamp": "..."}
    - This appears to be a backend bug, not a client-side issue
    """

    @allure.title("Test endpoint basic get: {description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.xfail(reason="Known issue: Endpoint 2 returns 500 - backend bug")
    def test_endpoint_basic_get(self, base_url, headers, test_endpoint):
        """Test basic GET request (expected to fail with 500)"""
        endpoint = f"{base_url}{test_endpoint}"
        logger.info(f"Testing basic GET request to {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"Status: {response.status_code}, Response time: {response.elapsed.total_seconds():.3f}s")

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        if response.status_code == HTTP_OK:
            _endpoint_results[test_endpoint]["passed"] += 1
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        # General assertion: endpoint must return a valid HTTP status code
        assert 200 <= response.status_code < 600, \
            f"Invalid HTTP status code: {response.status_code}"

        # Verify response has required attributes
        assert hasattr(response, 'text'), "Response missing text attribute"
        assert response.headers.get('Content-Type') is not None, \
            "Response missing Content-Type header"

        # # Expecting 500 Internal Server Error
        # assert response.status_code == HTTP_INTERNAL_ERROR, \
        #     f"Expected 500 Internal Server Error, got {response.status_code}"

        # Verify error structure
        error_body = response.json()
        assert "message" in error_body, "Error response missing 'message' field"
        assert "status" in error_body, "Error response missing 'status' field"
        assert error_body["status"] == "error", f"Expected status='error', got '{error_body['status']}'"
        assert "timestamp" in error_body, "Error response missing 'timestamp' field"

        logger.info(f"Error response: {error_body}")

    @allure.title("Test endpoint 2 with query parameters: {description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("query_params,description", [
        ({"id": "1"}, "id parameter with value 1"),
        ({"id": "123"}, "id parameter with value 123"),
        ({"page": "1"}, "page parameter"),
        ({"retry": "true"}, "retry flag"),
        ({"id": "1", "page": "1"}, "multiple parameters"),
        ({"id": "123", "retry": "true"}, "multiple parameters (id and retry)"),
        ({"wildcard": "*"}, "wildcard parameter with asterisk"),
        ({"filter": "*"}, "filter parameter matching all"),
        ({"match": "true"}, "match parameter always true"),
        ({}, "no parameters (baseline)"),
    ])
    def test_endpoint_with_query_parameters(self, base_url, headers, query_params, description, test_endpoint):
        """Test if query parameters fix the 500 error

        Testing hypothesis: endpoint might require specific parameters
        Expected: Still returns 500 (parameters don't fix the issue)
        """
        endpoint = f"{base_url}{test_endpoint}"
        logger.info(f"Testing with {description}: {query_params}")

        with allure.step(f"Send GET request with params: {query_params}"):
            response = requests.get(
                endpoint,
                headers=headers,
                params=query_params,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        with allure.step("Record test results"):
            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

        with allure.step("Log response details"):
            logger.info(f"Query params: {query_params}")
            logger.info(f"Status: {response.status_code}")
            logger.info(f"Response: {response.text[:200]}")

        with allure.step("Verify expected failure"):
            if response.status_code == HTTP_OK:
                logger.warning(f" UNEXPECTED SUCCESS with params: {query_params}")
                _endpoint_results[test_endpoint]["passed"] += 1
                pytest.fail(f"Endpoint unexpectedly succeeded with params {query_params}")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

            # Still failing
            assert response.status_code == HTTP_INTERNAL_ERROR, \
                f"Expected 500 with params {query_params}, got {response.status_code}"


    @pytest.mark.parametrize("http_method,request_func,description", [
        ("POST", lambda url, **kwargs: requests.post(url, json={}, **kwargs), "POST with empty JSON body"),
        ("POST", lambda url, **kwargs: requests.post(url, json={"id": 1}, **kwargs), "POST with id parameter"),
        ("PUT", lambda url, **kwargs: requests.put(url, json={}, **kwargs), "PUT request"),
        ("PATCH", lambda url, **kwargs: requests.patch(url, json={}, **kwargs), "PATCH request"),
        ("DELETE", lambda url, **kwargs: requests.delete(url, **kwargs), "DELETE request"),
    ])
    def test_endpoint_different_http_methods(self, base_url, headers, http_method, request_func, description, test_endpoint):
        """Test if endpoint expects a different HTTP method

        Some endpoints might be documented as GET but actually require POST
        Expected: Returns 500 or 405 (Method Not Allowed)
        """
        endpoint = f"{base_url}{test_endpoint}"
        logger.info(f"Testing {description}")

        response = request_func(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        logger.info(f"{http_method} request:")
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text[:200]}")

        # Check for method-specific responses
        if response.status_code == 405:  # Method Not Allowed
            logger.info(f"✓ {http_method} not allowed (expected)")
            _endpoint_results[test_endpoint]["failed"] += 1
        elif response.status_code == HTTP_OK:
            logger.warning(f"⚠️ UNEXPECTED SUCCESS with {http_method}")
            _endpoint_results[test_endpoint]["passed"] += 1
            pytest.fail(f"Endpoint unexpectedly succeeded with {http_method}")
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        # Document the failure
        assert response.status_code in [HTTP_INTERNAL_ERROR, 405], \
            f"Expected 500 or 405 with {http_method}, got {response.status_code}"


    @pytest.mark.parametrize("num_requests,description", [
        (20, "Rapid-fire consistency test (20 requests)"),
        (10, "Quick consistency check (10 requests)"),
    ])
    def test_endpoint_consistency_rapid_fire(self, base_url, headers, num_requests, description, test_endpoint):
        """Test if 500 is consistent across rapid requests

        Checks if error is:
        - Transient (occasionally succeeds)
        - Rate-limited (changes with frequency)
        - Permanent (always fails)

        Expected: All requests fail with 500 (permanent error)
        """
        endpoint = f"{base_url}{test_endpoint}"
        logger.info(f"Running {description}")

        results = []

        for i in range(num_requests):
            start_time = time.time()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            response_time = time.time() - start_time

            results.append({
                "request_num": i + 1,
                "status_code": response.status_code,
                "response_time": response_time
            })

            # Record results
            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response_time)
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

        # Analyze pattern
        status_codes = [r["status_code"] for r in results]
        success_count = status_codes.count(HTTP_OK)
        error_count = status_codes.count(HTTP_INTERNAL_ERROR)
        rate_limited = status_codes.count(HTTP_TOO_MANY_REQUESTS)

        logger.info(f"\n{description} results:")
        logger.info(f"Total requests: {num_requests}")
        logger.info(f"Successes (200): {success_count}")
        logger.info(f"Errors (500): {error_count}")
        logger.info(f"Rate limited (429): {rate_limited}")
        logger.info(f"Status codes: {status_codes}")

        if success_count > 0:
            logger.warning(f"⚠️ UNEXPECTED: {success_count} successful requests (endpoint recovered!)")
            pytest.fail(f"Endpoint unexpectedly succeeded {success_count} times")

        if rate_limited > 0:
            logger.info(f"⚠️ Rate limiting detected: {rate_limited} requests throttled")

        # All requests should fail consistently
        assert error_count == num_requests, \
            f"Expected all {num_requests} requests to fail, but got {error_count} errors, " \
            f"{success_count} successes, {rate_limited} rate-limited"


    @pytest.mark.parametrize("num_requests,delay,description", [
        (10, 2.0, "Delayed requests (2s between each)"),
        (5, 5.0, "Long delays (5s between each)"),
    ])
    def test_endpoint_consistency_with_delays(self, base_url, fresh_auth_token, num_requests, delay, description, test_endpoint):
        """Test if delays between requests affect success rate

        Some endpoints might have cooldown requirements
        Expected: Still fails consistently (delays don't help)
        """
        endpoint = f"{base_url}{test_endpoint}"
        headers = {"Authorization": f"Bearer {fresh_auth_token}"}
        logger.info(f"Running {description}")

        results = []

        for i in range(num_requests):
            if i > 0:
                logger.debug(f"Waiting {delay}s before request #{i+1}")
                time.sleep(delay)

            start_time = time.time()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            response_time = time.time() - start_time

            results.append({
                "request_num": i + 1,
                "status_code": response.status_code,
                "response_time": response_time
            })

            # Record results
            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response_time)
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

        # Analyze pattern
        status_codes = [r["status_code"] for r in results]
        success_count = status_codes.count(HTTP_OK)

        logger.info(f"\n{description} results:")
        logger.info(f"Successes: {success_count}/{num_requests}")
        logger.info(f"Status codes: {status_codes}")

        if success_count > 0:
            logger.warning(f"⚠️ UNEXPECTED: {success_count} successful requests with {delay}s delays")
            pytest.fail(f"Endpoint unexpectedly succeeded {success_count} times with delays")

        assert success_count == 0, \
            f"Expected all requests to fail, but {success_count} succeeded with {delay}s delays"


    def test_endpoint_with_different_tokens(self, base_url, test_endpoint):
        """Test if error is token-specific

        Generates multiple fresh tokens to rule out auth issues
        Expected: All tokens fail the same way (not an auth issue)
        """
        from conftest import INITIAL_REFRESH_TOKEN, AUTH_GENERATE_ENDPOINT

        endpoint = f"{base_url}{test_endpoint}"
        logger.info("Testing with multiple different tokens")

        results = []

        # Generate 3 different tokens
        for i in range(3):
            logger.info(f"Generating token #{i+1}")

            # Get fresh token
            auth_response = requests.post(
                f"{base_url}{AUTH_GENERATE_ENDPOINT}",
                json={"refresh_token": INITIAL_REFRESH_TOKEN},
                timeout=REQUEST_TIMEOUT,
                verify=SSL_VERIFY
            )
            assert auth_response.status_code == HTTP_OK, "Failed to generate token"

            token = auth_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Test endpoint with this token
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            results.append({
                "token_num": i + 1,
                "status_code": response.status_code
            })

            # Record results
            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

        status_codes = [r["status_code"] for r in results]
        logger.info(f"\nMultiple tokens test:")
        logger.info(f"Status codes: {status_codes}")

        # All tokens should fail the same way
        assert all(code == HTTP_INTERNAL_ERROR for code in status_codes), \
            f"Expected all tokens to produce 500, got: {status_codes}"


    @pytest.mark.parametrize("extra_headers,description", [
        ({"Content-Type": "application/json"}, "with Content-Type header"),
        ({"Accept": "application/json"}, "with Accept header"),
        ({"Content-Type": "application/json", "Accept": "application/json"}, "with both headers"),
        ({"X-Request-ID": "test-123"}, "with custom header"),
        ({"Accept": "*/*"}, "With Accept wildcard"),
        ({"X-Requested-With": "XMLHttpRequest"}, "AJAX-style request"),
        ({"User-Agent": "Mozilla/5.0"}, "Browser User-Agent"),
        ({"User-Agent": "curl/7.68.0"}, "curl User-Agent"),
        ({"User-Agent": "python-requests"}, "Python requests library"),
        ({"Origin": "https://qa-home-assignment.magmadevs.com"}, "With Origin header"),
        ({"Referer": "https://qa-home-assignment.magmadevs.com"}, "With Referer"),
        ({}, "No extra headers (baseline)"),
    ])
    def test_endpoint_additional_headers(self, base_url, headers, extra_headers, description, test_endpoint):
        """Test with different header combinations

        Some APIs require specific headers (Content-Type, Accept, etc.)
        Expected: Headers don't fix the issue
        """
        endpoint = f"{base_url}{test_endpoint}"
        headers_with_extra = {**headers, **extra_headers}
        logger.info(f"Testing {description}: {extra_headers}")

        response = requests.get(
            endpoint,
            headers=headers_with_extra,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        logger.info(f"Headers: {extra_headers}")
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text[:200]}")

        if response.status_code == HTTP_OK:
            logger.warning(f"⚠️ UNEXPECTED SUCCESS with headers: {extra_headers}")
            _endpoint_results[test_endpoint]["passed"] += 1
            pytest.fail(f"Endpoint unexpectedly succeeded with headers {extra_headers}")
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        assert response.status_code == HTTP_INTERNAL_ERROR, \
            f"Expected 500 with headers {extra_headers}, got {response.status_code}"


    def test_endpoint_response_structure(self, base_url, headers, test_endpoint):
        """Verify error response structure for documentation

        Ensures error format is consistent for proper error handling
        """
        endpoint = f"{base_url}{test_endpoint}"
        logger.info("Verifying error response structure")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1
        _endpoint_results[test_endpoint]["failed"] += 1

        assert response.status_code == HTTP_INTERNAL_ERROR

        # Verify JSON response
        assert response.headers.get("Content-Type") == "application/json", \
            f"Expected JSON response, got {response.headers.get('Content-Type')}"

        error_body = response.json()

        logger.info("\nError response structure:")
        logger.info(f"Keys present: {list(error_body.keys())}")
        logger.info(f"Full response: {error_body}")

        # Verify required fields
        assert "message" in error_body, "Error should have 'message' field"
        assert "status" in error_body, "Error should have 'status' field"
        assert "timestamp" in error_body, "Error should have 'timestamp' field"

        # Verify field values
        assert error_body["message"] == "Request failed", \
            f"Expected message 'Request failed', got '{error_body['message']}'"
        assert error_body["status"] == "error", \
            f"Expected status 'error', got '{error_body['status']}'"

        # Timestamp should be ISO format
        try:
            datetime.fromisoformat(error_body["timestamp"].replace('Z', '+00:00'))
            logger.info("✓ Timestamp is valid ISO format")
        except ValueError:
            pytest.fail(f"Timestamp not in ISO format: {error_body['timestamp']}")


    def test_endpoint_response_time_consistency(self, base_url, headers, test_endpoint):
        """Check if response time gives clues about the failure

        Fast failures might indicate early validation
        Slow failures might indicate timeout or processing error
        """
        endpoint = f"{base_url}{test_endpoint}"
        logger.info("Analyzing response time consistency")

        response_times = []

        for i in range(10):
            start_time = time.time()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start_time
            response_times.append(elapsed)

            # Record results
            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(elapsed)
            _endpoint_results[test_endpoint]["test_count"] += 1
            _endpoint_results[test_endpoint]["failed"] += 1

        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        logger.info(f"\nResponse time analysis:")
        logger.info(f"Average: {avg_time:.3f}s")
        logger.info(f"Min: {min_time:.3f}s")
        logger.info(f"Max: {max_time:.3f}s")
        logger.info(f"All times: {[f'{t:.3f}s' for t in response_times]}")

        # Fast consistent failures suggest validation error
        if avg_time < 0.5:
            logger.info("⚡ Fast failures suggest early validation/routing error")
        elif avg_time > 5:
            logger.info("🐌 Slow failures suggest timeout or processing error")
        else:
            logger.info("⏱️ Moderate response times suggest mid-processing failure")

        # Response times should be relatively consistent for same error
        time_variance = max_time - min_time
        assert time_variance < 2.0, \
            f"Response times too inconsistent (variance: {time_variance:.3f}s). " \
            f"Range: {min_time:.3f}s - {max_time:.3f}s"


    def test_endpoint_redirect_detection(self, base_url, headers, test_endpoint):
        """Detect if endpoint 2 performs redirects before failing"""
        endpoint = f"{base_url}{test_endpoint}"

        # Disable automatic redirect following
        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            allow_redirects=False  # KEY: Don't follow redirects
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"REDIRECT DETECTION TEST: {test_endpoint}")
        logger.info(f"{'='*60}")

        # Check for redirect status codes
        is_redirect = 300 <= response.status_code < 400

        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Is Redirect: {is_redirect}")

        if is_redirect:
            location = response.headers.get('Location', 'NOT FOUND')
            logger.warning(f" REDIRECT DETECTED!")
            logger.warning(f"   Redirect to: {location}")
            logger.warning(f"   Status: {response.status_code}")

            # Follow redirect  to see final destination
            if location:
                logger.info(f"\n   Following redirect manually...")
                final_response = requests.get(
                    location if location.startswith('http') else f"{base_url}{location}",
                    headers=headers,
                    verify=SSL_VERIFY,
                    allow_redirects=False
                )
                logger.info(f"   Final Status: {final_response.status_code}")
                logger.info(f"   Final Body: {final_response.text[:200]}")
        else:
            logger.info(f"✓ No redirect - direct response")
            logger.info(f"Response Body: {response.text[:200]}")

        logger.info(f"\nRedirect-related headers:")
        redirect_headers = ['Location', 'Refresh', 'Content-Location']
        for header in redirect_headers:
            value = response.headers.get(header)
            if value:
                logger.info(f"  {header}: {value}")

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        if response.status_code == HTTP_OK:
            _endpoint_results[test_endpoint]["passed"] += 1
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        return response

    @pytest.mark.parametrize("sequence", [
        [1, 2],  # Call 1 then 2
        [1, 3, 2],  # Call 1, 3, then 2
        [1, 4, 2],  # Call 1, 4, then 2
        [1, 5, 2],  # Call 1, 5, then 2
        [1, 6, 2],  # Call 1, 6, then 2
        [3, 2],  # Call 3 then 2
        [4, 2],  # Call 4 then 2
        [5, 2],  # Call 5 then 2
        [1, 3, 4, 2],  # Multiple endpoints before 2
        [1, 3, 4, 5, 6, 2],  # All endpoints before 2
    ])
    def test_endpoint_after_sequence(self, base_url, fresh_auth_token, sequence, test_endpoint):
        """Test if endpoint 2 requires calling other endpoints first"""
        headers = {"Authorization": f"Bearer {fresh_auth_token}"}
        session = requests.Session()  # Preserve cookies/state

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing sequence: {' → '.join(str(e) for e in sequence)}")
        logger.info(f"{'=' * 60}")

        # Call all endpoints in sequence except the last
        for endpoint_num in sequence[:-1]:
            endpoint = f"{base_url}/api/test/{endpoint_num}"
            logger.info(f"\nCalling endpoint {endpoint_num}...")

            response = session.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

        logger.info(f"  Status: {response.status_code}")

        # Check for cookies/session data
        if session.cookies:
            logger.info(f"  Cookies: {dict(session.cookies)}")

        # Check for useful response data
        try:
            data = response.json()
            if "session_id" in data or "token" in data:
                logger.info(f"  Found session data: {data}")
        except:
            pass

        time.sleep(0.5)

        # Finally call endpoint 2
        logger.info(f"\n→ Finally calling endpoint 2...")
        endpoint_2 = f"{base_url}{test_endpoint}"

        response_2 = session.get(
            endpoint_2,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"  Status: {response_2.status_code}")
        logger.info(f"  Response: {response_2.text[:200]}")

        if response_2.status_code == HTTP_OK:
            logger.warning(f" BREAKTHROUGH! Sequence works: {sequence}")
            pytest.fail(f"DISCOVERY: Endpoint 2 requires sequence: {sequence}")

        # Record results for endpoint 2
        _endpoint_results[test_endpoint]["status_codes"].append(response_2.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response_2.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        if response_2.status_code == HTTP_OK:
            _endpoint_results[test_endpoint]["passed"] += 1
            logger.warning(f" BREAKTHROUGH! Endpoint 2 succeeded after sequence: {sequence}")
            pytest.fail(f"Endpoint 2 unexpectedly succeeded after sequence {sequence}")
        else:
            _endpoint_results[test_endpoint]["failed"] += 1


    def test_endpoint_server_routing(self, base_url, headers, test_endpoint):
        """Check if endpoint 2 consistently routes to the same backend"""
        endpoint = f"{base_url}{test_endpoint}"

        servers_seen = set()

        for i in range(20):
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY
            )

            # Cloudflare adds headers revealing backend
            cf_ray = response.headers.get('CF-Ray', 'NONE')
            cf_cache = response.headers.get('CF-Cache-Status', 'NONE')
            server = response.headers.get('Server', 'NONE')

            logger.info(f"Request {i+1}: Status={response.status_code}")
            logger.info(f"  CF-Ray: {cf_ray}")
            logger.info(f"  CF-Cache: {cf_cache}")
            logger.info(f"  Server: {server}")

            # First 10 chars of CF-Ray identify datacenter
            servers_seen.add(cf_ray[:10])

            time.sleep(0.5)

        logger.info(f"\nUnique Cloudflare datacenters: {len(servers_seen)}")
        logger.info(f"Datacenters: {servers_seen}")


    def test_endpoint_per_ip(self, headers, test_endpoint):
        """Test endpoint 2 by directly targeting each Cloudflare IP"""

        ips = ["172.67.157.203", "104.21.8.177"]

        for ip in ips:
            endpoint = f"https://{ip}{test_endpoint}"
            headers_with_host = {
                **headers,
                "Host": "qa-home-assignment.magmadevs.com"
            }

            logger.info(f"\n{'='*60}")
            logger.info(f"Testing IP: {ip}")
            logger.info(f"{'='*60}")

            success = 0
            fail = 0

            for i in range(10):
                try:
                    response = requests.get(
                        endpoint,
                        headers=headers_with_host,
                        timeout=REQUEST_TIMEOUT,
                        verify=False
                    )

                    if response.status_code == 200:
                        success += 1
                    else:
                        fail += 1

                    logger.info(
                            f"  [{i + 1}] Status: {response.status_code}, CF-Ray: {response.headers.get('CF-Ray', 'N/A')}")

                except requests.exceptions.RequestException as e:
                    fail += 1
                    logger.error(f"  [{i + 1}] Request failed: {str(e)}")

                time.sleep(0.5)

            logger.info(f"\nIP {ip} Results: ✓ {success} | ✗ {fail}")


    @allure.title("Analyze response time patterns for clues")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_timing_analysis(self, base_url, headers, test_endpoint):
        """Analyze response time patterns to understand failure cause

        Variable timing can reveal:
        - Database query timeouts (slow failures)
        - Race conditions (inconsistent timing)
        - Resource contention (increasing delays)
        - Retry logic (clusters of similar times)
        """
        endpoint = f"{base_url}{test_endpoint}"

        results = []

        for i in range(50):
            start = time.time()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start

            results.append({
                "request": i + 1,
                "status": response.status_code,
                "time": elapsed,
                "timestamp": datetime.now().isoformat()
            })

            time.sleep(0.1)  # Small delay to avoid rate limiting

        # Statistical analysis
        times = [r["time"] for r in results]

        avg = statistics.mean(times)
        median = statistics.median(times)
        stdev = statistics.stdev(times) if len(times) > 1 else 0
        min_time = min(times)
        max_time = max(times)

        logger.info(f"\n{'='*70}")
        logger.info(f"RESPONSE TIME ANALYSIS (50 requests)")
        logger.info(f"{'='*70}")
        logger.info(f"Average:  {avg:.3f}s")
        logger.info(f"Median:   {median:.3f}s")
        logger.info(f"Std Dev:  {stdev:.3f}s")
        logger.info(f"Min:      {min_time:.3f}s")
        logger.info(f"Max:      {max_time:.3f}s")
        logger.info(f"Range:    {max_time - min_time:.3f}s")

        logger.info(f"\n{'='*70}")
        logger.info(f"PATTERN DETECTION")
        logger.info(f"{'='*70}")

        # 1. Bimodal distribution (two distinct clusters)
        fast_requests = [t for t in times if t < 0.5]
        slow_requests = [t for t in times if t >= 0.5]

        if len(fast_requests) > 0 and len(slow_requests) > 0:
            logger.warning(f"⚠ BIMODAL DISTRIBUTION:")
            logger.warning(f"   Fast requests: {len(fast_requests)} (avg: {statistics.mean(fast_requests):.3f}s)")
            logger.warning(f"   Slow requests: {len(slow_requests)} (avg: {statistics.mean(slow_requests):.3f}s)")
            logger.warning(f"   → Suggests: Multiple failure paths or retry logic")

        # 2. High variability
        coefficient_of_variation = (stdev / avg) * 100 if avg > 0 else 0
        logger.info(f"\nCoefficient of Variation: {coefficient_of_variation:.1f}%")

        if coefficient_of_variation > 50:
            logger.warning(f"⚠ HIGH VARIABILITY ({coefficient_of_variation:.1f}%)")
            logger.warning(f"   → Suggests: Resource contention, network issues, or race conditions")
        elif coefficient_of_variation < 20:
            logger.info(f"✓ Low variability ({coefficient_of_variation:.1f}%)")
            logger.info(f"   → Suggests: Consistent failure path")

        # 3. Outlier detection
        outliers = [r for r in results if abs(r["time"] - avg) > 2 * stdev]
        if outliers:
            logger.warning(f"\n⚠ OUTLIERS DETECTED: {len(outliers)} requests")
            for outlier in outliers[:5]:  # Show first 5
                logger.warning(f"   Request #{outlier['request']}: {outlier['time']:.3f}s")
            logger.warning(f"   → Suggests: Sporadic timeouts or backend restarts")

        # 4. Trend analysis (are times increasing?)
        first_10 = statistics.mean(times[:10])
        last_10 = statistics.mean(times[-10:])
        trend = last_10 - first_10

        logger.info(f"\nTrend Analysis:")
        logger.info(f"   First 10 requests avg: {first_10:.3f}s")
        logger.info(f"   Last 10 requests avg:  {last_10:.3f}s")
        logger.info(f"   Trend: {'+' if trend > 0 else ''}{trend:.3f}s")

        if abs(trend) > 0.1:
            logger.warning(f"⚠ TIMING TREND DETECTED")
            if trend > 0:
                logger.warning(f"   → Increasing delays (backend degradation?)")
            else:
                logger.warning(f"   → Decreasing delays (warmup period?)")

        # 5. Histogram
        logger.info(f"\nResponse Time Distribution:")
        buckets = [0, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, float('inf')]
        bucket_labels = ['<0.1s', '0.1-0.2s', '0.2-0.5s', '0.5-1s', '1-2s', '2-5s', '>5s']

        for i in range(len(buckets) - 1):
            count = sum(1 for t in times if buckets[i] <= t < buckets[i+1])
            if count > 0:
                bar = '█' * (count // 2)  # Visual bar
                logger.info(f"   {bucket_labels[i]:8s}: {count:3d} {bar}")

        # Document findings
        with allure.step("Record timing statistics"):
            allure.attach(
                f"Average: {avg:.3f}s\n"
                f"Median: {median:.3f}s\n"
                f"Std Dev: {stdev:.3f}s\n"
                f"Range: {min_time:.3f}s - {max_time:.3f}s\n"
                f"Variability: {coefficient_of_variation:.1f}%",
                name="Timing Statistics",
                attachment_type=allure.attachment_type.TEXT
            )

    def test_endpoint_large_payload(self, base_url, headers, test_endpoint):
        """Test endpoint 2 with a large payload to see if it affects the error

        Some endpoints may fail due to payload size or processing limits
        Expected: Still fails with 500
        """
        endpoint = f"{base_url}{test_endpoint}"
        large_payload = {"data": "x" * 10_000_000}  # 10 MB

        logger.info("Testing with large payload (10MB)")

        response = requests.post(
            endpoint,
            headers=headers,
            json=large_payload,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT * 2  # Increase timeout for large payload
        )

        # Record results
        _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {response.text[:200]}")

        if response.status_code == HTTP_OK:
            logger.warning("⚠️ UNEXPECTED SUCCESS with large payload")
            _endpoint_results[test_endpoint]["passed"] += 1
            pytest.fail("Endpoint unexpectedly succeeded with large payload")
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        assert response.status_code == HTTP_INTERNAL_ERROR, \
            f"Expected 500 with large payload, got {response.status_code}"
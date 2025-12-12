# Functional tests for /api/test/1
import pytest
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.logger_config import get_test_logger
from constants import (
    TEST_ENDPOINT_1,
    HTTP_OK,
    REQUEST_TIMEOUT
)
from conftest import _endpoint_results, SSL_VERIFY

logger = get_test_logger()


@pytest.mark.parametrize("test_endpoint", [TEST_ENDPOINT_1])
class TestEndpoint1AdvancedDiscovery:
    """Advanced discovery tests to find failure scenarios for endpoint 1"""

    # def test_stress_rapid_fire(self, base_url, headers, test_endpoint):
    #     """High volume rapid-fire requests to find breaking point"""
    #     endpoint = f"{base_url}{test_endpoint}"
    #     results = []
    #
    #     for i in range(100):  # 100 rapid requests
    #         try:
    #             response = requests.get(
    #                 endpoint,
    #                 headers=headers,
    #                 verify=SSL_VERIFY,
    #                 timeout=REQUEST_TIMEOUT
    #             )
    #             results.append({
    #                 "request": i + 1,
    #                 "status": response.status_code,
    #                 "time": response.elapsed.total_seconds()
    #             })
    #         except Exception as e:
    #             results.append({
    #                 "request": i + 1,
    #                 "status": "ERROR",
    #                 "error": str(e)
    #             })
    #
    #     # Analyze for failures
    #     failures = [r for r in results if r.get("status") != HTTP_OK]
    #     logger.info(f"Completed 100 rapid requests - Failures: {len(failures)}")
    #
    #     if failures:
    #         logger.warning(f" Found failures: {failures[:5]}")

    def test_stress_rapid_fire(self, base_url, headers, test_endpoint):
        """High volume rapid-fire requests to find breaking point"""
        endpoint = f"{base_url}{test_endpoint}"
        results = []

        for i in range(100):  # 100 rapid requests
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == HTTP_OK:
                    _endpoint_results[test_endpoint]["passed"] += 1
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1
                    logger.warning(f"⚠️ Rapid-fire failure at request #{i + 1}: {response.status_code}")

                results.append({
                    "request": i + 1,
                    "status": response.status_code,
                    "time": response.elapsed.total_seconds()
                })

                if response.status_code == 429:
                    logger.info(f"✓ Rate limit detected at request #{i + 1}")
                    break

            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                results.append({
                    "request": i + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
                logger.error(f"Error at request #{i + 1}: {e}")

        # Analyze for failures
        failures = [r for r in results if r.get("status") != HTTP_OK]
        logger.info(f"Completed {len(results)} rapid requests - Failures: {len(failures)}")

        if 429 not in [r.get("status") for r in results]:
            logger.info("✓ No rate limiting detected in rapid-fire test")

    def test_concurrent_requests(self, base_url, headers, test_endpoint):
        """Concurrent requests to test thread safety"""
        endpoint = f"{base_url}{test_endpoint}"
        results = []

        def make_request(request_id):
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )
                return {
                    "id": request_id,
                    "status": response.status_code,
                    "time": response.elapsed.total_seconds()
                }
            except Exception as e:
                return {"id": request_id, "status": "ERROR", "error": str(e)}

        # 20 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)

                # Record results
                _endpoint_results[test_endpoint]["test_count"] += 1
                if result.get("status") == HTTP_OK:
                    _endpoint_results[test_endpoint]["status_codes"].append(result["status"])
                    _endpoint_results[test_endpoint]["response_times"].append(result["time"])
                    _endpoint_results[test_endpoint]["passed"] += 1
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1
                    if result.get("status") != "ERROR":
                        _endpoint_results[test_endpoint]["status_codes"].append(result["status"])

        failures = [r for r in results if r.get("status") != HTTP_OK]
        logger.info(f"Concurrent test - Failures: {len(failures)}/20")

        if failures:
            logger.warning(f"⚠️ Concurrent failures: {failures}")
        else:
            logger.info("✓ All concurrent requests successful")

    def test_long_running_session(self, base_url, fresh_auth_token, test_endpoint):
        """Long-running test to detect degradation over time"""
        endpoint = f"{base_url}{test_endpoint}"
        headers = {"Authorization": f"Bearer {fresh_auth_token}"}
        results = []

        # Run for 5 minutes with 5-second intervals
        for i in range(60):
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Failure at minute {i + 1}: {response.status_code}")

            results.append({
                "minute": i + 1,
                "status": response.status_code,
                "time": response.elapsed.total_seconds()
            })

            time.sleep(5)

        failures = [r for r in results if r["status"] != HTTP_OK]
        logger.info(f"5-minute test - Failures: {len(failures)}/60")

        if failures:
            logger.warning(f"⚠️ Performance degradation detected")
        else:
            logger.info("✓ Stable performance over 5 minutes")

    def test_invalid_payloads(self, base_url, headers, test_endpoint):
        """Test with various invalid payloads"""
        endpoint = f"{base_url}{test_endpoint}"

        payloads = [
            {"data": "invalid"},
            {"id": -1},
            {"test": "x" * 10000},  # Large payload
            None,
        ]

        for i, payload in enumerate(payloads):
            response = requests.get(
                endpoint,
                headers=headers,
                json=payload,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK or response.status_code == 400:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info(f"✓ Payload #{i + 1}: Status {response.status_code}")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Payload #{i + 1} caused unexpected failure: {payload}")

    def test_expired_token(self, base_url, test_endpoint):
        """Test with expired/invalid token"""
        endpoint = f"{base_url}{test_endpoint}"

        invalid_tokens = [
            "expired_token_12345",
            "",
            "Bearer invalid",
            "invalid_format"
        ]

        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == 401:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info("✓ Properly handles invalid tokens")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Invalid token not rejected: {response.status_code}")

    def test_missing_headers(self, base_url, headers, test_endpoint):
        """Test with missing or malformed headers"""
        endpoint = f"{base_url}{test_endpoint}"

        header_combinations = [
            {},  # No headers
            {"Authorization": ""},  # Empty auth
            {"Content-Type": "application/json"},  # Missing auth
        ]

        for i, test_headers in enumerate(header_combinations):
            response = requests.get(
                endpoint,
                headers=test_headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == 401:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info(f"✓ Headers #{i + 1}: Properly rejected {response.status_code}")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Headers #{i + 1}: Unexpected status {response.status_code}")

    def test_timeout_scenarios(self, base_url, headers, test_endpoint):
        """Test with various timeout settings"""
        endpoint = f"{base_url}{test_endpoint}"

        timeouts = [0.001, 0.01, 0.1, 1.0]  # Very short timeouts

        for timeout in timeouts:
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=timeout
                )

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == HTTP_OK:
                    _endpoint_results[test_endpoint]["passed"] += 1
                    logger.info(f"✓ Timeout {timeout}s: {response.status_code}")
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1

            except requests.exceptions.Timeout:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Timeout occurred at {timeout}s")
            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.error(f"Error with timeout {timeout}s: {e}")

    def test_network_interruption_simulation(self, base_url, headers, test_endpoint):
        """Simulate network interruptions"""
        endpoint = f"{base_url}{test_endpoint}"

        # Test connection pooling behavior
        session = requests.Session()

        for i in range(10):
            try:
                response = session.get(
                    endpoint,
                    headers=headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == HTTP_OK:
                    _endpoint_results[test_endpoint]["passed"] += 1
                    logger.info(f"✓ Request #{i + 1}: {response.status_code}")
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1

                # Simulate connection drop every 3 requests
                if (i + 1) % 3 == 0:
                    session.close()
                    session = requests.Session()
                    logger.info("⚠️ Simulated connection drop")

            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.error(f"Error during interruption test: {e}")

    def test_response_size_patterns(self, base_url, headers, test_endpoint):
        """Monitor response size for anomalies"""
        endpoint = f"{base_url}{test_endpoint}"
        sizes = []

        for _ in range(20):
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
                size = len(response.content)
                sizes.append(size)
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

            time.sleep(0.5)

        if len(set(sizes)) > 1:
            logger.warning(f"⚠️ Inconsistent response sizes: {set(sizes)}")
        else:
            logger.info(f"✓ Consistent response size: {sizes[0]} bytes")

    def test_statistical_outlier_detection(self, base_url, headers, test_endpoint):
        """Statistical analysis to detect outliers"""
        endpoint = f"{base_url}{test_endpoint}"
        times = []
        statuses = []

        for _ in range(50):
            start = time.time()
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            elapsed = time.time() - start

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(elapsed)
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

            times.append(elapsed)
            statuses.append(response.status_code)
            time.sleep(0.2)

        # Statistical analysis
        mean_time = statistics.mean(times)
        stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        median_time = statistics.median(times)

        # Detect outliers (> 3 standard deviations)
        outliers = [t for t in times if abs(t - mean_time) > 3 * stdev_time]

        logger.info(f"Response time analysis (50 samples):")
        logger.info(f"  Mean: {mean_time:.3f}s, Median: {median_time:.3f}s, StdDev: {stdev_time:.3f}s")
        logger.info(f"  Outliers: {len(outliers)}")

        if outliers:
            logger.warning(f"⚠️ Detected timing outliers: {[f'{t:.3f}s' for t in outliers]}")

        # Check for status code anomalies
        if len(set(statuses)) > 1:
            logger.warning(f"⚠️ Mixed status codes: {set(statuses)}")




    def test_rate_limiting_detection(self, base_url, headers, test_endpoint):
        """Detect rate limiting thresholds"""
        endpoint = f"{base_url}{test_endpoint}"
        results = []

        for i in range(200):  # 200 requests to trigger potential rate limit
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"️ Rate limit hit at request #{i + 1}: {response.status_code}")

            results.append(response.status_code)

            if response.status_code == 429:
                logger.info(f"✓ Rate limit detected at request #{i + 1}")
                break

        if 429 not in results:
            logger.info("✓ No rate limiting detected in 200 requests")

    def test_payload_size_boundaries(self, base_url, headers, test_endpoint):
        """Test various payload sizes to find limits"""
        endpoint = f"{base_url}{test_endpoint}"

        payload_sizes = [0, 10, 100, 1000, 10000, 100000, 1000000]  # bytes

        for size in payload_sizes:
            payload = {"data": "x" * size}

            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    json=payload,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == HTTP_OK:
                    _endpoint_results[test_endpoint]["passed"] += 1
                    logger.info(f"✓ Payload size {size} bytes: {response.status_code}")
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1
                    logger.warning(f"⚠️ Payload size {size} bytes caused failure: {response.status_code}")

            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.error(f"Error with payload size {size} bytes: {e}")

    def test_response_content_consistency(self, base_url, headers, test_endpoint):
        """Check if response content is identical across requests"""
        endpoint = f"{base_url}{test_endpoint}"
        responses = []

        for i in range(30):
            response = requests.get(
                endpoint,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
                responses.append(response.text)
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

            time.sleep(0.3)

        unique_responses = set(responses)

        if len(unique_responses) == 1:
            logger.info(f"✓ All responses identical ({len(responses)} samples)")
        else:
            logger.warning(f"⚠️ Response content varies: {len(unique_responses)} unique responses")
            for i, resp in enumerate(list(unique_responses)[:3]):
                logger.info(f"  Variant #{i+1}: {resp[:100]}")

    def test_http_method_variations(self, base_url, headers, test_endpoint):
        """Test different HTTP methods"""
        endpoint = f"{base_url}{test_endpoint}"

        methods = {
            "POST": lambda: requests.post(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
            "PUT": lambda: requests.put(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
            "DELETE": lambda: requests.delete(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
            "PATCH": lambda: requests.patch(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
            "HEAD": lambda: requests.head(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
            "OPTIONS": lambda: requests.options(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT),
        }

        for method_name, method_func in methods.items():
            try:
                response = method_func()

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == 405:
                    _endpoint_results[test_endpoint]["passed"] += 1
                    logger.info(f"✓ {method_name} correctly rejected: {response.status_code}")
                elif response.status_code == HTTP_OK:
                    _endpoint_results[test_endpoint]["passed"] += 1
                    logger.warning(f"⚠️ {method_name} unexpectedly accepted: {response.status_code}")
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1
                    logger.info(f"{method_name}: {response.status_code}")

            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.error(f"Error testing {method_name}: {e}")

    def test_special_characters_in_headers(self, base_url, test_endpoint):
        """Test with special characters and encodings in headers"""
        endpoint = f"{base_url}{test_endpoint}"

        special_headers = [
            {"Authorization": "Bearer test", "X-Custom": "< script>alert('xss')</script>"},
            {"Authorization": "Bearer test", "X-Custom": "../../../../etc/passwd"},
            {"Authorization": "Bearer test", "X-Custom": "' OR '1'='1"},
            {"Authorization": "Bearer test", "X-Custom": "\x00\x01\x02"},
            {"Authorization": "Bearer test", "X-Custom": "€ñ中文"},
        ]

        for i, test_headers in enumerate(special_headers):
            try:
                response = requests.get(
                    endpoint,
                    headers=test_headers,
                    verify=SSL_VERIFY,
                    timeout=REQUEST_TIMEOUT
                )

                _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
                _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
                _endpoint_results[test_endpoint]["test_count"] += 1

                if response.status_code == HTTP_OK or response.status_code == 401:
                    _endpoint_results[test_endpoint]["passed"] += 1
                else:
                    _endpoint_results[test_endpoint]["failed"] += 1
                    logger.warning(f"⚠️ Special header #{i+1} caused unexpected status: {response.status_code}")

            except Exception as e:
                _endpoint_results[test_endpoint]["test_count"] += 1
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.error(f"Error with special header #{i+1}: {e}")

    def test_cache_behavior(self, base_url, headers, test_endpoint):
        """Test caching behavior"""
        endpoint = f"{base_url}{test_endpoint}"

        # First request
        response1 = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
        etag1 = response1.headers.get('ETag')
        cache_control1 = response1.headers.get('Cache-Control')

        _endpoint_results[test_endpoint]["status_codes"].append(response1.status_code)
        _endpoint_results[test_endpoint]["response_times"].append(response1.elapsed.total_seconds())
        _endpoint_results[test_endpoint]["test_count"] += 1

        if response1.status_code == HTTP_OK:
            _endpoint_results[test_endpoint]["passed"] += 1
        else:
            _endpoint_results[test_endpoint]["failed"] += 1

        # Second request with If-None-Match
        if etag1:
            headers_with_etag = {**headers, "If-None-Match": etag1}
            response2 = requests.get(endpoint, headers=headers_with_etag, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

            _endpoint_results[test_endpoint]["status_codes"].append(response2.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response2.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response2.status_code == 304:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info("✓ Cache validation works (304 Not Modified)")
            elif response2.status_code == HTTP_OK:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info("⚠️ No cache validation (200 OK instead of 304)")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1

        logger.info(f"ETag: {etag1 or 'None'}, Cache-Control: {cache_control1 or 'None'}")

    def test_partial_token_variations(self, base_url, test_endpoint, auth_token):
        """Test with partial or modified tokens"""
        endpoint = f"{base_url}{test_endpoint}"

        token_variations = [
            auth_token[:-5],  # Truncated
            auth_token + "extra",  # Extended
            auth_token.upper(),  # Changed case
            auth_token[:10] + "X" * (len(auth_token) - 10),  # Corrupted middle
        ]

        for i, token in enumerate(token_variations):
            test_headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                endpoint,
                headers=test_headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            _endpoint_results[test_endpoint]["status_codes"].append(response.status_code)
            _endpoint_results[test_endpoint]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[test_endpoint]["test_count"] += 1

            if response.status_code == 401:
                _endpoint_results[test_endpoint]["passed"] += 1
                logger.info(f"✓ Token variation #{i+1} properly rejected")
            else:
                _endpoint_results[test_endpoint]["failed"] += 1
                logger.warning(f"⚠️ Token variation #{i+1} not rejected: {response.status_code}")
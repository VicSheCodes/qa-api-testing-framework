import allure
import pytest
import requests
import statistics
import time
from conftest import SSL_VERIFY, _endpoint_results
from constants import (
    HTTP_OK,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    REQUEST_TIMEOUT
)

from config.logger_config import get_test_logger

logger = get_test_logger()

# Suppress SSL warnings when using Charles
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@pytest.mark.discovery
@pytest.mark.slow
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
class TestEndpointsCommon:

    def test_basic_get(self, base_url, headers, endpoint_path):
        """Basic GET request validation"""
        endpoint = f"{base_url}{endpoint_path}"
        response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        if response.status_code == HTTP_OK:
            _endpoint_results[endpoint_path]["passed"] += 1
        else:
            _endpoint_results[endpoint_path]["failed"] += 1

        assert response.status_code in [HTTP_OK, HTTP_INTERNAL_ERROR, HTTP_SERVICE_UNAVAILABLE]

    def test_response_structure(self, base_url, headers, endpoint_path):
        """Verify response structure/format"""
        endpoint = f"{base_url}{endpoint_path}"
        response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        if response.status_code == HTTP_OK:
            _endpoint_results[endpoint_path]["passed"] += 1
            # Verify response can be parsed
            try:
                data = response.json()
                assert isinstance(data, (dict, list)), "Response must be JSON object or array"
                logger.info(f"Response structure: {type(data).__name__}")
            except ValueError:
                logger.info(f"Response is text, not JSON: {response.text[:100]}")
        else:
            _endpoint_results[endpoint_path]["failed"] += 1

    def test_response_time_consistency(self, base_url, headers, endpoint_path):
        """Test response time patterns"""
        endpoint = f"{base_url}{endpoint_path}"
        response_times = []

        for _ in range(15):
            start = time.time()
            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start
            response_times.append(elapsed)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(elapsed)
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

            time.sleep(0.2)

        # Check for outliers (times > 2x median)
        median_time = statistics.median(response_times)
        outliers = [t for t in response_times if t > median_time * 2]

        logger.info(f"Response times: min={min(response_times):.3f}s, max={max(response_times):.3f}s, median={median_time:.3f}s")
        if outliers:
            logger.warning(f"Detected {len(outliers)} outliers: {[f'{t:.3f}s' for t in outliers]}")

    def test_with_different_tokens(self, base_url, fresh_auth_token, endpoint_path):
        """Test with multiple fresh tokens to rule out auth issues"""
        endpoint = f"{base_url}{endpoint_path}"

        for i in range(3):
            headers = {"Authorization": f"Bearer {fresh_auth_token}"}
            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

            logger.info(f"Token #{i+1}: Status {response.status_code}")
            time.sleep(0.5)

    def test_redirect_detection(self, base_url, headers, endpoint_path):
        """Check for redirects"""
        endpoint = f"{base_url}{endpoint_path}"
        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False
        )

        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        if response.status_code in [301, 302, 303, 307, 308]:
            logger.warning(f"⚠️ Redirect detected: {response.status_code} → {response.headers.get('Location')}")
            _endpoint_results[endpoint_path]["failed"] += 1
        elif response.status_code == HTTP_OK:
            _endpoint_results[endpoint_path]["passed"] += 1
        else:
            _endpoint_results[endpoint_path]["failed"] += 1

    def test_server_routing(self, base_url, headers, endpoint_path):
        """Test backend routing consistency"""
        endpoint = f"{base_url}{endpoint_path}"
        server_headers = []

        for _ in range(10):
            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            server_id = response.headers.get('Server', 'unknown')
            server_headers.append(server_id)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

            time.sleep(0.1)

        unique_servers = set(server_headers)
        if len(unique_servers) > 1:
            logger.warning(f"⚠️ Multiple servers detected: {unique_servers}")
        else:
            logger.info(f"Consistent routing: {unique_servers}")

    @pytest.mark.parametrize("sequence", [
        [1, 3, 4],
        [1, 2, 3],
        [3, 4, 5],
        [1, 4, 5, 6]
    ])
    def test_after_sequence(self, base_url, fresh_auth_token, endpoint_path, sequence):
        """Test if endpoint requires calling other endpoints first"""
        headers = {"Authorization": f"Bearer {fresh_auth_token}"}
        session = requests.Session()

        logger.info(f"\nTesting {endpoint_path} after sequence: {' → '.join(str(e) for e in sequence)}")

        # Call all endpoints in sequence
        for endpoint_num in sequence:
            endpoint = f"{base_url}/api/test/{endpoint_num}"
            response = session.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            logger.info(f"  Called /api/test/{endpoint_num}: {response.status_code}")
            time.sleep(0.3)

        # Finally call target endpoint
        final_endpoint = f"{base_url}{endpoint_path}"
        response = session.get(final_endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        if response.status_code == HTTP_OK:
            _endpoint_results[endpoint_path]["passed"] += 1
            logger.warning(f"⚠️ {endpoint_path} succeeded after sequence: {sequence}")
        else:
            _endpoint_results[endpoint_path]["failed"] += 1

    def test_consistency_rapid_fire(self, base_url, headers, endpoint_path):
        """Test consistency with rapid requests"""
        endpoint = f"{base_url}{endpoint_path}"
        status_codes = []

        for _ in range(10):
            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            status_codes.append(response.status_code)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

        logger.info(f"Status codes: {status_codes}")

    def test_consistency_with_delays(self, base_url, headers, endpoint_path):
        """Test consistency with 1s delays"""
        endpoint = f"{base_url}{endpoint_path}"

        for i in range(5):
            if i > 0:
                time.sleep(1.0)

            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

    def test_timing_analysis(self, base_url, headers, endpoint_path):
        """Statistical timing analysis"""
        endpoint = f"{base_url}{endpoint_path}"
        response_times = []

        for _ in range(10):
            start = time.time()
            response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start
            response_times.append(elapsed)

            _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(elapsed)
            _endpoint_results[endpoint_path]["test_count"] += 1

            if response.status_code == HTTP_OK:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

        avg = statistics.mean(response_times)
        median = statistics.median(response_times)
        stdev = statistics.stdev(response_times) if len(response_times) > 1 else 0

        logger.info(f"Timing - Avg: {avg:.3f}s, Median: {median:.3f}s, StdDev: {stdev:.3f}s")

    def test_different_http_methods(self, base_url, headers, endpoint_path):
        """Test POST, PUT, DELETE, PATCH methods"""
        endpoint = f"{base_url}{endpoint_path}"

        for method in ["POST", "PUT", "DELETE", "PATCH"]:
            response = requests.request(method, endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            logger.info(f"{method}: {response.status_code}")

    def test_with_query_parameters(self, base_url, headers, endpoint_path):
        """Test with various query parameters"""
        endpoint = f"{base_url}{endpoint_path}"

        params_list = [
            {"id": "1"},
            {"action": "test"},
            {"debug": "true"}
        ]

        for params in params_list:
            response = requests.get(endpoint, headers=headers, params=params, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            logger.info(f"Params {params}: {response.status_code}")

    def test_additional_headers(self, base_url, headers, endpoint_path):
        """Test with different header combinations"""
        endpoint = f"{base_url}{endpoint_path}"

        test_headers = [
            {**headers, "X-Custom-Header": "test"},
            {**headers, "Accept": "application/json"},
            {**headers, "User-Agent": "Test-Client/1.0"}
        ]

        for test_header in test_headers:
            response = requests.get(endpoint, headers=test_header, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            logger.info(f"Headers: {response.status_code}")
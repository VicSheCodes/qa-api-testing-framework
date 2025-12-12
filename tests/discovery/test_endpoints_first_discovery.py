import pytest
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from config.logger_config import get_test_logger
from constants import (
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    HTTP_OK
)
from conftest import _endpoint_results, SSL_VERIFY

logger = get_test_logger()

# Suppress SSL warnings when using Charles Proxy
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@pytest.mark.discovery
@pytest.mark.regression
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_endpoint_basic_availability(base_url, headers, endpoint_path):
    """
    Basic availability test for API endpoints.

    Validates that:
    - Endpoint is reachable with valid authentication
    - Returns a response status code

    Part of initial endpoint behavior discovery phase.
    """
    endpoint = f"{base_url}{endpoint_path}"

    start_time = time.time()
    response = requests.get(endpoint, headers=headers, verify=SSL_VERIFY)
    response_time = time.time() - start_time

    # Record results for summary
    _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
    _endpoint_results[endpoint_path]["response_times"].append(response_time)
    _endpoint_results[endpoint_path]["test_count"] += 1

    if response.status_code == HTTP_OK:
        _endpoint_results[endpoint_path]["passed"] += 1
    else:
        _endpoint_results[endpoint_path]["failed"] += 1

        assert response.status_code is not None, "No status code returned"
    assert hasattr(response, 'status_code'), "Response missing status_code attribute"

    logger.info(f"\nEndpoint: {endpoint_path}")
    logger.info(f"Observed Status: {response.status_code}, Response Time: {response_time:.3f}s")
    logger.info(f"Body Preview: {response.text[:100]}")

    assert isinstance(response.status_code, int), "Invalid status code type"
    assert 100 <= response.status_code < 600, f"Status code out of valid HTTP range: {response.status_code}"


@pytest.mark.discovery
@pytest.mark.slow
@pytest.mark.parametrize("endpoint_num,num_requests,delay,increase_delay", [
    # Quick discovery - single request
    (1, 1, 0, False),
    (2, 1, 0, False),   # Endpoint 2 known 500 on first call
    (3, 1, 0, False),
    (4, 1, 0, False),
    (5, 1, 0, False),
    (6, 1, 0, False),

    # Consistency check - multiple rapid requests
    (1, 10, 0, False),
    (2, 10, 0, False),
    (3, 10, 0, False),
    (4, 30, 0, False),
    (5, 10, 0, False),
    (6, 10, 0, False),

    # Fixed delay between requests (1 second)
    (1, 10, 1.0, False),
    (3, 10, 1.0, False),  # Endpoint 3 mentioned warmup
    (4, 20, 1.0, False),  # Endpoint 4 known instability 429 after 4 calls
    (5, 10, 1.0, False),
    (6, 10, 1.0, False),

    # Increasing delay, start 0.5s, increases each iteration
    (1, 10, 0.5, True),
    (3, 10, 0.5, True),
    (4, 10, 0.5, True),
    (5, 10, 0.5, True),
    (6, 10, 0.5, True),

    # Long-running consistency (20 requests)
    (1, 20, 0.5, False),
    (3, 20, 0.5, False),
    (4, 20, 1.0, False),
    (5, 20, 0.5, False),
    (6, 20, 1.0, False),
])
def test_endpoints_discovery(base_url, fresh_auth_token, endpoint_num, discovery_report,
                           num_requests, delay, increase_delay):
    """
    Discover endpoint behavior through systematic testing.

    Tests for:
    - Initial response (first call)
    - Consistency across multiple calls
    - Recovery patterns (error -> success)
    - Warmup requirements
    - Rate limiting behavior
    """
    endpoint = f"{base_url}/api/test/{endpoint_num}"
    headers = {"Authorization": f"Bearer {fresh_auth_token}"}

    results = []
    first_success_at = None
    error_count = 0
    current_delay = delay

    for i in range(num_requests):
        if i > 0 and current_delay > 0:
            time.sleep(current_delay)
            if increase_delay:
                current_delay *= 1.5  # Exponential backoff

        start_time = time.time()
        # response = requests.get(endpoint, headers=headers)
        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY  # ← ADD THIS FOR CHARLES
        )
        elapsed = time.time() - start_time

        result = {
            "request_num": i + 1,
            "status_code": response.status_code,
            "response_time": elapsed,
            "delay_before": current_delay if i > 0 else 0,
        }

        # Capture response body for analysis
        try:
            result["response_body"] = response.json()
        except:
            result["response_body"] = response.text[:100]  # First 100 chars

        # Track first success after errors
        if response.status_code == 200 and first_success_at is None and error_count > 0:
            first_success_at = i + 1
            result["recovered"] = True

        if response.status_code != 200:
            error_count += 1

        results.append(result)

        # Write results to report
    discovery_report.write_test_results(
        endpoint_num, num_requests, delay, increase_delay, results)

    # Analyze results
    status_codes = [r["status_code"] for r in results]
    success_count = status_codes.count(200)

    # Log discovery findings
    logger.info(f"\n=== Endpoint {endpoint_num} Discovery ===")
    logger.info(f"Requests: {num_requests}, Delay: {delay}s, Increasing: {increase_delay}")
    logger.info(f"Success rate: {success_count}/{num_requests}")
    logger.info(f"Status codes: {status_codes}")

    if first_success_at:
        logger.info(f"⚠ Recovered at request #{first_success_at}")

    if error_count > 0:
        logger.info(f" Errors: {error_count}")

    # Assertions based on patterns
    if num_requests == 1:
        assert response.status_code in [200, 500, 503], \
            f"Unexpected status code: {response.status_code}"
    else:
        # For multiple requests, at least track if there's a pattern
        assert len(results) == num_requests, "Not all requests completed"



class EndpointDiscoveryReport:
    """Generate comprehensive test reports"""

    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.output_dir / f"endpoint_discovery_{self.timestamp}.txt"

    def write_header(self):
        """Write report header"""
        with open(self.report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("API ENDPOINT DISCOVERY REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

    def write_test_results(self, endpoint_num: int, num_requests: int,
                          delay: float, increase_delay: bool, results: List[Dict]):
        """Write detailed test results"""
        with open(self.report_file, 'a') as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"ENDPOINT /api/test/{endpoint_num}\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"Test Configuration:\n")
            f.write(f"  - Number of Requests: {num_requests}\n")
            f.write(f"  - Base Delay: {delay}s\n")
            f.write(f"  - Increasing Delay: {increase_delay}\n")
            f.write(f"\n")

            # Status code summary
            status_codes = [r["status_code"] for r in results]
            success_count = status_codes.count(200)
            error_count = len(status_codes) - success_count

            f.write(f"Results Summary:\n")
            f.write(f"  - Total Requests: {len(results)}\n")
            f.write(f"  - Successful (200): {success_count}\n")
            f.write(f"  - Failed: {error_count}\n")
            f.write(f"  - Success Rate: {(success_count/len(results)*100):.1f}%\n")
            f.write(f"\n")

            # Response time statistics
            response_times = [r["response_time"] for r in results]
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)

            f.write(f"Response Time Analysis:\n")
            f.write(f"  - Average: {avg_time:.3f}s\n")
            f.write(f"  - Minimum: {min_time:.3f}s\n")
            f.write(f"  - Maximum: {max_time:.3f}s\n")
            f.write(f"\n")

            # Detailed request log
            f.write(f"Detailed Request Log:\n")
            f.write(f"{'-' * 80}\n")

            for r in results:
                status_symbol = "✓" if r["status_code"] == 200 else "✗"
                f.write(f"Request #{r['request_num']:2d}: {status_symbol} "
                       f"Status={r['status_code']} "
                       f"Time={r['response_time']:.3f}s "
                       f"Delay={r['delay_before']:.3f}s")

                if r.get("recovered"):
                    f.write(" [RECOVERED FROM ERROR]")

                if "response_body" in r:
                    f.write(f"\n              Body: {r['response_body']}")

                f.write("\n")

            # Pattern analysis
            f.write(f"\n{'-' * 80}\n")
            f.write(f"Pattern Analysis:\n")

            # Check for consistency
            if len(set(status_codes)) == 1:
                f.write(f"  ✓ CONSISTENT: All requests returned {status_codes[0]}\n")
            else:
                f.write(f"  ⚠ INCONSISTENT: Multiple status codes observed\n")
                f.write(f"    Status code distribution: {dict((x, status_codes.count(x)) for x in set(status_codes))}\n")

            # Check for recovery pattern
            if error_count > 0 and success_count > 0:
                first_success = next((i for i, r in enumerate(results) if r["status_code"] == 200), None)
                if first_success and first_success > 0:
                    f.write(f"  ⚠ WARMUP REQUIRED: First success at request #{first_success + 1}\n")

            # Check for rate limiting
            if 429 in status_codes:
                f.write(f"  ⚠ RATE LIMITING DETECTED: {status_codes.count(429)} requests throttled\n")

            f.write(f"\n")


@pytest.fixture(scope="session")
def discovery_report():
    """Session-scoped report generator"""
    report = EndpointDiscoveryReport()
    report.write_header()
    return report

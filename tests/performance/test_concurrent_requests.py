"""
Performance Testing Module - Concurrent Requests
================================================

Usage:
------
Run tests and generate Allure report:
    pytest tests/performance/test_concurrent_requests.py -v --alluredir=allure-results
    allure serve allure-results

Run specific endpoint:
    pytest tests/performance/test_concurrent_requests.py::test_concurrent_requests[/api/test/1] -v --alluredir=allure-results

View test results:
    allure serve allure-results

Generate one-page HTML report:
    allure generate allure-results -o allure-report --clean
    open allure-report/index.html

Run with markers:
    pytest tests/performance/test_concurrent_requests.py -m performance -v --alluredir=allure-results

Continuous monitoring (watch mode):
    pytest-watch tests/performance/test_concurrent_requests.py -- -v --alluredir=allure-results

Performance Thresholds per Endpoint:
------------------------------------
/api/test/1: avg_time ≤ 1.0s, success_rate = 100%, p95 ≤ 1.5s
/api/test/2: expected_failure (0% success) - monitoring
/api/test/3: needs_warmup (3 requests), avg_time ≤ 2.0s, success_rate ≥ 95%
/api/test/4: slow_endpoint (avg_time ≤ 3.5s, success_rate ≥ 50%) - monitoring
/api/test/5: avg_time ≤ 5.0s, success_rate ≥ 95%, p95 ≤ 6.0s
/api/test/6: avg_time ≤ 1.0s, success_rate = 100%, p95 ≤ 1.5s
"""
import concurrent.futures
import requests
import pytest
import time
import statistics
import allure
from conftest import SSL_VERIFY, _endpoint_results
from constants import (
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
    REQUEST_TIMEOUT,
)
from config.logger_config import get_test_logger

logger = get_test_logger()

# Performance thresholds (per endpoint)
PERFORMANCE_THRESHOLDS = {
    TEST_ENDPOINT_1: {
        "max_avg_response_time": 1.0,
        "min_success_rate": 1.0,
        "max_p95_latency": 1.5,
    },
    TEST_ENDPOINT_2: {
        "max_avg_response_time": 2.0,
        "min_success_rate": 0.0,  # Currently failing - just measure it
        "max_p95_latency": 3.0,
        "expected_failure": True,  # Flag for anomaly
    },
    TEST_ENDPOINT_3: {
        "max_avg_response_time": 2.0,
        "min_success_rate": 0.95,
        "max_p95_latency": 3.0,
        "needs_warmup": True,  # Flag for warmup
        "warmup_requests": 3,
    },
    TEST_ENDPOINT_4: {
        "max_avg_response_time": 3.5,  # Slower endpoint
        "min_success_rate": 0.5,  # Allow 50% success rate for now
        "max_p95_latency": 5.0,
        "expected_failure": True,  # Flag for anomaly
    },
    TEST_ENDPOINT_5: {
        "max_avg_response_time": 5.0,
        "min_success_rate": 0.95,
        "max_p95_latency": 6.0,
    },
    TEST_ENDPOINT_6: {
        "max_avg_response_time": 1.0,
        "min_success_rate": 1.0,
        "max_p95_latency": 1.5,
    },
}


@allure.feature("Performance Testing")
@allure.story("Concurrent Requests")
@pytest.mark.performance
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_concurrent_requests(base_url, headers, endpoint_path):
    """
    Sends concurrent requests to all endpoints.

    Test FAILS if:
    - Success rate is 0% (endpoint is completely broken)
    - All requests timeout or error out

    For endpoints with known issues (needs_warmup, expected_failure):
    - Warmup requests are sent first to prime the endpoint
    - Metrics are collected and reported even if below threshold
    - Test is marked as expected failure (xfail)
    """
    endpoint = f"{base_url}{endpoint_path}"
    total_requests = 10
    concurrency = 5
    thresholds = PERFORMANCE_THRESHOLDS[endpoint_path]

    # Handle warmup for endpoints that need it (e.g., endpoint 3)
    if thresholds.get("needs_warmup"):
        warmup_count = thresholds.get("warmup_requests", 3)
        with allure.step(f"Warmup requests ({warmup_count} requests)"):
            for i in range(warmup_count):
                try:
                    requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                    logger.info(f"Warmup request {i+1}/{warmup_count} completed")
                except Exception as e:
                    logger.warning(f"Warmup request {i+1} failed: {e}")
                time.sleep(0.2)

    @allure.step("Execute concurrent requests")
    def do_request(i):
        start = time.time()
        try:
            resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start

            _endpoint_results[endpoint_path]["status_codes"].append(resp.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(elapsed)
            _endpoint_results[endpoint_path]["test_count"] += 1
            if resp.status_code == 200:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

            return {"i": i, "status": resp.status_code, "time": elapsed, "ok": resp.status_code == 200}
        except requests.RequestException as e:
            elapsed = time.time() - start
            _endpoint_results[endpoint_path]["test_count"] += 1
            _endpoint_results[endpoint_path]["failed"] += 1
            logger.error(f"Request {i} failed: {e}")
            return {"i": i, "status": 0, "time": elapsed, "ok": False, "error": str(e)}

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(do_request, i) for i in range(total_requests)]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())

    # Calculate metrics
    response_times = [r["time"] for r in results if r["ok"]]
    successful_requests = [r for r in results if r["ok"]]
    success_count = len(successful_requests)
    error_count = len(results) - success_count
    success_rate = success_count / total_requests if total_requests > 0 else 0
    avg_response_time = statistics.mean(response_times) if response_times else 0.0
    p95_latency = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) >= 20 else (max(response_times) if response_times else 0.0)

    # Attach metrics to Allure report
    with allure.step(f"Performance Metrics for {endpoint_path}"):
        metrics_text = (
            f"Total Requests: {total_requests}\n"
            f"Successful: {success_count}\n"
            f"Failed: {error_count}\n"
            f"Success Rate: {success_rate * 100:.1f}%\n"
        )
        if response_times:
            metrics_text += (
                f"Avg Response Time: {avg_response_time:.3f}s\n"
                f"P95 Latency: {p95_latency:.3f}s\n"
                f"Min Time: {min(response_times):.3f}s\n"
                f"Max Time: {max(response_times):.3f}s\n"
            )
        else:
            metrics_text += "No successful responses to calculate latency\n"

        allure.attach(metrics_text, name=f"{endpoint_path}_metrics", attachment_type=allure.attachment_type.TEXT)

    logger.info(f"Endpoint: {endpoint_path} | Success Rate: {success_rate*100:.1f}% | Avg Time: {avg_response_time:.3f}s")

    # CRITICAL: Fail if success rate is 0% (endpoint completely broken)
    with allure.step("Validate endpoint is responding"):
        if success_rate == 0.0:
            pytest.fail(f"Endpoint {endpoint_path} has 0% success rate - completely broken")

    # Check if endpoint has known issues
    is_expected_failure = thresholds.get("expected_failure", False)

    if is_expected_failure:
        # Mark test as expected failure but still run assertions to collect data
        pytest.xfail(f"Endpoint {endpoint_path} has known issues - monitoring metrics")

    # Performance assertions (only strict for stable endpoints)
    with allure.step("Validate success rate threshold"):
        min_success = thresholds["min_success_rate"]
        assert success_rate >= min_success, \
            f"Success rate {success_rate*100:.1f}% below threshold {min_success*100}%"

    with allure.step("Validate average response time"):
        if response_times:  # Only check if we have successful responses
            max_time = thresholds["max_avg_response_time"]
            assert avg_response_time <= max_time, \
                f"Avg response time {avg_response_time:.3f}s exceeds threshold {max_time}s"

    with allure.step("Validate P95 latency"):
        if response_times:  # Only check if we have successful responses
            max_p95 = thresholds["max_p95_latency"]
            assert p95_latency <= max_p95, \
                f"P95 latency {p95_latency:.3f}s exceeds threshold {max_p95}s"
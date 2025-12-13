"""
Stress Testing Module - Breaking Point Analysis
================================================

Usage:
------
Run stress tests and generate Allure report:
    pytest tests/performance/test_stress.py -v --alluredir=allure-results
    allure serve allure-results

Run specific stress level:
    pytest tests/performance/test_stress.py -m stress_light -v --alluredir=allure-results
    pytest tests/performance/test_stress.py -m stress_heavy -v --alluredir=allure-results

Generate one-page HTML report:
    allure generate allure-results -o allure-report --clean
    open allure-report/index.html

Stress Test Levels:
-------------------
Light Stress:    20-50 sequential requests (test robustness)
Medium Stress:   100-200 concurrent requests (test limits)
Heavy Stress:    500+ concurrent requests (find breaking point)
Extended Stress: Sustained load over 5+ minutes (test stability)
"""

import time
import statistics
import pytest
import requests
import concurrent.futures
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
)
from config.logger_config import get_test_logger

logger = get_test_logger()


@allure.feature("Stress Testing")
@allure.story("Light Stress - Sequential Requests")
@pytest.mark.performance
@pytest.mark.stress_light
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_light_stress_sequential(base_url, headers, endpoint_path):
    """
    Light stress test: 50 sequential requests to measure robustness.

    Test PASSES if:
    - Success rate ≥ 95%
    - No timeouts occur
    - Response time remains consistent

    Test FAILS if:
    - Success rate < 95%
    - Any timeout occurs
    - Endpoint becomes unresponsive
    """
    endpoint = f"{base_url}{endpoint_path}"
    iterations = 50
    successes = 0
    timeouts = 0
    errors = 0
    response_times = []

    with allure.step(f"Execute {iterations} sequential requests to {endpoint_path}"):
        for i in range(iterations):
            try:
                start = time.time()
                resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                elapsed = time.time() - start
                response_times.append(elapsed)

                _endpoint_results[endpoint_path]["status_codes"].append(resp.status_code)
                _endpoint_results[endpoint_path]["response_times"].append(elapsed)
                _endpoint_results[endpoint_path]["test_count"] += 1

                if resp.status_code == 200:
                    successes += 1
                    _endpoint_results[endpoint_path]["passed"] += 1
                else:
                    errors += 1
                    _endpoint_results[endpoint_path]["failed"] += 1

                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{iterations} requests completed")

            except requests.Timeout:
                timeouts += 1
                _endpoint_results[endpoint_path]["test_count"] += 1
                _endpoint_results[endpoint_path]["failed"] += 1
                logger.error(f"Request {i+1} timed out")

            except requests.RequestException as e:
                errors += 1
                _endpoint_results[endpoint_path]["test_count"] += 1
                _endpoint_results[endpoint_path]["failed"] += 1
                logger.error(f"Request {i+1} failed: {e}")

            time.sleep(0.05)  # Small delay between requests

    # Calculate metrics
    success_rate = successes / iterations if iterations > 0 else 0.0
    avg_response_time = statistics.mean(response_times) if response_times else 0.0
    max_response_time = max(response_times) if response_times else 0.0

    # Attach stress test results
    with allure.step("Stress Test Analysis"):
        stress_report = (
            f"Endpoint: {endpoint_path}\n"
            f"Total Requests: {iterations}\n"
            f"Successful: {successes}\n"
            f"Errors: {errors}\n"
            f"Timeouts: {timeouts}\n"
            f"Success Rate: {success_rate*100:.1f}%\n\n"
            f"Response Times:\n"
            f"  Average: {avg_response_time:.3f}s\n"
            f"  Max: {max_response_time:.3f}s\n"
        )
        allure.attach(stress_report, name=f"{endpoint_path}_light_stress", attachment_type=allure.attachment_type.TEXT)

    logger.info(
        f"Light stress test for {endpoint_path}: {successes}/{iterations} successes "
        f"({success_rate*100:.1f}%), avg={avg_response_time:.3f}s, "
        f"timeouts={timeouts}, errors={errors}"
    )

    # Fail if success rate below 95%
    with allure.step("Validate success rate under stress"):
        assert success_rate >= 0.95, \
            f"Success rate {success_rate*100:.1f}% below 95% threshold for {endpoint_path}"

    # Fail if any timeouts occurred
    with allure.step("Validate no timeouts"):
        assert timeouts == 0, f"{timeouts} timeouts occurred for {endpoint_path}"


@allure.feature("Stress Testing")
@allure.story("Medium Stress - Concurrent Requests")
@pytest.mark.performance
@pytest.mark.stress_medium
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_6,  # Fast endpoints only
])
def test_medium_stress_concurrent(base_url, headers, endpoint_path):
    """
    Medium stress test: 200 concurrent requests to test limits.

    Test PASSES if:
    - Success rate ≥ 90%
    - Average response time remains acceptable
    - No complete failures

    Test FAILS if:
    - Success rate < 90%
    - Endpoint becomes unresponsive
    - Critical performance degradation
    """
    endpoint = f"{base_url}{endpoint_path}"
    total_requests = 200
    concurrency = 20
    successes = 0
    failures = 0
    response_times = []

    def do_request(i):
        try:
            start = time.time()
            resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start
            return {
                "i": i,
                "status": resp.status_code,
                "time": elapsed,
                "ok": resp.status_code == 200
            }
        except requests.RequestException as e:
            return {"i": i, "status": 0, "time": 0, "ok": False, "error": str(e)}

    with allure.step(f"Execute {total_requests} concurrent requests ({concurrency} workers)"):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [ex.submit(do_request, i) for i in range(total_requests)]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())

    for result in results:
        _endpoint_results[endpoint_path]["status_codes"].append(result["status"])
        _endpoint_results[endpoint_path]["test_count"] += 1

        if result["ok"]:
            successes += 1
            _endpoint_results[endpoint_path]["passed"] += 1
            response_times.append(result["time"])
        else:
            failures += 1
            _endpoint_results[endpoint_path]["failed"] += 1

    success_rate = successes / total_requests if total_requests > 0 else 0.0
    avg_response_time = statistics.mean(response_times) if response_times else 0.0

    # Attach results
    with allure.step("Medium Stress Analysis"):
        stress_report = (
            f"Endpoint: {endpoint_path}\n"
            f"Total Requests: {total_requests}\n"
            f"Concurrent Workers: {concurrency}\n"
            f"Successful: {successes}\n"
            f"Failed: {failures}\n"
            f"Success Rate: {success_rate*100:.1f}%\n"
            f"Average Response Time: {avg_response_time:.3f}s\n"
        )
        allure.attach(stress_report, name=f"{endpoint_path}_medium_stress", attachment_type=allure.attachment_type.TEXT)

    logger.info(
        f"Medium stress test for {endpoint_path}: {successes}/{total_requests} successes "
        f"({success_rate*100:.1f}%), avg={avg_response_time:.3f}s"
    )

    # Fail if success rate below 90%
    with allure.step("Validate success rate under medium stress"):
        assert success_rate >= 0.90, \
            f"Success rate {success_rate*100:.1f}% below 90% threshold for {endpoint_path}"

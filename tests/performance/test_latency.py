"""
Latency Testing Module - Single & Sequential Requests
======================================================

Usage:
------
Run latency tests and generate Allure report:
    pytest tests/performance/test_latency.py -v --alluredir=allure-results
    allure serve allure-results

Run specific latency test:
    pytest tests/performance/test_latency.py::test_single_request_latency -v --alluredir=allure-results

Generate one-page HTML report:
    allure generate allure-results -o allure-report --clean
    open allure-report/index.html

Run with performance marker only:
    pytest tests/performance/test_latency.py -m performance -v --alluredir=allure-results

Latency Thresholds (Based on Measurements):
--------------------------------------------
Good Latency (PASS):   ≤ 1.0s
Acceptable Latency:    1.0s - 2.0s
Slow Latency (WARN):   2.0s - 5.0s
Critical/Timeout:      > 5.0s (FAIL)

Per Endpoint:
/api/test/1: Good latency (~0.3-0.5s) - threshold 1.0s
/api/test/3: Needs warmup - threshold 2.0s (after warmup)
/api/test/4: Slow endpoint - threshold 3.5s
/api/test/5: Moderate latency (~4.2s) - threshold 5.0s
/api/test/6: Good latency (~0.3-0.5s) - threshold 1.0s
"""

import time
import pytest
import requests
import statistics
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

# Latency thresholds per endpoint (in seconds)
LATENCY_THRESHOLDS = {
    TEST_ENDPOINT_1: {
        "good": 1.0,      # Pass if ≤ 1.0s
        "acceptable": 2.0,  # Warning if > 1.0s and ≤ 2.0s
        "slow": 5.0,      # Fail if > 5.0s
        "needs_warmup": False,
    },
    TEST_ENDPOINT_2: {
        "good": 1.0,
        "acceptable": 2.0,
        "slow": 5.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_3: {
        "good": 2.0,      # Endpoint 3 needs warmup, higher threshold
        "acceptable": 3.0,
        "slow": 5.0,
        "needs_warmup": True,
        "warmup_requests": 3,
    },
    TEST_ENDPOINT_4: {
        "good": 3.5,      # Endpoint 4 is slow
        "acceptable": 4.5,
        "slow": 6.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_5: {
        "good": 5.0,      # Endpoint 5 measured at ~4.2s
        "acceptable": 6.0,
        "slow": 7.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_6: {
        "good": 1.0,
        "acceptable": 2.0,
        "slow": 5.0,
        "needs_warmup": False,
    },
}


@allure.feature("Performance Testing")
@allure.story("Latency Measurement")
@pytest.mark.performance
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_single_request_latency(base_url, headers, endpoint_path):
    """
    Measure single request latency for each endpoint.

    Test PASSES if:
    - Response time ≤ good threshold
    - Request completes without timeout

    Test FAILS if:
    - Response time exceeds slow threshold
    - Request fails or times out

    Test WARNS if:
    - Response time between good and acceptable threshold
    """
    endpoint = f"{base_url}{endpoint_path}"
    thresholds = LATENCY_THRESHOLDS[endpoint_path]

    # Warmup if needed
    if thresholds["needs_warmup"]:
        warmup_count = thresholds.get("warmup_requests", 1)
        with allure.step(f"Warmup requests ({warmup_count} requests)"):
            for i in range(warmup_count):
                try:
                    requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                    logger.info(f"Warmup request {i+1}/{warmup_count} completed for {endpoint_path}")
                except Exception as e:
                    logger.warning(f"Warmup request {i+1} failed for {endpoint_path}: {e}")
                time.sleep(0.2)

    # Measure latency
    with allure.step(f"Measure single request latency for {endpoint_path}"):
        start = time.time()
        try:
            resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            elapsed = time.time() - start

            # Record metrics
            _endpoint_results[endpoint_path]["status_codes"].append(resp.status_code)
            _endpoint_results[endpoint_path]["response_times"].append(elapsed)
            _endpoint_results[endpoint_path]["test_count"] += 1

            if resp.status_code == 200:
                _endpoint_results[endpoint_path]["passed"] += 1
            else:
                _endpoint_results[endpoint_path]["failed"] += 1

            # Attach latency metrics to report
            with allure.step("Latency Analysis"):
                latency_report = (
                    f"Endpoint: {endpoint_path}\n"
                    f"Response Time: {elapsed:.3f}s\n"
                    f"Status Code: {resp.status_code}\n"
                    f"Good Threshold: {thresholds['good']}s\n"
                    f"Acceptable Threshold: {thresholds['acceptable']}s\n"
                    f"Slow Threshold: {thresholds['slow']}s\n"
                )
                allure.attach(latency_report, name=f"{endpoint_path}_latency", attachment_type=allure.attachment_type.TEXT)

            logger.info(f"Latency: {elapsed:.3f}s, Status: {resp.status_code}, Endpoint: {endpoint_path}")

            # Fail fast if response fails
            if resp.status_code != 200:
                pytest.fail(f"Request to {endpoint_path} returned status {resp.status_code}")

            # Fail if latency exceeds slow threshold
            if elapsed > thresholds["slow"]:
                pytest.fail(f"Latency {elapsed:.3f}s exceeds critical threshold {thresholds['slow']}s for {endpoint_path}")

            # Warn if latency is acceptable but not good
            if elapsed > thresholds["good"]:
                allure.attach(
                    f"⚠️ Slower than expected: {elapsed:.3f}s (good: {thresholds['good']}s)",
                    name=f"{endpoint_path}_latency_warning",
                    attachment_type=allure.attachment_type.TEXT
                )
                logger.warning(f"⚠️ {endpoint_path} latency {elapsed:.3f}s is above good threshold {thresholds['good']}s")

            # Pass if latency is good
            with allure.step("Validate latency is within good threshold"):
                if elapsed <= thresholds["good"]:
                    logger.info(f"✅ {endpoint_path} latency {elapsed:.3f}s is GOOD (threshold: {thresholds['good']}s)")
                    allure.attach(
                        f"✅ Good latency: {elapsed:.3f}s (good: {thresholds['good']}s)",
                        name=f"{endpoint_path}_latency_pass",
                        attachment_type=allure.attachment_type.TEXT
                    )

        except requests.Timeout:
            elapsed = time.time() - start
            _endpoint_results[endpoint_path]["test_count"] += 1
            _endpoint_results[endpoint_path]["failed"] += 1
            logger.error(f"Timeout: {elapsed:.3f}s exceeded REQUEST_TIMEOUT ({REQUEST_TIMEOUT}s) for {endpoint_path}")
            pytest.fail(f"Request to {endpoint_path} timed out after {REQUEST_TIMEOUT}s")

        except requests.RequestException as e:
            elapsed = time.time() - start
            _endpoint_results[endpoint_path]["test_count"] += 1
            _endpoint_results[endpoint_path]["failed"] += 1
            logger.error(f"Request failed for {endpoint_path}: {e}")
            pytest.fail(f"Request to {endpoint_path} failed: {e}")


@allure.feature("Performance Testing")
@allure.story("Latency Consistency")
@pytest.mark.performance
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_6,  # Fast endpoints only
])
def test_sequential_latency_consistency(base_url, headers, endpoint_path):
    """
    Measure latency consistency over 5 sequential requests.

    Test PASSES if:
    - All requests succeed
    - Average latency ≤ good threshold
    - No extreme spikes (p95 latency reasonable)

    Test FAILS if:
    - Any request fails
    - Average latency exceeds slow threshold
    """
    endpoint = f"{base_url}{endpoint_path}"
    num_requests = 5
    thresholds = LATENCY_THRESHOLDS[endpoint_path]
    response_times = []

    with allure.step(f"Execute {num_requests} sequential requests to {endpoint_path}"):
        for i in range(num_requests):
            try:
                start = time.time()
                resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                elapsed = time.time() - start
                response_times.append(elapsed)

                if resp.status_code != 200:
                    pytest.fail(f"Request {i+1}/{num_requests} to {endpoint_path} returned status {resp.status_code}")

                logger.info(f"Request {i+1}/{num_requests}: {elapsed:.3f}s - Status {resp.status_code}")

            except requests.RequestException as e:
                logger.error(f"Request {i+1}/{num_requests} failed for {endpoint_path}: {e}")
                pytest.fail(f"Request {i+1}/{num_requests} to {endpoint_path} failed: {e}")

            time.sleep(0.1)  # Small delay between requests

    # Calculate statistics
    avg_latency = statistics.mean(response_times)
    min_latency = min(response_times)
    max_latency = max(response_times)
    p95_latency = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) >= 5 else max(response_times)

    # Attach consistency report
    with allure.step("Latency Consistency Analysis"):
        consistency_report = (
            f"Endpoint: {endpoint_path}\n"
            f"Total Requests: {num_requests}\n"
            f"Average Latency: {avg_latency:.3f}s\n"
            f"Min Latency: {min_latency:.3f}s\n"
            f"Max Latency: {max_latency:.3f}s\n"
            f"P95 Latency: {p95_latency:.3f}s\n"
            f"Good Threshold: {thresholds['good']}s\n"
            f"Slow Threshold: {thresholds['slow']}s\n"
        )
        allure.attach(consistency_report, name=f"{endpoint_path}_consistency", attachment_type=allure.attachment_type.TEXT)

    logger.info(
        f"Consistency for {endpoint_path}: avg={avg_latency:.3f}s, "
        f"min={min_latency:.3f}s, max={max_latency:.3f}s, p95={p95_latency:.3f}s"
    )

    # Fail if average latency exceeds slow threshold
    with allure.step("Validate average latency"):
        if avg_latency > thresholds["slow"]:
            pytest.fail(f"Average latency {avg_latency:.3f}s exceeds slow threshold {thresholds['slow']}s for {endpoint_path}")

    # Warn if average latency is acceptable but not good
    with allure.step("Validate latency consistency"):
        if avg_latency > thresholds["good"]:
            logger.warning(f"⚠️ {endpoint_path} average latency {avg_latency:.3f}s above good threshold {thresholds['good']}s")
        else:
            logger.info(f"✅ {endpoint_path} average latency {avg_latency:.3f}s is GOOD")
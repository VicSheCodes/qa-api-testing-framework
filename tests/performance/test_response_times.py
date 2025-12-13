"""
Response Time Statistics Testing Module
========================================

Usage:
------
Run response time tests and generate Allure report:
    pytest tests/performance/test_response_times.py -v --alluredir=allure-results
    allure serve allure-results

Run specific response time test:
    pytest tests/performance/test_response_times.py::test_response_time_statistics -v --alluredir=allure-results

Generate one-page HTML report:
    allure generate allure-results -o allure-report --clean
    open allure-report/index.html

Run with performance marker only:
    pytest tests/performance/test_response_times.py -m performance -v --alluredir=allure-results

Run slow tests only:
    pytest tests/performance/test_response_times.py -m slow -v --alluredir=allure-results

Response Time Thresholds (Based on Measurements):
--------------------------------------------------
Good Response Time (PASS):   ≤ 1.0s
Acceptable Response Time:    1.0s - 2.0s
Slow Response Time (WARN):   2.0s - 5.0s
Critical/Timeout:            > 5.0s (FAIL)

Per Endpoint:
/api/test/1: Good response time (~0.3-0.5s) - threshold 1.0s
/api/test/3: Needs warmup - threshold 2.0s (after warmup)
/api/test/4: Slow endpoint - threshold 3.5s
/api/test/5: Moderate response time (~4.2s) - threshold 5.0s
/api/test/6: Good response time (~0.3-0.5s) - threshold 1.0s
"""

import statistics
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
)
from config.logger_config import get_test_logger

logger = get_test_logger()


# Response time thresholds per endpoint (in seconds)
RESPONSE_TIME_THRESHOLDS = {
    TEST_ENDPOINT_1: {
        "good": 1.0,
        "acceptable": 2.0,
        "slow": 5.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_2: {
        "good": 1.0,
        "acceptable": 2.0,
        "slow": 5.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_3: {
        "good": 2.0,
        "acceptable": 3.0,
        "slow": 5.0,
        "needs_warmup": True,
        "warmup_requests": 3,
    },
    TEST_ENDPOINT_4: {
        "good": 3.5,
        "acceptable": 4.5,
        "slow": 6.0,
        "needs_warmup": False,
    },
    TEST_ENDPOINT_5: {
        "good": 5.0,
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
@allure.story("Response Time Statistics")
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.parametrize("endpoint_path", [
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_2,
    TEST_ENDPOINT_3,
    TEST_ENDPOINT_4,
    TEST_ENDPOINT_5,
    TEST_ENDPOINT_6,
])
def test_response_time_statistics(base_url, headers, endpoint_path):
    """
    Gather response time statistics over 10 runs for each endpoint.

    Test PASSES if:
    - Average response time ≤ good threshold
    - All requests complete without timeout
    - Success rate = 100%

    Test FAILS if:
    - Average response time exceeds slow threshold
    - Any request times out
    - Request returns non-200 status

    Test WARNS if:
    - Average response time between good and acceptable threshold
    """
    endpoint = f"{base_url}{endpoint_path}"
    runs = 10
    times = []
    thresholds = RESPONSE_TIME_THRESHOLDS[endpoint_path]
    status_codes = []
    failed_requests = 0

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

    # Measure response times
    with allure.step(f"Execute {runs} sequential requests to {endpoint_path}"):
        for i in range(runs):
            try:
                start = time.time()
                resp = requests.get(endpoint, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
                elapsed = time.time() - start
                times.append(elapsed)
                status_codes.append(resp.status_code)

                _endpoint_results[endpoint_path]["status_codes"].append(resp.status_code)
                _endpoint_results[endpoint_path]["response_times"].append(elapsed)
                _endpoint_results[endpoint_path]["test_count"] += 1

                if resp.status_code == 200:
                    _endpoint_results[endpoint_path]["passed"] += 1
                else:
                    _endpoint_results[endpoint_path]["failed"] += 1
                    failed_requests += 1

                logger.info(f"Request {i+1}/{runs}: {elapsed:.3f}s - Status {resp.status_code}")

            except requests.Timeout as e:
                elapsed = time.time() - start
                _endpoint_results[endpoint_path]["test_count"] += 1
                _endpoint_results[endpoint_path]["failed"] += 1
                failed_requests += 1
                logger.error(f"Request {i+1}/{runs} timed out after {REQUEST_TIMEOUT}s for {endpoint_path}")
                pytest.fail(f"Request {i+1}/{runs} to {endpoint_path} timed out after {REQUEST_TIMEOUT}s")

            except requests.RequestException as e:
                elapsed = time.time() - start
                _endpoint_results[endpoint_path]["test_count"] += 1
                _endpoint_results[endpoint_path]["failed"] += 1
                failed_requests += 1
                logger.error(f"Request {i+1}/{runs} failed for {endpoint_path}: {e}")
                pytest.fail(f"Request {i+1}/{runs} to {endpoint_path} failed: {e}")

            time.sleep(0.1)

    # Calculate statistics
    avg = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    stddev = statistics.stdev(times) if len(times) > 1 else 0.0
    success_rate = (runs - failed_requests) / runs if runs > 0 else 0.0

    # Attach detailed statistics to Allure report
    with allure.step("Response Time Analysis"):
        stats_report = (
            f"Endpoint: {endpoint_path}\n"
            f"Total Requests: {runs}\n"
            f"Successful: {runs - failed_requests}\n"
            f"Failed: {failed_requests}\n"
            f"Success Rate: {success_rate*100:.1f}%\n\n"
            f"Response Times:\n"
            f"  Average: {avg:.3f}s\n"
            f"  Median: {median_time:.3f}s\n"
            f"  Min: {min_time:.3f}s\n"
            f"  Max: {max_time:.3f}s\n"
            f"  Std Dev: {stddev:.3f}s\n\n"
            f"Thresholds:\n"
            f"  Good: {thresholds['good']}s\n"
            f"  Acceptable: {thresholds['acceptable']}s\n"
            f"  Slow: {thresholds['slow']}s\n"
        )
        allure.attach(stats_report, name=f"{endpoint_path}_statistics", attachment_type=allure.attachment_type.TEXT)

    logger.info(
        f"Response times for {endpoint_path} (n={runs}): "
        f"avg={avg:.3f}s, median={median_time:.3f}s, "
        f"min={min_time:.3f}s, max={max_time:.3f}s, stddev={stddev:.3f}s"
    )

    # Fail fast if success rate is not 100%
    with allure.step("Validate success rate"):
        if success_rate < 1.0:
            pytest.fail(f"Success rate {success_rate*100:.1f}% for {endpoint_path} - some requests failed")

    # Fail if average exceeds slow threshold
    with allure.step("Validate response time does not exceed slow threshold"):
        if avg > thresholds["slow"]:
            pytest.fail(
                f"Average response time {avg:.3f}s exceeds critical threshold "
                f"{thresholds['slow']}s for {endpoint_path}"
            )

    # Warn if average is acceptable but not good
    with allure.step("Validate response time quality"):
        if avg > thresholds["good"]:
            allure.attach(
                f"⚠️ Average response time {avg:.3f}s is above good threshold {thresholds['good']}s",
                name=f"{endpoint_path}_response_time_warning",
                attachment_type=allure.attachment_type.TEXT
            )
            logger.warning(
                f"⚠️ {endpoint_path} average response time {avg:.3f}s "
                f"above good threshold {thresholds['good']}s"
            )
        else:
            allure.attach(
                f"✅ Average response time {avg:.3f}s is GOOD (good: {thresholds['good']}s)",
                name=f"{endpoint_path}_response_time_pass",
                attachment_type=allure.attachment_type.TEXT
            )
            logger.info(f"✅ {endpoint_path} average response time {avg:.3f}s is GOOD")

    # Assert basic requirements
    assert avg > 0, f"Average response time must be greater than 0 for {endpoint_path}"
    assert all(t < REQUEST_TIMEOUT for t in times), \
        f"All response times must be under REQUEST_TIMEOUT ({REQUEST_TIMEOUT}s) for {endpoint_path}"
    assert len(times) == runs, f"Expected {runs} measurements for {endpoint_path}, got {len(times)}"
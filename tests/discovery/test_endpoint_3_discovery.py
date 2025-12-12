import allure
import pytest
import requests
import statistics
import time
from datetime import datetime
from conftest import SSL_VERIFY, _endpoint_results
from constants import (
    HTTP_OK,
    HTTP_INTERNAL_ERROR,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_TOO_MANY_REQUESTS,
    TEST_ENDPOINT_1,
    TEST_ENDPOINT_3,
    REQUEST_TIMEOUT
)
from config.logger_config import get_test_logger

logger = get_test_logger()

# Suppress SSL warnings when using Charles
if not SSL_VERIFY:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@allure.feature("API Test Endpoints")
@allure.story("Endpoint 3 Investigation")
class TestEndpoint3Discovery:

    @allure.title("Test endpoint 2 basic get: {description}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.skip(reason="Not required for EP3 investigation")
    def test_endpoint_basic_get(self, base_url, headers, endpoint_path):
        """Test basic GET request"""
        endpoint = f"{base_url}{endpoint_path}"
        logger.info(f"Testing basic GET request to {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"Status: {response.status_code}, Response time: {response.elapsed.total_seconds():.3f}s")

        # Record results
        _endpoint_results[endpoint_path]["status_codes"].append(response.status_code)
        _endpoint_results[endpoint_path]["response_times"].append(response.elapsed.total_seconds())
        _endpoint_results[endpoint_path]["test_count"] += 1

        # Document the failure
        assert response.status_code == HTTP_INTERNAL_ERROR, \
            f"Expected 429, got {response.status_code}"

        # Verify error structure
        error_body = response.json()
        assert "message" in error_body, "Error response missing 'message' field"
        assert "status" in error_body, "Error response missing 'status' field"
        assert error_body["status"] == "error", f"Expected status='error', got '{error_body['status']}'"
        assert "timestamp" in error_body, "Error response missing 'timestamp' field"

        logger.info(f"Error response: {error_body}")


    @allure.title("Test endpoint 3 dependency on endpoint 1")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.skip(reason="EP3 works independently")
    def test_endpoint_3_requires_endpoint_1_warmup(self, base_url, headers):
        """Test if endpoint 3 requires endpoint 1 to be called first"""
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 dependency on EP1 ===")

        # Test 1: Call EP3 directly (should fail with 503)
        logger.info("\nTest 1: Calling EP3 without EP1 warmup...")
        response_direct = requests.get(
            endpoint_3,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )

        logger.info(f"EP3 direct call: Status {response_direct.status_code}")
        assert response_direct.status_code == HTTP_SERVICE_UNAVAILABLE, \
            f"Expected 503 for cold EP3, got {response_direct.status_code}"

        # Test 2: Call EP1, then immediately call EP3 (should succeed)
        logger.info("\nTest 2: Calling EP1 then EP3 immediately...")

        ep1_response = requests.get(
            endpoint_1,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        logger.info(f"EP1 warmup call: Status {ep1_response.status_code}")
        assert ep1_response.status_code == HTTP_OK, \
            f"EP1 warmup failed: {ep1_response.status_code}"

        ep3_response = requests.get(
            endpoint_3,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        logger.info(f"EP3 after EP1: Status {ep3_response.status_code}")
        assert ep3_response.status_code == HTTP_OK, \
            f"EP3 should work after EP1, got {ep3_response.status_code}"

        logger.info("✓ Confirmed: EP3 requires EP1 to be called first")

        allure.attach(
            "EP3 depends on EP1 for initialization/warmup",
            name="Dependency Analysis",
            attachment_type=allure.attachment_type.TEXT
        )


    @allure.title("Test endpoint 3 warmup timeout period")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_3_warmup_timeout(self, base_url, headers):
        """Test how long EP3 stays warm after EP1 call"""
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 warmup timeout ===")

        # Warmup EP1
        logger.info("Step 1: Warming up EP1...")
        ep1_response = requests.get(
            endpoint_1,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        assert ep1_response.status_code == HTTP_OK
        logger.info(f"✓ EP1 warmed up at {datetime.now().strftime('%H:%M:%S')}")

        # Test different delay intervals
        timeout_periods = [5, 10, 30, 60, 120]  # seconds
        warmup_timeout = None

        for wait_time in timeout_periods:
            logger.info(f"\nStep 2: Waiting {wait_time}s before calling EP3...")
            time.sleep(wait_time)

            elapsed_time = wait_time
            response = requests.get(
                endpoint_3,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            logger.info(f"After {elapsed_time}s: EP3 status {response.status_code}")

            if response.status_code == HTTP_SERVICE_UNAVAILABLE:
                warmup_timeout = elapsed_time
                logger.info(f"✓ Warmup expired between {timeout_periods[timeout_periods.index(wait_time)-1]}s and {wait_time}s")
                break
            elif response.status_code == HTTP_OK:
                logger.info(f"✓ Still warm after {elapsed_time}s")
                # Re-warmup for next iteration
                requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY, timeout=REQUEST_TIMEOUT)
            else:
                logger.warning(f"⚠ Unexpected status: {response.status_code}")

        if warmup_timeout:
            logger.info(f"\n📊 Warmup timeout: between {timeout_periods[timeout_periods.index(warmup_timeout)-1]}s and {warmup_timeout}s")
        else:
            logger.info(f"\n📊 Warmup persists for at least {timeout_periods[-1]}s")

        allure.attach(
            f"Warmup timeout period: {warmup_timeout}s" if warmup_timeout else f"Persists >{timeout_periods[-1]}s",
            name="Warmup Timeout Analysis",
            attachment_type=allure.attachment_type.TEXT
        )


    @allure.title("Test endpoint 3 rate limiting after warmup")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.skip(reason="Long test not needed currently")
    def test_endpoint_3_rate_limit_behavior(self, base_url, headers):
        """Test if EP3 has rate limiting after successful warmup"""
        time.sleep(40)
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 rate limiting ===")

        # Step 1: Warmup via EP1
        logger.info("Step 1: Warming up via EP1...")
        ep1_response = requests.get(
            endpoint_1,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        assert ep1_response.status_code == HTTP_OK
        logger.info("✓ EP1 warmup successful")

        # Step 2: Make multiple requests to EP3
        logger.info("\nStep 2: Sending multiple requests to EP3...")
        status_codes = []
        successful_requests = 0

        for i in range(1, 21):
            response = requests.get(
                endpoint_3,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            status_codes.append(response.status_code)

            logger.info(f"Request {i}: Status {response.status_code}")

            if response.status_code == HTTP_OK:
                successful_requests += 1
            elif response.status_code == HTTP_TOO_MANY_REQUESTS:
                logger.info(f"✓ Rate limit hit after {successful_requests} successful requests")

                # Log all headers
                logger.info("Response headers:")
                for header_name, header_value in response.headers.items():
                    logger.info(f"  {header_name}: {header_value}")
                break
            elif response.status_code == HTTP_SERVICE_UNAVAILABLE:
                logger.info(f"⚠ EP3 went cold after {successful_requests} requests (warmup expired?)")
                break

            time.sleep(0.1)

        logger.info(f"\n Summary: {successful_requests} successful requests before failure")
        logger.info(f"Status codes: {status_codes}")

        allure.attach(
            f"Successful requests before rate limit: {successful_requests}\nStatus progression: {status_codes}",
            name="Rate Limit Analysis",
            attachment_type=allure.attachment_type.TEXT
        )


    @allure.title("Test EP3 rate limit = 14 requests")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_3_rate_limit_exact_count(self, base_url, headers):
        """Verify rate limit triggers after exactly 14 requests"""
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        # Warmup
        requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)
        time.sleep(10)  # Wait for backend boot

        # Test exact rate limit
        logger.info("Testing exact rate limit count...")
        success_count = 0

        for i in range(1, 21):
            response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            logger.info(f"Request {i}: {response.status_code}")

            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 503:
                logger.info(f"Rate limit triggered at request {i}")
                break

            time.sleep(1)

        logger.info(f"Successful requests before rate limit: {success_count}")
        assert success_count == 14, f"Expected 14 successful requests, got {success_count}"

    @allure.title("Test endpoint 3 multiple warmup cycles")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_3_warmup_cycles(self, base_url, headers):
        """Test if EP3 behavior is consistent across multiple warmup cycles"""
        time.sleep(40)
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 warmup cycle consistency ===")

        cycle_results = []

        for cycle in range(1, 4):
            logger.info(f"\n--- Cycle {cycle} ---")

            # Warmup
            logger.info("Warming up via EP1...")
            ep1_response = requests.get(
                endpoint_1,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )
            assert ep1_response.status_code == HTTP_OK

            # Test EP3 immediately
            ep3_response = requests.get(
                endpoint_3,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            cycle_results.append({
                'cycle': cycle,
                'ep3_status': ep3_response.status_code,
                'ep3_time': ep3_response.elapsed.total_seconds()
            })

            logger.info(f"Cycle {cycle}: EP3 status {ep3_response.status_code}, "
                       f"time {ep3_response.elapsed.total_seconds():.3f}s")

            # Wait before next cycle
            time.sleep(10)

        # Analyze consistency
        all_successful = all(r['ep3_status'] == HTTP_OK for r in cycle_results)
        avg_time = statistics.mean([r['ep3_time'] for r in cycle_results])

        logger.info(f"\n Results across {len(cycle_results)} cycles:")
        logger.info(f"All successful: {all_successful}")
        logger.info(f"Average response time: {avg_time:.3f}s")

        assert all_successful, "EP3 behavior inconsistent across warmup cycles"

        allure.attach(
            f"Cycles tested: {len(cycle_results)}\nAll successful: {all_successful}\nAvg time: {avg_time:.3f}s",
            name="Consistency Analysis",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Test endpoint 3 recovery during sustained load")
    @allure.severity(allure.severity_level.NORMAL)
    def test_endpoint_3_recovery_pattern(self, base_url, headers):
        """
        Test if EP3 recovers after failure during sustained load with increasing delays
        This test will:
        Warmup EP1 first
        Send 50 requests to EP3 with increasing delays:
        Request 1: 0ms delay
        Request 2: 100ms delay
        Request 3: 150ms delay
        ...
        Request 50: 2.55s delay
        Track:
        When first failure occurs
        If/when recovery happens
        Recovery stability (does it stay recovered?)
        Analyze:
        Success/failure patterns
        Recovery thresholds
        Whether increasing delays help
        """
        time.sleep(40)
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 recovery pattern ===")

        # Step 1: Warmup via EP1
        logger.info("Step 1: Warming up via EP1...")
        ep1_response = requests.get(
            endpoint_1,
            headers=headers,
            verify=SSL_VERIFY,
            timeout=REQUEST_TIMEOUT
        )
        assert ep1_response.status_code == HTTP_OK
        logger.info(f"✓ EP1 warmup successful at {datetime.now().strftime('%H:%M:%S')}")

        # Step 2: Send 50 requests with increasing delays
        logger.info("\nStep 2: Sending 50 requests to EP3 with increasing delays...")

        results = []
        initial_delay = 0.1  # Start with 100ms
        delay_increment = 0.05  # Increase by 50ms each request
        current_delay = initial_delay

        first_failure = None
        recovery_point = None
        consecutive_successes = 0

        for i in range(1, 51):
            # Wait before request
            if i > 1:
                time.sleep(current_delay)

            # Make request
            start_time = datetime.now()
            response = requests.get(
                endpoint_3,
                headers=headers,
                verify=SSL_VERIFY,
                timeout=REQUEST_TIMEOUT
            )

            result = {
                'request_num': i,
                'status_code': response.status_code,
                'delay_before': current_delay if i > 1 else 0,
                'timestamp': start_time.strftime('%H:%M:%S.%f')[:-3],
                'response_time': response.elapsed.total_seconds()
            }
            results.append(result)

            # Track first failure
            if response.status_code != HTTP_OK and first_failure is None:
                first_failure = i
                logger.info(f"⚠ First failure at request {i} (delay: {current_delay:.3f}s)")

                # Log failure headers
                logger.info("Failure response headers:")
                for header_name, header_value in response.headers.items():
                    logger.info(f"  {header_name}: {header_value}")

            # Track recovery
            if first_failure is not None and response.status_code == HTTP_OK:
                consecutive_successes += 1
                if consecutive_successes == 1:
                    recovery_point = i
                    logger.info(f"✓ First recovery at request {i} (delay: {current_delay:.3f}s)")
            elif response.status_code != HTTP_OK:
                consecutive_successes = 0

            # Log progress every 5 requests
            if i % 5 == 0:
                logger.info(f"Progress: {i}/50 requests | "
                           f"Current status: {response.status_code} | "
                           f"Delay: {current_delay:.3f}s")

            # Increase delay for next iteration
            current_delay += delay_increment

        # Analysis
        logger.info("\n" + "="*60)
        logger.info("📊 ANALYSIS RESULTS")
        logger.info("="*60)

        # Calculate statistics
        status_codes = [r['status_code'] for r in results]
        successful_count = status_codes.count(HTTP_OK)
        failed_count = len(status_codes) - successful_count

        logger.info(f"\nOverall Statistics:")
        logger.info(f"  Total requests: {len(results)}")
        logger.info(f"  Successful (200): {successful_count}")
        logger.info(f"  Failed (non-200): {failed_count}")
        logger.info(f"  Success rate: {(successful_count/len(results)*100):.1f}%")

        if first_failure:
            logger.info(f"\nFailure Pattern:")
            logger.info(f"  First failure at request: {first_failure}")
            logger.info(f"  Delay when first failed: {results[first_failure-1]['delay_before']:.3f}s")

            if recovery_point:
                logger.info(f"\nRecovery Pattern:")
                logger.info(f"  First recovery at request: {recovery_point}")
                logger.info(f"  Delay when recovered: {results[recovery_point-1]['delay_before']:.3f}s")
                logger.info(f"  Time between first failure and recovery: "
                           f"{(recovery_point - first_failure) * 0.1:.1f}s (approx)")

                # Check if recovery is stable
                post_recovery_results = results[recovery_point-1:]
                post_recovery_success = sum(1 for r in post_recovery_results if r['status_code'] == HTTP_OK)
                recovery_stability = (post_recovery_success / len(post_recovery_results)) * 100

                logger.info(f"  Recovery stability: {recovery_stability:.1f}% success rate after recovery")
            else:
                logger.info(f"\n❌ No recovery observed during test")
        else:
            logger.info(f"\n✓ No failures detected - EP3 remained stable throughout")

        # Status code progression
        logger.info(f"\nStatus Code Progression (every 10th request):")
        for i in range(0, len(results), 10):
            r = results[i]
            logger.info(f"  Request {r['request_num']:2d}: {r['status_code']} "
                       f"(delay: {r['delay_before']:.3f}s)")

        # Detailed results table
        detailed_results = "\n".join([
            f"Request {r['request_num']:2d} | "
            f"Status: {r['status_code']} | "
            f"Delay: {r['delay_before']:.3f}s | "
            f"Time: {r['timestamp']} | "
            f"Response: {r['response_time']:.3f}s"
            for r in results
        ])

        allure.attach(
            f"Total: {len(results)} requests\n"
            f"Success: {successful_count} ({(successful_count/len(results)*100):.1f}%)\n"
            f"Failed: {failed_count}\n"
            f"First failure: Request {first_failure if first_failure else 'None'}\n"
            f"Recovery: Request {recovery_point if recovery_point else 'None'}\n"
            f"\n{detailed_results}",
            name="Recovery Pattern Analysis",
            attachment_type=allure.attachment_type.TEXT
        )

        # Assertions for documentation
        if first_failure and recovery_point:
            logger.info(f"\n✓ EP3 shows recovery behavior:")
            logger.info(f"  - Fails after {first_failure} requests")
            logger.info(f"  - Recovers with {results[recovery_point-1]['delay_before']:.3f}s delay")
        elif first_failure and not recovery_point:
            logger.info(f"\n⚠ EP3 fails and does NOT recover with increasing delays")
        else:
            logger.info(f"\n✓ EP3 remains stable throughout test (no rate limit observed)")

    @allure.title("Test EP3 recovery with EP1 re-warmup")
    def test_endpoint_3_recovery_with_ep1_rewarm(self, base_url, headers):
        """Test if calling EP1 during EP3 failures recovers it"""
        time.sleep(40)
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP3 recovery with EP1 intervention ===")

        # Initial warmup
        requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)
        logger.info("✓ Initial EP1 warmup")

        results = []

        for i in range(1, 31):
            time.sleep(0.5)  # Fast requests to trigger failure
            response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)

            results.append({
                'request': i,
                'status': response.status_code,
                'action': 'normal'
            })

            logger.info(f"Request {i}: {response.status_code}")

            # When we hit failure, try EP1 warmup
            if response.status_code == 503 and i == 16:
                logger.info("⚠ Failure detected - Re-warming via EP1...")
                requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)

                # Retry EP3 immediately
                retry_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
                results.append({
                    'request': f"{i}-retry",
                    'status': retry_response.status_code,
                    'action': 'after_ep1_rewarm'
                })
                logger.info(f"After EP1 re-warm: {retry_response.status_code}")

        # Analysis
        logger.info("\n=== RESULTS ===")
        for r in results:
            logger.info(f"Request {r['request']}: {r['status']} ({r['action']})")

        allure.attach(
            "\n".join([f"{r['request']}: {r['status']} - {r['action']}" for r in results]),
            name="EP1 Re-warmup Test",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Test EP1 async warmup delay")
    def test_endpoint_1_async_warmup_timing(self, base_url, headers):
        """Test if EP1 warmup has async startup delay"""
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== Testing EP1 async warmup timing ===")

        # Let EP3 go completely cold
        logger.info("Waiting 40s for EP3 to go cold...")
        time.sleep(40)

        # Confirm cold state
        cold_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        logger.info(f"Cold check: {cold_response.status_code}")
        assert cold_response.status_code == 503, "EP3 should be cold"

        # Call EP1 and immediately test EP3 every second
        logger.info("\nCalling EP1 to trigger warmup...")
        ep1_time = datetime.now()
        requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)

        results = []
        for i in range(15):  # Test for 15 seconds
            time.sleep(1)
            elapsed = i + 1

            response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            results.append({
                'seconds_after_ep1': elapsed,
                'status': response.status_code,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })

            status_emoji = "✓" if response.status_code == 200 else "✗"
            logger.info(f"{status_emoji} T+{elapsed}s: EP3 = {response.status_code}")

            # Stop when recovered
            if response.status_code == 200:
                logger.info(f"\n🎯 EP3 recovered {elapsed} seconds after EP1 call")
                break

        # Analysis
        logger.info("\n=== TIMING ANALYSIS ===")
        recovery_time = next((r['seconds_after_ep1'] for r in results if r['status'] == 200), None)

        if recovery_time:
            logger.info(f"✓ Backend startup time: {recovery_time} seconds")
            logger.info(f"EP1 called at: {ep1_time.strftime('%H:%M:%S.%f')[:-3]}")
            logger.info(f"EP3 ready at: {results[recovery_time-1]['timestamp']}")
        else:
            logger.info("✗ EP3 did not recover within 15 seconds")

        allure.attach(
            "\n".join([f"T+{r['seconds_after_ep1']}s: {r['status']} at {r['timestamp']}" for r in results]),
            name="EP1 Async Warmup Timing",
            attachment_type=allure.attachment_type.TEXT
        )

        # Verify 9-second startup hypothesis
        assert recovery_time is not None, "EP3 should recover after EP1"
        assert 7 <= recovery_time <= 11, f"Expected ~9s startup, got {recovery_time}s"


    @allure.title("Test EP3 cold start vs rate limit recovery")
    def test_endpoint_3_cold_vs_cooldown(self, base_url, headers):
        """
        Test difference between cold start and rate limit recovery
        Cold start <1 second EP1 initializes shared session
        Rate limit recovery~9 seconds Circuit breaker cooldown
        """

        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        logger.info("=== TEST 1: Cold Start Timing ===")

        # Wait for complete cold state
        logger.info("Waiting 60s for complete cold state...")
        time.sleep(60)

        # Confirm cold
        cold_check = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        logger.info(f"Cold check: {cold_check.status_code}")
        assert cold_check.status_code == 503

        # Call EP1 and immediately check EP3
        logger.info("\nCalling EP1...")
        ep1_start = datetime.now()
        requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)

        logger.info("Immediately calling EP3...")
        ep3_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        ep3_delay = (datetime.now() - ep1_start).total_seconds()

        logger.info(f"✓ EP3 responded in {ep3_delay:.3f}s: {ep3_response.status_code}")

        # EXPECTED: 200 response in <1 second (instant warmup)
        assert ep3_response.status_code == 200, "EP3 should work instantly after cold EP1"
        assert ep3_delay < 2, f"Expected instant warmup, took {ep3_delay:.3f}s"

        logger.info("\n=== TEST 2: Rate Limit Recovery Timing ===")

        # Trigger rate limit
        logger.info("Triggering rate limit...")
        for i in range(15):
            requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            time.sleep(0.5)

        # Confirm rate limited
        limited_check = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        logger.info(f"Rate limit check: {limited_check.status_code}")
        assert limited_check.status_code == 503, "Should be rate limited"

        # Try EP1 re-warmup (this should NOT work immediately)
        logger.info("\nTrying EP1 re-warmup...")
        requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)

        logger.info("Immediately calling EP3...")
        retry_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        logger.info(f"After EP1: {retry_response.status_code}")

        # EXPECTED: Still 503 (circuit breaker still open)
        assert retry_response.status_code == 503, "EP1 should NOT clear rate limit"

        # Wait for cooldown
        logger.info("\nWaiting for cooldown recovery...")
        recovery_time = None

        for i in range(1, 16):
            time.sleep(1)
            test_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            logger.info(f"T+{i}s: {test_response.status_code}")

            if test_response.status_code == 200:
                recovery_time = i
                logger.info(f"✓ Recovered after {i} seconds")
                break

        # EXPECTED: ~9 seconds recovery time
        assert recovery_time is not None, "Should recover eventually"
        assert 7 <= recovery_time <= 11, f"Expected ~9s cooldown, got {recovery_time}s"

        # Summary
        logger.info("\n=== SUMMARY ===")
        logger.info(f"Cold start: {ep3_delay:.3f}s (instant)")
        logger.info(f"Rate limit recovery: {recovery_time}s (cooldown)")

        allure.attach(
            f"Cold start delay: {ep3_delay:.3f}s\n"
            f"Rate limit cooldown: {recovery_time}s\n"
            f"\nConclusion:\n"
            f"- EP1 creates session → EP3 works instantly\n"
            f"- Rate limit triggers → 9s cooldown required\n"
            f"- EP1 does NOT reset rate limit",
            name="Cold Start vs Rate Limit Analysis",
            attachment_type=allure.attachment_type.TEXT
        )

    @allure.title("Test EP1 response time during cold start")
    def test_endpoint_3_cold_start_timing(self, base_url, headers):
        """Test EP1's response time when cold vs warm"""
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        # Test 1: Cold start timing
        logger.info("\n--- Cold Start Test ---")
        logger.info("Waiting 60s for complete cold state...")
        time.sleep(60)
        logger.info("Calling EP3 directly (no EP1)...")
        ep3_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
        logger.info(f"EP3: {ep3_response.status_code}")
        assert response.status_code == 200, "EP3 should work after cold period"

        logger.info(f"EP3 : {ep3_response.status_code}")
        assert ep3_response.status_code == 200, "EP3 should work after EP1 cold start"


    @allure.title("Test EP1 does NOT reset rate limit")
    def test_endpoint_1_cannot_reset_rate_limit(self, base_url, headers):
        """Verify EP1 has no effect on active rate limit"""
        endpoint_1 = f"{base_url}{TEST_ENDPOINT_1}"
        endpoint_3 = f"{base_url}{TEST_ENDPOINT_3}"

        # Trigger rate limit
        logger.info("Triggering rate limit...")
        for i in range(15):
            requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)
            time.sleep(1)

        # Try EP1 reset
        logger.info("Attempting EP1 reset...")
        ep1_response = requests.get(endpoint_1, headers=headers, verify=SSL_VERIFY)
        assert ep1_response.status_code == 200

        # EP3 should still be rate-limited
        ep3_response = requests.get(endpoint_3, headers=headers, verify=SSL_VERIFY)

        assert ep3_response.status_code == 503, "EP1 should NOT reset rate limit"
        logger.info("✓ Confirmed: EP1 cannot reset rate limit")



#
#
# # Wait 60+ seconds first
# sleep 60
#
# # Test 1: Cold vs cooldown behavior
# pytest tests/discovery/test_endpoint_3_discovery.py::TestEndpoint3Discovery::test_endpoint_3_cold_vs_cooldown -v
#
# # Wait 40 seconds
# sleep 40
#
# # Test 2: EP1 timing analysis
# pytest tests/discovery/test_endpoint_3_discovery.py::TestEndpoint3Discovery::test_endpoint_1_cold_start_timing -v

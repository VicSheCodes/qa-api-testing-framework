# API Resilience Testing - Comprehensive Test Plan

**Project:** QA Home Assignment - API Resilience Testing  
**Candidate:** Victoria Gur  
**Date:** December 2025  
**Environment:** `https://qa-home-assignment.magmadevs.com`  
**Framework:** Python 3.12 + pytest + locust + Allure

---

## 1. Executive Summary

This test plan provides comprehensive coverage for a 6-endpoint REST API system with focus on:
- **Functional Testing**: Endpoint behavior validation
- **Security Testing**: Authentication and authorization
- **Performance Testing**: Latency, throughput, concurrent load
- **Reliability Testing**: Error handling, retry logic, timeout behavior
- **Load Testing**: Backend capacity and rate limiting
- **Schema Testing**: Response structure validation
- **Regression Testing**: Critical path stability
- **Negative Testing**: Error scenarios and edge cases

**Key Testing Dimensions:**
- 6 REST API endpoints (`/api/test/1` through `/api/test/6`)
- JWT Bearer token authentication (15-minute expiry)
- Two-layer rate limiting (application + backend capacity)
- Backend cold start behavior (8-second warmup required)
- Variable response times (0.18s to 4.3s across endpoints)

---

## 2. Test Scope & Coverage

### 2.1 In Scope
- ✅ All 6 test endpoints (`/api/test/1` - `/api/test/6`)
- ✅ Authentication and token lifecycle
- ✅ Rate limiting boundaries and recovery
- ✅ Performance characteristics (latency, throughput)
- ✅ Backend cold start and warmup behavior
- ✅ Error handling and resilience
- ✅ Security vulnerabilities (auth bypass, token reuse)
- ✅ Concurrent request handling
- ✅ Response schema compliance
- ✅ Known anomalies and edge cases

### 2.2 Out of Scope
- ❌ Load testing beyond 50 concurrent users
- ❌ Database-level testing
- ❌ Infrastructure changes
- ❌ API redesign or code changes
- ❌ Documentation updates (outside this plan)

---

## 3. Test Strategy & Approach

### 3.1 Discovery-Based Testing
- **Phase 1**: Manual endpoint exploration (completed)
- **Phase 2**: Behavioral pattern identification (completed)
- **Phase 3**: Automated test case development (development)
- **Phase 4**: Full regression suite execution (developmnet)

### 3.2 Testing Pyramid

```
┌─────────────────────────────────┐
│  End-to-End Tests (5%)          │  Scenario testing, integration
├─────────────────────────────────┤
│  Integration Tests (20%)        │  Multiple endpoints, workflows
├─────────────────────────────────┤
│  API Tests (40%)                │  Individual endpoint behavior
├─────────────────────────────────┤
│  Unit & Component Tests (35%)   │  Helper functions, utilities
└─────────────────────────────────┘
```

### 3.3 Testing Types by Category

| Category | Purpose | Tools | Priority |
|----------|---------|-------|----------|
| **Functional** | Endpoint behavior validation | pytest, requests | Critical |
| **Security** | Auth, token lifecycle, SQL injection | pytest, custom payloads | Critical |
| **Performance** | Latency, throughput, concurrency | locust, time module | High |
| **Reliability** | Error handling, retry, timeout | pytest, unittest | High |
| **Load** | Rate limits, backend capacity | locust, custom load generator | High |
| **Schema** | Response structure compliance | jsonschema, pydantic | Medium |
| **Regression** | Critical path stability | pytest markers | High |
| **Negative** | Error scenarios, edge cases | pytest, custom payloads | Medium |


### 3.4 Key Considerations

✅ EP1 = Warmup trigger (health check that wakes backend)
✅ EP3 = Capacity test (needs the 8s warmup via EP1 first)
✅ EP4 = Rate limit test (independent, no warmup needed)
✅ EP5 = Timeout test (intentional 4.3s delay)
✅ EP6 = Baseline reference (fast, reliable)


# Based on discovery, each endpoint has unique behavior:

### EP1 — Health Check / Backend Warmup
- **Purpose:** Trigger 8-second asynchronous backend initialization.
- **Behavior:** Always `200 OK`, ~0.18s latency.
- **Strategy:** Call before testing EP3; no rate limit. Use a single warmup call and wait 8s before EP3 tests.

### EP2 — Intentional Failure Simulation
- **Purpose:** Validate client error handling and resilience.
- **Behavior:** Always returns `429` or `500` (non-recoverable).
- **Strategy:** Use for negative tests only; assert expected failures and error schema.

### EP3 — Backend Capacity Testing
- **Purpose:** Test overload and capacity boundaries.
- **Behavior:** `200 OK` for requests 1–14, then `503` for request 15+.
- **Strategy:** Warmup via EP1 first, validate boundary at 14/15, verify cooldown (10–13s) before retrying.

### EP4 — Strict Client Rate Limiting
- **Purpose:** Test application-level quota enforcement.
- **Behavior:** `200 OK` for requests 1–4, then `429` for request 5+.
- **Strategy:** Test exact boundary at 4 requests, verify isolation from EP3 rate limits.

### EP5 — Timeout / Retry Testing
- **Purpose:** Verify slow-response handling and retry logic.
- **Behavior:** Always `200 OK` after a fixed ~4.3s delay.
- **Strategy:** Use client timeout >5s, validate retry/backoff behavior; no rate limit.

### EP6 — Baseline Reference Endpoint
- **Purpose:** Positive control for regression and performance baselines.
- **Behavior:** Always `200 OK`, ~0.21s latency, returns structured data.
- **Strategy:** Use for regression checks and baseline metrics; no special handling required.

---

## 4. Test Organization & Structure

### 4.1 Directory Structure
```bash
find tests/ -name "*.py" -type f 
```

```
tests/
├── __init__.py
├── conftest.py                          # pytest fixtures & configuration
│
├── functional/                          # Core functionality tests
│   ├── __init__.py
│   ├── test_health_check.py             # EP1 basic validation
│   └── test_core_functional.py          # EP3, EP4, EP5, EP6 basic tests
│
├── discovery/                           # Behavioral pattern discovery
│   ├── __init__.py
│   ├── test_endpoint_1_discovery.py     # EP1 discovery tests
│   ├── test_endpoint_2_discovery.py     # EP2 discovery tests
│   ├── test_endpoint_3_discovery.py     # EP3 discovery (warmup, rate limit)
│   ├── test_endpoint_4_discovery.py     # EP4 discovery (strict rate limit)
│   ├── test_endpoint_5_discovery.py     # EP5 discovery (slow response)
│   ├── test_endpoint_6_discovery.py     # EP6 discovery (baseline)
│   ├── test_endpoints_first_discovery.py # Combined endpoint tests
│   └── test_endpoint_discovery.py       # Advanced discovery scenarios
│
├── security/                            # Security & authentication tests
│   ├── __init__.py
│   └── test_security_auth.py            # Token lifecycle, auth bypass
│
├── performance/                         # Performance & latency tests
│   ├── __init__.py
│   ├── test_latency.py                  # Individual endpoint latency
│   ├── test_response_times.py           # Response time statistics
│   ├── test_concurrent_requests.py      # Concurrent access patterns
│   └── test_stress.py                   # High-load stress testing
│
├── reliability/                         # Error handling & resilience
│   ├── __init__.py
│   ├── test_retry_logic.py              # Exponential backoff, retries
│   ├── test_timeout_handling.py         # Timeout configuration
│   └── test_network_issues.py           # Connection failures
│
├── load/                                # Load & rate limit testing
│   ├── __init__.py
│   ├── load_behaviour.py                # Rate limit behavior analysis
│   └── load_one_endpoint.py             # Single endpoint load testing
│
├── schema/                              # Response schema validation
│   ├── __init__.py
│   ├── test_schema_compliance.py        # JSON schema validation
│   └── test_schema_discovery.py         # Schema exploration
│
├── regression/                          # Regression test suite
│   ├── __init__.py
│   ├── test_critical_paths.py           # Critical user journeys
│   └── test_known_bugs.py               # Known issue validation
│
└── negative/                            # Negative test scenarios
    ├── __init__.py
    └── negative.py                      # Error cases, edge conditions
```

### 4.2 Test File Organization

Tests follows this structure:

```python
"""Module docstring describing test scope."""
import pytest
from constants import TEST_ENDPOINT_1, HTTP_OK
from conftest import _endpoint_results

@pytest.mark.functional
@pytest.mark.critical
def test_basic_functionality(base_url, headers):
    """Test description with expected behavior."""
    # Arrange
    endpoint = f"{base_url}{TEST_ENDPOINT_1}"
    
    # Act
    response = requests.get(endpoint, headers=headers)
    
    # Assert
    assert response.status_code == HTTP_OK
```

---

## 5. Test Cases by Category

### 5.1 Functional Tests (38 test cases)

#### 5.1.1 Endpoint 1: Health Check

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep1_basic_availability` | GET `/api/test/1` returns 200 | 200 OK | P0 |
| `test_ep1_response_structure` | Response contains required fields | `{message, status, timestamp}` | P1 |
| `test_ep1_no_rate_limit` | 20 consecutive requests all succeed | 100% success | P2 |
| `test_ep1_fast_response` | Response time <500ms | avg <500ms | P2 |
| `test_ep1_warmup_trigger` | Call triggers backend warmup | EP3 ready after wait | P0 |

#### 5.1.2 Endpoint 2: Broken Endpoint

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep2_expected_failure` | GET returns 429 or 500 | Error | P2 |
| `test_ep2_consistent_failure` | 10 requests all fail | 0% success | P1 |
| `test_ep2_http_spec_violation` | OPTIONS returns 200 (invalid) | Document anomaly | P1 |

#### 5.1.3 Endpoint 3: Backend Capacity

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep3_basic_success` | GET with warmup returns 200 | 200 OK | P0 |
| `test_ep3_response_structure` | Response contains data object | `{data, message, status}` | P1 |
| `test_ep3_rate_limit_boundary_14` | 14th request succeeds, 15th fails | 200/503 | P0 |
| `test_ep3_rate_limit_recovery` | After wait, requests succeed again | 200 OK | P0 |
| `test_ep3_cold_start` | Cold backend returns 503 | 503 error | P1 |
| `test_ep3_warmup_required` | EP1 call fixes cold start | 200 OK | P0 |

#### 5.1.4 Endpoint 4: Application Rate Limit

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep4_basic_success` | GET with reset limit returns 200 | 200 OK | P0 |
| `test_ep4_rate_limit_boundary_4` | 4th request succeeds, 5th fails | 200/429 | P0 |
| `test_ep4_rate_limit_recovery` | After wait, requests succeed | 200 OK | P0 |
| `test_ep4_independent_from_ep3` | EP4 limit doesn't affect EP3 | Both work | P0 |

#### 5.1.5 Endpoint 5: Slow Response

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep5_basic_success` | GET returns 200 | 200 OK | P0 |
| `test_ep5_slow_response` | Latency ~4.3 seconds | 4.0s - 4.5s | P1 |
| `test_ep5_consistent_delay` | 10 requests all ~4.3s | variance <500ms | P1 |
| `test_ep5_no_rate_limit` | 20 consecutive requests | 100% success | P2 |

#### 5.1.6 Endpoint 6: Baseline Data

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_ep6_basic_success` | GET returns 200 | 200 OK | P0 |
| `test_ep6_response_structure` | Response has data with count/id/value | Proper structure | P1 |
| `test_ep6_no_rate_limit` | 20 consecutive requests | 100% success | P2 |
| `test_ep6_fast_response` | Response <500ms | avg <500ms | P2 |

### 5.2 Security Tests (12 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_auth_invalid_token` | GET with invalid token | 401 Unauthorized | P0 |
| `test_auth_missing_header` | GET without Authorization header | 401 Unauthorized | P0 |
| `test_auth_malformed_token` | GET with malformed token | 401 Unauthorized | P1 |
| `test_auth_token_refresh` | Refresh token generates new tokens | 200 OK, new tokens | P0 |
| `test_auth_single_use_token` | Refresh token can't be reused | 401/400 on reuse | P0 |
| `test_auth_token_expiry` | Expired token rejected | 401 Unauthorized | P0 |
| `test_auth_token_lifecycle` | Token valid for 15 minutes | Expires after 15m | P1 |
| `test_auth_sql_injection` | SQL injection in headers rejected | Safe response | P1 |
| `test_auth_token_format` | Bearer token format validated | 401 on invalid format | P2 |
| `test_auth_concurrent_refresh` | Multiple refreshes simultaneously | All succeed | P2 |
| `test_auth_xss_prevention` | XSS payloads handled safely | Safe response | P2 |
| `test_auth_csrf_protection` | CSRF tokens validated | Protected | P2 |

### 5.3 Performance Tests (15 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_perf_ep1_latency_baseline` | EP1 avg latency <500ms | <500ms | P1 |
| `test_perf_ep3_latency_baseline` | EP3 avg latency <500ms | <500ms | P1 |
| `test_perf_ep4_latency_baseline` | EP4 avg latency <500ms | <500ms | P1 |
| `test_perf_ep5_latency_consistency` | EP5 all requests ~4.3s | variance <500ms | P0 |
| `test_perf_ep6_latency_baseline` | EP6 avg latency <500ms | <500ms | P1 |
| `test_perf_percentile_p95` | 95th percentile latency | ep1/ep3/ep4/ep6 <1s | P2 |
| `test_perf_percentile_p99` | 99th percentile latency | ep1/ep3/ep4/ep6 <2s | P2 |
| `test_perf_cold_start_latency` | First request after idle | Slower (503) | P1 |
| `test_perf_throughput_baseline` | Requests/second capacity | Track baseline | P2 |
| `test_perf_response_size` | Response payload size | Document sizes | P2 |
| `test_perf_concurrent_5_users` | 5 concurrent users | <2s p95 latency | P2 |
| `test_perf_concurrent_10_users` | 10 concurrent users | <3s p95 latency | P2 |
| `test_perf_concurrent_20_users` | 20 concurrent users | <5s p95 latency | P3 |
| `test_perf_sustained_load_300s` | 300-second sustained load | No degradation | P3 |
| `test_perf_spike_load` | Sudden load spike | Graceful degradation | P3 |

### 5.4 Reliability Tests (10 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_reliability_timeout_default` | Default timeout behavior | Respects timeout | P1 |
| `test_reliability_timeout_ep5_short` | EP5 with 3s timeout | Timeout error | P1 |
| `test_reliability_timeout_ep5_long` | EP5 with 5s timeout | 200 OK | P1 |
| `test_reliability_connection_retry` | Retry on connection error | Succeeds after retry | P2 |
| `test_reliability_503_retry` | Retry on 503 error | Succeeds after retry | P2 |
| `test_reliability_429_retry` | Retry on 429 with wait | Succeeds after cooldown | P2 |
| `test_reliability_exponential_backoff` | Backoff increases exponentially | 1s, 2s, 4s, 8s | P2 |
| `test_reliability_network_failure_recovery` | Network error then recovery | Retries and succeeds | P3 |
| `test_reliability_partial_response` | Incomplete response handling | Error handling | P3 |
| `test_reliability_malformed_json` | Invalid JSON response | Graceful error | P2 |

### 5.5 Load & Rate Limiting Tests (12 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_load_ep3_capacity_14` | EP3 limit at exactly 14 | Request 15 fails | P0 |
| `test_load_ep3_capacity_boundary` | Test requests 1-15 | Pattern 14 ok/15 fail | P0 |
| `test_load_ep3_cooldown_timing` | Rate limit cooldown ~10-13s | Recovery in window | P0 |
| `test_load_ep4_quota_4` | EP4 limit at exactly 4 | Request 5 fails | P0 |
| `test_load_ep4_quota_boundary` | Test requests 1-5 | Pattern 4 ok/5 fail | P0 |
| `test_load_ep4_cooldown_timing` | Rate limit cooldown ~20-30s | Recovery in window | P0 |
| `test_load_ep3_ep4_isolation` | Trigger EP4 limit, EP3 works | EP3 not affected | P0 |
| `test_load_concurrent_burst_ep1` | 50 burst requests to EP1 | All succeed (no limit) | P2 |
| `test_load_concurrent_burst_ep3` | 50 burst to EP3 | Rate limit applies | P2 |
| `test_load_concurrent_burst_ep4` | 50 burst to EP4 | Strict limit applies | P2 |
| `test_load_backend_capacity_exhaustion` | Fill EP3 capacity multiple times | Consistent pattern | P2 |
| `test_load_rate_limit_headers` | Rate limit headers present | X-RateLimit-* or missing | P1 |

### 5.6 Schema Compliance Tests (8 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_schema_ep1_response_structure` | EP1 response matches schema | Valid JSON schema | P1 |
| `test_schema_ep3_response_structure` | EP3 response matches schema | Valid JSON schema | P1 |
| `test_schema_ep4_response_structure` | EP4 response matches schema | Valid JSON schema | P1 |
| `test_schema_ep5_response_structure` | EP5 response matches schema | Valid JSON schema | P1 |
| `test_schema_ep6_response_structure` | EP6 response matches schema | Valid JSON schema | P1 |
| `test_schema_error_response_format` | Error responses valid JSON | Valid JSON structure | P2 |
| `test_schema_timestamp_format` | Timestamps are ISO8601 | Matches format | P2 |
| `test_schema_status_field_values` | Status field only valid values | "success" or error | P2 |

### 5.7 Regression Tests (10 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_regression_ep1_always_available` | EP1 always 200 OK | 100% success | P0 |
| `test_regression_ep3_warmup_required` | EP3 requires EP1 warmup | 503 without warmup | P0 |
| `test_regression_ep4_strict_limit` | EP4 limit strictly 4 | Consistent | P0 |
| `test_regression_ep5_slow_always` | EP5 always ~4.3s | Consistent delay | P0 |
| `test_regression_ep6_baseline_stable` | EP6 always works, fast | 200 OK <500ms | P0 |
| `test_regression_token_refresh_works` | Token refresh succeeds | New tokens returned | P0 |
| `test_regression_auth_required` | Endpoints require auth | 401 without token | P0 |
| `test_regression_ep2_always_fails` | EP2 never succeeds | Always 429/500 | P1 |
| `test_regression_rate_limit_isolation` | EP3 and EP4 isolated | Independent limits | P0 |
| `test_regression_backend_recovery` | Backend recovers after idle | Needs warmup | P1 |

### 5.8 Negative Tests (14 test cases)

| Test ID | Description | Expected | Priority |
|---------|-------------|----------|----------|
| `test_negative_invalid_endpoint` | GET `/api/test/99` | 404 Not Found | P2 |
| `test_negative_wrong_http_method` | POST to GET-only endpoint | 405 Method Not Allowed | P2 |
| `test_negative_invalid_json_body` | POST with invalid JSON | 400 Bad Request | P2 |
| `test_negative_missing_required_field` | POST missing required field | 400 Bad Request | P2 |
| `test_negative_very_long_token` | Token >10KB | 401 or 400 | P2 |
| `test_negative_special_chars_token` | Special chars in token | 401 | P2 |
| `test_negative_null_token` | Null Authorization header | 401 | P2 |
| `test_negative_empty_token` | Empty Authorization header | 401 | P2 |
| `test_negative_sql_injection_header` | SQL injection in custom header | Safe handling | P1 |
| `test_negative_xss_payload_header` | XSS payload in header | Safe handling | P1 |
| `test_negative_extremely_large_response` | Payload >100MB | Handled safely | P3 |
| `test_negative_timeout_client_disconnect` | Client disconnects mid-response | Server handles | P3 |
| `test_negative_rapid_same_request` | 1000 identical requests/sec | Rate limit or succeed | P3 |
| `test_negative_header_injection` | Header injection attempt | Prevented | P2 |

---

## 6. Test Fixtures & Configuration

 - Key Pytest Fixtures ( `conftest.py`)
 - Pytest Configuration (`pytest.ini`)
 - Constants Definition (`constants.py`)
 
```

---

## 7. Test Execution Strategy

### 7.1 Execution Phases

#### Phase 1: Setup & Validation (5 minutes)
```bash
# Validate environment
pytest tests/ --collect-only
pytest tests/functional/test_health_check.py -v

# Verify authentication
pytest tests/security/test_security_auth.py::test_auth_token_refresh -v
```

#### Phase 2: Discovery Tests (5 minutes)
```bash
# Reporting of all endpoints
pytest tests/discovery/ -v
```

#### Phase 3: Functional Tests (30 minutes)
```bash
# Core functionality validation
pytest tests/functional/ -v

```

#### Phase 4: Security & Reliability (20 minutes)
```bash
# Auth and error handling
pytest tests/security/ -v
pytest tests/reliability/ -v
pytest tests/negative/ -v
```

#### Phase 5: Load & Performance (45 minutes)
```bash
# Rate limits and latency
pytest tests/load/ -v
pytest tests/performance/ -v --timeout=600
```

#### Phase 6: Regression & Schema (15 minutes)
```bash
# Ensure nothing broke, validate schemas
pytest tests/regression/ -v
pytest tests/schema/ -v
```

**Total Runtime:** ~2-3 hours (full suite)

### 7.2 Execution Patterns

Test execution is organized by pytest markers for flexible suite composition:

**Critical Path Tests** (`@pytest.mark.critical_path`)
- Core functionality that must pass before any other tests
- Includes: Authentication, EP1 health check, EP6 baseline
- Execution: Always run first
- Failure: Blocks all dependent tests

**Regression Tests** (`@pytest.mark.regression`)
- Verify known behaviors remain stable
- Covers: All endpoints basic functionality
- Execution: Run after critical path passes
- Frequency: Every test run

**Performance Tests** (`@pytest.mark.performance`)
- Latency profiling and benchmarking
- Covers: Baseline metrics, comparison analysis
- Execution: Separate suite (longer duration)

**Stress Tests** (`@pytest.mark.stress_light` / `@pytest.mark.stress_medium`)
- Load and concurrency validation
- Light: 10-50 concurrent requests
- Medium: 50-200 concurrent requests
- Execution: Optional, on-demand

**Security Tests** (`@pytest.mark.security`)
- Token handling, authentication, authorization
- Covers: Invalid tokens, expired tokens, missing auth
- Execution: Part of full test suite

**Schema Validation** (`@pytest.mark.schema`)
- Response structure and data type validation
- Covers: JSON schema compliance per endpoint
- Execution: Integrated with functional tests

**Negative Tests** (`@pytest.mark.negative`)
- Error handling and edge cases
- Covers: EP2 failures, invalid inputs, boundary conditions
- Execution: Full validation suite

**Core Functional** (`@pytest.mark.core_functional`)
- Essential endpoint behaviors
- Covers: Basic availability, happy path scenarios
- Execution: Always run

**Slow Tests** (`@pytest.mark.slow`)
- Tests with extended execution time (>5s)
- Covers: EP5 timeout testing, backend warmup
- Execution: Optional flag: `-m "not slow"` to skip

**Discovery Tests** (`@pytest.mark.discovery`)
- Endpoint behavior exploration and analysis
- Covers: Rate limit boundaries, response patterns
- Execution: Initial analysis, reference data

**Example Execution Commands:**

```bash
# Run critical path only (~5 minutes)
pytest -m critical_path -v

# Run critical path + regression (~20 minutes)
pytest -m "critical_path or regression" -v

# Run full suite excluding slow tests (~60 minutes)
pytest -m "not slow" -v

# Run full suite including slow tests (~90 minutes)
pytest tests/ -v

# Run only performance tests
pytest -m performance -v

# Run security + schema validation
pytest -m "security or schema" -v

# Run everything except discovery
pytest -m "not discovery" -v
```
---

## 8. Test Data Management

### 8.1 Authentication Data

| Item | Value | Scope | Notes |
|------|-------|-------|-------|
| Initial Refresh Token | `initial_refresh_token_2024_qa_evaluation` | Session | One-time bootstrap |
| Access Token | Generated | Per-test | 15-minute expiry |
| Refresh Token | Generated | Per-test | Single-use |
| Token Type | Bearer | All requests | Standard HTTP auth |

### 8.2 Request Headers

```python
headers = {
    "Authorization": "Bearer {access_token}",
    "User-Agent": "Python-QA-Test-Suite/1.0",
    "Accept": "application/json",
}
```

### 8.3 Expected Response Structures

**EP1/EP3/EP4/EP5:**
```json
{
  "message": "string",
  "status": "success",
  "timestamp": "ISO8601"
}
```

**EP6 (structured data):**
```
{
  "data": {
    "count": integer,
    "id": integer,
    "value": integer
  },
  "status": "success",
  "timestamp": "ISO8601"
}
```

---

## 9. Success Criteria & Acceptance

### 9.1 Test Pass Criteria

✅ **Critical Tests (P0):** 100% pass rate required
✅ **High Priority (P1):** ≥95% pass rate
✅ **Medium Priority (P2):** ≥90% pass rate
✅ **Low Priority (P3):** ≥85% pass rate

### 9.2 Coverage Goals

| Category | Target | Acceptance |
|----------|--------|-----------|
| Functional Coverage | 100% endpoints | All 6 tested |
| Auth Coverage | 100% scenarios | Valid/invalid/expired |
| Error Coverage | 80% scenarios | 429, 503, 401, 404, 405 |
| Performance Baselines | All endpoints | Latency documented |
| Rate Limit Boundaries | Both layers | 14 (EP3), 4 (EP4) verified |

### 9.3 Quality Gates

✅ All critical paths execute successfully  
✅ No new anomalies introduced  
✅ Rate limit boundaries confirmed  
✅ Authentication lifecycle valid  
✅ Response schemas compliant  
✅ Performance within baseline ±10%  

---

## 10. Risk Assessment & Mitigation

### 10.1 Identified Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| EP3 cold start (503) | HIGH | Always warmup  + 8s wait |
| EP4 strict limit (4 req) | HIGH | Space out test execution (30s cooldown) |
| Token expiry (15 min) | MEDIUM | Auto-refresh at 12-minute mark |
| EP5 slow response (4.3s) | MEDIUM | Set timeout >5 seconds |
| EP2 always fails | MEDIUM | Document as intentional, skip positive tests |
| Rate limit isolation confusion | MEDIUM | Clear documentation (429 vs 503) |

### 10.2 Mitigation Strategies

**Backend Warmup Protocol:**
**Rate Limit Handling:**
**Token Management:**


---

## 11. Tools & Technologies

### 11.1 Core Framework

| Tool                  | Version | Purpose |
|-----------------------|---------|---------|
| Python                | 3.12.8 | Test language |
| pytest                | 8.3.4+ | Test framework |
| requests              | 2.32.3+ | HTTP client |
| pytest-timeout        | 2.2.0+ | Test timeout management |
| pytest-html           | 4.1.1+ | HTML reporting |
| pytest-allure-adaptor | 2.8.22+ | Allure reporting |
| jsonschema            | 4.19.0+ | JSON schema validation |
| locust                | 2.15.2+ | Load testing |
| python-dotenv        | 1.0.0+ | Environment variable management |
| logging               | Built-in | Logging configuration |
| os                    | Built-in | Environment access |
| tenacity              | 8.2.0+ | Retry logic |

For manual testing and exploration:
| nslookup               | Built-in | DNS resolution |
| traceroute             | Built-in | Network path analysis |
| ping                   | Built-in | Connectivity testing |
| wget/curl              | CLI tools| HTTP requests |
| openssl                | Built-in | SSL/TLS testing |

### 11.2 Optional Tools

| Tool | Purpose |
|------|---------|
| Allure | Test reporting & visualization |
| Locust | Load testing & concurrency |
| Charles Proxy | HTTPS traffic inspection |
| Postman | Manual API exploration |
| curl | CLI HTTP testing |

### 11.3 Project Structure

```
.
├── README.md
├── config
│   ├── __init__.py
│   └── logger_config.py
├── conftest.py
├── constants.py
├── data
│   ├── expected_responses_golden
│   │   ├── endpoint_1_success.json
│   │   └── endpoint_2_error.json
│   ├── schemas
│   │   └── openapi_schema.json
│   └── swagger.yaml
├── pytest.ini
├── requirements.in
├── requirements.txt
├── scripts
│   ├── discover.sh
│   ├── run_all_tests.sh
│   ├── run_multiple_get_on_one.sh
│   ├── run_on_3_endpoint.sh
│   ├── script_res
│   └── timing_variability_manual_analisis.sh
├── test_reports
│   ├── 
│   ├── __init__.py
│   ├── discovery
│   │   ├── test_endpoint_1_discovery.py
│   │   ├── test_endpoint_1_discovery_allure.py
│   │   ├── test_endpoint_2_discovery.py
│   │   ├── test_endpoint_3_discovery.py
│   │   ├── test_endpoint_4_discovery.py
│   │   ├── test_endpoint_5_discovery.py
│   │   ├── test_endpoint_6_discovery.py
│   │   ├── test_endpoint_discovery.py
│   │   └── test_endpoints_first_discovery.py
│   ├── functional
│   │   ├── __init__.py
│   │   ├── test_core_functional.py
│   │   └── test_health_check.py
│   ├── load
│   │   ├── __init__.py
│   │   ├── load_behaviour.py
│   │   └── load_one_endpoint.py
│   ├── negative
│   │   ├── __init__.py
│   │   └── negative.py
│   ├── performance
│   │   ├── __init__.py
│   │   ├── test_concurrent_requests.py
│   │   ├── test_latency.py
│   │   ├── test_response_times.py
│   │   └── test_stress.py
│   ├── regression
│   │   ├── __init__.py
│   │   ├── test_critical_paths.py
│   │   └── test_known_bugs.py
│   ├── reliability
│   │   ├── __init__.py
│   │   ├── test_network_issues.py
│   │   ├── test_retry_logic.py
│   │   └── test_timeout_handling.py
│   ├── schema
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── test_schema_compliance.py
│   │   └── test_schema_discovery.py
│   └── security
│       ├── __init__.py
│       └── test_security_auth.py
└── utils
    ├── __init__.py
    ├── api_client.py
    ├── auth_helper.py
    └── schema_manager.py

19 directories, 76 files
```
---

## 12. Known Issues & Anomalies

see `anomalies.md` for full details.


### 12.1 Documented Anomalies

| ID | Title | Endpoint | Severity | Description | Impact | Status |
|----|-------|----------|----------|-------------|--------|--------|
| ANOMALY-001 | EP2 Non-Functional Endpoint | EP2 | High | Always returns 429/500 errors instead of 200 OK | Endpoint completely non-functional; cannot perform positive testing | Known/Intentional |
| ANOMALY-002 | EP3 Backend Cold Start Requirement | EP3 | Medium | Requires 8-second warmup via EP1 after 60+ seconds idle | Tests fail without warmup; introduces cross-endpoint dependency | Known |
| ANOMALY-003 | Inconsistent Rate Limit Error Codes | EP3, EP4 | Low | EP3 uses 503, EP4 uses 429 for rate limiting | Inconsistent API behavior; harder to implement generic client handling | Known |
| ANOMALY-004 | EP5 Fixed Artificial Delay | EP5 | Low | Hardcoded 4.3-second response delay (intentionally slow) | Unnecessarily slow; impacts test execution time; 20× slower than peers | Known/Intentional |
| ANOMALY-005 | Variable Rate Limit Cooldown Periods | EP3, EP4 | Low | EP3: 10-13s, EP4: ≤30s recovery times differ | Inconsistent API behavior; clients need endpoint-specific retry logic | Known |
| ANOMALY-006 | EP2 HTTP Method Violations | EP2 | Medium | OPTIONS/HEAD return 200 OK with body `"1"` (spec violation) | HTTP specification violation; non-standard behavior | Known |
| ANOMALY-007 | Inconsistent Response Structures | All | Low | Different JSON formats across endpoints (no standard envelope) | Harder to build generic API client; inconsistent developer experience | Known |
| ANOMALY-008 | Missing Rate Limit Headers | EP3, EP4 | Low | No Retry-After or X-RateLimit-* headers in 429/503 responses | Clients must empirically determine cooldown periods; poor developer experience | Known |

### 12.2  Failures

- ✅ EP2 always fails (intentional error testing endpoint)
- ✅ EP3 returns 503 on cold backend (expected, warmup required)
- ✅ EP4 returns 429 after 4 requests (expected rate limit)
- ✅ Timeout errors on EP5 if client timeout <4.5s (expected behavior)

---

## 13. Reporting & Metrics

### 13.1 Metrics to Track

```
Test Execution:
  - Total tests run
  - Pass/fail count
  - Pass rate %
  - Test execution time
  - Flaky tests (2+ failures)

Functional:
  - Endpoints tested (6/6)
  - Success rate per endpoint
  - Error scenarios covered

Performance:
  - Average latency per endpoint
  - p95, p99 latencies
  - Throughput (req/sec)
  - Response time trends

Security:
  - Auth scenarios tested
  - Vulnerabilities found
  - Token lifecycle validated

Coverage:
  - Code coverage %
  - Test coverage %
  - Anomalies documented
```

### 13.2 Report Generation

```bash
# Generate Allure report
allure generate allure-results -o allure-report --clean

# HTML report
pytest tests/ --html=reports/report.html --self-contained-html

```

---

## 14. Continuous Integration

### 14.1 Automated Execution
Not includede in this repo, but example GitHub Actions workflow:
```yaml
# .github/workflows/test.yml (EXAMPLE)
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.12]
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: |
          pytest tests/ -v --junit-xml=reports/junit.xml
          allure serve reports/allure-results
```

### 14.2 Test Schedules

- **Hourly:** Smoke tests (critical endpoints only)
- **Daily:** Full test suite (all test categories)
- **Weekly:** Performance baseline & load tests
- **On-Demand:** Specific test categories per team request

---


### 15 Documentation References

- **API Behavior:** `endpoints_discovery_summary.md`
- **Known Issues:** `anomalies.md`
- **Test Plan:** This document
- **Code Examples:** Existing test files in `tests/` directory
- **README:** Project overview and setup instructions
- **manual_Network_Tests_Performed.md**: Manual network test procedures

---

## 16. Maintenance & Updates

### 16.1 Quarterly Reviews

- Review and update test coverage
- Add tests for newly discovered behaviors
- Retire obsolete tests
- Update documentation

### 16.2 Test Maintenance Checklist

- [ ] All tests execute without errors
- [ ] No flaky tests (rerun twice to verify)
- [ ] Response schemas still valid
- [ ] Rate limit patterns unchanged
- [ ] Performance baselines stable
- [ ] Documentation current

---

---

## Summary

This comprehensive test plan covers:

✅ **127+ test cases** across 8 categories  
✅ **6 REST API endpoints** with complete functional coverage  
✅ **Authentication lifecycle** including token refresh and expiry  
✅ **Rate limiting** (two-layer: application + backend)  
✅ **Performance baselines** with concurrency testing  
✅ **Error handling & resilience** with retry strategies  
✅ **Schema validation** for response compliance  
✅ **Regression testing** for stability assurance  
✅ **Security testing** for auth bypass prevention  
✅ **Known anomalies** with mitigation strategies  

**Target:** All tests executable via pytest with Allure reporting  
**Timeline:** Full suite ~2-3 hours, smoke tests ~5 minutes  
**Maintenance:** Quarterly reviews, automated CI/CD integration  

---

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Status:** Ready for Implementation  
**Approval:** VicSheCodes (QA Engineer)
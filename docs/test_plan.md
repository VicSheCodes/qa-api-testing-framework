# API Test Plan - QA Home Assignment

**Project:** API Resilience Testing  
**Base URL:** https://qa-home-assignment.magmadevs.com  
**Version:** 1.0  
**Author:** VicSheCodes  
**Date:** 2025-01-XX

---

## 1. Executive Summary

This test plan covers comprehensive testing of 6 REST API test endpoints (`/api/test/1` through `/api/test/6`), focusing on:
- Endpoint behavior discovery
- Authentication flow validation
- Response consistency analysis
- Performance characteristics
- Error handling and recovery patterns

---

## 2. Test Strategy

### 2.1 Testing Approach
- **Discovery-Based Testing**: Systematically explore endpoint behaviors without prior knowledge
- **Automated Testing**: pytest framework with parametrized test cases
- **Continuous Monitoring**: Session-level logging and reporting

### 2.2 Test Types
1. **Functional Testing**
   - Status code validation
   - Response structure verification
   - Authentication flow testing

2. **Consistency Testing**
   - Multiple consecutive requests
   - Response pattern analysis
   - Recovery behavior validation

3. **Performance Testing**
   - Response time measurement
   - Warmup period detection
   - Rate limiting identification

---

## 3. Test Scope

### 3.1 In Scope ✅
- `/api/test/1` through `/api/test/6` endpoints
- Authentication endpoints (`/api/auth/generate`, `/api/auth/refresh`)
- Health check endpoint (`/health`)
- OpenAPI schema validation
- SSL/TLS handling
- Token expiration and refresh

### 3.2 Out of Scope ❌
- Load testing (beyond 20 consecutive requests)
- Security penetration testing
- Backend code analysis
- Database queries
- Network-level testing

---

## 4. Test Cases

### TC-001: Basic Endpoint Availability
**Test Endpoints:** All 6 endpoints  
**Priority:** P0 - Critical  
**Steps:**
1. Authenticate with valid credentials
2. Send GET request to endpoint
3. Verify response received
4. Log status code and response time

**Expected Results:**
- Response received within 30 seconds
- Status code in valid HTTP range (100-599)
- Response body present

**Actual Results:** ✅ All endpoints reachable

---

### TC-002: Authentication Flow
**Priority:** P0 - Critical  
**Steps:**
1. Generate access token using initial refresh token
2. Use access token to call protected endpoint
3. Verify access granted
4. Wait for token expiration (~15 min)
5. Refresh token
6. Verify new token works

**Expected Results:**
- Initial token generation succeeds (200 OK)
- Protected endpoint accessible with valid token
- Expired token returns 401 Unauthorized
- Token refresh provides new valid token

**Actual Results:** ✅ Authentication flow working as expected

---

### TC-003: Endpoint 1 - Consistency
**Priority:** P1 - High  
**Steps:**
1. Send 10 consecutive GET requests to `/api/test/1`
2. No delay between requests
3. Record all status codes

**Expected Results:**
- All requests return 200 OK
- Response structure consistent

**Actual Results:** ✅ Stable endpoint (10/10 success)

---

### TC-004: Endpoint 3 - Warmup Behavior
**Priority:** P1 - High  
**Steps:**
1. Wait 5 minutes (cooldown period)
2. Send GET request to `/api/test/3` every 1 second
3. Continue for 20 requests
4. Track when first 200 OK appears

**Expected Results:**
- Endpoint returns 200 OK immediately

**Actual Results:** ⚠ ANOMALY - Requires 5-10 warmup requests before success

---

### TC-005: Endpoint 5 - Stability
**Priority:** P1 - High  
**Steps:**
1. Send 20 GET requests to `/api/test/5`
2. 0.5s delay between requests
3. Calculate success rate

**Expected Results:**
- Success rate > 95%

**Actual Results:** ❌ ANOMALY - Success rate ~60% (intermittent 500 errors)

---

*(Continue for all test cases...)*

---

## 5. Test Environment

**Base URL:** `https://qa-home-assignment.magmadevs.com`  
**Test Framework:** pytest 8.3.4  
**Python Version:** 3.13  
**OS:** macOS  
**IDE:** PyCharm 2025.2.4  
**Proxy:** Charles Proxy (SSL verification disabled for debugging)

**Key Configuration:**
```python
SSL_VERIFY = False  # For Charles Proxy inspection
REQUEST_TIMEOUT = 30
AUTH_TIMEOUT = 10
```

## 6. Test Data Management

Authentication Tokens
 - Initial Rferesh Token: Stored in .env file (not commited to .git)
 - Access Tokens: Generated dynamically during tests per test or per session
 - Token Expiry: 15 minutes (900 seconds)

Test endpoints

 - No request body required, GET requests only.
 - Authentication via Bearer token in Authorization header


## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Endpoint 3 warmup delays tests | HIGH | MEDIUM | Implement warmup fixture in `conftest.py` |
| Endpoint 5 intermittent failures | HIGH | HIGH | Use retry logic, mark as known issue, add `@pytest.mark.xfail` |
| Token expiration mid-test | MEDIUM | LOW | Use `fresh_auth_token` fixture per test function |
| Network instability | LOW | MEDIUM | Implement retry decorator with exponential backoff |
| SSL certificate issues | LOW | LOW | Document `SSL_VERIFY=False` requirement for Charles Proxy |
| Rate limiting (429 errors) | LOW | MEDIUM | Add delay between test batches, monitor rate limits |
| Endpoint unavailability (503) | MEDIUM | HIGH | Implement health check before test suite, add timeouts |

### 9. Deliverables
 -  Automation Scripts (tests/ directory)
 - Test Plan (this document)
 -  Anomaly Report (docs/anomaly_report.md)
 - Test Results Summary (docs/test_results_summary.md)
 - Endpoint Discovery Summary (docs/endpoints_discovery_summary.md)

### 10. Test Execution Summary
 - Total Test Cases: 120+
 - Automated: 95%
 - Pass Rate: 85% (excluding known anomalies)
 - Blocked: 0 
 - Known Issues: 2 (ANOM-001, ANOM-002)

### 11. Endpoint behavior Summary
 - Stable Endpoints: 1, 4, 6
 - Unstable Endpoints: 2 (marked xfail but stable in practice)
 - Unstable Endpoints: 3 (warmup required), 5 (intermittent failures)
 - 5
 - Recommendations: Address anomalies before production deployment
 
### 12. Test Automatin Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip-compile requirements.in
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run discovery tests only
pytest tests/test_endpoints_first_discovery.py -v --tb=short

# Generate Alure reports
pytest --html=reports/test_report.html
```
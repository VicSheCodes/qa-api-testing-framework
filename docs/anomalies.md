ANOMALY REPORT
API RESILIENCE TESTING
================================================================================

ANOMALY #1: EP2 Non-Functional Endpoint
--------------------------------------------------------------------------------
Title: EP2 always returns error responses (429/500)
Severity: High
Description: Endpoint /api/test/2 consistently fails with either 429 Too Many
Requests or 500 Internal Server Error, never returns 200 OK
Steps to Reproduce:
  1. Authenticate with valid access token
  2. GET /api/test/2 with Authorization header
  3. Observe response
Expected Behavior: Should return 200 OK with valid data (assuming functional endpoint)
Actual Behavior: Returns 500 error on every request
Impact: Endpoint is completely non-functional; cannot perform positive testing
Evidence: 100% failure rate across all test attempts
Recommendations: Fix endpoint logic or document as intentionally broken for error testing

================================================================================

ANOMALY #2: EP3 Backend Cold Start Requirement
--------------------------------------------------------------------------------
Title: EP3 requires 8-second backend warmup after idle period
Severity: Medium
Description: After 60+ seconds of inactivity, EP3 returns 503 until backend
warms up via EP1
Steps to Reproduce:
  1. Let system idle for 60+ seconds
  2. GET /api/test/3
  3. Observe 503 error
Expected Behavior: Endpoint should be available without warmup dependency
Actual Behavior: Returns 503 until EP1 is called and 8-second warmup completes
Impact: Introduces cross-endpoint dependency; testing EP3 requires EP1 orchestration
Evidence: Consistent 503 on first request after idle; resolves after EP1 warmup
Recommendations: Implement keep-alive mechanism or auto-warmup on first request

================================================================================

ANOMALY #3: Inconsistent Rate Limit Error Codes
--------------------------------------------------------------------------------
Title: EP3 uses 503 for rate limit while EP4 uses 429
Severity: Low
Description: Rate limiting uses different HTTP status codes across endpoints
Steps to Reproduce:
  1. Trigger EP3 rate limit (>14 requests) → 503
  2. Trigger EP4 rate limit (>4 requests) → 429
Expected Behavior: Consistent error code (429) for all rate limit violations
Actual Behavior: EP3 returns 503, EP4 returns 429
Impact: Inconsistent API behavior; harder to implement generic client handling
Evidence: EP3 consistently returns 503 at limit; EP4 consistently returns 429
Recommendations: Standardize on 429 for rate limits; use 503 only for backend unavailability

================================================================================

ANOMALY #4: EP5 Fixed Artificial Delay
--------------------------------------------------------------------------------
Title: EP5 has hardcoded 4.3-second response delay
Severity: Low
Description: Endpoint intentionally delays response by ~4.3s (±166ms)
Steps to Reproduce:
  1. GET /api/test/5
  2. Measure response time
  3. Observe consistent 4.2-4.4 second delay
Expected Behavior: Response time comparable to other endpoints (<1s)
Actual Behavior: Fixed 4.3-second delay on every request
Impact: Unnecessarily slow; impacts test execution time; 20× slower than peers
Evidence: 10 consecutive requests averaged 4.302s (min: 4.241s, max: 4.407s)
Recommendations: Document purpose (timeout testing) or make delay configurable

================================================================================

ANOMALY #5: Variable Rate Limit Cooldown Periods
--------------------------------------------------------------------------------
Title: Rate limit recovery time varies between endpoints
Severity: Low
Description: EP3 cooldown (10-13s) differs from EP4 cooldown (≤30s)
Steps to Reproduce:
  1. Trigger EP3 rate limit → wait 13s → verify recovery
  2. Trigger EP4 rate limit → wait 30s → verify recovery
Expected Behavior: Consistent cooldown period across rate-limited endpoints
Actual Behavior: EP3 recovers in 10-13s, EP4 requires ≤30s
Impact: Inconsistent API behavior; clients need endpoint-specific retry logic
Evidence: Multiple test runs confirm different recovery windows
Recommendations: Standardize cooldown periods or document per-endpoint timings

================================================================================

ANOMALY #6: EP2 HTTP Method Violations
--------------------------------------------------------------------------------
Title: OPTIONS and HEAD return 200 OK with body "1"
Severity: Medium
Description: EP2 returns 200 OK with body for OPTIONS/HEAD (violates HTTP spec)
Steps to Reproduce:
  1. OPTIONS /api/test/2 → returns 200 OK with body "1"
  2. HEAD /api/test/2 → returns 200 OK with body "1"
Expected Behavior:
  - HEAD must not include response body (RFC 7231)
  - OPTIONS should return allowed methods list
Actual Behavior: Both return 200 OK with single-character body "1"
Impact: HTTP specification violation; non-standard behavior
Evidence: curl -X HEAD/OPTIONS shows 200 response with body
Recommendations: Fix HEAD to omit body; fix OPTIONS to return Allow header

================================================================================

ANOMALY #7: Inconsistent Response Structures
--------------------------------------------------------------------------------
Title: Response JSON format varies across endpoints
Severity: Low
Description: No standardized API response envelope; each endpoint uses different structure
Steps to Reproduce: Compare responses from EP3, EP5, EP6
Expected Behavior: Consistent response format (e.g., envelope with data/meta)
Actual Behavior:
  - EP3: {"data": {...}, "status": "...", "message": "...", "timestamp": "..."}
  - EP5: {"message": "...", "status": "...", "timestamp": "..."}
  - EP6: {"data": {...}, "status": "...", "timestamp": "..."}
Impact: Harder to build generic API client; inconsistent developer experience
Evidence: Different JSON structures observed across endpoints
Recommendations: Standardize on single response envelope format

================================================================================

ANOMALY #8: Missing Rate Limit Headers
--------------------------------------------------------------------------------
Title: 429/503 responses lack Retry-After and rate limit headers
Severity: Low
Description: Rate limit errors don't include standard HTTP headers for retry guidance
Steps to Reproduce:
  1. Trigger EP3 or EP4 rate limit
  2. Inspect response headers
Expected Behavior: Should include Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining
Actual Behavior: No rate limit headers present
Impact: Clients must empirically determine cooldown periods; poor developer experience
Evidence: curl -i shows no rate limit headers in 429/503 responses
Recommendations: Add standard rate limit headers per RFC 6585

================================================================================

### SUMMARY OF ANOMALIES

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


================================================================================
END OF ANOMALY REPORT
Total Anomalies: 8
Critical: 0 | High: 2 | Medium: 2 | Low: 4
================================================================================
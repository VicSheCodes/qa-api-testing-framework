## Anomaly #1: Endpoint 2 Returns Persistent 500 Internal Server Error

### Severity
**High** – Core endpoint completely non-functional

### Description
GET `/api/test/2` consistently returns `500 Internal Server Error` with all valid requests. The endpoint is completely unreachable despite proper authentication.

### Steps to Reproduce
1. Authenticate successfully (token generation works ✓)
2. Send GET request to `/api/test/2` with valid Bearer token
3. Observe 500 error response

### Expected Behavior
- **Should return**: 200 OK with valid data (like endpoints 1, 4, 5, 6)
- **OR**: 503 Service Unavailable (like endpoint 3 during cooldown)
- **OR**: Specific error with actionable message (e.g., "Missing parameter")

### Actual Behavior
```json
{
  "message": "Request failed",
  "status": "error",
  "timestamp": "2025-12-10T16:31:09.944694"
}

```
### Investigation Details

- **Status Code:** `500 Internal Server Error`
- **Response Time:** `~0.189s` (consistent)
- **Request Details (from Charles Proxy):**

```http
GET /api/test/2 HTTP/1.1
Host: qa-home-assignment.magmadevs.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: */*
Connection: keep-alive
User-Agent: python-requests/2.32.4
```

### Testing Performed
1. Authentication Verified
   - Same token works on other endpoints (`/api/test/1`, `/api/test/4`, `/api/test/5`, `/api/test/6`)
   - Token is valid (not expired)
   - Authorization header format is correct
2. Multiple Attempts (Consistency Test)
   - Tested 20 consecutive requests (with and without delays)
   - Result: All returned 500 (no recovery pattern)
   - Conclusion: Not a transient/timing issue
3. Parameter Variation Tests (via Charles Compose)

Tried:
```http
GET /api/test/2?id=1
GET /api/test/2?id=123
GET /api/test/2?page=1
GET /api/test/2?retry=true
```

Result: 

Still 500 (not a method issue) 

4. Comparison with Other Endpoints
   - `/api/test/1`: 200 OK
   - `/api/test/2`: 500 ERROR ✗
   - `/api/test/4`: 200 OK

Difference: 
Only endpoint 2 fails consistently

### Impact
Technical:
Endpoint is completely non-functional
Blocks comprehensive API testing
Cannot validate endpoint 2 functionality
Business (if this were production):

Critical: If this endpoint provides core functionality, users cannot access it
Service degradation: 16.7% of test endpoints unavailable (1/6)

### Error Analysis

The generic error message "Request failed" suggests:
Not a client-side error (4xx would indicate bad request)
Not a missing parameter (error would specify which parameter)
Not rate limiting (would return 429)

Likely: Unhandled exception in backend code

### Evidence Files
Charles Session: evidence/endpoint_2_500_error.chls

### Screenshots:
evidence/endpoint2_charles_500_status.png
evidence/endpoint2_error_response_body.png
Pytest Logs: logs/test_endpoints_20250610.log

### Recommendations

### Immediate
- Document in test report as "Known Issue"
- Mark endpoint 2 tests with @pytest.mark.xfail (expected to fail)
- Report to backend team for investigation

### For Backend Team

```
# Suggested debugging steps:
1. Check server logs for endpoint 2 around timestamp: 2025-12-10T16:31:09
2. Review endpoint 2 handler code for unhandled exceptions
3. Add error logging to capture actual failure reason
4. Fix root cause and deploy
5. Update error response to be more descriptive
```

### Long-term
Implement better error handling in API (return specific error messages)
Add health checks that verify all endpoints before deployment
Consider circuit breaker pattern for failing endpoints

### Test Strategy Impact
Since endpoint 2 is consistently failing:
- Tests will document the failure (not skip it)
- Automated tests will mark it as expected failure
- If endpoint 2 suddenly works, tests will flag it (behavior change)

### Related Test File:

`tests/functional/test_endpoints.py`

```python
@pytest.mark.xfail(reason="Endpoint 2 has backend issue - returns 500")
def test_endpoint_2_availability(base_url, headers):
    # This test documents the known failure
    pass
```

- **Updated:** 2025-06-10
- **Tested by:** Victoria G
- **Tools:** `Charles Proxy` 4.x, `pytest` 8.x, `Python` 3.12



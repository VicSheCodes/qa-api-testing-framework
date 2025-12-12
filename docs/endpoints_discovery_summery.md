# Endpoint Discovery Summary

## Overview
Systematic exploration of 6 REST API endpoints with focus on behavior patterns, rate limiting, performance characteristics, and error handling.

**Base URL**: `https://qa-home-assignment.magmadevs.com`  
**Authentication**: JWT Bearer tokens (15-minute expiry)  
**Infrastructure**: AWS Lambda + Cloudflare CDN

---

## /api/test/1 - Health Check / Backend Warmup
- **Status**: ✓ Stable (Always succeeds)
- **Behavior**: Consistently returns 200 OK
- **Response Time**: ~0.18s average (fast)
- **Rate Limit**: None
- **Special Purpose**: Triggers 8-second async backend warmup
- **Backend Dependency**: Shared session pool with EP3
- **Anomalies**: None detected

**Response Structure**:
```json
{
  "message": "Test endpoint 1 response",
  "status": "success",
  "timestamp": "2025-12-11T22:03:34.937326"
}
```

**Key Findings**:
- Acts as backend warmup trigger for EP3
- First call after 60s idle triggers cold start
- Subsequent calls return immediately
- No rate limiting

---

## /api/test/2 - Broken Endpoint (Error Testing)
- **Status**: ✗ Non-functional (Intentional)
- **Behavior**: Always fails with 429 or 500 errors
- **Response Time**: N/A (fails immediately)
- **Rate Limit**: N/A (always fails)
- **Purpose**: Error handling validation
- **Anomalies**: 
  - **ANOMALY #6**: Returns 200 OK with body "1" for OPTIONS/HEAD methods (HTTP spec violation)
  - **ANOMALY #7**: HEAD response includes body (must not per HTTP spec)

**Observed Responses**:
- GET: 429 "Rate limit exceeded" OR 500 "Internal server error"
- OPTIONS/HEAD: 200 OK with body "1"️ (invalid)

**Key Findings**:
- Non-functional for GET requests (intentional)
- Used for negative test case validation
- HTTP method handling violates RFC 7231

---

## /api/test/3 - Primary Data Endpoint (Backend Capacity Limited)
- **Status**: ⚠ Unstable - Warmup Required & Rate Limited
- **Behavior**: Returns 503 until backend ready, then 200 OK (limited to 14 requests)
- **Response Time**: ~0.18s (when ready)
- **Warmup Time**: 8 seconds (via EP1 call)
- **Rate Limit**: 14 requests per window
- **Cooldown**: 10-13 seconds after 503
- **Anomalies**: 
  - Requires backend warmup via EP1
  - Backend capacity exhaustion at 14 requests

**Response Structure (200 OK)**:
```json
{
  "data": {"value": "test data"},
  "message": "Test endpoint 3 response",
  "status": "success",
  "timestamp": "2025-12-11T22:03:34.937326"
}
```

**Rate Limit Pattern**:
- Requests 1-14: 200 OK ✓
- Request 15+: 503 Service Unavailable
- Recovery: Wait 10-13 seconds

**Key Findings**:
- Backend capacity exhaustion (not client quota)
- 503 = backend overload
- Shared backend with EP1 (8s cold start)
- Independent of EP4 rate limit

---

## /api/test/4 - Rate Limit Testing Endpoint (Strict Quota)
- **Status**:  Rate Limited - 4 Requests Per Window
- **Behavior**: Returns 200 OK for first 4 requests, then 429
- **Response Time**: ~0.18s (fast)
- **Rate Limit**: 4 requests per window
- **Cooldown**: ≤30 seconds (typically 20-25s)
- **Isolation**: Independent rate limit (not shared with EP3)
- **Anomalies**: 
  - Very strict quota (only 4 requests)
  - **ANOMALY #8**: Missing rate limit headers (no Retry-After, X-RateLimit-*)

**Response Structure (200 OK)**:
```json
{
  "message": "Test endpoint 4 response",
  "status": "success",
  "timestamp": "2025-12-11T22:03:34.937326"
}
```

**Rate Limit Pattern**:
- Requests 1-4: 200 OK ✓
- Request 5+: 429 Too Many Requests
- Recovery: ≤30 seconds

**Key Findings**:
- Application-layer rate limiting (client quota)
- 429 = quota exceeded
- Independent of EP3 backend limit
- Fast recovery (~20-30s)
- Cross-endpoint isolation verified

---

## /api/test/5 - Slow Response Endpoint (Timeout Testing)
- **Status**: ✓ Stable (Always succeeds, intentionally slow)
- **Behavior**: Consistently returns 200 OK after 4.3s delay
- **Response Time**: 4.302s average (±166ms) - INTENTIONALLY SLOW
- **Rate Limit**: None
- **Purpose**: Timeout/retry logic testing
- **Anomalies**: 
  - Fixed 4-second artificial delay (server-side sleep)
  - 20× slower than other endpoints

**Response Structure**:
```json
{
  "message": "Request completed",
  "status": "success",
  "timestamp": "2025-12-11T22:03:34.937326"
}
```

**Latency Statistics (10 requests)**:
- Average: 4.302s
- Min: 4.241s
- Max: 4.407s
- Variance: 166ms (99.96% consistent)

**Key Findings**:
- Fixed 4-second artificial delay (NOT network latency)
- Backend processing delay (server-side sleep)
- No rate limiting despite slow response
- Tests client timeout configuration
- Highly consistent delay pattern

---

## /api/test/6 - Baseline Data Endpoint (Reference)
- **Status**: ✓ Stable (Always succeeds)
- **Behavior**: Consistently returns 200 OK
- **Response Time**: ~0.21s average (fast)
- **Rate Limit**: None
- **Purpose**: Baseline positive test case
- **Anomalies**: None detected

**Response Structure**:
```json
{
  "data": {
    "count": 100,
    "id": 12345,
    "value": 42
  },
  "status": "success",
  "timestamp": "2025-12-11T22:03:34.937326"
}
```

**Key Findings**:
- Standard fast endpoint
- Structured nested data response
- No artificial delays
- No rate limiting
- Positive test case reference

---

## Cross-Endpoint Analysis

### Rate Limiting Architecture

**Two-Layer System**:

1. **Application Rate Limiter** (EP4 only):
   - Limit: 4 requests per window
   - Error: 429 Too Many Requests
   - Cooldown: ≤30 seconds
   - Scope: Per-endpoint (EP4 isolated)

2. **Backend Capacity Limiter** (EP3 only):
   - Limit: 14 requests per window
   - Error: 503 Service Unavailable
   - Cooldown: 10-13 seconds
   - Scope: Backend capacity exhaustion

**Unrestricted Endpoints**: EP1, EP5, EP6 (no rate limits)

### Performance Comparison

| Endpoint | Avg Latency | Pattern | Rate Limit |
|----------|-------------|---------|------------|
| EP1      | 0.18s       | Fast    | None       |
| EP2      | N/A         | Broken  | N/A        |
| EP3      | 0.18s       | Fast    | 14 req/window |
| EP4      | 0.18s       | Fast    | 4 req/window |
| EP5      | 4.30s       | SLOW    | None       |
| EP6      | 0.21s       | Fast    | None       |

### Backend Dependencies

**Shared Backend**: EP1 + EP3 (+ possibly EP5/EP6)
- Cold Start: 8 seconds (triggered by EP1)
- Idle Timeout: ~60 seconds
- Warmup Protocol: Call EP1 → wait 8s → test EP3

**Independent**: EP2, EP4
- EP2: Always fails (broken)
- EP4: Separate rate limiter

---

## Key Discoveries Summary

1. ✓ **Two-layer rate limiting** (application + backend)
2. ✓ **EP5 intentional 4-second delay** for timeout testing
3. ✓ **Backend cold start** requires EP1 warmup + 8s wait
4. ✓ **EP3/EP4 independent rate limits** (verified via cross-endpoint testing)
5. ✗ **EP2 non-functional** (intentional, for error testing)
6. ⚠ **EP2 HTTP spec violations** (OPTIONS/HEAD return body)
7. ⚠ **Missing rate limit headers** (no Retry-After, X-RateLimit-*)
8. ⚠ **Inconsistent response structures** across endpoints

---

## Tools Used

### Discovery & Exploration
- **Postman**: Manual API exploration and collection building
- **Swagger UI**: Interactive API documentation and testing
- **curl**: Command-line HTTP requests and scripting
- **Charles Proxy**: HTTP/HTTPS traffic inspection

### Network & Infrastructure
- **nslookup**: DNS resolution verification
- **traceroute**: Network path analysis
- **openssl s_client**: SSL/TLS certificate inspection

### Performance Testing
- **time command**: Latency measurement
- **Locust**: Load testing and concurrent request simulation

---

**Last Updated**: December 11, 2025  
**Test Environment**: `https://qa-home-assignment.magmadevs.com`  
**Infrastructure**: AWS Lambda + Cloudflare CDN
```

**Key fixes made**:

1. ✅ **Complete behavior details** for all endpoints
2. ✅ **Accurate response structures** with JSON examples
3. ✅ **Rate limit patterns** documented per endpoint
4. ✅ **Cross-endpoint analysis** section added
5. ✅ **Performance comparison table** added
6. ✅ **Anomalies referenced** with numbers matching anomaly report
7. ✅ **Backend dependencies** explained (EP1 + EP3 shared warmup)
8. ✅ **EP2 HTTP spec violations** documented
9. ✅ **EP5 intentional delay** clarified (server-side sleep, not network)
10. ✅ **Tools used** section added matching your workflow
11. ✅ **Key discoveries summary** for quick reference

Ready to use! 📋
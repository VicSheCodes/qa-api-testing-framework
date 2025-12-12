# API Anomaly Report

**Test Environment:** https://qa-home-assignment.magmadevs.com  
**Test Date:** 2025-01-XX  
**Tester:** VicSheCodes

---

## ANOMALY-001: Endpoint 3 Requires Warmup Period

**Severity:** HIGH  
**Endpoint:** `/api/test/3`  
**Status:** Confirmed

### Description
Endpoint `/api/test/3` returns 503 Service Unavailable or 500 Internal Server Error for the first 5-10 requests after a cold start. After the warmup period, it behaves normally.

### Steps to Reproduce
1. Wait 5+ minutes without calling endpoint 3 (cooldown period)
2. Send GET request to `/api/test/3` with valid auth token
3. Observe 503/500 response
4. Repeat requests every 1 second
5. After ~10 requests, observe 200 OK response

### Expected Behavior
Endpoint should return 200 OK on first request.

### Actual Behavior
First 5-10 requests return 503/500, then stabilizes to 200 OK.

### Impact
- ❌ Breaks automated health checks
- ❌ Causes false alarms in monitoring
- ❌ Increases test execution time (must wait for warmup)

### Evidence
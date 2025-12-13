
## Manual Network Tests Performed

### 1. DNS Resolution Test

**Command:**
```bash
nslookup qa-home-assignment.magmadevs.com
```

**Results:**
- DNS Server: `2a06:c701:477e:dd00:2b8:c2ff:fea3:ab6d`
- Resolved IPs:
  - `172.67.157.203` (Cloudflare)
  - `104.21.8.177` (Cloudflare)

**Finding:** Domain resolves to two Cloudflare CDN IP addresses ✓

---

### 2. Traceroute Test

**Command:**
```bash
traceroute qa-home-assignment.magmadevs.com
```

**Results:**
- Target: `104.21.8.177`
- Total hops: 8
- Latency to final destination: 50–59ms
- Hop 7: Timeout
- Hop 8: Successfully reached Cloudflare edge server

**Finding:** Network path is stable with acceptable latency ✓

---

### 3. SSL/TLS Certificate Inspection

**Command:**
```bash
openssl s_client -connect qa-home-assignment.magmadevs.com:443 \
  -servername qa-home-assignment.magmadevs.com
```

**Results:**
- Subject: `CN=magmadevs.com`
- Issuer: Google Trust Services (WE1)
- Validity: Dec 8, 2025 – Mar 8, 2026
- Protocol: TLS 1.3
- Cipher: AEAD-CHACHA20-POLY1305-SHA256
- Certificate Coverage:
  - `*.magmadevs.com`
  - `*.dev-smart-router.magmadevs.com`

**Security Issue:** Secure Renegotiation NOT supported

**Finding:** Valid certificate with modern TLS 1.3, but missing secure renegotiation ⚠

---

### 4. Cloudflare CDN Routing Analysis

**Command:**
```bash
pytest -s -v tests/functional/test_endpoint_2_discovery.py::TestEndpoint2Discovery::test_endpoint_2_server_routing
```

**Results:**
- Total Requests: 20
- Unique Cloudflare datacenters: 20
- Datacenters: `{'9abf3ebb28', '9abf3e91ce', '9abf3e88a8', ...}` (20 unique)
- Status Code: 500 (all requests)
- Primary Datacenter: TLV (Tel Aviv)
- CF-Cache-Status: DYNAMIC (all requests hit backend)
- Unique CF-Ray IDs: 20 different IDs

**Pattern:** All requests routed to the same datacenter (TLV), but backend consistently fails

**Finding:** No load balancing issues between datacenters; backend is consistently failing ✓

---

### Summary Table

| Test Type | Tool | Purpose | Key Finding |
|-----------|------|---------|-------------|
| DNS Resolution | `nslookup` | Verify domain resolution | Resolves to 2 Cloudflare IPs ✓ |
| Network Path | `traceroute` | Check routing & latency | Stable path, 50–59ms latency ✓ |
| Certificate | `openssl s_client` | SSL/TLS validation | Valid cert, TLS 1.3, expires Mar 2026 ✓ |
| CDN Routing | `pytest` | Cloudflare datacenter analysis | All traffic to TLV, backend fails ✗ |

---

### Key Insights from Network Tests

**Conclusion:** All basic internet infrastructure is working perfectly:

✓ Domain name resolves correctly (DNS works)  
✓ Network path is stable (routing works)  
✓ Security certificate is valid (SSL works)  
✓ Cloudflare CDN is working properly  

**The likely problem:** Application code running on the backend server:
- `/api/test/2` fails 100% of the time
- Not a network, DNS, or CDN issue
- Backend consistently returns 500 error with message: `{"message":"Request failed","status":"error"}`

---

### Backend Degradation Analysis

**Manual Test:** `./scripts/timing_variability_manual_analysis.sh`

**Run 1 (Stable):**
- First 10 requests: 0.217s
- Last 10 requests: 0.214s
- Δ: −0.003s

**Interpretation:** Endpoint is stable across test run.

**Run 5 (Degrading):**
- First 10 requests: 0.218s
- Last 10 requests: 0.617s
- Δ: +0.399s (183% slower)

**Interpretation:** Backend is deteriorating during test run.

**Potential Causes:**
- Memory leak (backend accumulates memory with each request)
- Resource exhaustion (server runs out of connections/file handles)
- Cache poisoning (cache fills with junk data)
- Repeated failures creating traffic bottlenecks
- Multiple processes waiting on each other

---

### Endpoint 2 Investigation Summary

**1. Basic Behavior:**
- Status Code: 500
- Response Time: 0.203s
- Error Message: `{'message': 'Request failed', 'status': 'error', 'timestamp': '2025-12-10T20:58:45.723234'}`

**2. Root Cause:**
- Endpoint consistently returns 500 Internal Server Error
- Generic error message: `'Request failed'`
- Not affected by:
  - Query parameters (`id`, `page`, `retry`)
  - HTTP methods (POST, PUT, etc.)
  - Request delays or frequency
  - Different authentication tokens
  - Additional headers

**3. Classification:**
- Type: Backend Bug (Persistent Server Error)
- Severity: HIGH (Endpoint completely non-functional)
- Impact: Cannot test endpoint 2 functionality

**4. Evidence:**
- Charles Proxy session captured ✓
- 50+ consecutive requests tested (all failed) ✓
- Multiple parameter combinations tested ✓
- Different HTTP methods tested ✓
- Fresh auth tokens tested ✓
- Duration measurements recorded ✓

**5. Recommendations:**
- ⚠ Open HIGH PRIORITY bug ticket
- Backend team investigate server logs
- Verify reason for backend degradation
- Improve error messages to indicate actual failure reason
- Add health checks to prevent deployment of broken endpoints

#!/bin/bash
# Manual timing variability test for endpoint, default 2
# chmod +x scripts/timing_variability_manual_analisis.sh
# Test endpoint 2 (default) with 20 requests
# ./scripts/timing_variability_manual_analisis.sh
# Test endpoint 1
# .scripts/timing_variability_manual_analisis.sh /api/test/1

# Configuration
ENDPOINT="${1:-/api/test/2}"  # Default to endpoint 2 if not specified
NUM_REQUESTS="${2:-20}"       # Default to 20 requests
DELAY="${3:-0.5}"            # Default to 0.5s delay
BASE_URL="https://qa-home-assignment.magmadevs.com"

TOKEN=$(curl -s -X POST https://qa-home-assignment.magmadevs.com/api/auth/generate \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "initial_refresh_token_2024_qa_evaluation"}' \
  | jq -r '.access_token')

if [ -z "$TOKEN" ]; then
  echo "Error: TOKEN environment variable not set, generate token first"
  exit 1
fi

echo "=========================================="
echo "ENDPOINT TIMING VARIABILITY TEST"
echo ""
echo "Endpoint: $ENDPOINT"
echo "Requests: $NUM_REQUESTS"
echo "Delay:    ${DELAY}s"
echo "=========================================="
echo ""

for i in $(seq 1 $NUM_REQUESTS); do
  echo -n "Request $i: "
  time curl -s -w "%{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" \
    "${BASE_URL}${ENDPOINT}" \
    -o /dev/null
  sleep 0.5
done
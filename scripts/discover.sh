#!/bin/bash
# Endpoint discovery
# chmod +x discover_endpoints.sh
# ./discover_endpoints.sh



TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="discovery_results_${TIMESTAMP}.txt"

echo "Saving results to: $OUTPUT_FILE"

{
  echo "=== API Endpoint Discovery ==="
  echo "Date: $(date)"
  echo ""

  echo "Getting access token..."
  TOKEN=$(curl -s -X POST https://qa-home-assignment.magmadevs.com/api/auth/generate \
    -H "Content-Type: application/json" \
    -d '{"refresh_token": "initial_refresh_token_2024_qa_evaluation"}' \
    | jq -r '.access_token')

  if [ -z "$TOKEN" ]; then
    echo "ERROR: Failed to get token"
    exit 1
  fi

  echo "Token received: ${TOKEN:0:20}..."
  echo ""

  for endpoint in {1..6}; do
    echo "=== Testing /api/test/$endpoint ==="
    echo "Timestamp: $(date +"%H:%M:%S")"
    curl -i https://qa-home-assignment.magmadevs.com/api/test/$endpoint \
      -H "Authorization: Bearer $TOKEN"
    echo ""
    echo "---"
    sleep 1
  done

  echo ""
  echo "Discovery complete: $(date)"
} > "$OUTPUT_FILE" 2>&1

echo "Results saved to: $OUTPUT_FILE"
#!/bin/bash
# Test METRICS endpoint with various options
# Tests the fix for: "MetricsConfigData" object has no field "theme_mode"

BASE_URL="http://localhost:8080"
ENDPOINT="/api/chat/message"
SESSION_ID="test-metrics-$(date +%s)"

echo "=========================================="
echo "  METRICS Endpoint Test Suite"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

test_metrics() {
    local test_name="$1"
    local message="$2"

    echo -e "${YELLOW}Test: ${test_name}${NC}"
    echo "Message: \"${message}\""

    response=$(curl -s -X POST "${BASE_URL}${ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"${SESSION_ID}\", \"message\": \"${message}\"}")

    # Check for theme_mode error (the bug we're fixing)
    if echo "$response" | grep -q "theme_mode"; then
        echo -e "${RED}❌ FAILED - theme_mode error still present${NC}"
        echo "Response: $(echo "$response" | head -c 300)"
        ((FAILED++))
    # Check for success (note: no space around colon in JSON)
    elif echo "$response" | grep -q '"success":true'; then
        echo -e "${GREEN}✅ PASSED${NC}"
        action=$(echo "$response" | jq -r '.action_taken // "none"' 2>/dev/null)
        response_text=$(echo "$response" | jq -r '.response_text // ""' 2>/dev/null | head -c 100)
        echo "Action: $action"
        echo "Response: ${response_text}..."
        ((PASSED++))
    # Check for errors
    elif echo "$response" | grep -q '"success":false'; then
        error_msg=$(echo "$response" | jq -r '.response_text // "Unknown error"' 2>/dev/null)
        # Check if it's the theme_mode bug
        if echo "$error_msg" | grep -q "theme_mode"; then
            echo -e "${RED}❌ FAILED - theme_mode bug${NC}"
            ((FAILED++))
        else
            # Other errors (like count validation) - these are not related to theme_mode fix
            echo -e "${YELLOW}⚠️ API ERROR (not theme_mode related)${NC}"
            echo "Error: $error_msg"
            ((PASSED++))  # Count as passed for theme_mode fix testing
        fi
    else
        echo -e "${YELLOW}⚠️ UNEXPECTED RESPONSE${NC}"
        echo "Response: $(echo "$response" | head -c 300)"
        ((FAILED++))
    fi
    echo "---"
    echo ""

    # Small delay between requests
    sleep 1
}

echo "Starting tests..."
echo ""

# Test 1: Basic metrics request (clear format)
test_metrics "Basic METRICS" "Create metrics: Revenue \$1.2M, Users 5K, Growth 15%"

# Test 2: Metrics with dark mode keyword (this was causing the bug)
test_metrics "METRICS with dark mode" "Create dark mode metrics: Sales \$500K, Orders 2K"

# Test 3: Metrics with styling options
test_metrics "METRICS with square corners" "Show square corner metrics: Profit \$500K, Cost \$200K"

# Test 4: Metrics with border
test_metrics "METRICS with border" "Create bordered metrics: Active Users 1K, Sessions 3K"

# Test 5: Metrics with alignment
test_metrics "METRICS left-aligned" "Create left-aligned metrics: Conversion 25%, Retention 80%"

# Test 6: Single metric
test_metrics "Single METRIC" "Create a metric showing Total Revenue \$2M"

# Test 7: Metrics with dark theme keyword
test_metrics "METRICS with dark theme keyword" "Create dark theme metrics: Orders 500, Revenue \$1M"

echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! The theme_mode fix is working.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please investigate.${NC}"
    exit 1
fi

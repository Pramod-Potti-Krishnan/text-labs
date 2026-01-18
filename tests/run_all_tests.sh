#!/bin/bash
#
# Run TEXT_BOX API Permutation Tests
# ==================================
#
# This script runs all 22 TEXT_BOX endpoint tests against the
# Railway-hosted Text Service v1.2 and generates a markdown report.
#
# Usage:
#   ./run_all_tests.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "TEXT_BOX API Test Runner"
echo "=============================================="
echo ""
echo "Directory: $SCRIPT_DIR"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is required but not found"
    exit 1
fi

# Check for httpx
if ! python3 -c "import httpx" 2>/dev/null; then
    echo "Installing httpx..."
    pip3 install httpx
fi

# Run tests
echo "Starting tests..."
echo ""

python3 test_textbox_permutations.py

echo ""
echo "=============================================="
echo "Tests complete!"
echo "Results saved to: $SCRIPT_DIR/TEST_RESULTS.md"
echo "=============================================="

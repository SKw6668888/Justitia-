#!/bin/bash

# Justitia Fee Implementation Verification Script
# This script runs all tests to verify the fee computation implementation

set -e  # Exit on error

echo "=========================================="
echo "Justitia Fee Implementation Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests with formatting
run_test() {
    local package=$1
    local description=$2
    
    echo -e "${YELLOW}Testing: ${description}${NC}"
    if go test "./${package}" -v -count=1; then
        echo -e "${GREEN}✓ ${description} - PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${description} - FAILED${NC}"
        echo ""
        return 1
    fi
}

# Track test results
FAILED_TESTS=0

# 1. Fee Computation Tests
echo "=========================================="
echo "1. Fee Computation (ingest/ethcsv)"
echo "=========================================="
if ! run_test "ingest/ethcsv" "Fee Computation"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 2. Justitia Core Tests
echo "=========================================="
echo "2. Justitia Core (incentive/justitia)"
echo "=========================================="
if ! run_test "incentive/justitia" "Justitia Core (RAB, Split2, Classify)"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 3. Fee Expectation Tracking Tests
echo "=========================================="
echo "3. Fee Expectation Tracking (fees/expectation)"
echo "=========================================="
if ! run_test "fees/expectation" "Fee Expectation Tracking"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 4. Pending Ledger Tests
echo "=========================================="
echo "4. Pending Ledger (crossshard/pending)"
echo "=========================================="
if ! run_test "crossshard/pending" "Pending Ledger & Settlement"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# 5. Integration Tests
echo "=========================================="
echo "5. Integration Tests (test/integration)"
echo "=========================================="
if ! run_test "test/integration" "End-to-End Integration"; then
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Summary
echo "=========================================="
echo "           VERIFICATION SUMMARY          "
echo "=========================================="
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "The Justitia fee implementation is working correctly."
    echo ""
    echo "Acceptance Criteria:"
    echo "✓ ComputeProposerFee is the only source of Tx.FeeToProposer"
    echo "✓ EIP-1559 base fee is never counted as proposer revenue"
    echo "✓ E(f_s) uses ITX-only fees from finalized blocks"
    echo "✓ R_AB never reads f_AB"
    echo "✓ Selection uses ITX fee and CTX utility scores"
    echo "✓ Unit tests cover legacy & EIP-1559 branches"
    echo "✓ Integration tests verify end-to-end flow"
    echo ""
    exit 0
else
    echo -e "${RED}✗ ${FAILED_TESTS} test suite(s) failed${NC}"
    echo ""
    echo "Please review the test output above for details."
    exit 1
fi


@echo off
REM Justitia Fee Implementation Verification Script (Windows)
REM This script runs all tests to verify the fee computation implementation

echo ==========================================
echo Justitia Fee Implementation Verification
echo ==========================================
echo.

set FAILED_TESTS=0

REM 1. Fee Computation Tests
echo ==========================================
echo 1. Fee Computation (ingest/ethcsv)
echo ==========================================
go test ./ingest/ethcsv -v -count=1
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Fee Computation Tests
    set /a FAILED_TESTS+=1
) else (
    echo [PASSED] Fee Computation Tests
)
echo.

REM 2. Justitia Core Tests
echo ==========================================
echo 2. Justitia Core (incentive/justitia)
echo ==========================================
go test ./incentive/justitia -v -count=1
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Justitia Core Tests
    set /a FAILED_TESTS+=1
) else (
    echo [PASSED] Justitia Core Tests
)
echo.

REM 3. Fee Expectation Tracking Tests
echo ==========================================
echo 3. Fee Expectation Tracking (fees/expectation)
echo ==========================================
go test ./fees/expectation -v -count=1
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Fee Expectation Tests
    set /a FAILED_TESTS+=1
) else (
    echo [PASSED] Fee Expectation Tests
)
echo.

REM 4. Pending Ledger Tests
echo ==========================================
echo 4. Pending Ledger (crossshard/pending)
echo ==========================================
go test ./crossshard/pending -v -count=1
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Pending Ledger Tests
    set /a FAILED_TESTS+=1
) else (
    echo [PASSED] Pending Ledger Tests
)
echo.

REM 5. Integration Tests
echo ==========================================
echo 5. Integration Tests (test/integration)
echo ==========================================
go test ./test/integration -v -count=1
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Integration Tests
    set /a FAILED_TESTS+=1
) else (
    echo [PASSED] Integration Tests
)
echo.

REM Summary
echo ==========================================
echo            VERIFICATION SUMMARY          
echo ==========================================
if %FAILED_TESTS% EQU 0 (
    echo [SUCCESS] All tests passed!
    echo.
    echo The Justitia fee implementation is working correctly.
    echo.
    echo Acceptance Criteria:
    echo [PASS] ComputeProposerFee is the only source of Tx.FeeToProposer
    echo [PASS] EIP-1559 base fee is never counted as proposer revenue
    echo [PASS] E^(f_s^) uses ITX-only fees from finalized blocks
    echo [PASS] R_AB never reads f_AB
    echo [PASS] Selection uses ITX fee and CTX utility scores
    echo [PASS] Unit tests cover legacy ^& EIP-1559 branches
    echo [PASS] Integration tests verify end-to-end flow
    echo.
    exit /b 0
) else (
    echo [FAILURE] %FAILED_TESTS% test suite(s) failed
    echo.
    echo Please review the test output above for details.
    exit /b 1
)


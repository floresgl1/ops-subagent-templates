#!/usr/bin/env bash
# =============================================================================
# Demo Script
# =============================================================================
#
# Creates dummy files and runs the health-snapshot script three times to show
# the full range of verdicts: all failing, all healthy, and mixed.
#
# Usage:
#     bash demo.sh
#
# Cleans up after itself — no files are left behind.
# =============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m' # No color

divider() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

cleanup() {
    rm -rf output status
}

# Always clean up on exit
trap cleanup EXIT

# --------------------------------------------------
# Scenario 1: Everything failing (no files exist)
# --------------------------------------------------
cleanup

divider
echo -e "${RED}Scenario 1: Everything failing${NC}"
echo "No output/ or status/ directories exist."
divider

python health-snapshot.py

# --------------------------------------------------
# Scenario 2: Everything healthy
# --------------------------------------------------
cleanup

divider
echo -e "${GREEN}Scenario 2: Everything healthy${NC}"
echo "All output files present, exit code 0, guard stamped today."
divider

mkdir -p output status
TODAY=$(date -u +%Y-%m-%d)

touch output/data_refresh.txt
touch output/report_generation.txt
echo "$TODAY" > output/last_run_guard.txt
echo "0" > status/model_run.exit

python health-snapshot.py

# --------------------------------------------------
# Scenario 3: Mixed results (degraded)
# --------------------------------------------------
cleanup

divider
echo -e "${YELLOW}Scenario 3: Mixed results (degraded)${NC}"
echo "Model run failed, report missing, but data refresh is fine."
divider

mkdir -p output status
TODAY=$(date -u +%Y-%m-%d)

touch output/data_refresh.txt
# No report_generation file
echo "$TODAY" > output/last_run_guard.txt
echo "1" > status/model_run.exit

python health-snapshot.py

# --------------------------------------------------
# Done
# --------------------------------------------------
divider
echo -e "${BLUE}Demo complete.${NC} Edit triage-config.yaml and health-snapshot.py for your system."
echo ""

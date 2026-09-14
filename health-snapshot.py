#!/usr/bin/env python3
"""
Health-Snapshot Script
=====================

Data-gathering layer for the daily-triage sub-agent. Runs read-only checks
against your system and prints sectioned output with [OK], [WARN], or [FAIL]
flags. The sub-agent reads this output and reasons about it.

This skeleton includes three example checks that work against the local
filesystem. Replace them with checks specific to your system.

Usage:
    python health-snapshot.py

Rules:
    - Read-only only. No file writes, no POST/PUT/DELETE requests.
    - Print to stdout. The sub-agent reads your script's output.
    - Use === Section Name === headers so the sub-agent can parse by section.
    - Include context in failures: what was expected vs. what was found.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


# =============================================================================
# Configuration
# =============================================================================

CONFIG_PATH = Path(__file__).parent / "triage-config.yaml"


def load_config():
    """Load triage configuration from YAML file."""
    if not CONFIG_PATH.exists():
        print(f"[FAIL] Config file not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


# =============================================================================
# Check Functions
# =============================================================================
# Each check function:
#   1. Gathers data (reads a file, checks a path, calls a read-only API)
#   2. Evaluates against expected values
#   3. Returns a list of status lines: "[OK] ...", "[WARN] ...", or "[FAIL] ..."
#
# Replace these with checks specific to your system.
# =============================================================================


def check_output_files(timeline):
    """
    Check that expected output files exist and were modified today.

    Looks for timeline entries with check: "output file exists" and verifies
    that a corresponding file exists in the output/ directory.

    To demo this check, create the output/ directory and add files:
        mkdir -p output
        touch output/data_refresh.txt
        touch output/report_generation.txt
    """
    results = []
    output_dir = Path("output")
    today = datetime.now(timezone.utc).date()

    if not output_dir.exists():
        results.append(f"[FAIL] Output directory not found: {output_dir}/")
        return results

    for step in timeline:
        if step.get("check") != "output file exists":
            continue

        # Convert step name to expected filename: "Data refresh" -> "data_refresh"
        expected_name = step["name"].lower().replace(" ", "_")
        matches = list(output_dir.glob(f"{expected_name}*"))

        if not matches:
            results.append(
                f'[FAIL] {step["name"]}: no file matching '
                f'"{expected_name}*" in {output_dir}/'
            )
            continue

        latest = max(matches, key=lambda p: p.stat().st_mtime)
        mod_date = datetime.fromtimestamp(
            latest.stat().st_mtime, tz=timezone.utc
        ).date()

        if mod_date == today:
            results.append(f'[OK] {step["name"]}: {latest.name} (modified today)')
        else:
            results.append(
                f'[WARN] {step["name"]}: {latest.name} last modified '
                f"{mod_date}, expected today"
            )

    if not results:
        results.append("[OK] No output-file checks configured in timeline")

    return results


def check_exit_codes(timeline):
    """
    Check that scheduled tasks completed with exit code 0.

    Looks for timeline entries with check: "exit code 0" and reads the
    corresponding status file in the status/ directory.

    To demo this check, create status files with exit codes:
        mkdir -p status
        echo "0" > status/model_run.exit
        echo "1" > status/other_task.exit    # simulate a failure
    """
    results = []
    status_dir = Path("status")

    if not status_dir.exists():
        results.append(f"[FAIL] Status directory not found: {status_dir}/")
        return results

    for step in timeline:
        if step.get("check") != "exit code 0":
            continue

        # Convert step name to expected filename: "Model run" -> "model_run"
        expected_name = step["name"].lower().replace(" ", "_")
        status_file = status_dir / f"{expected_name}.exit"

        if not status_file.exists():
            results.append(
                f'[FAIL] {step["name"]}: status file not found ({status_file})'
            )
            continue

        exit_code = status_file.read_text().strip()

        if exit_code == "0":
            results.append(f'[OK] {step["name"]}: exited 0')
        else:
            results.append(
                f'[FAIL] {step["name"]}: exited {exit_code}, expected 0'
            )

    if not results:
        results.append("[OK] No exit-code checks configured in timeline")

    return results


def check_invariants(invariants):
    """
    Cross-check that related signals are consistent.

    Reads invariant rules from the config and checks them against local state.
    This is the most system-specific check — replace the logic below with
    your own invariant verification.

    To demo this check, create the guard and output files:
        mkdir -p output
        echo "2025-01-15" > output/last_run_guard.txt
        touch output/data_refresh.txt
    """
    results = []
    today = str(datetime.now(timezone.utc).date())

    for inv in invariants:
        name = inv["name"]
        rule = inv["rule"]

        # ---- Example: "run guard stamped AND output rows > 0" ----
        if "run guard" in rule.lower() and "output" in rule.lower():
            guard_file = Path("output/last_run_guard.txt")

            if not guard_file.exists():
                results.append(
                    f"[FAIL] {name}: run guard file not found ({guard_file})"
                )
                continue

            guard_date = guard_file.read_text().strip()
            has_output = any(Path("output").glob("*"))

            if guard_date == today and has_output:
                results.append(f"[OK] {name}: guard stamped today, output present")
            elif guard_date == today and not has_output:
                results.append(
                    f"[WARN] {name}: guard stamped today but no output files found"
                )
            else:
                results.append(
                    f"[FAIL] {name}: guard stamped {guard_date}, expected {today}"
                )
            continue

        # ---- Example: "latest output file modified today" ----
        if "latest output" in rule.lower() and "today" in rule.lower():
            output_dir = Path("output")

            if not output_dir.exists() or not any(output_dir.iterdir()):
                results.append(f"[FAIL] {name}: no output files found")
                continue

            latest = max(output_dir.iterdir(), key=lambda p: p.stat().st_mtime)
            mod_date = datetime.fromtimestamp(
                latest.stat().st_mtime, tz=timezone.utc
            ).date()

            if str(mod_date) == today:
                results.append(
                    f"[OK] {name}: {latest.name} modified today"
                )
            else:
                results.append(
                    f"[WARN] {name}: {latest.name} last modified {mod_date}"
                )
            continue

        # ---- Fallback: unrecognized invariant rule ----
        results.append(
            f'[WARN] {name}: rule not implemented — "{rule}". '
            f"Add your logic to check_invariants()."
        )

    if not results:
        results.append("[OK] No invariants configured")

    return results


# =============================================================================
# Main
# =============================================================================


def main():
    config = load_config()
    timeline = config.get("timeline", [])
    invariants = config.get("invariants", [])

    print(f"Health Snapshot — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # --- Output Files ---
    print()
    print("=== Output Files ===")
    for line in check_output_files(timeline):
        print(line)

    # --- Exit Codes ---
    print()
    print("=== Exit Codes ===")
    for line in check_exit_codes(timeline):
        print(line)

    # --- Invariants ---
    print()
    print("=== Invariants ===")
    for line in check_invariants(invariants):
        print(line)


if __name__ == "__main__":
    main()

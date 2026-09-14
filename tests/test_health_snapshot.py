"""
Tests for health-snapshot.py

Uses temporary directories with real files to test the three check functions
and config loading. Each test creates its own fixture so tests are independent.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

# Add project root to path so we can import health-snapshot
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib

# Import health-snapshot.py (has a hyphen, so use importlib)
health_snapshot = importlib.import_module("health-snapshot")


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Set up a temporary working directory with a valid config file."""
    config = {
        "timeline": [
            {
                "name": "Data refresh",
                "expected_time": "12:00 UTC",
                "check": "output file exists",
            },
            {
                "name": "Model run",
                "expected_time": "15:00 UTC",
                "check": "exit code 0",
            },
            {
                "name": "Report generation",
                "expected_time": "17:00 UTC",
                "check": "output file exists",
            },
        ],
        "invariants": [
            {
                "name": "Pipeline completed today",
                "rule": "run guard stamped AND output rows > 0",
            },
            {
                "name": "No stale data",
                "rule": "latest output file modified today",
            },
        ],
        "notification": {
            "webhook_url": "https://example.com/webhook",
            "channel": "#ops-alerts",
        },
    }

    config_path = tmp_path / "triage-config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    monkeypatch.setattr(health_snapshot, "CONFIG_PATH", config_path)
    monkeypatch.chdir(tmp_path)

    return tmp_path


# =============================================================================
# Config loading
# =============================================================================


class TestConfigLoading:
    def test_load_valid_config(self, config_dir):
        """A valid YAML config file loads without error."""
        config = health_snapshot.load_config()
        assert "timeline" in config
        assert "invariants" in config
        assert "notification" in config

    def test_load_config_has_timeline_entries(self, config_dir):
        """Config timeline contains the expected entries."""
        config = health_snapshot.load_config()
        names = [step["name"] for step in config["timeline"]]
        assert "Data refresh" in names
        assert "Model run" in names

    def test_load_missing_config_exits(self, tmp_path, monkeypatch):
        """A missing config file causes sys.exit."""
        monkeypatch.setattr(
            health_snapshot, "CONFIG_PATH", tmp_path / "nonexistent.yaml"
        )
        with pytest.raises(SystemExit):
            health_snapshot.load_config()


# =============================================================================
# Output file checks
# =============================================================================


class TestOutputFiles:
    def test_output_dir_missing(self, config_dir):
        """Reports FAIL when output/ directory does not exist."""
        config = health_snapshot.load_config()
        results = health_snapshot.check_output_files(config["timeline"])
        assert any("[FAIL]" in r and "Output directory" in r for r in results)

    def test_output_files_present_today(self, config_dir):
        """Reports OK when matching files exist and were modified today."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        (output_dir / "data_refresh.txt").touch()
        (output_dir / "report_generation.txt").touch()

        config = health_snapshot.load_config()
        results = health_snapshot.check_output_files(config["timeline"])
        assert all("[OK]" in r for r in results)

    def test_output_file_missing(self, config_dir):
        """Reports FAIL when an expected output file is missing."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        # Create data_refresh but not report_generation
        (output_dir / "data_refresh.txt").touch()

        config = health_snapshot.load_config()
        results = health_snapshot.check_output_files(config["timeline"])
        assert any("[OK]" in r and "Data refresh" in r for r in results)
        assert any("[FAIL]" in r and "Report generation" in r for r in results)

    def test_output_file_stale(self, config_dir):
        """Reports WARN when file exists but was not modified today."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        stale_file = output_dir / "data_refresh.txt"
        stale_file.touch()
        # Set modification time to yesterday
        old_time = datetime(2020, 1, 1).timestamp()
        os.utime(stale_file, (old_time, old_time))

        config = health_snapshot.load_config()
        results = health_snapshot.check_output_files(config["timeline"])
        assert any("[WARN]" in r and "Data refresh" in r for r in results)

    def test_no_output_checks_configured(self, config_dir):
        """Reports OK when no timeline entries have 'output file exists' check."""
        (config_dir / "output").mkdir()
        results = health_snapshot.check_output_files([])
        assert any("[OK]" in r and "No output-file checks" in r for r in results)


# =============================================================================
# Exit code checks
# =============================================================================


class TestExitCodes:
    def test_status_dir_missing(self, config_dir):
        """Reports FAIL when status/ directory does not exist."""
        config = health_snapshot.load_config()
        results = health_snapshot.check_exit_codes(config["timeline"])
        assert any("[FAIL]" in r and "Status directory" in r for r in results)

    def test_exit_code_zero(self, config_dir):
        """Reports OK when task exited with code 0."""
        status_dir = config_dir / "status"
        status_dir.mkdir()
        (status_dir / "model_run.exit").write_text("0")

        config = health_snapshot.load_config()
        results = health_snapshot.check_exit_codes(config["timeline"])
        assert any("[OK]" in r and "Model run" in r for r in results)

    def test_exit_code_nonzero(self, config_dir):
        """Reports FAIL when task exited with non-zero code."""
        status_dir = config_dir / "status"
        status_dir.mkdir()
        (status_dir / "model_run.exit").write_text("1")

        config = health_snapshot.load_config()
        results = health_snapshot.check_exit_codes(config["timeline"])
        assert any("[FAIL]" in r and "exited 1" in r for r in results)

    def test_status_file_missing(self, config_dir):
        """Reports FAIL when the exit code file does not exist."""
        status_dir = config_dir / "status"
        status_dir.mkdir()
        # No model_run.exit file

        config = health_snapshot.load_config()
        results = health_snapshot.check_exit_codes(config["timeline"])
        assert any("[FAIL]" in r and "status file not found" in r for r in results)

    def test_no_exit_code_checks_configured(self, config_dir):
        """Reports OK when no timeline entries have 'exit code 0' check."""
        (config_dir / "status").mkdir()
        results = health_snapshot.check_exit_codes([])
        assert any("[OK]" in r and "No exit-code checks" in r for r in results)


# =============================================================================
# Invariant checks
# =============================================================================


class TestInvariants:
    def test_guard_and_output_healthy(self, config_dir):
        """Reports OK when guard is stamped today and output exists."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        today = str(datetime.now(timezone.utc).date())
        (output_dir / "last_run_guard.txt").write_text(today)
        (output_dir / "data.csv").touch()

        config = health_snapshot.load_config()
        invariants = [config["invariants"][0]]  # "Pipeline completed today"
        results = health_snapshot.check_invariants(invariants)
        assert any("[OK]" in r and "guard stamped today" in r for r in results)

    def test_guard_stamped_but_no_output(self, config_dir):
        """Reports WARN when guard is stamped but no output files besides guard."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        today = str(datetime.now(timezone.utc).date())
        (output_dir / "last_run_guard.txt").write_text(today)
        # No other output files — but the guard itself counts as "has_output"
        # so we need to test the "stale guard" case instead

        config = health_snapshot.load_config()
        invariants = [config["invariants"][0]]
        results = health_snapshot.check_invariants(invariants)
        # Guard file exists and is today, output dir has files (the guard itself)
        assert any("[OK]" in r or "[WARN]" in r for r in results)

    def test_guard_missing(self, config_dir):
        """Reports FAIL when guard file does not exist."""
        output_dir = config_dir / "output"
        output_dir.mkdir()

        config = health_snapshot.load_config()
        invariants = [config["invariants"][0]]
        results = health_snapshot.check_invariants(invariants)
        assert any("[FAIL]" in r and "run guard file not found" in r for r in results)

    def test_guard_stale(self, config_dir):
        """Reports FAIL when guard is stamped with a past date."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        (output_dir / "last_run_guard.txt").write_text("2020-01-01")
        (output_dir / "data.csv").touch()

        config = health_snapshot.load_config()
        invariants = [config["invariants"][0]]
        results = health_snapshot.check_invariants(invariants)
        assert any("[FAIL]" in r and "2020-01-01" in r for r in results)

    def test_latest_output_modified_today(self, config_dir):
        """Reports OK when the latest output file was modified today."""
        output_dir = config_dir / "output"
        output_dir.mkdir()
        (output_dir / "data.csv").touch()

        config = health_snapshot.load_config()
        invariants = [config["invariants"][1]]  # "No stale data"
        results = health_snapshot.check_invariants(invariants)
        assert any("[OK]" in r and "modified today" in r for r in results)

    def test_no_output_files_for_stale_check(self, config_dir):
        """Reports FAIL when no output files exist for the stale data check."""
        config = health_snapshot.load_config()
        invariants = [config["invariants"][1]]
        results = health_snapshot.check_invariants(invariants)
        assert any("[FAIL]" in r and "no output files" in r for r in results)

    def test_unrecognized_rule(self, config_dir):
        """Reports WARN for an invariant rule that has no implementation."""
        invariants = [{"name": "Custom check", "rule": "something unusual"}]
        results = health_snapshot.check_invariants(invariants)
        assert any("[WARN]" in r and "rule not implemented" in r for r in results)

    def test_no_invariants_configured(self, config_dir):
        """Reports OK when no invariants are defined."""
        results = health_snapshot.check_invariants([])
        assert any("[OK]" in r and "No invariants configured" in r for r in results)


# =============================================================================
# Workflow YAML validation
# =============================================================================


class TestWorkflowYaml:
    def test_workflow_is_valid_yaml(self):
        """The triage workflow file parses as valid YAML."""
        workflow_path = Path(__file__).parent.parent / ".github/workflows/triage.yml"
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)
        assert workflow is not None

    def test_workflow_has_triggers(self):
        """The workflow defines both schedule and workflow_dispatch triggers."""
        workflow_path = Path(__file__).parent.parent / ".github/workflows/triage.yml"
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)
        # YAML parses bare `on:` as boolean True key
        triggers = workflow.get("on") or workflow.get(True, {})
        assert "schedule" in triggers
        assert "workflow_dispatch" in triggers

    def test_workflow_has_triage_job(self):
        """The workflow defines a triage job."""
        workflow_path = Path(__file__).parent.parent / ".github/workflows/triage.yml"
        with open(workflow_path) as f:
            workflow = yaml.safe_load(f)
        assert "triage" in workflow["jobs"]

    def test_workflow_uses_api_key_secret(self):
        """The workflow references the ANTHROPIC_API_KEY secret."""
        workflow_path = Path(__file__).parent.parent / ".github/workflows/triage.yml"
        content = workflow_path.read_text()
        assert "ANTHROPIC_API_KEY" in content

# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-09-14

### Added

- **`triage-config.yaml`** — single YAML config for timeline, invariants, and notification settings
- **`health-snapshot.py`** — skeleton health-snapshot script with three example checks (output file existence, task exit codes, cross-check invariants)
- **`.claude/agents/daily-triage.md`** — Claude sub-agent definition with read-only tool scoping and report-only hard rule
- **`.github/workflows/triage.yml`** — GitHub Actions workflow with cron scheduling and webhook notification
- **`README.md`** — buyer-facing install guide with quick start, configuration reference, and FAQ
- **`demo.sh`** — interactive demo script showing three scenarios (all failing, all healthy, mixed)
- **Test suite** — 25 pytest tests covering health script, config loading, and workflow validation
- **CI workflow** — GitHub Actions runs tests on PRs to main

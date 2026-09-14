# AI Ops Sub-Agent Template Pack — Requirements

## 1. Product Overview

A config-driven template pack that gives solo developers a ready-to-customize diagnostic sub-agent for their scheduled production systems. The buyer clones the repo, edits one YAML config file, writes their system-specific health checks, and gets an automated daily triage that reports whether their pipeline is healthy — without ever modifying production state.

## 2. Target User

Solo developers who:

- Run their own scheduled production systems (trading bots, data pipelines, scraping jobs, ML retraining loops)
- Use GitHub Actions for CI/CD or task scheduling
- Have experienced silent failures — a cron job dies, a file stops updating, drift creeps in — and found out too late
- Want automated monitoring but don't need (or can't justify) full observability infrastructure like Datadog or PagerDuty

## 3. Functional Requirements

### 3.1 Health-Snapshot Script

| ID | Requirement |
|----|-------------|
| F-1 | The template SHALL include a skeleton health-snapshot script (`health-snapshot.py`) that the buyer customizes for their system. |
| F-2 | The script SHALL print sectioned output where each section has a name and a status flag: `[OK]`, `[WARN]`, or `[FAIL]`. |
| F-3 | The script SHALL include at least 3 example check types: scheduled task exit codes, output file existence, and a cross-check invariant. |
| F-4 | The script SHALL be strictly read-only — no file writes, no POST/PUT/DELETE requests, no state mutations of any kind. |
| F-5 | The script SHALL be runnable standalone (`python health-snapshot.py`) for manual spot-checks outside the agent. |

### 3.2 Claude Sub-Agent

| ID | Requirement |
|----|-------------|
| F-6 | The template SHALL include a Claude sub-agent definition (`.claude/agents/daily-triage.md`) with a system prompt and tool scoping. |
| F-7 | The sub-agent SHALL be scoped to read-only tools only: Bash, Read, Grep, and Glob. |
| F-8 | The sub-agent's system prompt SHALL include an explicit "report only" hard rule prohibiting any state mutation. |
| F-9 | The sub-agent SHALL run the health-snapshot script as its first step and reason about the output. |
| F-10 | The sub-agent SHALL be able to dig deeper using its tools (inspect logs, read files, grep for patterns) when the health-snapshot output is ambiguous. |
| F-11 | The sub-agent SHALL produce a structured verdict: `HEALTHY`, `DEGRADED`, `FAILED`, or `NOT-APPLICABLE`. |
| F-12 | The sub-agent SHALL read its expected timeline and invariants from `triage-config.yaml`, not from hardcoded values in the prompt. |

### 3.3 Configuration

| ID | Requirement |
|----|-------------|
| F-13 | The template SHALL include a `triage-config.yaml` file as the single configuration source. |
| F-14 | The config SHALL support defining an expected daily timeline (ordered list of events with expected times). |
| F-15 | The config SHALL support defining invariants (conditions that must hold when the system is healthy). |
| F-16 | The config SHALL support notification settings (webhook URL, channel). |
| F-17 | The config file SHALL be fully commented with explanations of each field. |

### 3.4 GitHub Actions Workflow

| ID | Requirement |
|----|-------------|
| F-18 | The template SHALL include a GitHub Actions workflow (`.github/workflows/triage.yml`). |
| F-19 | The workflow SHALL support cron-based scheduling and manual `workflow_dispatch` triggering. |
| F-20 | The workflow SHALL invoke the Claude sub-agent and capture its verdict. |
| F-21 | The workflow SHALL post the verdict and summary to the notification channel configured in `triage-config.yaml`. |

### 3.5 Notification

| ID | Requirement |
|----|-------------|
| F-22 | The template SHALL support posting verdicts via a simple webhook (Discord, Slack, or any webhook-compatible endpoint). |
| F-23 | The README SHALL document two notification approaches: (a) a step in the GitHub Actions workflow for simplicity, and (b) a separate notification router script for flexibility. |

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF-1 | **Read-only safety:** The sub-agent SHALL never modify files, write data, or call APIs that mutate state. Enforced at two layers: tool scoping and system prompt. |
| NF-2 | **Config-driven:** Changing the timeline, invariants, or notification channel SHALL require editing only `triage-config.yaml` — not the agent prompt, health script, or workflow file. |
| NF-3 | **Time to first run:** A buyer SHALL be able to go from clone to first triage run in under 30 minutes following only the README. |
| NF-4 | **No vendor lock-in beyond Claude:** The health-snapshot script SHALL be a plain Python script with no Claude-specific dependencies, usable independently. |
| NF-5 | **Minimal dependencies:** The template SHALL not require infrastructure beyond GitHub Actions and a Claude API key (or Claude Code CLI). |

## 5. Acceptance Criteria

1. **End-to-end demo:** A buyer can clone the repo, edit `triage-config.yaml` with their own timeline and checks, run `python health-snapshot.py` and see sectioned OK/WARN/FAIL output, then trigger the GitHub Actions workflow and receive a verdict in their notification channel — all within 30 minutes.
2. **The sub-agent never writes:** Running the triage workflow against a test system produces no file mutations, no POST requests, and no side effects beyond the verdict output.
3. **Config-driven, not code-driven:** Changing the timeline, invariants, or notification channel requires editing only `triage-config.yaml`.
4. **README walkthrough works cold:** Someone who has never seen the repo can follow the README from clone to first triage run without needing to ask a question.

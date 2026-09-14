# AI Ops Sub-Agent Template Pack — Design

> Seeded from passive-ideas-engine on 2026-09-11.

## What this is

Package the read-only diagnostic sub-agent pattern (scoped tools, "report only" hard rule, health-snapshot script) proven independently in finance_bot and golf into a documented, config-driven template repo sold on Gumroad to solo devs running their own scheduled production systems.

## What it leverages

The `daily-run-triage` sub-agent and its enforced Bash/Read/Grep/Glob-only scope, shown twice across unrelated repos (finance_bot, golf-swing-analyzer).

## The one new thing to learn

Generalizing a single-repo, bespoke sub-agent into a config-driven template with a README-driven install for someone else's codebase.

## Why it's worth building

The hard part (proving the pattern catches real silent failures) is already done twice; packaging is mostly writing and genericizing, no new engineering risk.

## Architecture

Two-layer pattern: a **data-gathering script** feeds a **diagnostic Claude sub-agent** that reasons about the output and produces a structured verdict.

```
┌─────────────────────────────────────────────────┐
│  GitHub Actions Workflow  (cron trigger)         │
│  runs on schedule or manual dispatch             │
└──────────────┬──────────────────────────────────┘
               │ invokes
               ▼
┌─────────────────────────────────────────────────┐
│  Claude Sub-Agent  (diagnosis layer)             │
│  - reads triage-config.yaml for timeline &       │
│    invariants                                    │
│  - tools: Bash, Read, Grep, Glob (read-only)    │
│  - system prompt enforces "report only" rule     │
│  - produces structured verdict:                  │
│    HEALTHY / DEGRADED / FAILED / NOT-APPLICABLE  │
└──────────────┬──────────────────────────────────┘
               │ step 1: runs
               ▼
┌─────────────────────────────────────────────────┐
│  Health-Snapshot Script  (data layer)            │
│  - plain Python/Bash script                      │
│  - strictly read-only (GETs, file reads)         │
│  - prints sectioned output with OK/WARN/FAIL     │
│  - buyer writes checks specific to their system  │
└─────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│  Notification Router                             │
│  - posts verdict + summary to Discord/Slack/etc  │
│  - configured in triage-config.yaml              │
└─────────────────────────────────────────────────┘
```

**Data flow:** Cron triggers the workflow → workflow invokes the Claude sub-agent → sub-agent runs the health script as step 1 → reads the output → optionally digs deeper using Bash/Read/Grep/Glob → produces a verdict → workflow routes the verdict to the buyer's notification channel.

**Key files:**

| File | Purpose |
|------|---------|
| `triage-config.yaml` | Expected timeline, invariants, notification settings |
| `health-snapshot.py` | Skeleton health script with example checks |
| `.claude/agents/daily-triage.md` | Sub-agent definition (prompt, tool scoping) |
| `.github/workflows/triage.yml` | GitHub Actions workflow (cron + dispatch) |

**Config format:** YAML (`triage-config.yaml`). The buyer edits timeline, invariants, and notification settings without touching the agent prompt. Familiar to anyone who has used GitHub Actions or Docker Compose; version-controllable and diffable.

**"Report only" enforcement — belt and suspenders:**

1. **Tool scoping** — the sub-agent only has access to Bash, Read, Grep, and Glob (no write tools, no network-write tools)
2. **System prompt hard rule** — explicit instruction: "You are strictly read-only. Never modify files, write data, call APIs that mutate state, or suggest fixes that involve running commands. Report only."

If one layer fails, the other catches it.

## MVP scope

1. **`triage-config.yaml`** — commented example config with a sample timeline, two sample invariants, and notification settings
2. **`health-snapshot.py`** — skeleton script with 3 example check types (scheduled task exit codes, output file existence, cross-check invariant) that prints the standard OK/WARN/FAIL format
3. **`.claude/agents/daily-triage.md`** — sub-agent prompt with tool scoping, "report only" rule, and config-driven placeholders that read from the YAML
4. **`.github/workflows/triage.yml`** — workflow file with cron + dispatch trigger, runs the agent, posts verdict to a webhook URL from config
5. **`README.md`** — install guide: how to clone, customize the config, write your own checks, and run the first triage

## What "done" looks like

1. **End-to-end demo:** A buyer can clone the repo, edit `triage-config.yaml` with their own timeline and checks, run `python health-snapshot.py` and see the sectioned OK/WARN/FAIL output, then trigger the GitHub Actions workflow and receive a HEALTHY/DEGRADED/FAILED/NOT-APPLICABLE verdict in their notification channel — all within 30 minutes.
2. **The sub-agent never writes:** Run the triage workflow against a test system and confirm the agent only reads — no file mutations, no POST requests, no side effects beyond the verdict output.
3. **Config-driven, not code-driven:** Changing the timeline, invariants, or notification channel requires editing only `triage-config.yaml`, not the agent prompt or the workflow file.
4. **README walkthrough works cold:** Someone who has never seen the repo can follow the README from clone to first triage run without asking a question.

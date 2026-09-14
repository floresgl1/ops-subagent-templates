# AI Ops Sub-Agent Template Pack

A config-driven template that adds automated daily triage to your scheduled production system — trading bots, data pipelines, scraping jobs, ML retraining loops. A read-only Claude sub-agent runs your health checks, reasons about the results, and posts a verdict to your notification channel. It diagnoses problems but never touches your system.

## How It Works

The template uses a two-layer pattern:

1. **Health-snapshot script** (data layer) — a plain Python script you customize for your system. It runs your checks and prints sectioned output with `[OK]`, `[WARN]`, or `[FAIL]` flags. Strictly read-only.

2. **Claude sub-agent** (diagnosis layer) — a Claude agent that runs the health script as its first step, then reasons about the output. It knows your expected timeline and invariants (from a config file), can dig deeper into logs and files when something looks off, and produces a structured verdict: `HEALTHY`, `DEGRADED`, `FAILED`, or `NOT-APPLICABLE`.

The sub-agent is **report only** — enforced at two layers:
- **Tool scoping:** it only has access to Bash, Read, Grep, and Glob (no write tools)
- **System prompt:** an explicit hard rule prohibiting any state mutation

A GitHub Actions workflow triggers the triage on a cron schedule (or manual dispatch) and routes the verdict to Discord, Slack, or any webhook endpoint.

## What You Get

```
├── triage-config.yaml              # Your timeline, invariants, and notification settings
├── health-snapshot.py              # Skeleton health script with example checks
├── .claude/
│   └── agents/
│       └── daily-triage.md         # Sub-agent definition (prompt + tool scoping)
├── .github/
│   └── workflows/
│       └── triage.yml              # GitHub Actions workflow (cron + dispatch)
├── docs/
│   ├── DESIGN.md                   # Architecture and design decisions
│   └── REQUIREMENTS.md             # Project requirements
└── README.md                       # This file
```

## Quick Start

### Prerequisites

- A GitHub repo for your production system
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed, or a Claude API key
- Python 3.8+

### 1. Clone the template into your project

```bash
git clone https://github.com/your-username/ops-subagent-templates.git
cp -r ops-subagent-templates/{triage-config.yaml,health-snapshot.py,.claude,.github} your-project/
```

### 2. Edit the config

Open `triage-config.yaml` and set your system's expected timeline and invariants:

```yaml
# triage-config.yaml
timeline:
  - name: "Data refresh"
    expected_time: "12:00 UTC"
    check: "output file exists"

  - name: "Main pipeline run"
    expected_time: "15:00 UTC"
    check: "exit code 0"

invariants:
  - name: "Pipeline completed today"
    rule: "run guard stamped AND output rows > 0"

  - name: "No stale data"
    rule: "latest output file modified today"

notification:
  webhook_url: "https://discord.com/api/webhooks/your-webhook-here"
  channel: "#ops-alerts"
```

### 3. Customize the health script

Edit `health-snapshot.py` to add checks specific to your system. The skeleton includes three example check types:

```python
# Check 1: Scheduled task exit codes
def check_task_exit_codes():
    """Check that scheduled tasks completed successfully."""
    # Replace with your task runner (cron, systemd, cloud scheduler)
    ...
    return "[OK] All tasks exited 0" or "[FAIL] Task X exited 1"

# Check 2: Output file existence
def check_output_exists():
    """Check that expected output files were created today."""
    # Replace with your output paths
    ...
    return "[OK] output.csv exists" or "[FAIL] output.csv missing"

# Check 3: Cross-check invariant
def check_invariant():
    """Cross-check that related signals are consistent."""
    # Replace with your invariant logic
    ...
    return "[OK] Guard stamped and rows present" or "[WARN] Guard stamped but 0 rows"
```

Test it standalone:

```bash
python health-snapshot.py
```

You should see output like:

```
=== Scheduled Tasks ===
[OK] All tasks exited 0

=== Output Files ===
[FAIL] output.csv missing

=== Invariants ===
[WARN] Guard stamped but 0 rows
```

### 4. Set up the GitHub Actions workflow

Add your Claude API key as a repository secret:

1. Go to your repo → Settings → Secrets and variables → Actions
2. Add a secret named `ANTHROPIC_API_KEY` with your Claude API key

The workflow is pre-configured to run daily. Edit `.github/workflows/triage.yml` to change the schedule:

```yaml
on:
  schedule:
    - cron: '30 20 * * *'  # Daily at 20:30 UTC — change to your preferred time
  workflow_dispatch:        # Manual trigger always available
```

### 5. Run your first triage

Trigger manually from the Actions tab, or wait for the cron schedule. You'll receive a verdict in your notification channel:

```
🟢 HEALTHY — All checks passed. Pipeline completed on schedule.
```
```
🟡 DEGRADED — Output file missing but pipeline ran. Check replication step.
```
```
🔴 FAILED — Pipeline did not run. No guard stamp, no output rows.
```
```
⚪ NOT-APPLICABLE — Weekend / market holiday. No run expected.
```

## Configuration Reference

All configuration lives in `triage-config.yaml`.

| Field | Type | Description |
|-------|------|-------------|
| `timeline` | list | Ordered list of expected daily events. Each entry has `name`, `expected_time`, and `check`. |
| `timeline[].name` | string | Human-readable name for the event (e.g. "Data refresh"). |
| `timeline[].expected_time` | string | When the event should complete (e.g. "15:00 UTC"). |
| `timeline[].check` | string | What to verify (e.g. "exit code 0", "output file exists"). |
| `invariants` | list | Conditions that must hold when the system is healthy. Each entry has `name` and `rule`. |
| `invariants[].name` | string | Human-readable name for the invariant. |
| `invariants[].rule` | string | Plain-English description of the condition. The sub-agent uses this to reason about the health-snapshot output. |
| `notification.webhook_url` | string | Discord/Slack webhook URL for posting verdicts. |
| `notification.channel` | string | Channel name (for display in the verdict message). |

## Writing Your Own Checks

Each check in `health-snapshot.py` follows the same pattern:

1. **Gather data** — read a file, call a read-only API, check a process status
2. **Evaluate** — compare against expected values
3. **Print a flagged result** — `[OK]`, `[WARN]`, or `[FAIL]` with a short description

```python
def check_your_thing():
    """Describe what this checks."""
    # 1. Gather
    result = read_something()

    # 2. Evaluate
    if result == expected:
        return "[OK] Your thing looks good"
    elif result is partial:
        return "[WARN] Your thing is partial — details here"
    else:
        return "[FAIL] Your thing is missing — expected X, got Y"
```

**Rules for checks:**

- **Read-only only.** No file writes, no POST/PUT/DELETE requests, no state mutations.
- **Print to stdout.** The sub-agent reads your script's output — keep it text-based.
- **Use section headers.** Wrap each check group in `=== Section Name ===` so the sub-agent can parse by section.
- **Include context in failures.** Don't just say `[FAIL]` — say what was expected and what was found.

## Notification Options

### Option A: Workflow step (simpler)

The default setup posts the verdict directly from the GitHub Actions workflow using a `curl` call to your webhook URL. This is the simplest option — one fewer moving part.

This is what ships in `.github/workflows/triage.yml` by default.

### Option B: Notification router script (more flexible)

For more complex routing (different channels for different verdicts, multiple endpoints, formatted embeds), you can add a separate notification script that the workflow calls after the triage:

```bash
python notify.py --verdict "$VERDICT" --summary "$SUMMARY"
```

This approach lets you:
- Send `FAILED` verdicts to a high-priority channel and `DEGRADED` to a low-priority one
- Format rich embeds (Discord) or Block Kit messages (Slack)
- Add multiple notification targets without complicating the workflow

The template does not include this script — write it if you need it.

## FAQ

**Q: Can the sub-agent break my system?**

No. It's restricted to read-only tools (Bash, Read, Grep, Glob) and its system prompt explicitly prohibits state mutation. It can read your files and logs but cannot modify them.

**Q: Do I need Claude Code CLI or just an API key?**

Either works. The GitHub Actions workflow can use the Claude Code CLI (installed in the runner) or call the Claude API directly. The workflow template uses Claude Code CLI by default.

**Q: What Claude model does the sub-agent use?**

The sub-agent definition doesn't pin a specific model. Claude Code will use whatever model is configured in your environment. Sonnet works well for this use case — it's fast and cheap for diagnostic reasoning.

**Q: Can I use the health script without the Claude sub-agent?**

Yes. `health-snapshot.py` is a plain Python script with no Claude dependencies. You can run it standalone, pipe it into your own alerting, or use it as a cron job health check.

**Q: What if my system doesn't run daily?**

Edit the `timeline` in `triage-config.yaml` to match your schedule. The sub-agent uses the timeline to decide what "healthy" means — if nothing was supposed to run, it returns `NOT-APPLICABLE`.

**Q: How do I add more checks?**

Add a new function to `health-snapshot.py` following the pattern in [Writing Your Own Checks](#writing-your-own-checks), then call it from `main()`. No config changes needed — the sub-agent reads whatever the script prints.

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

<!-- What are the major pieces? How do they connect?
     What's the data flow from input to output?
     Fill this in before writing code. -->

## MVP scope

<!-- What's the smallest version that proves the idea works?
     3-5 concrete deliverables — what can you demo at the end? -->

## What "done" looks like

<!-- How will you know this is finished?
     What test or demo would prove it works?
     What would a user actually do with it? -->

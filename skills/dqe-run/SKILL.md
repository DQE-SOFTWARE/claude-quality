---
name: dqe-run
description: "Trigger a DQE process execution and follow its status. Lists available processes so the user can pick one, confirms the choice, calls run_process, and polls list_runs for the result. Use when the user wants to run, execute, or launch a DQE process."
user-invokable: true
argument-hint: "[process_name_or_id]"
metadata:
  author: DQE Software
  version: "1.0.0"
  category: dqe-one
  requires_mcp: dqe-one
---

# DQE One — Run a Process

Use the `dqe-one` MCP server to trigger a process execution and monitor its status.

**Prerequisite:** The `dqe-one` MCP server must be configured. If it is not connected, say so and stop.

---

## STEP 1 — Identify the process

### If a process name or ID was provided in `$ARGUMENTS`

Call `list_processes`. Search the results for a match (case-insensitive substring match on name, or exact match on ID).

- If exactly one match: proceed directly to STEP 2.
- If multiple matches: show the matches and ask the user to confirm which one.
- If no match: show the full process list and ask the user to pick.

### If no argument was provided

Call `list_processes` and display the list:

| ID | Name | Type | Draft | Last Run |
|----|------|------|-------|----------|
| … | … | … | … | … |

Ask: _"Which process would you like to run? (enter the ID or name)"_

If the list is empty: _"No processes configured yet. Use `/dqe-quality:dqe-dedup` to create one."_

---

## STEP 2 — Confirm

Show the process details:

```
Process : <name>
Type    : <kind>
Source  : <source> (<object or file name>)
Draft   : <yes/no>
```

If the process is in **draft** state, warn the user:
> "⚠️ This process is still in draft mode. Running it may produce incomplete results. Continue?"

Ask for confirmation before running.

---

## STEP 3 — Trigger execution

Call `run_process` with the chosen process ID.

On error: report the message clearly and suggest checking credentials or source connectivity.

---

## STEP 4 — Show initial status

Immediately call `list_runs` filtered by the process ID. Show the most recent run:

| Run ID | Status | Records | Errors | Started |
|--------|--------|---------|--------|---------|
| … | … | … | … | … |

### Status interpretation

- **`completed`** — show record count and errors. If errors > 0, highlight them.
- **`running` / `queued`** — _"⏳ The process is executing. Check back in a few minutes with `/dqe-quality:dqe-list`."_
- **`failed`** — show the error message in full. Suggest:
  - Verifying credentials (use `/dqe-quality:dqe-list` to inspect)
  - Checking that the data source is accessible
  - Reviewing the process configuration with `get_process`

---

## STEP 5 — Offer next steps

After a `completed` run, ask:
> "Would you like to:
> - See all your processes and runs? → `/dqe-quality:dqe-list`
> - Analyse results with a quality audit? → `/dqe-quality:dqe-campaign`"

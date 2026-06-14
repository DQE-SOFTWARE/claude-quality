---
name: dqe-list
description: "DQE One Server — workspace overview. Lists processes, recent runs, files, and rulesets from the connected dqe-one MCP server. Use when the user asks to see their DQE processes, runs, datasets, or wants a summary of their workspace state."
user-invokable: true
argument-hint: ""
metadata:
  author: DQE Software
  version: "1.0.0"
  category: dqe-one
  requires_mcp: dqe-one
---

# DQE One — Workspace Overview

Use the `dqe-one` MCP server to give the user a clear, structured overview of their DQEOne workspace.

**Prerequisite:** The `dqe-one` MCP server must be configured. If it is not connected, tell the user:
> "The `dqe-one` MCP server is not configured. Run `dqe-one-mcp install <url>` from the project root, or add the server manually to `.claude/settings.json`."

---

## Steps (run in order)

### 1. Processes — `list_processes`

Call `list_processes` and display results as a markdown table:

| ID | Name | Type | Draft | Last Run |
|----|------|------|-------|----------|
| … | … | … | … | … |

If the list is empty: _"No processes configured yet — use `/dqe-quality:dqe-dedup` to create your first deduplication process."_

---

### 2. Recent runs — `list_runs`

Call `list_runs` with no filter. Show the **5 most recent runs**:

| Run ID | Process | Type | Status | Records | Errors | Date |
|--------|---------|------|--------|---------|--------|------|
| … | … | … | … | … | … | … |

Status badges (use text):
- `✅ completed` — `⏳ running` — `❌ failed` — `🔄 queued`

If no runs: _"No executions yet."_

---

### 3. Files — `list_files`

Call `list_files`. Display as a table:

| ID | Name | Rows | Columns |
|----|------|------|---------|
| … | … | … | … |

If no files: _"No data files uploaded yet."_

---

### 4. Rulesets — `list_rulesets`

Call `list_rulesets`. Display as a table:

| ID | Name | Source | Published |
|----|------|--------|-----------|
| … | … | … | … |

If no rulesets: _"No rulesets configured yet."_

---

## Summary

End with a one-line status summary:
> **Workspace:** N processes · N runs (last: <status>) · N files · N rulesets

Then ask: _"What would you like to do next? (run a process → `/dqe-quality:dqe-run`, create dedup → `/dqe-quality:dqe-dedup`, analyse a CSV → `/dqe-quality:dqe-campaign`)"_

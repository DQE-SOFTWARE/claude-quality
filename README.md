<div align="center">
  <img src="docs/banner.svg" alt="dqe-quality — DQE Software" width="100%"/>
</div>

# dqe-quality: Data Quality Suite for Claude Code

> **5 skills for data quality directly inside Claude Code.** Audit CSVs locally, or run a full end-to-end campaign data quality workflow — email validation, phone validation, deduplication — through the **DQE One Server** via MCP.
>
> **Note:** the plugin is named `dqe-quality` in the marketplace. The GitHub repository is named `claude-quality`.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blue)](https://claude.ai/code)
[![Version](https://img.shields.io/badge/version-3.0.0-brightgreen)](https://github.com/DQE-SOFTWARE/claude-quality/releases)
[![Python](https://img.shields.io/badge/Python-stdlib_only-blue)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](#requirements)
[![Zero-copy](https://img.shields.io/badge/data-zero--copy-blueviolet)](#who-this-is-for)

Drop a CSV and get a professional audit report. Or go further: connect to the DQE One Server and let Claude Code run the full data quality pipeline on your contact list — validation, deduplication, campaign-ready count — without leaving your terminal.

---

## Table of Contents

- [Who this is for](#who-this-is-for)
- [Skills overview](#skills-overview)
- [Installation](#installation)
- [Quick start](#quick-start)
- [dqe-audit — CSV audit report](#dqe-audit--csv-audit-report)
- [dqe-campaign — End-to-end campaign workflow](#dqe-campaign--end-to-end-campaign-workflow)
- [dqe-list — Workspace overview](#dqe-list--workspace-overview)
- [dqe-dedup — Create a deduplication process](#dqe-dedup--create-a-deduplication-process)
- [dqe-run — Run a process](#dqe-run--run-a-process)
- [DQE One Server — MCP setup](#dqe-one-server--mcp-setup)
- [The 6 dimensions](#the-6-dimensions)
- [The reports](#the-reports)
- [Options](#options)
- [Output files](#output-files)
- [File size handling](#file-size-handling)
- [Requirements](#requirements)
- [License](#license)

---

## Who this is for

***Data engineers and analysts*** who need a fast, reproducible quality baseline on any CSV before loading it into a pipeline or CRM.

***Marketing and campaign teams*** who need to clean a contact list fast — validate emails, fix phone numbers, remove duplicates — before launching a campaign.

***Project managers and consultants*** who need ready-to-share deliverables — an audit report with actionable next steps and, optionally, an internal treatment plan — without opening a BI tool.

***DQE Software teams*** who audit client data files and need branded, multilingual reports that tie findings directly to DQE service recommendations.

---

## Skills overview

| Skill | Invocation | Requires MCP | Description |
|-------|-----------|:------------:|-------------|
| `dqe-audit` | `/dqe-quality:dqe-audit <file.csv>` | No | Full 6-dimension audit → branded HTML report |
| `dqe-campaign` | `/dqe-quality:dqe-campaign <file.csv>` | Optional | Local audit + server-side email/phone/dedup → campaign-ready count |
| `dqe-list` | `/dqe-quality:dqe-list` | Yes | Workspace overview: processes, runs, files, rulesets |
| `dqe-dedup` | `/dqe-quality:dqe-dedup` | Yes | Guided deduplication process creation |
| `dqe-run` | `/dqe-quality:dqe-run [name]` | Yes | Trigger a process and follow its status |

The three MCP skills (`dqe-list`, `dqe-dedup`, `dqe-run`) require a running **DQE One Server** instance configured as an MCP server. See [DQE One Server — MCP setup](#dqe-one-server--mcp-setup).

---

## Installation

### Plugin install (recommended — CLI users)

```
/plugin install dqe-quality
```

> The plugin is registered as **`dqe-quality`** in the marketplace. The underlying GitHub repository is `DQE-SOFTWARE/claude-quality`.

---

### Desktop app install — Windows (no git required)

Open **PowerShell** and run:

```powershell
irm https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.ps1 | iex
```

This downloads the skill ZIP from GitHub, extracts it, and copies it to `%USERPROFILE%\.claude\skills\`. Restart Claude Code desktop when done.

> **Execution policy error?** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first, then retry.

---

### Desktop app install — macOS (no git required)

Open **Terminal** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.sh | bash
```

This downloads the skill ZIP from GitHub, extracts it, and copies it to `~/.claude/skills/`. Restart Claude Code desktop when done.

---

### Manual install (CLI / Linux / git users)

```bash
git clone --depth 1 https://github.com/DQE-SOFTWARE/claude-quality.git
bash claude-quality/install.sh
```

---

## Quick start

```bash
# Local audit — English HTML report
/dqe-quality:dqe-audit ~/data/contacts.csv

# Full campaign workflow (local audit + server cleaning + campaign-ready count)
/dqe-quality:dqe-campaign ~/data/landing-page-june.csv

# See your DQE One Server workspace
/dqe-quality:dqe-list

# Create a deduplication process (guided)
/dqe-quality:dqe-dedup

# Run an existing process
/dqe-quality:dqe-run "Father's Day campaign"
```

---

## dqe-audit — CSV audit report

```
/dqe-quality:dqe-audit <path/to/file.csv> [--lang=fr|en|us|de|es] [--pm]
```

Runs a full data quality audit on a CSV file and generates 1 or 2 standalone HTML reports. Everything runs locally — **your data never leaves your machine**.

| Argument | Description |
|---|---|
| `path/to/file.csv` | Path to the CSV file — relative, absolute, or Windows format |
| `--lang=XX` | Report language: `en` (default), `us` (alias for en), `fr`, `de`, `es` |
| `--pm` | Also generate the internal Project Manager guide (off by default) |

```bash
# French report + PM guide
/dqe-quality:dqe-audit ~/data/clients.csv --lang=fr --pm

# Spanish report
/dqe-quality:dqe-audit ~/data/clientes.csv --lang=es

# Windows path (auto-converted to WSL)
/dqe-quality:dqe-audit "C:\Users\demo\data\export.csv" --lang=de
```

---

## dqe-campaign — End-to-end campaign workflow

```
/dqe-quality:dqe-campaign [path/to/contacts.csv | --source=<type>] [--lang=fr|en] [--no-server]
```

The flagship skill. Audits your contact data and cleans it through the DQE One Server — email validation, phone validation, deduplication — producing a campaign-ready contact count.

**The data can come from a local CSV file or directly from any remote source connected to the DQE One Server.**

### Data sources

| Source | Invocation |
|--------|-----------|
| Local CSV | `/dqe-quality:dqe-campaign ~/data/contacts.csv` |
| Salesforce | `/dqe-quality:dqe-campaign --source=salesforce` |
| Microsoft Dynamics 365 | `/dqe-quality:dqe-campaign --source=dynamics` |
| PostgreSQL | `/dqe-quality:dqe-campaign --source=postgres` |
| Google BigQuery | `/dqe-quality:dqe-campaign --source=bigquery` |
| Snowflake | `/dqe-quality:dqe-campaign --source=snowflake` |
| SFTP | `/dqe-quality:dqe-campaign --source=sftp` |
| Interactive (ask me) | `/dqe-quality:dqe-campaign` |

### Flow — Local CSV

1. **Local audit** — detects email/phone columns, validates formats, counts duplicates, calculates a quality score
2. **Inline audit card** — score, key metrics, campaign-ready estimate
3. **Server-side cleaning** via DQE One Server (if MCP configured and confirmed):
   - Uploads the file, creates and runs `check_email`, `check_phone`, `check_duplicate`
4. **Campaign-ready count**

### Flow — Remote source (Salesforce, Dynamics, PostgreSQL, BigQuery, Snowflake, SFTP)

1. **Credential selection** — lists available connections from `list_credentials`
2. **Table / object selection** — asks for the Salesforce object, Dynamics entity, SQL table, BigQuery dataset.table, Snowflake database.schema.table, or SFTP path
3. **Field mapping** — asks for primary key, email field, phone field
4. **Server-side processes** — creates and runs `check_email`, `check_phone`, `check_duplicate` directly on the remote data — **no local file needed**
5. **Campaign-ready count**

```bash
# Interactive — skill asks where the data is
/dqe-quality:dqe-campaign

# From a local CSV
/dqe-quality:dqe-campaign ~/data/landing-page-june.csv

# From Dynamics 365 (skip the source question)
/dqe-quality:dqe-campaign --source=dynamics

# From Salesforce
/dqe-quality:dqe-campaign --source=salesforce

# Local audit only — no MCP calls
/dqe-quality:dqe-campaign ~/data/contacts.csv --no-server
```

**Example output (local CSV):**

```
╔══════════════════════════════════════════════════════════════╗
║  DQE Data Quality Audit                                      ║
║  landing-page-fathers-day.csv · 1 247 records · 6 columns    ║
╠══════════════════════════════════════════════════════════════╣
║  Quality Score: 61/100  🟡                                   ║
╠════════════════════════════════════╦═════════════════════════╣
║  📧 Email validation               ║  📱 Phone validation    ║
║  Valid   : 1 089 (87%)             ║  Valid : 1 034 (83%)    ║
║  Invalid : 112                     ║  Invalid: 213           ║
║  Missing : 46                      ║  Missing: 0             ║
╠════════════════════════════════════╩═════════════════════════╣
║  👥 Duplicates detected: 89 records in 41 groups             ║
╠══════════════════════════════════════════════════════════════╣
║  🎯 Campaign-ready estimate: 1 046 / 1 247                   ║
╚══════════════════════════════════════════════════════════════╝

[After DQE server cleaning]

✅ Ready for campaign: 1 158 contacts
```

> Remote source mode requires the `dqe-one` MCP server and at least one credential configured in DQEOne. Use `--no-server` or omit the MCP config to run local audit only.

---

## dqe-list — Workspace overview

```
/dqe-quality:dqe-list
```

Calls the `dqe-one` MCP server and displays a structured overview of your DQEOne workspace:

- **Processes** — ID, name, type, draft status, last run
- **Recent runs** (last 5) — status, record count, errors, date
- **Files** — uploaded datasets with row/column counts
- **Rulesets** — available deduplication rulesets

Ends with a one-line workspace summary and suggested next steps.

*Requires: `dqe-one` MCP server configured. See [MCP setup](#dqe-one-server--mcp-setup).*

---

## dqe-dedup — Create a deduplication process

```
/dqe-quality:dqe-dedup [--source=csv|salesforce|dynamics|postgres|bigquery|sftp]
```

Guides you through creating a `check_duplicate` process on the DQE One Server:

1. Loads available files, rulesets, and credentials in parallel
2. Asks for the data source (CSV, Salesforce, Dynamics, PostgreSQL, BigQuery, SFTP)
3. Asks for ruleset, primary key, and field mapping — one section at a time
4. Shows a full configuration summary for confirmation
5. Calls `create_process` and optionally triggers the first run

```bash
# Start with a specific source pre-selected
/dqe-quality:dqe-dedup --source=csv
/dqe-quality:dqe-dedup --source=salesforce
```

*Requires: `dqe-one` MCP server configured.*

---

## dqe-run — Run a process

```
/dqe-quality:dqe-run [process_name_or_id]
```

Triggers execution of a DQE process and shows its status.

1. Lists processes (or matches the one you named)
2. Confirms the process details (warns if still in draft)
3. Calls `run_process`
4. Shows the run status immediately and interprets `completed`, `running`, or `failed`

```bash
# Pick from the list
/dqe-quality:dqe-run

# Run a specific process by name
/dqe-quality:dqe-run "Monthly dedup — CRM"
```

*Requires: `dqe-one` MCP server configured.*

---

## DQE One Server — MCP setup

The three skills `dqe-list`, `dqe-dedup`, `dqe-run`, and the server-cleaning phase of `dqe-campaign` all require a **DQE One Server** instance configured as an MCP server named `dqe-one`.

### Option A — Using the dqe-one-mcp CLI (recommended)

```bash
pip install dqe-one-mcp
dqe-one-mcp install https://your-dqe-instance.com
```

This writes the MCP config to `.claude/settings.json` automatically.

### Option B — Manual configuration

Add this to your `.claude/settings.json`:

```json
{
  "mcpServers": {
    "dqe-one": {
      "type": "http",
      "url": "https://your-dqe-instance.com/mcp",
      "headers": {
        "Authorization": "Basic <base64(email:api_token)>"
      }
    }
  }
}
```

Replace `<base64(email:api_token)>` with the output of:

```bash
echo -n "your@email.com:your_api_token" | base64
```

Get your API token from **My Profile** in the DQE One web interface, or from the **Setup** page at `/mcp-setup/`.

---

## The 6 dimensions

| # | Dimension | What it detects |
|---|---|---|
| 1 | **Completeness** | Fill rate per column, globally empty fields |
| 2 | **Invalid dates** | Format errors, future dates, impossible values, mixed formats |
| 3 | **Duplicates** | Exact duplicates, near-duplicates (name+email, name+address) |
| 4 | **Anomalies** | Statistical outliers, generic values (null, test, xxx…), digits in text fields |
| 5 | **Broken relationships** | Postal code format per country (FR/DE/ES/US), ZIP/city mismatches, unreachable contacts |
| 6 | **Format inconsistencies** | Mixed phone formats, inconsistent casing, type heterogeneity |

---

## The reports

### 📊 Audit Report (dqe-audit — always generated)

- Quality score (0–100) with colour-coded rating
- Column profiling: detected type, fill rate, dominant value type
- Executive summary with 6 dimension cards
- Detailed per-dimension analysis with complete anomaly tables
- DQE service recommendations based on findings
- **Next Steps** — numbered action list from actual findings
- **Contact DQE Software** CTA block

### ⚙️ Project Manager Guide (dqe-audit — with `--pm`)

Advanced technical document for DQE internal teams:

- Detected parameters: encoding, delimiter, row/column counts
- Full column schema with top values and type distribution
- Prioritised treatment plan per dimension
- Technical configuration cards per relevant DQE service

---

## Options

### `--lang` — Report language (`dqe-audit`, `dqe-campaign`)

| Value | Language |
|-------|----------|
| `en` | English (default) |
| `us` | English (alias) |
| `fr` | French |
| `de` | German |
| `es` | Spanish |

### `--pm` — Project Manager guide (`dqe-audit` only)

Generates the internal PM guide alongside the audit report.

### `--no-server` — Local audit only (`dqe-campaign` only)

Skips all MCP server calls. Runs the local analysis only and stops after the audit card.

### `--source=<type>` — Pre-select data source (`dqe-campaign`, `dqe-dedup`)

Skips the source selection question. Accepted values: `csv`, `salesforce`, `dynamics`, `postgres`, `bigquery`, `snowflake`, `sftp`.

---

## Output files

Generated by `dqe-audit` next to the source CSV:

```
<basename>_dqe_audit_YYYYMMDD_<lang>.html        # always
<basename>_dqe_pm_guide_YYYYMMDD_<lang>.html     # with --pm
```

**Collision guard:** if a file with the same name already exists, a numeric suffix is added automatically.

---

## File size handling

| File size | Behaviour |
|-----------|-----------|
| Up to 200k rows | Full analysis — every row |
| 200k – 500k rows | Auto-sampled (1 in N rows), result extrapolated |
| Above 500k rows | Rejected — tip provided to extract a sample |

---

## Requirements

- [Claude Code](https://claude.ai/code) CLI, desktop app, or IDE extension
- Python 3.x — standard library only, **no `pip install` needed**
- For MCP skills: a running [DQE One Server](https://www.dqe-software.com) instance

---

## License

MIT — © 2026 [DQE Software](https://github.com/DQE-SOFTWARE)

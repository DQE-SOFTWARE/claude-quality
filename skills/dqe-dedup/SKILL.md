---
name: dqe-dedup
description: "Guided creation of a DQE deduplication process on the dqe-one MCP server. Walks the user through selecting a data source (CSV file, Salesforce, Dynamics, PostgreSQL, BigQuery, SFTP), choosing a ruleset, mapping fields, and triggering the first run. Use when the user wants to set up deduplication or when dqe-campaign needs to create a dedup process."
user-invokable: true
argument-hint: "[--source=csv|salesforce|dynamics|postgres|bigquery|sftp]"
metadata:
  author: DQE Software
  version: "1.0.0"
  category: dqe-one
  requires_mcp: dqe-one
---

# DQE One — Create a Deduplication Process (Guided)

Use the `dqe-one` MCP server to guide the user through creating a `check_duplicate` process step by step.

**Prerequisite:** The `dqe-one` MCP server must be configured. If it is not connected, say so and stop.

---

## STEP 0 — Parse arguments

Check `$ARGUMENTS` for `--source=<type>`. If present, pre-select that source type and skip the source question. Otherwise ask.

---

## STEP 1 — Load available resources (parallel)

Before asking any questions, call these three tools in parallel so you have the data ready:

```
list_files        → available CSV files
list_rulesets     → available deduplication rulesets
list_credentials  → available data source credentials
```

If `list_rulesets` returns an empty list, warn the user:
> "No rulesets are configured yet. A ruleset defines the matching and merging rules for deduplication. Please create one in the DQEOne interface first, then come back."
> Stop here.

---

## STEP 2 — Collect configuration (one section at a time)

Ask questions section by section. Do not proceed to the next section until the current one is answered.

### Section A — Process name
> "What would you like to name this deduplication process?"

### Section B — Data source
> "Where is your data?
> - `csv` — an uploaded file (shown below)
> - `salesforce` — Salesforce org
> - `dynamics` — Microsoft Dynamics 365
> - `postgres` — PostgreSQL database
> - `bigquery` — Google BigQuery
> - `sftp` — SFTP server"

Show the list of available files (from `list_files`) and credentials (from `list_credentials`) to help the user decide.

Depending on the answer:
- **csv**: ask which file ID to use (show the file list)
- **salesforce / dynamics / postgres / bigquery / sftp**: ask which credential ID to use (show credential list), then ask for the object/table name
- **sftp**: additionally ask for input file path and output directory path

### Section C — Ruleset
> "Which ruleset should govern the matching and merging rules?"

Show the ruleset list (ID, name, source). If only one ruleset exists, propose it automatically.

### Section D — Primary key
> "Which field is the unique identifier for each record? (e.g. `Id`, `email`, `customer_id`)"

If the source is a CSV file, call `get_file` with the chosen file ID to show the available column names.

### Section E — Field mapping
> "Which fields should be included in the deduplication? List the field names, or confirm to use all columns."

Suggest the fields from `get_file` if CSV; otherwise ask the user to provide them.

Build the `fields` object: `{ "FieldName": "Display Label", … }`.

---

## STEP 3 — Confirmation

Show a complete summary of the configuration:

```
Process name : <name>
Source       : <source>
File / Object: <file name or object name>
Credential   : <credential name> (if applicable)
Ruleset      : <ruleset name>
Primary key  : <field>
Fields       : <field list>
```

Ask: _"Does this look correct? I'll create the process now."_

If the user requests changes, go back to the relevant section.

---

## STEP 4 — Create the process

Call `create_process` with the collected parameters:

```json
{
  "name": "<name>",
  "kind": "check_duplicate",
  "source": "<source>",
  "primaryKey": "<field>",
  "fields": { … },
  "ruleSet": <ruleset_id>,
  "file": <file_id>,          // if source=csv
  "credential": <cred_id>,    // if not csv
  "object": "<table_name>"    // if not csv and not sftp
}
```

On success: _"✅ Process **<name>** created (ID: <id>)."_
On error: report the error and ask whether to retry with different parameters.

---

## STEP 5 — Offer immediate execution

Ask: _"Would you like to run this process now?"_

If yes: call `run_process` with the new process ID, then call `list_runs` filtered by that process ID to show initial status.

Report:
- If status is `running` or `queued`: _"⏳ Process is running. Use `/dqe-quality:dqe-list` in a few minutes to check the final status."_
- If status is `completed`: show record count and any errors.
- If status is `failed`: show the error message and suggest checking credentials or source connectivity.
